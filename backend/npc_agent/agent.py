import random
from typing import List, Dict, Optional
from vertexai.generative_models import GenerativeModel
from . import prompt

class WerewolfAgent:
    """Vertex AIベースの人狼ゲームエージェント"""
    
    def __init__(self, name: str, description: str, instruction: str, model_name: str = "gemini-1.5-flash"):
        self.name = name
        self.description = description
        self.instruction = instruction
        self.model_name = model_name
        self.model = GenerativeModel(model_name)
    
    def generate_response(self, context: str) -> str:
        """指定されたコンテキストに基づいて応答を生成"""
        try:
            prompt_text = f"""
{self.instruction}

{context}

上記の情報を元に、あなたの役割({self.name})に従って適切な発言を生成してください。
発言は50文字以内で、自然で人間らしい内容にしてください。

発言:
"""
            response = self.model.generate_content(prompt_text)
            return response.text.strip()[:100]  # 100文字制限
        except Exception as e:
            # フォールバック
            fallback_responses = {
                "question_agent": ["みなさんの意見を聞かせてください。", "何か気になることはありませんか？"],
                "accuse_agent": ["少し怪しい行動が見えました。", "この発言は疑わしいですね。"],
                "support_agent": ["その通りだと思います。", "良い指摘ですね。"]
            }
            return random.choice(fallback_responses.get(self.name, ["..."]))

class AgentTool:
    """エージェントツールラッパー"""
    def __init__(self, agent: WerewolfAgent):
        self.agent = agent
    
    def execute(self, context: str) -> str:
        return self.agent.generate_response(context)

# 質問エージェント
question_agent = WerewolfAgent(
    name="question_agent",
    description="""人狼ゲームに参加しているプレイヤーとして、他のプレイヤーに質問を生成するエージェントです。
    このエージェントの仕事は、情報を収集し、他のプレイヤーの行動や発言から役職を特定することです。
    自身が村人側の場合は、他のプレイヤーの行動や発言を観察し、誰が人狼であるかを見極めることが目的です。
    自身が人狼側の場合は、他のプレイヤーを混乱させるために質問をすることが目的です。""",
    instruction=prompt.QUESTION_AGENT_INSTR,
)

# 告発エージェント
accuse_agent = WerewolfAgent(
    name="accuse_agent", 
    description="""人狼ゲームに参加しているプレイヤーとして、他のプレイヤーに疑いの目を向ける発言を生成するエージェントです。
    このエージェントの仕事は、他のプレイヤーの行動や発言から、誰が怪しいかを特定し、疑いの目を向けることです。
    自身が村人側の場合は、他のプレイヤーの行動や発言を観察し、誰が人狼であるかを見極めることが目的です。
    自身が人狼側の場合は、他のプレイヤーを告発することで、村人側を混乱させることが目的です。""",
    instruction=prompt.ACCUSE_AGENT_INSTR,
)

# サポートエージェント  
support_agent = WerewolfAgent(
    name="support_agent",
    description="""人狼ゲームに参加しているプレイヤーとして、他のプレイヤーをサポートする発言を生成するエージェントです。
    このエージェントの仕事は、他のプレイヤーの行動や発言を分析し、自身が所属する陣営を支援することです。
    自身が村人側の場合は、村人側のプレイヤーが疑われるのを擁護するのが目的です。
    自身が人狼側の場合は、他のプレイヤーをサポートすることで、村人側を混乱させることが目的です。""",
    instruction=prompt.SUPPORT_AGENT_INSTR,
)

class RootAgent:
    """複数のエージェントを統合するルートエージェント"""
    
    def __init__(self):
        self.model = GenerativeModel("gemini-1.5-flash")
        self.question_tool = AgentTool(question_agent)
        self.accuse_tool = AgentTool(accuse_agent)
        self.support_tool = AgentTool(support_agent)
    
    def generate_speech(self, player_info: Dict, game_context: Dict, recent_messages: List[Dict]) -> str:
        """統合された発言を生成"""
        try:
            # 各エージェントから提案を取得
            context = self._build_context(player_info, game_context, recent_messages)
            
            # 状況に応じてエージェントを選択
            agent_outputs = []
            
            # ゲーム序盤は質問を重視
            if game_context.get('day_number', 1) <= 2:
                question_output = self.question_tool.execute(context)
                agent_outputs.append(f"質問案: {question_output}")
            
            # 中盤以降は告発とサポートを追加
            if game_context.get('day_number', 1) >= 2:
                accuse_output = self.accuse_tool.execute(context)
                support_output = self.support_tool.execute(context)
                agent_outputs.append(f"告発案: {accuse_output}")
                agent_outputs.append(f"支援案: {support_output}")
            
            # ルートエージェントが最終判断
            final_prompt = f"""
{prompt.ROOT_AGENT_INSTR}

# あなたの情報
- 名前: {player_info.get('name', '不明')}
- 役職: {player_info.get('role', '不明')}
- 陣営: {'人狼' if player_info.get('role') == 'werewolf' else '村人'}

# ゲーム状況
{context}

# 各エージェントからの提案
{chr(10).join(agent_outputs)}

上記の提案を参考に、現在の状況に最も適した発言を1つ選んで生成してください。
- 50文字以内で簡潔に
- あなたの役職と目標に合致した内容
- 自然で人間らしい発言

最終発言:
"""
            
            response = self.model.generate_content(final_prompt)
            speech = response.text.strip()
            
            # 発言の長さを制限
            if len(speech) > 80:
                speech = speech[:77] + "..."
                
            return speech
            
        except Exception as e:
            # エラー時のフォールバック
            fallback_speeches = [
                "今の状況をよく考えてみましょう。",
                "皆さんの意見を聞かせてください。", 
                "慎重に判断したいと思います。",
                "何か見落としはないでしょうか？"
            ]
            return random.choice(fallback_speeches)
    
    def _build_context(self, player_info: Dict, game_context: Dict, recent_messages: List[Dict]) -> str:
        """エージェントに渡すコンテキストを構築"""
        context_parts = []
        
        # ゲーム状況
        context_parts.append(f"現在{game_context.get('day_number', 1)}日目の{game_context.get('phase', '昼')}フェーズです。")
        context_parts.append(f"生存プレイヤー数: {game_context.get('alive_count', '不明')}人")
        
        # 最近の発言履歴
        if recent_messages:
            context_parts.append("最近の発言:")
            for msg in recent_messages[-3:]:  # 最新3件
                speaker = msg.get('speaker', '不明')
                content = msg.get('content', '')
                context_parts.append(f"- {speaker}: {content}")
        
        return "\n".join(context_parts)

# グローバルインスタンス
root_agent = RootAgent()
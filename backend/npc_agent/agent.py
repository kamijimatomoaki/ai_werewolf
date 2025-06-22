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
                "support_agent": ["その通りだと思います。", "良い指摘ですね。"],
                "coming_out_agent": ["まだ時期ではありません。", "もう少し様子を見ます。"]
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
    description="""人狼ゲームに参加しているプレイヤーとして、味方支援と信頼構築に特化したエージェントです。
    同陣営プレイヤーの擁護と信頼関係の構築、建設的な議論の促進が目的です。
    村人側では確実な村人の擁護、人狼側では間接的支援と信頼獲得を行います。""",
    instruction=prompt.SUPPORT_AGENT_INSTR,
)

# カミングアウトエージェント
coming_out_agent = WerewolfAgent(
    name="coming_out_agent",
    description="""人狼ゲームの役職公開（カミングアウト）に特化した戦略エージェントです。
    役職公開のタイミングと方法の最適化、真役職の信憑性向上と偽役職の演出が目的です。
    村人側では真証明、人狼側では偽装と村人側撹乱を行います。""",
    instruction=prompt.COMING_OUT_AGENT_INSTR,
)

class RootAgent:
    """複数のエージェントを統合するルートエージェント"""
    
    def __init__(self):
        self.model = GenerativeModel("gemini-1.5-flash")
        self.question_tool = AgentTool(question_agent)
        self.accuse_tool = AgentTool(accuse_agent)
        self.support_tool = AgentTool(support_agent)
        self.coming_out_tool = AgentTool(coming_out_agent)
    
    def generate_speech(self, player_info: Dict, game_context: Dict, recent_messages: List[Dict]) -> str:
        """統合された発言を生成"""
        try:
            # 各エージェントから提案を取得
            context = self._build_context(player_info, game_context, recent_messages)
            
            # カミングアウト判定を最優先でチェック
            co_context = self._build_coming_out_context(player_info, game_context, recent_messages)
            coming_out_output = self.coming_out_tool.execute(co_context)
            
            # カミングアウトが必要と判断された場合は即座に実行
            if self._should_come_out(coming_out_output, player_info, game_context):
                return self._format_coming_out_speech(coming_out_output, player_info)
            
            # 通常のエージェント選択ロジック
            agent_outputs = []
            day_number = game_context.get('day_number', 1)
            
            # ゲーム序盤（1-2日目）: 情報収集重視
            if day_number <= 2:
                question_output = self.question_tool.execute(context)
                agent_outputs.append(f"質問案: {question_output}")
                
                # 序盤でも適度なサポートを追加
                support_output = self.support_tool.execute(context)
                agent_outputs.append(f"支援案: {support_output}")
            
            # 中盤（3-4日目）: 積極的推理と立場明確化
            elif day_number <= 4:
                question_output = self.question_tool.execute(context)
                accuse_output = self.accuse_tool.execute(context)
                support_output = self.support_tool.execute(context)
                agent_outputs.extend([
                    f"質問案: {question_output}",
                    f"告発案: {accuse_output}",
                    f"支援案: {support_output}"
                ])
            
            # 終盤（5日目以降）: 決定的行動重視
            else:
                accuse_output = self.accuse_tool.execute(context)
                support_output = self.support_tool.execute(context)
                agent_outputs.extend([
                    f"告発案: {accuse_output}",
                    f"支援案: {support_output}"
                ])
                
                # 終盤でのカミングアウトも検討
                agent_outputs.append(f"カミングアウト案: {coming_out_output}")
            
            # ルートエージェントが最終判断
            final_prompt = self._build_final_prompt(player_info, game_context, context, agent_outputs)
            
            response = self.model.generate_content(final_prompt)
            speech = response.text.strip()
            
            # 発言の長さを制限
            if len(speech) > 80:
                speech = speech[:77] + "..."
                
            return speech
            
        except Exception as e:
            # エラー時のフォールバック（より戦略的なフォールバック）
            role = player_info.get('role', 'villager')
            day_number = game_context.get('day_number', 1)
            
            fallback_speeches = {
                'villager': [
                    "情報を整理して冷静に判断しましょう。",
                    "疑わしい点があれば教えてください。",
                    "みんなで協力して真実を見つけましょう。"
                ],
                'werewolf': [
                    "慎重に考えたいと思います。",
                    "皆さんの意見を聞かせてください。",
                    "状況を整理してみましょう。"
                ],
                'seer': [
                    "次の占い結果を見てから判断したいです。",
                    "現在の情報ではまだ不十分です。",
                    "結果を整理してから話します。"
                ],
                'bodyguard': [
                    "守るべき人を慎重に選びたいです。",
                    "みんなを守りたいと思います。",
                    "信頼できる人を探しています。"
                ]
            }
            
            speeches = fallback_speeches.get(role, fallback_speeches['villager'])
            return random.choice(speeches)
    
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
    
    def _build_coming_out_context(self, player_info: Dict, game_context: Dict, recent_messages: List[Dict]) -> str:
        """カミングアウト判定用のコンテキストを構築"""
        context_parts = []
        
        # 基本情報
        day_number = game_context.get('day_number', 1)
        alive_count = game_context.get('alive_count', 5)
        role = player_info.get('role', 'villager')
        
        context_parts.append(f"あなたの役職: {role}")
        context_parts.append(f"現在{day_number}日目、生存者{alive_count}人")
        
        # カミングアウトの緊急性判定
        urgency_factors = []
        if day_number >= 3:
            urgency_factors.append("中盤以降で戦略的行動が必要")
        if alive_count <= 5:
            urgency_factors.append("少人数で影響力が大")
        
        if urgency_factors:
            context_parts.append("緊急性: " + ", ".join(urgency_factors))
        
        # 最近の議論から自分への疑いをチェック
        if recent_messages:
            player_name = player_info.get('name', '')
            suspicion_count = 0
            for msg in recent_messages[-5:]:
                content = msg.get('content', '').lower()
                if player_name.lower() in content and any(word in content for word in ['疑', '怪し', '人狼']):
                    suspicion_count += 1
            
            if suspicion_count >= 2:
                context_parts.append("警告: あなたへの疑いが高まっています")
        
        return "\n".join(context_parts)
    
    def _should_come_out(self, coming_out_output: str, player_info: Dict, game_context: Dict) -> bool:
        """カミングアウトすべきか判定"""
        # カミングアウトを示すキーワードをチェック
        co_keywords = ['実は', '私は', 'CO', 'カミングアウト', '占い師', 'ボディガード']
        
        output_lower = coming_out_output.lower()
        for keyword in co_keywords:
            if keyword in coming_out_output or keyword.lower() in output_lower:
                return True
        
        # 緊急状況での強制カミングアウト
        day_number = game_context.get('day_number', 1)
        alive_count = game_context.get('alive_count', 5)
        role = player_info.get('role', 'villager')
        
        if day_number >= 4 and alive_count <= 4 and role in ['seer', 'bodyguard']:
            return True
            
        return False
    
    def _format_coming_out_speech(self, coming_out_output: str, player_info: Dict) -> str:
        """カミングアウト発言をフォーマット"""
        # 基本的にはエージェントの出力を使用
        if len(coming_out_output) > 100:
            coming_out_output = coming_out_output[:97] + "..."
        
        return coming_out_output
    
    def _build_final_prompt(self, player_info: Dict, game_context: Dict, context: str, agent_outputs: List[str]) -> str:
        """最終判断用プロンプトを構築"""
        # ペルソナ情報の抽出
        persona = player_info.get('persona', {})
        persona_info = ""
        if persona:
            persona_info = f"""
# あなたのペルソナ
- 性格: {persona.get('personality', '不明')}
- 話し方: {persona.get('speech_style', '不明')}
- 背景: {persona.get('background', '不明')}"""
        
        return f"""
{prompt.ROOT_AGENT_INSTR}

# あなたの情報
- 名前: {player_info.get('name', '不明')}
- 役職: {player_info.get('role', '不明')}
- 陣営: {'人狼' if player_info.get('role') == 'werewolf' else '村人'}
{persona_info}

# ゲーム状況
{context}

# 各エージェントからの提案
{chr(10).join(agent_outputs)}

上記の提案を参考に、現在の状況に最も適した発言を1つ選んで生成してください。
【重要】ペルソナの話し方と性格を絶対に守ってください。

最終発言:
"""

# グローバルインスタンス
root_agent = RootAgent()
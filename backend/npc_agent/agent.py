import os
import random
import asyncio
from typing import List, Dict, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, FunctionDeclaration, Tool, GenerationConfig
from dotenv import load_dotenv
from . import prompt

# 環境変数を読み込み
load_dotenv()

# Vertex AI初期化
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "").strip('"')
GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION", "").strip('"')

if GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
    try:
        vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
        print(f"[DEBUG] Vertex AI initialized in npc_agent: {GOOGLE_PROJECT_ID} @ {GOOGLE_LOCATION}")
    except Exception as e:
        print(f"[WARNING] Failed to initialize Vertex AI in npc_agent: {e}")
else:
    print(f"[WARNING] Missing Vertex AI credentials: PROJECT={GOOGLE_PROJECT_ID}, LOCATION={GOOGLE_LOCATION}")

def generate_content_with_timeout(model, prompt, timeout_seconds=30):
    """シンプルで確実なcontent生成（Cloud Run環境対応）"""
    try:
        # GenerationConfigでより確実な制限を設定
        generation_config = GenerationConfig(
            max_output_tokens=1000,  # 最大出力トークン数
            temperature=0.7,         # ランダム性
            top_p=0.9               # nucleus sampling
        )
        
        print(f"[DEBUG] Calling Vertex AI API (timeout={timeout_seconds}s)")
        
        # Cloud Run環境では信号処理を避け、直接APIを呼び出す
        # Vertex AI自体にタイムアウトが組み込まれているため
        response = model.generate_content(prompt, generation_config=generation_config)
        print(f"[DEBUG] Vertex AI API call successful")
        return response
            
    except Exception as e:
        print(f"[ERROR] Error in generate_content_with_timeout: {e}")
        # 詳細なエラー情報をログに記録
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        raise e

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
発言は500文字以内で、自然で人間らしい内容にしてください。

発言:
"""
            response = generate_content_with_timeout(self.model, prompt_text, timeout_seconds=20)
            speech = response.text.strip()
            
            # 自然な切断処理
            if len(speech) > 500:
                cutoff_point = speech.rfind('。', 0, 497)
                if cutoff_point > 100:
                    speech = speech[:cutoff_point + 1]
                else:
                    speech = speech[:497] + "..."
            
            return speech
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

# 人狼ゲーム専用ツール定義
def create_werewolf_tools():
    """人狼ゲーム専用のFunction Callingツールを作成"""
    
    # プレイヤー分析ツール
    analyze_player_tool = FunctionDeclaration(
        name="analyze_player",
        description="指定したプレイヤーの行動パターンと発言を分析して、役職を推測する",
        parameters={
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "分析対象のプレイヤー名"
                },
                "behavior_focus": {
                    "type": "string", 
                    "description": "分析の焦点（投票パターン、発言内容、積極性など）"
                }
            },
            "required": ["player_name", "behavior_focus"]
        }
    )
    
    # 投票戦略ツール
    vote_strategy_tool = FunctionDeclaration(
        name="plan_vote_strategy",
        description="現在の状況に基づいて最適な投票戦略を立案する",
        parameters={
            "type": "object",
            "properties": {
                "target_candidates": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "投票候補者のリスト"
                },
                "strategy_type": {
                    "type": "string",
                    "enum": ["offensive", "defensive", "information_gathering"],
                    "description": "戦略のタイプ"
                }
            },
            "required": ["target_candidates", "strategy_type"]
        }
    )
    
    # 疑惑度評価ツール
    suspicion_rating_tool = FunctionDeclaration(
        name="rate_player_suspicion",
        description="プレイヤーごとの疑惑度を1-10のスケールで評価する",
        parameters={
            "type": "object",
            "properties": {
                "players": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "評価対象のプレイヤー名リスト"
                },
                "evaluation_criteria": {
                    "type": "string",
                    "description": "評価基準（発言の一貫性、投票行動、積極性など）"
                }
            },
            "required": ["players", "evaluation_criteria"]
        }
    )
    
    # カミングアウトタイミング分析ツール
    coming_out_timing_tool = FunctionDeclaration(
        name="analyze_coming_out_timing",
        description="カミングアウトの最適なタイミングを分析する",
        parameters={
            "type": "object",
            "properties": {
                "my_role": {
                    "type": "string",
                    "description": "自分の役職"
                },
                "game_phase": {
                    "type": "string",
                    "description": "現在のゲームフェーズ"
                },
                "alive_count": {
                    "type": "integer",
                    "description": "生存プレイヤー数"
                }
            },
            "required": ["my_role", "game_phase", "alive_count"]
        }
    )
    
    return Tool(function_declarations=[
        analyze_player_tool,
        vote_strategy_tool, 
        suspicion_rating_tool,
        coming_out_timing_tool
    ])

class RootAgent:
    """複数のエージェントを統合するルートエージェント（ツール使用対応）"""
    
    def __init__(self):
        # ツール対応モデルを初期化
        try:
            self.werewolf_tools = create_werewolf_tools()
            self.model = GenerativeModel(
                "gemini-1.5-flash",
                tools=[self.werewolf_tools]
            )
            self.tools_available = True
            print("[DEBUG] Tool-enabled model initialized successfully")
        except Exception as e:
            print(f"[WARNING] Failed to initialize tool-enabled model: {e}")
            self.model = GenerativeModel("gemini-1.5-flash")  # フォールバック
            self.tools_available = False
            
        # 従来のエージェントツールも保持
        self.question_tool = AgentTool(question_agent)
        self.accuse_tool = AgentTool(accuse_agent)
        self.support_tool = AgentTool(support_agent)
        self.coming_out_tool = AgentTool(coming_out_agent)
    
    def execute_tool_function(self, function_name: str, args: Dict) -> str:
        """ツール関数を実際に実行する"""
        try:
            if function_name == "analyze_player":
                return self._analyze_player(args["player_name"], args["behavior_focus"])
            elif function_name == "plan_vote_strategy":
                return self._plan_vote_strategy(args["target_candidates"], args["strategy_type"])
            elif function_name == "rate_player_suspicion":
                return self._rate_player_suspicion(args["players"], args["evaluation_criteria"])
            elif function_name == "analyze_coming_out_timing":
                return self._analyze_coming_out_timing(args["my_role"], args["game_phase"], args["alive_count"])
            else:
                return f"Unknown tool function: {function_name}"
        except Exception as e:
            return f"Tool execution error: {str(e)}"
    
    def _analyze_player(self, player_name: str, behavior_focus: str) -> str:
        """プレイヤー分析ツールの実装"""
        analysis_results = [
            f"{player_name}の{behavior_focus}について分析しました。",
            "発言パターンから推測される役職傾向を検討中...",
            "投票行動との一貫性をチェック中..."
        ]
        return " ".join(analysis_results)
    
    def _plan_vote_strategy(self, target_candidates: List[str], strategy_type: str) -> str:
        """投票戦略立案ツールの実装"""
        strategy_map = {
            "offensive": "積極的に疑わしいプレイヤーを排除する戦略",
            "defensive": "確実な情報に基づいて慎重に判断する戦略", 
            "information_gathering": "情報収集を優先する戦略"
        }
        strategy_desc = strategy_map.get(strategy_type, "バランス型戦略")
        return f"候補者{target_candidates}に対して{strategy_desc}を採用することを推奨します。"
    
    def _rate_player_suspicion(self, players: List[str], evaluation_criteria: str) -> str:
        """疑惑度評価ツールの実装"""
        ratings = []
        for player in players:
            # ランダムに疑惑度を設定（実際の実装では詳細な分析を行う）
            suspicion_level = random.randint(3, 8)
            ratings.append(f"{player}: {suspicion_level}/10")
        return f"{evaluation_criteria}基準での疑惑度評価: {', '.join(ratings)}"
    
    def _analyze_coming_out_timing(self, my_role: str, game_phase: str, alive_count: int) -> str:
        """カミングアウトタイミング分析ツールの実装"""
        if my_role in ['seer', 'bodyguard'] and alive_count <= 5:
            return "現在の状況では積極的なカミングアウトを推奨します。情報共有が重要です。"
        elif game_phase == "day_vote" and alive_count <= 4:
            return "投票フェーズでの戦略的カミングアウトを検討してください。"
        else:
            return "現在はカミングアウトよりも情報収集を優先することを推奨します。"

    def generate_speech(self, player_info: Dict, game_context: Dict, recent_messages: List[Dict]) -> str:
        """ツール使用対応の発言生成"""
        # デバッグログ追加
        print(f"[DEBUG] RootAgent.generate_speech called for {player_info.get('name', 'unknown')}")
        print(f"[DEBUG] Tools available: {self.tools_available}")
        print(f"[DEBUG] Player info keys: {list(player_info.keys())}")
        print(f"[DEBUG] Persona data: {player_info.get('persona', 'No persona')}")
        print(f"[DEBUG] Game context: {game_context}")
        print(f"[DEBUG] Recent messages count: {len(recent_messages)}")
        
        # ツール使用が利用可能かチェック
        if not self.tools_available:
            print("[DEBUG] Tools not available, using traditional speech generation")
            return self._generate_traditional_speech(player_info, game_context, recent_messages)
        
        try:
            # コンテキストを構築
            context = self._build_context(player_info, game_context, recent_messages)
            
            # ツール使用を促すプロンプトを構築
            tool_prompt = self._build_tool_enhanced_prompt(player_info, game_context, context, recent_messages)
            
            print("[DEBUG] Attempting tool-enhanced speech generation")
            # AIモデルにツール使用を含めて発言生成を依頼（タイムアウト付き）
            response = generate_content_with_timeout(self.model, tool_prompt, timeout_seconds=25)
            
            # レスポンスを処理（ツール呼び出しを含む）
            final_speech = self._process_response_with_tools(response, player_info, game_context)
            
            print(f"[DEBUG] Tool-enhanced speech generated: {final_speech[:100]}...")
            return final_speech
            
        except (TimeoutError, Exception) as e:
            # タイムアウトやその他のエラー時のフォールバック - 従来の方法を使用
            print(f"[ERROR] Tool-enhanced speech generation failed: {e}")
            print(f"[DEBUG] Falling back to traditional agent system")
            try:
                return self._generate_traditional_speech(player_info, game_context, recent_messages)
            except (TimeoutError, Exception) as fallback_error:
                print(f"[ERROR] Traditional speech generation also failed: {fallback_error}")
                print(f"[DEBUG] Using emergency fallback speech")
                return self._emergency_fallback_speech(player_info)

    def _emergency_fallback_speech(self, player_info: Dict) -> str:
        """緊急時フォールバック発言（AIモデルを使わない）"""
        fallback_speeches = [
            "少し考えさせてください。",
            "状況を整理している途中です。",
            "もう少し様子を見ます。",
            "慎重に判断したいと思います。",
            "皆さんの意見を聞かせてください。"
        ]
        
        # プレイヤー名に基づいて一貫性のある発言を選択
        player_name = player_info.get('name', 'プレイヤー')
        import hashlib
        seed = int(hashlib.md5(player_name.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        selected_speech = random.choice(fallback_speeches)
        print(f"[DEBUG] Emergency fallback speech for {player_name}: {selected_speech}")
        return selected_speech

    def _build_tool_enhanced_prompt(self, player_info: Dict, game_context: Dict, context: str, recent_messages: List[Dict]) -> str:
        """ツール使用を促すプロンプトを構築"""
        # ペルソナ情報の抽出
        persona = player_info.get('persona', {})
        persona_info = ""
        
        if persona:
            if isinstance(persona, str):
                persona_info = f"# あなたのペルソナ設定\n{persona}\n"
            else:
                persona_info = f"# あなたの名前: {player_info.get('name', '不明')}\n"
        
        # 他のプレイヤー情報を抽出
        other_players = [p['name'] for p in game_context.get('all_players', []) 
                        if p['name'] != player_info.get('name') and p['is_alive']]
        
        return f"""
あなたは人狼ゲームの熟練プレイヤーです。現在の状況を分析し、最適な発言を行ってください。

{persona_info}

# あなたの基本情報
- 名前: {player_info.get('name', '不明')}
- 役職: {player_info.get('role', '不明')}
- 陣営: {'人狼' if player_info.get('role') == 'werewolf' else '村人'}

# ゲーム状況
{context}

# 生存プレイヤー: {', '.join(other_players)}

# 利用可能なツール
以下のツールを使用して分析を行い、より戦略的な発言を生成できます：
- analyze_player: プレイヤーの行動パターンを分析
- plan_vote_strategy: 投票戦略を立案
- rate_player_suspicion: プレイヤーの疑惑度を評価
- analyze_coming_out_timing: カミングアウトのタイミングを分析

必要に応じてツールを使用して状況を分析し、その結果を踏まえて自然で説得力のある発言を生成してください。
ペルソナの特徴（話し方、性格など）を100%維持してください。

発言は500文字以内で、ゲームの進行に貢献する内容にしてください。
"""

    def _process_response_with_tools(self, response, player_info: Dict, game_context: Dict) -> str:
        """ツール呼び出しを含むレスポンスを処理"""
        try:
            # レスポンスにfunction_callsが含まれているかチェック
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # ツール呼び出しがある場合
                if hasattr(candidate.content, 'parts'):
                    tool_results = []
                    text_parts = []
                    
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            # ツール呼び出しを実行
                            function_name = part.function_call.name
                            args = {key: value for key, value in part.function_call.args.items()}
                            
                            print(f"[DEBUG] Executing tool: {function_name} with args: {args}")
                            tool_result = self.execute_tool_function(function_name, args)
                            tool_results.append(f"[{function_name}結果]: {tool_result}")
                            
                        elif hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    
                    # ツール結果がある場合は、それを踏まえて最終発言を生成
                    if tool_results:
                        final_prompt = self._build_final_speech_prompt(
                            player_info, game_context, tool_results, text_parts
                        )
                        # ツールなしモデルで最終発言を生成（タイムアウト付き）
                        simple_model = GenerativeModel("gemini-1.5-flash")
                        final_response = generate_content_with_timeout(simple_model, final_prompt, timeout_seconds=20)
                        return final_response.text.strip()
                    
                    # ツール呼び出しがない場合は通常のテキストを返す
                    elif text_parts:
                        return " ".join(text_parts).strip()
            
            # フォールバック: response.textを使用
            if hasattr(response, 'text') and response.text:
                return response.text.strip()
                
            return "少し考えさせてください。"
            
        except Exception as e:
            print(f"[ERROR] Error processing response with tools: {e}")
            return "状況を整理して考えてみます。"

    def _build_final_speech_prompt(self, player_info: Dict, game_context: Dict, tool_results: List[str], text_parts: List[str]) -> str:
        """ツール結果を踏まえた最終発言生成プロンプト"""
        persona = player_info.get('persona', '')
        persona_info = f"# ペルソナ設定\n{persona}\n" if persona else ""
        
        return f"""
{persona_info}

# ツール分析結果
{chr(10).join(tool_results)}

# 初期発言案
{' '.join(text_parts) if text_parts else ''}

上記のツール分析結果を踏まえて、あなたのペルソナに完全に合致した自然な発言を1つ生成してください。
- ペルソナの話し方、口調、性格を100%維持
- ツール分析結果を自然に反映
- 500文字以内
- 人狼ゲームの進行に貢献する内容

最終発言:
"""

    def _generate_traditional_speech(self, player_info: Dict, game_context: Dict, recent_messages: List[Dict]) -> str:
        """従来のエージェントシステムによる発言生成（改良版）"""
        try:
            # コンテキストを構築
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
            
            # ルートエージェントが最終判断（ツールなしモデル使用）
            final_prompt = self._build_final_prompt(player_info, game_context, context, agent_outputs)
            
            # ツールなしの従来モデルを使用（タイムアウト付き）
            simple_model = GenerativeModel("gemini-1.5-flash")
            response = generate_content_with_timeout(simple_model, final_prompt, timeout_seconds=20)
            speech = response.text.strip()
            
            # 発言の長さを制限（500文字に設定）
            if len(speech) > 500:
                cutoff_point = speech.rfind('。', 0, 497)
                if cutoff_point > 100:
                    speech = speech[:cutoff_point + 1]
                else:
                    speech = speech[:497] + "..."
                
            return speech
            
        except (TimeoutError, Exception) as e:
            print(f"[ERROR] Traditional speech generation failed: {e}")
            if isinstance(e, TimeoutError):
                print(f"[WARNING] Traditional speech generation timed out, using simple fallback")
            # 最後のフォールバック
            return self._generate_simple_fallback_speech(player_info, game_context)
    
    def _generate_simple_fallback_speech(self, player_info: Dict, game_context: Dict) -> str:
        """最終フォールバック発言生成"""
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
        if len(coming_out_output) > 500:
            cutoff_point = coming_out_output.rfind('。', 0, 497)
            if cutoff_point > 100:
                coming_out_output = coming_out_output[:cutoff_point + 1]
            else:
                coming_out_output = coming_out_output[:497] + "..."
        
        return coming_out_output
    
    def _build_final_prompt(self, player_info: Dict, game_context: Dict, context: str, agent_outputs: List[str]) -> str:
        """最終判断用プロンプトを構築"""
        # ペルソナ情報の詳細な抽出
        persona = player_info.get('persona', {})
        persona_info = ""
        
        # デバッグログを追加
        print(f"[DEBUG] _build_final_prompt: persona type={type(persona)}, content={persona}")
        
        if persona:
            if isinstance(persona, dict):
                # 辞書形式の場合
                persona_info = f"""
# あなたの詳細なペルソナ設定
- 年齢: {persona.get('age', '不明')}歳
- 性別: {persona.get('gender', '不明')}
- 性格: {persona.get('personality', '不明')}
- 話し方: {persona.get('speech_style', '不明')}
- 背景: {persona.get('background', '不明')}

【最重要】話し方の指示:
{persona.get('speech_style', '普通の話し方')}で一貫して発言してください。
語尾や口調、方言などの特徴を必ず維持してください。"""
            elif isinstance(persona, str):
                # 文字列形式の場合（実際のケース）
                persona_info = f"""
# あなたの詳細なペルソナ設定
{persona}

【最重要】話し方の指示:
上記のペルソナ設定に記載された話し方、語尾、口調、方言などの全ての特徴を100%維持して発言してください。
設定されたキャラクターの個性を完全に反映してください。"""
            else:
                print(f"[WARNING] Unexpected persona type: {type(persona)}")
                persona_info = f"# あなたの名前: {player_info.get('name', '不明')}"
        
        return f"""
{prompt.ROOT_AGENT_INSTR}

# あなたの基本情報
- 名前: {player_info.get('name', '不明')}
- 役職: {player_info.get('role', '不明')}
- 陣営: {'人狼' if player_info.get('role') == 'werewolf' else '村人'}
{persona_info}

# ゲーム状況
{context}

# 各エージェントからの提案
{chr(10).join(agent_outputs)}

上記の提案を参考に、現在の状況に最も適した発言を1つ選んで生成してください。

【絶対遵守事項】
1. ペルソナの話し方を100%維持すること
2. 語尾や口調の特徴を必ず含めること
3. キャラクターの年齢と性格に合った発言をすること
4. 500文字以内で自然な発言をすること

最終発言:
"""

# グローバルインスタンス
root_agent = RootAgent()
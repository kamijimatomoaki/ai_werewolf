import os
import sys
import random
import asyncio
import uuid
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

# Cloud Run環境でのデフォルト値設定
if not GOOGLE_PROJECT_ID:
    GOOGLE_PROJECT_ID = "fourth-dynamo-423103-q2"
    print(f"[INIT] Using default project ID: {GOOGLE_PROJECT_ID}")

if not GOOGLE_LOCATION:
    GOOGLE_LOCATION = "asia-northeast1"
    print(f"[INIT] Using default location: {GOOGLE_LOCATION}")

print(f"[INIT] Vertex AI initialization check:")
print(f"[INIT] GOOGLE_PROJECT_ID: '{GOOGLE_PROJECT_ID}'")
print(f"[INIT] GOOGLE_LOCATION: '{GOOGLE_LOCATION}'")

# Vertex AI初期化を試行（簡潔版）
vertex_ai_initialized = False
try:
    print(f"[INIT] Starting Vertex AI initialization...")
    print(f"[INIT] - GOOGLE_PROJECT_ID: '{GOOGLE_PROJECT_ID}' (length: {len(GOOGLE_PROJECT_ID) if GOOGLE_PROJECT_ID else 0})")
    print(f"[INIT] - GOOGLE_LOCATION: '{GOOGLE_LOCATION}' (length: {len(GOOGLE_LOCATION) if GOOGLE_LOCATION else 0})")
    
    # 基本的な環境変数確認とデフォルト設定
    if not GOOGLE_PROJECT_ID:
        # Cloud Run環境での自動検出を試行
        try:
            import subprocess
            result = subprocess.run([
                'curl', '-s', '-H', 'Metadata-Flavor: Google',
                'http://metadata.google.internal/computeMetadata/v1/project/project-id'
            ], capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0 and result.stdout.strip():
                GOOGLE_PROJECT_ID = result.stdout.strip()
                print(f"[INIT] Auto-detected project: {GOOGLE_PROJECT_ID}")
        except:
            print(f"[INIT] Could not auto-detect project, using fallback")
            
    if not GOOGLE_LOCATION:
        GOOGLE_LOCATION = "asia-northeast1"
        print(f"[INIT] Using default location: {GOOGLE_LOCATION}")
    
    # Vertex AI初期化
    if GOOGLE_PROJECT_ID and GOOGLE_LOCATION:
        vertexai.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
        
        # 簡単なテスト実行
        test_model = GenerativeModel("gemini-1.5-flash")
        test_response = test_model.generate_content("テスト")
        
        print(f"✅ [SUCCESS] Vertex AI initialized and tested: {GOOGLE_PROJECT_ID} @ {GOOGLE_LOCATION}")
        vertex_ai_initialized = True
    else:
        print(f"❌ [ERROR] Cannot initialize Vertex AI: missing configuration")
        vertex_ai_initialized = False
        
except Exception as e:
    print(f"❌ [ERROR] Vertex AI initialization failed: {e}")
    vertex_ai_initialized = False

def generate_content_with_timeout(model, prompt, timeout_seconds=15):
    """効率化されたcontent生成（ユーザー体験重視・短縮タイムアウト）"""
    try:
        # 高速化のためのGenerationConfig設定
        generation_config = GenerationConfig(
            max_output_tokens=800,   # 出力を短縮してレスポンス向上
            temperature=0.7,         # ランダム性
            top_p=0.9,              # nucleus sampling
            candidate_count=1        # 単一候補で高速化
        )
        
        print(f"[DEBUG] Calling Vertex AI API (optimized timeout={timeout_seconds}s)")
        
        # タイムアウトを短縮して迅速なレスポンスを実現
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
            response = generate_content_with_timeout(self.model, prompt_text, timeout_seconds=12)
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

# 発言履歴分析エージェント
speech_history_agent = WerewolfAgent(
    name="speech_history_agent", 
    description="""発言履歴の収集と分析に特化した情報エージェントです。
    特定プレイヤーの過去の発言パターンを詳細に分析し、発言の一貫性や矛盾点を特定します。
    役職推理のための証拠となる発言を収集し、現在の発言生成に活用できる形で整理します。""",
    instruction=prompt.SPEECH_HISTORY_AGENT_INSTR,
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
    
    # 発言履歴取得ツール
    speech_history_tool = FunctionDeclaration(
        name="get_speech_history",
        description="特定プレイヤーまたは全プレイヤーの発言履歴を取得・分析する",
        parameters={
            "type": "object",
            "properties": {
                "room_id": {
                    "type": "string",
                    "description": "部屋ID"
                },
                "player_name": {
                    "type": "string",
                    "description": "分析対象のプレイヤー名（空の場合は全プレイヤー）"
                },
                "day_number": {
                    "type": "integer",
                    "description": "取得対象の日数（空の場合は全日程）"
                },
                "analysis_focus": {
                    "type": "string",
                    "description": "分析の焦点（役職示唆、投票理由、矛盾点など）"
                }
            },
            "required": ["room_id", "analysis_focus"]
        }
    )
    
    return Tool(function_declarations=[
        analyze_player_tool,
        vote_strategy_tool, 
        suspicion_rating_tool,
        coming_out_timing_tool,
        speech_history_tool
    ])

class RootAgent:
    """複数のエージェントを統合するルートエージェント（ツール使用対応）"""
    
    def __init__(self):
        global vertex_ai_initialized
        print("[DEBUG] RootAgent initialization starting...")
        
        # 基本設定
        self.model = None
        self.tools_available = False
        self.fallback_mode = True
        
        # Vertex AI初期化状態をチェック
        if not vertex_ai_initialized:
            print("[WARNING] Vertex AI not initialized, using fallback mode")
        else:
            # モデル初期化を試行
            try:
                print("[DEBUG] Attempting to initialize AI model...")
                self.model = GenerativeModel("gemini-1.5-flash")
                self.tools_available = False
                self.fallback_mode = False
                print("✅ [SUCCESS] Basic model initialized successfully")
                
                # ツール対応モデルの初期化を試行（オプション）
                try:
                    print("[DEBUG] Attempting to initialize tool-enabled model...")
                    self.werewolf_tools = create_werewolf_tools()
                    tool_model = GenerativeModel("gemini-1.5-flash", tools=[self.werewolf_tools])
                    self.model = tool_model
                    self.tools_available = True
                    print("✅ [SUCCESS] Tool-enabled model initialized successfully")
                except Exception as tool_error:
                    print(f"[WARNING] Tool-enabled model failed, using basic model: {tool_error}")
                    # 基本モデルは既に初期化済みなので続行
                    
            except Exception as model_error:
                print(f"[ERROR] Model initialization failed: {model_error}")
                self.model = None
                self.tools_available = False
                self.fallback_mode = True
        
        # 従来のエージェントツールを初期化（必ず実行）
        try:
            self.question_tool = AgentTool(question_agent)
            self.accuse_tool = AgentTool(accuse_agent)
            self.support_tool = AgentTool(support_agent)
            self.coming_out_tool = AgentTool(coming_out_agent)
            self.speech_history_tool = AgentTool(speech_history_agent)
            print("[DEBUG] Legacy agent tools initialized")
        except Exception as tool_init_error:
            print(f"[WARNING] Legacy agent tools initialization failed: {tool_init_error}")
            
        print(f"[DEBUG] RootAgent initialization complete: model={self.model is not None}, tools={self.tools_available}, fallback={self.fallback_mode}")
    
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
            elif function_name == "get_speech_history":
                # 🚫 発言履歴取得ツールの使用を制限（コンテキスト汚染防止）
                return "発言履歴の取得は制限されています。提供されたコンテキスト情報のみを使用してください。"
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
        """疑惑度評価ツールの実装（知性的分析）"""
        ratings = []
        for player in players:
            # 基本疑惑度（中程度から開始）
            suspicion_level = 5
            
            # 発言量による調整（発言が少ない=疑わしい）
            speech_count = len([log for log in self.recent_speeches 
                              if log.get('speaker') == player])
            if speech_count < 2:
                suspicion_level += 2  # 発言少ない=疑いUp
            elif speech_count > 5:
                suspicion_level -= 1  # 発言多い=疑いDown
            
            # 投票パターンによる調整
            # (実際の投票データがあれば更に詳細な分析可能)
            if "投票" in evaluation_criteria and player in self.recent_speeches:
                # 投票に関する発言の一貫性をチェック
                player_speeches = [log for log in self.recent_speeches 
                                 if log.get('speaker') == player]
                if len(player_speeches) > 0:
                    last_speech = player_speeches[-1].get('content', '')
                    if any(word in last_speech for word in ['疑わしい', '人狼', '怪しい']):
                        suspicion_level -= 1  # 積極的に疑いを表明=疑いDown
            
            # ランダム要素を最小限に（±1のバリエーション）
            suspicion_level += random.randint(-1, 1)
            
            # 範囲制限 (1-10)
            suspicion_level = max(1, min(10, suspicion_level))
            
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
    
    def _get_speech_history(self, room_id: str, player_name: Optional[str], day_number: Optional[int], analysis_focus: str) -> str:
        """発言履歴取得ツールの実装（PostgreSQL CloudSQL連携）"""
        try:
            # データベースセッションを取得
            from game_logic.main import SessionLocal, Player, get_player_speech_history
            
            db = SessionLocal()
            try:
                # room_idをUUIDに変換
                room_uuid = uuid.UUID(room_id)
                
                # プレイヤー名からプレイヤーIDを取得
                player_id = None
                if player_name:
                    player = db.query(Player).filter(Player.character_name == player_name).first()
                    if player:
                        player_id = player.player_id
                    else:
                        return f"プレイヤー '{player_name}' が見つかりません。"
                
                # 発言履歴を取得
                speech_logs = get_player_speech_history(
                    db=db,
                    room_id=room_uuid,
                    player_id=player_id,
                    day_number=day_number,
                    limit=30  # 分析用に十分な数を取得
                )
                
                # 発言履歴が空の場合
                if not speech_logs:
                    return f"発言履歴が見つかりません（プレイヤー: {player_name or '全員'}, 日数: {day_number or '全期間'}）"
                
                # 発言履歴を分析して結果を生成
                if player_name:
                    analysis_result = f"{player_name}の発言履歴分析（{analysis_focus}）:\n"
                    analysis_result += f"- 発言数: {len(speech_logs)}件\n"
                    
                    # 発言内容から傾向を分析
                    contents = [log['content'] for log in speech_logs if log['content']]
                    if contents:
                        # 最新の発言から分析
                        recent_speeches = contents[-5:]  # 最新5件
                        analysis_result += f"- 最新の発言傾向: {self._analyze_speech_patterns(recent_speeches, analysis_focus)}\n"
                        
                        # 時系列での変化を分析
                        if len(contents) >= 3:
                            early_speeches = contents[:len(contents)//2]
                            late_speeches = contents[len(contents)//2:]
                            analysis_result += f"- 発言の変化: {self._compare_speech_periods(early_speeches, late_speeches)}\n"
                        
                        # 具体的な発言例を追加
                        analysis_result += f"- 注目発言: 「{recent_speeches[-1][:50]}...」\n"
                    
                else:
                    analysis_result = f"全プレイヤーの発言履歴分析（{analysis_focus}）:\n"
                    analysis_result += f"- 総発言数: {len(speech_logs)}件\n"
                    
                    # プレイヤー別発言数
                    player_counts = {}
                    for log in speech_logs:
                        name = log['player_name']
                        player_counts[name] = player_counts.get(name, 0) + 1
                    
                    analysis_result += f"- 発言者分布: {dict(sorted(player_counts.items(), key=lambda x: x[1], reverse=True))}\n"
                    analysis_result += f"- 議論の活発度: {'高' if len(speech_logs) > 20 else '中' if len(speech_logs) > 10 else '低'}\n"
                    
                    # 最新の議論傾向
                    recent_contents = [log['content'] for log in speech_logs[-10:] if log['content']]
                    if recent_contents:
                        analysis_result += f"- 最新の議論傾向: {self._analyze_recent_discussion(recent_contents, analysis_focus)}"
                
                return analysis_result
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"[ERROR] Speech history analysis failed: {e}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")
            return f"発言履歴取得エラー: データベース接続またはクエリに失敗しました。({str(e)})"
    
    def _analyze_speech_patterns(self, speeches: List[str], focus: str) -> str:
        """発言パターンを分析（簡易版）"""
        if not speeches:
            return "発言がありません"
        
        # キーワード分析
        suspicious_words = ['疑わしい', '怪しい', '人狼', '偽', '嘘']
        defensive_words = ['信じる', '擁護', '確実', '真']
        aggressive_words = ['投票', '処刑', '告発', '確信']
        
        suspicious_count = sum(any(word in speech for word in suspicious_words) for speech in speeches)
        defensive_count = sum(any(word in speech for word in defensive_words) for speech in speeches)
        aggressive_count = sum(any(word in speech for word in aggressive_words) for speech in speeches)
        
        if suspicious_count > defensive_count and suspicious_count > aggressive_count:
            return "疑惑提起型（他プレイヤーへの疑念を多く表明）"
        elif defensive_count > aggressive_count:
            return "擁護型（信頼関係を重視する発言が多い）"
        elif aggressive_count > 0:
            return "積極型（投票や告発に関する発言が多い）"
        else:
            return "情報収集型（質問や分析中心の発言）"
    
    def _compare_speech_periods(self, early_speeches: List[str], late_speeches: List[str]) -> str:
        """時期による発言の変化を分析"""
        early_avg_length = sum(len(s) for s in early_speeches) / len(early_speeches) if early_speeches else 0
        late_avg_length = sum(len(s) for s in late_speeches) / len(late_speeches) if late_speeches else 0
        
        if late_avg_length > early_avg_length * 1.5:
            return "発言が詳細化（後半でより長く具体的な発言）"
        elif late_avg_length < early_avg_length * 0.7:
            return "発言が簡潔化（後半で短く要点を絞った発言）"
        else:
            return "発言スタイルは一貫している"
    
    def _analyze_recent_discussion(self, recent_contents: List[str], focus: str) -> str:
        """最近の議論傾向を分析"""
        if not recent_contents:
            return "最近の発言がありません"
        
        # フォーカスに応じた分析
        if "役職示唆" in focus:
            role_keywords = ['占い師', 'ボディガード', '村人', '人狼', 'カミングアウト', 'CO']
            role_mentions = sum(any(word in content for word in role_keywords) for content in recent_contents)
            return f"役職関連の発言が{role_mentions}件（活発な役職議論）" if role_mentions > 2 else "役職議論は控えめ"
        
        elif "投票理由" in focus:
            vote_keywords = ['投票', '処刑', '吊り', '理由']
            vote_mentions = sum(any(word in content for word in vote_keywords) for content in recent_contents)
            return f"投票関連の発言が{vote_mentions}件（投票戦略が活発）" if vote_mentions > 1 else "投票戦略の議論は少ない"
        
        else:
            return f"活発な議論（最近{len(recent_contents)}件の発言）"
    
    def _build_role_specific_rules(self, role: str) -> str:
        """役職別の戦略ルールを生成"""
        
        # 全役職共通の必須投票ルール
        mandatory_voting_rule = """
🚨【全役職共通・最優先ルール】🚨
**3ラウンド後必須投票システム**
- ラウンド3（最終発言）では必ず投票先を決定してください
- 「まだ迷っている」「もう少し考えたい」などの先延ばし発言は禁止
- 必ず「○○さんに投票します」と明確に投票意思を表明してください
- 投票フェーズでは議論時間はありません - 迅速に投票してください
"""
        
        if role == 'werewolf':
            return mandatory_voting_rule + """
🐺 人狼専用戦略ルール:
1. 絶対に自分が人狼であることを明かしてはいけません
2. 村人として振る舞い、他の人狼も庇わないでください
3. 占い師や重要な村人役職を見つけて処刑に誘導してください
4. 疑いをそらすため、積極的に他プレイヤーを疑ってください
5. 夜のアクションでは村人陣営を狙ってください
6. カミングアウトは偽役職のみ行い、真の人狼であることは隠し通してください
7. **ラウンド3では村人を処刑候補として迅速に決定してください**
"""
        elif role == 'seer':
            return mandatory_voting_rule + """
🔮 占い師専用戦略ルール:
1. 占い結果を活用して人狼を見つけてください
2. カミングアウトのタイミングを慎重に選んでください
3. 偽占い師（人狼が騙っている場合）に対抗してください
4. 占い結果を根拠に論理的な推理を展開してください
5. 人狼に狙われないよう、時には控えめに行動してください
6. **ラウンド3では占い結果に基づいて人狼候補を迅速に決定してください**
"""
        elif role == 'bodyguard':
            return mandatory_voting_rule + """
🛡️ ボディガード専用戦略ルール:
1. 重要な村人（特に占い師）を守ってください
2. 護衛成功の場合は適切なタイミングでカミングアウトしてください
3. 人狼の襲撃パターンを分析してください
4. 村人として信頼を築いてください
5. **ラウンド3では護衛対象を守るため人狼候補を迅速に決定してください**
"""
        elif role == 'madman':
            return mandatory_voting_rule + """
🎭 狂人専用戦略ルール:
1. 人狼陣営として行動しますが、人狼が誰かは知りません
2. 偽の占い師としてカミングアウトし、村人を混乱させてください
3. 真の占い師の信憑性を下げるため対抗してください
4. 村人陣営を疑心暗鬼に陥れて人狼を有利にしてください
5. 自分が処刑されても構いません（人狼陣営の勝利が目標）
6. **ラウンド3では村人陣営に不利になる投票を迅速に決定してください**
"""
        else:  # villager
            return mandatory_voting_rule + """
👤 村人専用戦略ルール:
1. 情報収集と論理的推理に集中してください
2. 役職者（占い師等）を保護してください
3. 人狼を見つけるため積極的に議論に参加してください
4. 怪しい行動や発言矛盾を指摘してください
5. 村人陣営の勝利のため協力してください
6. **ラウンド3では収集した情報に基づいて人狼候補を迅速に決定してください**
"""

    def generate_speech(self, player_info: Dict, game_context: Dict, recent_messages: List[Dict]) -> str:
        """【高速化版】Function Callingを全面的に採用した発言生成"""
        print(f"[DEBUG] RootAgent.generate_speech (v2) called for {player_info.get('name', 'unknown')}")
        
        # 緊急フォールバックモードかチェック
        if getattr(self, 'fallback_mode', False) or self.model is None:
            print("[ERROR] AI model not available, using emergency fallback.")
            return self._handle_speech_generation_failure(player_info, Exception("AI model not available"))
        
        try:
            # コンテキストを構築
            context = self._build_context(player_info, game_context, recent_messages)
            
            # ツール使用を促すプロンプトを構築
            tool_prompt = self._build_tool_enhanced_prompt(player_info, game_context, context, recent_messages)
            
            print("[DEBUG] Attempting tool-enhanced speech generation (Function Calling)")
            # AIモデルにツール使用を含めて発言生成を依頼（タイムアウトを45秒に延長）
            response = generate_content_with_timeout(self.model, tool_prompt, timeout_seconds=45)
            
            # レスポンスを処理（ツール呼び出しを含む）
            final_speech = self._process_response_with_tools(response, player_info, game_context)
            
            print(f"[DEBUG] Tool-enhanced speech generated: {final_speech[:100]}...")
            return final_speech
            
        except (TimeoutError, Exception) as e:
            # タイムアウトやその他のエラー時のフォールバック
            if isinstance(e, TimeoutError):
                print(f"[WARNING] Tool-enhanced speech generation timed out after 45 seconds: {e}")
            else:
                print(f"[ERROR] Tool-enhanced speech generation failed: {e}")
            
            # 失敗した場合は、よりシンプルなフォールバック発言を生成
            print(f"[DEBUG] Falling back to simple speech generation for {player_info.get('name', 'unknown player')}")
            return self._generate_simple_fallback_speech(player_info, game_context)

    def _handle_speech_generation_failure(self, player_info: Dict, error: Exception) -> str:
        """発言生成失敗時の適切な処理"""
        player_name = player_info.get('name', 'AIプレイヤー')
        
        # ログに詳細なエラー情報を記録
        print(f"[CRITICAL] Speech generation failed for {player_name}: {error}")
        import traceback
        print(f"[CRITICAL] Full traceback: {traceback.format_exc()}")
        
        # システムエラーメッセージではなく、適切なゲーム内発言を返す
        fallback_speeches = [
            "少し考えさせてください。",
            "状況を整理しています。",
            "慎重に判断したいと思います。",
            "もう少し様子を見ます。",
            "皆さんの意見を聞かせてください。"
        ]
        
        # プレイヤー名に基づいて一貫性のある発言を選択
        import hashlib
        seed = int(hashlib.md5(player_name.encode()).hexdigest()[:8], 16)
        import random
        random.seed(seed)
        
        selected_speech = random.choice(fallback_speeches)
        print(f"[DEBUG] Using fallback speech for {player_name}: {selected_speech}")
        return selected_speech

    def _emergency_fallback_speech(self, player_info: Dict) -> str:
        """緊急時フォールバック発言（AIモデルを使わない）
        
        注意: この関数は廃止予定です。
        新しいエラーハンドリングにより、この定型文ベースのフォールバックは使用されません。
        _handle_speech_generation_failure()を使用してください。
        """
        # ペルソナ情報を取得
        persona = player_info.get('persona', {})
        speech_style = ""
        
        if isinstance(persona, dict):
            speech_style = persona.get('speech_style', '')
        elif isinstance(persona, str):
            if '話し方:' in persona:
                try:
                    speech_style = persona.split('話し方:')[1].split('。')[0].strip()
                except:
                    speech_style = ""
        
        # ペルソナに基づいたフォールバック発言を生成
        # 注意: 実際のキャラクターのペルソナを反映させたフォールバック発言を使用
        if speech_style and ('侍' in speech_style or '武士' in speech_style):
            fallback_speeches = [
                "少し考えさせてくだされ。",
                "状況を整理している途中じゃ。",
                "もう少し様子を見申す。",
                "慎重に判断したいと思う。",
                "皆の意見を聞かせてくだされ。"
            ]
        elif speech_style and ('関西' in speech_style or '大阪' in speech_style):
            fallback_speeches = [
                "少し考えさせてください。",
                "状況を整理している途中です。",
                "もう少し様子を見ます。",
                "慎重に判断したいと思います。",
                "皆の意見を聞かせてください。"
            ]
        elif speech_style and 'ナリ' in speech_style:
            fallback_speeches = [
                "少し考えさせてください。",
                "状況を整理している途中です。",
                "もう少し様子を見ます。",
                "慎重に判断したいと思います。",
                "皆の意見を聞かせてください。"
            ]
        elif speech_style and 'だよ' in speech_style:
            fallback_speeches = [
                "少し考えさせてください。",
                "状況を整理している最中です。",
                "もう少し様子を見ます。",
                "慎重に判断したいと思います。",
                "皆の意見を聞かせてください。"
            ]
        else:
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
        # ペルソナ情報の抽出と強化
        persona = player_info.get('persona', {})
        persona_info = ""
        
        # 🔍 ペルソナ処理デバッグログ追加
        print(f"[DEBUG] _build_tool_enhanced_prompt: Processing persona for {player_info.get('name')}")
        print(f"[DEBUG] Persona type: {type(persona)}")
        print(f"[DEBUG] Persona content: {persona}")
        
        if persona:
            if isinstance(persona, str):
                # 🔧 文字列形式のペルソナ処理を強化
                persona_info = f"""# あなたの詳細なペルソナ設定
{persona}

【🚨 絶対厳守】キャラクター維持命令:
上記のペルソナ設定に記載された話し方、語尾、口調、方言、キャッチフレーズなどの全ての特徴を100%完璧に維持して発言してください。
設定されたキャラクターの個性を完全に反映してください。
他のキャラクターの口調や設定を絶対に使用してはいけません。
"""
                print(f"[DEBUG] Using string persona for {player_info.get('name')}")
                
            elif isinstance(persona, dict):
                # 🔧 辞書形式のペルソナ処理を強化
                speech_style = persona.get('speech_style', '普通の話し方')
                personality = persona.get('personality', '不明')
                background = persona.get('background', '不明')
                
                persona_info = f"""# あなたの詳細なペルソナ設定
- 年齢: {persona.get('age', '不明')}歳
- 性別: {persona.get('gender', '不明')}
- 性格: {personality}
- 話し方: {speech_style}
- 背景: {background}

【🚨 絶対厳守】キャラクター維持命令:
{speech_style}で一貫して発言してください。
語尾や口調、方言、キャッチフレーズなどの特徴を必ず維持してください。
他のキャラクターの口調や語尾を絶対に使用してはいけません。
あなたの性格「{personality}」に合った発言をしてください。
"""
                print(f"[DEBUG] Using dict persona for {player_info.get('name')}: speech_style={speech_style}")
                
            else:
                persona_info = f"# あなたの名前: {player_info.get('name', '不明')}\n"
                print(f"[DEBUG] Using default persona for {player_info.get('name')}")
        else:
            persona_info = f"# あなたの名前: {player_info.get('name', '不明')}\n"
            print(f"[DEBUG] No persona provided for {player_info.get('name')}")
        
        # 他のプレイヤー情報を抽出
        other_players = [p['name'] for p in game_context.get('all_players', []) 
                        if p['name'] != player_info.get('name') and p['is_alive']]
        
        # 🔧 プロンプトサイズ制限（Vertex AI API制限対応）
        base_prompt = f"""あなたは人狼ゲームの熟練プレイヤーです。以下のルールを理解し、最適な発言を行ってください。

{persona_info}

# あなたの基本情報
- 名前: {player_info.get('name', '不明')}
- 役職: {player_info.get('role', '不明')} (※秘密情報)
- 陣営: {'人狼' if player_info.get('role') == 'werewolf' else '村人'}

【🚨 絶対遵守ルール 🚨】
🔥 **役職理解**: あなたの真の役職は「{player_info.get('role', '不明')}」です。
- この役職が持つ本来の能力を理解してください
- 戦術として他の役職を騙ることは可能ですが、真の役職を忘れてはいけません
- 人狼の場合は村人として振る舞い、時には偽の占い師や他の役職を騙っても構いません

{self._build_role_specific_rules(player_info.get('role'))}

## 🚨 必須ルール（絶対遵守）
1. **ターン制の理解**: 現在のターンが自分の順番になったときのみ発言する
2. **1ラウンド1発言制**: 各ラウンドで1回のみ発言し、追加発言は絶対にしない
3. **3ラウンド完全実行**: 必ず3ラウンド全て参加し、各ラウンドで戦略的発言を行う
4. **必須投票実行**: 3ラウンド終了後は必ず誰かに投票し、投票を回避・先延ばししない
5. **存在しない情報の禁止**: プレイヤープロフィールや未発言内容を発言として言及しない

## 発言原則
1. **自己紹介・挨拶禁止**: ゲーム開始後は推理のみ
2. **即座の推理展開**: 他プレイヤーの行動から論理的推理
3. **具体的な根拠提示**: 「○○さんの発言が人狼らしい理由は〜」
4. **明確な投票意図**: ラウンド3では「○○さんに投票する」と明言
5. **攻撃的推理**: 疑わしいプレイヤーを積極的に告発

## 戦略的発言パターン
- 「○○さんの発言には矛盾があります」
- 「○○さんを人狼と断定します」  
- 「○○さんに投票します」

## 絶対禁止の表現
- 「よろしく」「はじめまして」（挨拶系）
- 「様子を見ましょう」「もう少し考えて」（先延ばし系）
- 「迷っています」「判断が難しい」（優柔不断系）

# ゲーム状況
{self._truncate_context(context, 800)}

# 生存プレイヤー: {', '.join(other_players[:5])}  

【🚨 重要制限 🚨】
🚫 **存在しない発言への言及絶対禁止**:
- まだ発言していないプレイヤーの発言を引用してはいけません
- 実際にゲーム内で発言された内容のみを根拠に使用してください
- プロフィール情報を「発言」として言及することを禁止します
- 「○○さんが言った」と言及する場合は、実際の発言ログを確認してください

🔒 **役職情報の秘匿**:
- 自分の真の役職（特に人狼）は絶対に秘密にしてください
- 他のプレイヤーの役職を知っているかのような発言は禁止です

発言は500文字以内で、ゲーム進行に貢献する内容にしてください。
"""
        
        # 🔧 プロンプト長さをチェックして制限
        if len(base_prompt) > 8000:  # 8000文字制限
            print(f"[WARNING] Prompt too long ({len(base_prompt)} chars), truncating...")
            base_prompt = base_prompt[:7800] + "\n\n発言は500文字以内で、ゲーム進行に貢献する内容にしてください。"
        
        return base_prompt

    def _truncate_context(self, context: str, max_length: int) -> str:
        """コンテキストを指定した長さに切り詰める"""
        if len(context) <= max_length:
            return context
        
        # 重要な情報を保持しながら切り詰め
        lines = context.split('\n')
        result_lines = []
        current_length = 0
        
        for line in lines:
            if current_length + len(line) + 1 <= max_length:
                result_lines.append(line)
                current_length += len(line) + 1
            else:
                break
        
        if len(result_lines) < len(lines):
            result_lines.append("... (情報が制限されています)")
        
        return '\n'.join(result_lines)

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
                            
                            tool_result = self.execute_tool_function(function_name, args)
                            tool_results.append(tool_result)
                            
                        elif hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    
                    # ツール結果がある場合は、それを踏まえて最終発言を生成
                    if tool_results:
                        final_prompt = self._build_final_speech_prompt(
                            player_info, game_context, tool_results, text_parts
                        )
                        # ツールなしモデルで最終発言を生成（タイムアウト付き）
                        simple_model = GenerativeModel("gemini-1.5-flash")
                        final_response = generate_content_with_timeout(simple_model, final_prompt, timeout_seconds=25)
                        return self._clean_speech_content(final_response.text.strip())
                    
                    # ツール呼び出しがない場合は通常のテキストを返す
                    elif text_parts:
                        return self._clean_speech_content(" ".join(text_parts).strip())
            
            # フォールバック: response.textを使用
            if hasattr(response, 'text') and response.text:
                return self._clean_speech_content(response.text.strip())
                
            return "少し考えさせてください。"
            
        except Exception as e:
            print(f"[ERROR] Error processing response with tools: {e}")
            return "状況を整理して考えてみます。"

    def _build_final_speech_prompt(self, player_info: Dict, game_context: Dict, tool_results: List[str], text_parts: List[str]) -> str:
        """ツール結果を踏まえた最終発言生成プロンプト"""
        persona = player_info.get('persona', '')
        
        if isinstance(persona, str) and persona:
            persona_info = f"""# ペルソナ設定
{persona}

【最重要】キャラクター維持指示:
上記ペルソナの話し方、語尾、口調、方言、キャッチフレーズなどの全ての特徴を100%維持してください。
"""
        elif isinstance(persona, dict):
            speech_style = persona.get('speech_style', '普通の話し方')
            persona_info = f"""# ペルソナ設定
話し方: {speech_style}
性格: {persona.get('personality', '普通')}

【最重要】キャラクター維持指示:
{speech_style}で一貫して発言してください。語尾や口調、方言を必ず維持してください。
"""
        else:
            persona_info = ""
        
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

    
    
    def _generate_simple_fallback_speech(self, player_info: Dict, game_context: Dict) -> str:
        """最終フォールバック発言生成（ペルソナ対応）"""
        role = player_info.get('role', 'villager')
        day_number = game_context.get('day_number', 1)
        
        # ペルソナ情報を取得
        persona = player_info.get('persona', {})
        speech_style = ""
        
        if isinstance(persona, dict):
            speech_style = persona.get('speech_style', '')
        elif isinstance(persona, str):
            if '話し方:' in persona:
                try:
                    speech_style = persona.split('話し方:')[1].split('。')[0].strip()
                except:
                    speech_style = ""
        
        # ペルソナ別のフォールバック発言を生成
        # 注意: プレイヤーの実際のペルソナを確認してからフォールバック発言を選択
        if speech_style and ('侍' in speech_style or '武士' in speech_style):
            fallback_speeches = {
                'villager': [
                    "情報を整理して冷静に判断いたす。",
                    "疑わしい点があれば聞かせてくだされ。",
                    "皆で協力して真実を見つけませぬか。"
                ],
                'werewolf': [
                    "慎重に考えたいと思う。",
                    "皆の意見を聞かせてくだされ。",
                    "状況を整理してみよう。"
                ]
            }
        elif speech_style and ('関西' in speech_style or '大阪' in speech_style):
            fallback_speeches = {
                'villager': [
                    "情報を整理して冷静に判断します。",
                    "疑わしい点があれば教えてください。",
                    "皆で協力して真実を見つけましょう。"
                ],
                'werewolf': [
                    "慎重に考えたいと思います。",
                    "皆の意見を聞かせてください。",
                    "状況を整理してみます。"
                ]
            }
        elif speech_style and 'ナリ' in speech_style:
            fallback_speeches = {
                'villager': [
                    "情報を整理して冷静に判断します。",
                    "疑わしい点があれば教えてください。",
                    "皆で協力して真実を見つけましょう。"
                ],
                'werewolf': [
                    "慎重に考えたいと思います。",
                    "皆の意見を聞かせてください。",
                    "状況を整理してみます。"
                ]
            }
        elif speech_style and 'だよ' in speech_style:
            fallback_speeches = {
                'villager': [
                    "情報を整理して冷静に判断します。",
                    "疑わしい点があれば教えてください。",
                    "皆で協力して真実を見つけましょう。"
                ],
                'werewolf': [
                    "慎重に考えたいと思います。",
                    "皆の意見を聞かせてください。",
                    "状況を整理してみます。"
                ]
            }
        else:
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
        
        speeches = fallback_speeches.get(role, fallback_speeches.get('villager', fallback_speeches['villager']))
        return random.choice(speeches)
    
    def _build_context(self, player_info: Dict, game_context: Dict, recent_messages: List[Dict]) -> str:
        """エージェントに渡すコンテキストを構築（Phase 4: サマリー+自身の発言を優先）"""
        context_parts = []
        
        # ゲーム状況
        context_parts.append(f"現在{game_context.get('day_number', 1)}日目の{game_context.get('phase', '昼')}フェーズです。")
        context_parts.append(f"生存プレイヤー数: {game_context.get('alive_count', '不明')}人")
        
        # Phase 4 実装: サマリー+自身の発言をデフォルトインプットに変更
        room_id = game_context.get('room_id')
        player_name = player_info.get('name')
        
        if room_id and player_name:
            # ゲームサマリーを取得（優先）- 緊急修正：タイムアウト付き
            try:
                from game_logic.main import SessionLocal, get_latest_game_summary
                import asyncio
                from concurrent.futures import ThreadPoolExecutor, TimeoutError
                
                def get_summary_with_timeout():
                    db = SessionLocal()
                    try:
                        # 🔧 厳格なroom_id検証
                        if not room_id:
                            print(f"[ERROR] Missing room_id for summary fetch")
                            return None
                            
                        try:
                            room_uuid = uuid.UUID(room_id)
                        except (ValueError, TypeError) as e:
                            print(f"[ERROR] Invalid room_id format: {room_id}, error: {e}")
                            return None
                        
                        # 🔧 room存在確認
                        from game_logic.main import get_room
                        room_exists = get_room(db, room_uuid)
                        if not room_exists:
                            print(f"[ERROR] Room not found: {room_id}")
                            return None
                        
                        summary = get_latest_game_summary(
                            db=db,
                            room_id=room_uuid,
                            day_number=game_context.get('day_number'),
                            phase=game_context.get('phase')
                        )
                        
                        # 🔧 サマリーのroom_id検証
                        if summary and summary.get('room_id') != room_id:
                            print(f"[ERROR] Summary room_id mismatch: expected {room_id}, got {summary.get('room_id')}")
                            return None
                            
                        return summary
                    finally:
                        db.close()
                
                # 🔧 改善: より短いタイムアウトで確実な動作
                try:
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(get_summary_with_timeout)
                        summary = future.result(timeout=10)  # 10秒でタイムアウト（短縮）
                except TimeoutError:
                    print(f"[WARNING] Summary fetch timed out for room {room_id}")
                    summary = None
                except Exception as db_error:
                    print(f"[WARNING] Summary fetch failed: {db_error}")
                    summary = None
                
                if summary:
                    context_parts.append("# ゲーム進行サマリー")
                    context_parts.append(f"- {summary['summary_content']}")
                    
                    if summary.get('important_events'):
                        events = summary['important_events']
                        if isinstance(events, list) and events:
                            context_parts.append(f"- 重要イベント: {', '.join(events[:3])}")  # 最新3件
                    
                    if summary.get('player_suspicions'):
                        suspicions = summary['player_suspicions']
                        if isinstance(suspicions, dict) and suspicions:
                            top_suspects = sorted(suspicions.items(), key=lambda x: x[1], reverse=True)[:2]
                            context_parts.append(f"- 疑惑度: {', '.join([f'{k}({v}%)' for k, v in top_suspects])}")
                else:
                    # サマリー取得失敗時は基本情報のみ使用
                    context_parts.append("# ゲーム進行サマリー")
                    if game_context.get('day_number', 1) == 1:
                        context_parts.append("- 1日目開始：全員が初対面、情報収集の段階")
                    else:
                        context_parts.append("- 前日の情報は直接の発言ログを参照してください")
                        
            except Exception as e:
                print(f"[WARNING] Failed to get game summary: {e}")
                # サマリー機能完全失敗時もゲーム続行
                context_parts.append("# ゲーム進行サマリー")
                context_parts.append("- 基本情報のみで進行中（サマリー機能一時停止）")
            
            # 自身の発言履歴を取得（重要）
            try:
                from game_logic.main import SessionLocal, Player, get_player_own_speeches
                
                db = SessionLocal()
                try:
                    # 🔧 厳格な検証
                    if not room_id or not player_name:
                        print(f"[ERROR] Missing room_id or player_name for speech history")
                        context_parts.append(f"# {player_name or 'unknown'}の過去の発言")
                        context_parts.append("- 発言履歴取得失敗（パラメータエラー）")
                        return "\n".join(context_parts)
                    
                    try:
                        room_uuid = uuid.UUID(room_id)
                    except (ValueError, TypeError) as e:
                        print(f"[ERROR] Invalid room_id format for speech history: {room_id}, error: {e}")
                        context_parts.append(f"# {player_name}の過去の発言")
                        context_parts.append("- 発言履歴取得失敗（ID形式エラー）")
                        return "\n".join(context_parts)
                    
                    # プレイヤー名からIDを取得（厳格に現在のroom内のプレイヤーのみ）
                    from game_logic.main import get_room
                    room = get_room(db, room_uuid)
                    if not room:
                        print(f"[ERROR] Room not found for speech history: {room_id}")
                        context_parts.append(f"# {player_name}の過去の発言")
                        context_parts.append("- 発言履歴取得失敗（部屋が見つかりません）")
                        return "\n".join(context_parts)
                    
                    # 🔧 現在のroom内のプレイヤーに限定
                    player = None
                    for p in room.players:
                        if p.character_name == player_name:
                            player = p
                            break
                    
                    if player:
                        own_speeches = get_player_own_speeches(
                            db=db,
                            room_id=room_uuid,
                            player_id=player.player_id,
                            limit=5  # 最新5件の自分の発言
                        )
                        
                        # 🔧 発言データの検証
                        validated_speeches = []
                        for speech in own_speeches:
                            if speech.get('player_name') == player_name:
                                validated_speeches.append(speech)
                            else:
                                print(f"[WARNING] Speech player name mismatch: expected {player_name}, got {speech.get('player_name')}")
                        
                        if validated_speeches:
                            context_parts.append(f"# {player_name}の過去の発言")
                            for i, speech in enumerate(validated_speeches[-3:], 1):  # 最新3件
                                content = speech['content']
                                if len(content) > 80:
                                    content = content[:80] + "..."
                                context_parts.append(f"- {i}回前: 「{content}」")
                        else:
                            context_parts.append(f"# {player_name}の過去の発言")
                            context_parts.append("- まだ発言がありません（初回発言）")
                    else:
                        context_parts.append(f"# {player_name}の過去の発言")
                        context_parts.append("- プレイヤー情報が見つかりません")
                        
                finally:
                    db.close()
                    
            except Exception as e:
                print(f"[WARNING] Failed to get own speech history: {e}")
                context_parts.append(f"# {player_name}の過去の発言")
                context_parts.append("- 発言履歴取得に失敗（データベース接続エラー）")
        
        # フォールバック: 従来のrecent_messagesも使用（緊急時・補完用）
        if recent_messages:
            context_parts.append("# 最新の議論")
            for msg in recent_messages[-2:]:  # 最新2件に削減（コスト効率化）
                speaker = msg.get('speaker', '不明')
                content = msg.get('content', '')
                if len(content) > 100:  # 長すぎる発言は要約
                    content = content[:100] + "..."
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
1. ペルソナで設定された話し方・口調・語尾を100%完全に維持すること
2. 関西弁や方言は使用禁止（ペルソナで明示的に指定されている場合を除く）
3. 「や」「わ」「やで」「やん」「ねん」「さかい」等の関西弁は絶対に使わない
4. ペルソナの年齢・性格・話し方設定に完全に従うこと
5. 500文字以内で自然な発言をすること

⚠️ 重要: ペルソナに関西弁の指定がない場合は、標準語または設定された口調のみで発言してください。

最終発言:
"""

    def _clean_speech_content(self, speech: str) -> str:
        """AI発言からツール関連の内部情報を除去し、関西弁を標準語に変換"""
        import re
        
        # 基本的な正規表現フィルタリング
        tool_label_patterns = [
            r'質問案:\s*',
            r'告発案:\s*',
            r'支援案:\s*',
            r'カミングアウト案:\s*',
            r'\[.*?結果\]:\s*',
            r'\[DEBUG\].*?$',
            r'\[ERROR\].*?$',
            r'function_name.*?$',
            r'\(`.*?`\)',  # バッククォートで囲まれた関数名
            r'\(.*?関数.*?\)',  # 関数に関する説明
        ]
        
        cleaned_speech = speech
        for pattern in tool_label_patterns:
            cleaned_speech = re.sub(pattern, '', cleaned_speech, flags=re.MULTILINE)
        
        # 🔧 関西弁フィルタリング（強制的に標準語に変換）
        cleaned_speech = self._convert_kansai_to_standard(cleaned_speech)
        
        # LLMを使った追加の整形処理
        cleaned_speech = self._llm_clean_speech(cleaned_speech)
        
        # 複数の空行を単一の空行に変換
        cleaned_speech = re.sub(r'\n\s*\n', '\n', cleaned_speech)
        
        # 先頭と末尾の空白を除去
        cleaned_speech = cleaned_speech.strip()
        
        return cleaned_speech
    
    def _convert_kansai_to_standard(self, speech: str) -> str:
        """関西弁を標準語に強制変換"""
        import re
        
        # 関西弁パターンの辞書（関西弁 -> 標準語）
        kansai_patterns = [
            (r'やで\b', 'です'),
            (r'やん\b', 'じゃないか'),
            (r'ねん\b', 'のです'),
            (r'へん\b', 'ない'),
            (r'おる\b', 'いる'),
            (r'しとる\b', 'している'),
            (r'きとる\b', 'ている'),
            (r'やから\b', 'だから'),
            (r'さかい\b', 'ので'),
            (r'まっせ\b', 'ますよ'),
            (r'でんな\b', 'ですね'),
            (r'どや\b', 'どうですか'),
            (r'ほんま\b', '本当に'),
            (r'なんや\b', 'なんですか'),
            (r'せや\b', 'そうです'),
            (r'わい\b', '私は'),
            (r'あかん\b', 'だめ'),
            (r'ちゃう\b', '違う'),
            (r'おもろい\b', '面白い'),
            (r'めっちゃ\b', 'とても'),
            (r'えらい\b', 'とても'),
            (r'ようけ\b', 'たくさん'),
            (r'かなん\b', '困る'),
            (r'いらう\b', '触る'),
            (r'ほかす\b', '捨てる'),
            (r'なおす\b', '片付ける'),
            (r'だんない\b', '大丈夫'),
            (r'しんどい\b', '疲れた'),
            (r'ぼちぼち\b', 'そろそろ'),
            (r'よう\b', 'よく'),
            (r'やっぱし\b', 'やっぱり'),
            (r'はよ\b', 'はやく'),
            (r'いけず\b', '意地悪'),
            (r'しょーもない\b', 'つまらない'),
            (r'てんごな\b', '変な'),
            (r'でかい\b', '大きい'),
            (r'ちっさい\b', '小さい'),
            (r'ええ\b', 'いい'),
            (r'あかん\b', 'いけない'),
        ]
        
        converted = speech
        for kansai, standard in kansai_patterns:
            converted = re.sub(kansai, standard, converted)
        
        print(f"[DEBUG] Kansai conversion: '{speech}' -> '{converted}'")
        return converted
    
    def _llm_clean_speech(self, speech: str) -> str:
        """LLMを使って発言を自然に整形"""
        try:
            from vertexai.generative_models import GenerativeModel
            
            # 短すぎる発言はそのまま返す
            if len(speech) < 50:
                return speech
            
            # プレイヤーのペルソナ情報を取得（関西弁情報は除去）
            persona_info = ""
            if hasattr(self, 'player') and self.player:
                # 話し方から関西弁関連の記述を除去
                speech_style = getattr(self.player, 'speech_style', '')
                if speech_style and any(kansai_word in speech_style for kansai_word in ['関西', '大阪', 'やで', 'ねん', 'やん']):
                    speech_style = "丁寧で標準的な話し方"
                
                persona_info = f"""
【プレイヤーのペルソナ情報】
- 名前: {getattr(self.player, 'character_name', '不明')}
- 性格: {getattr(self.player, 'personality', '不明')}
- 話し方: {speech_style}
- 背景: {getattr(self.player, 'background', '不明')}
注意: 話し方は標準語の丁寧語で統一してください。
"""
            
            cleaning_prompt = f"""以下のAIプレイヤーの発言から、技術的な説明や内部処理に関する記述を除去し、自然な人狼ゲームの発言に整形してください。

{persona_info}

【除去すべき要素】
- 関数名や技術的な処理の説明
- 括弧内のシステム的な説明
- プログラミングに関する言及
- 分析ツールや処理に関する説明
- 関西弁や方言（「やで」「ねん」「やん」「わい」「せや」「なんや」等）

【保持すべき要素】
- ゲームに関する推理や考察
- 他プレイヤーへの質問や意見
- 自己紹介や性格表現
- 投票や議論に関する発言

【重要な言語指示】
- 必ず標準語（丁寧語）で出力してください
- 関西弁や方言は一切使用しないでください
- 「です」「ます」調の丁寧な話し方にしてください
- キャラクターの性格は保持しつつ、言葉遣いは標準語にしてください

【元の発言】
{speech}

【整形後の発言】
（標準語の丁寧な言葉遣いで、自然で簡潔な人狼ゲームの発言として出力してください。500文字以内。）"""

            simple_model = GenerativeModel("gemini-1.5-flash")
            response = generate_content_with_timeout(simple_model, cleaning_prompt, timeout_seconds=8)
            
            cleaned = response.text.strip()
            
            # 整形結果が元の発言より大幅に短くなった場合は元の発言を使用
            if len(cleaned) < len(speech) * 0.3:
                return speech
                
            return cleaned
            
        except Exception as e:
            print(f"[WARNING] LLM cleaning failed: {e}")
            return speech

# グローバルインスタンス（堅牢版）
print("[INIT] Creating RootAgent instance...")
print(f"[INIT] Vertex AI state: {vertex_ai_initialized}")

try:
    root_agent = RootAgent()
    print(f"✅ [SUCCESS] RootAgent created: model={root_agent.model is not None}, fallback={root_agent.fallback_mode}")
except Exception as e:
    print(f"❌ [ERROR] RootAgent creation failed: {e}")
    # 最小限のフォールバックインスタンスを作成
    class FallbackRootAgent:
        def __init__(self):
            self.model = None
            self.tools_available = False
            self.fallback_mode = True
            
        def generate_speech(self, player_info, game_context, recent_messages):
            fallback_speeches = [
                "少し考えさせてください。",
                "状況を整理しています。",
                "慎重に判断したいと思います。"
            ]
            import random
            return random.choice(fallback_speeches)
    
    root_agent = FallbackRootAgent()
    print("[WARNING] Using minimal fallback RootAgent")
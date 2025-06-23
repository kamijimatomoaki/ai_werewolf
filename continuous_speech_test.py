#!/usr/bin/env python3
"""
AIエージェントの連続発言テスト - 一貫性と意図された動作の確認
"""
import sys
import os
sys.path.append('/home/fullm/tg_app/backend')

from backend.npc_agent.agent import root_agent
import json

class GameScenario:
    """ゲームシナリオのクラス"""
    def __init__(self, name, base_player_info, initial_context):
        self.name = name
        self.base_player_info = base_player_info
        self.current_context = initial_context
        self.message_history = []
        self.ai_speeches = []
        
    def add_message(self, speaker, content):
        """メッセージ履歴に追加"""
        self.message_history.append({
            'speaker': speaker,
            'content': content,
            'timestamp': f'2025-01-01T10:{len(self.message_history):02d}:00'
        })
        
    def update_context(self, updates):
        """ゲームコンテキストを更新"""
        self.current_context.update(updates)
        
    def generate_ai_speech(self):
        """AI発言を生成"""
        try:
            # 最新の状況で発言生成
            speech = root_agent.generate_speech(
                self.base_player_info,
                self.current_context,
                self.message_history[-3:] if len(self.message_history) > 3 else self.message_history
            )
            
            self.ai_speeches.append({
                'turn': len(self.ai_speeches) + 1,
                'speech': speech,
                'context_snapshot': self.current_context.copy(),
                'message_count': len(self.message_history)
            })
            
            # AI発言も履歴に追加
            self.add_message(self.base_player_info['name'], speech)
            
            return speech
            
        except Exception as e:
            error_msg = f"発言生成エラー: {e}"
            self.ai_speeches.append({
                'turn': len(self.ai_speeches) + 1,
                'speech': error_msg,
                'error': True
            })
            return error_msg

def test_consistency_basic():
    """基本的な一貫性テスト"""
    print("=== 基本一貫性テスト ===")
    
    # 論理的なキャラクター設定
    player_info = {
        'name': 'ConsistentAI',
        'role': 'villager',
        'is_alive': True,
        'persona': '冷静で論理的な分析を好む村人。一度決めた方針は簡単に変えない。'
    }
    
    initial_context = {
        'day_number': 1,
        'phase': 'day_discussion',
        'alive_count': 4,
        'total_players': 5,
        'all_players': [
            {'name': 'Player1', 'is_alive': True, 'is_human': True},
            {'name': 'Player2', 'is_alive': True, 'is_human': True},
            {'name': 'Player3', 'is_alive': True, 'is_human': True},
            {'name': 'ConsistentAI', 'is_alive': True, 'is_human': False}
        ]
    }
    
    scenario = GameScenario("基本一貫性", player_info, initial_context)
    
    # ターン1: 初回発言
    print("\n--- ターン1: 初回発言 ---")
    scenario.add_message('Player1', '誰が怪しいと思いますか？')
    speech1 = scenario.generate_ai_speech()
    print(f"発言1: \"{speech1[:100]}...\"")
    
    # ターン2: 同じ質問への反応
    print("\n--- ターン2: 同じ状況での発言 ---")
    scenario.add_message('Player2', 'Player1さんの意見はどうですか？')
    speech2 = scenario.generate_ai_speech()
    print(f"発言2: \"{speech2[:100]}...\"")
    
    # ターン3: 意見の確認
    print("\n--- ターン3: 意見の一貫性確認 ---")
    scenario.add_message('Player3', 'ConsistentAIさんの判断基準を教えてください')
    speech3 = scenario.generate_ai_speech()
    print(f"発言3: \"{speech3[:100]}...\"")
    
    # 一貫性分析
    print("\n--- 一貫性分析 ---")
    speeches = [s['speech'] for s in scenario.ai_speeches if 'error' not in s]
    
    # キーワード分析
    logical_keywords = ['分析', '論理', '根拠', '判断', '冷静']
    keyword_counts = [sum(1 for keyword in logical_keywords if keyword in speech) for speech in speeches]
    
    print(f"論理的キーワード使用回数: {keyword_counts}")
    
    # 矛盾チェック（簡易版）
    contradictions = []
    if len(speeches) >= 2:
        if '怪しい' in speeches[0] and '信頼' in speeches[1]:
            contradictions.append("疑いと信頼の矛盾")
    
    consistency_score = len(speeches) - len(contradictions)
    print(f"一貫性スコア: {consistency_score}/{len(speeches)}")
    print(f"矛盾点: {contradictions if contradictions else 'なし'}")
    
    return consistency_score >= len(speeches) * 0.8

def test_persona_continuity():
    """ペルソナ継続性テスト"""
    print("\n=== ペルソナ継続性テスト ===")
    
    # 特徴的なペルソナ設定
    player_info = {
        'name': 'PoliteAI',
        'role': 'seer',
        'is_alive': True,
        'persona': '非常に礼儀正しく、「〜ですね」「〜でございます」などの敬語を必ず使用する。控えめで謙虚な性格。'
    }
    
    initial_context = {
        'day_number': 2,
        'phase': 'day_discussion',
        'alive_count': 3,
        'total_players': 4
    }
    
    scenario = GameScenario("ペルソナ継続性", player_info, initial_context)
    
    # 複数ターンでペルソナ維持確認
    conversations = [
        ('Player1', 'どう思いますか？'),
        ('Player2', '占い結果を教えてください'),
        ('Player1', 'もっと積極的に発言してください'),
        ('Player2', '最終的な判断をお願いします')
    ]
    
    polite_patterns = ['です', 'ます', 'ございます', 'いたします', 'させていただき']
    polite_scores = []
    
    for i, (speaker, message) in enumerate(conversations, 1):
        print(f"\n--- ターン{i}: {message} ---")
        scenario.add_message(speaker, message)
        speech = scenario.generate_ai_speech()
        
        # 敬語使用度チェック
        polite_count = sum(1 for pattern in polite_patterns if pattern in speech)
        polite_scores.append(polite_count)
        
        print(f"発言{i}: \"{speech[:120]}...\"")
        print(f"敬語使用回数: {polite_count}")
    
    # ペルソナ継続性評価
    avg_polite_score = sum(polite_scores) / len(polite_scores) if polite_scores else 0
    consistency = all(score >= 2 for score in polite_scores)  # 最低2回は敬語使用
    
    print(f"\n--- ペルソナ継続性分析 ---")
    print(f"平均敬語使用回数: {avg_polite_score:.1f}")
    print(f"全ターンでペルソナ維持: {'✅' if consistency else '❌'}")
    
    return consistency

def test_strategic_consistency():
    """戦略一貫性テスト"""
    print("\n=== 戦略一貫性テスト ===")
    
    # 戦略的なキャラクター
    player_info = {
        'name': 'StrategicAI',
        'role': 'werewolf',
        'is_alive': True,
        'persona': '狡猾で戦略的な人狼。村人を装いながら疑いを他に向ける。'
    }
    
    initial_context = {
        'day_number': 2,
        'phase': 'day_discussion',
        'alive_count': 4,
        'total_players': 6
    }
    
    scenario = GameScenario("戦略一貫性", player_info, initial_context)
    
    # 戦略的状況の変化
    strategic_situations = [
        {
            'message': ('Player1', '私は占い師です。StrategicAIは村人でした。'),
            'context_update': {'day_number': 2}
        },
        {
            'message': ('Player2', 'Player1は偽占い師だと思います'),
            'context_update': {'alive_count': 4}
        },
        {
            'message': ('Player3', 'StrategicAIさんはどちらを信じますか？'),
            'context_update': {'phase': 'day_vote'}
        }
    ]
    
    werewolf_strategies = ['村人を装う', '疑いを逸らす', '偽情報を混ぜる', '味方を守る']
    strategy_consistency = []
    
    for i, situation in enumerate(strategic_situations, 1):
        print(f"\n--- ターン{i}: 戦略状況{i} ---")
        
        speaker, message = situation['message']
        scenario.add_message(speaker, message)
        scenario.update_context(situation['context_update'])
        
        speech = scenario.generate_ai_speech()
        
        # 人狼戦略の痕跡チェック
        strategy_indicators = ['村人', '信じ', '疑問', '証拠', '判断']
        strategy_score = sum(1 for indicator in strategy_indicators if indicator in speech)
        strategy_consistency.append(strategy_score)
        
        print(f"発言{i}: \"{speech[:120]}...\"")
        print(f"戦略指標スコア: {strategy_score}")
    
    # 戦略一貫性評価
    avg_strategy_score = sum(strategy_consistency) / len(strategy_consistency)
    is_consistent = all(score >= 1 for score in strategy_consistency)  # 最低1つは戦略要素
    
    print(f"\n--- 戦略一貫性分析 ---")
    print(f"平均戦略スコア: {avg_strategy_score:.1f}")
    print(f"戦略一貫性維持: {'✅' if is_consistent else '❌'}")
    
    return is_consistent

def test_context_adaptation():
    """文脈適応性テスト"""
    print("\n=== 文脈適応性テスト ===")
    
    player_info = {
        'name': 'AdaptiveAI',
        'role': 'villager',
        'is_alive': True,
        'persona': '状況に応じて柔軟に対応する村人。情報収集を重視する。'
    }
    
    initial_context = {
        'day_number': 1,
        'phase': 'day_discussion',
        'alive_count': 5,
        'total_players': 6
    }
    
    scenario = GameScenario("文脈適応性", player_info, initial_context)
    
    # 状況変化シナリオ
    context_changes = [
        {
            'event': '平和な初日',
            'message': ('Player1', 'みなさん、よろしくお願いします'),
            'expected_tone': ['協力', '挨拶', 'よろしく']
        },
        {
            'event': '占い師CO',
            'message': ('Player2', '私は占い師です。Player3は人狼でした！'),
            'expected_tone': ['分析', '検討', '慎重']
        },
        {
            'event': '対立激化',
            'message': ('Player3', 'Player2は嘘つきです！私は村人です！'),
            'expected_tone': ['判断', '証拠', '冷静']
        },
        {
            'event': '投票時間',
            'message': ('GameMaster', '投票時間です'),
            'expected_tone': ['決断', '投票', '理由']
        }
    ]
    
    adaptation_scores = []
    
    for i, change in enumerate(context_changes, 1):
        print(f"\n--- ターン{i}: {change['event']} ---")
        
        speaker, message = change['message']
        scenario.add_message(speaker, message)
        
        # コンテキスト更新
        if i == 4:  # 投票時間
            scenario.update_context({'phase': 'day_vote'})
        
        speech = scenario.generate_ai_speech()
        
        # 期待される反応の確認
        adaptation_score = sum(1 for tone in change['expected_tone'] if tone in speech)
        adaptation_scores.append(adaptation_score)
        
        print(f"発言{i}: \"{speech[:120]}...\"")
        print(f"適応度スコア: {adaptation_score}/{len(change['expected_tone'])}")
    
    # 適応性評価
    total_possible = sum(len(change['expected_tone']) for change in context_changes)
    total_achieved = sum(adaptation_scores)
    adaptation_rate = total_achieved / total_possible if total_possible > 0 else 0
    
    print(f"\n--- 文脈適応性分析 ---")
    print(f"適応率: {adaptation_rate:.2%} ({total_achieved}/{total_possible})")
    print(f"適応性評価: {'✅' if adaptation_rate >= 0.5 else '❌'}")
    
    return adaptation_rate >= 0.5

def main():
    """メインテスト実行"""
    print("=== AIエージェント連続発言テスト ===\n")
    
    # 各テストを実行
    test_results = {
        '基本一貫性': test_consistency_basic(),
        'ペルソナ継続性': test_persona_continuity(),
        '戦略一貫性': test_strategic_consistency(),
        '文脈適応性': test_context_adaptation()
    }
    
    print("\n" + "="*50)
    print("=== 連続発言テスト結果 ===")
    
    for test_name, result in test_results.items():
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    total_success = sum(test_results.values())
    total_tests = len(test_results)
    
    print(f"\n総合結果: {total_success}/{total_tests} テスト成功")
    
    if total_success == total_tests:
        print("🎉 連続発言機能が完璧に動作しています！")
    elif total_success >= total_tests * 0.75:
        print("✅ 連続発言機能は良好に動作しています。")
    elif total_success >= total_tests * 0.5:
        print("⚠️ 連続発言機能に一部問題がありますが、基本機能は動作しています。")
    else:
        print("❌ 連続発言機能に重大な問題があります。")

if __name__ == "__main__":
    main()
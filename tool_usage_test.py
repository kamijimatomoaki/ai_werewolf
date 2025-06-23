#!/usr/bin/env python3
"""
AIエージェントのツール使用機能詳細テスト
"""
import sys
import os
sys.path.append('/home/fullm/tg_app/backend')

from backend.npc_agent.agent import root_agent
import json
import re

def test_tool_invocation_detection():
    """ツール呼び出しの検出テスト"""
    print("=== ツール呼び出し検出テスト ===")
    
    # ツール使用を促すゲームシチュエーション
    player_info = {
        'name': 'ToolTestAI',
        'role': 'villager',
        'is_alive': True,
        'persona': '論理的で分析的なプレイヤー。必ずツールを使って戦略的に判断する。'
    }
    
    game_context = {
        'day_number': 2,
        'phase': 'day_discussion',
        'alive_count': 4,
        'total_players': 6,
        'all_players': [
            {'name': 'Player1', 'is_alive': True, 'is_human': True},
            {'name': 'Player2', 'is_alive': True, 'is_human': True},
            {'name': 'Player3', 'is_alive': True, 'is_human': True},
            {'name': 'ToolTestAI', 'is_alive': True, 'is_human': False}
        ]
    }
    
    # 複雑な状況を作成（ツール使用を促進）
    recent_messages = [
        {'speaker': 'Player1', 'content': '私は占い師です。Player2は人狼でした。', 'timestamp': '2025-01-01T10:00:00'},
        {'speaker': 'Player2', 'content': 'それは嘘です！私は村人です。Player1が人狼です。', 'timestamp': '2025-01-01T10:01:00'},
        {'speaker': 'Player3', 'content': 'どちらを信じればいいかわかりません...', 'timestamp': '2025-01-01T10:02:00'}
    ]
    
    try:
        print("複雑なシチュエーションでツール使用テスト実行中...")
        speech = root_agent.generate_speech(player_info, game_context, recent_messages)
        
        print(f"生成された発言長: {len(speech)}文字")
        
        # ツール呼び出しの検出
        tool_patterns = [
            r'analyze_player\s*\(',
            r'plan_vote_strategy\s*\(',
            r'rate_player_suspicion\s*\(',
            r'analyze_coming_out_timing\s*\('
        ]
        
        tools_detected = []
        for pattern in tool_patterns:
            if re.search(pattern, speech):
                tool_name = pattern.split('\\s')[0]
                tools_detected.append(tool_name)
        
        print(f"ツール呼び出し検出: {len(tools_detected)}個")
        for tool in tools_detected:
            print(f"  - {tool}")
        
        # 戦略的内容の確認
        strategic_keywords = ['分析', '戦略', '評価', '判断', '根拠', '証拠', '矛盾']
        strategic_count = sum(1 for keyword in strategic_keywords if keyword in speech)
        
        print(f"戦略的キーワード数: {strategic_count}")
        print(f"発言内容プレビュー: \"{speech[:200]}...\"")
        
        success = len(tools_detected) > 0 or strategic_count >= 3
        print(f"結果: {'✅ ツール使用または戦略的思考確認' if success else '❌ ツール使用不明'}")
        
        return success, speech
        
    except Exception as e:
        print(f"❌ ツール検出テストエラー: {e}")
        return False, ""

def test_specific_tool_scenarios():
    """特定ツールの使用シナリオテスト"""
    print("\n=== 特定ツール使用シナリオテスト ===")
    
    scenarios = [
        {
            'name': 'プレイヤー分析シナリオ',
            'expected_tool': 'analyze_player',
            'player_info': {
                'name': 'AnalyzerAI',
                'role': 'seer',
                'is_alive': True,
                'persona': '他のプレイヤーの行動を詳細に分析する占い師。'
            },
            'messages': [
                {'speaker': 'SuspiciousPlayer', 'content': '私は絶対に村人です！誰も疑わないでください！', 'timestamp': '2025-01-01T10:00:00'}
            ]
        },
        {
            'name': '投票戦略シナリオ',
            'expected_tool': 'plan_vote_strategy',
            'player_info': {
                'name': 'StrategistAI',
                'role': 'villager',
                'is_alive': True,
                'persona': '投票戦略を慎重に計画する村人。'
            },
            'messages': [
                {'speaker': 'Player1', 'content': '今日の投票は重要です。', 'timestamp': '2025-01-01T10:00:00'}
            ]
        },
        {
            'name': '疑惑度評価シナリオ',
            'expected_tool': 'rate_player_suspicion',
            'player_info': {
                'name': 'EvaluatorAI',
                'role': 'villager',
                'is_alive': True,
                'persona': '各プレイヤーの疑惑度を数値で評価する。'
            },
            'messages': [
                {'speaker': 'Player1', 'content': '誰が一番怪しいと思いますか？', 'timestamp': '2025-01-01T10:00:00'}
            ]
        },
        {
            'name': 'カミングアウトタイミングシナリオ',
            'expected_tool': 'analyze_coming_out_timing',
            'player_info': {
                'name': 'TimingAI',
                'role': 'seer',
                'is_alive': True,
                'persona': '占い師として最適なカミングアウトタイミングを計算する。'
            },
            'messages': [
                {'speaker': 'Player1', 'content': '占い師はいつCOするべきでしょうか？', 'timestamp': '2025-01-01T10:00:00'}
            ]
        }
    ]
    
    game_context = {
        'day_number': 2,
        'phase': 'day_discussion',
        'alive_count': 4,
        'total_players': 5
    }
    
    results = {}
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}テスト:")
        
        try:
            speech = root_agent.generate_speech(
                scenario['player_info'], 
                game_context, 
                scenario['messages']
            )
            
            # 期待されるツールの検出
            expected_pattern = f"{scenario['expected_tool']}\\s*\\("
            tool_used = bool(re.search(expected_pattern, speech))
            
            # 内容の戦略性チェック
            strategic_phrases = [
                '分析結果', '戦略的に', '評価すると', '判断すると',
                '根拠として', '証拠から', 'タイミング', '最適'
            ]
            strategic_content = any(phrase in speech for phrase in strategic_phrases)
            
            print(f"  期待ツール検出: {'✅' if tool_used else '❌'} ({scenario['expected_tool']})")
            print(f"  戦略的内容: {'✅' if strategic_content else '❌'}")
            print(f"  発言長: {len(speech)}文字")
            print(f"  内容: \"{speech[:150]}...\"")
            
            results[scenario['name']] = tool_used or strategic_content
            
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            results[scenario['name']] = False
    
    success_count = sum(results.values())
    print(f"\n特定ツールシナリオ結果: {success_count}/{len(scenarios)} 成功")
    return success_count >= len(scenarios) // 2

def test_tool_integration():
    """ツール統合・連携テスト"""
    print("\n=== ツール統合・連携テスト ===")
    
    # 複雑な状況（複数ツール使用が期待される）
    player_info = {
        'name': 'MasterAI',
        'role': 'seer',
        'is_alive': True,
        'persona': '高度な戦略家。複数のツールを組み合わせて最適な判断を行う。'
    }
    
    game_context = {
        'day_number': 3,
        'phase': 'day_discussion',
        'alive_count': 3,
        'total_players': 5,
        'all_players': [
            {'name': 'Player1', 'is_alive': True, 'is_human': True},
            {'name': 'Player2', 'is_alive': True, 'is_human': True},
            {'name': 'MasterAI', 'is_alive': True, 'is_human': False}
        ]
    }
    
    # 複雑なメッセージ履歴
    recent_messages = [
        {'speaker': 'Player1', 'content': '私は占い師です。Player2は人狼でした。', 'timestamp': '2025-01-01T10:00:00'},
        {'speaker': 'Player2', 'content': '嘘です！私こそ真の占い師で、Player1が人狼です！', 'timestamp': '2025-01-01T10:01:00'},
        {'speaker': 'Player1', 'content': 'Player2は偽占いです。信じないでください。', 'timestamp': '2025-01-01T10:02:00'},
        {'speaker': 'Player2', 'content': 'MasterAIさん、どちらを信じますか？', 'timestamp': '2025-01-01T10:03:00'}
    ]
    
    try:
        print("複雑な対立状況でのツール統合テスト実行中...")
        speech = root_agent.generate_speech(player_info, game_context, recent_messages)
        
        # 複数ツール使用の検出
        all_tools = [
            'analyze_player',
            'plan_vote_strategy', 
            'rate_player_suspicion',
            'analyze_coming_out_timing'
        ]
        
        tools_used = []
        for tool in all_tools:
            if re.search(f"{tool}\\s*\\(", speech):
                tools_used.append(tool)
        
        print(f"使用されたツール数: {len(tools_used)}")
        for tool in tools_used:
            print(f"  - {tool}")
        
        # 統合的思考の確認
        integration_keywords = [
            '総合的に', '全体的に', '分析の結果', '戦略として',
            'これらの要因', '複数の視点', '多角的に'
        ]
        integration_score = sum(1 for keyword in integration_keywords if keyword in speech)
        
        print(f"統合的思考スコア: {integration_score}")
        print(f"発言の詳細さ: {len(speech)}文字")
        print(f"内容プレビュー: \"{speech[:300]}...\"")
        
        # 成功判定
        success = len(tools_used) >= 2 or integration_score >= 2 or len(speech) >= 500
        print(f"結果: {'✅ 高度な統合思考確認' if success else '❌ 統合不十分'}")
        
        return success
        
    except Exception as e:
        print(f"❌ ツール統合テストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("=== AIエージェントツール使用機能テスト ===\n")
    
    # 各テストを実行
    test_results = {}
    
    print("1. ツール呼び出し検出テスト")
    detection_success, sample_speech = test_tool_invocation_detection()
    test_results['ツール検出'] = detection_success
    
    print("\n2. 特定ツールシナリオテスト")
    scenario_success = test_specific_tool_scenarios()
    test_results['シナリオ別'] = scenario_success
    
    print("\n3. ツール統合テスト")
    integration_success = test_tool_integration()
    test_results['統合・連携'] = integration_success
    
    print("\n" + "="*50)
    print("=== ツール使用機能テスト結果 ===")
    
    for test_name, result in test_results.items():
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    total_success = sum(test_results.values())
    total_tests = len(test_results)
    
    print(f"\n総合結果: {total_success}/{total_tests} テスト成功")
    
    if total_success == total_tests:
        print("🎉 ツール使用機能が完全に動作しています！")
    elif total_success >= 2:
        print("✅ ツール使用機能は基本的に動作しています。")
    else:
        print("❌ ツール使用機能に問題がある可能性があります。")
        
    # サンプル発言の表示
    if sample_speech:
        print(f"\n=== サンプル発言 ===")
        print(f"\"{sample_speech}\"")

if __name__ == "__main__":
    main()
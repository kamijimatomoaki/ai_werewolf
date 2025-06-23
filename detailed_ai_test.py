#!/usr/bin/env python3
"""
AIエージェントの詳細テスト - 出力型検証を含む
"""
import sys
import os
sys.path.append('/home/fullm/tg_app/backend')

from backend.npc_agent.agent import root_agent
import json

def test_output_type_validation():
    """出力型の詳細検証"""
    print("=== 出力型検証テスト ===")
    
    # 基本的なテストケース
    player_info = {
        'name': 'TypeTestAI',
        'role': 'villager',
        'is_alive': True,
        'persona': 'テスト用AI。標準的な話し方をします。'
    }
    
    game_context = {
        'day_number': 1,
        'phase': 'day_discussion',
        'alive_count': 4,
        'total_players': 5,
        'all_players': [
            {'name': 'Player1', 'is_alive': True, 'is_human': True},
            {'name': 'Player2', 'is_alive': True, 'is_human': True},
            {'name': 'TypeTestAI', 'is_alive': True, 'is_human': False},
            {'name': 'Player3', 'is_alive': True, 'is_human': True}
        ]
    }
    
    recent_messages = [
        {'speaker': 'Player1', 'content': 'おはようございます', 'timestamp': '2025-01-01T10:00:00'}
    ]
    
    try:
        speech = root_agent.generate_speech(player_info, game_context, recent_messages)
        
        print("1. 基本型チェック:")
        print(f"   - 型: {type(speech)}")
        print(f"   - 文字列か: {isinstance(speech, str)}")
        
        print("2. 内容検証:")
        print(f"   - 空文字列でないか: {speech != ''}")
        print(f"   - 文字数: {len(speech)}")
        print(f"   - 最低文字数（5文字以上）: {len(speech) >= 5}")
        print(f"   - 最大文字数（1000文字以下）: {len(speech) <= 1000}")
        
        print("3. 内容品質チェック:")
        has_newline = '\n' in speech
        print(f"   - 改行を含むか: {has_newline}")
        print(f"   - 特殊文字のみでないか: {speech.strip() != ''}")
        
        print("4. 生成された発言:")
        print(f"   \"{speech}\"")
        
        # 成功判定
        is_valid = (
            isinstance(speech, str) and
            speech != '' and
            len(speech) >= 5 and
            len(speech) <= 1000 and
            speech.strip() != ''
        )
        
        print(f"\n✅ 出力型検証結果: {'成功' if is_valid else '失敗'}")
        return is_valid
        
    except Exception as e:
        print(f"❌ 出力型検証エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_roles():
    """複数の役職での発言生成テスト"""
    print("\n=== 複数役職テスト ===")
    
    roles = ['villager', 'werewolf', 'seer', 'bodyguard']
    results = {}
    
    base_game_context = {
        'day_number': 2,
        'phase': 'day_discussion',
        'alive_count': 3,
        'total_players': 4
    }
    
    recent_messages = [
        {'speaker': 'OtherPlayer', 'content': '今日は誰を疑いますか？', 'timestamp': '2025-01-01T10:00:00'}
    ]
    
    for role in roles:
        print(f"\n{role}での発言生成テスト:")
        
        player_info = {
            'name': f'Test{role.title()}',
            'role': role,
            'is_alive': True,
            'persona': f'{role}の役職を持つテスト用AI。'
        }
        
        try:
            speech = root_agent.generate_speech(player_info, base_game_context, recent_messages)
            
            is_valid = isinstance(speech, str) and len(speech) >= 5 and speech.strip() != ''
            results[role] = is_valid
            
            print(f"   型: {type(speech)}")
            print(f"   文字数: {len(speech)}")
            print(f"   内容: \"{speech[:100]}{'...' if len(speech) > 100 else ''}\"")
            print(f"   結果: {'✅ 成功' if is_valid else '❌ 失敗'}")
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            results[role] = False
    
    success_count = sum(results.values())
    print(f"\n複数役職テスト結果: {success_count}/{len(roles)} 成功")
    return success_count == len(roles)

def test_persona_reflection():
    """ペルソナ反映テスト"""
    print("\n=== ペルソナ反映テスト ===")
    
    # 特徴的なペルソナ設定
    personas = [
        {
            'name': 'PoliteAI',
            'persona': '非常に丁寧で礼儀正しい話し方をします。「～ですね」「～でございます」など敬語を多用します。',
            'expected_keywords': ['です', 'ます', 'ございます']
        },
        {
            'name': 'CasualAI',
            'persona': 'フランクで親しみやすい話し方をします。「だよね」「～じゃん」など関西弁を使います。',
            'expected_keywords': ['だよね', 'じゃん', 'やん']
        }
    ]
    
    game_context = {
        'day_number': 1,
        'phase': 'day_discussion',
        'alive_count': 3
    }
    
    recent_messages = [
        {'speaker': 'Player1', 'content': 'どう思いますか？', 'timestamp': '2025-01-01T10:00:00'}
    ]
    
    persona_results = {}
    
    for persona_data in personas:
        print(f"\n{persona_data['name']}のペルソナテスト:")
        
        player_info = {
            'name': persona_data['name'],
            'role': 'villager',
            'is_alive': True,
            'persona': persona_data['persona']
        }
        
        try:
            speech = root_agent.generate_speech(player_info, game_context, recent_messages)
            
            print(f"   生成発言: \"{speech}\"")
            
            # ペルソナ反映チェック
            speech_lower = speech.lower()
            keyword_found = any(keyword in speech_lower for keyword in persona_data['expected_keywords'])
            
            print(f"   ペルソナ反映: {'✅ 期待されるキーワード発見' if keyword_found else '❌ キーワード未発見'}")
            
            is_valid = isinstance(speech, str) and len(speech) >= 5
            persona_results[persona_data['name']] = is_valid and keyword_found
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            persona_results[persona_data['name']] = False
    
    success_count = sum(persona_results.values())
    print(f"\nペルソナ反映テスト結果: {success_count}/{len(personas)} 成功")
    return success_count > 0  # 少なくとも1つ成功すれば良い

def test_error_handling():
    """エラーハンドリングテスト"""
    print("\n=== エラーハンドリングテスト ===")
    
    # 不正なデータでのテスト
    invalid_cases = [
        {
            'name': 'Empty player info',
            'player_info': {},
            'game_context': {'day_number': 1},
            'recent_messages': []
        },
        {
            'name': 'Missing role',
            'player_info': {'name': 'TestAI'},
            'game_context': {'day_number': 1},
            'recent_messages': []
        },
        {
            'name': 'Invalid game context',
            'player_info': {'name': 'TestAI', 'role': 'villager'},
            'game_context': {},
            'recent_messages': []
        }
    ]
    
    error_handling_results = {}
    
    for case in invalid_cases:
        print(f"\n{case['name']}テスト:")
        
        try:
            speech = root_agent.generate_speech(
                case['player_info'], 
                case['game_context'], 
                case['recent_messages']
            )
            
            # エラーケースでも何らかの発言が生成されるかチェック
            is_valid = isinstance(speech, str) and len(speech) >= 1
            error_handling_results[case['name']] = is_valid
            
            print(f"   結果: {'✅ フォールバック成功' if is_valid else '❌ 完全失敗'}")
            print(f"   発言: \"{speech}\"")
            
        except Exception as e:
            print(f"   ❌ 例外発生: {e}")
            error_handling_results[case['name']] = False
    
    success_count = sum(error_handling_results.values())
    print(f"\nエラーハンドリングテスト結果: {success_count}/{len(invalid_cases)} 成功")
    return success_count >= len(invalid_cases) // 2  # 半分以上成功すれば良い

def main():
    """メインテスト実行"""
    print("=== AIエージェント詳細テスト開始 ===\n")
    
    # 各テストを実行
    test_results = {
        '出力型検証': test_output_type_validation(),
        '複数役職': test_multiple_roles(),
        'ペルソナ反映': test_persona_reflection(),
        'エラーハンドリング': test_error_handling()
    }
    
    print("\n" + "="*50)
    print("=== 最終テスト結果 ===")
    
    for test_name, result in test_results.items():
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    total_success = sum(test_results.values())
    total_tests = len(test_results)
    
    print(f"\n総合結果: {total_success}/{total_tests} テスト成功")
    
    if total_success == total_tests:
        print("🎉 全てのテストが成功しました！AIエージェントは正常に動作しています。")
    elif total_success >= total_tests // 2:
        print("⚠️  一部のテストが失敗しましたが、基本機能は動作しています。")
    else:
        print("❌ 多くのテストが失敗しました。AIエージェントに問題がある可能性があります。")

if __name__ == "__main__":
    main()
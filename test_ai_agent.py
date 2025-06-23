#!/usr/bin/env python3
"""
AIエージェントの発言機能をテストするスクリプト
"""
import sys
import os
sys.path.append('/home/fullm/tg_app/backend')

from backend.npc_agent.agent import root_agent

def test_ai_speech_generation():
    """AI発言生成をテストする"""
    print("=== AIエージェント発言テスト開始 ===")
    
    # テスト用のプレイヤー情報
    player_info = {
        'name': 'テストAI',
        'role': 'villager',
        'is_alive': True,
        'persona': 'テスト用のペルソナです。冷静に分析して判断します。'
    }
    
    # テスト用のゲーム情報
    game_context = {
        'day_number': 1,
        'phase': 'day_discussion',
        'alive_count': 4,
        'total_players': 5,
        'all_players': [
            {'name': 'プレイヤー1', 'is_alive': True, 'is_human': True},
            {'name': 'プレイヤー2', 'is_alive': True, 'is_human': True},
            {'name': 'テストAI', 'is_alive': True, 'is_human': False},
            {'name': 'AI2', 'is_alive': True, 'is_human': False},
            {'name': 'プレイヤー3', 'is_alive': False, 'is_human': True}
        ]
    }
    
    # テスト用の発言履歴
    recent_messages = [
        {'speaker': 'プレイヤー1', 'content': '今日は誰が怪しいと思いますか？', 'timestamp': '2025-01-01T10:00:00'},
        {'speaker': 'プレイヤー2', 'content': 'まだ情報が少ないですね。', 'timestamp': '2025-01-01T10:01:00'}
    ]
    
    try:
        print("1. root_agentの初期化確認...")
        if root_agent is None:
            print("❌ root_agentがNoneです")
            return False
        else:
            print("✅ root_agentが正常に初期化されています")
            
        print(f"2. ツール使用可能性: {getattr(root_agent, 'tools_available', 'Unknown')}")
        
        print("3. AI発言生成テスト実行中...")
        speech = root_agent.generate_speech(player_info, game_context, recent_messages)
        
        print("4. 生成結果の検証...")
        if speech is None:
            print("❌ speechがNoneです")
            return False
        elif speech == "":
            print("❌ speechが空文字です")
            return False
        elif len(speech.strip()) < 5:
            print(f"❌ speechが短すぎます: '{speech}'")
            return False
        else:
            print(f"✅ 正常に発言が生成されました")
            print(f"生成された発言: {speech}")
            print(f"文字数: {len(speech)}")
            return True
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_traditional_speech():
    """従来の発言生成をテストする"""
    print("\n=== 従来発言生成テスト ===")
    
    player_info = {
        'name': 'テストAI2',
        'role': 'werewolf',
        'is_alive': True,
        'persona': 'テスト用ペルソナ2'
    }
    
    game_context = {
        'day_number': 2,
        'phase': 'day_discussion',
        'alive_count': 3
    }
    
    recent_messages = []
    
    try:
        speech = root_agent._generate_traditional_speech(player_info, game_context, recent_messages)
        print(f"従来方式での発言: {speech}")
        return speech is not None and len(speech.strip()) > 5
    except Exception as e:
        print(f"従来方式でもエラー: {e}")
        return False

def test_simple_fallback():
    """最終フォールバックをテストする"""
    print("\n=== 最終フォールバックテスト ===")
    
    player_info = {'role': 'seer'}
    game_context = {'day_number': 1}
    
    try:
        speech = root_agent._generate_simple_fallback_speech(player_info, game_context)
        print(f"フォールバック発言: {speech}")
        return speech is not None and len(speech.strip()) > 5
    except Exception as e:
        print(f"フォールバックでもエラー: {e}")
        return False

if __name__ == "__main__":
    print("AIエージェント発言機能テスト開始\n")
    
    # 各テストを実行
    test1_ok = test_ai_speech_generation()
    test2_ok = test_traditional_speech()
    test3_ok = test_simple_fallback()
    
    print(f"\n=== テスト結果まとめ ===")
    print(f"メイン発言生成: {'✅' if test1_ok else '❌'}")
    print(f"従来発言生成: {'✅' if test2_ok else '❌'}")
    print(f"フォールバック: {'✅' if test3_ok else '❌'}")
    
    if test1_ok or test2_ok or test3_ok:
        print("\n✅ 少なくとも1つの方式で発言生成が成功しています")
    else:
        print("\n❌ 全ての方式で発言生成が失敗しています")
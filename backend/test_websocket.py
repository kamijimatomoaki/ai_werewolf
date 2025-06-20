#!/usr/bin/env python3
"""
WebSocket接続テストスクリプト

このスクリプトはWebSocket接続の改善をテストします：
- 自動再接続機能
- ハートビート機能
- 接続状態の監視
"""

import asyncio
import json
import time
from socketio import AsyncClient

class WebSocketTester:
    def __init__(self, url="http://localhost:8000"):
        self.url = url
        self.sio = AsyncClient()
        self.connected = False
        self.reconnect_count = 0
        
        # イベントハンドラー設定
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('pong', self.on_pong)
        self.sio.on('game_started', self.on_game_started)
        self.sio.on('new_speech', self.on_new_speech)
        self.sio.on('player_joined', self.on_player_joined)
    
    async def on_connect(self):
        print(f"✅ 接続成功! Session ID: {self.sio.sid}")
        self.connected = True
        
        # テスト部屋に参加
        await self.sio.emit('join_room', {'room_id': 'test-room'})
        print("📡 テスト部屋に参加")
    
    async def on_disconnect(self):
        print("❌ 接続が切断されました")
        self.connected = False
        self.reconnect_count += 1
        print(f"🔄 再接続試行回数: {self.reconnect_count}")
    
    async def on_pong(self):
        print("💓 Pongを受信 (ハートビート)")
    
    async def on_game_started(self, data):
        print(f"🎮 ゲーム開始イベント: {data}")
    
    async def on_new_speech(self, data):
        print(f"💬 新しい発言: {data}")
    
    async def on_player_joined(self, data):
        print(f"👤 プレイヤー参加: {data}")
    
    async def connect_test(self):
        """接続テスト"""
        print("🔌 WebSocket接続テストを開始...")
        
        try:
            await self.sio.connect(self.url, transports=['websocket', 'polling'])
            print("✅ 初期接続成功")
            
            # 10秒間接続を維持
            await asyncio.sleep(10)
            
            # ハートビートテスト
            print("💓 ハートビートテスト...")
            for i in range(3):
                await self.sio.emit('ping')
                print(f"📤 Ping送信 {i + 1}/3")
                await asyncio.sleep(2)
            
            print("✅ ハートビートテスト完了")
            
        except Exception as e:
            print(f"❌ 接続エラー: {e}")
        finally:
            if self.connected:
                await self.sio.disconnect()
                print("🔌 接続を切断")
    
    async def reconnect_test(self):
        """再接続テスト（手動）"""
        print("🔄 再接続テストを開始...")
        
        try:
            # 最初の接続
            await self.sio.connect(self.url)
            print("✅ 初期接続成功")
            await asyncio.sleep(2)
            
            # 意図的に切断
            await self.sio.disconnect()
            print("⚠️ 意図的に切断")
            await asyncio.sleep(1)
            
            # 再接続
            await self.sio.connect(self.url)
            print("✅ 再接続成功")
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ 再接続テストエラー: {e}")
        finally:
            if self.connected:
                await self.sio.disconnect()

async def main():
    tester = WebSocketTester()
    
    print("=== WebSocket改善テスト ===")
    print(f"サーバーURL: {tester.url}")
    print()
    
    # 基本接続テスト
    await tester.connect_test()
    await asyncio.sleep(1)
    
    # 再接続テスト
    await tester.reconnect_test()
    
    print("\n=== テスト完了 ===")
    print("フロントエンドでも以下の機能をテストしてください：")
    print("- 自動再接続")
    print("- 接続状態表示")
    print("- 手動再接続ボタン")
    print("- ハートビートによる接続維持")

if __name__ == "__main__":
    asyncio.run(main())
import { test, expect } from '@playwright/test';

test.describe('チャット機能の発言権移行テスト', () => {
  test('発言権が正常に循環し投票フェーズに移行する', async ({ page }) => {
    // 1. アプリケーションにアクセス
    await page.goto('http://localhost:5173');
    
    // 2. 新しいゲームルームを作成（プレイヤー3人、AI1人）
    await page.click('[data-testid="create-room-button"]');
    await page.fill('[data-testid="room-name-input"]', 'テストルーム');
    await page.fill('[data-testid="total-players-input"]', '4');
    await page.fill('[data-testid="human-players-input"]', '3');
    await page.fill('[data-testid="ai-players-input"]', '1');
    await page.click('[data-testid="create-button"]');
    
    // ルーム作成完了を待つ
    await expect(page.locator('[data-testid="room-created"]')).toBeVisible();
    
    // 3. 追加プレイヤーをシミュレート（複数ブラウザコンテキスト）
    const context2 = await page.context().browser()?.newContext();
    const context3 = await page.context().browser()?.newContext();
    
    if (context2 && context3) {
      const page2 = await context2.newPage();
      const page3 = await context3.newPage();
      
      // プレイヤー2が参加
      await page2.goto('http://localhost:5173');
      await page2.click('[data-testid="join-room-button"]');
      await page2.fill('[data-testid="player-name-input"]', 'プレイヤー2');
      await page2.click('[data-testid="join-button"]');
      
      // プレイヤー3が参加
      await page3.goto('http://localhost:5173');
      await page3.click('[data-testid="join-room-button"]');
      await page3.fill('[data-testid="player-name-input"]', 'プレイヤー3');
      await page3.click('[data-testid="join-button"]');
      
      // 4. ゲームを開始
      await page.click('[data-testid="start-game-button"]');
      
      // 5. 議論フェーズまで進める（昼フェーズ開始を待つ）
      await expect(page.locator('[data-testid="phase-indicator"]')).toContainText('議論');
      
      // 6. 最初のプレイヤーで発言
      await expect(page.locator('[data-testid="current-turn-indicator"]')).toContainText('あなたの番です');
      await page.fill('[data-testid="chat-input"]', '最初の発言です');
      await page.click('[data-testid="speak-button"]');
      
      // 7. 次のプレイヤーに発言権が移ることを確認
      await expect(page.locator('[data-testid="current-turn-indicator"]')).not.toContainText('あなたの番です');
      await expect(page2.locator('[data-testid="current-turn-indicator"]')).toContainText('あなたの番です');
      
      // 8. 2番目のプレイヤーで発言
      await page2.fill('[data-testid="chat-input"]', '2番目の発言です');
      await page2.click('[data-testid="speak-button"]');
      
      // 9. 3番目のプレイヤーに発言権が移ることを確認
      await expect(page2.locator('[data-testid="current-turn-indicator"]')).not.toContainText('あなたの番です');
      await expect(page3.locator('[data-testid="current-turn-indicator"]')).toContainText('あなたの番です');
      
      // 10. 3番目のプレイヤーで発言
      await page3.fill('[data-testid="chat-input"]', '3番目の発言です');
      await page3.click('[data-testid="speak-button"]');
      
      // 11. AIプレイヤーが自動で発言することを確認
      await expect(page.locator('[data-testid="chat-log"]')).toContainText('AI');
      
      // 12. 発言権が正常に循環することを確認（複数ラウンド）
      for (let round = 0; round < 2; round++) {
        // プレイヤー1の番
        await expect(page.locator('[data-testid="current-turn-indicator"]')).toContainText('あなたの番です');
        await page.fill('[data-testid="chat-input"]', `ラウンド${round + 2}の発言`);
        await page.click('[data-testid="speak-button"]');
        
        // プレイヤー2の番
        await expect(page2.locator('[data-testid="current-turn-indicator"]')).toContainText('あなたの番です');
        await page2.fill('[data-testid="chat-input"]', `ラウンド${round + 2}の発言`);
        await page2.click('[data-testid="speak-button"]');
        
        // プレイヤー3の番
        await expect(page3.locator('[data-testid="current-turn-indicator"]')).toContainText('あなたの番です');
        await page3.fill('[data-testid="chat-input"]', `ラウンド${round + 2}の発言`);
        await page3.click('[data-testid="speak-button"]');
        
        // AI発言を待つ
        await page.waitForTimeout(2000);
      }
      
      // 13. 規定回数の発言後に投票フェーズに移行することを確認
      await expect(page.locator('[data-testid="phase-indicator"]')).toContainText('投票', { timeout: 10000 });
      await expect(page.locator('[data-testid="voting-panel"]')).toBeVisible();
      
      // クリーンアップ
      await context2.close();
      await context3.close();
    }
  });

  test('発言権スタック問題の検証', async ({ page }) => {
    // バックエンドのスタック問題をテスト
    await page.goto('http://localhost:5173');
    
    // ルーム作成
    await page.click('[data-testid="create-room-button"]');
    await page.fill('[data-testid="room-name-input"]', 'スタックテスト');
    await page.fill('[data-testid="total-players-input"]', '2');
    await page.fill('[data-testid="human-players-input"]', '1');
    await page.fill('[data-testid="ai-players-input"]', '1');
    await page.click('[data-testid="create-button"]');
    
    // ゲーム開始
    await page.click('[data-testid="start-game-button"]');
    await expect(page.locator('[data-testid="phase-indicator"]')).toContainText('議論');
    
    // 人間プレイヤーが発言
    await page.fill('[data-testid="chat-input"]', 'テスト発言');
    await page.click('[data-testid="speak-button"]');
    
    // AIプレイヤーが5秒以内に発言することを確認（スタックしていない）
    await expect(page.locator('[data-testid="chat-log"]')).toContainText('AI', { timeout: 5000 });
    
    // 発言権が再び人間プレイヤーに戻ることを確認
    await expect(page.locator('[data-testid="current-turn-indicator"]')).toContainText('あなたの番です', { timeout: 10000 });
  });

  test('部屋の自動クローズ機能テスト', async ({ page }) => {
    // この部分は手動実行用のテスト
    await page.goto('http://localhost:8000/api/rooms/cleanup', { method: 'POST' });
    
    // レスポンスの確認
    const response = await page.textContent('pre');
    expect(response).toContain('cleaned_rooms');
    expect(response).toContain('threshold');
  });
});
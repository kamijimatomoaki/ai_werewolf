# AI人狼オンライン Phase 2: 機能拡張 設計書

## 📋 概要

Phase 2では、Phase 1で構築した堅牢な基盤を活用して、ゲーム体験を大幅に向上させる新機能を実装します。

**実装期間**: 2-4週間相当  
**目標**: ゲームの戦略性向上と観戦体験の追加  
**前提条件**: Phase 1完了済み

## 🎯 Phase 2 実装目標

### 1. ボディガード機能実装 🛡️
**目標**: 人狼の攻撃から村人を守る役職の追加

#### 実装内容
- **ボディガード役職の追加**
- **夜フェーズでの守り選択UI**
- **攻撃防御ロジック**
- **ゲームバランス調整**

### 2. 観戦者機能実装 👁️
**目標**: ゲーム進行をリアルタイムで観戦できる機能

#### 実装内容
- **観戦者モード**
- **観戦者専用UI**
- **リアルタイム同期**
- **観戦者チャット**

### 3. アニメーション強化 ✨
**目標**: ユーザーエクスペリエンス向上のための視覚効果

#### 実装内容
- **フェーズ遷移アニメーション**
- **カードフリップ効果**
- **スムーズなUI遷移**
- **マイクロインタラクション**

## 🛡️ 1. ボディガード機能詳細設計

### 1.1 役職システム拡張

#### バックエンド変更
```python
# ゲームバランス調整
def get_role_config(player_count: int) -> List[str]:
    configs: Dict[int, List[str]] = {
        5: ['werewolf', 'seer', 'villager', 'villager', 'villager'],
        6: ['werewolf', 'werewolf', 'seer', 'villager', 'villager', 'villager'],
        7: ['werewolf', 'werewolf', 'seer', 'bodyguard', 'villager', 'villager', 'villager'],
        8: ['werewolf', 'werewolf', 'seer', 'bodyguard', 'villager', 'villager', 'villager', 'villager']
    }
    return configs.get(player_count, ['villager'] * player_count)
```

#### 新規API
```python
@app.post("/api/rooms/{room_id}/bodyguard_protect")
async def handle_bodyguard_protect(
    room_id: uuid.UUID,
    protector_id: uuid.UUID,
    protect_data: BodyguardProtectInput,
    db: Session = Depends(get_db)
):
    """ボディガードが指定したプレイヤーを守る"""
```

### 1.2 フロントエンド実装

#### BodyguardPanel コンポーネント
```typescript
interface BodyguardPanelProps {
  roomId: string;
  playerId: string;
  isActive: boolean; // 夜フェーズかつボディガードの場合
  availableTargets: PlayerInfo[];
  onProtect: (targetId: string) => Promise<void>;
}
```

#### useBodyguardProtection カスタムフック
```typescript
interface UseBodyguardProtectionReturn {
  availableTargets: PlayerInfo[];
  protectionResult: BodyguardProtectionResult | null;
  isProtecting: boolean;
  canProtect: boolean;
  protect: (targetId: string) => Promise<void>;
}
```

### 1.3 ゲームロジック

#### 夜のアクション処理拡張
```python
def process_night_actions(db: Session, room_id: uuid.UUID) -> Dict[str, Any]:
    # 1. ボディガードの守り行動を取得
    # 2. 人狼の攻撃対象を決定
    # 3. 守りと攻撃の判定
    # 4. 結果の反映
```

#### 守り判定ロジック
- ボディガードが守ったプレイヤーが攻撃された場合、攻撃を無効化
- ボディガード自身が攻撃された場合は守れない
- 同じプレイヤーを連続で守ることはできない

## 👁️ 2. 観戦者機能詳細設計

### 2.1 観戦者システム

#### データベースモデル拡張
```python
class Spectator(Base):
    __tablename__ = "spectators"
    spectator_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.room_id"), nullable=False)
    spectator_name = Column(String, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
```

#### 観戦者API
```python
@app.post("/api/rooms/{room_id}/spectate")
async def join_as_spectator(
    room_id: uuid.UUID, 
    spectator_name: str, 
    db: Session = Depends(get_db)
):
    """観戦者として部屋に参加"""

@app.get("/api/rooms/{room_id}/spectator_view")
def get_spectator_view(room_id: uuid.UUID, db: Session = Depends(get_db)):
    """観戦者用のゲーム情報を取得"""
```

### 2.2 観戦者UI

#### SpectatorView コンポーネント
```typescript
interface SpectatorViewProps {
  roomId: string;
  spectatorId: string;
  onLeaveSpectator: () => void;
}

// 観戦者には以下が表示される
// - プレイヤー一覧（役職は隠す）
// - 公開されている会話ログ
// - ゲームの進行状況
// - 観戦者チャット
```

#### SpectatorChat コンポーネント
```typescript
interface SpectatorChatProps {
  roomId: string;
  spectatorId: string;
  messages: SpectatorMessage[];
  onSendMessage: (message: string) => Promise<void>;
}
```

### 2.3 権限管理

#### 観戦者の制限
- ゲームに影響を与える行動は不可
- プレイヤーの役職情報は非表示
- 夜のアクションは見えない
- 観戦者同士のチャットのみ可能

## ✨ 3. アニメーション強化詳細設計

### 3.1 フェーズ遷移アニメーション

#### PhaseTransition コンポーネント
```typescript
interface PhaseTransitionProps {
  fromPhase: string;
  toPhase: string;
  onTransitionComplete: () => void;
}

// アニメーション例:
// - 昼→夜: 画面が暗くなるフェードアウト
// - 夜→昼: 太陽が昇るアニメーション
// - 投票→結果: カードめくりエフェクト
```

### 3.2 カードフリップ効果

#### PlayerCard アニメーション
```typescript
// プレイヤーカードのフリップアニメーション
// - 役職公開時
// - プレイヤー脱落時
// - ゲーム終了時の役職一斉公開
```

### 3.3 マイクロインタラクション

#### 実装対象
- ボタンホバー効果
- ローディングアニメーション
- 通知ポップアップ
- スムーズなページ遷移

## 📁 Phase 2 ファイル構成

### 新規作成予定ファイル

```
frontend/src/
├── components/
│   ├── game/
│   │   ├── BodyguardPanel.tsx       # ボディガード専用UI
│   │   ├── SpectatorView.tsx        # 観戦者ビュー
│   │   ├── SpectatorChat.tsx        # 観戦者チャット
│   │   └── PhaseTransition.tsx      # フェーズ遷移アニメーション
│   ├── ui/
│   │   ├── AnimatedCard.tsx         # アニメーション付きカード
│   │   ├── LoadingSpinner.tsx       # 改良版ローディング
│   │   └── NotificationToast.tsx    # 通知システム
│   └── layout/
│       └── SpectatorLayout.tsx      # 観戦者専用レイアウト
├── hooks/
│   ├── useBodyguardProtection.ts    # ボディガード機能
│   ├── useSpectatorMode.ts          # 観戦者機能
│   └── useAnimations.ts             # アニメーション制御
└── animations/
    ├── phaseTransitions.ts          # フェーズ遷移定義
    ├── cardAnimations.ts            # カードアニメーション
    └── uiAnimations.ts              # UI アニメーション
```

### バックエンド拡張

```
backend/
├── game_logic/
│   └── main.py                      # ボディガード API 追加
└── models/
    └── spectator.py                 # 観戦者モデル (main.py に統合予定)
```

## 🔧 実装順序

### Stage 1: ボディガード機能 (Week 1)
1. **バックエンド実装**
   - 役職システム拡張
   - 守りロジック実装
   - API エンドポイント追加

2. **フロントエンド実装**
   - BodyguardPanel コンポーネント
   - useBodyguardProtection フック
   - GameRoom 統合

### Stage 2: 観戦者機能 (Week 2)
1. **データベース設計**
   - Spectator モデル追加
   - 権限管理システム

2. **観戦者UI**
   - SpectatorView コンポーネント
   - SpectatorChat 実装
   - 観戦者専用レイアウト

### Stage 3: アニメーション強化 (Week 3-4)
1. **アニメーションライブラリ選定**
   - Framer Motion or CSS Animations
   - パフォーマンス考慮

2. **段階的実装**
   - フェーズ遷移アニメーション
   - カードフリップ効果
   - マイクロインタラクション

## 🎯 成功指標

### ボディガード機能
- [ ] 7人以上のゲームで正常動作
- [ ] 守り判定ロジックの正確性
- [ ] UI の直感的操作性

### 観戦者機能
- [ ] 複数観戦者の同時接続
- [ ] リアルタイム同期の正確性
- [ ] 観戦者チャットの動作

### アニメーション
- [ ] スムーズな動作 (60fps)
- [ ] モバイル端末での動作
- [ ] アクセシビリティ配慮

## 🔐 セキュリティ考慮事項

### 観戦者機能
- 観戦者はゲーム状態を変更できない
- 役職情報の漏洩防止
- 観戦者チャットの適切な分離

### ボディガード機能
- 守り対象の選択制限
- 不正な API 呼び出し防止
- ゲームバランスの維持

## 📊 パフォーマンス考慮

### アニメーション
- GPU アクセラレーション活用
- アニメーション最適化
- メモリ使用量監視

### 観戦者機能
- WebSocket 接続の効率化
- 不要なデータ送信削減
- スケーラビリティ確保

---

**Phase 2 設計書バージョン**: 1.0  
**作成日**: 2025-06-20  
**次のステップ**: Stage 1 ボディガード機能実装開始
# AI人狼オンライン コンポーネント設計書

## 📋 概要

このドキュメントは、AI人狼オンラインのフロントエンドコンポーネント設計を詳述します。
特にPhase 1での大規模コンポーネント分割と新機能実装のためのアーキテクチャ設計を示します。

## 🏗️ 現在のアーキテクチャ

### 現在の問題点
- **GameRoom.tsx**: 596行の巨大コンポーネント
- **責務の混在**: UI描画、状態管理、ビジネスロジックが混在
- **再利用性の低さ**: 機能が密結合している
- **テスト困難**: 大きすぎてテストが書きにくい

## 🎯 新しいコンポーネント設計

### コンポーネント階層図

```
GameRoom (リファクタリング後)
├── GameHeader
│   ├── RoomInfo
│   ├── GameStatus
│   └── ConnectionStatus
├── PlayerList
│   ├── PlayerCard
│   └── PersonaGenerator
├── GameContent
│   ├── CurrentTurnIndicator
│   ├── SpeechInput
│   ├── VotingPanel
│   ├── NightPhasePanel
│   │   ├── SeerPanel ← 新規実装
│   │   └── WerewolfPanel
│   └── GameControls
└── GameLog
    ├── LogEntry
    └── LogFilter
```

## 🔧 詳細設計

### 1. GameRoom (メインコンポーネント)

**責務**: 全体の状態管理とレイアウト制御
**ファイル**: `/src/components/GameRoom.tsx`

```typescript
interface GameRoomProps {
  roomId: string;
  onBackToLobby: () => void;
}

interface GameRoomState {
  room: RoomInfo | null;
  logs: GameLogInfo[];
  loading: boolean;
  error: string | null;
}
```

**リファクタリング後のサイズ目標**: 150行以下

### 2. PlayerList (プレイヤー一覧)

**責務**: プレイヤー表示とペルソナ管理
**ファイル**: `/src/components/game/PlayerList.tsx`

```typescript
interface PlayerListProps {
  players: PlayerInfo[];
  currentPlayerId?: string;
  gameStatus: string;
  onGeneratePersona: (playerId: string, keywords: string) => Promise<void>;
  onStartGame?: () => Promise<void>;
}
```

**子コンポーネント**:
- `PlayerCard`: 個別プレイヤー情報表示
- `PersonaGenerator`: AIペルソナ生成UI

### 3. GameControls (ゲーム制御)

**責務**: ゲーム進行の制御UI
**ファイル**: `/src/components/game/GameControls.tsx`

```typescript
interface GameControlsProps {
  gameStatus: string;
  isMyTurn: boolean;
  currentPlayer?: PlayerInfo;
  onSpeak: (statement: string) => Promise<void>;
  onTransitionToVote: () => Promise<void>;
  onStartGame?: () => Promise<void>;
}
```

### 4. VotingPanel (投票UI)

**責務**: 投票機能の専用UI
**ファイル**: `/src/components/game/VotingPanel.tsx`

```typescript
interface VotingPanelProps {
  players: PlayerInfo[];
  currentPlayerId: string;
  voteResult?: VoteResult;
  onVote: (targetId: string) => Promise<void>;
}
```

### 5. NightPhasePanel (夜フェーズUI)

**責務**: 夜フェーズの専用UI制御
**ファイル**: `/src/components/game/NightPhasePanel.tsx`

```typescript
interface NightPhasePanelProps {
  roomId: string;
  currentPlayer: PlayerInfo;
  players: PlayerInfo[];
  onNightAction: () => Promise<void>;
}
```

### 6. SeerPanel (占い師UI) ⭐ 新規実装

**責務**: 占い師専用の占い機能UI
**ファイル**: `/src/components/game/SeerPanel.tsx`

```typescript
interface SeerPanelProps {
  roomId: string;
  playerId: string;
  availableTargets: PlayerInfo[];
  isInvestigating: boolean;
  investigationResult?: SeerInvestigateResult;
  onInvestigate: (targetId: string) => Promise<void>;
}

interface SeerInvestigateResult {
  investigator: string;
  target: string;
  result: string; // "人狼" または "村人"
  message: string;
}
```

**実装詳細**:
- 占い対象プレイヤーの選択UI
- 占い結果の表示
- 占い履歴の管理
- アニメーション効果

### 7. GameLog (ログ表示)

**責務**: ゲームログの表示と管理
**ファイル**: `/src/components/game/GameLog.tsx`

```typescript
interface GameLogProps {
  logs: GameLogInfo[];
  autoScroll?: boolean;
  maxHeight?: string;
}
```

**子コンポーネント**:
- `LogEntry`: 個別ログエントリ
- `LogFilter`: ログフィルタリング機能

## 🔄 カスタムフック設計

### 1. useGameState

**責務**: ゲーム状態の管理と同期
**ファイル**: `/src/hooks/useGameState.ts`

```typescript
interface UseGameStateProps {
  roomId: string;
}

interface UseGameStateReturn {
  room: RoomInfo | null;
  logs: GameLogInfo[];
  loading: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
}
```

### 2. useSeerInvestigation ⭐ 新規実装

**責務**: 占い師機能の状態管理
**ファイル**: `/src/hooks/useSeerInvestigation.ts`

```typescript
interface UseSeerInvestigationProps {
  roomId: string;
  playerId: string;
}

interface UseSeerInvestigationReturn {
  availableTargets: PlayerInfo[];
  investigationResult: SeerInvestigateResult | null;
  isInvestigating: boolean;
  canInvestigate: boolean;
  investigate: (targetId: string) => Promise<void>;
  clearResult: () => void;
}
```

### 3. useOfflineDetection ⭐ 新規実装

**責務**: オフライン状態の検知と処理
**ファイル**: `/src/hooks/useOfflineDetection.ts`

```typescript
interface UseOfflineDetectionReturn {
  isOffline: boolean;
  isReconnecting: boolean;
  retryConnection: () => void;
  connectionQuality: 'good' | 'poor' | 'offline';
}
```

## 🎨 UIコンポーネント設計

### 1. ErrorBoundary ⭐ 新規実装

**責務**: エラーの捕捉と表示
**ファイル**: `/src/components/ui/ErrorBoundary.tsx`

```typescript
interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{error: Error}>;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}
```

### 2. OfflineIndicator ⭐ 新規実装

**責務**: オフライン状態の視覚的表示
**ファイル**: `/src/components/ui/OfflineIndicator.tsx`

```typescript
interface OfflineIndicatorProps {
  isOffline: boolean;
  isReconnecting: boolean;
  onRetry?: () => void;
  className?: string;
}
```

### 3. LoadingSpinner ⭐ 新規実装

**責務**: 統一されたローディング表示
**ファイル**: `/src/components/ui/LoadingSpinner.tsx`

```typescript
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  text?: string;
  className?: string;
}
```

## 📡 API サービス拡張

### 新規API メソッド

```typescript
// /src/services/api.ts に追加

class ApiService {
  // 既存メソッド...

  // 占い師機能
  async getAvailableTargets(playerId: string): Promise<{
    available_targets: PlayerInfo[];
    can_investigate: boolean;
  }> {
    // 実装
  }

  async seerInvestigate(
    roomId: string,
    investigatorId: string,
    targetId: string
  ): Promise<SeerInvestigateResult> {
    // 実装
  }

  // ネットワーク状態確認
  async healthCheck(): Promise<{status: string}> {
    // 実装
  }
}
```

## 🧪 テスト戦略

### コンポーネントテスト

各コンポーネントは以下の観点でテストします:

```typescript
// 例: SeerPanel.test.tsx
describe('SeerPanel', () => {
  it('占い対象を選択できる', () => {
    // テスト実装
  });

  it('占い結果が正しく表示される', () => {
    // テスト実装
  });

  it('占い済みの場合は再占いを防ぐ', () => {
    // テスト実装
  });
});
```

### カスタムフックテスト

```typescript
// 例: useSeerInvestigation.test.ts
describe('useSeerInvestigation', () => {
  it('利用可能な対象を正しく取得する', () => {
    // テスト実装
  });

  it('占い機能が正しく動作する', () => {
    // テスト実装
  });
});
```

## 🚀 段階的移行計画

### Step 1: ユーティリティコンポーネント作成
- ErrorBoundary
- OfflineIndicator
- LoadingSpinner

### Step 2: カスタムフック実装
- useGameState
- useSeerInvestigation
- useOfflineDetection

### Step 3: 機能別コンポーネント分割
- PlayerList
- GameControls
- VotingPanel

### Step 4: 新機能実装
- SeerPanel
- NightPhasePanel

### Step 5: メインコンポーネント統合
- GameRoom のリファクタリング
- 統合テスト

## 📊 パフォーマンス考慮事項

### メモ化戦略

```typescript
// React.memo の活用
export const PlayerCard = React.memo<PlayerCardProps>(({player, ...props}) => {
  // 実装
});

// useMemo の活用
const sortedPlayers = useMemo(() => {
  return players.sort((a, b) => a.character_name.localeCompare(b.character_name));
}, [players]);

// useCallback の活用
const handleVote = useCallback((targetId: string) => {
  return onVote(targetId);
}, [onVote]);
```

### 再レンダリング最適化

- 適切な依存配列の設定
- 状態の正規化
- コンポーネントの適切な分割

## 🎯 成功指標

### コード品質
- [ ] 各コンポーネント200行以下
- [ ] 関数50行以下
- [ ] TypeScript strict mode 対応
- [ ] ESLint警告0件

### パフォーマンス
- [ ] 初期レンダリング時間 < 100ms
- [ ] 状態更新時の再レンダリング < 50ms
- [ ] メモリリーク無し

### ユーザビリティ
- [ ] 占い師機能の直感的操作
- [ ] エラー状態の分かりやすい表示
- [ ] オフライン対応の適切な動作

---

**作成日**: 2025-06-20  
**最終更新**: 2025-06-20  
**バージョン**: 1.0.0
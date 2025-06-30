# AI人狼オンライン - システムアーキテクチャ図

## アプリケーション構成図

```mermaid
graph TB
    subgraph "ユーザー層"
        USER1[プレイヤー1<br/>人間ユーザー]
        USER2[プレイヤー2<br/>人間ユーザー]
        USER3[観戦者<br/>リアルタイム視聴]
    end
    
    subgraph "AI人狼オンライン アプリケーション"
        subgraph "フロントエンド (React SPA)"
            GAMEROOM[ゲームルーム画面<br/>GameRoom.tsx]
            ROOMLIST[ルーム一覧画面<br/>RoomList.tsx]
            
            subgraph "ゲームコンポーネント"
                PLAYERLIST[プレイヤーリスト<br/>PlayerList.tsx]
                VOTINGPANEL[投票パネル<br/>VotingPanel.tsx]
                GAMELOG[ゲームログ<br/>GameLog.tsx]
                ROLESPANEL[役職パネル群<br/>SeerPanel.tsx<br/>WerewolfPanel.tsx<br/>BodyguardPanel.tsx]
            end
            
            subgraph "リアルタイム通信"
                WEBSOCKET[WebSocketフック<br/>useWebSocket.ts]
                SOCKETIO[Socket.IO Client<br/>リアルタイム同期]
            end
        end
        
        subgraph "バックエンド (FastAPI)"
            MAINAPI[メインAPI<br/>main.py]
            
            subgraph "ゲームロジック"
                ROOMMANAGER[ルーム管理<br/>Room Creation/Join]
                GAMEENGINE[ゲームエンジン<br/>Phase Management]
                VOTELOGIC[投票処理<br/>Vote Counting]
                ROLELOGIC[役職処理<br/>Seer/Bodyguard Actions]
            end
            
            subgraph "WebSocket通信"
                SOCKETSERVER[Socket.IO Server<br/>リアルタイム通信]
                EVENTHANDLER[イベントハンドラー<br/>speak/vote/action]
            end
        end
        
        subgraph "AIエージェントシステム"
            AIMANAGER[AI管理システム<br/>agent.py]
            
            subgraph "5つの専門エージェント"
                QUESTIONAI[質問エージェント<br/>情報収集・推理]
                ACCUSEAI[告発エージェント<br/>疑惑提起・告発]
                SUPPORTAI[サポートエージェント<br/>味方支援・信頼構築]
                COMINGOUTAI[COエージェント<br/>役職公開戦略]
                HISTORYAI[履歴エージェント<br/>発言分析]
            end
            
            STRATEGICENGINE[統合戦略エンジン<br/>最適発言選択]
            NLPROCESSOR[自然言語処理<br/>発言生成・清浄化]
        end
    end
    
    subgraph "外部AI・データサービス"
        VERTEXAI[Google Vertex AI<br/>Gemini 1.5 Flash<br/>自然言語生成]
        DATABASE[(PostgreSQL<br/>ゲーム状態<br/>プレイヤーデータ<br/>会話履歴)]
        REDIS[(Redis Cache<br/>セッション管理<br/>リアルタイム状態)]
    end
    
    %% ユーザー接続
    USER1 --> GAMEROOM
    USER2 --> ROOMLIST
    USER3 --> GAMEROOM
    
    %% フロントエンド内部接続
    GAMEROOM --> PLAYERLIST
    GAMEROOM --> VOTINGPANEL
    GAMEROOM --> GAMELOG
    GAMEROOM --> ROLESPANEL
    GAMEROOM --> WEBSOCKET
    WEBSOCKET --> SOCKETIO
    
    %% フロントエンド-バックエンド接続
    SOCKETIO <--> SOCKETSERVER
    ROOMLIST --> MAINAPI
    
    %% バックエンド内部接続
    MAINAPI --> ROOMMANAGER
    MAINAPI --> GAMEENGINE
    SOCKETSERVER --> EVENTHANDLER
    EVENTHANDLER --> VOTELOGIC
    EVENTHANDLER --> ROLELOGIC
    GAMEENGINE --> AIMANAGER
    
    %% AIエージェント内部接続
    AIMANAGER --> QUESTIONAI
    AIMANAGER --> ACCUSEAI
    AIMANAGER --> SUPPORTAI
    AIMANAGER --> COMINGOUTAI
    AIMANAGER --> HISTORYAI
    
    QUESTIONAI --> STRATEGICENGINE
    ACCUSEAI --> STRATEGICENGINE
    SUPPORTAI --> STRATEGICENGINE
    COMINGOUTAI --> STRATEGICENGINE
    HISTORYAI --> STRATEGICENGINE
    
    STRATEGICENGINE --> NLPROCESSOR
    NLPROCESSOR --> VERTEXAI
    
    %% データ接続
    MAINAPI --> DATABASE
    MAINAPI --> REDIS
    AIMANAGER --> DATABASE
    SOCKETSERVER --> REDIS
    
    %% スタイリング
    classDef userStyle fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef frontendStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef backendStyle fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef aiStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef dataStyle fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class USER1,USER2,USER3 userStyle
    class GAMEROOM,ROOMLIST,PLAYERLIST,VOTINGPANEL,GAMELOG,ROLESPANEL,WEBSOCKET,SOCKETIO frontendStyle
    class MAINAPI,ROOMMANAGER,GAMEENGINE,VOTELOGIC,ROLELOGIC,SOCKETSERVER,EVENTHANDLER backendStyle
    class AIMANAGER,QUESTIONAI,ACCUSEAI,SUPPORTAI,COMINGOUTAI,HISTORYAI,STRATEGICENGINE,NLPROCESSOR aiStyle
    class VERTEXAI,DATABASE,REDIS dataStyle
```

## ゲームフロー構成図

```mermaid
graph LR
    subgraph "1. ゲーム開始フロー"
        A1[ルーム作成] --> A2[プレイヤー参加]
        A2 --> A3[AI生成]
        A3 --> A4[ゲーム開始]
    end
    
    subgraph "2. 昼フェーズ (3ラウンド制)"
        B1[ラウンド1発言] --> B2[ラウンド2発言]
        B2 --> B3[ラウンド3発言]
        B3 --> B4[投票フェーズ]
    end
    
    subgraph "3. 投票・処刑フェーズ"
        C1[全員投票] --> C2[得票集計]
        C2 --> C3[最多票者処刑]
        C3 --> C4[勝利判定]
    end
    
    subgraph "4. 夜フェーズ"
        D1[人狼襲撃] --> D2[占い師占い]
        D2 --> D3[ボディガード護衛]
        D3 --> D4[結果反映]
    end
    
    subgraph "5. AI意思決定フロー"
        E1[状況分析] --> E2[5エージェント提案]
        E2 --> E3[統合エンジン評価]
        E3 --> E4[最適戦略選択]
        E4 --> E5[自然言語生成]
    end
    
    A4 --> B1
    B4 --> C1
    C4 --> D1
    C4 --> GAMEEND[ゲーム終了]
    D4 --> B1
    
    %% AI処理の並行実行
    B1 -.-> E1
    B2 -.-> E1
    B3 -.-> E1
    D1 -.-> E1
    
    E5 -.-> B1
    E5 -.-> B2
    E5 -.-> B3
    E5 -.-> D1
    
    classDef gameflowStyle fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef aiflowStyle fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    
    class A1,A2,A3,A4,B1,B2,B3,B4,C1,C2,C3,C4,D1,D2,D3,D4,GAMEEND gameflowStyle
    class E1,E2,E3,E4,E5 aiflowStyle
```

## データモデル構成図

```mermaid
erDiagram
    ROOMS {
        uuid id PK
        string name
        string status
        string current_phase
        int current_day
        int current_round
        timestamp created_at
        json settings
    }
    
    PLAYERS {
        uuid id PK
        uuid room_id FK
        string name
        string role
        boolean is_ai
        boolean is_alive
        json persona
        timestamp joined_at
    }
    
    SPEECHES {
        uuid id PK
        uuid player_id FK
        uuid room_id FK
        int day
        int round
        text content
        timestamp created_at
    }
    
    VOTES {
        uuid id PK
        uuid voter_id FK
        uuid target_id FK
        uuid room_id FK
        int day
        timestamp created_at
    }
    
    NIGHT_ACTIONS {
        uuid id PK
        uuid player_id FK
        uuid room_id FK
        string action_type
        uuid target_id FK
        int day
        timestamp created_at
    }
    
    AI_STRATEGIES {
        uuid id PK
        uuid player_id FK
        string agent_type
        json strategy_data
        float confidence_score
        timestamp created_at
    }
    
    GAME_LOGS {
        uuid id PK
        uuid room_id FK
        string event_type
        json event_data
        timestamp created_at
    }
    
    ROOMS ||--o{ PLAYERS : "contains"
    PLAYERS ||--o{ SPEECHES : "makes"
    PLAYERS ||--o{ VOTES : "casts"
    PLAYERS ||--o{ NIGHT_ACTIONS : "performs"
    PLAYERS ||--o{ AI_STRATEGIES : "uses"
    ROOMS ||--o{ SPEECHES : "logs"
    ROOMS ||--o{ VOTES : "tracks"
    ROOMS ||--o{ NIGHT_ACTIONS : "records"
    ROOMS ||--o{ GAME_LOGS : "maintains"
```

## 全体システム構成図

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Browser<br/>React + TypeScript]
        MOB[Mobile Browser<br/>PWA]
    end
    
    subgraph "Load Balancer"
        LB[Google Cloud Load Balancer]
    end
    
    subgraph "Application Layer - Google Cloud Run"
        FRONTEND[Frontend Service<br/>React SPA<br/>nginx + Vite]
        BACKEND[Backend Service<br/>FastAPI + Socket.IO<br/>Python 3.11]
    end
    
    subgraph "AI Layer"
        VERTEX[Google Vertex AI<br/>Gemini 1.5 Flash<br/>Natural Language Processing]
        AGENT[AI Agent Service<br/>Multi-Persona Management<br/>Strategy Engine]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL Database<br/>Game State<br/>Player Data<br/>Chat History)]
        CACHE[Redis Cache<br/>Session Management<br/>Real-time State]
    end
    
    subgraph "Infrastructure"
        CLOUDRUN[Google Cloud Run<br/>Auto Scaling<br/>Containerized Deployment]
        STORAGE[Cloud Storage<br/>Static Assets<br/>Game Logs]
        MONITOR[Cloud Monitoring<br/>Logging & Analytics]
    end
    
    %% Client connections
    WEB --> LB
    MOB --> LB
    
    %% Load balancer routing
    LB --> FRONTEND
    LB --> BACKEND
    
    %% Frontend to Backend
    FRONTEND --> BACKEND
    
    %% Backend to AI
    BACKEND --> VERTEX
    BACKEND --> AGENT
    AGENT --> VERTEX
    
    %% Backend to Data
    BACKEND --> DB
    BACKEND --> CACHE
    
    %% Infrastructure connections
    FRONTEND --> CLOUDRUN
    BACKEND --> CLOUDRUN
    AGENT --> CLOUDRUN
    
    BACKEND --> STORAGE
    BACKEND --> MONITOR
    
    %% Styling
    classDef clientStyle fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef appStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef aiStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef dataStyle fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef infraStyle fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class WEB,MOB clientStyle
    class FRONTEND,BACKEND appStyle
    class VERTEX,AGENT aiStyle
    class DB,CACHE dataStyle
    class CLOUDRUN,STORAGE,MONITOR infraStyle
```

## データフロー図

```mermaid
sequenceDiagram
    participant U as User (Web Client)
    participant F as Frontend (React)
    participant B as Backend (FastAPI)
    participant AI as AI Agent
    participant V as Vertex AI
    participant DB as PostgreSQL
    
    Note over U,DB: ゲーム開始フロー
    
    U->>F: ゲーム参加要求
    F->>B: WebSocket接続 & 参加API
    B->>DB: プレイヤー情報保存
    B->>AI: AIプレイヤー生成要求
    AI->>V: ペルソナ初期化
    V-->>AI: ペルソナ設定完了
    AI-->>B: AIプレイヤー準備完了
    B-->>F: ゲーム状態更新 (WebSocket)
    F-->>U: ゲーム画面表示
    
    Note over U,DB: ゲームプレイフロー
    
    loop ゲームターン
        U->>F: 発言入力
        F->>B: 発言送信 (WebSocket)
        B->>DB: 発言保存
        B-->>F: 全員に発言通知
        F-->>U: 発言表示
        
        B->>AI: AI発言トリガー
        AI->>V: 文脈分析 & 発言生成
        V-->>AI: AI発言テキスト
        AI->>B: AI発言送信
        B->>DB: AI発言保存
        B-->>F: AI発言通知
        F-->>U: AI発言表示
        
        Note over B: フェーズ進行判定
        B->>B: ターン終了チェック
        alt フェーズ変更
            B->>DB: ゲーム状態更新
            B-->>F: フェーズ変更通知
            F-->>U: 画面遷移
        end
    end
    
    Note over U,DB: ゲーム終了フロー
    
    B->>B: 勝利条件判定
    B->>DB: ゲーム結果保存
    B-->>F: ゲーム終了通知
    F-->>U: 結果画面表示
```

## マイクロサービス構成詳細

```mermaid
graph LR
    subgraph "Frontend Container"
        REACT[React App<br/>- UI Components<br/>- State Management<br/>- WebSocket Client]
        NGINX[nginx<br/>- Static File Serving<br/>- Reverse Proxy<br/>- SSL Termination]
        REACT --> NGINX
    end
    
    subgraph "Backend Container"
        FASTAPI[FastAPI Server<br/>- REST API<br/>- WebSocket Handler<br/>- Business Logic]
        SOCKETIO[Socket.IO<br/>- Real-time Communication<br/>- Room Management<br/>- Event Broadcasting]
        FASTAPI --> SOCKETIO
    end
    
    subgraph "AI Container"
        AIAGENT[AI Agent Manager<br/>- Multi-Agent Coordination<br/>- Persona Management<br/>- Strategy Engine]
        NLPROCESSOR[NL Processor<br/>- Text Generation<br/>- Context Analysis<br/>- Response Filtering]
        AIAGENT --> NLPROCESSOR
    end
    
    subgraph "External Services"
        VERTEXAI[Google Vertex AI<br/>- Gemini 1.5 Flash<br/>- Natural Language Generation<br/>- Context Understanding]
        POSTGRESQL[(PostgreSQL<br/>- Game State<br/>- Player Data<br/>- Conversation History)]
        REDIS[(Redis<br/>- Session Cache<br/>- Real-time State<br/>- WebSocket Sessions)]
    end
    
    %% Service connections
    NGINX -.->|HTTPS| FASTAPI
    FASTAPI --> POSTGRESQL
    FASTAPI --> REDIS
    FASTAPI --> AIAGENT
    NLPROCESSOR --> VERTEXAI
    
    %% Styling
    classDef frontendStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef backendStyle fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    classDef aiStyle fill:#fff8e1,stroke:#ffa000,stroke-width:2px
    classDef externalStyle fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    
    class REACT,NGINX frontendStyle
    class FASTAPI,SOCKETIO backendStyle
    class AIAGENT,NLPROCESSOR aiStyle
    class VERTEXAI,POSTGRESQL,REDIS externalStyle
```

## デプロイメント構成図

```mermaid
graph TB
    subgraph "Development Environment"
        DEVLOCAL[Local Development<br/>Docker Compose<br/>Hot Reload]
    end
    
    subgraph "CI/CD Pipeline"
        GITHUB[GitHub Repository<br/>Source Code<br/>Version Control]
        CLOUDBUILD[Google Cloud Build<br/>Automated Testing<br/>Docker Image Build]
        REGISTRY[Google Container Registry<br/>Docker Image Storage<br/>Version Management]
    end
    
    subgraph "Production Environment - Google Cloud"
        CLOUDRUN[Google Cloud Run<br/>- Auto Scaling<br/>- Load Balancing<br/>- Health Monitoring]
        
        subgraph "Running Containers"
            FRONTCONTAINER[Frontend Container<br/>nginx + React SPA]
            BACKCONTAINER[Backend Container<br/>FastAPI + Socket.IO]
            AICONTAINER[AI Agent Container<br/>Vertex AI Integration]
        end
        
        CLOUDRUN --> FRONTCONTAINER
        CLOUDRUN --> BACKCONTAINER
        CLOUDRUN --> AICONTAINER
    end
    
    subgraph "Managed Services"
        CLOUDSQL[Cloud SQL<br/>PostgreSQL<br/>Automated Backups]
        MEMORYSTORE[Memorystore<br/>Redis<br/>High Availability]
        VERTEXAI[Vertex AI<br/>Gemini API<br/>ML Platform]
        MONITORING[Cloud Monitoring<br/>Logging<br/>Alerting]
    end
    
    %% Development flow
    DEVLOCAL --> GITHUB
    
    %% CI/CD flow
    GITHUB --> CLOUDBUILD
    CLOUDBUILD --> REGISTRY
    REGISTRY --> CLOUDRUN
    
    %% Production connections
    BACKCONTAINER --> CLOUDSQL
    BACKCONTAINER --> MEMORYSTORE
    AICONTAINER --> VERTEXAI
    CLOUDRUN --> MONITORING
    
    %% Styling
    classDef devStyle fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef cicdStyle fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px
    classDef prodStyle fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef serviceStyle fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    
    class DEVLOCAL devStyle
    class GITHUB,CLOUDBUILD,REGISTRY cicdStyle
    class CLOUDRUN,FRONTCONTAINER,BACKCONTAINER,AICONTAINER prodStyle
    class CLOUDSQL,MEMORYSTORE,VERTEXAI,MONITORING serviceStyle
```

## セキュリティ・ネットワーク構成

```mermaid
graph TB
    subgraph "Internet"
        USERS[Users<br/>Web/Mobile Clients]
    end
    
    subgraph "Google Cloud - DMZ"
        WAF[Cloud Armor<br/>Web Application Firewall<br/>DDoS Protection]
        LB[Load Balancer<br/>SSL/TLS Termination<br/>Traffic Distribution]
    end
    
    subgraph "Application Tier - VPC"
        subgraph "Public Subnet"
            FRONTEND[Frontend Service<br/>Cloud Run<br/>Public Access]
        end
        
        subgraph "Private Subnet"
            BACKEND[Backend Service<br/>Cloud Run<br/>Private Access]
            AISERVICE[AI Service<br/>Cloud Run<br/>Private Access]
        end
    end
    
    subgraph "Data Tier - Private VPC"
        DATABASE[(Cloud SQL<br/>PostgreSQL<br/>Private IP)]
        CACHE[(Memorystore<br/>Redis<br/>Private Network)]
    end
    
    subgraph "External APIs"
        VERTEX[Vertex AI<br/>Google APIs<br/>Service Account Auth]
    end
    
    subgraph "Security & Monitoring"
        IAM[Identity & Access Management<br/>Service Accounts<br/>Role-based Access]
        SECRETS[Secret Manager<br/>API Keys<br/>Database Credentials]
        AUDIT[Cloud Audit Logs<br/>Security Monitoring<br/>Compliance]
    end
    
    %% Network flow
    USERS --> WAF
    WAF --> LB
    LB --> FRONTEND
    FRONTEND -.->|Private Network| BACKEND
    BACKEND -.->|Private Network| AISERVICE
    
    %% Data connections
    BACKEND -.->|Private IP| DATABASE
    BACKEND -.->|Private Network| CACHE
    AISERVICE -.->|Service Account| VERTEX
    
    %% Security connections
    BACKEND -.->|Auth| IAM
    AISERVICE -.->|Auth| IAM
    BACKEND -.->|Secrets| SECRETS
    AISERVICE -.->|Secrets| SECRETS
    
    %% Monitoring
    FRONTEND --> AUDIT
    BACKEND --> AUDIT
    AISERVICE --> AUDIT
    
    %% Styling
    classDef publicStyle fill:#ffebee,stroke:#f44336,stroke-width:2px
    classDef appStyle fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef dataStyle fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef securityStyle fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    
    class USERS,WAF,LB publicStyle
    class FRONTEND,BACKEND,AISERVICE appStyle
    class DATABASE,CACHE,VERTEX dataStyle
    class IAM,SECRETS,AUDIT securityStyle
```

このシステムアーキテクチャは、スケーラビリティ、セキュリティ、パフォーマンスを考慮したクラウドネイティブ設計となっています。Google Cloud Platformの各種マネージドサービスを活用し、高可用性と自動スケーリングを実現しています。
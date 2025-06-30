# AI人狼オンライン - システムアーキテクチャ図

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
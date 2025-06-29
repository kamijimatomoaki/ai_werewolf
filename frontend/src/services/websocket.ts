import { io, Socket } from 'socket.io-client';

export interface WebSocketEvents {
  // サーバーからのイベント
  'game_started': (data: { room_id: string; message: string }) => void;
  'new_speech': (data: { room_id: string; speaker_id: string; statement: string }) => void;
  'player_joined': (data: { player_name: string; sid: string }) => void;
  'new_message': (data: { sender_sid: string; message: string }) => void;
  'room_updated': (data: { room_id: string; room_data: any }) => void;
  'vote_phase_started': (data: { room_id: string; message: string }) => void;
  'vote_cast': (data: { room_id: string; voter_id: string; target_id: string }) => void;
  'night_phase_started': (data: { room_id: string; message: string }) => void;
  
  // クライアントからのイベント
  'join_room': (data: { room_id: string }) => void;
  'chat_message': (data: { room_id: string; message: string }) => void;
}

// 接続状態の種類
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

class WebSocketService {
  private socket: Socket | null = null;
  private currentRoomId: string | null = null;
  private serverUrl: string = this.getWebSocketUrl();
  private connectionStatus: ConnectionStatus = 'disconnected';
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000; // 初期遅延時間（ミリ秒）
  private maxReconnectDelay: number = 30000; // 最大遅延時間（30秒）
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private connectionListeners: ((status: ConnectionStatus) => void)[] = [];

  // WebSocket URLを適切に生成
  private getWebSocketUrl(): string {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
    console.log('API_BASE_URL:', apiBaseUrl);
    console.log('VITE_API_BASE_URL env var:', import.meta.env.VITE_API_BASE_URL);
    
    if (apiBaseUrl) {
      // Cloud Run環境の場合
      const url = apiBaseUrl.replace('/api', '');
      console.log('WebSocket URL (production):', url);
      return url;
    } else {
      // ローカル開発環境の場合
      console.log('WebSocket URL (development): http://localhost:8000');
      return 'http://localhost:8000';
    }
  }

  connect(serverUrl?: string, sessionToken?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // serverUrlが指定されていない場合は自動生成されたURLを使用
        this.serverUrl = serverUrl || this.getWebSocketUrl();
        console.log('Connecting to WebSocket:', this.serverUrl);
        this.setConnectionStatus('connecting');
        
        // 既存の接続があれば切断
        if (this.socket) {
          this.socket.disconnect();
        }

        // ローカルストレージからsession_tokenを取得
        const storedSessionToken = sessionToken || localStorage.getItem('session_token');

        this.socket = io(this.serverUrl, {
          transports: ['websocket', 'polling'],
          autoConnect: true,
          reconnection: false, // 自動再接続を無効化（カスタムロジックを使用）
          timeout: 20000, // 接続タイムアウト（20秒に延長）
          forceNew: true, // 強制的に新しい接続を作成
          withCredentials: false,
          query: { // session_tokenをクエリパラメータとして送信
            session_token: storedSessionToken || '',
          },
        });

        this.socket.on('connect', () => {
          console.log('WebSocket connected:', this.socket?.id);
          this.setConnectionStatus('connected');
          this.reconnectAttempts = 0; // 再接続試行回数をリセット
          this.startHeartbeat();
          
          // 部屋に再参加
          if (this.currentRoomId) {
            this.socket!.emit('join_room', { room_id: this.currentRoomId });
          }
          
          resolve();
        });

        this.socket.on('connect_error', (error) => {
          console.error('WebSocket connection error:', error);
          this.setConnectionStatus('error');
          
          // 自動再接続を試行
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          } else {
            reject(new Error(`接続に失敗しました: ${error.message}`));
          }
        });

        this.socket.on('disconnect', (reason) => {
          console.log('WebSocket disconnected:', reason);
          this.setConnectionStatus('disconnected');
          this.stopHeartbeat();
          
          // 自動再接続を試行（サーバー側から切断された場合）
          if (reason === 'io server disconnect') {
            // サーバーが意図的に切断した場合は再接続しない
            console.log('サーバーが接続を切断しました');
          } else {
            this.scheduleReconnect();
          }
        });

        this.socket.on('reconnect', () => {
          console.log('WebSocket reconnected');
          this.setConnectionStatus('connected');
          this.reconnectAttempts = 0;
        });

        this.socket.on('pong', () => {
          // Heartbeat応答を受信
          console.log('Heartbeat received');
        });

      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        this.setConnectionStatus('error');
        reject(error);
      }
    });
  }

  disconnect() {
    this.clearReconnectTimer();
    this.stopHeartbeat();
    
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.currentRoomId = null;
    this.setConnectionStatus('disconnected');
    this.reconnectAttempts = 0;
  }

  // 再接続のスケジューリング
  private scheduleReconnect() {
    if (this.reconnectTimer || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(`再接続を試行します... (${this.reconnectAttempts}/${this.maxReconnectAttempts}) - ${delay}ms後`);
    this.setConnectionStatus('reconnecting');

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect(this.serverUrl).catch(error => {
        console.error('再接続に失敗:', error);
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      });
    }, delay);
  }

  // 再接続タイマーをクリア
  private clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // ハートビート開始
  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.socket?.connected) {
        this.socket.emit('ping');
      }
    }, 30000); // 30秒ごとにping送信
  }

  // ハートビート停止
  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // 接続状態の設定とリスナーへの通知
  private setConnectionStatus(status: ConnectionStatus) {
    this.connectionStatus = status;
    this.connectionListeners.forEach(listener => {
      try {
        listener(status);
      } catch (error) {
        console.error('Connection status listener error:', error);
      }
    });
  }

  // 接続状態リスナーの追加
  onConnectionStatusChange(listener: (status: ConnectionStatus) => void) {
    this.connectionListeners.push(listener);
    // 現在の状態を即座に通知
    listener(this.connectionStatus);
  }

  // 接続状態リスナーの削除
  offConnectionStatusChange(listener: (status: ConnectionStatus) => void) {
    const index = this.connectionListeners.indexOf(listener);
    if (index > -1) {
      this.connectionListeners.splice(index, 1);
    }
  }

  // 手動再接続
  reconnect(): Promise<void> {
    this.reconnectAttempts = 0;
    this.clearReconnectTimer();
    return this.connect(this.serverUrl);
  }

  joinRoom(roomId: string) {
    if (!this.socket) {
      console.error('WebSocket not connected');
      return;
    }

    // 以前の部屋から退出
    if (this.currentRoomId && this.currentRoomId !== roomId) {
      this.leaveRoom(this.currentRoomId);
    }

    this.currentRoomId = roomId;
    this.socket.emit('join_room', { room_id: roomId });
    console.log('Joined room:', roomId);
  }

  leaveRoom(roomId: string) {
    if (!this.socket) return;
    
    // Socket.IOでは明示的なleave_roomイベントは通常不要だが、
    // カスタムロジックがある場合は送信
    this.socket.emit('leave_room', { room_id: roomId });
    console.log('Left room:', roomId);
  }

  sendChatMessage(roomId: string, message: string) {
    if (!this.socket) {
      console.error('WebSocket not connected');
      return;
    }

    this.socket.emit('chat_message', { room_id: roomId, message });
  }

  // イベントリスナーの登録
  on(event: string, listener: (...args: any[]) => void) {
    if (!this.socket) {
      console.error('WebSocket not connected');
      return;
    }
    this.socket.on(event, listener);
  }

  // イベントリスナーの削除
  off(event: string, listener?: (...args: any[]) => void) {
    if (!this.socket) return;
    if (listener) {
      this.socket.off(event, listener);
    } else {
      this.socket.off(event);
    }
  }

  // ワンタイムイベントリスナー
  once(event: string, listener: (...args: any[]) => void) {
    if (!this.socket) {
      console.error('WebSocket not connected');
      return;
    }
    this.socket.once(event, listener);
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  getCurrentRoomId(): string | null {
    return this.currentRoomId;
  }

  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  getMaxReconnectAttempts(): number {
    return this.maxReconnectAttempts;
  }

  getSocket(): Socket | null {
    return this.socket;
  }
}

// シングルトンインスタンスをエクスポート
export const websocketService = new WebSocketService();
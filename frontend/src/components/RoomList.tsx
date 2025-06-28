import { useState, useEffect } from 'react';
import keyVisual from '@/assets/key_visual.png';

import { apiService } from '@/services/api';
import { usePlayer } from '@/contexts/PlayerContext';
import { RoomSummary, RoomCreate } from '@/types/api';
import SpectatorJoinDialog from '@/components/game/SpectatorJoinDialog';

interface RoomListProps {
  onRoomJoin: (roomId: string) => void;
  onSpectatorJoin: (roomId: string, spectatorId: string) => void;
}

export default function RoomList({ onRoomJoin, onSpectatorJoin }: RoomListProps) {
  const { joinRoom: joinRoomAuth, clearRoomSession } = usePlayer();
  const [rooms, setRooms] = useState<RoomSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 部屋作成モーダル
  const [isOpen, setIsOpen] = useState(false);
  const [newRoom, setNewRoom] = useState<RoomCreate>({
    room_name: '',
    total_players: 5,
    human_players: 1,
    ai_players: 4,
    is_private: false,
  });
  const [hostName, setHostName] = useState('');
  
  // 参加モーダル
  const [isJoinOpen, setIsJoinOpen] = useState(false);
  const [selectedRoomId, setSelectedRoomId] = useState<string>('');
  const [joinPlayerName, setJoinPlayerName] = useState('');

  // 観戦モーダル
  const [isSpectatorOpen, setIsSpectatorOpen] = useState(false);
  const [spectatorRoomId, setSpectatorRoomId] = useState<string>('');
  const [spectatorRoomName, setSpectatorRoomName] = useState('');

  // 部屋一覧を取得
  const fetchRooms = async () => {
    try {
      setLoading(true);
      setError(null);
      const roomList = await apiService.getRooms();
      setRooms(roomList);
    } catch (err: any) {
      setError(err.message || '部屋一覧の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 部屋作成
  const handleCreateRoom = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // バリデーション
      if (newRoom.total_players < 5 || newRoom.total_players > 12) {
        throw new Error('プレイヤー数は5〜12人の範囲で設定してください');
      }
      if (newRoom.human_players < 1) {
        throw new Error('人間プレイヤーは最低1人必要です');
      }
      
      // 念のため古いセッションをクリア
      console.log('🧹 Creating room - clearing old session to prevent conflicts');
      clearRoomSession();
      
      const createdRoom = await apiService.createRoom(newRoom, hostName || 'ホスト');
      
      console.log('✅ Room created successfully:', createdRoom.room_id);
      
      // 作成成功後、部屋に参加（ホストプレイヤーはcreateRoomで既に追加されているため、joinRoomAuthは不要）
      onRoomJoin(createdRoom.room_id);
      
    } catch (err: any) {
      setError(err.message || '部屋の作成に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 部屋参加の開始
  const handleStartJoinRoom = (roomId: string) => {
    setSelectedRoomId(roomId);
    setJoinPlayerName('');
    setIsJoinOpen(true);
  };

  // 部屋参加の実行
  const handleJoinRoom = async () => {
    try {
      setLoading(true);
      setError(null);
      
      if (!joinPlayerName.trim()) {
        throw new Error('プレイヤー名を入力してください');
      }
      
      // 古いセッション情報をクリアしてから新しい部屋に参加
      console.log('🧹 Joining room - clearing old session to prevent conflicts');
      clearRoomSession();
      
      await joinRoomAuth(selectedRoomId, joinPlayerName);
      console.log('✅ Joined room successfully:', selectedRoomId);
      onRoomJoin(selectedRoomId);
      setIsJoinOpen(false);
      
    } catch (err: any) {
      setError(err.message || '部屋への参加に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 観戦参加を開始
  const handleStartSpectatorJoin = (room: RoomSummary) => {
    setSpectatorRoomId(room.room_id);
    setSpectatorRoomName(room.room_name);
    setIsSpectatorOpen(true);
  };

  // 観戦者として参加
  const handleSpectatorJoin = async (spectatorName: string) => {
    try {
      setLoading(true);
      
      const response = await fetch(`/api/rooms/${spectatorRoomId}/spectators/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          spectator_name: spectatorName
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '観戦参加に失敗しました');
      }

      const data = await response.json();
      onSpectatorJoin(spectatorRoomId, data.spectator_id);
      
    } catch (err: any) {
      throw new Error(err.message || '観戦参加に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 初期化時に部屋一覧を取得
  useEffect(() => {
    // ロビー表示時に古いセッション情報をクリア
    console.log('🧹 RoomList mounted - clearing any old room session');
    clearRoomSession();
    fetchRooms();
  }, [clearRoomSession]);

  // ステータスに応じた色を返す
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'waiting': return 'success';
      case 'day_discussion': return 'warning';
      case 'day_vote': return 'danger';
      case 'night': return 'secondary';
      default: return 'default';
    }
  };

  // ステータスの日本語表示
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'waiting': return '待機中';
      case 'day_discussion': return '昼の議論';
      case 'day_vote': return '投票中';
      case 'night': return '夜';
      default: return status;
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* キービジュアルヘッダー */}
      <div className="text-center mb-8">
        <img 
          src={keyVisual} 
          alt="人狼ゲーム" 
          className="mx-auto mb-4 max-w-md w-full h-auto rounded-lg shadow-2xl border border-gray-700"
        />
        <h1 className="text-4xl font-bold text-white mb-2 drop-shadow-lg">
          AI人狼オンライン
        </h1>
        <p className="text-gray-300 text-lg">AIと一緒に楽しむ心理戦ゲーム</p>
      </div>
      
      {/* コントロール部分 */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">部屋一覧</h2>
        <div className="flex gap-3">
          <button 
            onClick={fetchRooms}
            className="px-4 py-2 border border-gray-600 text-gray-300 hover:bg-gray-700 rounded transition-colors"
          >
            更新
          </button>
          <button 
            onClick={() => setIsOpen(true)}
            className="px-4 py-2 bg-red-700 hover:bg-red-600 text-white shadow-lg rounded transition-colors"
          >
            部屋を作成
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-900/40 border border-red-500/60 rounded-lg text-red-200 backdrop-blur-sm">
          <p className="font-semibold">エラー: {error}</p>
        </div>
      )}

      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500 mx-auto mb-4"></div>
          <p className="text-lg text-gray-300">読み込み中...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {rooms.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <div className="mb-6">
                <div className="text-6xl mb-4">🌙</div>
                <p className="text-xl text-gray-300 mb-2">静寂の夜が続いています...</p>
                <p className="text-gray-400">現在利用可能な部屋がありません</p>
              </div>
              <button 
                onClick={() => setIsOpen(true)}
                className="px-8 py-3 bg-red-700 hover:bg-red-600 text-white shadow-lg rounded-lg text-lg transition-colors"
              >
                最初の部屋を作成
              </button>
            </div>
          ) : (
            rooms.map((room) => (
              <div key={room.room_id} className="p-4 bg-gray-800/70 border border-gray-600/50 rounded-lg hover:bg-gray-700/80 hover:shadow-2xl hover:border-red-500/30 transition-all duration-300 backdrop-blur-sm">
                <div className="space-y-3">
                  <div className="flex justify-between items-start">
                    <h3 className="text-xl font-semibold text-white">
                      {room.room_name || `部屋 ${room.room_id.slice(0, 8)}`}
                    </h3>
                    <span className={`px-2 py-1 text-xs rounded ${
                      getStatusColor(room.status) === 'success' ? 'bg-green-500/20 text-green-400' :
                      getStatusColor(room.status) === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                      getStatusColor(room.status) === 'danger' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {getStatusLabel(room.status)}
                    </span>
                  </div>
                  
                  <div className="space-y-1 text-sm text-gray-400">
                    <p>総プレイヤー数: {room.total_players}人</p>
                    <p>人間プレイヤー: {room.human_players}人</p>
                    <p>AIプレイヤー: {room.ai_players}人</p>
                  </div>

                  <div className="flex gap-2">
                    <button 
                      className={`flex-1 px-4 py-2 rounded transition-colors ${
                        room.status !== 'waiting' 
                          ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                          : 'bg-red-700 hover:bg-red-600 text-white'
                      }`}
                      onClick={() => handleStartJoinRoom(room.room_id)}
                      disabled={room.status !== 'waiting'}
                    >
                      参加
                    </button>
                    <button 
                      className={`flex-1 px-4 py-2 border rounded transition-colors ${
                        room.status === 'waiting' || room.status === 'finished'
                          ? 'border-gray-600 text-gray-500 cursor-not-allowed'
                          : 'border-gray-600 text-gray-300 hover:bg-gray-700'
                      }`}
                      onClick={() => handleStartSpectatorJoin(room)}
                      disabled={room.status === 'waiting' || room.status === 'finished'}
                    >
                      観戦
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* 部屋作成モーダル */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-gray-900 border border-gray-700 rounded-lg">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-white">新しい部屋を作成</h2>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">ホスト名</label>
                  <input
                    type="text"
                    placeholder="あなたの名前"
                    value={hostName}
                    onChange={(e) => setHostName(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">部屋名</label>
                  <input
                    type="text"
                    placeholder="部屋名（オプション）"
                    value={newRoom.room_name}
                    onChange={(e) => setNewRoom(prev => ({ ...prev, room_name: e.target.value }))}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">人間プレイヤー</label>
                    <input
                      type="number"
                      min={1}
                      max={8}
                      value={String(newRoom.human_players)}
                      onChange={(e) => {
                        const humanPlayers = Number(e.target.value);
                        setNewRoom(prev => ({ 
                          ...prev, 
                          human_players: humanPlayers,
                          total_players: humanPlayers + prev.ai_players
                        }));
                      }}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">AIプレイヤー</label>
                    <input
                      type="number"
                      min={0}
                      max={8}
                      value={String(newRoom.ai_players)}
                      onChange={(e) => {
                        const aiPlayers = Number(e.target.value);
                        setNewRoom(prev => ({ 
                          ...prev, 
                          ai_players: aiPlayers,
                          total_players: prev.human_players + aiPlayers
                        }));
                      }}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
                
                {/* 総プレイヤー数の表示 */}
                <div className="p-4 bg-gradient-to-r from-gray-700/50 to-gray-600/50 rounded-lg border border-gray-500/30 backdrop-blur-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-200">総プレイヤー数:</span>
                    <span className="text-white font-bold text-xl bg-red-600/20 px-3 py-1 rounded-full">{newRoom.total_players}人</span>
                  </div>
                  <div className="flex justify-between items-center text-sm text-gray-300 mt-2">
                    <span className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                      人間: {newRoom.human_players}人
                    </span>
                    <span className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                      AI: {newRoom.ai_players}人
                    </span>
                  </div>
                  {(newRoom.total_players < 5 || newRoom.total_players > 12) && (
                    <div className="mt-3 p-2 bg-yellow-600/20 border border-yellow-500/30 rounded text-yellow-200 text-xs">
                      ⚠️ 推奨プレイヤー数は5〜12人です
                    </div>
                  )}
                </div>
                
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={newRoom.is_private}
                    onChange={(e) => setNewRoom(prev => ({ ...prev, is_private: e.target.checked }))}
                    className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <label className="text-sm text-gray-300">
                    プライベート部屋（部屋一覧に表示されません）
                  </label>
                </div>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setIsOpen(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  キャンセル
                </button>
                <button
                  onClick={handleCreateRoom}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
                >
                  {loading ? '作成中...' : '部屋を作成'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 部屋参加モーダル */}
      {isJoinOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-gray-900 border border-gray-700 rounded-lg">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-white">部屋に参加</h2>
                <button
                  onClick={() => setIsJoinOpen(false)}
                  className="text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">プレイヤー名</label>
                <input
                  type="text"
                  placeholder="あなたの名前を入力"
                  value={joinPlayerName}
                  onChange={(e) => setJoinPlayerName(e.target.value)}
                  autoFocus
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setIsJoinOpen(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  キャンセル
                </button>
                <button
                  onClick={handleJoinRoom}
                  disabled={loading || !joinPlayerName.trim()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
                >
                  {loading ? '参加中...' : '参加'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 観戦参加モーダル */}
      <SpectatorJoinDialog
        isOpen={isSpectatorOpen}
        roomName={spectatorRoomName}
        onClose={() => setIsSpectatorOpen(false)}
        onJoin={handleSpectatorJoin}
      />
    </div>
  );
}
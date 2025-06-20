import { useState, useEffect } from 'react';
import { Button } from "@heroui/button";
import { Card } from "@heroui/card";
import { Input } from "@heroui/input";
import { Modal, ModalContent, ModalHeader, ModalBody, ModalFooter, useDisclosure } from "@heroui/modal";
import { Chip } from "@heroui/chip";
import { Switch } from "@heroui/switch";

import { apiService } from '@/services/api';
import { usePlayer } from '@/contexts/PlayerContext';
import { RoomSummary, RoomCreate } from '@/types/api';
import SpectatorJoinDialog from '@/components/game/SpectatorJoinDialog';

interface RoomListProps {
  onRoomJoin: (roomId: string) => void;
  onSpectatorJoin: (roomId: string, spectatorId: string) => void;
}

export default function RoomList({ onRoomJoin, onSpectatorJoin }: RoomListProps) {
  const { joinRoom: joinRoomAuth } = usePlayer();
  const [rooms, setRooms] = useState<RoomSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 部屋作成モーダル
  const { isOpen, onOpen, onOpenChange } = useDisclosure();
  const [newRoom, setNewRoom] = useState<RoomCreate>({
    room_name: '',
    total_players: 5,
    human_players: 1,
    ai_players: 4,
    is_private: false,
  });
  const [hostName, setHostName] = useState('');
  
  // 参加モーダル
  const { 
    isOpen: isJoinOpen, 
    onOpen: onJoinOpen, 
    onOpenChange: onJoinOpenChange 
  } = useDisclosure();
  const [selectedRoomId, setSelectedRoomId] = useState<string>('');
  const [joinPlayerName, setJoinPlayerName] = useState('');

  // 観戦モーダル
  const { 
    isOpen: isSpectatorOpen, 
    onOpen: onSpectatorOpen, 
    onOpenChange: onSpectatorOpenChange 
  } = useDisclosure();
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
      if (newRoom.total_players !== newRoom.human_players + newRoom.ai_players) {
        throw new Error('総プレイヤー数は人間プレイヤー数とAIプレイヤー数の合計と一致する必要があります');
      }
      
      const createdRoom = await apiService.createRoom(newRoom, hostName || 'ホスト');
      
      // 作成成功後、認証してから部屋に参加
      await joinRoomAuth(createdRoom.room_id, hostName || 'ホスト');
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
    onJoinOpen();
  };

  // 部屋参加の実行
  const handleJoinRoom = async () => {
    try {
      setLoading(true);
      setError(null);
      
      if (!joinPlayerName.trim()) {
        throw new Error('プレイヤー名を入力してください');
      }
      
      await joinRoomAuth(selectedRoomId, joinPlayerName);
      onRoomJoin(selectedRoomId);
      onJoinOpenChange();
      
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
    onSpectatorOpen();
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
    fetchRooms();
  }, []);

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
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">人狼ゲーム - 部屋一覧</h1>
        <div className="flex gap-3">
          <Button color="secondary" variant="bordered" onClick={fetchRooms}>
            更新
          </Button>
          <Button color="primary" onPress={onOpen}>
            部屋を作成
          </Button>
        </div>
      </div>

      {error && (
        <Card className="mb-4 p-4 bg-red-50 border-red-200 text-red-800">
          <p className="font-semibold">エラー: {error}</p>
        </Card>
      )}

      {loading ? (
        <div className="text-center py-8">
          <p className="text-lg">読み込み中...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {rooms.length === 0 ? (
            <div className="col-span-full text-center py-8">
              <p className="text-lg text-gray-500">現在利用可能な部屋がありません</p>
              <Button color="primary" className="mt-4" onPress={onOpen}>
                最初の部屋を作成
              </Button>
            </div>
          ) : (
            rooms.map((room) => (
              <Card key={room.room_id} className="p-4 hover:shadow-lg transition-shadow">
                <div className="space-y-3">
                  <div className="flex justify-between items-start">
                    <h3 className="text-xl font-semibold">
                      {room.room_name || `部屋 ${room.room_id.slice(0, 8)}`}
                    </h3>
                    <Chip color={getStatusColor(room.status)} variant="flat" size="sm">
                      {getStatusLabel(room.status)}
                    </Chip>
                  </div>
                  
                  <div className="space-y-1 text-sm text-gray-600">
                    <p>総プレイヤー数: {room.total_players}人</p>
                    <p>人間プレイヤー: {room.human_players}人</p>
                    <p>AIプレイヤー: {room.ai_players}人</p>
                  </div>

                  <div className="flex gap-2">
                    <Button 
                      color="primary" 
                      className="flex-1"
                      onClick={() => handleStartJoinRoom(room.room_id)}
                      isDisabled={room.status !== 'waiting'}
                    >
                      参加
                    </Button>
                    <Button 
                      color="secondary" 
                      variant="bordered"
                      className="flex-1"
                      onClick={() => handleStartSpectatorJoin(room)}
                      isDisabled={room.status === 'waiting' || room.status === 'finished'}
                    >
                      観戦
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* 部屋作成モーダル */}
      <Modal isOpen={isOpen} onOpenChange={onOpenChange} size="2xl">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                新しい部屋を作成
              </ModalHeader>
              <ModalBody>
                <div className="space-y-4">
                  <Input
                    label="ホスト名"
                    placeholder="あなたの名前"
                    value={hostName}
                    onChange={(e) => setHostName(e.target.value)}
                  />
                  
                  <Input
                    label="部屋名"
                    placeholder="部屋名（オプション）"
                    value={newRoom.room_name}
                    onChange={(e) => setNewRoom(prev => ({ ...prev, room_name: e.target.value }))}
                  />
                  
                  <div className="grid grid-cols-3 gap-4">
                    <Input
                      label="総プレイヤー数"
                      type="number"
                      min={5}
                      max={12}
                      value={String(newRoom.total_players)}
                      onChange={(e) => setNewRoom(prev => ({ ...prev, total_players: Number(e.target.value) }))}
                    />
                    
                    <Input
                      label="人間プレイヤー"
                      type="number"
                      min={1}
                      max={newRoom.total_players}
                      value={String(newRoom.human_players)}
                      onChange={(e) => setNewRoom(prev => ({ ...prev, human_players: Number(e.target.value) }))}
                    />
                    
                    <Input
                      label="AIプレイヤー"
                      type="number"
                      min={0}
                      value={String(newRoom.ai_players)}
                      onChange={(e) => setNewRoom(prev => ({ 
                        ...prev, 
                        ai_players: Number(e.target.value),
                        total_players: newRoom.human_players + Number(e.target.value)
                      }))}
                    />
                  </div>
                  
                  <Switch
                    isSelected={newRoom.is_private}
                    onValueChange={(value) => setNewRoom(prev => ({ ...prev, is_private: value }))}
                  >
                    プライベート部屋（部屋一覧に表示されません）
                  </Switch>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button color="danger" variant="light" onPress={onClose}>
                  キャンセル
                </Button>
                <Button 
                  color="primary" 
                  onPress={handleCreateRoom}
                  isLoading={loading}
                >
                  部屋を作成
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* 部屋参加モーダル */}
      <Modal isOpen={isJoinOpen} onOpenChange={onJoinOpenChange}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                部屋に参加
              </ModalHeader>
              <ModalBody>
                <Input
                  label="プレイヤー名"
                  placeholder="あなたの名前を入力"
                  value={joinPlayerName}
                  onChange={(e) => setJoinPlayerName(e.target.value)}
                  autoFocus
                />
              </ModalBody>
              <ModalFooter>
                <Button color="danger" variant="light" onPress={onClose}>
                  キャンセル
                </Button>
                <Button 
                  color="primary" 
                  onPress={handleJoinRoom}
                  isLoading={loading}
                  isDisabled={!joinPlayerName.trim()}
                >
                  参加
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* 観戦参加モーダル */}
      <SpectatorJoinDialog
        isOpen={isSpectatorOpen}
        roomName={spectatorRoomName}
        onClose={onSpectatorOpenChange}
        onJoin={handleSpectatorJoin}
      />
    </div>
  );
}
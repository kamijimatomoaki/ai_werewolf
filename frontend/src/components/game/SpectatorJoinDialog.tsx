import React, { useState } from 'react';
import { Button } from '@heroui/button';
import { Input } from '@heroui/input';
import { Modal, ModalContent, ModalHeader, ModalBody, ModalFooter } from '@heroui/modal';

interface SpectatorJoinDialogProps {
  isOpen: boolean;
  roomName: string;
  onClose: () => void;
  onJoin: (spectatorName: string) => Promise<void>;
}

export function SpectatorJoinDialog({ isOpen, roomName, onClose, onJoin }: SpectatorJoinDialogProps) {
  const [spectatorName, setSpectatorName] = useState('');
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleJoin = async () => {
    if (!spectatorName.trim()) {
      setError('観戦者名を入力してください');
      return;
    }

    setIsJoining(true);
    setError(null);

    try {
      await onJoin(spectatorName.trim());
      setSpectatorName('');
      onClose();
    } catch (err: any) {
      setError(err.message || '観戦参加に失敗しました');
    } finally {
      setIsJoining(false);
    }
  };

  const handleClose = () => {
    if (!isJoining) {
      setSpectatorName('');
      setError(null);
      onClose();
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={handleClose}
      isDismissable={!isJoining}
      hideCloseButton={isJoining}
    >
      <ModalContent>
        <ModalHeader className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-xl">👁️</span>
            <span>観戦参加</span>
          </div>
          <p className="text-sm text-gray-600 font-normal">
            「{roomName}」を観戦します
          </p>
        </ModalHeader>
        
        <ModalBody>
          <div className="space-y-4">
            <div>
              <Input
                label="観戦者名"
                placeholder="観戦者名を入力してください"
                value={spectatorName}
                onChange={(e) => {
                  setSpectatorName(e.target.value);
                  if (error) setError(null);
                }}
                maxLength={20}
                isDisabled={isJoining}
                autoFocus
                errorMessage={error}
                isInvalid={!!error}
              />
              <p className="text-xs text-gray-500 mt-1">
                最大20文字まで入力できます
              </p>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-800 mb-2">観戦モードについて</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• ゲームの進行をリアルタイムで観戦できます</li>
                <li>• プレイヤーの役職は表示されません</li>
                <li>• 他の観戦者とチャットができます</li>
                <li>• ゲームに影響を与えることはできません</li>
              </ul>
            </div>
          </div>
        </ModalBody>
        
        <ModalFooter>
          <Button 
            variant="bordered" 
            onPress={handleClose}
            isDisabled={isJoining}
          >
            キャンセル
          </Button>
          <Button 
            color="primary" 
            onPress={handleJoin}
            isDisabled={!spectatorName.trim() || isJoining}
            isLoading={isJoining}
          >
            観戦開始
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

export default SpectatorJoinDialog;
import React, { useState, useRef, useEffect } from 'react';
import { Card, CardBody, CardHeader } from '@heroui/card';
import { Button } from '@heroui/button';
import { Input } from '@heroui/input';

interface SpectatorChatMessage {
  message_id: string;
  spectator_name: string;
  message: string;
  timestamp: string;
}

interface SpectatorChatProps {
  roomId: string;
  spectatorId: string;
  messages: SpectatorChatMessage[];
  onSendMessage: (message: string) => Promise<void>;
}

export function SpectatorChat({ roomId, spectatorId, messages, onSendMessage }: SpectatorChatProps) {
  const [newMessage, setNewMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!newMessage.trim() || isSending) return;

    const message = newMessage.trim();
    setNewMessage('');
    setIsSending(true);

    try {
      await onSendMessage(message);
    } catch (error) {
      console.error('Failed to send message:', error);
      // メッセージ送信に失敗した場合、入力を復元
      setNewMessage(message);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ja-JP', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <Card className="h-96 flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">💬</span>
          <h3 className="text-lg font-semibold">観戦者チャット</h3>
        </div>
      </CardHeader>
      
      <CardBody className="flex flex-col h-full p-0">
        {/* メッセージ表示エリア */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 text-sm">
              観戦者チャットが開始されていません
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.message_id} className="flex flex-col space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-xs font-medium text-blue-600">
                      {msg.spectator_name[0]}
                    </span>
                  </div>
                  <span className="text-sm font-medium">{msg.spectator_name}</span>
                  <span className="text-xs text-gray-500">
                    {formatTime(msg.timestamp)}
                  </span>
                </div>
                <div className="ml-8 text-sm bg-gray-50 rounded-lg p-2">
                  {msg.message}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* メッセージ入力エリア */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex gap-2">
            <Input
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="観戦者とチャット..."
              maxLength={500}
              isDisabled={isSending}
              className="flex-1"
            />
            <Button
              color="primary"
              size="md"
              onPress={handleSendMessage}
              isDisabled={!newMessage.trim() || isSending}
              isLoading={isSending}
              className="min-w-16"
            >
              送信
            </Button>
          </div>
          
          {/* 文字数制限表示 */}
          <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
            <span>観戦者のみ参加できます</span>
            <span>{newMessage.length}/500</span>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

export default SpectatorChat;
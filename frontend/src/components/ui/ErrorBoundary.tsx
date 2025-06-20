import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Card } from "@heroui/card";
import { Button } from "@heroui/button";

// エラー情報の型定義
interface ErrorDetails {
  message: string;
  stack?: string;
  componentStack?: string;
  timestamp: Date;
  userAgent: string;
  url: string;
}

interface Props {
  children: ReactNode;
  fallback?: React.ComponentType<{ error: Error; errorDetails: ErrorDetails; retry: () => void }>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorDetails: ErrorDetails | null;
}

// デフォルトのエラー表示コンポーネント
const DefaultErrorFallback: React.FC<{
  error: Error;
  errorDetails: ErrorDetails;
  retry: () => void;
}> = ({ error, errorDetails, retry }) => {
  const [showDetails, setShowDetails] = React.useState(false);

  const handleReportError = () => {
    // エラーレポート機能（将来的に実装）
    console.error('Error Report:', {
      error: error.message,
      stack: error.stack,
      details: errorDetails
    });
    
    // 将来的にはAPIエンドポイントに送信
    alert('エラーレポートが送信されました');
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
      <Card className="max-w-2xl w-full p-6">
        <div className="text-center">
          {/* エラーアイコン */}
          <div className="mx-auto w-16 h-16 mb-4 text-red-500">
            <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            予期しないエラーが発生しました
          </h1>
          
          <p className="text-gray-600 mb-6">
            申し訳ございませんが、アプリケーションでエラーが発生しました。
            ページを再読み込みするか、後でもう一度お試しください。
          </p>

          {/* アクションボタン */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center mb-6">
            <Button
              color="primary"
              onClick={retry}
              className="min-w-[120px]"
            >
              再試行
            </Button>
            
            <Button
              variant="bordered"
              onClick={() => window.location.reload()}
              className="min-w-[120px]"
            >
              ページ再読み込み
            </Button>
            
            <Button
              variant="ghost"
              onClick={() => window.location.href = '/'}
              className="min-w-[120px]"
            >
              ホームに戻る
            </Button>
          </div>

          {/* エラー詳細トグル */}
          <div className="border-t pt-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDetails(!showDetails)}
              className="text-gray-500"
            >
              {showDetails ? '詳細を隠す' : 'エラー詳細を表示'}
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReportError}
              className="ml-3 text-gray-500"
            >
              エラーを報告
            </Button>
          </div>

          {/* エラー詳細情報 */}
          {showDetails && (
            <div className="mt-4 p-4 bg-gray-100 rounded-lg text-left">
              <h3 className="font-semibold text-sm text-gray-700 mb-2">エラー詳細:</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <div>
                  <strong>エラーメッセージ:</strong>
                  <pre className="mt-1 whitespace-pre-wrap font-mono text-xs">
                    {error.message}
                  </pre>
                </div>
                
                <div>
                  <strong>発生時刻:</strong> {errorDetails.timestamp.toLocaleString()}
                </div>
                
                <div>
                  <strong>ページURL:</strong> {errorDetails.url}
                </div>
                
                {error.stack && (
                  <div>
                    <strong>スタックトレース:</strong>
                    <pre className="mt-1 whitespace-pre-wrap font-mono text-xs bg-white p-2 rounded border max-h-40 overflow-y-auto">
                      {error.stack}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorDetails: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    const errorDetails: ErrorDetails = {
      message: error.message,
      stack: error.stack,
      timestamp: new Date(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    return {
      hasError: true,
      error,
      errorDetails
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // エラー詳細を補完
    if (this.state.errorDetails) {
      this.state.errorDetails.componentStack = errorInfo.componentStack;
    }

    // エラーログ出力
    console.error('ErrorBoundary caught an error:', error);
    console.error('Component stack:', errorInfo.componentStack);

    // カスタムエラーハンドラを実行
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // エラー追跡サービスに送信（将来的に実装）
    // 例: Sentry, LogRocket, Bugsnag など
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorDetails: null
    });
  };

  render() {
    if (this.state.hasError && this.state.error && this.state.errorDetails) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback;
      
      return (
        <FallbackComponent
          error={this.state.error}
          errorDetails={this.state.errorDetails}
          retry={this.handleRetry}
        />
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
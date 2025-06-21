'use client';

import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { useState, useEffect, Suspense } from 'react';
import { requestPasswordReset } from '@/utils/api';

function PasswordResetSentContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const email = searchParams.get('email');
  const sentAtParam = searchParams.get('sentAt');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  // 初期クールダウンタイマーの設定
  useEffect(() => {
    if (sentAtParam) {
      const sentAt = parseInt(sentAtParam, 10);
      const now = Date.now();
      const elapsedSeconds = Math.floor((now - sentAt) / 1000);
      const remainingSeconds = Math.max(0, 60 - elapsedSeconds);
      setCooldownSeconds(remainingSeconds);
    }
  }, [sentAtParam]);

  // クールダウンタイマー
  useEffect(() => {
    if (cooldownSeconds > 0) {
      const timer = setTimeout(() => {
        setCooldownSeconds(cooldownSeconds - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldownSeconds]);

  const handleResendEmail = async () => {
    if (!email) {
      setError('メールアドレスが見つかりません。');
      return;
    }
    setLoading(true);
    setMessage('');
    setError('');
    try {
      await requestPasswordReset(email);
      setMessage('パスワードリセットメールを再送信しました。');
      setCooldownSeconds(60); // 60秒のクールダウン

      // URLを更新して新しい送信時刻を記録
      const newSentAt = Date.now();
      const newUrl = `/auth/password-reset-sent?email=${encodeURIComponent(email)}&sentAt=${newSentAt}`;
      router.replace(newUrl);
    } catch (err: unknown) {
      let errorMessage = 'メールの再送信に失敗しました。';

      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response: { status?: number; data?: { detail?: string } } };
        if (axiosError.response?.status === 429) {
          errorMessage = 'しばらく時間をおいてから再度お試しください。';
        } else if (axiosError.response?.data?.detail) {
          errorMessage = axiosError.response.data.detail;
        }
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const isButtonDisabled = loading || cooldownSeconds > 0 || !email;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center text-gray-900">パスワードリセットメール送信完了</h1>

        <div className="bg-blue-50 border border-blue-200 text-blue-600 px-4 py-3 rounded relative" role="alert">
          <p className="text-sm">
            {email ? `${email} ` : '指定されたメールアドレス'}にパスワードリセットメールを送信しました。メール内のリンクをクリックして、新しいパスワードを設定してください。
          </p>
        </div>

        {message && <p className="text-sm text-green-600">{message}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            メールが届かない場合は、以下をご確認ください：
          </p>
          <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
            <li>迷惑メールフォルダをチェックしてください</li>
            <li>メールアドレスが正しく入力されているか確認してください</li>
            <li>しばらく待ってからもう一度確認してください</li>
          </ul>
        </div>

        <div className="text-center">
          <button
            onClick={handleResendEmail}
            disabled={isButtonDisabled}
            className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading
              ? '送信中...'
              : cooldownSeconds > 0
                ? `再送信可能まで ${cooldownSeconds}秒`
                : 'パスワードリセットメールを再送信'}
          </button>
        </div>

        <div className="text-sm text-center space-y-2">
          <p>
            <Link href="/auth/login" className="text-blue-600 hover:text-blue-500">
              ログインページに戻る
            </Link>
          </p>
          <p>
            <Link href="/auth/forgot-password" className="text-blue-600 hover:text-blue-500">
              別のメールアドレスでリセット
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function PasswordResetSentPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">読み込み中...</div>}>
      <PasswordResetSentContent />
    </Suspense>
  );
} 

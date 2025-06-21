'use client'; // Mark this as a Client Component

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getApiUrl } from '@/utils/api';

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState('verifying'); // 'verifying', 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setErrorMessage('確認トークンが見つかりません。');
      return;
    }

    const verifyEmail = async () => {
      setStatus('verifying');
      try {
        // 共通関数を使用してAPI URLを取得
        const apiUrl = getApiUrl();
        console.log(`Verifying token: ${token} with API: ${apiUrl}/v1/auth/verify-email`); // デバッグログ

        const response = await fetch(`${apiUrl}/v1/auth/verify-email?token=${token}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'メール認証に失敗しました');
        }

        console.log("Verification successful"); // デバッグログ
        setStatus('success');

        // 3秒後にログインページへリダイレクト
        setTimeout(() => {
          router.push('/auth/login');
        }, 3000);

      } catch (error: unknown) {
        console.error('Email verification failed:', error); // デバッグログ
        setStatus('error');
        setErrorMessage(
          (error instanceof Error ? error.message : null) || 
          'メールアドレスの確認中に予期せぬエラーが発生しました。'
        );
      }
    };

    verifyEmail();
  }, [token, router]); // tokenが変わるたびに実行

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md text-center">
        <h1 className="text-2xl font-bold text-gray-900">メールアドレスの確認</h1>

        {status === 'verifying' && (
          <div>
            <p className="text-gray-600">メールアドレスを確認中です...</p>
            {/* ここにスピナーなどのローディング表示を追加すると良い */}
            <div className="mt-4 w-8 h-8 border-4 border-blue-500 border-solid border-t-transparent rounded-full animate-spin mx-auto"></div>
          </div>
        )}

        {status === 'success' && (
          <div className="text-green-600">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="font-semibold">メールアドレスの確認が完了しました！</p>
            <p className="mt-2 text-sm text-gray-500">数秒後にログインページに移動します...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="text-red-600">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="font-semibold">確認に失敗しました</p>
            <p className="mt-2 text-sm">{errorMessage}</p>
            <button
              onClick={() => router.push('/auth/register')}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors duration-200"
            >
              登録ページに戻る
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// SuspenseでラップしてClient Componentをレンダリング
export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <VerifyEmailContent />
    </Suspense>
  );
}

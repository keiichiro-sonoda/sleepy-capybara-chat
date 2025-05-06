'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import axios from 'axios';
import { getApiUrl } from '@/utils/api';

export default function ResendConfirmationPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [nextAvailable, setNextAvailable] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setNextAvailable(null);
    setIsLoading(true);

    try {
      const response = await axios.post(`${getApiUrl()}/v1/auth/resend-confirmation`, {
        email
      });

      setSuccess('確認メールを再送信しました。メールボックスをご確認ください。');
      setEmail(''); // Clear the form
    } catch (error: any) {
      console.error('Resend confirmation error:', error);
      if (error.response) {
        if (error.response.status === 429) {
          const detail = error.response.data.detail;
          setError(detail.message || '再送信の回数制限に達しました。');
          if (detail.next_available) {
            setNextAvailable(detail.next_available);
          }
        } else if (error.response.data.detail) {
          setError(error.response.data.detail);
        } else {
          setError('確認メールの再送信に失敗しました。もう一度お試しください。');
        }
      } else {
        setError('確認メールの再送信中にエラーが発生しました。');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center text-gray-900">確認メールの再送信</h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded relative" role="alert">
            <p className="text-sm">{error}</p>
            {nextAvailable && (
              <p className="text-sm mt-2">
                次回の再送信可能時間: {nextAvailable}
              </p>
            )}
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 text-green-600 px-4 py-3 rounded relative" role="alert">
            <p className="text-sm">{success}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              メールアドレス
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
              isLoading ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'
            } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
          >
            {isLoading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                送信中...
              </>
            ) : (
              '確認メールを再送信'
            )}
          </button>
        </form>

        <div className="text-sm text-center space-y-2">
          <p>
            <Link href="/auth/login" className="text-blue-600 hover:text-blue-500">
              ログインページに戻る
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

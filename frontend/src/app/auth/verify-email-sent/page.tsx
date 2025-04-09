'use client';

import Link from 'next/link';

export default function VerifyEmailSentPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center text-gray-900">メール確認のお願い</h1>

        <div className="bg-blue-50 border border-blue-200 text-blue-600 px-4 py-3 rounded relative" role="alert">
          <p className="text-sm">
            登録いただいたメールアドレスに確認メールを送信しました。メール内のリンクをクリックして、アカウントを有効化してください。
          </p>
        </div>

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

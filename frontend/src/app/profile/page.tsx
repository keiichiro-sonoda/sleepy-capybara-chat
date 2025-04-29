'use client';

import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useAuth } from '@/hooks/useAuth';
import TokenUsage from '@/components/user/TokenUsage';

// Shadcn UI components
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function ProfileContent() {
  const { user } = useAuth();
  const router = useRouter();

  if (!user) {
    return <div className="flex justify-center items-center h-screen">読み込み中...</div>;
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">プロフィール</h1>
        <p className="text-muted-foreground">あなたのアカウント情報とトークン使用量を確認できます。</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* プロフィール情報 */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>アカウント情報</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">メールアドレス</p>
                <p className="font-medium">{user.email}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">メール認証</p>
                <div className="flex items-center">
                  <Badge variant={user.is_verified ? "success" : "warning"}>
                    {user.is_verified ? '認証済み' : '未認証'}
                  </Badge>
                </div>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">ステータス</p>
                <div className="flex items-center">
                  <Badge variant="success">アクティブ</Badge>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button
                onClick={() => router.push('/chat')}
                className="w-full"
              >
                チャットに戻る
              </Button>
            </CardFooter>
          </Card>
        </div>

        {/* トークン使用量 */}
        <div className="lg:col-span-2">
          <TokenUsage />
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}

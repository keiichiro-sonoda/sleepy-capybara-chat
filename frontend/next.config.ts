import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 本番ビルド用の設定
  output: "standalone", // Docker本番環境で必要
  
  // 開発環境での型チェック無効化（必要に応じて）
  typescript: {
    ignoreBuildErrors: false,
  },
  
  // ESLintエラーでビルドを停止しない（必要に応じて）
  eslint: {
    ignoreDuringBuilds: false,
  },
};

export default nextConfig;

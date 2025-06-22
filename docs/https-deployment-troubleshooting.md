# HTTPS環境デプロイメント トラブルシューティングガイド

## 概要

ローカル開発環境（HTTP）からグローバル本番環境（HTTPS + Cloudflare Tunnel）への移行時に発生する問題点と解決策をまとめたガイドです。

## 環境の違い

### ローカル開発環境

- **プロトコル**: HTTP
- **ドメイン**: localhost
- **プロキシ**: なし（直接通信）
- **SSL/TLS**: なし
- **CORS**: シンプル（same-origin）

### グローバル本番環境

- **プロトコル**: HTTPS
- **ドメイン**: your-domain.com
- **プロキシ**: Cloudflare Tunnel
- **SSL/TLS**: Cloudflare管理のSSL証明書
- **CORS**: Cross-origin制約

## 現在のCloudflare Tunnel設定

```text
1. your-domain.com/api → http://backend:8000
2. your-domain.com/*   → http://frontend:3000
```

**重要**: Cloudflare Tunnelのパスルーティングでは、**リストの順序が重要**です。より具体的なパス（例: `/api`）を、より汎用的なパス（例: `*`）よりも**上に**配置する必要があります。`api`のパスが先に評価されるようにしないと、全てのリクエストが`*`にマッチしてしまい、APIリクエストがバックエンドに到達しません。

## 発生する問題と原因・解決策

### 1. Mixed Content エラー

**症状**:

```text
Mixed Content: The page at 'https://your-domain.com/chat' was loaded over HTTPS, but requested an insecure XMLHttpRequest endpoint 'http://your-domain.com/api/v1/models/'. This request has been blocked.
```

**原因**:

- HTTPSサイトからHTTPエンドポイントへのリクエストがブラウザによってブロックされる
- サーバー側でのリダイレクト時にHTTPSからHTTPにダウングレードが発生

**確認方法**:

```bash
curl -v https://your-domain.com/api/v1/models
# 307リダイレクトでHTTPに変換されていないかチェック
```

**解決策**:

1. **フロントエンド側**: 全APIエンドポイントに末尾スラッシュ追加
2. **バックエンド側**: HTTPS強制設定、プロキシヘッダー信頼設定
3. **Cloudflare側**: SSL/TLS設定確認

### 1.1. 末尾スラッシュによるMixed Content問題（重要な発見）

**発見した事実**:

- **末尾スラッシュあり**: `/v1/auth/login/` → Mixed Content エラー発生、HTTPリダイレクト
- **末尾スラッシュなし**: `/v1/auth/login` → **正常動作**、HTTPS維持

**実際のエラーログ**:

```text
Mixed Content: The page at 'https://your-domain.com/auth/login' was loaded over HTTPS, but requested an insecure XMLHttpRequest endpoint 'http://your-domain.com/api/v1/auth/login'. This request has been blocked.
```

**原因分析**:

1. **FastAPI側の問題**: FastAPIは末尾スラッシュの正規化を行う際、リダイレクトを発生させる
2. **Cloudflare Tunnel処理**: リダイレクト処理時にHTTPSからHTTPにダウングレードが発生
3. **パス処理の違い**: 末尾スラッシュの有無でサーバー側の処理パスが異なる

**対処法**:

- **即座の解決**: 全てのAPIエンドポイントから末尾スラッシュを削除
- **根本的解決**: FastAPIのリダイレクト設定またはCloudflare Tunnelの設定見直し

**確認コマンド**:

```bash
# 末尾スラッシュなしでテスト
curl -v https://your-domain.com/api/v1/auth/login -X POST

# 末尾スラッシュありでテスト  
curl -v https://your-domain.com/api/v1/auth/login/ -X POST
```

### 1.2. エンドポイント別の末尾スラッシュ要件（更なる重要発見）

**発見した事実**:

- **modelsエンドポイント**: `/v1/models/` （末尾スラッシュ**必要**） → ✅ 正常動作
- **modelsエンドポイント**: `/v1/models` （末尾スラッシュなし） → ❌ 307リダイレクト → Mixed Content
- **その他エンドポイント**: `/v1/auth/login` （末尾スラッシュなし） → ✅ 正常動作

**原因**:

- **FastAPIルーター設計の違い**:

  ```python
  # modelsルーター: ルートパス使用
  @router.get("/", response_model=list[AIModel])  # /models + / = /models/
  
  # authルーター: 直接パス使用  
  @router.post("/login", response_model=Token)    # /auth + /login = /auth/login
  ```

**教訓**:

- **エンドポイントごとに個別テストが必要**
- **バックエンドのルーター設計を理解する重要性**
- **一律の対応では解決しない場合がある**

**テスト結果**:

```bash
# ✅ 正常: modelsエンドポイント（末尾スラッシュあり）
curl -v https://your-domain.com/api/v1/models/ → HTTP/2 200

# ❌ 失敗: modelsエンドポイント（末尾スラッシュなし）  
curl -v https://your-domain.com/api/v1/models → HTTP/2 307 → http://...models/
```

### 2. 404 Not Found エラー（API エンドポイント）

**症状**:

```text
POST https://your-domain.com/api/v1/auth/login/ 404 (Not Found)
```

**原因**:

- Cloudflare Tunnelのパス設定とバックエンドのルーティング不一致
- FastAPIの`root_path`設定不足
- パス正規化の問題

**確認方法**:

```bash
# 各エンドポイントの存在確認
curl -v https://your-domain.com/api/v1/auth/login/
curl -v https://your-domain.com/api/v1/models/
curl -v https://your-domain.com/api/docs  # FastAPI docs
```

**解決策**:

1. **FastAPI設定**: `root_path="/api"`設定
2. **Cloudflare設定**: パス設定の見直し
3. **エンドポイント確認**: 全エンドポイントの動作テスト

### 3. CORS設定問題

**症状**:

```text
Access to XMLHttpRequest at 'https://your-domain.com/api/...' from origin 'https://your-domain.com' has been blocked by CORS policy
```

**原因**:

- CORS設定にHTTPSドメインが含まれていない
- Cloudflare経由でのOriginヘッダー変更

**確認方法**:

```bash
# Originヘッダー付きでリクエスト
curl -H "Origin: https://your-domain.com" -v https://your-domain.com/api/v1/models/
```

### 4. 認証トークン問題

**症状**:

- ログイン後のトークンが保存されない
- API認証が失敗する

**原因**:

- HTTPS環境でのCookie/LocalStorage設定問題
- トークンの送信ヘッダー問題

**確認方法**:

- ブラウザのDevToolsでLocalStorageとネットワークリクエスト確認

### 5. プロキシ設定問題

**症状**:

- 内部サーバーエラー
- タイムアウト

**原因**:

- Cloudflare TunnelとDockerネットワーク間の通信問題
- ホスト名解決問題

**確認方法**:

```bash
# Docker内部からの接続テスト
docker exec -it backend curl http://localhost:8000/api/v1/models/
```

## トラブルシューティング手順

### Step 1: ネットワーク疎通確認

```bash
# 1. 基本的な接続確認
ping your-domain.com

# 2. SSL証明書確認
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# 3. Cloudflare Tunnel状態確認
docker logs cloudflared
```

### Step 2: API エンドポイント確認

```bash
# 1. ルートエンドポイント
curl https://your-domain.com/api/

# 2. 認証不要エンドポイント
curl https://your-domain.com/api/v1/models/

# 3. FastAPI docs
curl https://your-domain.com/api/docs

# 4. ヘルスチェック
curl https://your-domain.com/api/health
```

### Step 3: ブラウザデバッグ

1. **Console**: Mixed Contentエラー確認
2. **Network**: リクエストURL、ステータスコード確認
3. **Application**: LocalStorage、Cookie確認
4. **Security**: SSL証明書、Mixed Content警告確認

### Step 4: バックエンドログ確認

```bash
# Docker環境
docker logs backend

# 特定のログレベル
docker logs backend 2>&1 | grep ERROR
```

## 設定チェックリスト

### フロントエンド (.env.local)

- [ ] `NEXT_PUBLIC_API_URL=https://your-domain.com/api`
- [ ] 全APIエンドポイントに末尾スラッシュ

### バックエンド (app/main.py)

- [ ] `root_path="/api"`設定
- [ ] `TrustedHostMiddleware`設定
- [ ] CORS設定にHTTPSドメイン追加

### Cloudflare Tunnel

- [ ] パス設定: `/api → http://backend:8000`
- [ ] SSL/TLS設定: Full (strict)
- [ ] DNS設定確認

### Docker設定

- [ ] ネットワーク設定確認
- [ ] ポート設定確認
- [ ] 環境変数設定確認

## よくある解決方法

### 1. キャッシュクリア

```bash
# ブラウザキャッシュクリア
# Ctrl+Shift+R (Windows/Linux)
# Cmd+Shift+R (Mac)

# Cloudflareキャッシュクリア
# Cloudflare Dashboard > Caching > Purge Everything
```

### 2. サービス再起動

```bash
# Docker環境全体再起動
docker-compose down && docker-compose up -d

# 特定のサービス再起動
docker-compose restart backend
docker-compose restart frontend
```

### 3. 設定の段階的確認

1. ローカルHTTP環境で正常動作確認
2. HTTPSエンドポイントをcurlで直接テスト
3. フロントエンドからのAPIアクセステスト
4. 認証フロー全体のテスト

## 次のアクション

現在の問題（ログイン404エラー）を解決するための具体的な手順：

1. **FastAPI docs確認**: `https://your-domain.com/api/docs`にアクセス可能か
2. **エンドポイント一覧確認**: 利用可能なエンドポイントの確認
3. **バックエンドログ確認**: 404エラーの詳細確認
4. **パス設定見直し**: Cloudflare Tunnelとバックエンドの設定一致確認

## 参考リンク

- [FastAPI behind a proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/)
- [Cloudflare Tunnel documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Mixed Content - Web Security](https://developer.mozilla.org/en-US/docs/Web/Security/Mixed_content)

## 重要な教訓

### 末尾スラッシュの重要性

**教訓**: HTTPS環境では末尾スラッシュの有無が重大な影響を及ぼす

**学んだこと**:

1. **FastAPI + Cloudflare Tunnel環境**: 末尾スラッシュがあるとHTTPリダイレクトが発生しMixed Contentエラーになる
2. **デバッグの重要性**: 小さな変更（スラッシュの追加/削除）でも大きな影響がある
3. **一貫性の重要性**: 全てのエンドポイントで同じパターンを使用する

**ベストプラクティス**:

- HTTPS環境では末尾スラッシュを使わない
- 変更時は全てのエンドポイントで一貫性を保つ
- 各変更の影響を個別にテストする
- 問題解決のプロセスを詳細に記録する

**今後の参考**:

- 他のプロキシ環境でも同様の問題が起こる可能性がある
- パス正規化の動作は環境によって異なることを認識する
- リダイレクト処理がHTTPSコンテキストを維持しない場合がある

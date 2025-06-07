# Sleepy Capybara Chat - ストリーミング実装の技術解説

## 概要

Sleepy Capybara ChatアプリケーションにはOllama APIを利用したAIチャット機能が実装されています。この文書では、リアルタイムでAIの応答を表示する「ストリーミングモード」の実装方法について詳細に解説します。

## ストリーミングとは

ストリーミングモードでは、AIの応答が生成されるたびに少しずつクライアントに送信され、ユーザーはAIの「思考プロセス」をリアルタイムで見ることができます。これは以下の利点があります：

- **即時フィードバック**: ユーザーは応答の全体が完成する前に内容の確認を始められる
- **自然な対話感**: 人間同士の会話のように、相手が考えている様子を見ることができる
- **長い応答での体験向上**: 特に長文の応答でユーザーの待ち時間の不満を軽減できる

## 技術的な実装

### 1. バックエンド実装 (FastAPI)

#### 1.1 スキーマ定義

```python
# backend/app/schemas/chat.py
class MessageCreate(MessageBase):
    stream: bool = False  # ストリーミングモードフラグ、デフォルトはFalse
```

#### 1.2 ストリーミングエンドポイント

FastAPIの`StreamingResponse`を使用して、Server-Sent Events (SSE) 形式でデータをストリーミングします：

```python
# backend/app/api/v1/chat/chat.py
from fastapi.responses import StreamingResponse
import json

@router.post("/sessions/{session_id}/messages")
async def create_message(
    session_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ... 省略 ...
    
    # ストリーミングモードの場合
    if message.stream:
        return StreamingResponse(
            _stream_chat_response(
                session_id, request_data, settings.OLLAMA_API_BASE_URL, db
            ),
            media_type="text/event-stream",
        )
    
    # 非ストリーミングモードの場合
    # ... 省略 ...
```

#### 1.3 ストリーミング処理関数

非同期ジェネレータを使って、Ollamaからのストリーミングレスポンスをクライアントにリレーします：

```python
async def _stream_chat_response(session_id, request_data, ollama_api_base_url, db):
    complete_response = ""
    
    # ストリーム開始イベントを送信
    yield "data: " + json.dumps({"event": "start"}) + "\n\n"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST", f"{ollama_api_base_url}/api/chat", json=request_data, timeout=300.0
        ) as response:
            # エラー処理
            if response.status_code != 200:
                # ... 省略 ...
            
            # Ollamaからのストリーミングレスポンスを処理
            async for line in response.aiter_lines():
                if not line: continue
                
                try:
                    data = json.loads(line)
                    
                    # 応答チャンクの処理
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        complete_response += chunk
                        # クライアントにチャンクを送信
                        yield "data: " + json.dumps(
                            {"event": "chunk", "content": chunk}
                        ) + "\n\n"
                    
                    # 応答完了時の処理
                    if data.get("done", False):
                        # DBに保存
                        ai_message = Message(
                            session_id=session_id,
                            role="assistant",
                            content=complete_response,
                        )
                        db.add(ai_message)
                        db.commit()
                        
                        # 完了イベント送信
                        yield "data: " + json.dumps(
                            {
                                "event": "done",
                                "content": complete_response,
                                "session_id": session_id,
                            }
                        ) + "\n\n"
                        break
                    
                    # 少し待機してクライアントに処理時間を与える
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    # エラーハンドリング
                    # ... 省略 ...
```

### 2. フロントエンド実装 (Next.js)

#### 2.1 API関数

ストリーミングAPIを呼び出すための関数：

```typescript
// frontend/src/utils/api.ts
export const sendChatMessageStreaming = async (
  sessionId: number, 
  content: string, 
  onChunk: (chunk: string) => void,
  onComplete: (fullResponse: string) => void,
  onError: (error: string) => void
): Promise<void> => {
  const token = localStorage.getItem('token');
  if (!token) {
    throw new Error('認証が必要です');
  }

  try {
    const apiUrl = `${getApiUrl()}/v1/chat/sessions/${sessionId}/messages`;
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        content,
        role: "user",
        stream: true
      })
    });

    // レスポンスストリームの処理
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    // ストリームからデータを読み取り続ける
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      // バッファに追加
      buffer += decoder.decode(value, { stream: true });
      
      // バッファを行に分割して処理
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (!line.trim() || !line.startsWith('data: ')) continue;
        
        try {
          // イベントデータをパース
          const eventData = JSON.parse(line.substring(6));
          
          if (eventData.event === 'chunk' && eventData.content) {
            // チャンクを処理
            onChunk(eventData.content);
          } else if (eventData.event === 'done') {
            // 完了を処理
            onComplete(eventData.content);
            return;
          } else if (eventData.event === 'error') {
            // エラーを処理
            onError(eventData.message || 'Unknown error');
            return;
          }
        } catch (e) {
          console.error('Error parsing event data:', e, line);
        }
      }
    }
  } catch (error) {
    console.error('Error in streaming request:', error);
    onError(error instanceof Error ? error.message : String(error));
  }
};
```

#### 2.2 UIコンポーネント

ストリーミングモードを切り替えるトグルボタン：

```tsx
// frontend/src/components/chat/ChatHeader.tsx
{onToggleStreaming && (
  <button
    onClick={onToggleStreaming}
    className={`px-3 py-1 rounded text-sm ${
      useStreaming 
        ? 'bg-blue-100 text-blue-700' 
        : 'bg-gray-100 text-gray-700'
    }`}
    title={useStreaming ? 'ストリーミングモード: ON' : 'ストリーミングモード: OFF'}
  >
    {useStreaming ? 'ストリーム' : '一括'}
  </button>
)}
```

ストリーミング中の視覚効果：

```tsx
// frontend/src/components/chat/ChatMessages.tsx
<p className="whitespace-pre-wrap">
  {message.content}
  {message.isStreaming && (
    <span className="inline-block w-2 h-4 ml-1 bg-gray-500 animate-pulse" />
  )}
</p>
<div className={`text-xs mt-1 ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
  {message.timestamp.toLocaleTimeString()}
  {message.isStreaming && ' (ストリーミング中...)'}
</div>
```

#### 2.3 メッセージ送信ロジック

```tsx
// frontend/src/app/chat/page.tsx
if (useStreaming) {
  // ストリーミングモードでのメッセージ送信
  // 最初に空のアシスタントメッセージを追加
  const tempAssistantId = (Date.now() + 1).toString();
  const assistantMessage: Message = {
    id: tempAssistantId,
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    isStreaming: true // ストリーミング中フラグを設定
  };
  
  setMessages(prev => [...prev, assistantMessage]);
  
  // ストリーミングリクエストを送信
  await sendChatMessageStreaming(
    sessionId!,
    content,
    // チャンク受信時のコールバック - メッセージを逐次更新
    (chunk: string) => {
      setMessages(prev => prev.map(msg => 
        msg.id === tempAssistantId 
          ? { ...msg, content: msg.content + chunk } 
          : msg
      ));
    },
    // 完了時のコールバック
    (fullResponse: string) => {
      setMessages(prev => prev.map(msg => 
        msg.id === tempAssistantId 
          ? { ...msg, content: fullResponse, isStreaming: false } 
          : msg
      ));
      setIsLoading(false);
    },
    // エラー時のコールバック
    (errorMsg: string) => {
      setError(`AIからの応答の取得に失敗しました: ${errorMsg}`);
      setMessages(prev => prev.map(msg => 
        msg.id === tempAssistantId 
          ? { ...msg, content: 'エラーが発生しました', isStreaming: false } 
          : msg
      ));
      setIsLoading(false);
    }
  );
} else {
  // 非ストリーミングモード（従来の実装）
  // ...
}
```

## データフロー

ストリーミングモードでのデータフローは以下の通りです：

1. **ユーザー**: メッセージを送信
2. **フロントエンド**: 
   - 空のアシスタントメッセージを作成（ストリーミング中フラグON）
   - バックエンドのストリーミングAPIにリクエスト送信
3. **バックエンド**:
   - FastAPIがリクエストを受け取り、StreamingResponseを初期化
   - Ollama APIにストリーミングリクエストを送信
   - Ollamaからのレスポンスチャンクを受け取り次第、SSE形式でフロントエンドに転送
4. **フロントエンド**:
   - 各チャンクを受信するたびにアシスタントメッセージの内容を更新
   - 完了イベントを受信したらストリーミング中フラグをOFFに
5. **バックエンド**:
   - 応答が完了したら、完全な応答をデータベースに保存

## ストリーミングモードと非ストリーミングモードの切り替え

ユーザーは画面右上のトグルボタンでモードを切り替えることができます：

- **ストリーミングモード**: AIの応答が生成されるたびに逐次表示
- **非ストリーミングモード**: AIの応答が完全に生成された後に一括表示

内部的には、`useStreaming` 状態フラグに基づいて処理方法が切り替わります：

```tsx
const [useStreaming, setUseStreaming] = useState(true);

// 切り替え関数
const toggleStreamingMode = () => {
  setUseStreaming(prev => !prev);
};
```

## 技術的なポイント

1. **Server-Sent Events (SSE)**: HTTP接続を開いたままサーバーからクライアントに一方向のイベントを送信するための標準
2. **非同期ストリーミング処理**: FastAPIの非同期機能とジェネレータを活用
3. **状態管理**: React状態更新を使った効率的なUIの更新
4. **エラーハンドリング**: ストリームの各段階でのエラー処理

## 参考資料

- [Ollama API ドキュメント](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [Server-Sent Events の使用](https://developer.mozilla.org/ja/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [fetch API のストリーミングレスポンス](https://developer.mozilla.org/ja/docs/Web/API/Streams_API) 

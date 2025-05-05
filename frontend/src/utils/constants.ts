// モデルの型定義
export type AIModel = {
    id: string;
    name: string;
    provider: "ollama" | "openai";
    thinking_mode?: "none" | "optional" | "forced"; // 思考モードサポート状況を追加 (オプショナル)
}; 

// モデルの型定義
export type AIModel = {
    id: string;
    name: string;
    provider: "ollama" | "openai";
}; 

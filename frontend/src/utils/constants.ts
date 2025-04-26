// 利用可能なモデルのリスト
export const AVAILABLE_MODELS: AIModel[] = [
    { id: "llama3", name: "Llama 3", provider: "ollama" },
    { id: "gpt-4.1-nano", name: "GPT-4.1 Nano", provider: "openai" },
];

// モデルの型定義
export type AIModel = {
    id: string;
    name: string;
    provider: "ollama" | "openai";
}; 

"use client";

import * as React from "react";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose,   // 明示的に閉じるボタン用
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Trash2 } from "lucide-react"; // 削除アイコン

import { UserWithTokenLimits, TokenLimit, MetricType, PeriodUnit } from "@/lib/types";
import { createTokenLimit, updateTokenLimit, deleteTokenLimit } from "@/lib/api/admin";
import { getAvailableModels } from "@/utils/api"; // API関数をインポート
import { AIModel } from "@/utils/constants"; // AIModel型をインポート

// MetricTypeとPeriodUnitのEnum値を配列として取得（Selectコンポーネント用）
const metricTypeOptions = Object.values(MetricType);
const periodUnitOptions = Object.values(PeriodUnit);

// 仮の利用可能モデルリスト（将来的にはAPIから取得）
// const availableModels = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "claude-2", "claude-3-opus", "claude-3-sonnet"];

interface EditTokenLimitsDialogProps {
  user: UserWithTokenLimits | null; // 編集対象のユーザー
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onLimitsUpdate: () => void; // 制限更新後にテーブルを再読み込みするためのコールバック
}

export function EditTokenLimitsDialog({
  user,
  isOpen,
  onOpenChange,
  onLimitsUpdate,
}: EditTokenLimitsDialogProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 編集中のトークン制限を管理するためのstate（ユーザーの既存の制限で初期化）
  const [currentLimits, setCurrentLimits] = useState<Partial<TokenLimit>[]>([]);
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);

  // 元の制限データを保持（リセット用）
  const [originalLimits, setOriginalLimits] = useState<Partial<TokenLimit>[]>([]);

  useEffect(() => {
    if (user?.token_limits) {
      // 既存の制限をディープコピーして編集用に設定
      const limits = JSON.parse(JSON.stringify(user.token_limits));
      setCurrentLimits(limits);
      setOriginalLimits(limits); // 元のデータも保存
    } else {
      setCurrentLimits([]);
      setOriginalLimits([]);
    }
  }, [user]);

  useEffect(() => {
    const fetchModels = async () => {
      if (isOpen && availableModels.length === 0 && !modelsLoading) { // ダイアログが開き、モデル未取得で、ロード中でもない場合
        setModelsLoading(true);
        setModelsError(null);
        try {
          const models = await getAvailableModels();
          setAvailableModels(models);
        } catch (err) {
          setModelsError(err instanceof Error ? err.message : "Failed to load models");
        } finally {
          setModelsLoading(false);
        }
      }
    };
    fetchModels();
  }, [isOpen, availableModels.length, modelsLoading]); // isOpen, modelsLoading, availableModels.length を依存配列に追加

  if (!user) return null;

  // モーダルが閉じる時の処理
  const handleOpenChange = (open: boolean) => {
    if (!open) {
      // モーダルを閉じる時は元のデータにリセット
      setCurrentLimits(JSON.parse(JSON.stringify(originalLimits)));
      setError(null);
    }
    onOpenChange(open);
  }; // ユーザーが選択されていない場合は何も表示しない

  const handleAddNewLimit = () => {
    // 新しい空の制限オブジェクトを追加（デフォルト値などを設定）
    // IDはサーバー側で採番されるのでここでは不要
    const newLimitTemplate: Partial<TokenLimit> = {
      user_id: user.id,
      model_id: "", // デフォルトのモデルIDや空文字
      model_name: "", // 表示用
      metric_type: MetricType.TOKENS,
      limit_value: 0,
      period_unit: PeriodUnit.MONTH,
      period_value: 1,
    };
    setCurrentLimits([...currentLimits, newLimitTemplate]);
  };

  const handleLimitChange = (
    index: number,
    field: keyof TokenLimit,
    value: string | number | MetricType | PeriodUnit
  ) => {
    const updatedLimits = [...currentLimits];
    const limitToUpdate = { ...updatedLimits[index] } as Partial<TokenLimit>; // 型アサーション

    if (field === 'limit_value' || field === 'period_value') {
      // 空文字列の場合は0として扱う（表示は空文字列のまま）
      const stringValue = value as string;
      if (stringValue === '') {
        (limitToUpdate as Record<string, unknown>)[field] = '';
      } else {
        const numValue = parseInt(stringValue, 10);
        (limitToUpdate as Record<string, unknown>)[field] = isNaN(numValue) ? 0 : numValue;
      }
    } else if (field === 'model_name') {
      // モデル名が変更された場合、対応するmodel_idのみ設定
      const selectedModel = availableModels.find(m => m.name === value);
      if (selectedModel) {
        limitToUpdate.model_id = selectedModel.id; // これはAIModelIdのenum値
        // model_nameはAPI送信時に除外されるため、ここでは設定しない
      }
    } else {
      (limitToUpdate as Record<string, unknown>)[field] = value;
    }
    updatedLimits[index] = limitToUpdate;
    setCurrentLimits(updatedLimits);
  };

  // 数値フィールドのフォーカスが外れた時の処理
  const handleNumberBlur = (
    index: number,
    field: 'limit_value' | 'period_value'
  ) => {
    const updatedLimits = [...currentLimits];
    const limitToUpdate = { ...updatedLimits[index] } as Partial<TokenLimit>;

    // 空文字列の場合は適切なデフォルト値を設定
    const currentValue = (limitToUpdate as Record<string, unknown>)[field];
    if (currentValue === '' || currentValue === null || currentValue === undefined) {
      (limitToUpdate as Record<string, unknown>)[field] = field === 'period_value' ? 1 : 0;
      updatedLimits[index] = limitToUpdate;
      setCurrentLimits(updatedLimits);
    }
  };

  const handleRemoveLimit = async (index: number, limitId?: number) => {
    if (limitId) { // 既存の制限の場合、APIで削除
      setIsLoading(true);
      try {
        await deleteTokenLimit(limitId);
        onLimitsUpdate(); // 親コンポーネントに更新を通知して再描画
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete limit");
      } finally {
        setIsLoading(false);
      }
    }
    // UI上から制限を削除（API削除が成功した場合も、失敗した場合もUIは更新する形。別途エラー表示で対応）
    const updatedLimits = currentLimits.filter((_, i) => i !== index);
    setCurrentLimits(updatedLimits);
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    setError(null);
    try {
      for (const limit of currentLimits) {
        if (limit.id) { // IDがあれば既存の制限なので更新
          // user_id とmodel_nameを除いた更新データを準備
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { model_name: _, ...updateData } = limit;
          if (Object.keys(updateData).length > 0) { // 何か変更がある場合のみ更新
            await updateTokenLimit(limit.id, updateData as Partial<Omit<TokenLimit, 'id' | 'user_id'>>);
          }
        } else { // IDがなければ新しい制限なので作成
          await createTokenLimit(limit as Omit<TokenLimit, 'id'>);
        }
      }
      onLimitsUpdate(); // 親コンポーネントに更新を通知
      setOriginalLimits(JSON.parse(JSON.stringify(currentLimits))); // 保存後は現在の状態を元データとして設定
      onOpenChange(false); // モーダルを閉じる
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save limits");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Edit Token Limits for {user.email}</DialogTitle>
          <DialogDescription>
            Manage token usage limits for this user. Click save when you&apos;re done.
            {modelsLoading && <span className="text-xs text-muted-foreground mt-1 block">Loading available models...</span>}
            {modelsError && <span className="text-xs text-red-500 mt-1 block">Error loading models: {modelsError}</span>}
          </DialogDescription>
        </DialogHeader>

        {error && <p className="text-sm text-red-500 bg-red-50 p-3 rounded-md">Error: {error}</p>}

        <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto pr-2">
          {currentLimits.map((limit, index) => (
            <div key={limit.id || `new-${index}`} className="grid grid-cols-6 items-center gap-3 p-3 border rounded-md">
              <div className="col-span-5 grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor={`model_name-${index}`} className="text-xs">Model Name</Label>
                  <Select
                    value={limit.model_name || ""}
                    onValueChange={(value: string) => handleLimitChange(index, 'model_name', value)}
                    disabled={modelsLoading || !!modelsError} // モデルロード中やエラー時は無効化
                  >
                    <SelectTrigger id={`model_name-${index}`} className="mt-1">
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableModels.map(model => (
                        <SelectItem key={model.id} value={model.name}>{model.name}</SelectItem>
                      ))}
                      {/* ユーザーが既に入力済みのモデル名がAPIからのリストにない場合、それも選択肢として表示する */}
                      {limit.model_name && !availableModels.some(m => m.name === limit.model_name) && (
                        <SelectItem value={limit.model_name}>
                          {limit.model_name} (current)
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor={`limit_value-${index}`} className="text-xs">Limit Value</Label>
                  <Input
                    id={`limit_value-${index}`}
                    type="number"
                    value={typeof limit.limit_value === 'string' && limit.limit_value === '' ? '' : (limit.limit_value || 0)}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleLimitChange(index, 'limit_value', e.target.value)}
                    onBlur={() => handleNumberBlur(index, 'limit_value')}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor={`metric_type-${index}`} className="text-xs">Metric Type</Label>
                  <Select
                    value={limit.metric_type || MetricType.TOKENS}
                    onValueChange={(value: string) => handleLimitChange(index, 'metric_type', value as MetricType)}
                  >
                    <SelectTrigger id={`metric_type-${index}`} className="mt-1">
                      <SelectValue placeholder="Select metric" />
                    </SelectTrigger>
                    <SelectContent>
                      {metricTypeOptions.map(option => (
                        <SelectItem key={option} value={option}>{option}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor={`period_unit-${index}`} className="text-xs">Period Unit</Label>
                  <Select
                    value={limit.period_unit || PeriodUnit.MONTH}
                    onValueChange={(value: string) => handleLimitChange(index, 'period_unit', value as PeriodUnit)}
                  >
                    <SelectTrigger id={`period_unit-${index}`} className="mt-1">
                      <SelectValue placeholder="Select period unit" />
                    </SelectTrigger>
                    <SelectContent>
                      {periodUnitOptions.map(option => (
                        <SelectItem key={option} value={option}>{option}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor={`period_value-${index}`} className="text-xs">Period Value</Label>
                  <Input
                    id={`period_value-${index}`}
                    type="number"
                    value={typeof limit.period_value === 'string' && limit.period_value === '' ? '' : (limit.period_value || 1)}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleLimitChange(index, 'period_value', e.target.value)}
                    onBlur={() => handleNumberBlur(index, 'period_value')}
                    className="mt-1"
                  />
                </div>
              </div>
              <div className="col-span-1 flex justify-end">
                <Button variant="ghost" size="icon" onClick={() => handleRemoveLimit(index, limit.id)} disabled={isLoading}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        <Button variant="outline" onClick={handleAddNewLimit} className="w-full mt-2" disabled={isLoading}>
          Add New Limit Rule
        </Button>

        <DialogFooter className="mt-4">
          <DialogClose asChild>
            <Button type="button" variant="outline" disabled={isLoading}>Cancel</Button>
          </DialogClose>
          <Button type="button" onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 

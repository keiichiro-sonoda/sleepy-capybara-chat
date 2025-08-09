from enum import Enum as PyEnum


class MetricType(str, PyEnum):
    TOKENS = "tokens"


class PeriodUnit(str, PyEnum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


class AIModelId(PyEnum):
    QWEN3_8B = "qwen3:8b"
    GPT_4_1_NANO = "gpt-4.1-nano"
    GPT_5_NANO = "gpt-5-nano"
    # 他のモデルもAVAILABLE_MODELSに合わせてここに追加

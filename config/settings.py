import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

class Settings:
    # LiveKit配置
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")

    # Deepgram配置
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    DEEPGRAM_CONFIG: Dict = {
        "model": "nova-2-general",
        "language": "en-US",
        "smart_format": True,
        "punctuate": True,
        "endpointing": 25,
        "interim_results": True,
        "vad_events": True
    }

    # TTS配置
    TTS_CONFIG: Dict = {
        "model": "sonic-english",
        "voice": "694f9389-aac1-45b6-b726-9d9369183238",
        "speed": "slow",
        "emotion": ["curiosity:highest", "positivity:high"]
    }

    # LLM配置
    LLM_CONFIG: Dict = {
        "model": "gpt-4o-mini",
        "base_url": "https://api.zhizengzeng.com/v1"
    }

    # API价格配置（单位：美元）
    PRICE_CONFIG: Dict = {
        "LLM": {
            "INPUT_PRICE": 0.0015 / 1000,   # 每1k tokens的输入价格
            "OUTPUT_PRICE": 0.002 / 1000,    # 每1k tokens的输出价格
        },
        "TTS": {
            "PRICE": 0.015 / 1000,          # 每1k字符的价格
        },
        "STT": {
            "PRICE": 0.0059 / 60,           # 每秒的价格（转换自每分钟价格）
        },
        "VAD": {
            "PRICE": 0.0001 / 60,           # 每秒的价格（示例价格）
        }
    }

    # Supabase配置
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE: str = os.getenv("LOG_FILE", "agent.log")

settings = Settings()
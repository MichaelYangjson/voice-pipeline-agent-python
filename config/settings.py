import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

class Settings:
    # LiveKit配置
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")

    # TTS配置 - 固定值
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

    # Supabase配置
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE: str = os.getenv("LOG_FILE", "agent.log")

settings = Settings()
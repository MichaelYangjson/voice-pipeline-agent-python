from supabase import create_client, Client
from config.settings import settings
from utils.logger import setup_logger, logger


class SupabaseClient:
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )

    async def log_tts_usage(self, text: str, voice_id: str, model: str, duration: float):
        try:
            self.client.table('tts_logs').insert({
                'text': text,
                'voice_id': voice_id,
                'model': model,
                'duration': duration
            }).execute()
        except Exception as e:
            logger.error(f"Error logging TTS usage: {str(e)}")

    async def log_llm_usage(self, prompt: str, response: str, model: str, tokens: int, duration: float):
        try:
            self.client.table('llm_logs').insert({
                'prompt': prompt,
                'response': response,
                'model': model,
                'tokens_used': tokens,
                'duration': duration
            }).execute()
        except Exception as e:
            logger.error(f"Error logging LLM usage: {str(e)}")

    async def log_stt_usage(self, transcription: str, audio_duration: float, model: str, duration: float):
        try:
            self.client.table('stt_logs').insert({
                'transcription': transcription,
                'audio_duration': audio_duration,
                'model': model,
                'duration': duration
            }).execute()
        except Exception as e:
            logger.error(f"Error logging STT usage: {str(e)}")

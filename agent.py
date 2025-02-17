import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import silero, deepgram, openai
from livekit.plugins.cartesia import tts
from config.settings import settings
from config.prompts import SYSTEM_PROMPT
from database.supabase_client import SupabaseClient
from utils.logger import setup_logger, logger

db_client = SupabaseClient()


def prewarm(proc: JobProcess):
    """预热函数，加载VAD模型"""
    try:
        proc.userdata["vad"] = silero.VAD.load()
        logger.info("VAD model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading VAD model: {str(e)}")
        raise


async def setup_metrics_collector(agent: VoicePipelineAgent):
    @agent.on("metrics_collected")
    async def on_metrics_collected(metric_type: str, metrics: dict):
        if metric_type == "tts":
            await db_client.log_tts_usage(
                text=metrics.get("text", ""),
                voice_id=metrics.get("voice_id", ""),
                model=metrics.get("model", ""),
                duration=metrics.get("duration", 0.0)
            )
        elif metric_type == "llm":
            await db_client.log_llm_usage(
                prompt=metrics.get("prompt", ""),
                response=metrics.get("response", ""),
                model=metrics.get("model", ""),
                tokens=metrics.get("tokens_used", 0),
                duration=metrics.get("duration", 0.0)
            )
        elif metric_type == "stt":
            await db_client.log_stt_usage(
                transcription=metrics.get("text", ""),
                audio_duration=metrics.get("audio_duration", 0.0),
                model=metrics.get("model", ""),
                duration=metrics.get("duration", 0.0)
            )


async def entrypoint(ctx: JobContext):
    """主入口函数"""
    try:
        initial_ctx = llm.ChatContext().append(
            role="system",
            text=SYSTEM_PROMPT
        )

        logger.info(f"Connecting to room {ctx.room.name}")
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

        participant = await ctx.wait_for_participant()
        logger.info(f"Starting voice assistant for participant {participant.identity}")

        cartesia_tts = tts.TTS(**settings.TTS_CONFIG)

        agent = VoicePipelineAgent(
            vad=ctx.proc.userdata["vad"],
            stt=deepgram.STT(),
            llm=openai.LLM(**settings.LLM_CONFIG),
            tts=cartesia_tts,
            chat_ctx=initial_ctx,
        )

        await setup_metrics_collector(agent)
        agent.start(ctx.room, participant)
        await agent.say("Hey, what's your name", allow_interruptions=True)

    except Exception as e:
        logger.error(f"Error in entrypoint: {str(e)}")
        raise


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )

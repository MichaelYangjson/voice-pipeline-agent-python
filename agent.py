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
from livekit.agents.pipeline.agent import VoicePipelineAgent
from livekit.agents.metrics.base import LLMMetrics, STTMetrics, TTSMetrics, VADMetrics
from livekit.plugins import silero, deepgram, openai
from livekit.plugins.cartesia import tts
from config.settings import settings
from config.prompts import SYSTEM_PROMPT
from database.supabase_client import SupabaseClient
from utils.logger import setup_logger, logger
import asyncio
from livekit import rtc
from datetime import datetime

db_client = SupabaseClient()

# 定义价格常量
OPENAI_LLM_INPUT_PRICE = 0.0015 / 1000  # 每1k tokens的输入价格
OPENAI_LLM_OUTPUT_PRICE = 0.002 / 1000   # 每1k tokens的输出价格
OPENAI_TTS_PRICE = 0.015 / 1000          # 每1k字符的TTS价格
DEEPGRAM_STT_PRICE = 0.0059              # 每分钟的STT价格

def prewarm(proc: JobProcess):
    """预热函数，加载VAD模型"""
    try:
        proc.userdata["vad"] = silero.VAD.load()
        logger.info("VAD model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading VAD model: {str(e)}")
        raise


class UsageStats:
    def __init__(self):
        # STT 统计
        self.stt_count = 0
        self.stt_total_duration = 0.0
        self.stt_total_audio = 0.0
        self.stt_total_streaming = 0
        
        # TTS 统计
        self.tts_count = 0
        self.tts_total_duration = 0.0
        self.tts_total_chars = 0
        self.tts_total_audio = 0.0
        self.tts_total_ttfb = 0.0
        self.tts_cancelled = 0
        
        # LLM 统计
        self.llm_count = 0
        self.llm_total_duration = 0.0
        self.llm_total_ttft = 0.0
        self.llm_total_tokens = 0
        self.llm_prompt_tokens = 0
        self.llm_completion_tokens = 0
        self.llm_cancelled = 0
        
        # VAD 统计
        self.vad_total_idle = 0.0
        self.vad_total_inference = 0.0
        self.vad_inference_count = 0


def setup_usage_collector(agent):
    stats = UsageStats()
    
    def usage_collector(*args):
        if not args:
            return
            
        metrics_data = args[0]
        
        async def handle_metrics():
            try:
                # STT 使用统计
                if isinstance(metrics_data, STTMetrics):
                    stats.stt_count += 1
                    stats.stt_total_duration += metrics_data.duration
                    stats.stt_total_audio += metrics_data.audio_duration
                    if metrics_data.streamed:
                        stats.stt_total_streaming += 1
                    
                    logger.info(
                        f"Speech-to-Text Metrics [ID: {metrics_data.request_id}]:"
                        f"\n  Model: {metrics_data.label}"
                        f"\n  Processing Time: {metrics_data.duration:.2f}s"
                        f"\n  Audio Duration: {metrics_data.audio_duration:.2f}s"
                        f"\n  Streaming: {'Yes' if metrics_data.streamed else 'No'}"
                        f"\n  Error: {metrics_data.error if metrics_data.error else 'None'}"
                        f"\n  -------- Cumulative Stats --------"
                        f"\n  Total Calls: {stats.stt_count}"
                        f"\n  Avg Processing Time: {stats.stt_total_duration/stats.stt_count:.2f}s"
                        f"\n  Total Audio Processed: {stats.stt_total_audio:.2f}s"
                        f"\n  Streaming Requests: {stats.stt_total_streaming}"
                    )
                    
                # TTS 使用统计
                elif isinstance(metrics_data, TTSMetrics):
                    stats.tts_count += 1
                    stats.tts_total_duration += metrics_data.duration
                    stats.tts_total_chars += metrics_data.characters_count
                    stats.tts_total_audio += metrics_data.audio_duration
                    stats.tts_total_ttfb += metrics_data.ttfb
                    if metrics_data.cancelled:
                        stats.tts_cancelled += 1
                    
                    logger.info(
                        f"Text-to-Speech Metrics [ID: {metrics_data.request_id}]:"
                        f"\n  Model: {metrics_data.label}"
                        f"\n  Characters: {metrics_data.characters_count}"
                        f"\n  Processing Time: {metrics_data.duration:.2f}s"
                        f"\n  Audio Duration: {metrics_data.audio_duration:.2f}s"
                        f"\n  Time to First Byte: {metrics_data.ttfb:.2f}s"
                        f"\n  Streaming: {'Yes' if metrics_data.streamed else 'No'}"
                        f"\n  Cancelled: {'Yes' if metrics_data.cancelled else 'No'}"
                        f"\n  Error: {metrics_data.error if metrics_data.error else 'None'}"
                        f"\n  -------- Cumulative Stats --------"
                        f"\n  Total Calls: {stats.tts_count}"
                        f"\n  Total Characters: {stats.tts_total_chars}"
                        f"\n  Avg TTFB: {stats.tts_total_ttfb/stats.tts_count:.2f}s"
                        f"\n  Cancelled Requests: {stats.tts_cancelled}"
                    )
                    
                # LLM 使用统计
                elif isinstance(metrics_data, LLMMetrics):
                    stats.llm_count += 1
                    stats.llm_total_duration += metrics_data.duration
                    stats.llm_total_ttft += metrics_data.ttft
                    stats.llm_total_tokens += metrics_data.total_tokens
                    stats.llm_prompt_tokens += metrics_data.prompt_tokens
                    stats.llm_completion_tokens += metrics_data.completion_tokens
                    if metrics_data.cancelled:
                        stats.llm_cancelled += 1
                    
                    logger.info(
                        f"LLM Metrics [ID: {metrics_data.request_id}]:"
                        f"\n  Model: {metrics_data.label}"
                        f"\n  Processing Time: {metrics_data.duration:.2f}s"
                        f"\n  Time to First Token: {metrics_data.ttft:.2f}s"
                        f"\n  Tokens: {metrics_data.total_tokens} (Prompt: {metrics_data.prompt_tokens}, Completion: {metrics_data.completion_tokens})"
                        f"\n  Tokens/Second: {metrics_data.tokens_per_second:.1f}"
                        f"\n  Cancelled: {'Yes' if metrics_data.cancelled else 'No'}"
                        f"\n  Error: {metrics_data.error if metrics_data.error else 'None'}"
                        f"\n  -------- Cumulative Stats --------"
                        f"\n  Total Calls: {stats.llm_count}"
                        f"\n  Total Tokens: {stats.llm_total_tokens}"
                        f"\n  Avg TTFT: {stats.llm_total_ttft/stats.llm_count:.2f}s"
                        f"\n  Cancelled Requests: {stats.llm_cancelled}"
                    )
                    
                # VAD 使用统计
                elif isinstance(metrics_data, VADMetrics):
                    stats.vad_total_idle += metrics_data.idle_time
                    stats.vad_total_inference += metrics_data.inference_duration_total
                    stats.vad_inference_count += metrics_data.inference_count
                    
                    logger.info(
                        f"VAD Metrics:"
                        f"\n  Model: {metrics_data.label}"
                        f"\n  Idle Time: {metrics_data.idle_time:.2f}s"
                        f"\n  Inference Time: {metrics_data.inference_duration_total:.2f}s"
                        f"\n  Inference Count: {metrics_data.inference_count}"
                        f"\n  -------- Cumulative Stats --------"
                        f"\n  Total Inference Count: {stats.vad_inference_count}"
                        f"\n  Total Idle Time: {stats.vad_total_idle:.2f}s"
                        f"\n  Total Inference Time: {stats.vad_total_inference:.2f}s"
                        f"\n  Avg Inference Time: {stats.vad_total_inference/stats.vad_inference_count:.4f}s"
                    )

            except Exception as e:
                logger.error(f"Error in usage collection: {str(e)}")
                logger.error(f"Metrics data type: {type(metrics_data)}")
                logger.error(f"Metrics data content: {vars(metrics_data)}")

        asyncio.create_task(handle_metrics())

    # 注册事件监听器
    agent.on("metrics_collected", usage_collector)


def setup_metrics_collector(agent, ctx):
    """设置指标收集器"""
    usage_collector = metrics.UsageCollector()
    
    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        # 记录指标
        metrics.log_metrics(mtrcs)
        # 收集使用情况
        usage_collector.collect(mtrcs)

    async def log_session_cost():
        """记录会话成本"""
        try:
            summary = usage_collector.get_summary()
            
            # 计算LLM成本
            llm_cost = (
                summary.llm_prompt_tokens * settings.PRICE_CONFIG["LLM"]["INPUT_PRICE"]
                + summary.llm_completion_tokens * settings.PRICE_CONFIG["LLM"]["OUTPUT_PRICE"]
            )
            
            # 计算TTS成本
            tts_cost = summary.tts_characters_count * settings.PRICE_CONFIG["TTS"]["PRICE"]
            
            # 计算STT成本
            stt_cost = summary.stt_audio_duration * settings.PRICE_CONFIG["STT"]["PRICE"]

            total_cost = llm_cost + tts_cost + stt_cost

            # 记录详细的使用统计（只包含可用属性）
            logger.info(
                f"\nSession Usage Summary:"
                f"\n------------------------"
                f"\nLLM Usage:"
                f"\n  - Prompt Tokens: {summary.llm_prompt_tokens:,}"
                f"\n  - Completion Tokens: {summary.llm_completion_tokens:,}"
                f"\n  - Total Tokens: {summary.llm_prompt_tokens + summary.llm_completion_tokens:,}"
                f"\n  - Cost: ${llm_cost:.4f}"
                f"\n"
                f"\nTTS Usage:"
                f"\n  - Characters: {summary.tts_characters_count:,}"
                f"\n  - Cost: ${tts_cost:.4f}"
                f"\n"
                f"\nSTT Usage:"
                f"\n  - Audio Duration: {summary.stt_audio_duration:.2f}s"
                f"\n  - Cost: ${stt_cost:.4f}"
                f"\n"
                f"\nTotal Session Cost: ${total_cost:.4f}"
                f"\n------------------------"
            )

        except Exception as e:
            logger.error(f"Error in log_session_cost: {str(e)}")
            logger.debug(f"Available summary attributes: {vars(summary) if summary else 'No summary available'}")

    # 添加关闭回调
    ctx.add_shutdown_callback(log_session_cost)


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
            allow_interruptions=True,
            interrupt_speech_duration=0.8,
            interrupt_min_words=1,
            # minimal silence duration to consider end of turn
            min_endpointing_delay=0.5,
            vad=ctx.proc.userdata["vad"],
            stt=deepgram.STT(api_key=settings.DEEPGRAM_API_KEY),
            llm=openai.LLM(**settings.LLM_CONFIG),
            tts=cartesia_tts,
            chat_ctx=initial_ctx,
        )

        # 设置指标收集器
        setup_metrics_collector(agent, ctx)
        
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

from datetime import datetime
from typing import Optional
from supabase import create_client, Client
from config.settings import settings
from utils.logger import logger


class SupabaseClient:
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )

    async def get_user_uuid_by_apikey(self, api_key: str) -> Optional[str]:
        """根据 API key 获取用户 UUID"""
        try:
            response = self.client.table('apikeys')\
                .select('user_uuid')\
                .eq('api_key', api_key)\
                .eq('status', 'active')\
                .single()\
                .execute()
            
            if response.data:
                return response.data.get('user_uuid')
            return None
        except Exception as e:
            logger.error(f"Error getting user_uuid for API key: {str(e)}")
            return None

    async def log_usage(self,
                       api_key: str,
                       service_type: str,
                       usage_amount: float,
                       cost: float,
                       model: str,
                       request_id: Optional[str] = None,
                       status: str = 'success',
                       error_message: Optional[str] = None):
        """
        记录 API 使用情况
        """
        try:
            # 获取用户 UUID
            user_uuid = await self.get_user_uuid_by_apikey(api_key)
            if not user_uuid:
                logger.error(f"Invalid or inactive API key: {api_key}")
                return

            data = {
                'api_key': api_key,
                'user_uuid': user_uuid,
                'service_type': service_type,
                'usage_amount': usage_amount,
                'cost': cost,
                'model': model,
                'created_at': datetime.now().isoformat(),
                'status': status
            }
            
            if request_id:
                data['request_id'] = request_id
            if error_message:
                data['error_message'] = error_message
                
            self.client.table('usage_logs').insert(data).execute()
            logger.debug(f"Logged {service_type} usage for user {user_uuid}: {data}")
            
        except Exception as e:
            logger.error(f"Error logging usage: {str(e)}")

    async def check_credits(self, api_key: str, required_cost: float) -> bool:
        """检查用户是否有足够的积分"""
        try:
            user_uuid = await self.get_user_uuid_by_apikey(api_key)
            if not user_uuid:
                return False

            # 获取用户当前有效的积分总和
            response = self.client.table('credits')\
                .select('credits')\
                .eq('user_uuid', user_uuid)\
                .gte('expired_at', datetime.now().isoformat())\
                .execute()

            total_credits = sum(row.get('credits', 0) for row in response.data)
            return total_credits >= required_cost

        except Exception as e:
            logger.error(f"Error checking credits: {str(e)}")
            return False

    async def log_llm_usage(self, api_key: str, tokens: int, cost: float, **kwargs):
        # 检查积分是否足够
        if not await self.check_credits(api_key, cost):
            logger.error(f"Insufficient credits for API key: {api_key}")
            return

        await self.log_usage(
            api_key=api_key,
            service_type='llm',
            usage_amount=tokens,
            cost=cost,
            **kwargs
        )

    async def log_tts_usage(self, api_key: str, characters: int, cost: float, **kwargs):
        if not await self.check_credits(api_key, cost):
            logger.error(f"Insufficient credits for API key: {api_key}")
            return

        await self.log_usage(
            api_key=api_key,
            service_type='tts',
            usage_amount=characters,
            cost=cost,
            **kwargs
        )

    async def log_stt_usage(self, api_key: str, duration: float, cost: float, **kwargs):
        if not await self.check_credits(api_key, cost):
            logger.error(f"Insufficient credits for API key: {api_key}")
            return

        await self.log_usage(
            api_key=api_key,
            service_type='stt',
            usage_amount=duration,
            cost=cost,
            **kwargs
        )

    async def log_vad_usage(self, api_key: str, duration: float, cost: float, **kwargs):
        if not await self.check_credits(api_key, cost):
            logger.error(f"Insufficient credits for API key: {api_key}")
            return

        await self.log_usage(
            api_key=api_key,
            service_type='vad',
            usage_amount=duration,
            cost=cost,
            **kwargs
        )

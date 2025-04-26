from astrbot.api.all import *
import random
import time
import asyncio
from typing import List # 导入 List

@register("doNotPoke", "Flartiny ", "监控戳一戳事件插件", "1.0.0")
class PokeMonitorPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.user_poke_timestamps = {}
        # 修正类型提示
        self.poke_responses: List[str] = config.get('poke_responses')
        self.poke_response_enabled = config.get('poke_response_enabled')
        self.poke_back_enabled = config.get('poke_back_enabled')
        self.poke_back_probability = config.get('poke_back_probability')
        self.super_poke_probability = config.get('super_poke_probability')

    @event_message_type(EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        message_obj = event.message_obj
        raw_message = message_obj.raw_message
        is_super = False  # 超级加倍标志

        if raw_message.get('post_type') == 'notice' and \
                raw_message.get('notice_type') == 'notify' and \
                raw_message.get('sub_type') == 'poke':
            bot_id = raw_message.get('self_id')
            sender_id = raw_message.get('user_id')
            target_id = raw_message.get('target_id')

            now = time.time()
            three_minutes_ago = now - 3 * 60

            # 清理旧记录
            if sender_id in self.user_poke_timestamps:
                self.user_poke_timestamps[sender_id] = [
                    t for t in self.user_poke_timestamps[sender_id] if t > three_minutes_ago
                ]

            if bot_id and sender_id and target_id:
                # 用户戳机器人
                if str(target_id) == str(bot_id):
                    # 记录戳一戳 (即使不回复也记录，用于 poke_count)
                    if sender_id not in self.user_poke_timestamps:
                        self.user_poke_timestamps[sender_id] = []
                    self.user_poke_timestamps[sender_id].append(now)
                    # poke_count = len(self.user_poke_timestamps[sender_id]) # 如果后续需要用到次数可以保留

                    # 文本回复 (修改后)
                    if self.poke_response_enabled:
                        # 检查列表是否为空，然后随机选择
                        if self.poke_responses:
                            response = random.choice(self.poke_responses)
                            yield event.plain_result(response)
                        else:
                            # 如果列表为空，可以给一个默认回复或不回复
                            yield event.plain_result("哎呀！") # 或者直接 pass

                    # 概率戳回 (保持不变)
                    if self.poke_back_enabled and random.random() < self.poke_back_probability:
                        if random.random() < self.super_poke_probability:
                            poke_times = 10
                            yield event.plain_result("喜欢戳是吧")
                            is_super = True # 标记为超级戳
                        else:
                            poke_times = 1
                            yield event.plain_result("戳回去")

                        # 发送戳一戳
                        if event.get_platform_name() == "aiocqhttp":
                            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                            assert isinstance(event, AiocqhttpMessageEvent)
                            client = event.bot
                            group_id = raw_message.get('group_id')
                            payloads = {"user_id": sender_id}
                            if group_id:
                                payloads["group_id"] = group_id
                            else:
                                print("警告：尝试在非群聊环境中戳回，可能不支持。")
                                return

                            for i in range(poke_times):
                                try:
                                    await client.api.call_action('send_poke', **payloads)
                                    if is_super and i < poke_times - 1:
                                        await asyncio.sleep(0.5)
                                except Exception as e:
                                    print(f"发送戳一戳失败: {e}")
                                    break
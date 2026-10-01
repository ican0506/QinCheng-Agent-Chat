import re
from app.realtime_policy.models import FreshnessIntent


class FreshnessIntentDetector:
    @staticmethod
    def detect(message: str) -> FreshnessIntent:
        text = message.strip()
        historical = re.search(
            r'历史(?:政策|通知|申报)|'
            r'往年.*(?:申报|政策|通知|时间)|'
            r'(?:之前|过去|以前|去年).*?(?:政策|通知|申报|申请|截止|文件)|'
            r'当时.*?(?:政策|通知|申报|申请|截止|发布|文件)',
            text,
        )
        current = re.search(
            r'最新|还能申请|还能申领|窗口|申报时间|截止时间|什么时候截止|'
            r'最新通知|新政策|最近发布|今年还有|通知.*出来了吗|'
            r'(?:现在|当前|目前).{0,12}(?:政策|补贴|申请|申领|窗口|通知|截止)|'
            r'(?:政策|补贴|申请|申领|窗口|通知|截止).{0,12}(?:现在|当前|目前)',
            text,
        )
        # 保留用户只输入一个当前性提示词的短查询；画像中的“目前未就业/今年毕业”不触发。
        current = current or re.fullmatch(r'(?:现在|当前|目前|今年)[？?]?', text)
        return FreshnessIntent(
            requiresRealtimeSearch=bool(current or historical),
            reason='官方历史通知查询' if historical else ('政策当前性查询' if current else None),
        )

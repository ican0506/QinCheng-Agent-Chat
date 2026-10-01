import re
from app.realtime_policy.models import FreshnessIntent


class FreshnessIntentDetector:
    @staticmethod
    def detect(message: str) -> FreshnessIntent:
        match = re.search(r'最新|现在|当前|今年|目前|还能申请|还能申领|窗口|申报时间|截止时间|什么时候截止|最新通知|新政策|最近发布', message)
        historical = re.search(r'历史|当时|往年|20\d{2}届', message) and re.search(r'通知|申报|申请|截止|发布', message)
        return FreshnessIntent(requiresRealtimeSearch=bool(match or historical), reason='官方历史通知查询' if historical else ('政策当前性查询' if match else None))

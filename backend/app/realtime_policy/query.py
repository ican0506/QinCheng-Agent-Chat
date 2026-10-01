import re
from datetime import date
from app.models.chat import UserProfile


def build_query(message: str, profile: UserProfile, policy_names: list[str]) -> tuple[str, list[str]]:
    names = [name for name in policy_names if name in message]
    topics = [word for word in ('创业', '就业', '毕业生', '社保', '社会保险', '求职', '见习', '补贴') if word in message]
    historical = bool(re.search(r'历史|当时|往年|20\d{2}届', message))
    year = re.search(r'20\d{2}', message)
    parts = [profile.city or '', *names, *topics, year.group() if year else str(date.today().year), '申报通知' if historical else '最新 申报']
    return ' '.join(dict.fromkeys(p for p in parts if p)), names or topics

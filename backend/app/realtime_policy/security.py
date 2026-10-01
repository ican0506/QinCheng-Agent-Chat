import ipaddress
from urllib.parse import urlsplit, urlunsplit


def canonical_url(url: str, allowed_domains: list[str]) -> str | None:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower()
        if parsed.scheme.lower() != 'https' or not host or parsed.username or parsed.password:
            return None
        if host == 'localhost' or host.endswith('.localhost'):
            return None
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            pass
        domains = [d.strip().lower().rstrip('.') for d in allowed_domains if d.strip()]
        if not any(host == d or host.endswith('.' + d) for d in domains):
            return None
        port = parsed.port
        if port not in (None, 443):
            return None
        return urlunsplit(('https', host, parsed.path or '/', parsed.query, ''))
    except ValueError:
        return None

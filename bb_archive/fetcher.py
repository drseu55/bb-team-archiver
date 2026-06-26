import time
import random
from typing import Optional

import requests

BASE_URL = "https://www.bb-team.org/forums/viewthread"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    session.headers.update({"Accept-Language": "bg,en;q=0.9"})
    return session


def build_url(thread_id: int, page_num: int) -> str:
    if page_num <= 1:
        return f"{BASE_URL}/{thread_id}"
    return f"{BASE_URL}/{thread_id}/P{(page_num - 1) * 40}"


def fetch_page(
    session: requests.Session, url: str, delay: float = 1.5
) -> Optional[str]:
    time.sleep(random.uniform(delay * 0.5, delay * 1.5))
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except requests.RequestException as e:
        print(f"  \u2716 Error fetching {url}: {e}")
        return None

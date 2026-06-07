import json
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    DB_FILE_PATH,
    DEFAULT_ARCHIVE_LIMIT,
    EVERGREEN_ARCHIVE_LIMIT,
    EVERGREEN_TOPICS,
)

_EVERGREEN_SET = set(EVERGREEN_TOPICS)


def _load_db() -> list[dict]:
    try:
        with open(DB_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _parse_date(date_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except (ValueError, TypeError):
            continue
    return None


def _is_alive(article: dict, now: datetime) -> bool:
    pub_date = _parse_date(article.get("published_date") or article.get("published", ""))
    if pub_date is None:
        # Keep undatable articles; better to retain than silently drop
        return True

    age_days = (now - pub_date).days
    topics = set(article.get("topics", []))

    if topics & _EVERGREEN_SET:
        return age_days <= EVERGREEN_ARCHIVE_LIMIT

    return age_days <= DEFAULT_ARCHIVE_LIMIT


def save_articles(new_articles: list[dict]) -> int:
    """Merge new articles into the DB, deduplicate, apply archival rules, persist."""
    os.makedirs(os.path.dirname(DB_FILE_PATH) or ".", exist_ok=True)

    existing = _load_db()
    now = datetime.now(tz=timezone.utc)

    seen_urls: set[str] = {a["url"] for a in existing}
    for article in new_articles:
        if article.get("url") not in seen_urls:
            existing.append(article)
            seen_urls.add(article["url"])

    alive = [a for a in existing if _is_alive(a, now)]

    with open(DB_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(alive, f, ensure_ascii=False, indent=2)

    added = len(alive) - (len(existing) - len(new_articles))
    print(f"DB updated — total: {len(alive)} articles, {len(new_articles) - (len(new_articles) - max(0, added))} new added, {len(existing) - len(alive)} purged.")
    return len(alive)


def load_articles() -> list[dict]:
    """Read-only access for the frontend or other consumers."""
    return _load_db()

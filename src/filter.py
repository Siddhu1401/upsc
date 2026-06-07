import os
import sys
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import List

# pyrefly: ignore [missing-import]
from groq import Groq, RateLimitError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import GROQ_API_KEY

log = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY)
FILTER_MODEL = "llama-3.1-8b-instant"

# Keywords provided as context hints to the model — NOT used for matching
UPSC_CONTEXT_HINTS = """
GS Paper 1: History, Geography, Indian Society, Culture, Post-independence India
GS Paper 2: Polity, Constitution, Governance, Social Justice, International Relations, Parliament, 
            Judiciary, Supreme Court, High Court, Bills, Acts, Federalism, Treaties, UN, Foreign Policy,
            Diplomacy, India-China, India-Pakistan, India-US, G20, BRICS, SCO, ASEAN, WTO, IMF, World Bank
GS Paper 3: Economy, Agriculture, GDP, Inflation, RBI, Budget, Fiscal Deficit, Infrastructure, 
            Environment, Climate Change, Biodiversity, Science & Technology, Space, ISRO, Defence, 
            Internal Security, Disaster Management, Energy, Digital India
GS Paper 4: Ethics, Integrity, Transparency, Accountability, Corruption

REJECT these categories: cricket scores, celebrity news, sports results, movie reviews,
entertainment, local crime, personal finance tips, astrology, fashion, lifestyle, recipes.
"""

SYSTEM_PROMPT = f"""You are a strict UPSC CSE Current Affairs filter working for India's top IAS coaching institute.

Your ONLY job is to decide if a news article is relevant to the UPSC Civil Services Examination syllabus.

UPSC SYLLABUS REFERENCE:
{UPSC_CONTEXT_HINTS}

RULES:
1. Return true if the article touches ANY part of the UPSC CSE syllabus — even partially.
2. Be GENEROUS and INCLUSIVE. When in doubt, return true. It is better to include a borderline article than to miss a relevant one.
3. Return false ONLY for articles that are clearly irrelevant: sports scores, entertainment, celebrity gossip, lifestyle, local crime with no governance angle.
4. Government policies, court rulings, international events, economic data, environmental issues, science discoveries, defence news — these are ALWAYS true.
5. You must respond with ONLY a JSON object: {{"results": [true, false, ...]}} — one boolean per article, in order.
"""

FRESHNESS_WINDOW = timedelta(hours=24)

def _is_fresh(article: dict) -> bool:
    """
    Returns True if the article was published within the last 24 hours.
    Uses the RFC 2822 `published_date` field from the scraper.
    Defaults to True (include) if the date cannot be parsed.
    """
    raw_date = article.get('published_date', '').strip()
    if not raw_date:
        return True  # No date info — don't discard
    try:
        pub_dt = parsedate_to_datetime(raw_date)
        now_utc = datetime.now(timezone.utc)
        return (now_utc - pub_dt) <= FRESHNESS_WINDOW
    except Exception:
        return True  # Unparseable date — don't discard

def filter_batch(articles_batch: List[dict], batch_num: int) -> List[bool]:
    """
    Two-stage filter gate:
      1. Freshness check  — instantly drops articles older than 24 hours (free).
      2. LLM relevance    — llama-3.1-8b-instant decides UPSC syllabus relevance.
    Falls back to True (include) on any LLM error to avoid data loss.
    """
    if not articles_batch:
        return []

    # ── Stage 1: Freshness gate (instant, free) ───────────────────────────
    fresh_flags = [_is_fresh(a) for a in articles_batch]
    fresh_articles = [a for a, f in zip(articles_batch, fresh_flags) if f]
    stale_count = len(articles_batch) - len(fresh_articles)
    if stale_count:
        log.info(f"[Filter] Batch {batch_num}: {stale_count} stale article(s) dropped (>24h old).")

    # If nothing is fresh in this batch, return immediately
    if not fresh_articles:
        return [False] * len(articles_batch)

    # ── Stage 2: LLM relevance gate ──────────────────────────────────────

    # Build the article list for the prompt (only fresh articles)
    articles_text = ""
    for idx, article in enumerate(fresh_articles):
        title = article.get('title', '').strip()
        snippet = (article.get('summary', '') or article.get('content', '') or '')[:300].strip()
        articles_text += f"{idx + 1}. \"{title}\" — {snippet}\n"

    user_prompt = (
        f"Evaluate these {len(fresh_articles)} news article headlines and snippets for UPSC relevance.\n"
        f"Return a JSON object with a 'results' array of {len(fresh_articles)} booleans.\n\n"
        f"ARTICLES:\n{articles_text}\n"
        f"Respond with ONLY: {{\"results\": [true/false, ...]}}"
    )

    retries = 0
    while retries < 3:
        try:
            response = client.chat.completions.create(
                model=FILTER_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=100,
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)
            results = data.get("results", [])

            # Validate length — pad or trim if model misbehaves
            if len(results) < len(fresh_articles):
                results += [True] * (len(fresh_articles) - len(results))
            results = results[:len(fresh_articles)]

            # ── Rate-limit guard ──────────────────────────────────────────
            # llama-3.1-8b-instant: 30 RPM / 6K TPM
            # This call costs ~970 tokens → safe budget = 6 calls/min
            # Sleep 12s ensures we never exceed 5 calls/min (= ~4850 TPM)
            time.sleep(12)

            # Re-map LLM results back to full batch (stale articles = False)
            llm_iter = iter(results)
            return [next(llm_iter) if is_fresh else False for is_fresh in fresh_flags]

        except RateLimitError:
            log.warning(f"[Filter] Rate limit hit on batch {batch_num}. Backing off 15s...")
            time.sleep(15)
            retries += 1
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"[Filter] JSON parse error on batch {batch_num}: {e}. Defaulting all to True.")
            return [True] * len(articles_batch)
        except Exception as e:
            err = str(e)
            if '503' in err or 'unavailable' in err.lower():
                log.warning(f"[Filter] Service unavailable. Sleeping 5s...")
                time.sleep(5)
                retries += 1
            else:
                log.error(f"[Filter] Unexpected error on batch {batch_num}: {e}. Defaulting all to True.")
                return [True] * len(articles_batch)

    # After 3 retries, include everything to avoid losing articles
    log.warning(f"[Filter] Max retries hit on batch {batch_num}. Including all articles as fallback.")
    return [True] * len(articles_batch)
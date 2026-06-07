import os
import sys
import time
import json
import logging
from typing import List, Optional
# pyrefly: ignore [missing-import]
from groq import Groq, RateLimitError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import GROQ_API_KEY

log = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY)
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

def analyze_batch(articles_batch: List[dict]) -> List[dict]:
    if not articles_batch:
        return []

    articles_text = ""
    for idx, article in enumerate(articles_batch):
        content = article.get('summary', '') or article.get('content', '')
        articles_text += f"{idx + 1}. Title: {article.get('title', '')}\nSnippet: {content[:2000]}\n\n"

    SYSTEM_PROMPT = """You are an expert UPSC CSE analyst for India's top IAS coaching institute.
Your task is to produce a DEEP, COMPREHENSIVE analysis of each news article for serious UPSC aspirants.

CRITICAL RULES — NO EXCEPTIONS:
1. Every single field MUST be filled. Empty strings ("") are STRICTLY FORBIDDEN.
2. Every field must contain AT LEAST 2 full, substantive sentences. One-liners are NOT acceptable.
3. Write as a UPSC subject-matter expert, not a news summariser.
4. gs_paper_number must be ONLY one of: "GS1", "GS2", "GS3", or "GS4".

FIELD DEFINITIONS (write this much detail for each):
- what: What happened? Explain the event, policy, judgment, or development in full context (3-4 sentences).
- why: Why did this happen? What were the driving forces, political/economic/social causes? (2-3 sentences)
- historical_context: What is the relevant historical background — past events, treaties, policies, or trends that led to this? (2-3 sentences)
- significance: Why does this matter nationally or globally? What precedent does it set? (2-3 sentences)
- implications: What are the short and long-term consequences for India and the world? (2-3 sentences)
- stakeholders: Who are the key players affected — government bodies, communities, international actors, industry? (2-3 sentences)
- advantages: What are the benefits or positive outcomes of this development? (2 sentences)
- challenges: What obstacles, risks, or difficulties exist? (2 sentences)
- criticisms: What are the valid criticisms or opposing viewpoints from experts, opposition, or affected parties? (2 sentences)
- way_forward: What concrete steps, policies, or reforms are needed going forward? (2-3 sentences)
- prelims_angle: Specific facts, dates, bodies, Acts, schemes — what a UPSC Prelims MCQ could test from this. (2 sentences)
- mains_angle: Which GS Mains paper, which specific topic, and what kind of question this could generate. (2-3 sentences)
- essay_angle: How this topic connects to broader themes suitable for a GS4 or Essay paper. (2 sentences)
"""

    user_prompt = (
        f"Analyze these {len(articles_batch)} news articles. "
        f"Return a JSON object: {{\"analysis\": [array of {len(articles_batch)} objects]}}.\n\n"
        "Each object in the array must have EXACTLY these keys (all mandatory, no empty strings):\n"
        "  gs_paper_number, topic, deep_analysis (object with: what, why, historical_context, "
        "significance, implications, stakeholders, advantages, challenges, criticisms, way_forward), "
        "upsc_thinking_layer (object with: prelims_angle, mains_angle, essay_angle)\n\n"
        f"ARTICLES:\n{articles_text}\n\n"
        "Return ONLY valid JSON. No markdown, no explanation outside JSON."
    )

    retries = 0
    while True:
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=4096,
            )
            raw_content = response.choices[0].message.content
            
            try:
                data = json.loads(raw_content)
                analyses = data.get("analysis", [])
                
                if len(analyses) != len(articles_batch):
                    log.error(f"[ERROR] Analysis failed for batch. Length mismatch. Skipping.")
                    return []
                
                enriched_batch = []
                for article, analysis in zip(articles_batch, analyses):
                    article_copy = article.copy()
                    
                    da = analysis.get("deep_analysis", {})
                    utl = analysis.get("upsc_thinking_layer", {})

                    article_copy.update({
                        "gs_tags": [analysis.get("gs_paper_number", "GS2")],
                        "topics": [analysis.get("topic", "")],
                        "deep_analysis": {
                            "what": da.get("what", ""),
                            "why": da.get("why", ""),
                            "historical_context": da.get("historical_context", ""),
                            "significance": da.get("significance", ""),
                            "implications": da.get("implications", ""),
                            "stakeholders": da.get("stakeholders", ""),
                            "advantages": da.get("advantages", ""),
                            "challenges": da.get("challenges", ""),
                            "criticisms": da.get("criticisms", ""),
                            "way_forward": da.get("way_forward", "")
                        },
                        "upsc_thinking_layer": {
                            "prelims_angle": utl.get("prelims_angle", ""),
                            "mains_angle": utl.get("mains_angle", ""),
                            "essay_angle": utl.get("essay_angle", "")
                        },
                        "knowledge_graph": [],
                        "relevance_score": 10,
                    })
                    enriched_batch.append(article_copy)
                
                # ── Rate-limit guard ──────────────────────────────────────────
                # llama-4-scout-17b: 30K TPM
                # 10 articles per call costs ~5,000 tokens → 6 calls/min max
                # Sleep 12s ensures ~5 calls/min (= ~25K TPM), safe margin
                time.sleep(12)
                return enriched_batch

            except json.JSONDecodeError:
                log.error(f"[ERROR] Analysis failed for batch. JSON malformed. Skipping.")
                return []

        except RateLimitError as e:
            log.warning("Rate limit hit, sleeping 6s...")
            time.sleep(6)
            retries += 1
        except Exception as e:
            err = str(e)
            if '503' in err or 'service unavailable' in err.lower():
                log.warning("Rate limit hit, sleeping 6s...")
                time.sleep(6)
                retries += 1
            else:
                log.error(f"[ERROR] Analysis failed for batch. Non-recoverable error: {e}. Skipping.")
                return []

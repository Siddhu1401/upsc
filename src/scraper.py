import sys
import os
import requests
import feedparser

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import RSS_FEEDS

def fetch_feed_items(feed_name, url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return []
        
        feed = feedparser.parse(response.content)
        items = []
        
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "").strip() or entry.get("description", "").strip()
            pub_date = entry.get("published", "").strip() or entry.get("pubDate", "").strip()
            
            if not title or not link:
                continue
                
            items.append({
                "title": title,
                "url": link,
                "summary": summary,
                "published_date": pub_date,
                "feed_source": feed_name
            })
            
        return items
    except Exception:
        return []

def scrape_all_feeds():
    all_raw_articles = []
    seen_urls = set()
    
    for name, url in RSS_FEEDS.items():
        feed_items = fetch_feed_items(name, url)
        for item in feed_items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                all_raw_articles.append(item)
                
    return all_raw_articles

if __name__ == "__main__":
    articles = scrape_all_feeds()
    print(f"Scraped {len(articles)} unique raw articles from sources.")
    
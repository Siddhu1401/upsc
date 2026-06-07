import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DB_FILE_PATH = os.getenv("DB_FILE_PATH", "data/news.json")

DEFAULT_ARCHIVE_LIMIT = 60
EVERGREEN_TOPICS = ["Uniform Civil Code", "Delimitation", "Federalism", "Semiconductor Mission", "Climate Change"]
EVERGREEN_ARCHIVE_LIMIT = 365

RSS_FEEDS = {
    "PIB_MAIN": "https://pib.gov.in/RssMain.aspx",
    "PRS_LEGISLATIVE": "https://prsindia.org/the-prs-blog/feed",
    "IE_EXPLAINED": "https://indianexpress.com/section/explained/feed/",
    "IE_ECONOMY": "https://indianexpress.com/section/business/feed/",
    "IE_WORLD": "https://indianexpress.com/section/world/feed/",
    "DOWN_TO_EARTH": "https://www.downtoearth.org.in/rss/all",
    "LIVELAW": "https://www.livelaw.in/rss/feed.php"
}

SYLLABUS_MAP = {
    "GS1": ["Art & Culture", "History", "Geography", "Society"],
    "GS2": ["Polity", "Constitution", "Governance", "Judiciary", "International Relations"],
    "GS3": ["Economy", "Environment", "Science & Technology", "Internal Security", "Disaster Management"],
    "GS4": ["Ethics", "Integrity", "Case Studies"],
    "ESSAY": ["Philosophical Themes", "Socio-Economic Perspectives", "Macro Trends"],
    "OPTIONAL_GEOGRAPHY": ["Physical Geography", "Human Geography", "Economic & Regional Spatial Planning"],
    "INTERVIEW": ["Key Opinion Pieces", "High-Impact Policy Debate", "Administrative Case Studies"]
}
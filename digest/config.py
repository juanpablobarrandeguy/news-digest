"""Configuration: feeds, selection tuning, and environment-driven settings."""

import os

# --------------------------------------------------------------------------
# Feeds
# --------------------------------------------------------------------------
# weight: nudges ranking when two stories compete for the same slot.
# category: "ai" | "tech" | "world". Items in "tech" feeds that trip the AI
# keyword filter get promoted to "ai" automatically.

FEEDS = [
    # --- AI ---------------------------------------------------------------
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "category": "ai", "weight": 1.2},
    {"name": "The Decoder", "url": "https://the-decoder.com/feed/", "category": "ai", "weight": 1.0},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "category": "ai", "weight": 0.9},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "category": "ai", "weight": 0.9},
    {"name": "Import AI", "url": "https://importai.substack.com/feed", "category": "ai", "weight": 1.1},
    # 2026-08-02: VentureBeat AI sacado — https://venturebeat.com/category/ai/feed/
    # parseaba bien pero llevaba 75 dias sin publicar. La raiz (venturebeat.com/feed/)
    # esta viva pero trae solo 7 items y casi nada de AI.

    # --- Tech -------------------------------------------------------------
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "tech", "weight": 1.2},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "tech", "weight": 1.0},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "tech", "weight": 1.0},
    # points=200 dejaba pasar 1 sola nota por corrida. 100 trae ~11 y sigue
    # siendo selectivo. Subilo de nuevo si el ruido molesta.
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage?points=100", "category": "tech", "weight": 1.3},

    # --- Nacional (Argentina) --------------------------------------------
    # A deliberate spread across the editorial spectrum so the section isn't
    # one outlet's framing. Run verify_feeds.py before launch — Argentine
    # outlets rearrange their RSS paths more often than most.
    #
    # 2026-08-02: Página/12 fuera de servicio. Sus 5 rutas RSS conocidas fallan
    # en el MISMO offset (2:3029) y devuelven 404 al bajarlas con requests: no
    # es XML sucio, es que ya no publican RSS. Se deja anotado, no borrado.
    #   {"name": "Página/12", "url": "https://www.pagina12.com.ar/rss/portada", ...}
    # En su lugar entran elDiarioAR (noticia general de centroizquierda) y
    # Letra P (analisis politico diario).
    {"name": "elDiarioAR", "url": "https://www.eldiarioar.com/rss/", "category": "nacional", "weight": 1.0},
    {"name": "Letra P", "url": "https://www.letrap.com.ar/rss/pages/home.xml", "category": "nacional", "weight": 0.9},
    {"name": "Infobae", "url": "https://www.infobae.com/arc/outboundfeeds/rss/?outputType=xml", "category": "nacional", "weight": 1.1},
    {"name": "Clarín", "url": "https://www.clarin.com/rss/lo-ultimo/", "category": "nacional", "weight": 1.1},
    {"name": "La Nación", "url": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml", "category": "nacional", "weight": 1.1},
    {"name": "Ámbito", "url": "https://www.ambito.com/rss/pages/economia.xml", "category": "nacional", "weight": 0.9},
    {"name": "Perfil", "url": "https://www.perfil.com/feed", "category": "nacional", "weight": 0.9},

    # --- World ------------------------------------------------------------
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "world", "weight": 1.2},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "world", "weight": 1.0},
    {"name": "NPR World", "url": "https://feeds.npr.org/1004/rss.xml", "category": "world", "weight": 1.0},
    {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "category": "world", "weight": 1.1},
]

# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------

LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "28"))

# Stories per section in the final email.
SECTION_LIMITS = {
    "ai": int(os.getenv("LIMIT_AI", "5")),
    "tech": int(os.getenv("LIMIT_TECH", "5")),
    "nacional": int(os.getenv("LIMIT_NACIONAL", "5")),
    "world": int(os.getenv("LIMIT_WORLD", "5")),
}

SECTION_TITLES = {
    "ai": "AI",
    "tech": "Tech",
    "nacional": "Nacional",
    "world": "World",
}

SECTION_ORDER = ["ai", "tech", "nacional", "world"]

# Language each section is summarized in. Argentine sources are Spanish, so
# translating them into English just adds a lossy hop.
SECTION_LANGUAGE = {
    "ai": os.getenv("LANG_AI", "English"),
    "tech": os.getenv("LANG_TECH", "English"),
    "nacional": os.getenv("LANG_NACIONAL", "Spanish (rioplatense, neutral register)"),
    "world": os.getenv("LANG_WORLD", "English"),
}

# Hard cap on items pulled from any single feed before ranking.
MAX_PER_FEED = 25

# A story from a "tech" feed matching any of these gets moved to the AI section.
AI_KEYWORDS = [
    "ai ", " ai", "a.i.", "artificial intelligence", "machine learning", "llm",
    "large language model", "neural", "openai", "anthropic", "claude", "chatgpt",
    "gpt-", "gemini", "deepmind", "mistral", "llama", "hugging face", "nvidia",
    "inference", "transformer", "diffusion model", "agentic", "copilot",
    "training run", "foundation model", "rag ", "fine-tun",
]

# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------

STATE_PATH = os.getenv("STATE_PATH", "state/seen.json")
STATE_RETENTION_DAYS = int(os.getenv("STATE_RETENTION_DAYS", "14"))

# --------------------------------------------------------------------------
# LLM
# --------------------------------------------------------------------------
# "gemini" (free tier) | "groq" (free tier) | "anthropic" (paid) | "none"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")  # blank = provider default
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BATCH_SIZE = int(os.getenv("LLM_BATCH_SIZE", "12"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "90"))

PROVIDER_DEFAULT_MODEL = {
    "gemini": "gemini-3.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "anthropic": "claude-haiku-4-5-20251001",
}

# --------------------------------------------------------------------------
# Tweet angles
# --------------------------------------------------------------------------
# An optional section at the end of the email: which of today's stories are
# worth posting about, and possible entry points. You write the actual tweets.

TWEETS_ENABLED = os.getenv("TWEETS_ENABLED", "1").lower() in ("1", "true", "yes")
TWEET_MAX_ANGLES = int(os.getenv("TWEET_MAX_ANGLES", "3"))
TWEET_MIN_SCORE = int(os.getenv("TWEET_MIN_SCORE", "55"))
TWEET_LANE = os.getenv("TWEET_LANE") or (
    "Infraestructura, cloud y AI desde la trinchera: alguien que administra "
    "servidores, bases de datos y AWS todos los dias, y que ademas sigue de "
    "cerca lo que pasa en AI. Tambien politica y actualidad argentina. "
    "Publico objetivo: gente tecnica hispanohablante."
)

# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")
MAIL_FROM = os.getenv("MAIL_FROM", "") or SMTP_USER
MAIL_SUBJECT_PREFIX = os.getenv("MAIL_SUBJECT_PREFIX", "Daily Digest")

TIMEZONE = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")

# Print the email to stdout instead of sending it.
DRY_RUN = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")

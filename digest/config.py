"""Configuration: feeds, selection tuning, and environment-driven settings."""

import os

# --------------------------------------------------------------------------
# Feeds
# --------------------------------------------------------------------------
# weight: nudges ranking when two stories compete for the same slot.
# category: "ai" | "tech" | "world" | "nacional" | "caba". Items in "tech" feeds
# that trip the AI keyword filter get promoted to "ai" automatically, and items
# in "nacional" feeds that trip the CABA keyword filter move to "caba".

FEEDS = [
    # --- AI ---------------------------------------------------------------
    # 2026-10-02: fuentes primarias de los grandes players. Anthropic y Meta no
    # publican RSS; sus anuncios llegan por The Decoder, Simon Willison y HN.
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml", "category": "ai", "weight": 1.3},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "category": "ai", "weight": 1.2},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/", "category": "ai", "weight": 1.0},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "category": "ai", "weight": 1.2},
    {"name": "The Decoder", "url": "https://the-decoder.com/feed/", "category": "ai", "weight": 1.0},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "category": "ai", "weight": 0.9},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "category": "ai", "weight": 0.9},
    # 2026-10-02: Import AI sacado — desde GitHub Actions devuelve XML invalido
    # (2:1326, invalid token) todos los dias.
    #   {"name": "Import AI", "url": "https://importai.substack.com/feed", ...}
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
    # 2026-10-02: infraestructura, nube y datos.
    {"name": "The New Stack", "url": "https://thenewstack.io/feed/", "category": "tech", "weight": 1.0},

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
    # 2026-10-02: Sociedad de La Nación alimenta la sección CABA (lo porteño se
    # separa por palabras clave, ver CABA_KEYWORDS); lo demás queda en Argentina.
    {"name": "La Nación Sociedad", "url": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/sociedad/?outputType=xml", "category": "nacional", "weight": 0.9},

    # --- World ------------------------------------------------------------
    # 2026-10-02: foco en EE.UU., Ucrania/Rusia e Israel/Medio Oriente.
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "world", "weight": 1.2},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "world", "weight": 1.0},
    {"name": "NPR World", "url": "https://feeds.npr.org/1004/rss.xml", "category": "world", "weight": 1.0},
    {"name": "NYT World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "category": "world", "weight": 1.1},
    {"name": "NYT Politics", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml", "category": "world", "weight": 1.0},
    {"name": "Guardian World", "url": "https://www.theguardian.com/world/rss", "category": "world", "weight": 1.1},
    {"name": "Guardian US", "url": "https://www.theguardian.com/us-news/rss", "category": "world", "weight": 1.0},
    # 2026-10-02: Times of Israel sacado — desde GitHub Actions devuelve HTML en
    # lugar del feed (10:43, mismatched tag).
    #   {"name": "Times of Israel", "url": "https://www.timesofisrael.com/feed/", ...}
]

# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------

LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "28"))

# Stories per section in the final email.
SECTION_LIMITS = {
    "ai": int(os.getenv("LIMIT_AI", "5")),
    "tech": int(os.getenv("LIMIT_TECH", "5")),
    "world": int(os.getenv("LIMIT_WORLD", "5")),
    "nacional": int(os.getenv("LIMIT_NACIONAL", "5")),
    "caba": int(os.getenv("LIMIT_CABA", "5")),
}

SECTION_TITLES = {
    "ai": "AI",
    "tech": "Tech & Data",
    "world": "World",
    "nacional": "Argentina",
    "caba": "CABA",
}

SECTION_ORDER = ["ai", "tech", "world", "nacional", "caba"]

# Lo que le importa al lector, por sección. El editor (digest/editor.py) elige
# las notas de cada sección contra este texto. Editalo para afinar el filtro.
SECTION_INTERESTS = {
    "ai": (
        "Novedades de los principales players de IA (OpenAI, Anthropic, Google/DeepMind, "
        "Meta, Microsoft, xAI, Mistral, DeepSeek y similares): lanzamientos de modelos, "
        "cambios de producto relevantes e investigación que mueve el estado del arte."
    ),
    "tech": (
        "Tecnología y datos que hay que tener en el radar: infraestructura, nube, "
        "bases de datos, ingeniería de datos y movimientos importantes de la industria "
        "tecnológica. No le interesa la industria automotriz (ventas, entregas o "
        "modelos de autos, aunque sean eléctricos)."
    ),
    "world": (
        "Política internacional, sobre todo Estados Unidos, Ucrania/Rusia e "
        "Israel/Medio Oriente, más lo internacional que toque a Argentina."
    ),
    "nacional": "Política, economía y actualidad argentina de alcance nacional.",
    "caba": "Noticias de la Ciudad de Buenos Aires: gobierno porteño, transporte, servicios y vida en la ciudad.",
}

# Cuántas candidatas por sección ve el editor antes de elegir.
EDITOR_POOL = int(os.getenv("EDITOR_POOL", "30"))
EDITOR_ENABLED = os.getenv("EDITOR_ENABLED", "1").lower() in ("1", "true", "yes")

# Language each section is summarized in. Argentine sources are Spanish, so
# translating them into English just adds a lossy hop.
SECTION_LANGUAGE = {
    "ai": os.getenv("LANG_AI", "English"),
    "tech": os.getenv("LANG_TECH", "English"),
    "nacional": os.getenv("LANG_NACIONAL", "Spanish (rioplatense, neutral register)"),
    "caba": os.getenv("LANG_CABA", "Spanish (rioplatense, neutral register)"),
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

# Stories dropped before ranking, in every section: sports and exchange-rate
# coverage (2026-10-02, a pedido).
# EXCLUDE_URL_PARTS matches the link path; EXCLUDE_TITLE_RE the headline.
EXCLUDE_URL_PARTS = [
    "/deportes/", "/deporte/", "/futbol/", "/sports/", "/sport/", "/football/",
    "/economia/dolar/", "/dolar-hoy", "/dolar-blue",
]
EXCLUDE_TITLE_RE = r"\bd[oó]lar (hoy|blue|oficial|mep|ccl)\b|\bcotizaci[oó]n del d[oó]lar\b"

# A story from a "nacional" feed matching any of these moves to the CABA section.
# Matched as whole words, case-insensitive; a trailing "*" matches any ending
# ("porteñ*" catches porteño, porteña, porteños). Ambiguous names (Belgrano,
# Flores) are left out on purpose: they trip on clubs, people and flowers.
CABA_KEYWORDS = [
    "caba", "ciudad de buenos aires", "ciudad autónoma de buenos aires", "porteñ*",
    "gobierno de la ciudad", "jefe de gobierno", "jorge macri", "subte*", "premetro",
    "ecobici", "palermo", "recoleta", "caballito", "san telmo", "villa crespo",
    "almagro", "microcentro", "obelisco", "costanera sur", "9 de julio", "aeroparque",
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
LLM_RETRIES = int(os.getenv("LLM_RETRIES", "2"))  # per model, on 429 / 5xx, with backoff

# Gemini: blank = ask the API for the newest stable "gemini-X.Y-flash" on each
# run. Google retires model IDs every few months; a hardcoded default rots.
PROVIDER_DEFAULT_MODEL = {
    "gemini": "",
    "groq": "llama-3.3-70b-versatile",
    "anthropic": "claude-haiku-4-5-20251001",
}

# --------------------------------------------------------------------------
# Trending ("Noticias viralizables")
# --------------------------------------------------------------------------
# An optional section at the end of the email: which of today's stories are
# worth posting about (LinkedIn, the brand's Instagram, X) and possible entry
# points. You write the actual posts. Variables keep the TWEET_* names.

TRENDING_TITLE = "Noticias viralizables / trending"
TWEETS_ENABLED = os.getenv("TWEETS_ENABLED", "1").lower() in ("1", "true", "yes")
TWEET_MAX_ANGLES = int(os.getenv("TWEET_MAX_ANGLES", "3"))
TWEET_MIN_SCORE = int(os.getenv("TWEET_MIN_SCORE", "55"))
TWEET_LANE = os.getenv("TWEET_LANE") or (
    "Marca de servicios de sitios web, infraestructura, nube, datos e IA aplicada "
    "(barrandeguydev), con LinkedIn e Instagram de la marca. Infraestructura, cloud "
    "y AI desde la trinchera: alguien que administra servidores, bases de datos y "
    "nube todos los dias, y que ademas sigue de cerca lo que pasa en AI. Tambien "
    "politica y actualidad argentina. Publico objetivo: gente tecnica y duenos de "
    "pymes hispanohablantes."
)

# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------

# Default: Resend over SMTP. User is the literal "resend", password is a Resend
# API key, and MAIL_FROM must be on a domain verified in Resend.
SMTP_HOST = os.getenv("SMTP_HOST") or "smtp.resend.com"
SMTP_PORT = int(os.getenv("SMTP_PORT") or "465")
SMTP_USER = os.getenv("SMTP_USER") or "resend"
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")
MAIL_FROM = os.getenv("MAIL_FROM") or "digest@barrandeguydev.com"
MAIL_SUBJECT_PREFIX = os.getenv("MAIL_SUBJECT_PREFIX", "Daily Digest")

TIMEZONE = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")

# Print the email to stdout instead of sending it.
DRY_RUN = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")

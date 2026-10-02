# Copiá los valores y pegá el bloque en PowerShell antes de correr run.py.
# NO commitees este archivo con las claves reales adentro (.gitignore ya lo cubre).

$env:LLM_PROVIDER = "gemini"
$env:LLM_API_KEY  = "tu-key-de-gemini"
$env:SMTP_PASS    = "re_tu-api-key-de-resend"
$env:MAIL_TO      = "tu-mail@ejemplo.com"

# Opcionales (sin LLM_MODEL se usa el Gemini Flash estable mas nuevo)
# $env:LLM_MODEL       = "gemini-X.Y-flash"
# $env:MAIL_FROM       = "digest@barrandeguydev.com"
# $env:TWEET_MIN_SCORE = "55"
# $env:TWEETS_ENABLED  = "0"
# $env:DRY_RUN         = "1"

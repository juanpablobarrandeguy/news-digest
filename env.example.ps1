# Copiá los valores y pegá el bloque en PowerShell antes de correr run.py.
# NO commitees este archivo con las claves reales adentro (.gitignore ya lo cubre).

$env:LLM_PROVIDER = "gemini"
$env:LLM_API_KEY  = "tu-key-de-gemini"
$env:SMTP_USER    = "tuusuario@gmail.com"
$env:SMTP_PASS    = "xxxx xxxx xxxx xxxx"
$env:MAIL_TO      = "tuusuario@gmail.com"

# Opcionales
# $env:LLM_MODEL       = "gemini-3.5-flash"
# $env:TWEET_MIN_SCORE = "55"
# $env:TWEETS_ENABLED  = "0"
# $env:DRY_RUN         = "1"

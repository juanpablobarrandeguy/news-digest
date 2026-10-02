# Daily News Digest

An email in your inbox at ~08:00 ART every morning with the news from the last
~28 hours, in five sections: **AI** (the big players and the state of the art),
**Tech & Data**, **World** (US, Ukraine/Russia, Israel/Middle East), **Argentina**
and **CABA**. One paragraph per story, a link at the end of each.

The stories are not just the newest ones: an LLM "editor" picks, per section, the
ones that match the reader's interests (`SECTION_INTERESTS` in `digest/config.py`).

**Argentina** and **CABA** are summarized in Spanish; everything else in English.
Configurable per section.

Runs entirely on free infrastructure — GitHub Actions for the cron, Resend (SMTP)
for delivery, Gemini's free API tier for picking and summarizing. No server, no cost.

```
RSS feeds ──► dedupe + rank ──► LLM editor ──► LLM summarize ──┬─► HTML email ──► Resend SMTP
                    ▲                                          │        ▲
              state/seen.json ◄────────────────────────────────┼────────┘
                                                               └─► trending ──┘
```

All model calls go through `digest/llm.py`. Swapping providers is one env var.

## Setup

### 1. Push to GitHub

A private repo is fine. Private repos get 2,000 free Actions minutes a month;
this run uses about one.

### 2. Resend API key

The digest is sent from `digest@barrandeguydev.com` through Resend's SMTP relay
(`smtp.resend.com:465`, user `resend`). The domain is already verified in Resend.

Resend → API Keys → Create API Key: permission **Sending access**, domain
`barrandeguydev.com`. One key just for this job, so it can be revoked on its own.

### 3. Gemini API key

Grab a free key at <https://aistudio.google.com/apikey>. No credit card required.

No model ID to maintain: with `LLM_MODEL` unset, each run asks the API for the
newest stable `gemini-X.Y-flash` and uses that. If you pin `LLM_MODEL` and Google
retires it, the run switches to the current one and the email footer says so.
A run makes a handful of requests (editor, 2–3 summary batches, trending), well
within the free tier; rate limits (429) are retried with backoff.

### 4. Repository secrets

Settings → Secrets and variables → Actions → **Secrets**:

| Secret | Value |
|---|---|
| `LLM_API_KEY` | your Gemini key |
| `SMTP_PASS` | the Resend API key |
| `MAIL_TO` | where the digest goes |

Optional overrides under the **Variables** tab: `LLM_PROVIDER`, `LLM_MODEL`,
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `MAIL_FROM`, `TWEETS_ENABLED`, `TWEET_LANE`.
To go back to Gmail: `SMTP_HOST=smtp.gmail.com`, `SMTP_USER`=the Gmail address,
`MAIL_FROM`=the same address, and an app password in `SMTP_PASS`.

### 5. Verify the feeds

```bash
python verify_feeds.py
```

Every feed should report OK. Argentine outlets rearrange their RSS paths more
often than the international ones, so fix or drop anything marked DEAD in
`digest/config.py` before going live. Página/12's path is confirmed current;
the rest are best-known-good and worth checking.

### 6. Test it

Actions → Daily News Digest → Run workflow, with **dry run** checked. That prints
the digest to the job log without emailing or touching state. Run it again
unchecked and check your inbox.

### 7. Confirm the schedule took

After the first successful manual run, check that `state/seen.json` got a commit
from `github-actions[bot]`. That commit is what proves the workflow has write
permission — if it's missing, the digest will repeat stories every morning.

The first scheduled run lands the next day at ~07:50 ART. GitHub sometimes
ignores the very first cron on a new workflow, so if nothing arrives on day one,
check Actions before debugging anything else.

## Local use (Windows / PowerShell)

```powershell
pip install -r requirements.txt

# Cargá las variables (copiá el bloque de env.example.ps1 con tus valores)
$env:LLM_API_KEY = "tu-key"
$env:DRY_RUN     = "1"
python run.py

# Para una corrida real, agregá SMTP_PASS (API key de Resend) / MAIL_TO y sacá DRY_RUN
Remove-Item Env:DRY_RUN
```

Si `python` no responde, probá `py -3`.

## Local use (bash)

```bash
pip install -r requirements.txt

# Print without sending — no email, no state written
DRY_RUN=1 LLM_PROVIDER=none python run.py

# Full run
export SMTP_PASS=re_xxxxxxxx MAIL_TO=you@example.com
export LLM_API_KEY=... LLM_PROVIDER=gemini
python run.py

# Offline test suite — synthetic feeds, no network
python smoke_test.py
```

## The "Noticias viralizables / trending" section

At the end of the email: which of the day's stories are worth posting about on
LinkedIn, the brand's Instagram or X, scored 0-100, with 2-3 possible entry
points and a suggested format each.

It does **not** write the posts. It surfaces topics and framings — you supply the
take. On political stories it gives the factual hook and names what people
disagree about, without picking a side.

Set your lane in `TWEET_LANE` (`digest/config.py` or a repo variable). The
default assumes infra/cloud/AI plus Argentine current affairs. Raise
`TWEET_MIN_SCORE` if too much clears the bar; most days should surface one or
two things, not five. `TWEETS_ENABLED=0` turns the section off.

The scoring prompt is told to be harsh, so an empty section is a normal outcome
and means nothing was worth posting about.

## Configuration

Everything lives in `digest/config.py` or is overridable by environment variable.

| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini`, `groq`, `anthropic`, or `none` |
| `LLM_MODEL` | provider default | Override when a model ID is retired |
| `LOOKBACK_HOURS` | `28` | Window for "recent" |
| `LIMIT_AI` / `LIMIT_TECH` / `LIMIT_WORLD` / `LIMIT_NACIONAL` / `LIMIT_CABA` | `5` | Stories per section |
| `EDITOR_ENABLED` | `1` | `0` skips the relevance editor and keeps the newest stories |
| `EDITOR_POOL` | `30` | Candidates per section the editor chooses from |
| `LANG_NACIONAL` / `LANG_CABA` | Spanish | Output language for the Argentine sections |
| `LANG_AI` / `LANG_TECH` / `LANG_WORLD` | English | Output language per section |
| `STATE_RETENTION_DAYS` | `14` | How long a URL stays suppressed |
| `TIMEZONE` | `America/Argentina/Buenos_Aires` | Date shown in the header |
| `DRY_RUN` | unset | `1` prints instead of sending |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` | `smtp.resend.com` / `465` / `resend` | Mail relay |
| `MAIL_FROM` | `digest@barrandeguydev.com` | Must be on a domain verified in Resend |
| `TWEETS_ENABLED` | `1` | `0` drops the tweet-angles section |
| `TWEET_LANE` | infra/cloud/AI + AR | What you post about |
| `TWEET_MIN_SCORE` | `55` | Bar an angle must clear |
| `TWEET_MAX_ANGLES` | `3` | Ceiling per email |

`LLM_PROVIDER=none` skips the model entirely and uses each feed's own description
as the paragraph. Uglier, but it works with zero API keys.

**Adding feeds:** append to `FEEDS` in `digest/config.py` with a `name`, `url`,
`category` (`ai` / `tech` / `world` / `nacional` / `caba`), and a `weight` — weight only
breaks ties when stories compete for a slot. Run `verify_feeds.py` afterwards.

**Source mix:** the national feeds deliberately span the Argentine editorial
spectrum rather than clustering on one group's coverage, and the summarizer is
instructed to describe events rather than adopt any single outlet's framing.
Adjust the list to taste — just keep in mind that narrowing it narrows what you
see each morning.

## Design notes

**Relevance is decided by an editor pass, not by the feed order.** Ranking keeps
the ~30 freshest candidates per section; one LLM call sees all of them next to
`SECTION_INTERESTS` and returns ids per section. Ids outside a section are
ignored, short answers are topped up from the ranking, and if the call fails the
ranking alone decides. Edit `SECTION_INTERESTS` to retune what gets through.

**CABA is carved out of the national feeds by keyword** (`CABA_KEYWORDS`, whole
words). Ambiguous names like Belgrano or Flores are left out on purpose.

**Quiet failures are printed in the email.** Dead feeds, a failed editor or
summary call, a missing key or a retired model each add a line to an "Avisos"
footer, so degraded output doesn't go unnoticed for weeks.

**Sections are summarized in their own language.** National stories stay in
Spanish instead of taking a lossy translation hop through English. Articles are
grouped by target language before batching, so this costs no extra API calls —
one request per language, not one per section.

**The model never emits URLs.** It receives numbered articles and returns ids;
real links are stitched back on afterwards. This is the single most important
detail — ask an LLM for a link and you get a plausible 404.

**The tweet section fails soft.** If that call errors or returns garbage, the
section is dropped and the digest goes out without it. It is never allowed to
block the email.

**Failures degrade, they don't cascade.** A dead feed is logged and skipped. If
the LLM times out, rate-limits, or returns garbage, that batch falls back to RSS
snippets and the email still arrives.

**Dedup persists both URL and normalized headline.** The same story from three
outlets collapses to one, and the losing variants are remembered too — otherwise
they resurface the next morning once the winner is marked as seen.

**The state commit keeps the workflow alive.** GitHub disables scheduled workflows
after 60 days of repository inactivity. The daily state commit counts as activity,
so this never trips.

## Known quirks

- **Cron drift.** GitHub's scheduler is best-effort and runs late under load —
  occasionally 15+ minutes. Hence the 10:50 UTC schedule for an 08:00 target. If
  you need punctuality, this is the wrong scheduler.
- **Argentina has no DST**, so 10:50 UTC is permanently 07:50 ART. Nothing to
  maintain. If you move somewhere with DST, the cron will need seasonal edits.
- **Feeds rot.** Outlets restructure or kill their RSS. If a section goes quiet
  for a few days, check the workflow log — dead feeds are logged by name.
- **Quiet days.** If nothing new clears the filters, the run exits without
  sending rather than mailing you an empty digest.

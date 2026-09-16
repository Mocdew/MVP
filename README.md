# Deal Desk

Brand-deal infrastructure for creators. Connect YouTube, log a deal, attach the posts that fulfilled it, generate a report the brand will accept.

Pitch and reasoning: [brand-deal-infrastructure.md](brand-deal-infrastructure.md).

## What's built (week 1–3 of the plan)

- Google sign-in
- YouTube connect (OAuth, offline refresh, tokens encrypted at rest)
- Ingest: last 200 uploads → `posts` + append-only `post_metrics` snapshots; best-effort watch time from the Analytics API
- Deals, deliverables, attach-a-post-by-URL
- Baseline: median of the creator's last 20 organic posts, same format, published before the sponsored post
- Reports: frozen `snapshot_json`, public `/r/<token>` page, PDF export
- `POST /internal/refresh` for a daily cron
- Instrumentation: `account_connected`, `deal_logged`, `deliverable_attached`, `report_generated`, `report_viewed`

Not built yet: Instagram (week 4), media kit (week 5), rate index (month 3+).

## Run it locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then fill it in — see below
flask --app run db upgrade      # or: flask --app run shell -c "from dealdesk.db import db; db.create_all()"
flask --app run run --debug
```

Open http://localhost:5000.

### .env

| Key | Where it comes from |
|---|---|
| `SECRET_KEY` | anything long and random |
| `TOKEN_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Cloud Console → APIs & Services → Credentials → *Create OAuth client ID* (Web application). Add `http://localhost:5000/auth/google/callback` **and** `http://localhost:5000/connect/youtube/callback` as authorised redirect URIs. |
| `DATABASE_URL` | leave as SQLite locally; Neon/Supabase Postgres URL on deploy |
| `INTERNAL_REFRESH_TOKEN` | anything; the cron sends it as `Authorization: Bearer …` |

### Google Cloud setup (once)

1. Create a project. Enable **YouTube Data API v3** and **YouTube Analytics API**.
2. OAuth consent screen → External → add scopes `openid`, `email`, `profile`, `youtube.readonly`, `yt-analytics.readonly`.
3. Leave the app in **Testing** and add each design partner's Google email as a test user (up to 100). No verification needed until public launch.

### Migrations

First time: `flask --app run db init && flask --app run db migrate -m "initial"` then `db upgrade`. After that, `db migrate` + `db upgrade` on every model change. Never `ALTER TABLE` by hand.

### PDF export

`weasyprint` needs GTK on Windows — install via [their instructions](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows) or skip it locally; the `/r/<token>.pdf` route returns 503 if it isn't importable. It works out of the box on Linux (Render).

## Tests

```bash
pytest
```

No network; OAuth is bypassed by setting `session["user_id"]`.

## Deploy (Render)

- Web service: `gunicorn run:app`
- Cron job, daily: `curl -X POST -H "Authorization: Bearer $INTERNAL_REFRESH_TOKEN" https://<host>/internal/refresh`
- Set every `.env` key as an environment variable; point `DATABASE_URL` at Postgres.

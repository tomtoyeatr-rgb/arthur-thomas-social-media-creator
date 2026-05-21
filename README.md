# Arthur Thomas Social Media Creator

A Streamlit MVP for creating, reviewing, approving, scheduling, and dry-run publishing social media content for Arthur Thomas Properties.

The app is designed so no post can publish unless it has been manually approved. Publishing defaults to dry-run mode and only prints and logs posts unless `ENABLE_PUBLISHING=true` and `DRY_RUN=false`.

## Features

- Generate social media drafts with the OpenAI API when configured
- Local fallback draft generator when no API key is present
- Store posts in SQLite
- Review, edit, approve, reject, and schedule posts
- Dashboard counts for draft, approved, scheduled, and posted content
- Calendar view for scheduled posts
- Brand safety checks for fair housing risk, political content, confidential details, legal threats, eviction commentary, resident shaming, fabricated property details, unapproved pricing, guaranteed returns, profanity, and discriminatory language
- Action logging for created, edited, approved, rejected, scheduled, and publishing events
- Scheduler process powered by APScheduler

## Setup

1. Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install requirements:

```powershell
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

4. Add `OPENAI_API_KEY` in `.env`.

The app still runs without an API key, but it will use the local fallback generator.

5. Run the Streamlit app:

```powershell
streamlit run app.py
```

6. Generate a draft from the Generate Post page.

7. Approve and schedule a post from the Review Posts page.

8. Run the scheduler in dry-run mode:

```powershell
python scheduler.py
```

## Streamlit Community Cloud

To deploy on Streamlit Community Cloud:

1. Put this project in a GitHub repository.
2. Do not upload `.env`, `.venv`, `__pycache__`, or the SQLite database file.
3. In Streamlit Cloud, create an app from the GitHub repository.
4. Set the main file path to `app.py`.
5. Add private values in Streamlit Cloud Secrets instead of GitHub.

Use this secrets format:

```toml
OPENAI_API_KEY = "paste_openai_key_here"
ENABLE_PUBLISHING = "false"
DRY_RUN = "true"
THREADS_ACCESS_TOKEN = "paste_threads_token_here"
THREADS_API_BASE_URL = "https://graph.threads.net/v1.0"
```

## Environment Variables

```env
OPENAI_API_KEY=
ENABLE_PUBLISHING=false
DRY_RUN=true
META_ACCESS_TOKEN=
META_PAGE_ID=
INSTAGRAM_BUSINESS_ACCOUNT_ID=
THREADS_ACCESS_TOKEN=
THREADS_API_BASE_URL=https://graph.threads.net/v1.0
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_ORG_ID=
```

## Publishing Behavior

MVP publishing is intentionally conservative.

- Posts must have `approved_at` set before publishing.
- `ENABLE_PUBLISHING=false` keeps the system in dry-run behavior.
- `DRY_RUN=true` prints and logs the post instead of sending it to a platform.
- Threads text publishing is supported when `THREADS_ACCESS_TOKEN` is configured.
- Facebook, Instagram, LinkedIn, and Google Business Profile live adapters are placeholders for future integrations.

To allow live Threads posting, set both of these in `.env`:

```env
ENABLE_PUBLISHING=true
DRY_RUN=false
```

The post still must be manually approved before the scheduler can publish it.

Threads publishing uses Meta's two-step flow:

1. Create a text container with `POST /me/threads`.
2. Publish that container with `POST /me/threads_publish`.

## Database

The SQLite database is created automatically as `arthur_thomas_social.db`.

Main table: `posts`

- `id`
- `platform`
- `topic`
- `audience`
- `caption`
- `hashtags`
- `image_prompt`
- `status`
- `scheduled_at`
- `created_at`
- `approved_at`
- `posted_at`
- `notes`

Status options:

- `draft`
- `needs_review`
- `approved`
- `scheduled`
- `posted`
- `rejected`
- `failed`

The app also creates `action_logs` to track every important action.

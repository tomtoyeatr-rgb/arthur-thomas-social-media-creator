import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path(os.getenv("DATABASE_PATH", "arthur_thomas_social.db"))

STATUSES = {
    "draft",
    "needs_review",
    "approved",
    "scheduled",
    "posted",
    "rejected",
    "failed",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                topic TEXT NOT NULL,
                audience TEXT NOT NULL,
                caption TEXT NOT NULL,
                hashtags TEXT NOT NULL,
                image_prompt TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                scheduled_at TEXT,
                created_at TEXT NOT NULL,
                approved_at TEXT,
                posted_at TEXT,
                notes TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES posts(id)
            )
            """
        )
        conn.commit()


def dict_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def log_action(post_id: int | None, action: str, details: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO action_logs (post_id, action, details, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, action, details, utc_now_iso()),
        )
        conn.commit()


def create_post(
    *,
    platform: str,
    topic: str,
    audience: str,
    caption: str,
    hashtags: str,
    image_prompt: str,
    status: str = "needs_review",
    notes: str = "",
) -> int:
    if status not in STATUSES:
        raise ValueError(f"Invalid post status: {status}")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO posts (
                platform, topic, audience, caption, hashtags, image_prompt,
                status, created_at, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                platform,
                topic,
                audience,
                caption,
                hashtags,
                image_prompt,
                status,
                utc_now_iso(),
                notes,
            ),
        )
        post_id = int(cursor.lastrowid)
        conn.commit()

    log_action(post_id, "created", f"Created post with status {status}.")
    return post_id


def update_post(post_id: int, **fields: Any) -> None:
    allowed = {
        "platform",
        "topic",
        "audience",
        "caption",
        "hashtags",
        "image_prompt",
        "status",
        "scheduled_at",
        "approved_at",
        "posted_at",
        "notes",
    }
    invalid = set(fields) - allowed
    if invalid:
        raise ValueError(f"Unsupported fields: {', '.join(sorted(invalid))}")
    if "status" in fields and fields["status"] not in STATUSES:
        raise ValueError(f"Invalid post status: {fields['status']}")
    if not fields:
        return

    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values())
    values.append(post_id)

    with get_connection() as conn:
        conn.execute(f"UPDATE posts SET {assignments} WHERE id = ?", values)
        conn.commit()


def get_post(post_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    return dict_from_row(row)


def list_posts(status: str | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM posts WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM posts ORDER BY created_at DESC"
            ).fetchall()
    return [dict(row) for row in rows]


def get_status_counts() -> dict[str, int]:
    counts = {status: 0 for status in STATUSES}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM posts GROUP BY status"
        ).fetchall()
    for row in rows:
        counts[row["status"]] = int(row["count"])
    return counts


def get_due_scheduled_posts(now_iso: str | None = None) -> list[dict[str, Any]]:
    now_iso = now_iso or utc_now_iso()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM posts
            WHERE status = 'scheduled'
              AND scheduled_at IS NOT NULL
              AND scheduled_at <= ?
              AND approved_at IS NOT NULL
            ORDER BY scheduled_at ASC
            """,
            (now_iso,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_action_logs(limit: int = 100) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM action_logs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]

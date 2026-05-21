import os
from typing import Any
import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def publishing_settings() -> dict[str, bool]:
    return {
        "enable_publishing": env_bool("ENABLE_PUBLISHING", False),
        "dry_run": env_bool("DRY_RUN", True),
    }


def _threads_post_text(post: dict[str, Any]) -> dict[str, Any]:
    access_token = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
    if not access_token:
        return {
            "success": False,
            "dry_run": False,
            "message": "Threads publishing failed: THREADS_ACCESS_TOKEN is missing.",
        }

    text = f"{post['caption'].strip()}\n\n{post['hashtags'].strip()}".strip()
    if len(text) > 500:
        return {
            "success": False,
            "dry_run": False,
            "message": "Threads publishing failed: post is over 500 characters.",
        }

    base_url = os.getenv("THREADS_API_BASE_URL", "https://graph.threads.net/v1.0").rstrip("/")

    container_response = requests.post(
        f"{base_url}/me/threads",
        data={
            "media_type": "TEXT",
            "text": text,
            "access_token": access_token,
        },
        timeout=30,
    )
    if not container_response.ok:
        return {
            "success": False,
            "dry_run": False,
            "message": f"Threads container creation failed: {container_response.text}",
        }

    creation_id = container_response.json().get("id")
    if not creation_id:
        return {
            "success": False,
            "dry_run": False,
            "message": f"Threads container creation did not return an id: {container_response.text}",
        }

    publish_response = requests.post(
        f"{base_url}/me/threads_publish",
        data={
            "creation_id": creation_id,
            "access_token": access_token,
        },
        timeout=30,
    )
    if not publish_response.ok:
        return {
            "success": False,
            "dry_run": False,
            "message": f"Threads publishing failed: {publish_response.text}",
        }

    published = publish_response.json()
    published_id = published.get("id", "unknown")
    return {
        "success": True,
        "dry_run": False,
        "message": f"Published to Threads. Threads post id: {published_id}",
    }


def publish_post(post: dict[str, Any]) -> dict[str, Any]:
    if post.get("approved_at") is None:
        return {
            "success": False,
            "dry_run": True,
            "message": "Blocked: post is not manually approved.",
        }

    settings = publishing_settings()
    if not settings["enable_publishing"] or settings["dry_run"]:
        message = (
            f"DRY RUN publish for {post['platform']} post {post['id']}: "
            f"{post['caption']} {post['hashtags']}"
        )
        print(message)
        return {"success": True, "dry_run": True, "message": message}

    if post.get("platform") == "Threads":
        return _threads_post_text(post)

    return {
        "success": False,
        "dry_run": False,
        "message": (
            "Live publishing adapters are not enabled in this MVP. "
            "Add Meta, Instagram, LinkedIn, or Google Business Profile API code before live posting."
        ),
    }

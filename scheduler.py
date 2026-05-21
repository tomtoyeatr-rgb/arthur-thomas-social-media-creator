from database import get_due_scheduled_posts, init_db, log_action, update_post, utc_now_iso
from publisher import publish_post


def process_due_posts() -> int:
    init_db()
    due_posts = get_due_scheduled_posts()
    processed = 0

    for post in due_posts:
        if not post.get("approved_at"):
            update_post(post["id"], status="failed", notes="Publishing blocked because post was not approved.")
            log_action(post["id"], "publish_blocked", "Post was not manually approved.")
            continue

        result = publish_post(post)
        log_action(post["id"], "publish_attempt", result["message"])

        if result["success"]:
            update_post(
                post["id"],
                status="posted",
                posted_at=utc_now_iso(),
                notes=("Dry-run completed. " if result.get("dry_run") else "Published live. ") + (post.get("notes") or ""),
            )
            log_action(post["id"], "posted", "Post processed by scheduler.")
        else:
            update_post(post["id"], status="failed", notes=result["message"])
            log_action(post["id"], "failed", result["message"])

        processed += 1

    return processed


def start_scheduler() -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler

    init_db()
    scheduler = BlockingScheduler()
    scheduler.add_job(process_due_posts, "interval", minutes=1, id="publish_due_posts", replace_existing=True)
    print("Arthur Thomas Social Media Creator scheduler is running. Press Ctrl+C to stop.")
    scheduler.start()


if __name__ == "__main__":
    start_scheduler()

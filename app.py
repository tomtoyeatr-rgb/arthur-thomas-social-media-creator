import os
from datetime import datetime, time, timezone

import streamlit as st
from dotenv import load_dotenv

from content_agent import AUDIENCES, CONTENT_CATEGORIES, PLATFORMS, generate_social_post
from database import (
    create_post,
    get_post,
    get_status_counts,
    init_db,
    list_action_logs,
    list_posts,
    log_action,
    update_post,
    utc_now_iso,
)
from publisher import publishing_settings
from safety import approved_hashtag_text, run_brand_safety


load_dotenv()
init_db()

st.set_page_config(
    page_title="Arthur Thomas Social Media Creator",
    layout="wide",
)


def local_datetime_to_utc_iso(date_value, time_value) -> str:
    dt = datetime.combine(date_value, time_value)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def show_safety_result(platform: str, caption: str, hashtags: str, image_prompt: str, property_notes: str = ""):
    result = run_brand_safety(
        platform=platform,
        caption=caption,
        hashtags=hashtags,
        image_prompt=image_prompt,
        property_notes=property_notes,
    )
    if result.blocked:
        st.error(result.summary())
    elif result.flags or result.warnings:
        st.warning(result.summary())
    else:
        st.success(result.summary())
    return result


def dashboard_page() -> None:
    st.title("Arthur Thomas Social Media Creator")
    st.caption("Create, review, approve, schedule, and dry-run publish brand-safe content.")

    counts = get_status_counts()
    cols = st.columns(4)
    cols[0].metric("Drafts", counts.get("draft", 0) + counts.get("needs_review", 0))
    cols[1].metric("Approved", counts.get("approved", 0))
    cols[2].metric("Scheduled", counts.get("scheduled", 0))
    cols[3].metric("Posted", counts.get("posted", 0))

    st.subheader("Recent Posts")
    posts = list_posts()[:10]
    if posts:
        st.dataframe(
            [
                {
                    "ID": post["id"],
                    "Platform": post["platform"],
                    "Topic": post["topic"],
                    "Audience": post["audience"],
                    "Status": post["status"],
                    "Scheduled": post["scheduled_at"],
                }
                for post in posts
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No posts yet. Start with Generate Post.")

    st.subheader("Recent Activity")
    logs = list_action_logs(limit=10)
    if logs:
        st.dataframe(
            [
                {
                    "Time": log["created_at"],
                    "Post": log["post_id"],
                    "Action": log["action"],
                    "Details": log["details"],
                }
                for log in logs
            ],
            use_container_width=True,
            hide_index=True,
        )


def generate_page() -> None:
    st.title("Generate Post")

    with st.form("generate_post"):
        cols = st.columns(2)
        platform = cols[0].selectbox("Platform", PLATFORMS)
        audience = cols[1].selectbox("Audience", AUDIENCES)
        topic = st.text_input("Topic", placeholder="Example: winter maintenance reminders for rental owners")
        tone = st.text_input("Tone", value="professional, calm, helpful")
        category = st.selectbox("Content category", CONTENT_CATEGORIES)
        property_notes = st.text_area("Optional property notes", placeholder="Use only approved, non-confidential details.")
        submitted = st.form_submit_button("Generate Draft")

    if submitted:
        if not topic.strip():
            st.error("Please enter a topic.")
        else:
            with st.spinner("Drafting with Arthur Thomas brand rules..."):
                st.session_state.generated_post = generate_social_post(
                    platform=platform,
                    audience=audience,
                    topic=topic,
                    tone=tone,
                    category=category,
                    property_notes=property_notes,
                )
                st.session_state.generated_meta = {
                    "platform": platform,
                    "audience": audience,
                    "topic": topic,
                    "property_notes": property_notes,
                }

    generated = st.session_state.get("generated_post")
    meta = st.session_state.get("generated_meta")
    if generated and meta:
        st.subheader("Draft Output")
        caption = st.text_area("Caption", value=generated["caption"], height=180)
        hashtags = st.text_input("Hashtags", value=generated["hashtags"])
        image_prompt = st.text_area("Image prompt", value=generated["image_prompt"], height=110)

        safety = show_safety_result(
            meta["platform"],
            caption,
            hashtags,
            image_prompt,
            meta.get("property_notes", ""),
        )

        st.write("Compliance notes:", generated.get("compliance_notes", "Human review required."))
        if st.button("Save as Draft for Review", disabled=safety.blocked):
            post_id = create_post(
                platform=meta["platform"],
                topic=meta["topic"],
                audience=meta["audience"],
                caption=caption,
                hashtags=hashtags,
                image_prompt=image_prompt,
                status="needs_review",
                notes=safety.summary(),
            )
            log_action(post_id, "safety_checked", safety.summary())
            st.success(f"Draft saved for review as post {post_id}.")
            st.session_state.pop("generated_post", None)
            st.session_state.pop("generated_meta", None)


def review_page() -> None:
    st.title("Review Posts")

    posts = [post for post in list_posts() if post["status"] in {"draft", "needs_review", "approved", "scheduled", "rejected", "failed"}]
    if not posts:
        st.info("No posts to review.")
        return

    post_options = {
        f"#{post['id']} | {post['platform']} | {post['status']} | {post['topic']}": post["id"]
        for post in posts
    }
    selected_label = st.selectbox("Select post", list(post_options.keys()))
    post_id = post_options[selected_label]
    post = get_post(post_id)
    if not post:
        st.error("Post not found.")
        return

    cols = st.columns(3)
    cols[0].write(f"Status: {post['status']}")
    cols[1].write(f"Created: {post['created_at']}")
    cols[2].write(f"Approved: {post['approved_at'] or 'No'}")

    caption = st.text_area("Caption", value=post["caption"], height=220)
    hashtags = st.text_input("Hashtags", value=post["hashtags"])
    image_prompt = st.text_area("Image prompt", value=post["image_prompt"] or "", height=120)
    notes = st.text_area("Notes", value=post["notes"] or "", height=100)

    safety = show_safety_result(post["platform"], caption, hashtags, image_prompt)

    action_cols = st.columns(4)
    if action_cols[0].button("Save Edits"):
        update_post(post_id, caption=caption, hashtags=hashtags, image_prompt=image_prompt, notes=notes)
        log_action(post_id, "edited", "Post content edited.")
        st.success("Edits saved.")
        st.rerun()

    if action_cols[1].button("Approve", disabled=safety.blocked):
        update_post(
            post_id,
            caption=caption,
            hashtags=hashtags,
            image_prompt=image_prompt,
            notes=notes or safety.summary(),
            status="approved",
            approved_at=utc_now_iso(),
        )
        log_action(post_id, "approved", "Post manually approved.")
        st.success("Post approved.")
        st.rerun()

    if action_cols[2].button("Reject"):
        update_post(post_id, status="rejected", notes=notes or "Rejected during review.")
        log_action(post_id, "rejected", "Post manually rejected.")
        st.warning("Post rejected.")
        st.rerun()

    st.subheader("Schedule")
    schedule_cols = st.columns(3)
    schedule_date = schedule_cols[0].date_input("Date")
    schedule_time = schedule_cols[1].time_input("Time", value=time(hour=9, minute=0))
    can_schedule = bool(post.get("approved_at")) and post["status"] in {"approved", "scheduled"}
    if schedule_cols[2].button("Schedule", disabled=not can_schedule):
        scheduled_at = local_datetime_to_utc_iso(schedule_date, schedule_time)
        update_post(post_id, status="scheduled", scheduled_at=scheduled_at)
        log_action(post_id, "scheduled", f"Scheduled for {scheduled_at}.")
        st.success("Post scheduled.")
        st.rerun()

    if not can_schedule:
        st.info("Approve the post before scheduling.")


def calendar_page() -> None:
    st.title("Calendar")
    scheduled = [post for post in list_posts("scheduled")]
    if not scheduled:
        st.info("No scheduled posts.")
        return

    scheduled.sort(key=lambda post: post.get("scheduled_at") or "")
    st.dataframe(
        [
            {
                "Scheduled": post["scheduled_at"],
                "Platform": post["platform"],
                "Topic": post["topic"],
                "Audience": post["audience"],
                "Caption": post["caption"],
            }
            for post in scheduled
        ],
        use_container_width=True,
        hide_index=True,
    )


def settings_page() -> None:
    st.title("Settings")
    settings = publishing_settings()

    st.subheader("Publishing Controls")
    st.write("Dry run mode:", "On" if settings["dry_run"] else "Off")
    st.write("Publishing enabled:", "Yes" if settings["enable_publishing"] else "No")
    if settings["enable_publishing"] and not settings["dry_run"]:
        st.warning("Live publishing is allowed. Only manually approved scheduled posts can publish.")
    else:
        st.info("Dry-run mode is active. Posts will be printed and logged instead of posted live.")

    st.subheader("API Key Status")
    api_status = "Configured" if os.getenv("OPENAI_API_KEY", "").strip() else "Missing"
    st.write("OpenAI API key:", api_status)
    st.write("Meta access token:", "Configured" if os.getenv("META_ACCESS_TOKEN", "").strip() else "Missing")
    st.write("Threads access token:", "Configured" if os.getenv("THREADS_ACCESS_TOKEN", "").strip() else "Missing")
    st.write("LinkedIn access token:", "Configured" if os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip() else "Missing")

    st.subheader("Approved Hashtags")
    st.code(approved_hashtag_text())


PAGES = {
    "Dashboard": dashboard_page,
    "Generate Post": generate_page,
    "Review Posts": review_page,
    "Calendar": calendar_page,
    "Settings": settings_page,
}

with st.sidebar:
    st.header("Arthur Thomas")
    page = st.radio("Page", list(PAGES.keys()))

PAGES[page]()

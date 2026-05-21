import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

from safety import APPROVED_HASHTAGS, run_brand_safety
from settings import get_setting


load_dotenv()

BRAND_RULES_PATH = Path("config/arthur_thomas_brand_rules.md")

AUDIENCES = [
    "rental property owners",
    "real estate investors",
    "condo boards",
    "HOA boards",
    "residents",
    "homeowners",
    "vendors",
    "local community",
]

CONTENT_CATEGORIES = [
    "property management education",
    "preventative maintenance",
    "rental owner tips",
    "investor operations",
    "condo/HOA governance",
    "resident reminders",
    "seasonal property care",
    "local New Hampshire / Southern Maine community content",
    "property showcases",
    "company operations",
]

PLATFORMS = ["Facebook", "Instagram", "LinkedIn", "Threads"]


def load_brand_rules() -> str:
    if BRAND_RULES_PATH.exists():
        return BRAND_RULES_PATH.read_text(encoding="utf-8")
    return "Arthur Thomas Properties is professional, calm, clear, concise, and property-management focused."


def _pick_hashtags(audience: str, category: str) -> list[str]:
    tags = ["#ArthurThomasProperties", "#PropertyManagement"]
    if "investor" in audience or "investor" in category:
        tags.extend(["#RealEstateInvestor", "#RentalProperty"])
    if "condo" in audience.lower() or "hoa" in audience.lower() or "governance" in category:
        tags.extend(["#CondoManagement", "#HOAManagement"])
    if "maintenance" in category or "property care" in category:
        tags.extend(["#PreventativeMaintenance", "#PropertyCare"])
    if "resident" in audience or "resident" in category:
        tags.append("#ResidentExperience")
    if "Maine" in category:
        tags.append("#MaineRealEstate")
    else:
        tags.append("#NHRealEstate")

    approved = [tag for tag in tags if tag in APPROVED_HASHTAGS]
    return list(dict.fromkeys(approved))[:8]


def _fallback_post(platform: str, audience: str, topic: str, tone: str, category: str, property_notes: str) -> dict[str, str]:
    tags = _pick_hashtags(audience, category)
    topic_sentence = topic.strip().rstrip(".")
    note_sentence = property_notes.strip().rstrip(".")

    if platform == "LinkedIn":
        caption = (
            f"{topic_sentence} is an important part of thoughtful property management. "
            "Consistent systems, clear communication, and proactive follow-through help protect long-term property value while creating a better experience for residents and owners."
        )
    elif platform in {"Instagram", "Threads"}:
        caption = (
            f"{topic_sentence}.\n\n"
            "A calm, proactive approach keeps property care clear, practical, and easier to manage."
        )
    else:
        caption = (
            f"{topic_sentence} can make a real difference for property owners, residents, and community associations. "
            "The goal is simple: communicate clearly, plan ahead, and solve small issues before they become larger ones."
        )

    if note_sentence:
        caption = f"{caption}\n\nContext to consider: {note_sentence}."

    return {
        "caption": caption,
        "hashtags": " ".join(tags),
        "image_prompt": (
            "Clean, authentic New England property management scene with natural light, "
            "subtle Arthur Thomas Properties branding, professional and calm visual style."
        ),
    }


def _parse_content(raw: str) -> dict[str, str]:
    data = json.loads(raw)
    return {
        "caption": str(data.get("caption", "")).strip(),
        "hashtags": str(data.get("hashtags", "")).strip(),
        "image_prompt": str(data.get("image_prompt", "")).strip(),
    }


def generate_social_post(
    *,
    platform: str,
    audience: str,
    topic: str,
    tone: str,
    category: str,
    property_notes: str = "",
) -> dict[str, str]:
    api_key = get_setting("OPENAI_API_KEY", "").strip()
    brand_rules = load_brand_rules()

    if not api_key:
        content = _fallback_post(platform, audience, topic, tone, category, property_notes)
    else:
        try:
            from openai import OpenAI
        except ImportError:
            content = _fallback_post(platform, audience, topic, tone, category, property_notes)
            content["compliance_notes"] = "OpenAI package is not installed. Local fallback draft was used."
            content["blocked"] = "False"
            return content

        client = OpenAI(api_key=api_key)
        prompt = f"""
Create one social media draft for Arthur Thomas Properties.

Platform: {platform}
Audience: {audience}
Topic: {topic}
Tone: {tone}
Content category: {category}
Optional property notes: {property_notes or "None"}

Return strict JSON with caption, hashtags, and image_prompt.
Use 3 to 8 approved hashtags only.
Never fabricate property details, pricing, legal claims, guaranteed returns, or confidential information.
Manual approval is required before publishing.
"""
        completion = client.chat.completions.create(
            model=get_setting("OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=0.5,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful social media drafting agent for a property management company. "
                        "Follow these brand rules exactly:\n\n" + brand_rules
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = _parse_content(completion.choices[0].message.content or "{}")

    safety = run_brand_safety(
        platform=platform,
        caption=content["caption"],
        hashtags=content["hashtags"],
        image_prompt=content["image_prompt"],
        property_notes=property_notes,
    )
    content["compliance_notes"] = safety.summary()
    content["blocked"] = str(safety.blocked)
    return content

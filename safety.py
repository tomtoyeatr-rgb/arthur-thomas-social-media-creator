import re
from dataclasses import dataclass, field


APPROVED_HASHTAGS = {
    "#ArthurThomasProperties",
    "#PropertyManagement",
    "#NHRealEstate",
    "#NewHampshireRealEstate",
    "#MaineRealEstate",
    "#RentalProperty",
    "#RealEstateInvestor",
    "#CondoManagement",
    "#HOAManagement",
    "#PreventativeMaintenance",
    "#PropertyCare",
    "#ResidentExperience",
}

APPROVED_EMOJIS = {
    "\U0001f3e1",
    "\U0001f527",
    "\u2744\ufe0f",
    "\U0001f33f",
    "\U0001f4cd",
    "\u2705",
    "\U0001f4c8",
}

PLATFORM_RULES = {
    "Facebook": "Community-focused, educational, medium length.",
    "Instagram": "Concise, visual-first, include image prompt, max 3 emojis.",
    "LinkedIn": "Professional, strategic, operations-focused, avoid emojis.",
    "Threads": "Concise, conversational, property-management focused, and under 500 characters.",
}

BLOCK_PATTERNS = [
    ("political content", r"\b(republican|democrat|election|vote for|maga|liberal|conservative)\b"),
    ("legal threat", r"\b(we will sue|lawsuit|legal action|take you to court|criminal charges)\b"),
    ("eviction commentary", r"\b(evict|eviction|kick out|throw out)\b"),
    ("resident shaming", r"\b(bad tenant|nightmare tenant|deadbeat|lazy resident|problem tenant)\b"),
    ("guaranteed returns", r"\b(guaranteed roi|guaranteed return|risk-free|risk free|cannot lose)\b"),
    ("unapproved pricing", r"(\$\s?\d[\d,]*(?:\.\d{2})?|\b\d+%\s*(?:return|roi|yield)\b)"),
    ("profanity", r"\b(damn|hell|shit|fuck|crap|asshole)\b"),
    ("confidential contact detail", r"[\w.+-]+@[\w-]+\.[\w.-]+|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"),
]

FAIR_HOUSING_PATTERNS = [
    ("family status preference", r"\b(no kids|adults only|perfect for families|ideal for families)\b"),
    ("age preference", r"\b(young professionals|senior only|ideal bachelor pad|bachelor pad)\b"),
    ("religion preference", r"\b(christian community|churchgoers|faith-based tenants)\b"),
    ("disability preference", r"\b(no disabled|able-bodied|not wheelchair accessible)\b"),
    ("race or national origin preference", r"\b(preferred race|english speakers only|no immigrants)\b"),
    ("unsafe housing claim", r"\b(safe neighborhood|crime-free|no crime)\b"),
]

FLAG_PATTERNS = [
    ("possible fabricated property detail", r"\b(newly renovated|ocean view|luxury|brand new|minutes from|walking distance)\b"),
    ("active dispute risk", r"\b(complaint|violation|fine|dispute|late rent|nonpayment)\b"),
    ("legal advice risk", r"\b(legal advice|legally required|the law says|you must by law)\b"),
]


@dataclass
class SafetyResult:
    blocked: bool = False
    flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    compliance_notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.blocked:
            return "Blocked: " + "; ".join(self.flags)
        if self.flags or self.warnings:
            all_notes = self.flags + self.warnings
            return "Needs human review: " + "; ".join(all_notes)
        return "No obvious brand safety issues found. Human approval is still required."


def _find_matches(text: str, patterns: list[tuple[str, str]]) -> list[str]:
    matches = []
    for label, pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(label)
    return matches


def _extract_hashtags(hashtags: str) -> list[str]:
    return re.findall(r"#[A-Za-z0-9]+", hashtags or "")


def _emoji_count(text: str) -> int:
    return sum(text.count(emoji) for emoji in APPROVED_EMOJIS)


def run_brand_safety(
    *,
    platform: str,
    caption: str,
    hashtags: str,
    image_prompt: str = "",
    property_notes: str = "",
) -> SafetyResult:
    text = " ".join([caption or "", hashtags or "", image_prompt or "", property_notes or ""])
    result = SafetyResult()

    result.flags.extend(_find_matches(text, BLOCK_PATTERNS))
    result.flags.extend(_find_matches(text, FAIR_HOUSING_PATTERNS))
    result.blocked = bool(result.flags)

    result.warnings.extend(_find_matches(text, FLAG_PATTERNS))

    tags = _extract_hashtags(hashtags)
    if len(tags) < 3 or len(tags) > 8:
        result.warnings.append("use 3 to 8 approved hashtags")

    unapproved_tags = sorted(tag for tag in tags if tag not in APPROVED_HASHTAGS)
    if unapproved_tags:
        result.warnings.append("unapproved hashtags: " + ", ".join(unapproved_tags))

    if platform == "Instagram" and _emoji_count(caption) > 3:
        result.warnings.append("Instagram posts may use no more than 3 approved emojis")

    if platform == "LinkedIn" and _emoji_count(caption) > 0:
        result.warnings.append("LinkedIn should avoid emojis unless clearly appropriate")

    if platform == "Threads" and len(caption) + len(hashtags) + 1 > 500:
        result.warnings.append("Threads posts should stay under 500 characters including hashtags")

    if platform == "Instagram" and not image_prompt.strip():
        result.warnings.append("Instagram posts should include an image prompt")

    result.compliance_notes.append(PLATFORM_RULES.get(platform, "Follow Arthur Thomas brand rules."))
    result.compliance_notes.append("Manual approval is required before scheduling or publishing.")
    return result


def approved_hashtag_text() -> str:
    return "\n".join(sorted(APPROVED_HASHTAGS))

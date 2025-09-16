"""Rule-based extraction for Meeting Snap baseline slice."""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


DECISION_SIGNALS = [
    "decided",
    "decision",
    "agree",
    "approved",
    "we will",
    "we'll",
    "let's proceed",
    "go with",
]

ACTION_KEYWORDS = [
    "action",
    "todo",
    "next step",
    "next steps",
    "follow up",
    "follow-up",
    "i'll",
    "i will",
    "i'll take",
    "owner:",
]

IMPERATIVE_STARTERS = {
    "send",
    "draft",
    "book",
    "schedule",
    "email",
    "call",
    "ping",
    "update",
    "prepare",
    "create",
    "finalize",
    "review",
    "follow",
    "share",
    "complete",
    "submit",
}

RISK_KEYWORDS = [
    "risk",
    "blocked",
    "blocker",
    "dependency",
    "concern",
    "legal",
    "security",
    "capacity",
    "delay",
    "outage",
]

NEXT_CHECKIN_KEYWORDS = [
    "next meeting",
    "next check-in",
    "next checkin",
    "check-in",
    "checkin",
    "standup",
    "review",
]

QUESTION_PREFIXES = [
    "open",
    "unknown",
    "tbd",
]

DATE_PATTERNS = [
    r"\b(today)\b",
    r"\b(tomorrow)\b",
    r"\b(next\s+(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?)\b",
    r"\b(by\s+(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?)\b",
    r"\b((?:mon|tues|wednes|thurs|fri|satur|sun)day\s+\d{1,2}\s?(?:am|pm))\b",
    r"\b((?:mon|tues|wednes|thurs|fri|satur|sun)day)\b",
    r"\b(by\s+\d{1,2}\s+[A-Za-z]{3,})\b",
    r"\b(\d{1,2}\s+[A-Za-z]{3,})\b",
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{1,2}:\d{2}\s?(?:am|pm)?)\b",
    r"\b(\d{1,2}\s?(?:am|pm))\b",
]


def parse_lines(text: str) -> List[str]:
    """Split transcript text into normalized lines."""
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = _strip_timestamp(line)
        line = _normalize_whitespace(line)
        if line:
            lines.append(line)
    return lines


def extract_decisions(lines: List[str]) -> List[str]:
    """Return decision statements derived from transcript lines."""
    decisions: List[str] = []
    for line in lines:
        _speaker, content = _split_speaker(line)
        if not content:
            continue
        lowered = content.lower()
        if any(signal in lowered for signal in DECISION_SIGNALS):
            statement = _normalize_decision_phrase(content)
            if statement and statement not in decisions:
                decisions.append(statement)
    return decisions


def extract_actions(lines: List[str]) -> List[Dict[str, Optional[str]]]:
    """Return list of action dictionaries with owner and due."""
    actions: List[Dict[str, Optional[str]]] = []
    last_speaker: Optional[str] = None
    for line in lines:
        speaker, content = _split_speaker(line)
        if speaker:
            last_speaker = speaker
        if not content:
            continue
        if _is_action_line(content):
            context_speaker = speaker or last_speaker
            owner = _detect_owner(content, context_speaker)
            due = datephrase_parse(content)
            action_text = _normalize_action_text(content, owner, due)
            if action_text:
                actions.append({
                    "action": action_text,
                    "owner": owner,
                    "due": due,
                })
    return actions


def extract_questions(lines: List[str]) -> List[str]:
    """Return a list of open questions."""
    questions: List[str] = []
    for line in lines:
        _speaker, content = _split_speaker(line)
        if not content:
            continue
        content_lower = content.lower()
        if any(content_lower.startswith(prefix) for prefix in QUESTION_PREFIXES):
            cleaned = _strip_question_prefix(content)
            question_text = sentence_case(cleaned)
            if question_text and question_text not in questions:
                questions.append(question_text)
            continue
        cleaned = _strip_question_prefix(content)
        for fragment in re.findall(r"[^?]*\?", cleaned):
            question = sentence_case(fragment.strip())
            if question and question not in questions:
                questions.append(question)
    return questions


def extract_risks(lines: List[str]) -> List[str]:
    """Return a list of risk or blocker statements."""
    risks: List[str] = []
    for line in lines:
        _speaker, content = _split_speaker(line)
        if not content:
            continue
        lowered = content.lower()
        if any(keyword in lowered for keyword in RISK_KEYWORDS):
            statement = _normalize_risk_phrase(content)
            if statement and statement not in risks:
                risks.append(statement)
    return risks


def extract_next_checkin(lines: List[str]) -> Optional[str]:
    """Return the next check-in description if present."""
    for line in lines:
        _speaker, content = _split_speaker(line)
        lowered = content.lower()
        if any(keyword in lowered for keyword in NEXT_CHECKIN_KEYWORDS):
            match = re.search(
                r"(?i)next\s+(?:meeting|check[- ]?in|standup|review)[^:]*[:\-]?\s*(.*)",
                content,
            )
            if match:
                phrase = match.group(1).strip()
                if not phrase:
                    phrase = datephrase_parse(content) or ""
                phrase = phrase.rstrip(". ")
                if phrase:
                    return sentence_case(phrase)
            date_phrase = datephrase_parse(content)
            if date_phrase:
                return sentence_case(date_phrase)
    return None


def assemble(text: str) -> Dict[str, object]:
    """Extract a snapshot from raw transcript text."""
    lines = parse_lines(text)
    actions = extract_actions(lines)
    snapshot = {
        "decisions": extract_decisions(lines),
        "actions": actions,
        "questions": extract_questions(lines),
        "risks": extract_risks(lines),
        "next_checkin": extract_next_checkin(lines),
    }
    if not snapshot["next_checkin"]:
        fallback_due = _earliest_due(actions)
        if fallback_due:
            snapshot["next_checkin"] = fallback_due
    return snapshot


# Helper functions ---------------------------------------------------------


def _strip_timestamp(text: str) -> str:
    text = re.sub(r"^\s*\[[^\]]+\]\s*", "", text)
    text = re.sub(r"^\s*\([^\)]+\)\s*", "", text)
    text = re.sub(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s?(?:am|pm|AM|PM)?\s*-\s*", "", text)
    return text


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _split_speaker(line: str) -> Tuple[Optional[str], str]:
    match = re.match(r"([A-Za-z][\w'\- ]{0,30}):\s*(.*)", line)
    if match:
        speaker = match.group(1).strip()
        content = match.group(2).strip()
        speaker_lower = speaker.lower()
        label_tokens = {
            "decision",
            "action",
            "actions",
            "question",
            "questions",
            "risk",
            "risks",
            "note",
            "notes",
            "next check-in",
            "next checkin",
        }
        if any(label in speaker_lower for label in label_tokens):
            return None, line.strip()
        return speaker_title(speaker), content
    return None, line.strip()


def _normalize_decision_phrase(text: str) -> str:
    cleaned = re.sub(r"(?i)\bdecision\b[:\-\s]*", "", text)
    cleaned = re.sub(r"(?i)\bwe\s+go\s+with\b", "Go with ", cleaned)
    cleaned = re.sub(r"(?i)\bwe\s+will\b", "Will ", cleaned)
    cleaned = re.sub(r"(?i)\blet's\s+proceed\b", "Proceed", cleaned)
    cleaned = re.sub(r"(?i)\bdecided\b[:\-\s]*", "", cleaned)
    cleaned = re.sub(r"(?i)\bagree(?:d)?\b[:\-\s]*", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = cleaned.strip(" -.")
    return sentence_case(cleaned)


def _is_action_line(content: str) -> bool:
    lowered = content.lower()
    if any(keyword in lowered for keyword in ACTION_KEYWORDS):
        return True
    starter_match = re.match(r"^[*-]?\s*([A-Za-z']+)", content)
    if starter_match and starter_match.group(1).lower() in IMPERATIVE_STARTERS:
        return True
    return False


def _detect_owner(content: str, speaker: Optional[str]) -> Optional[str]:
    owner: Optional[str] = None
    match = re.search(r"(?i)owner[:\-]\s*([A-Za-z@\s]+)", content)
    if match:
        owner_text = match.group(1).strip()
        owner_segment = re.split(r"\bto\b|,|;|\.|\(|\)", owner_text, 1)[0].strip()
        owner = owner_segment.split()[0] if owner_segment else None
    if not owner:
        handle = re.search(r"@([A-Za-z0-9_]+)", content)
        if handle:
            owner = handle.group(1)
    if not owner:
        assigned = re.search(r"\b([A-Z][a-zA-Z]+)\s+to\b", content)
        if assigned:
            owner = assigned.group(1)
    if not owner and speaker and re.search(r"(?i)\bI(?:'ll| will)?\b", content):
        owner = speaker
    return speaker_title(owner) if owner else None


def _normalize_action_text(content: str, owner: Optional[str], due: Optional[str]) -> str:
    text = re.sub(r"(?i)\b(action|todo|next steps?|follow[- ]?up)[:\-]*", "", content)
    text = re.sub(r"(?i)owner[:\-]\s*", "", text)
    text = text.lstrip("-* ")
    if owner:
        pattern = re.compile(rf"\b{re.escape(owner)}\b\s+to\s+", re.IGNORECASE)
        text = pattern.sub("", text)
        text = re.sub(rf"^{re.escape(owner)}\b[\s,:-]*", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"@{re.escape(owner)}\s+", "", text, flags=re.IGNORECASE)
    if owner and re.search(r"(?i)\bI(?:'ll| will)\b", text):
        text = re.sub(r"(?i)\bI(?:'ll| will)\s+", "", text)
    if due:
        text = _remove_due_phrase(text, due)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip(" .")
    return sentence_case(text)


def _remove_due_phrase(text: str, due: str) -> str:
    lowered_due = due.lower()
    patterns = [re.escape(due), re.escape(lowered_due)]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    if lowered_due.startswith("by "):
        remainder = lowered_due[3:]
        text = re.sub(rf"\bby\s+{re.escape(remainder)}\b", "", text, flags=re.IGNORECASE)
    return text


def datephrase_parse(text: str) -> Optional[str]:
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _format_due_phrase(match.group(1))
    return None


def _format_due_phrase(phrase: str) -> str:
    raw = phrase.strip()
    lowered = raw.lower()
    if lowered in {"today", "tomorrow"}:
        return lowered.capitalize()
    if lowered.startswith("next "):
        parts = lowered.split()
        return "Next " + (parts[1].capitalize() if len(parts) > 1 else "")
    if lowered.startswith("by "):
        remainder = lowered[3:]
        return "By " + _smart_capitalize(remainder)
    return _smart_capitalize(raw)


def _smart_capitalize(text: str) -> str:
    words = []
    for word in text.split():
        if re.match(r"\d", word):
            words.append(word)
        elif word.lower() in {"am", "pm"}:
            words.append(word.lower())
        else:
            words.append(word.capitalize())
    return " ".join(words)


def sentence_case(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.endswith("?") or cleaned.endswith("!"):
        ending = cleaned[-1]
        body = cleaned[:-1]
        return (body[:1].upper() + body[1:]).strip() + ending
    return cleaned[:1].upper() + cleaned[1:]


def speaker_title(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    parts = [part for part in re.split(r"\s+", text.strip()) if part]
    return " ".join(part.capitalize() for part in parts) if parts else None


def _normalize_risk_phrase(text: str) -> str:
    cleaned = re.sub(r"(?i)\brisk\b[:\-\s]*", "", text)
    cleaned = re.sub(r"(?i)\bblocker\b[:\-\s]*", "", cleaned)
    cleaned = re.sub(r"(?i)\bconcern\b[:\-\s]*", "", cleaned)
    cleaned = cleaned.strip(" .-")
    return sentence_case(cleaned)


def _strip_question_prefix(text: str) -> str:
    return re.sub(r"(?i)^\s*(?:questions?|two questions|one question|open question)[:\-\s]*", "", text)


def _earliest_due(actions: List[Dict[str, Optional[str]]]) -> Optional[str]:
    for action in actions:
        due = action.get("due")
        if due:
            return due
    return None

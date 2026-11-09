import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse


DATE_PATTERN = re.compile(r"(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日")
TIME_PATTERN = re.compile(r"(?P<hour>\d{1,2})[:：](?P<minute>\d{2})")
DEADLINE_PATTERN = re.compile(
    r"(?P<excerpt>(?:请)?于?"
    r"(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日"
    r"(?:(?P<hour>\d{1,2})[:：](?P<minute>\d{2}))?前"
    r"(?P<action>[^，。；;]+))"
)
AUDIENCE_PATTERN = re.compile(r"(?P<basis>(?:面向|适用于)(?P<audience>[^。；;]+)[。；;]?)")
AUDIENCE_HEADING_PATTERN = re.compile(
    r"(?:^|\n)(?:[一二三四五六七八九十]+、)?"
    r"(?:补贴对象|适用对象|申报对象|参加对象|报名对象)\s*\n"
    r"(?P<basis>[^\r\n]+)"
)
ENTRY_PATTERN = re.compile(r"办理入口(?:为|是|[:：])?(?P<entry>[^。；;]+)")
LOCATION_PATTERN = re.compile(r"(?:办理地点|地点)(?:为|是|[:：])?(?P<location>[^，。；;]+)")
URL_PATTERN = re.compile(r"https?://[^\s，。；;）)】\]》>”\"']+")
ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
ISO_TIME_PATTERN = re.compile(r"\d{2}:\d{2}")
CHANGE_CUES = ("延长至", "更改为", "调整为", "改为")
CANDIDATE_FIELDS = {
    "audience",
    "action",
    "date",
    "time",
    "materials",
    "entry",
    "entry_url",
    "location",
    "relevance",
    "basis",
    "missing_profile_question",
    "source_excerpt",
}
NULLABLE_CANDIDATE_TEXT_FIELDS = CANDIDATE_FIELDS - {"materials", "relevance"}
RELEVANCE_VALUES = {"明确相关", "可能相关", "不适用"}
CAMPUSES = ("大学城校区", "五山校区", "国际校区")
UNDERGRADUATE_TERMS = ("本科生", "本科学生")
MASTER_TERMS = ("硕士生", "硕士研究生")
DOCTOR_TERMS = ("博士生", "博士研究生")
SCOPE_PREFIX = (
    r"(?:20\d{2}级|大学城校区|五山校区|国际校区|"
    r"本科生|本科学生|硕士研究生|硕士生|博士研究生|博士生|研究生|"
    r"[，、,；;\s]|^)"
)
COLLEGE_PATTERN = re.compile(
    SCOPE_PREFIX + r"(?P<value>[A-Za-z\u4e00-\u9fff]{1,20}学院)"
)
MAJOR_PATTERN = re.compile(
    r"(?:学院|20\d{2}级|大学城校区|五山校区|国际校区|"
    r"本科生|本科学生|硕士研究生|硕士生|博士研究生|博士生|研究生|"
    r"[，、,；;\s]|^)"
    r"(?P<value>(?:(?!学院)[A-Za-z\u4e00-\u9fff]){2,20}专业)"
)


def _require_source(source: Dict[str, Any]) -> None:
    required = ("id", "type", "title", "mode", "text")
    missing = [field for field in required if not source.get(field)]
    if missing:
        raise ValueError(f"source missing required fields: {', '.join(missing)}")
    if source["type"] != "notice":
        raise ValueError("source.type must be notice")
    if source["mode"] not in ("example", "real"):
        raise ValueError("source.mode must be example or real")
    if source["mode"] == "real":
        real_required = ("publisher", "url", "ingested_at")
        real_missing = [
            field
            for field in real_required
            if not isinstance(source.get(field), str) or not source[field].strip()
        ]
        if "published_on" not in source:
            real_missing.append("published_on")
        if real_missing:
            raise ValueError(
                f"real source missing required fields: {', '.join(real_missing)}"
            )
        if source["published_on"] is not None:
            if not isinstance(source["published_on"], str):
                raise ValueError("real source.published_on must be YYYY-MM-DD or null")
            _validate_iso_date(source["published_on"], "real source.published_on")
        _validate_absolute_url(source["url"], "real source.url")
        ingested_at = datetime.fromisoformat(
            source["ingested_at"].replace("Z", "+00:00")
        )
        if ingested_at.tzinfo is None or ingested_at.utcoffset() is None:
            raise ValueError("real source.ingested_at must include a timezone")
    elif not source.get("url") and not source.get("file_name"):
        raise ValueError("notice source requires url or file_name")


def _format_date(match: re.Match[str]) -> str:
    value = date(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
    )
    return value.isoformat()


def _format_time(hour: Optional[str], minute: Optional[str]) -> Optional[str]:
    if hour is None or minute is None:
        return None
    hour_value = int(hour)
    minute_value = int(minute)
    if hour_value > 23 or minute_value > 59:
        raise ValueError("notice contains an invalid time")
    return f"{hour_value:02d}:{minute_value:02d}"


def _validate_iso_date(value: str, field: str) -> None:
    if not ISO_DATE_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must use YYYY-MM-DD")
    date.fromisoformat(value)


def _validate_iso_time(value: str, field: str) -> None:
    if not ISO_TIME_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must use HH:MM")
    hour, minute = value.split(":")
    if int(hour) > 23 or int(minute) > 59:
        raise ValueError(f"{field} contains an invalid time")


def _validate_absolute_url(value: str, field: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"{field} must be an absolute HTTP(S) URL")


def _validate_candidate_evidence(
    source: Dict[str, Any],
    candidate: Dict[str, Any],
) -> None:
    source_text = source["text"]

    for field in ("audience", "action", "entry", "location"):
        value = candidate[field]
        if value is not None and value not in source_text:
            raise ValueError(
                f"candidate_extraction.{field} must be an exact source.text excerpt"
            )

    for material in candidate["materials"]:
        if material not in source_text:
            raise ValueError(
                "candidate_extraction.materials contains an item that is not "
                "an exact source.text excerpt"
            )

    candidate_date = candidate["date"]
    if candidate_date is not None:
        source_dates = {
            _format_date(match) for match in DATE_PATTERN.finditer(source_text)
        }
        for match in ISO_DATE_PATTERN.finditer(source_text):
            try:
                source_dates.add(date.fromisoformat(match.group(0)).isoformat())
            except ValueError:
                continue
        if candidate_date not in source_dates:
            raise ValueError(
                "candidate_extraction.date is not supported by source.text"
            )

    candidate_time = candidate["time"]
    if candidate_time is not None:
        source_times = {
            _format_time(match.group("hour"), match.group("minute"))
            for match in TIME_PATTERN.finditer(source_text)
        }
        if candidate_time not in source_times:
            raise ValueError(
                "candidate_extraction.time is not supported by source.text"
            )

    source_urls = set(URL_PATTERN.findall(source_text))
    entry_url = candidate["entry_url"]
    if entry_url is not None and entry_url not in source_urls:
        raise ValueError(
            "candidate_extraction.entry_url must match a complete source.text URL"
        )

    _validate_material_relations(candidate["materials"], source_text)
    _validate_event_excerpt(candidate)


def _validate_material_relations(materials: List[str], source_text: str) -> None:
    for index, first in enumerate(materials):
        first_position = source_text.find(first)
        for second in materials[index + 1 :]:
            second_position = source_text.find(second)
            if first_position < 0 or second_position < 0:
                continue
            start = min(first_position, second_position)
            end = max(
                first_position + len(first), second_position + len(second)
            )
            first_end = first_position + len(first)
            second_end = second_position + len(second)
            between_start = min(first_end, second_end)
            between_end = max(first_position, second_position)
            if re.search(
                r"[。；;\r\n]|（[一二三四五六七八九十]+）",
                source_text[between_start:between_end],
            ):
                continue
            clause_start = max(
                source_text.rfind(mark, 0, start) for mark in ("。", "；", ";")
            ) + 1
            clause_ends = [
                position
                for mark in ("。", "；", ";")
                for position in (source_text.find(mark, end),)
                if position >= 0
            ]
            clause_end = min(clause_ends) if clause_ends else len(source_text)
            clause = source_text[clause_start:clause_end]
            if re.search(
                r"或|或者|任选|二选一|只需.+之一|"
                r"确无.+的提供|没有.+时.{0,4}提供|无法.+可提供",
                clause,
            ):
                raise ValueError(
                    "candidate_extraction.materials must preserve an alternative "
                    "or conditional material phrase as one exact excerpt"
                )


def _excerpt_dates(text: str) -> set:
    values = {_format_date(match) for match in DATE_PATTERN.finditer(text)}
    for match in ISO_DATE_PATTERN.finditer(text):
        try:
            values.add(date.fromisoformat(match.group(0)).isoformat())
        except ValueError:
            continue
    return values


def _excerpt_times(text: str) -> set:
    return {
        _format_time(match.group("hour"), match.group("minute"))
        for match in TIME_PATTERN.finditer(text)
    }


def _is_explicitly_negated(text: str, value: str) -> bool:
    for match in re.finditer(re.escape(value), text):
        prefix = text[max(0, match.start() - 8) : match.start()]
        if any(
            marker in prefix
            for marker in ("无需", "不需", "不用", "不得", "禁止", "不必", "不在", "并非")
        ):
            return True
    return False


def _validate_event_excerpt(candidate: Dict[str, Any]) -> None:
    excerpt = candidate["source_excerpt"]
    event_values = (
        candidate["action"],
        candidate["date"],
        candidate["time"],
        candidate["location"],
    )
    if any(value is not None for value in event_values) and excerpt is None:
        raise ValueError(
            "candidate_extraction.source_excerpt is required for event fields"
        )

    if excerpt is None:
        return

    for field in ("action", "location"):
        value = candidate[field]
        if value is not None and value not in excerpt:
            raise ValueError(
                f"candidate_extraction.{field} must be supported by source_excerpt"
            )
        if value is not None and _is_explicitly_negated(excerpt, value):
            raise ValueError(
                f"candidate_extraction.{field} is explicitly negated in source_excerpt"
            )

    if candidate["date"] is not None and candidate["date"] not in _excerpt_dates(excerpt):
        raise ValueError(
            "candidate_extraction.date must be supported by source_excerpt"
        )
    if candidate["time"] is not None and candidate["time"] not in _excerpt_times(excerpt):
        raise ValueError(
            "candidate_extraction.time must be supported by source_excerpt"
        )


def validate_candidate_extraction(
    source: Dict[str, Any],
    candidate: Dict[str, Any],
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    _require_source(source)
    if not isinstance(candidate, dict):
        raise ValueError("candidate_extraction must be an object")

    missing = sorted(CANDIDATE_FIELDS - set(candidate))
    extra = sorted(set(candidate) - CANDIDATE_FIELDS)
    if missing:
        raise ValueError(
            f"candidate_extraction missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise ValueError(
            f"candidate_extraction contains unsupported fields: {', '.join(extra)}"
        )

    for field in sorted(NULLABLE_CANDIDATE_TEXT_FIELDS):
        value = candidate[field]
        if value is not None and not isinstance(value, str):
            raise ValueError(f"candidate_extraction.{field} must be a string or null")

    materials = candidate["materials"]
    if not isinstance(materials, list) or any(
        not isinstance(item, str) or not item for item in materials
    ):
        raise ValueError(
            "candidate_extraction.materials must be an array of non-empty strings"
        )

    relevance = candidate["relevance"]
    if not isinstance(relevance, str) or relevance not in RELEVANCE_VALUES:
        raise ValueError(
            "candidate_extraction.relevance must be 明确相关, 可能相关, or 不适用"
        )

    if candidate["date"] is not None:
        _validate_iso_date(candidate["date"], "candidate_extraction.date")
    if candidate["time"] is not None:
        _validate_iso_time(candidate["time"], "candidate_extraction.time")
    if candidate["entry_url"] is not None:
        _validate_absolute_url(
            candidate["entry_url"], "candidate_extraction.entry_url"
        )

    for field in ("basis", "source_excerpt"):
        value = candidate[field]
        if value is not None and (not value or value not in source["text"]):
            raise ValueError(
                f"candidate_extraction.{field} must be an exact source.text excerpt"
            )

    _validate_candidate_evidence(source, candidate)

    source_audience, source_basis = _audience_details(source["text"])
    if source_audience:
        if candidate["audience"] != source_audience:
            raise ValueError(
                "candidate_extraction.audience conflicts with source.text"
            )
        if candidate["basis"] != source_basis:
            raise ValueError(
                "candidate_extraction.basis conflicts with source.text audience"
            )
        constraints = _constraints(source_audience)
        has_known_constraints = any(constraints.values())
        if has_known_constraints:
            assessed = assess_relevance(
                source_audience, source_basis, profile or {}
            )
            if candidate["relevance"] != assessed["relevance"]:
                raise ValueError(
                    "candidate_extraction.relevance conflicts with the profile"
                )
            if (
                candidate["missing_profile_question"]
                != assessed["missing_profile_question"]
            ):
                raise ValueError(
                    "candidate_extraction.missing_profile_question conflicts "
                    "with the profile"
                )
    else:
        heading_audience, heading_basis = _audience_heading_details(source["text"])
        if heading_audience:
            if (
                candidate["audience"] != heading_audience
                or candidate["basis"] != heading_basis
            ):
                raise ValueError(
                    "candidate_extraction.audience conflicts with source.text "
                    "audience heading"
                )
        elif candidate["audience"] is not None and (
            candidate["basis"] is None
            or candidate["audience"] != candidate["basis"]
        ):
            raise ValueError(
                "candidate_extraction.audience must preserve the complete "
                "unparsed basis excerpt"
            )
        if candidate["relevance"] != "可能相关":
            raise ValueError(
                "candidate_extraction.relevance must be 可能相关 when source "
                "audience constraints cannot be evaluated deterministically"
            )
        if heading_audience and not candidate["missing_profile_question"]:
            raise ValueError(
                "candidate_extraction.missing_profile_question is required for "
                "unparsed source audience constraints"
            )

    validated = dict(candidate)
    validated["materials"] = list(materials)
    return validated


def _audience_details(text: str) -> Tuple[Optional[str], Optional[str]]:
    match = AUDIENCE_PATTERN.search(text)
    if not match:
        return None, None
    audience = match.group("audience").strip("，, ")
    basis = match.group("basis").strip()
    if basis[-1] not in "。；;":
        basis += "。"
    return audience, basis


def _audience_heading_details(text: str) -> Tuple[Optional[str], Optional[str]]:
    match = AUDIENCE_HEADING_PATTERN.search(text)
    if not match:
        return None, None
    basis = match.group("basis").strip()
    return basis, basis


def _constraints(audience: Optional[str]) -> Dict[str, List[str]]:
    if not audience:
        return {"campus": [], "education_level": [], "college": [], "major": [], "grade": []}

    campuses = [value for value in CAMPUSES if value in audience]
    levels: List[str] = []
    if any(term in audience for term in UNDERGRADUATE_TERMS):
        levels.append("undergraduate")
    has_master = any(term in audience for term in MASTER_TERMS)
    has_doctor = any(term in audience for term in DOCTOR_TERMS)
    if has_master:
        levels.append("master")
    if has_doctor:
        levels.append("doctor")
    if "研究生" in audience and not has_master and not has_doctor:
        levels.append("graduate")
    grades = sorted(set(re.findall(r"20\d{2}级", audience)))

    colleges: List[str] = []
    if "不限学院" not in audience and "各学院" not in audience and "全校" not in audience:
        colleges = sorted(set(match.group("value") for match in COLLEGE_PATTERN.finditer(audience)))

    majors: List[str] = []
    if "不限专业" not in audience and "各专业" not in audience:
        majors = sorted(set(match.group("value") for match in MAJOR_PATTERN.finditer(audience)))

    return {
        "campus": campuses,
        "education_level": levels,
        "college": colleges,
        "major": majors,
        "grade": grades,
    }


def _normalize_level(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    aliases = {
        "undergraduate": "undergraduate",
        "本科": "undergraduate",
        "本科生": "undergraduate",
        "master": "master",
        "硕士": "master",
        "硕士生": "master",
        "doctor": "doctor",
        "博士": "doctor",
        "博士生": "doctor",
        "graduate": "graduate",
        "研究生": "graduate",
    }
    return aliases.get(value, value)


def assess_relevance(
    audience: Optional[str],
    basis: Optional[str],
    profile: Optional[Dict[str, Any]],
) -> Dict[str, Optional[str]]:
    if not audience:
        return {
            "relevance": "可能相关",
            "basis": None,
            "missing_profile_question": None,
        }

    values = _constraints(audience)
    profile = profile or {}
    missing_labels: List[str] = []

    comparisons = (
        ("campus", "校区"),
        ("college", "学院"),
        ("major", "专业"),
        ("grade", "年级"),
    )
    for field, label in comparisons:
        allowed = values[field]
        if not allowed:
            continue
        actual = profile.get(field)
        if actual is None:
            missing_labels.append(label)
        elif actual not in allowed:
            return {
                "relevance": "不适用",
                "basis": basis,
                "missing_profile_question": None,
            }

    allowed_levels = values["education_level"]
    if allowed_levels:
        actual_level = _normalize_level(profile.get("education_level"))
        compatible_levels = set(allowed_levels)
        if "graduate" in compatible_levels:
            compatible_levels.update(("master", "doctor"))
        if actual_level is None:
            missing_labels.append("培养层次")
        elif actual_level not in compatible_levels:
            return {
                "relevance": "不适用",
                "basis": basis,
                "missing_profile_question": None,
            }

    if missing_labels:
        labels = "、".join(dict.fromkeys(missing_labels))
        return {
            "relevance": "可能相关",
            "basis": basis,
            "missing_profile_question": f"请确认你的{labels}。",
        }

    return {
        "relevance": "明确相关",
        "basis": basis,
        "missing_profile_question": None,
    }


def _action_details(text: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    match = DEADLINE_PATTERN.search(text)
    if not match:
        return None, None, None, None
    return (
        match.group("action").strip(),
        _format_date(match),
        _format_time(match.group("hour"), match.group("minute")),
        match.group("excerpt").strip(),
    )


def _materials(action: Optional[str], text: str) -> List[str]:
    if action and action.startswith("提交") and len(action) > 2:
        return [action[2:].strip()]
    candidates = re.findall(
        r"[A-Za-z0-9\u4e00-\u9fff_-]{1,30}(?:PDF|pdf|表格|表|材料|证明|附件)",
        text,
    )
    return list(dict.fromkeys(candidate.removeprefix("提交") for candidate in candidates))


def _entry_details(text: str) -> Tuple[Optional[str], Optional[str]]:
    match = ENTRY_PATTERN.search(text)
    if not match:
        return None, None
    entry = match.group("entry").strip("，, ")
    url_match = URL_PATTERN.search(entry)
    return entry, url_match.group(0) if url_match else None


def extract_notice(
    source: Dict[str, Any],
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    _require_source(source)
    text = source["text"]
    audience, basis = _audience_details(text)
    action, notice_date, notice_time, source_excerpt = _action_details(text)
    entry, entry_url = _entry_details(text)
    location_match = LOCATION_PATTERN.search(text)
    location = location_match.group("location").strip() if location_match else None
    relevance = assess_relevance(audience, basis, profile)

    return {
        "audience": audience,
        "action": action,
        "date": notice_date,
        "time": notice_time,
        "materials": _materials(action, text),
        "entry": entry,
        "entry_url": entry_url,
        "location": location,
        "relevance": relevance["relevance"],
        "basis": relevance["basis"],
        "missing_profile_question": relevance["missing_profile_question"],
        "source_excerpt": source_excerpt,
    }


def _event_id(source_id: str) -> str:
    if "-notice-" in source_id:
        return source_id.replace("-notice-", "-event-", 1)
    return f"{source_id}-event"


def _event_type(action: Optional[str]) -> str:
    if action and action.startswith(("提交", "报送", "上传", "递交")):
        return "submission"
    if action and action.endswith("申请"):
        return "submission"
    return "notice_task"


def build_bundle(
    source: Dict[str, Any],
    extraction: Dict[str, Any],
    today: str,
    timezone: str = "Asia/Shanghai",
    campus: str = "大学城校区",
) -> Dict[str, Any]:
    _require_source(source)
    date.fromisoformat(today)
    action = extraction.get("action")
    notice_date = extraction.get("date")
    notice_time = extraction.get("time")
    pending_fields = [field for field in ("date",) if extraction.get(field) is None]

    if "source_excerpt" in extraction:
        source_excerpt = extraction["source_excerpt"]
    else:
        excerpt_match = DEADLINE_PATTERN.search(source["text"])
        source_excerpt = (
            excerpt_match.group("excerpt")
            if excerpt_match
            else source["text"].strip()
        )
    if "location" in extraction:
        location = extraction["location"]
    else:
        location_match = LOCATION_PATTERN.search(source["text"])
        location = location_match.group("location").strip() if location_match else None

    event = {
        "id": _event_id(source["id"]),
        "type": _event_type(action),
        "title": action or source["title"],
        "date": notice_date,
        "start_time": notice_time,
        "end_time": None,
        "location": location,
        "status": "not_started",
        "pending_fields": pending_fields,
        "source_id": source["id"],
        "source_excerpt": source_excerpt,
    }

    return {
        "mode": source["mode"],
        "today": today,
        "timezone": timezone,
        "campus": campus,
        "sources": [dict(source)],
        "events": [event],
    }


def _date_values(text: str) -> List[str]:
    return [_format_date(match) for match in DATE_PATTERN.finditer(text)]


def _time_values(text: str) -> List[str]:
    return [
        _format_time(match.group("hour"), match.group("minute"))
        for match in TIME_PATTERN.finditer(text)
    ]


def _split_materials(value: str) -> List[str]:
    return [
        item.strip()
        for item in re.split(r"[、，,]|以及|及|和", value)
        if item.strip()
    ]


def compare_notice_versions(
    original_source: Dict[str, Any],
    correction_source: Dict[str, Any],
    target_event_id: str,
) -> Dict[str, Any]:
    _require_source(original_source)
    _require_source(correction_source)
    if correction_source.get("corrects") != original_source["id"]:
        raise ValueError("correction source does not reference the original source")

    changes: Dict[str, Any] = {}
    correction_text = correction_source["text"]
    has_change_cue = any(cue in correction_text for cue in CHANGE_CUES)
    date_values = _date_values(correction_text)
    if len(date_values) >= 2 and has_change_cue:
        before_date, after_date = date_values[:2]
        if before_date != after_date:
            changes["date"] = {"before": before_date, "after": after_date}

    time_values = _time_values(correction_text)
    if len(time_values) >= 2 and has_change_cue:
        before_time, after_time = time_values[:2]
        if before_time != after_time:
            time_field = (
                "end_time"
                if re.search(r"结束(?:时间|时刻)?", correction_text)
                else "start_time"
            )
            changes[time_field] = {"before": before_time, "after": after_time}

    original_audience, _ = _audience_details(original_source["text"])
    corrected_audience, _ = _audience_details(correction_text)
    if corrected_audience and corrected_audience != original_audience:
        changes["audience"] = {"before": original_audience, "after": corrected_audience}

    added_audience = re.search(
        r"(?:适用对象)?新增(?P<audience>[^，。；;]+?)(?:为)?"
        r"(?:适用对象|参加对象|参加资格|申报对象)",
        correction_text,
    )
    if added_audience:
        added_value = added_audience.group("audience").strip()
        changes["audience"] = {
            "before": original_audience,
            "after": (
                f"{original_audience}；{added_value}"
                if original_audience
                else added_value
            ),
        }

    materials_change = re.search(
        r"(?:申请|提交|所需)?材料(?:由|从)"
        r"(?P<before>.+?)(?:更改为|调整为|改为)"
        r"(?P<after>[^。；;]+)",
        correction_text,
    )
    if materials_change:
        changes["materials"] = {
            "before": _split_materials(materials_change.group("before")),
            "after": _split_materials(materials_change.group("after")),
        }

    location_change = re.search(
        r"(?:办理地点|活动地点|地点)(?:由|从)"
        r"(?P<before>[^，。；;]+?)(?:更改为|调整为|改为)"
        r"(?P<after>[^，。；;]+)",
        correction_text,
    )
    if location_change:
        changes["location"] = {
            "before": location_change.group("before").strip(),
            "after": location_change.group("after").strip(),
        }

    if not changes:
        raise ValueError("no supported notice changes were found")

    return {
        "target_event_id": target_event_id,
        "changes": changes,
        "source_id": correction_source["id"],
        "source_excerpt": correction_text.strip(),
    }


def refresh_sources(
    previous_sources: Sequence[Dict[str, Any]],
    current_sources: Sequence[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    previous_by_id = {source["id"]: source for source in previous_sources}
    current_by_id = {source["id"]: source for source in current_sources}
    if len(previous_by_id) != len(previous_sources) or len(current_by_id) != len(current_sources):
        raise ValueError("source ids must be unique within each source list")

    added = [
        source
        for source_id, source in current_by_id.items()
        if source_id not in previous_by_id
        and source.get("corrects") not in previous_by_id
    ]
    corrected = []
    for source_id, current in current_by_id.items():
        previous = previous_by_id.get(source_id)
        if previous and current.get("text") != previous.get("text"):
            corrected.append({"before": previous, "after": current})
        elif current.get("corrects") in previous_by_id:
            corrected.append({"before": previous_by_id[current["corrects"]], "after": current})

    return {"added": added, "corrected": corrected}


def verify_handoff_dates(sent_on: str) -> Dict[str, str]:
    sent_date = date.fromisoformat(sent_on)
    days_until_friday = (4 - sent_date.weekday()) % 7
    friday = sent_date + timedelta(days=days_until_friday)
    return {
        "tomorrow": (sent_date + timedelta(days=1)).isoformat(),
        "this_friday": friday.isoformat(),
    }

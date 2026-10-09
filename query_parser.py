import re
import shlex
from config import KNOWN_TAGS, MIN_RATING, MAX_RATING

RANGE_PATTERN = re.compile(r"^r:(?!-$)(?:(\d+)?-(\d+)?|(\d+))?$")
INCLUDE_TAG_PATTERN = re.compile(r"^t:(.+)?$")
EXCLUDE_TAG_PATTERN = re.compile(r"^!t:(.+)?$")


def parse_search_query(query_str: str) -> dict:
    min_rating, max_rating = None, None
    include_tags, exclude_tags = [], []
    name_tokens = []

    try:
        tokens = shlex.split(query_str)
    except ValueError:
        # Fallback if query has unclosed quotes
        tokens = query_str.split()

    for token in tokens:
        m_range = RANGE_PATTERN.match(token)
        if m_range:
            low, high, exact = m_range.groups()
            if exact is not None:
                r = int(exact)
                if MIN_RATING <= r <= MAX_RATING:
                    min_rating, max_rating = r, r
            else:
                if low:
                    r_low = int(low)
                    if MIN_RATING <= r_low <= MAX_RATING:
                        min_rating = r_low
                if high:
                    r_high = int(high)
                    if MIN_RATING <= r_high <= MAX_RATING:
                        max_rating = r_high
            continue

        m_inc = INCLUDE_TAG_PATTERN.match(token)
        if m_inc:
            tag_content = m_inc.group(1)
            if tag_content:
                tags = [
                    t.strip().lower()
                    for t in tag_content.split(",")
                    if t.strip().lower() in KNOWN_TAGS
                ]
                include_tags.extend(tags)
            continue

        m_exc = EXCLUDE_TAG_PATTERN.match(token)
        if m_exc:
            tag_content = m_exc.group(1)
            if tag_content:
                tags = [
                    t.strip().lower()
                    for t in tag_content.split(",")
                    if t.strip().lower() in KNOWN_TAGS
                ]
                exclude_tags.extend(tags)
            continue

        # Non-filter tokens belong to problem name search
        name_tokens.append(token)

    return {
        "min_rating": min_rating,
        "max_rating": max_rating,
        "include_tags": include_tags,
        "exclude_tags": exclude_tags,
        "name_query": " ".join(name_tokens),
    }


def build_sql_query(parsed: dict) -> tuple[str, dict]:
    conditions = []
    params = {}

    # Rating filters
    if parsed["min_rating"] is not None:
        conditions.append("rating >= :min_rating")
        params["min_rating"] = parsed["min_rating"]
    if parsed["max_rating"] is not None:
        conditions.append("rating <= :max_rating")
        params["max_rating"] = parsed["max_rating"]

    # Included tags (AND condition: problem must have all specified tags)
    for idx, tag in enumerate(parsed["include_tags"]):
        param_name = f"inc_tag_{idx}"
        conditions.append(
            f"EXISTS (SELECT 1 FROM json_each(problem.tags) WHERE lower(value) = :{param_name})"
        )
        params[param_name] = tag

    # Excluded tags (AND condition: problem must NOT have any specified tag)
    for idx, tag in enumerate(parsed["exclude_tags"]):
        param_name = f"exc_tag_{idx}"
        conditions.append(
            f"NOT EXISTS (SELECT 1 FROM json_each(problem.tags) WHERE lower(value) = :{param_name})"
        )
        params[param_name] = tag

    # Name substring search
    if parsed["name_query"]:
        conditions.append("name LIKE :name_query")
        params["name_query"] = f"%{parsed['name_query']}%"

    sql = "SELECT contestId, problem_index, name, rating, tags FROM problem"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    return sql, params

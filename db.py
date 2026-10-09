from pathlib import Path
import sqlite3
import json
import urllib.request
from typing import Optional, Tuple
from config import DB_PATH
from query_parser import parse_search_query, build_sql_query


def fetch_cf_api_problems() -> list:
    url = "https://codeforces.com/api/problemset.problems"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; CodeforcesFZF/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))
    if data.get("status") != "OK":
        raise RuntimeError(f"Codeforces API error: {data.get('comment')}")
    return data["result"]["problems"]


class DataBase:
    def __init__(self, db_path: Path = DB_PATH, refresh: bool = False, show_tags: bool = False):
        self.path = db_path
        db_exists = Path(self.path).is_file()

        # Connect with WAL mode and sensible timeouts for concurrent operations
        self.con = sqlite3.connect(self.path, timeout=30.0, check_same_thread=False)
        self.con.execute("PRAGMA journal_mode = WAL;")
        self.con.execute("PRAGMA synchronous = NORMAL;")
        self.cur = self.con.cursor()

        self.show_tags = show_tags

        if not db_exists:
            self.create_tables()
            self.insert_problems(fetch_cf_api_problems())
        else:
            self.create_tables()  # Ensure problem_statement table exists even on existing DB
            if refresh:
                self.refresh()

    def create_tables(self):
        with self.con:
            self.con.execute("""
            CREATE TABLE IF NOT EXISTS problem (
                contestId      INTEGER,
                problemsetName VARCHAR(256),
                problem_index  VARCHAR(256),
                name           VARCHAR(256),
                type           VARCHAR(256),
                points         REAL,
                rating         INTEGER,
                tags           TEXT
            )
            """)
            self.con.execute("""
            CREATE TABLE IF NOT EXISTS problem_statement (
                problem_id   TEXT PRIMARY KEY,
                statement_md TEXT NOT NULL,
                raw_json     TEXT,
                fetched_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

    def insert_problems(self, problems: list):
        insert_stmt = """
        INSERT INTO problem (
            contestId, problemsetName, problem_index, name, type, points, rating, tags
        ) VALUES (
            :contestId, :problemsetName, :problem_index, :name, :type, :points, :rating, :tags
        )
        """
        payloads = []
        for p in problems:
            tags = p.get("tags")
            formatted_tags = (
                [t.replace(" ", "_").replace("-", "_") for t in tags]
                if tags is not None
                else None
            )
            payloads.append({
                "contestId": p.get("contestId"),
                "problemsetName": p.get("problemsetName"),
                "problem_index": p.get("index"),
                "name": p.get("name"),
                "type": p.get("type"),
                "points": p.get("points"),
                "rating": p.get("rating"),
                "tags": json.dumps(formatted_tags) if formatted_tags is not None else None,
            })

        # Wrapped in context manager -> atomic transaction
        with self.con:
            self.con.executemany(insert_stmt, payloads)

    def refresh(self):
        problems = fetch_cf_api_problems()
        # Atomic clear and re-insert: if API fails, existing problems are preserved
        with self.con:
            self.con.execute("DELETE FROM problem")
            insert_stmt = """
            INSERT INTO problem (
                contestId, problemsetName, problem_index, name, type, points, rating, tags
            ) VALUES (
                :contestId, :problemsetName, :problem_index, :name, :type, :points, :rating, :tags
            )
            """
            payloads = []
            for p in problems:
                tags = p.get("tags")
                formatted_tags = (
                    [t.replace(" ", "_").replace("-", "_") for t in tags]
                    if tags is not None
                    else None
                )
                payloads.append({
                    "contestId": p.get("contestId"),
                    "problemsetName": p.get("problemsetName"),
                    "problem_index": p.get("index"),
                    "name": p.get("name"),
                    "type": p.get("type"),
                    "points": p.get("points"),
                    "rating": p.get("rating"),
                    "tags": json.dumps(formatted_tags) if formatted_tags is not None else None,
                })
            self.con.executemany(insert_stmt, payloads)

    def get_cached_statement(self, problem_id: str) -> Optional[Tuple[str, Optional[str]]]:
        """Returns (statement_md, raw_json) if cached, otherwise None."""
        cur = self.con.cursor()
        cur.execute(
            "SELECT statement_md, raw_json FROM problem_statement WHERE problem_id = ?",
            (problem_id,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else None

    def save_problem_statement(self, problem_id: str, statement_md: str, raw_json: Optional[str] = None):
        """Atomically saves problem statement markdown and optional raw json."""
        with self.con:
            self.con.execute(
                """
                INSERT OR REPLACE INTO problem_statement (problem_id, statement_md, raw_json, fetched_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (problem_id, statement_md, raw_json),
            )

    def search_problems(self, query: str) -> str:
        parsed = parse_search_query(query)
        sql, params = build_sql_query(parsed)

        cur = self.con.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()

        lines = []
        for contest_id, index, name, rating, tags in rows:
            rating_str = f"[{rating}]" if rating else "[Unrated]"
            if self.show_tags:
                formatted_tags = ""
                if tags:
                    try:
                        tag_list = json.loads(tags)
                        formatted_tags = ", ".join(tag_list)
                    except Exception:
                        formatted_tags = tags
                lines.append(f"{contest_id}/{index}:{rating_str} | {formatted_tags} | {name}\n")
            else:
                lines.append(f"{contest_id}/{index}:{name}\n")
        return "".join(lines)

    def toggle_tags(self):
        self.show_tags = not self.show_tags

    def close(self):
        self.con.close()

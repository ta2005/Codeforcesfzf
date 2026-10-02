#!/bin/python
from pathlib import Path
import sqlite3
import urllib.request 
import json
import re
import shlex
import sqlite3
import sys


path = "cf.sqlite"




def parse_search_query(query_str: str) -> dict:
    range_pattern = re.compile(r"^r:(\d+)(?:-(\d+))?$")
    include_tag_pattern = re.compile(r"^t:(.+)$")
    exclude_tag_pattern = re.compile(r"^!t:(.+)$")

    min_rating, max_rating = None, None
    include_tags, exclude_tags = [], []
    name_tokens = []

    tokens = shlex.split(query_str)

    for token in tokens:
        # Check range (r:1200 or r:1200-1500)
        m_range = range_pattern.match(token)
        if m_range:
            low, high = m_range.groups()
            min_rating = int(low)
            max_rating = int(high) if high else int(low)
            continue

        # Check included tags (t:dp,math)
        m_inc = include_tag_pattern.match(token)
        if m_inc:
            tags = [t.strip().lower() for t in m_inc.group(1).split(",") if t.strip()]
            include_tags.extend(tags)
            continue

        # Check excluded tags (!t:graphs,trees)
        m_exc = exclude_tag_pattern.match(token)
        if m_exc:
            tags = [t.strip().lower() for t in m_exc.group(1).split(",") if t.strip()]
            exclude_tags.extend(tags)
            continue

        # Remaining tokens are treated as name search
        name_tokens.append(token)

    return {
        "min_rating": min_rating,
        "max_rating": max_rating,
        "include_tags": include_tags,
        "exclude_tags": exclude_tags,
        "name_query": " ".join(name_tokens)
    }
def build_sql_query(parsed: dict) -> tuple[str, dict]:
    conditions = []
    params = {}

    # Rating filter
    if parsed["min_rating"] is not None:
        conditions.append("rating >= :min_rating")
        params["min_rating"] = parsed["min_rating"]
    if parsed["max_rating"] is not None:
        conditions.append("rating <= :max_rating")
        params["max_rating"] = parsed["max_rating"]

    # Included tags (Must have ALL specified tags)
    for idx, tag in enumerate(parsed["include_tags"]):
        param_name = f"inc_tag_{idx}"
        conditions.append(
            f"EXISTS (SELECT 1 FROM json_each(problem.tags) WHERE lower(value) = :{param_name})"
        )
        params[param_name] = tag

    # Excluded tags (Must NOT have any specified tags)
    for idx, tag in enumerate(parsed["exclude_tags"]):
        param_name = f"exc_tag_{idx}"
        conditions.append(
            f"NOT EXISTS (SELECT 1 FROM json_each(problem.tags) WHERE lower(value) = :{param_name})"
        )
        params[param_name] = tag

    # Name search
    if parsed["name_query"]:
        conditions.append("name LIKE :name_query")
        params["name_query"] = f"%{parsed['name_query']}%"

    sql = "SELECT contestId, problem_index, name, rating, tags FROM problem"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    return sql, params

class DataBase:
    def __init__(self, p=path):
        self.path = p
        self.con = sqlite3.connect(self.path)
        self.cur = self.con.cursor()

    def exists(self):
        return Path(self.path).is_file()

    def create(self):
        create_stmt = """
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
        """
        self.cur.execute(create_stmt)
        self.con.commit()

    def insert(self, problems):
        insert_stmt = """
        INSERT INTO problem (
            contestId, problemsetName, problem_index, name, type, points, rating, tags
        ) VALUES (
            :contestId, :problemsetName, :problem_index, :name, :type, :points, :rating, :tags
        )
        """
        
        # Prepare a list of formatted records for executemany
        payloads = []
        for p in problems:
            tags = p.get("tags")
            payloads.append({
                "contestId": p.get("contestId"),
                "problemsetName": p.get("problemsetName"),
                "problem_index": p.get("index"),  # Codeforces API uses 'index' (e.g. 'A', 'B')
                "name": p.get("name"),
                "type": p.get("type"),
                "points": p.get("points"),
                "rating": p.get("rating"),
                "tags": json.dumps(tags) if tags is not None else None  # Convert list to JSON string
            })

        self.cur.executemany(insert_stmt, payloads)
        self.con.commit()


    def close(self):
        self.con.close()


def getResponse():
    url = "https://codeforces.com/api/problemset.problems"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode("utf-8"))
    return data["result"]["problems"]


def search_problems(query_str: str, db_path: str = "cf.sqlite"):
    d=DataBase()
    if not d.exists() :
        d.create()
    parsed = parse_search_query(query_str)
    sql, params = build_sql_query(parsed)

    d.cur.execute(sql, params)
    rows = d.cur.fetchall()
    d.close()

    # Print formatted lines for fzf
    for contest_id, index, name, rating, tags in rows:
        rating_str = f"[{rating}]" if rating else "[Unrated]"
        print(f"{contest_id}/{index} | {name} {rating_str} | {tags}")

if __name__ == "__main__":
    search_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "r:1200-1600 t:dp !t:graphs"
    search_problems(search_input)

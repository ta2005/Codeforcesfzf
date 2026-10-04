#!/bin/python
from pathlib import Path
import urllib.request
import urllib.parse
import json
import re
import shlex
import sqlite3
import sys
import argparse
from http.server import HTTPServer , BaseHTTPRequestHandler

cache_dir = Path.home() / ".cache" / "codeforces_fzf"
cache_dir.mkdir(parents=True, exist_ok=True)
path = cache_dir / "cf.sqlite"


def getResponse():
    # print("making request")
    url = "https://codeforces.com/api/problemset.problems"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode("utf-8"))
    return data["result"]["problems"]


def parse_search_query(query_str: str) -> dict:
    range_pattern = re.compile(r"^r:(?!-$)(?:(\d+)?-(\d+)?|(\d+))?$")
    include_tag_pattern = re.compile(r"^t:(.+)?$")
    exclude_tag_pattern = re.compile(r"^!t:(.+)?$")
    min_rating, max_rating = None, None
    include_tags, exclude_tags = [], []
    name_tokens = []

    # this is split but works with any laoal
    tokens = shlex.split(query_str)

    for token in tokens:
        m_range = range_pattern.match(token)
        if m_range:
            low, high, exact = m_range.groups()
            min_rating = None
            max_rating = None
            if exact is not None:
                min_rating = int(exact)
                max_rating = int(exact)
            else:
                min_rating = int(low) if low else None
                max_rating = int(high) if high else None

            continue

        # Check included tags (t:dp,math)
        m_inc = include_tag_pattern.match(token)
        if m_inc:
            tag_content = m_inc.group(1)
            if tag_content:
                tags = [t.strip().lower() for t in tag_content.split(",") if t.strip()]
                include_tags.extend(tags)
            continue
        # Check excluded tags (!t:graphs,trees)
        m_exc = exclude_tag_pattern.match(token)
        if m_exc:
            tag_content = m_exc.group(1)
            if tag_content:
                tags = [t.strip().lower() for t in tag_content.split(",") if t.strip()]
                exclude_tags.extend(tags)
            continue

        # Remaining tokens are treated as name search
        name_tokens.append(token)

    return {
        "min_rating": min_rating,
        "max_rating": max_rating,
        "include_tags": include_tags,
        "exclude_tags": exclude_tags,
        "name_query": " ".join(name_tokens),
    }


class DataBase:
    def __init__(self, p=path, refresh=False,show_tags=False):
        test = Path(path).is_file()
        self.path = p
        self.con = sqlite3.connect(self.path)
        self.cur = self.con.cursor()
        self.show_tags=show_tags
        if not test:
            self.create()
            self.insert(getResponse())
        elif refresh:
            self.clear()
            self.insert(getResponse())

    def exists(path):
        return Path(path).is_file()

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

    def clear(self):
        self.cur.execute("DELETE FROM problem")
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
            payloads.append(
                {
                    "contestId": p.get("contestId"),
                    "problemsetName": p.get("problemsetName"),
                    "problem_index": p.get(
                        "index"
                    ),  # Codeforces API uses 'index' (e.g. 'A', 'B')
                    "name": p.get("name"),
                    "type": p.get("type"),
                    "points": p.get("points"),
                    "rating": p.get("rating"),
                    "tags": json.dumps(
                        [t.replace(" ", "_").replace("-", "_") for t in tags]
                    )
                    if tags is not None
                    else None,  # Convert list to JSON string
                }
            )

        self.cur.executemany(insert_stmt, payloads)
        self.con.commit()

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

    def search_problems(self, query, show_tags=False):
        if show_tags:
            self.show_tags = not self.show_tags
        parsed = parse_search_query(query)
        sql, params = DataBase.build_sql_query(parsed)

        self.cur.execute(sql, params)
        rows = self.cur.fetchall()

        # Print formatted lines for fzf
        res=""
        for contest_id, index, name, rating, tags in rows:
            rating_str = f"[{rating}]" if rating else "[Unrated]"
            if self.show_tags:
                res+=f"{contest_id}/{index}:{rating_str} | {tags} | {name}\n"
            else:
                res+=f"{contest_id}/{index}:{name}\n"
        return res

    def close(self):
        self.con.close()

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        qr=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        search = qr.get("q", [""])[0]
        toggle = "toggle" in qr
        ref = "ref" in qr
        if ref:
            self.server.db.clear()
            self.server.db.insert(getResponse())
        self.send_response(200)
        self.end_headers()
        results = self.server.db.search_problems(search, show_tags=toggle)
        self.wfile.write(results.encode('utf-8'))

class FzfServer(HTTPServer):
    def __init__(self, server_address, handler_class):
        super().__init__(server_address, handler_class)
        self.db = DataBase()


# if __name__ == "__main__":
#     parse = argparse.ArgumentParser()
#     parse.add_argument(
#         "-r",
#         "--refresh",
#         action="store_true",
#         help="refresh the database",
#     )
#     parse.add_argument(
#         "query", type=str, help="the query to search for", nargs="?", default=""
#     )
#     parse.add_argument(
#         "--show-tags",
#         action="store_true",
#         help="Show the tags and rating of the problems",
#     )
#     args = parse.parse_args()
#     d = DataBase(refresh=args.refresh)
#     d.search_problems(args.query, show_tags=args.show_tags)
if __name__ == "__main__":
    print("Starting Codeforces FZF Server on port 6713...")
    server = FzfServer(("localhost", 6713), RequestHandler)
    server.serve_forever()

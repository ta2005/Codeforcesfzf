#!/bin/python
from pathlib import Path
import sqlite3
import urllib.request 
import json

path = "cf.sqlite"

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


if __name__ == "__main__":
    db = DataBase()
    db.create()
    
    problems = getResponse()
    db.insert(problems)
    
    print(f"Inserted {len(problems)} problems into {path}.")
    db.close()

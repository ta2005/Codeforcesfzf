#!/usr/bin/env python3
import json
import re
import urllib.parse as up
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import PORT, SERVER_HOST
from db import DataBase
from problem_parser import parse_problem, format_problem_markdown

PROBLEM_ID_REGEX = re.compile(r"^\d+/[A-Za-z0-9]+$")


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean logging: silence standard GET requests to keep server console clean
        return

    def do_GET(self):
        parsed_url = up.urlparse(self.path)
        path = parsed_url.path
        query_params = up.parse_qs(parsed_url.query)

        try:
            if path == "/search":
                search = query_params.get("q", [""])[0]
                results = self.server.db.search_problems(search.lower())
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(results.encode("utf-8"))

            elif path == "/toggle":
                self.server.db.toggle_tags()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Toggled tags layout")

            elif path == "/refresh":
                self.server.db.refresh()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Refreshed database")

            elif path == "/preview":
                problem_id = query_params.get("id", [""])[0]
                if not PROBLEM_ID_REGEX.match(problem_id):
                    body = "⚠️ Invalid problem id format. Expected format: contestId/index (e.g. 1/A)"
                else:
                    # 1. Check cache first
                    cached = self.server.db.get_cached_statement(problem_id)
                    if cached:
                        body = cached[0]
                    else:
                        # 2. Cache miss: scrape Codeforces
                        try:
                            parsed_data = parse_problem(problem_id)
                            body = format_problem_markdown(parsed_data)
                            # 3. Atomically persist to SQLite BEFORE writing to socket
                            # Even if fzf kills curl, data is safely cached in SQLite
                            self.server.db.save_problem_statement(
                                problem_id=problem_id,
                                statement_md=body,
                                raw_json=json.dumps(parsed_data),
                            )
                        except Exception as e:
                            body = (
                                f"# Error Loading Problem {problem_id}\n\n"
                                f"Failed to fetch statement: `{e}`\n\n"
                                f"Press **Enter** to view directly on Codeforces."
                            )

                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))

            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Endpoint Not Found")

        except (BrokenPipeError, ConnectionResetError):
            # Normal when fzf cancels the curl preview process during fast scrolling
            pass


class FzfServer(HTTPServer):
    def __init__(self, server_address, handler_class):
        super().__init__(server_address, handler_class)
        self.db = DataBase()


if __name__ == "__main__":
    print(f"Starting Codeforces FZF Server on http://{SERVER_HOST}:{PORT}...")
    server = FzfServer((SERVER_HOST, PORT), RequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()

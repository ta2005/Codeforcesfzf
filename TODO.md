## Completed
- [x] Separate the script into modular files (`config.py`, `query_parser.py`, `db.py`, `problem_parser.py`, `server.py`, `cffzf`)
- [x] Solidify database layer with WAL mode (`PRAGMA journal_mode=WAL;`) and atomic transactions
- [x] Create dedicated `problem_statement` table to cache problem descriptions and test cases
- [x] Implement HTML-to-Markdown problem statement converter in `problem_parser.py`
- [x] Integrate Markdown preview pipeline into `cffzf` (using `glow` or `cat`)

## Next Steps
- [ ] Tmux integration: workspace generator script (create problem directory, copy template, write `in.txt`/`out.txt` from cached `raw_json`, and open Neovim)
- [ ] Add more granular query filters to parser (e.g., search by contest ID or rating ranges with shortcuts)
- [ ] Make preview backend configurable (e.g. choose between glow, bat, or raw text)
- [ ] Package for system installation (e.g. `setup.py` / `pyproject.toml` or install script to `~/.local/bin`)

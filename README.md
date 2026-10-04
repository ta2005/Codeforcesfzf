# Codeforces FZF Searcher

A lightning-fast, terminal-based fuzzy finder for Codeforces problems. 

This project uses a Python backend running locally to cache Codeforces problems in a SQLite database and serves them via a tiny HTTP server. A bash script uses `curl` and `fzf` to give you instant, zero-latency filtering across all 9,000+ Codeforces problems.

## Features
- **Ultra-fast filtering:** The UI updates in milliseconds because the Python script stays alive in the background.
- **Advanced Querying:** You aren't just limited to fuzzy finding! You can use strict SQL-backed tags:
  - `r:1200-1600` - Filter by rating range
  - `t:dp,math` - Must include these tags
  - `!t:graphs` - Exclude these tags
  - Example: `r:1800 t:dp !t:trees Watermelon`
- **Dynamic Previews:** Highlights a problem and shows its information instantly.
- **Live Toggles:** 
  - `Ctrl-S`: Toggle problem tags and ratings on the screen without closing the app.
  - `Ctrl-R`: Refresh and sync the SQLite database with the Codeforces API.

## Usage
Simply run:
`./fzf.sh`

*(If the server isn't running yet, fzf.sh will automatically start it in the background for you!)*

## Future Feature
Add tmux intergration 
Add preview
Add more filter 

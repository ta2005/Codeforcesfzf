#!/bin/bash

VIEWER=${BROWSER:-librewolf}
SERVER_URL="http://localhost:6713"

# 1. Start the Python server in the background if it isn't already running!
if ! curl -s "$SERVER_URL/" > /dev/null; then
    echo "Starting Codeforces background server..."
    python3 main.py &
    sleep 1 # Give it a second to boot up
fi

# 2. Run FZF talking only to the ultra-fast server
CHOICE=$(curl -s "$SERVER_URL/" | fzf \
	--disabled \
	--header 'Search (e.g. r:1200 t:dp) | Ctrl-S: Tags | Ctrl-R: Refresh' \
	--bind 'change:reload(curl -s -G --data-urlencode q={q} "'$SERVER_URL'/")' \
	--bind 'ctrl-r:execute-silent(curl -s "'$SERVER_URL'/?ref=true")+reload(curl -s -G --data-urlencode q={q} "'$SERVER_URL'/")' \
	--bind 'ctrl-s:execute-silent(curl -s "'$SERVER_URL'/?toggle=true")+reload(curl -s -G --data-urlencode q={q} "'$SERVER_URL'/")' \
	--delimiter ':' \
	--accept-nth 1 \
	--preview 'echo "Problem Info: {1}"' \
	--expect=enter)

# 3. Handle the selection
key=$(head -1 <<<"$CHOICE")
url=$(head -2 <<<"$CHOICE" | tail -1)

if [[ -n "$url" ]]; then
    # We stripped everything after the colon, so $url is just "contestId/index"
	full_url="https://codeforces.com/problemset/problem/${url}"
	swaymsg exec " ${VIEWER} \"${full_url}\" "
fi

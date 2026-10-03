#!/bin/bash

VIEWER=${BROWSER:-librewolf}

CHOICE=$(python3 main.py "" | fzf \
	--disabled \
	--header 'Search (e.g. r:1200-1600 t:dp !t:graphs)' \
	--bind 'change:reload(python3 main.py {q})' \
	--bind 'ctrl-r:execute(python3 main.py -r {q})' \
	--delimiter ':' \
	--preview 'echo "Problem Info: {1}"' \
	--expect=enter)
# --bind 'enter:become(xdg-open "https://codeforces.com/problemset/problem/"{1} >/dev/null 2>&1)' \

#
key=$(head -1 <<<"$CHOICE")
file=$(head -2 <<<"$CHOICE" | tail -1)
file=$(echo $file | cut -f1 -d':')
file="https://codeforces.com/problemset/problem/${file}"
if [[ -n "$file" ]]; then
	swaymsg exec " ${VIEWER} \"${file}\" "
fi

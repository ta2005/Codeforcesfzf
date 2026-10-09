from pathlib import Path

# Cache and Database paths
CACHE_DIR = Path.home() / ".cache" / "codeforces_fzf"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = CACHE_DIR / "cf.sqlite"

# Server configuration
PORT = 6713
SERVER_HOST = "localhost"

# Rating bounds
MIN_RATING = 800
MAX_RATING = 3500

# Canonical tags list recognized by Codeforces
KNOWN_TAGS = [
    "2_sat",
    "binary_search",
    "bitmasks",
    "brute_force",
    "chinese_remainder_theorem",
    "combinatorics",
    "communication",
    "constructive_algorithms",
    "data_structures",
    "dfs_and_similar",
    "divide_and_conquer",
    "dp",
    "dsu",
    "expression_parsing",
    "fft",
    "flows",
    "games",
    "geometry",
    "graph_matchings",
    "graphs",
    "greedy",
    "hashing",
    "implementation",
    "interactive",
    "math",
    "matrices",
    "meet_in_the_middle",
    "number_theory",
    "probabilities",
    "schedules",
    "shortest_paths",
    "sortings",
    "string_suffix_structures",
    "strings",
    "ternary_search",
    "trees",
    "two_pointers",
]

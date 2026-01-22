import os

DB_FILE = "gguf_history.db"
MD_REPORT_FILE = "HF_RANKING_REPORT.md"
HF_API = "https://huggingface.co/api/models"
HF_JSON_API = "https://huggingface.co/models-json"
HF_TOKEN = os.getenv("HF_TOKEN", "")
SEARCH_LIMIT = 100
PAGES_TO_FETCH = 50
DEEP_SCAN_CACHE_TTL = 3600  # 1 hour in seconds

BLACKLIST_KEYWORDS = [
    "lora",
    "adapter",
    "diffusion",
    "image",
    "text-to-speech",
    "tts",
    "music",
]

GGUF_KINGS = [
    "unsloth",
    "thebloke",
    "maziyarpanahi",
    "bartowski",
    "mradermacher",
    "nousresearch",
]

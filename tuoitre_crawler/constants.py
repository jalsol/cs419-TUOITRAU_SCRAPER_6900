LOGGER_NAME = "tuoitre_crawler"
BASE_DOMAIN = "https://tuoitre.vn"
COMMENT_API = "https://id.tuoitre.vn/api/getlist-comment.api"
COMMENT_APP_KEY = (
    "lHLShlUMAshjvNkHmBzNqERFZammKUXB1DjEuXKfWAwkunzW6fFbfrhP/IG0Xwp7aPwhwIuucLW1TVC9lzmUoA=="
)

ARTICLE_REACTION_LABELS = {
    "1": "star",
    "2": "like",
    "3": "love",
    "4": "haha",
    "5": "sad",
    "6": "wow",
}

COMMENT_REACTION_LABELS = {
    "1": "like",
    "3": "love",
    "5": "haha",
    "7": "sad",
    "9": "wow",
    "11": "angry",
    "13": "star",
}

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

__all__ = [
    "LOGGER_NAME",
    "BASE_DOMAIN",
    "COMMENT_API",
    "COMMENT_APP_KEY",
    "ARTICLE_REACTION_LABELS",
    "COMMENT_REACTION_LABELS",
    "USER_AGENTS",
]

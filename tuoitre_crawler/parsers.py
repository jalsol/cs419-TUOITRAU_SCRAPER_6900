import re

from bs4 import BeautifulSoup

from .constants import ARTICLE_REACTION_LABELS, COMMENT_REACTION_LABELS
from .helpers import absolutize


def normalize_comment(raw):
    reactions = {}
    raw_reactions = raw.get("reactions") or {}
    for key, label in COMMENT_REACTION_LABELS.items():
        value = int(raw_reactions.get(key, 0)) if isinstance(raw_reactions, dict) else 0
        if value:
            reactions[label] = value
    children = raw.get("child_comments") or []
    replies = [normalize_comment(child) for child in children]
    return {
        "commentId": str(raw.get("id")),
        "author": raw.get("sender_fullname"),
        "text": raw.get("content"),
        "date": raw.get("created_date"),
        "vote_reactions": reactions,
        "replies": replies,
    }


def extract_post_id(soup, url):
    meta = soup.find("meta", {"property": "dable:item_id"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    script_text = soup.decode()
    match = re.search(r"articleId'?:\s*'?(\d{10,})", script_text)
    if match:
        return match.group(1)
    digits = re.findall(r"(\d{8,})", url)
    return digits[-1] if digits else None


def extract_metadata(soup):
    title = (soup.find("meta", {"property": "og:title"}) or {}).get("content")
    authors = [name.get_text(strip=True) for name in soup.select(".detail-author .name")]
    if not authors:
        meta_author = soup.find("meta", {"property": "article:author"})
        if meta_author and meta_author.get("content"):
            authors = [meta_author["content"]]
    date_meta = soup.find("meta", {"property": "article:published_time"})
    date_value = date_meta["content"] if date_meta and date_meta.get("content") else None
    category_meta = soup.find("meta", {"property": "article:section"})
    category_value = (
        category_meta["content"] if category_meta and category_meta.get("content") else None
    )
    return {
        "title": title,
        "authors": authors,
        "date": date_value,
        "category": category_value,
    }


def extract_article_content(soup):
    content_root = soup.find(attrs={"data-role": "content"})
    if not content_root:
        content_root = soup
    text_parts = []
    for tag in content_root.find_all(["p", "li", "blockquote", "h2", "h3"]):
        text = tag.get_text(" ", strip=True)
        if text:
            text_parts.append(text)
    images = []
    for img in content_root.find_all("img"):
        src = img.get("data-src") or img.get("src")
        if not src:
            continue
        if src.startswith("data:"):
            continue
        images.append(absolutize(src))
    audio_urls = []
    for audio in content_root.find_all("audio"):
        src = audio.get("src")
        if not src and audio.find("source"):
            src = audio.find("source").get("src")
        if src:
            audio_urls.append(absolutize(src))
    for candidate in content_root.select('[data-type="audio"], [data-component="audio"]'):
        src = candidate.get("data-src") or candidate.get("data-url")
        if src:
            audio_urls.append(absolutize(src))
    return {"text": "\n\n".join(text_parts).strip(), "images": images, "audio": audio_urls}


def extract_article_reactions(soup):
    reactions = {}
    for span in soup.select(".formreactdetail .reactinfo span[data-viewreactid]"):
        reaction_id = span.get("data-viewreactid")
        label = ARTICLE_REACTION_LABELS.get(reaction_id, f"reaction_{reaction_id}")
        counter = span.get_text(strip=True)
        value = int(re.sub(r"[^0-9]", "", counter) or 0)
        reactions[label] = value
    return reactions


__all__ = [
    "normalize_comment",
    "extract_post_id",
    "extract_metadata",
    "extract_article_content",
    "extract_article_reactions",
]

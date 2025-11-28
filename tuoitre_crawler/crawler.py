import json
import logging
import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .constants import COMMENT_API, COMMENT_APP_KEY, LOGGER_NAME
from .helpers import absolutize, filename_from_url
from .http import build_session
from .parsers import (
    extract_article_content,
    extract_article_reactions,
    extract_metadata,
    extract_post_id,
    normalize_comment,
)

LOGGER = logging.getLogger(LOGGER_NAME)


class ProcessedPost:
    def __init__(self, post_id, url, data_path, category, comment_count):
        self.post_id = post_id
        self.url = url
        self.data_path = data_path
        self.category = category
        self.comment_count = comment_count


class TuoiTreCrawler:
    def __init__(
        self,
        output_dir,
        audio_dir,
        image_dir,
        delay=0.6,
        max_workers=4,
        min_comments_target=20,
    ):
        self.session = build_session()
        self.output_dir = output_dir
        self.audio_dir = audio_dir
        self.image_dir = image_dir
        self.delay = delay
        self.max_workers = max_workers
        self.min_comments_target = min_comments_target
        self.random = random.Random()
        self.processed_ids = set()
        self.listing_audio_map = defaultdict(list)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def run(self, categories, posts_per_category):
        summary = {
            "total_posts": 0,
            "total_comments": 0,
            "categories": {},
            "comment_rich_posts": 0,
        }
        self.listing_audio_map.clear()
        for category_url in categories:
            LOGGER.info("Collecting targets for %s", category_url)
            article_urls = self.collect_category_posts(category_url, posts_per_category)
            summary["categories"][category_url] = len(article_urls)
            LOGGER.info(
                "Processing %s posts for %s", len(article_urls), category_url
            )
            results = self.process_posts(category_url, article_urls)
            for result in results:
                summary["total_posts"] += 1
                summary["total_comments"] += result.comment_count
                if result.comment_count >= self.min_comments_target:
                    summary["comment_rich_posts"] += 1
        return summary

    def collect_category_posts(self, category_url, target_count):
        collected = {}
        page = 1
        while len(collected) < target_count:
            page_url = self._page_url(category_url, page)
            html = self.fetch_html(page_url)
            if not html:
                LOGGER.warning("Empty response for %s", page_url)
                break
            soup = BeautifulSoup(html, "html.parser")
            anchors = self._extract_category_links(soup)
            LOGGER.debug(
                "Found %s candidates on page %s of %s", len(anchors), page, category_url
            )
            for href in anchors:
                full = absolutize(href)
                if full not in collected:
                    collected[full] = None
                if len(collected) >= target_count:
                    break
            if not anchors:
                LOGGER.info("No more posts on %s", page_url)
                break
            page += 1
        return list(collected.keys())

    def process_posts(self, category_url, urls):
        results = []
        category_slug = self._category_slug(category_url)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {
                executor.submit(self.process_single_post, url, category_slug): url
                for url in urls
            }
            for future in as_completed(future_map):
                url = future_map[future]
                try:
                    processed = future.result()
                except Exception as exc:  # pragma: no cover - logging path
                    LOGGER.error("Failed to process %s: %s", url, exc)
                    continue
                if processed:
                    results.append(processed)
        return results

    def process_single_post(self, url, fallback_category):
        html = self.fetch_html(url)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        post_id = extract_post_id(soup, url)
        if not post_id:
            LOGGER.warning("Could not determine post id for %s", url)
            return None
        if post_id in self.processed_ids:
            LOGGER.debug("Skipping duplicate post %s", post_id)
            return None

        meta = extract_metadata(soup)
        if not meta.get("title"):
            meta["title"] = soup.title.string.strip() if soup.title else ""
        meta.setdefault("category", fallback_category)
        meta["postId"] = post_id
        meta["url"] = url

        content = extract_article_content(soup)
        meta["content"] = content["text"]
        meta["images"] = content["images"]
        listing_audio = self.listing_audio_map.get(url, [])
        merged_audio = list(dict.fromkeys(content["audio"] + listing_audio))
        meta["audio"] = merged_audio
        meta["vote_reactions"] = extract_article_reactions(soup)

        comment_payload = self.fetch_comments(post_id)
        meta["comments"] = comment_payload["items"]
        meta["comment_count"] = comment_payload["count"]

        local_images = self.download_images(post_id, meta["images"])
        local_audio = self.download_audio(post_id, meta["audio"])

        record = {
            "postId": post_id,
            "title": meta.get("title"),
            "content": meta.get("content"),
            "authors": meta.get("authors", []),
            "date": meta.get("date"),
            "category": meta.get("category"),
            "source_url": url,
            "audio_files": local_audio,
            "image_files": local_images,
            "vote_reactions": meta.get("vote_reactions", {}),
            "comments": meta.get("comments", []),
        }

        data_path = self.output_dir / f"{post_id}.json"
        with data_path.open("w", encoding="utf-8") as fp:
            json.dump(record, fp, ensure_ascii=False, indent=2)

        self.processed_ids.add(post_id)
        LOGGER.info("Saved %s", data_path)

        return ProcessedPost(
            post_id=post_id,
            url=url,
            data_path=data_path,
            category=record["category"],
            comment_count=len(record["comments"]),
        )

    def fetch_comments(self, post_id, page_size=50):
        comments = []
        page = 1
        while True:
            params = {
                "appKey": COMMENT_APP_KEY,
                "objId": post_id,
                "objType": 1,
                "pageindex": page,
                "pagesize": page_size,
            }
            response = self.safe_get(COMMENT_API, params=params)
            if not response:
                break
            try:
                payload = response.json()
            except ValueError:
                break
            raw = payload.get("Data") or "[]"
            try:
                batch = json.loads(raw)
            except ValueError:
                batch = []
            if not batch:
                break
            for comment in batch:
                comments.append(normalize_comment(comment))
            if len(batch) < page_size:
                break
            page += 1
        return {"items": comments, "count": len(comments)}

    def download_images(self, post_id, urls):
        saved = []
        target_dir = self.image_dir / post_id
        target_dir.mkdir(parents=True, exist_ok=True)
        for url in urls:
            file_name = filename_from_url(url)
            if not file_name:
                continue
            dest = target_dir / file_name
            if self.write_binary(url, dest):
                try:
                    saved.append(str(dest.relative_to(self.image_dir)))
                except ValueError:
                    saved.append(str(dest))
        return saved

    def download_audio(self, post_id, urls):
        saved = []
        for idx, url in enumerate(urls):
            ext = Path(filename_from_url(url) or "audio.mp3").suffix or ".mp3"
            name = f"{post_id}{'' if idx == 0 else f'_{idx+1}'}{ext}"
            dest = self.audio_dir / name
            if self.write_binary(url, dest):
                try:
                    saved.append(str(dest.relative_to(self.audio_dir.parent)))
                except ValueError:
                    saved.append(str(dest))
        return saved

    def write_binary(self, url, dest):
        response = self.safe_get(url, stream=True)
        if not response:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)
        return True

    def safe_get(self, url, **kwargs):
        try:
            self._throttle()
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            LOGGER.warning("Request failed for %s: %s", url, exc)
            return None

    def fetch_html(self, url):
        response = self.safe_get(url)
        if not response:
            return ""
        response.encoding = response.encoding or "utf-8"
        return response.text

    def _throttle(self):
        delay = max(0, self.delay + self.random.uniform(0, 0.3))
        time.sleep(delay)

    @staticmethod
    def _page_url(category_url, page):
        if page == 1:
            return category_url
        trimmed = category_url.rstrip("/")
        if trimmed.endswith(".htm"):
            trimmed = trimmed[:-4]
        return f"{trimmed}/trang-{page}.htm"

    def _extract_category_links(self, soup):
        selectors = [
            ".box-category-item a.box-category-link-title",
            "a[data-linktype=\"newsdetail\"]",
            "a[data-role=\"audio-autoplay\"]",
        ]
        links = []
        for selector in selectors:
            for anchor in soup.select(selector):
                href = anchor.get("href")
                if not href or href == "#":
                    continue
                full = absolutize(href)
                data_file = anchor.get("data-file")
                if data_file:
                    audio_url = absolutize(data_file)
                    self._remember_listing_audio(full, audio_url)
                links.append(full)
        return links

    @staticmethod
    def _category_slug(url):
        path = urlparse(url).path.strip("/")
        return path.split("/")[0] if path else "unknown"

    def _remember_listing_audio(self, post_url, audio_url):
        entry = self.listing_audio_map[post_url]
        if audio_url not in entry:
            entry.append(audio_url)


__all__ = ["TuoiTreCrawler", "ProcessedPost"]

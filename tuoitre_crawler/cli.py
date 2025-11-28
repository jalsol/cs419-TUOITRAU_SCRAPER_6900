import argparse
import json
import logging
from pathlib import Path

from .constants import LOGGER_NAME
from .crawler import TuoiTreCrawler


def parse_args():
    parser = argparse.ArgumentParser(description="Crawl tuoitre.vn categories")
    parser.add_argument(
        "--category",
        dest="categories",
        action="append",
        required=True,
        help="Category URL to crawl (repeat for multiple categories)",
    )
    parser.add_argument(
        "--posts-per-category",
        type=int,
        default=40,
        help="Target number of posts per category (>=34 to reach 100 total)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory for JSON/YAML output",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("audio"),
        help="Directory for downloaded audio files",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("images"),
        help="Base directory for downloaded images",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.6,
        help="Base delay between HTTP requests (seconds)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum concurrent article fetchers",
    )
    parser.add_argument(
        "--min-comments-target",
        type=int,
        default=20,
        help="Threshold for counting a post as comment-rich",
    )
    return parser.parse_args()


def validate_args(args):
    if len(args.categories) < 3:
        raise SystemExit("Provide at least three category URLs")
    total_target = args.posts_per_category * len(args.categories)
    if total_target < 100:
        raise SystemExit("Total requested posts must be at least 100")


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        force=True,
    )


def main():
    configure_logging()
    args = parse_args()
    validate_args(args)
    crawler = TuoiTreCrawler(
        output_dir=args.output_dir,
        audio_dir=args.audio_dir,
        image_dir=args.images_dir,
        delay=args.delay,
        max_workers=args.max_workers,
        min_comments_target=args.min_comments_target,
    )
    summary = crawler.run(args.categories, args.posts_per_category)
    logger = logging.getLogger(LOGGER_NAME)
    logger.info("Crawl summary: %s", json.dumps(summary, ensure_ascii=False, indent=2))


__all__ = ["parse_args", "validate_args", "configure_logging", "main"]

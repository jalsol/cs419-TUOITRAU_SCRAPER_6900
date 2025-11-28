# TuoiTre.vn scraper

Lightweight crawler for the A1 assignment that gathers ≥100 posts from tuoitre.vn, downloads associated media, and saves full comment threads for grading. The code now lives inside the `tuoitre_crawler/` package while `main.py` remains the CLI entry point for convenience.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/) for dependency management (already configured)
- Dependencies: `requests`, `beautifulsoup4`

Install the environment once:

```
uv sync
```

## Usage

Run the crawler via `uv run` (recommended) or plain Python. Provide at least three categories and make sure the total target is ≥100 posts.

```
uv run main.py \
    --category https://tuoitre.vn/thoi-su.htm \
    --category https://tuoitre.vn/the-gioi.htm \
    --category https://tuoitre.vn/kinh-doanh.htm \
    --category https://tuoitre.vn/phap-luat.htm \
    --category https://podcast.tuoitre.vn/chu-de/dat-va-nguoi-12.htm \
    --posts-per-category 60 \
    --max-workers 12 \
    --delay 0.45
```

Artifacts are written to:

- `data/` – normalized article JSON
- `images/<postId>/` – downloaded images
- `audio/` – MP3 assets (podcasts or inline players)

## Package layout

```
tuoitre_crawler/
	__init__.py        # exports TuoiTreCrawler
	constants.py       # API endpoints, user agents, reaction maps
	helpers.py         # URL helpers
	http.py            # shared requests Session with retries
	parsers.py         # metadata/content/comment extractors
	crawler.py         # TuoiTreCrawler implementation
	cli.py             # argument parsing + logging
```

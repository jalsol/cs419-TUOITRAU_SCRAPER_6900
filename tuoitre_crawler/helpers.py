from pathlib import Path
from urllib.parse import urljoin, urlparse

from .constants import BASE_DOMAIN


def filename_from_url(url):
    path = urlparse(url).path
    name = Path(path).name
    return name or None


def absolutize(url):
    return urljoin(BASE_DOMAIN, url)


__all__ = ["filename_from_url", "absolutize"]

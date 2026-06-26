import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .models import Post

_thread_local = threading.local()


def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0"})
        _thread_local.session = s
    return _thread_local.session


def download_images(
    posts: list[Post], output_dir: str, session: requests.Session
) -> None:
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    all_images: list[tuple[int, str, str]] = []
    img_src_to_idx: dict[str, int] = {}
    next_idx = 0

    for post in posts:
        soup = BeautifulSoup(post.content_html, "lxml")
        for img in soup.select("img[src]"):
            src = img.get("src", "").strip()
            if src and src not in img_src_to_idx:
                img_src_to_idx[src] = next_idx
                all_images.append((next_idx, src, _normalize_url(src)))
                next_idx += 1

    if not all_images:
        return

    results: dict[int, Optional[str]] = {}

    with ThreadPoolExecutor(max_workers=5) as ex:
        fut_map = {
            ex.submit(_download_one, idx, norm_url, images_dir): idx
            for idx, src, norm_url in all_images
        }
        for fut in as_completed(fut_map):
            idx = fut_map[fut]
            try:
                results[idx] = fut.result()
            except Exception:
                results[idx] = None

    for post in posts:
        soup = BeautifulSoup(post.content_html, "lxml")
        modified = False
        post_images: list[tuple[str, str]] = []

        for img in soup.select("img[src]"):
            src = img.get("src", "").strip()
            if not src:
                continue
            img_idx = img_src_to_idx.get(src)
            if img_idx is None:
                continue
            local_path = results.get(img_idx)
            if local_path:
                img["src"] = os.path.join("images", os.path.basename(local_path))
                post_images.append((src, local_path))
                modified = True
            else:
                post_images.append((src, ""))

        if modified:
            post.content_html = str(soup)
        post.images = post_images


def _normalize_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://www.bb-team.org" + url
    return url


def _download_one(idx: int, url: str, dest_dir: str) -> Optional[str]:
    if not url.startswith(("http://", "https://")):
        return None

    ext = _guess_ext(url)
    filename = f"{idx:05d}{ext}"
    filepath = os.path.join(dest_dir, filename)

    if os.path.exists(filepath):
        return filepath

    try:
        resp = _get_session().get(url, timeout=15, stream=True)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "")
        if "image" not in ct:
            return None

        actual_ext = _ext_from_content_type(ct)
        if actual_ext and actual_ext != ext:
            filename = f"{idx:05d}{actual_ext}"
            filepath = os.path.join(dest_dir, filename)

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return filepath
    except requests.RequestException:
        return None


def _guess_ext(url: str) -> str:
    m = re.search(r"\.(jpe?g|png|gif|webp|bmp|svg|avif)(?:[\?&#]|$)", url, re.I)
    if m:
        return "." + m.group(1).lower()
    return ".jpg"


AVATAR_OFFSET = 100000


def download_avatars(posts: list[Post], output_dir: str) -> None:
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    unique: dict[str, int] = {}
    for post in posts:
        if post.avatar_url and post.avatar_url not in unique:
            unique[post.avatar_url] = len(unique)

    if not unique:
        return

    results: dict[str, Optional[str]] = {}

    with ThreadPoolExecutor(max_workers=5) as ex:
        fut_map = {
            ex.submit(
                _download_one,
                AVATAR_OFFSET + idx,
                _normalize_url(url),
                images_dir,
            ): url
            for url, idx in unique.items()
        }
        for fut in as_completed(fut_map):
            url = fut_map[fut]
            try:
                results[url] = fut.result()
            except Exception:
                results[url] = None

    for post in posts:
        if post.avatar_url and post.avatar_url in results:
            local = results[post.avatar_url]
            if local:
                post.avatar_url = os.path.join("images", os.path.basename(local))
            else:
                post.avatar_url = ""


def _ext_from_content_type(ct: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/svg+xml": ".svg",
        "image/avif": ".avif",
    }
    for mime, ext in mapping.items():
        if mime in ct:
            return ext
    return ""

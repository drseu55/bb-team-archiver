import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from .fetcher import build_url, create_session, fetch_page
from .html_gen import generate_pages
from .image_dl import download_avatars, download_images
from .models import Post
from .parser import parse_page


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:120] or "thread"


def _dir_size(path: str) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))
    return total


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Archive BB-Team forum threads for offline reading",
    )
    p.add_argument("thread_id", type=int, help="Thread ID (e.g. 43647)")
    p.add_argument("--start", type=int, default=1, help="Start page (default: 1)")
    p.add_argument("--end", type=int, default=0, help="End page (default: all)")
    p.add_argument("--output", "-o", type=str, default="", help="Output directory")
    p.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5)",
    )
    p.add_argument("--no-images", action="store_true", help="Skip image download")
    p.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Concurrent page fetches (default: 1, use >1 for speed but be respectful)",
    )
    return p.parse_args(argv)


def main() -> None:
    t0 = time.time()
    args = parse_args()
    thread_id = args.thread_id
    delay = args.delay
    jobs = max(1, args.jobs)

    session = create_session()

    meta_page = args.start if args.start > 1 else 1

    print(f"Page {meta_page}...", flush=True)
    html = fetch_page(session, build_url(thread_id, meta_page), delay)
    if not html:
        sys.exit(1)

    page1_posts, title, total_orig_pages = parse_page(html)
    if not page1_posts:
        print("Error: No posts found in thread.")
        sys.exit(1)

    print(f"Title: {title}")
    print(f"Total pages (original): {total_orig_pages}")

    if args.end:
        total_pages = min(total_orig_pages, args.end)
    else:
        total_pages = total_orig_pages

    first_page = max(1, args.start)
    last_page = total_pages

    page_posts: dict[int, list[Post]] = {}

    for post in page1_posts:
        post.page_num = meta_page
    page_posts[meta_page] = page1_posts

    if meta_page > 1:
        page_posts.clear()
        page_posts[meta_page] = page1_posts

    pages_to_fetch = [
        p for p in range(first_page, last_page + 1)
        if p != meta_page
    ]

    if pages_to_fetch:
        if jobs > 1 and len(pages_to_fetch) > 1:
            results: dict[int, str | None] = {}
            total_jobs = len(pages_to_fetch)

            with ThreadPoolExecutor(max_workers=jobs) as ex:
                def fetch_page_wrapper(p: int) -> tuple[int, str | None]:
                    sess = create_session()
                    h = fetch_page(sess, build_url(thread_id, p), delay)
                    return p, h

                fut_map = {ex.submit(fetch_page_wrapper, p): p for p in pages_to_fetch}
                done = 0
                for fut in as_completed(fut_map):
                    p, h = fut.result()
                    results[p] = h
                    done += 1
                    print(f"  Page {p}/{total_pages} [{done}/{total_jobs}]",
                          flush=True)

            for p in pages_to_fetch:
                h = results.get(p)
                if h:
                    p_posts, _, _ = parse_page(h)
                    for post in p_posts:
                        post.page_num = p
                    page_posts[p] = p_posts
                else:
                    print(f"  Warning: page {p} failed")
        else:
            for page in pages_to_fetch:
                print(f"  Page {page}/{total_pages}...", flush=True)
                h = fetch_page(session, build_url(thread_id, page), delay)
                if h:
                    p_posts, _, _ = parse_page(h)
                    for post in p_posts:
                        post.page_num = page
                    page_posts[page] = p_posts

    all_posts: list[Post] = []
    for p in sorted(page_posts.keys()):
        all_posts.extend(page_posts[p])

    all_posts.sort(key=lambda p: p.post_num)

    if all_posts:
        all_posts[0].is_op = True

    output_dir = args.output or f"thread_{thread_id}"
    os.makedirs(output_dir, exist_ok=True)

    if not args.no_images:
        print(f"Downloading images...", flush=True)
        download_images(all_posts, output_dir, session)
        print(f"Downloading avatars...", flush=True)
        download_avatars(all_posts, output_dir)

    print(f"Generating HTML pages...", flush=True)
    generate_pages(
        title,
        page_posts,
        thread_id,
        total_orig_pages,
        output_dir,
    )

    print(f"Generating metadata JSON...", flush=True)
    _write_json(title, all_posts, thread_id, total_orig_pages, output_dir)

    elapsed = time.time() - t0
    total_size = _dir_size(output_dir)
    size_str = _format_size(total_size)
    print(f"Done! {len(all_posts)} posts saved to {output_dir}/  ({size_str})")
    if all_posts:
        print(f"  Range: posts #{all_posts[0].post_num}–#{all_posts[-1].post_num}, "
              f"pages {first_page}–{last_page}")
    print(f"  Time: {elapsed:.1f}s")


def _write_json(
    title: str,
    all_posts: list[Post],
    thread_id: int,
    total_orig_pages: int,
    output_dir: str,
) -> None:
    def post_dict(p: Post) -> dict:
        images_out: list[dict] = []
        for item in p.images:
            if isinstance(item, tuple):
                orig, local = item
            else:
                orig, local = item, ""
            images_out.append({"original": orig, "local": local})

        return {
            "post_num": p.post_num,
            "page": p.page_num,
            "author": p.author,
            "author_title": p.author_title,
            "date": p.date,
            "is_op": p.is_op,
            "content_html": p.content_html,
            "content_text": re.sub(r"<[^>]+>", "", p.content_html).strip(),
            "images": images_out,
        }

    data = {
        "thread_id": thread_id,
        "title": title,
        "total_pages": total_orig_pages,
        "total_posts": len(all_posts),
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "source_url": f"https://www.bb-team.org/forums/viewthread/{thread_id}",
        "posts": [post_dict(p) for p in all_posts],
    }

    path = os.path.join(output_dir, "metadata.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

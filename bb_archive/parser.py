import re
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from .models import Post

POST_SEL = "div.bg-fff.shadow.br1.pt3.ph3.pb1.mw7.mb3.center"
HEADER_SEL = "div.flex.justify-between.mb3.f6.lh-title"
AUTHOR_SEL = "div.flex"
DATE_SEL = "p.tr.grey-3.ma0"
CONTENT_SEL = "div.mb2"
AVATAR_SEL = "div.flex.items-center.justify-center.w-100.h-100.fff.f6.img-circle.br-100"


def parse_page(html: str) -> tuple[list[Post], str, int]:
    soup = BeautifulSoup(html, "lxml")
    title = get_thread_title(soup)
    total_pages = get_total_pages(soup)
    posts = extract_posts(soup)
    return posts, title, total_pages


def get_thread_title(soup: BeautifulSoup) -> str:
    title_tag = soup.select_one("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        title = re.sub(r"\s*\|\s*(BB-Форум|страница\s+\d+).*$", "", title).strip()
        if title:
            return title
    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(strip=True)
    return "Unknown Thread"


def get_total_pages(soup: BeautifulSoup) -> int:
    found: list[int] = []

    for pagi in soup.select(".pagination"):
        for link in pagi.select("a[href]"):
            href = link.get("href", "")
            m = re.search(r"/P(\d+)", href)
            if m:
                found.append(int(m.group(1)) // 40 + 1)
            elif re.search(r"/viewthread/\d+$", href):
                found.append(1)

    return max(found) if found else 1


def extract_posts(soup: BeautifulSoup) -> list[Post]:
    container_to_avatar: dict[int, str] = {}

    all_posts = soup.select(POST_SEL)
    if not all_posts:
        return []

    parent = all_posts[0].parent if all_posts[0].parent else soup
    children = list(parent.children)

    for i, child in enumerate(children):
        if not hasattr(child, "name") or child.name != "div":
            continue
        cls = " ".join(child.get("class", []))
        if "img-circle" in cls:
            for j in range(i - 1, -1, -1):
                prev = children[j]
                if (
                    hasattr(prev, "name")
                    and prev.name == "div"
                    and "bg-fff" in " ".join(prev.get("class", []))
                    and prev in all_posts
                ):
                    idx = all_posts.index(prev)
                    container_to_avatar[idx] = child.get_text(strip=True)
                    break

    posts: list[Post] = []
    for i, container in enumerate(all_posts):
        post = parse_single_post(container, i, container_to_avatar.get(i, ""))
        if post:
            posts.append(post)

    return posts


def _parse_date(raw: str) -> str:
    # raw: "15.03.1017:52" or "19.03.1015:31#4"
    # return: "15.03.2010 17:52" or "19.03.2010 15:31" (post num stripped)
    m = re.match(r"(\d{1,2}\.\d{2}\.)(\d{2})(\d{2}:\d{2})", raw)
    if m:
        return f"{m.group(1)}20{m.group(2)} {m.group(3)}"
    m = re.match(r"(\d{1,2}\.\d{2}\.)(\d{4})\s*(\d{2}:\d{2})", raw)
    if m:
        return f"{m.group(1)}{m.group(2)} {m.group(3)}"
    m = re.match(r"(\d{1,2}\.\d{2}\.\d{2,4}\s?\d{1,2}:\d{2})", raw)
    if m:
        return m.group(1)
    return raw


def parse_single_post(
    container: Tag, index: int, avatar_title: str
) -> Optional[Post]:
    header = container.select_one(HEADER_SEL)
    if not header:
        return None

    author_el = header.select_one(AUTHOR_SEL)
    date_el = header.select_one(DATE_SEL)
    content_el = container.select_one(CONTENT_SEL)

    if not author_el or not date_el:
        return None

    avatar_url = ""
    avatar_img = author_el.select_one("img[src]")
    if avatar_img:
        avatar_url = avatar_img.get("src", "").strip()

    author_raw = author_el.get_text(strip=True)
    author_title = avatar_title

    if author_title and author_raw.startswith(author_title):
        author = author_raw[len(author_title) :]
    else:
        author = author_raw

    date_raw = date_el.get_text(strip=True)
    date = _parse_date(date_raw)

    post_num = 0
    num_match = re.search(r"#(\d+)", date_raw)
    if num_match:
        post_num = int(num_match.group(1))

    images: list[str] = []
    if content_el:
        for img in content_el.find_all("img", src=True):
            src = img.get("src", "").strip()
            if src:
                images.append(src)
        content_html = content_el.decode_contents()
    else:
        content_html = ""

    is_op = index == 0 and post_num == 0

    return Post(
        author=author,
        author_title=author_title,
        avatar_url=avatar_url,
        date=date,
        post_num=post_num,
        is_op=is_op,
        content_html=content_html,
        images=images,
    )

import html as html_mod
import os
from typing import Optional

from .models import Post

CSS = """\
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif;
  background:#f4f5f7;color:#1a1a2e;line-height:1.65;padding:0}
.container{max-width:860px;margin:0 auto;padding:20px 16px}
h1{font-size:1.5rem;margin-bottom:4px;color:#16213e;word-break:break-word}
.subtitle{color:#666;font-size:0.85rem;margin-bottom:24px;padding-bottom:12px;border-bottom:2px solid #e0e0e0}
.pagination{display:flex;flex-wrap:wrap;align-items:center;gap:4px;
  justify-content:center;margin:16px 0;padding:8px 0}
.page-link{padding:4px 10px;border-radius:4px;text-decoration:none;
  color:#16213e;font-size:0.85rem;background:#fff;border:1px solid #e0e0e0}
.page-link:hover{background:#e94560;color:#fff;border-color:#e94560}
.page-current{background:#16213e;color:#fff;border-color:#16213e;font-weight:600}
.page-dots{color:#999;padding:0 4px}
.goto-form{display:inline-flex;align-items:center;gap:4px;margin-left:8px}
.goto-input{width:52px;padding:3px 6px;border:1px solid #e0e0e0;border-radius:4px;
  font-size:0.85rem;text-align:center;outline:none}
.goto-input:focus{border-color:#e94560}
.goto-btn{padding:4px 10px;border-radius:4px;border:1px solid #e0e0e0;
  background:#fff;color:#16213e;font-size:0.85rem;cursor:pointer}
.goto-btn:hover{background:#e94560;color:#fff;border-color:#e94560}
.post{background:#fff;border-radius:8px;padding:14px 18px;margin-bottom:14px;
  box-shadow:0 1px 3px rgba(0,0,0,.08);border-left:3px solid #e0e0e0}
.post.op{border-left-color:#e94560}
.post-header{display:flex;justify-content:space-between;align-items:center;
  flex-wrap:wrap;gap:4px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #eee;
  font-size:0.85rem;color:#888}
.post-author{font-weight:600;color:#16213e;font-size:0.95rem}
.post-avatar{width:32px;height:32px;border-radius:50%;margin-right:6px;vertical-align:middle}
.post-author-title{color:#e94560;font-size:0.75rem;margin-left:4px}
.post-date{color:#999}
.post-num{color:#bbb;font-size:0.75rem}
.post-body{font-size:0.95rem;line-height:1.7;overflow-wrap:break-word}
.post-body img{max-width:100%;height:auto;border-radius:4px;margin:8px 0;display:block}
.post-body b,strong{color:#16213e}
.post-body blockquote{border-left:3px solid #e94560;background:#fdf2f4;
  margin:8px 0;padding:8px 12px;border-radius:4px;color:#555;font-style:italic}
.post-body blockquote p:last-child{margin-bottom:0}
.footer{text-align:center;color:#999;font-size:0.8rem;margin-top:32px;padding-top:16px;border-top:2px solid #e0e0e0}
"""


def generate_pages(
    thread_title: str,
    page_posts: dict[int, list[Post]],
    thread_id: int,
    total_original_pages: int,
    output_dir: str,
) -> None:
    safe_title = html_mod.escape(thread_title)
    now = html_mod.escape(__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"))

    total_posts = sum(len(pp) for pp in page_posts.values())

    page_range = sorted(page_posts.keys())
    first_page = min(page_range)
    last_page = max(page_range)

    for cur_page in page_range:
        page_file = "index.html" if cur_page == first_page else f"page_{cur_page:02d}.html"
        page_path = os.path.join(output_dir, page_file)

        posts_html = "\n".join(_render_post(p) for p in page_posts[cur_page])
        pagi = _pagination_bar(cur_page, first_page, last_page, total_original_pages)

        html = f"""<!DOCTYPE html>
<html lang="bg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title} — страница {cur_page}</title>
<style>{CSS}</style>
<script>
function goToPage(first,form){{
  var n=parseInt(form.querySelector('input').value);
  if(n>=1){{
    var h=n===first?'index.html':'page_'+(n<10?'0':'')+n+'.html';
    location.href=h;
  }}
  return false;
}}
</script>
</head>
<body>
<div class="container">
<h1>{safe_title}</h1>
<div class="subtitle">
Архивирано от bb-team.org &middot; {total_posts} мнения &middot; {now}
</div>
{pagi}
{posts_html}
{pagi}
<div class="footer">
Архивирано от <a href="https://www.bb-team.org/forums/viewthread/{thread_id}">bb-team.org/forums/viewthread/{thread_id}</a>
</div>
</div>
</body>
</html>"""

        with open(page_path, "w", encoding="utf-8") as f:
            f.write(html)


def _pagination_bar(
    current: int, first_page: int, last_page: int, total_original: int
) -> str:
    total = last_page
    items: list[str] = []

    def _href(page: int) -> str:
        return "index.html" if page == first_page else f"page_{page:02d}.html"

    def link(page: int, label: Optional[str] = None) -> str:
        text = label or str(page)
        return f'<a class="page-link" href="{_href(page)}">{text}</a>'

    def current_span(page: int) -> str:
        return f'<span class="page-link page-current">{page}</span>'

    def dots() -> str:
        return '<span class="page-dots">…</span>'

    if current > first_page:
        prev_p = current - 1
        items.append(f'<a class="page-link page-prev" href="{_href(prev_p)}">‹</a>')

    pages = _visible_pages(current, total, first_page)

    for p in pages:
        if p is None:
            items.append(dots())
        elif p == current:
            items.append(current_span(p))
        else:
            items.append(link(p))

    if current < total:
        next_p = current + 1
        items.append(f'<a class="page-link page-next" href="{_href(next_p)}">›</a>')

    goto = (
        f'<form class="goto-form" onsubmit="return goToPage({first_page},this)">'
        f'<input type="number" class="goto-input"'
        f' min="1" max="{total}" placeholder="№" required>'
        f'<button type="submit" class="goto-btn">Go</button>'
        f"</form>"
    )
    items.append(goto)

    return '<div class="pagination">' + " ".join(items) + "</div>"


def _visible_pages(
    current: int, total: int, first: int
) -> list[Optional[int]]:
    count = total - first + 1
    if count <= 7:
        return list(range(first, total + 1))

    pages: list[Optional[int]] = []

    for p in range(first, min(first + 2, total + 1)):
        pages.append(p)

    if current > first + 3:
        pages.append(None)

    start = max(first + 2, current - 1)
    end = min(total - 1, current + 1)
    for p in range(start, end + 1):
        if p not in pages:
            pages.append(p)

    if current < total - 3:
        pages.append(None)

    for p in range(max(total - 1, first + 3), total + 1):
        if p not in pages:
            pages.append(p)

    return pages


def _render_post(post: Post) -> str:
    op_class = " op" if post.is_op else ""
    author = html_mod.escape(post.author)
    author_title = ""
    if post.author_title:
        author_title = f'<span class="post-author-title">[{html_mod.escape(post.author_title)}]</span>'
    date = html_mod.escape(post.date)
    post_num = f'<span class="post-num">#{post.post_num}</span>' if post.post_num > 0 else ""
    avatar_html = ""
    if post.avatar_url:
        escaped = html_mod.escape(post.avatar_url)
        avatar_html = f'<img class="post-avatar" src="{escaped}" alt="">'

    return f"""<div class="post{op_class}">
<div class="post-header">
<div>{avatar_html}<span class="post-author">{author}</span>{author_title}</div>
<div><span class="post-date">{date}</span> {post_num}</div>
</div>
<div class="post-body">{post.content_html}</div>
</div>"""

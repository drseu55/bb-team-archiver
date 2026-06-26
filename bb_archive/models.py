from dataclasses import dataclass, field


@dataclass
class Post:
    author: str = ""
    author_title: str = ""
    date: str = ""
    post_num: int = 0
    page_num: int = 0
    is_op: bool = False
    avatar_url: str = ""
    content_html: str = ""
    images: list[tuple[str, str]] = field(default_factory=list)

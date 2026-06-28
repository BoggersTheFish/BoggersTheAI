from .base import AdapterRegistry, IngestProtocol
from .hacker_news import HackerNewsAdapter
from .markdown import MarkdownAdapter
from .rss import RSSAdapter
from .wikipedia import WikipediaAdapter
from .x_api import XApiAdapter
from .arxiv import ArXivAdapter
from .semantic_scholar import SemanticScholarAdapter

__all__ = [
    "AdapterRegistry",
    "HackerNewsAdapter",
    "IngestProtocol",
    "MarkdownAdapter",
    "RSSAdapter",
    "WikipediaAdapter",
    "XApiAdapter",
    "ArXivAdapter",
    "SemanticScholarAdapter",
]

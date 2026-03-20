from .base import AdapterRegistry, IngestProtocol
from .hacker_news import HackerNewsAdapter
from .markdown import MarkdownAdapter
from .rss import RSSAdapter
from .vault import VaultAdapter
from .wikipedia import WikipediaAdapter
from .x_api import XApiAdapter

__all__ = [
    "AdapterRegistry",
    "HackerNewsAdapter",
    "IngestProtocol",
    "MarkdownAdapter",
    "RSSAdapter",
    "VaultAdapter",
    "WikipediaAdapter",
    "XApiAdapter",
]

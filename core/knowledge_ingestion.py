"""Knowledge Ingestion Layer for HENLA-6 KS-1.

Handles the ingestion of diverse human knowledge sources with full provenance tracking.
"""

from __future__ import annotations

import time
import hashlib
from typing import Any


class KnowledgeSource:
    def __init__(self, source_type: str, uri: str, author: str = "unknown"):
        self.source_id = hashlib.sha256(f"{source_type}:{uri}:{time.time()}".encode()).hexdigest()[:12]
        self.source_type = source_type
        self.uri = uri
        self.author = author
        self.timestamp = time.time()
        self.metadata: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return vars(self)


class IngestionEngine:
    def __init__(self):
        self.sources: dict[str, KnowledgeSource] = {}

    def ingest(self, source_type: str, uri: str, content: str, author: str = "unknown") -> KnowledgeSource:
        source = KnowledgeSource(source_type, uri, author)
        source.metadata["char_count"] = len(content)
        self.sources[source.source_id] = source
        return source

    def get_source(self, source_id: str) -> KnowledgeSource | None:
        return self.sources.get(source_id)

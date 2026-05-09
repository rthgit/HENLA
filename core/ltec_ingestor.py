"""HENLA-EXT-2 Large Text Experience Corpus (LTEC) Ingestor.

Handles mass ingestion of textual data, converting raw documents into 
structured experiential chunks ready for hypergraph transformation.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any


class LTECIngestor:
    def __init__(self, corpus_name: str = "LTEC-1"):
        self.corpus_name = corpus_name
        self.chunks = []
        self.metadata = {
            "corpus": corpus_name,
            "total_documents": 0,
            "total_chunks": 0,
            "sources": []
        }

    def ingest_directory(self, dir_path: str | Path, glob_pattern: str = "**/*.md"):
        """Ingest all matching files in a directory."""
        path = Path(dir_path)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
            
        files = list(path.glob(glob_pattern))
        for f in files:
            self.ingest_file(f)
            
        return self.metadata

    def ingest_file(self, file_path: str | Path):
        """Ingest a single file, chunking it and extracting metadata."""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        self.metadata["total_documents"] += 1
        self.metadata["sources"].append(str(path))
        
        # Simple chunking by paragraph (for demonstration)
        # In a real system, this would use semantic chunking
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        for i, para in enumerate(paragraphs):
            chunk_id = f"chunk_{hashlib.md5(para.encode()).hexdigest()[:8]}"
            chunk = {
                "id": chunk_id,
                "source": str(path),
                "index": i,
                "content": para,
                "metadata": {
                    "char_count": len(para),
                    "word_count": len(para.split())
                }
            }
            self.chunks.append(chunk)
            self.metadata["total_chunks"] += 1

    def save_corpus(self, output_dir: str | Path):
        """Save the ingested chunks and manifest."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        
        chunks_path = out / "ltec_chunks.jsonl"
        with open(chunks_path, "w", encoding="utf-8") as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk) + "\n")
                
        manifest_path = out / "ltec_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)
            
        print(f"[LTEC] Saved {self.metadata['total_chunks']} chunks from {self.metadata['total_documents']} documents.")
        return manifest_path

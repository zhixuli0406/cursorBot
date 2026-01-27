"""
RAG (Retrieval-Augmented Generation) System for CursorBot

Provides:
- Document loading and processing
- Text chunking strategies
- Embedding generation
- Vector storage and retrieval
- Context-augmented generation

Usage:
    from src.core.rag import get_rag_manager, RAGConfig
    
    rag = get_rag_manager()
    
    # Index documents
    await rag.index_file("/path/to/document.pdf")
    await rag.index_directory("/path/to/docs")
    await rag.index_text("Some text content", metadata={"source": "manual"})
    
    # Query with RAG
    response = await rag.query("What is the main topic?")
    
    # Search without generation
    results = await rag.search("keyword", top_k=5)
"""

import asyncio
import hashlib
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Union

from ..utils.logger import logger


# ============================================
# Data Classes and Enums
# ============================================

class ChunkingStrategy(Enum):
    """Text chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    CODE = "code"
    MARKDOWN = "markdown"


class EmbeddingProvider(Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    GOOGLE = "google"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


@dataclass
class Document:
    """Represents a document chunk."""
    id: str
    content: str
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    
    def __post_init__(self):
        if not self.id:
            # Generate ID from content hash
            self.id = hashlib.md5(self.content.encode()).hexdigest()[:16]


@dataclass
class SearchResult:
    """Search result with relevance score."""
    document: Document
    score: float
    rank: int = 0


@dataclass
class RAGConfig:
    """Configuration for RAG system."""
    # Chunking settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE
    
    # Embedding settings
    embedding_provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    
    # Retrieval settings
    top_k: int = 5
    similarity_threshold: float = 0.7
    
    # Generation settings
    include_sources: bool = True
    max_context_tokens: int = 4000
    
    # Storage settings
    persist_directory: str = "data/rag"
    collection_name: str = "default"


@dataclass
class RAGResponse:
    """Response from RAG query."""
    answer: str
    sources: list[SearchResult] = field(default_factory=list)
    context: str = ""
    metadata: dict = field(default_factory=dict)


# ============================================
# Document Loaders
# ============================================

class DocumentLoader(ABC):
    """Base class for document loaders."""
    
    @abstractmethod
    def load(self, source: str) -> list[Document]:
        """Load documents from source."""
        pass
    
    @abstractmethod
    def supports(self, source: str) -> bool:
        """Check if this loader supports the source."""
        pass


class TextLoader(DocumentLoader):
    """Load plain text files."""
    
    EXTENSIONS = {".txt", ".text", ".log"}
    
    def supports(self, source: str) -> bool:
        return Path(source).suffix.lower() in self.EXTENSIONS
    
    def load(self, source: str) -> list[Document]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        content = path.read_text(encoding="utf-8", errors="ignore")
        return [Document(
            id=hashlib.md5(source.encode()).hexdigest()[:16],
            content=content,
            metadata={
                "source": str(path.absolute()),
                "filename": path.name,
                "type": "text",
                "size": len(content),
            }
        )]


class MarkdownLoader(DocumentLoader):
    """Load Markdown files with structure awareness."""
    
    EXTENSIONS = {".md", ".markdown", ".mdx"}
    
    def supports(self, source: str) -> bool:
        return Path(source).suffix.lower() in self.EXTENSIONS
    
    def load(self, source: str) -> list[Document]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        content = path.read_text(encoding="utf-8", errors="ignore")
        
        # Extract sections based on headings
        sections = self._split_by_headings(content)
        
        documents = []
        for i, (heading, section_content) in enumerate(sections):
            doc_id = f"{hashlib.md5(source.encode()).hexdigest()[:12]}_{i:04d}"
            documents.append(Document(
                id=doc_id,
                content=section_content,
                metadata={
                    "source": str(path.absolute()),
                    "filename": path.name,
                    "type": "markdown",
                    "section": heading,
                    "section_index": i,
                }
            ))
        
        return documents if documents else [Document(
            id=hashlib.md5(source.encode()).hexdigest()[:16],
            content=content,
            metadata={
                "source": str(path.absolute()),
                "filename": path.name,
                "type": "markdown",
            }
        )]
    
    def _split_by_headings(self, content: str) -> list[tuple[str, str]]:
        """Split content by markdown headings."""
        # Pattern to match markdown headings
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        
        sections = []
        last_end = 0
        last_heading = "Introduction"
        
        for match in heading_pattern.finditer(content):
            # Save previous section
            section_content = content[last_end:match.start()].strip()
            if section_content:
                sections.append((last_heading, section_content))
            
            last_heading = match.group(2).strip()
            last_end = match.end()
        
        # Add final section
        final_content = content[last_end:].strip()
        if final_content:
            sections.append((last_heading, final_content))
        
        return sections


class CodeLoader(DocumentLoader):
    """Load source code files."""
    
    EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
        ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".cs",
        ".vue", ".svelte", ".html", ".css", ".scss", ".sass", ".less",
        ".json", ".yaml", ".yml", ".toml", ".xml", ".sql", ".sh", ".bash",
    }
    
    def supports(self, source: str) -> bool:
        return Path(source).suffix.lower() in self.EXTENSIONS
    
    def load(self, source: str) -> list[Document]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        content = path.read_text(encoding="utf-8", errors="ignore")
        language = self._detect_language(path.suffix)
        
        # Split by functions/classes for better context
        chunks = self._split_code(content, language)
        
        documents = []
        for i, chunk in enumerate(chunks):
            doc_id = f"{hashlib.md5(source.encode()).hexdigest()[:12]}_{i:04d}"
            documents.append(Document(
                id=doc_id,
                content=chunk["content"],
                metadata={
                    "source": str(path.absolute()),
                    "filename": path.name,
                    "type": "code",
                    "language": language,
                    "chunk_type": chunk.get("type", "code"),
                    "chunk_index": i,
                }
            ))
        
        return documents
    
    def _detect_language(self, suffix: str) -> str:
        """Detect programming language from file extension."""
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".cs": "csharp",
            ".vue": "vue",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".sh": "bash",
        }
        return language_map.get(suffix.lower(), "unknown")
    
    def _split_code(self, content: str, language: str) -> list[dict]:
        """Split code into logical chunks."""
        chunks = []
        
        if language == "python":
            # Split by class and function definitions
            pattern = re.compile(
                r"^((?:@\w+.*\n)*(?:class|def|async def)\s+\w+.*?)(?=^(?:@\w+.*\n)*(?:class|def|async def)\s+\w+|\Z)",
                re.MULTILINE | re.DOTALL
            )
            
            # Get module-level code first
            first_def = re.search(r"^(?:class|def|async def)\s+", content, re.MULTILINE)
            if first_def and first_def.start() > 0:
                module_code = content[:first_def.start()].strip()
                if module_code:
                    chunks.append({"content": module_code, "type": "module"})
            
            for match in pattern.finditer(content):
                chunk_content = match.group(1).strip()
                if chunk_content:
                    chunk_type = "class" if chunk_content.startswith("class") else "function"
                    chunks.append({"content": chunk_content, "type": chunk_type})
        
        # If no chunks found or other language, use the whole file
        if not chunks:
            chunks.append({"content": content, "type": "file"})
        
        return chunks


class PDFLoader(DocumentLoader):
    """Load PDF files."""
    
    EXTENSIONS = {".pdf"}
    
    def supports(self, source: str) -> bool:
        return Path(source).suffix.lower() in self.EXTENSIONS
    
    def load(self, source: str) -> list[Document]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        try:
            import pypdf
            
            reader = pypdf.PdfReader(str(path))
            documents = []
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    doc_id = f"{hashlib.md5(source.encode()).hexdigest()[:12]}_{i:04d}"
                    documents.append(Document(
                        id=doc_id,
                        content=text,
                        metadata={
                            "source": str(path.absolute()),
                            "filename": path.name,
                            "type": "pdf",
                            "page": i + 1,
                            "total_pages": len(reader.pages),
                        }
                    ))
            
            return documents
            
        except ImportError:
            logger.warning("pypdf not installed, falling back to basic extraction")
            # Return empty for now, user needs to install pypdf
            return [Document(
                id=hashlib.md5(source.encode()).hexdigest()[:16],
                content=f"[PDF file: {path.name}] - Install pypdf to extract content",
                metadata={
                    "source": str(path.absolute()),
                    "filename": path.name,
                    "type": "pdf",
                    "error": "pypdf not installed",
                }
            )]


class JSONLoader(DocumentLoader):
    """Load JSON files."""
    
    EXTENSIONS = {".json", ".jsonl"}
    
    def supports(self, source: str) -> bool:
        return Path(source).suffix.lower() in self.EXTENSIONS
    
    def load(self, source: str) -> list[Document]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        content = path.read_text(encoding="utf-8", errors="ignore")
        
        try:
            if path.suffix.lower() == ".jsonl":
                # JSON Lines format
                documents = []
                for i, line in enumerate(content.strip().split("\n")):
                    if line.strip():
                        data = json.loads(line)
                        text = json.dumps(data, indent=2, ensure_ascii=False)
                        doc_id = f"{hashlib.md5(source.encode()).hexdigest()[:12]}_{i:04d}"
                        documents.append(Document(
                            id=doc_id,
                            content=text,
                            metadata={
                                "source": str(path.absolute()),
                                "filename": path.name,
                                "type": "jsonl",
                                "line": i + 1,
                            }
                        ))
                return documents
            else:
                # Regular JSON
                data = json.loads(content)
                text = json.dumps(data, indent=2, ensure_ascii=False)
                return [Document(
                    id=hashlib.md5(source.encode()).hexdigest()[:16],
                    content=text,
                    metadata={
                        "source": str(path.absolute()),
                        "filename": path.name,
                        "type": "json",
                    }
                )]
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in {source}: {e}")
            return [Document(
                id=hashlib.md5(source.encode()).hexdigest()[:16],
                content=content,
                metadata={
                    "source": str(path.absolute()),
                    "filename": path.name,
                    "type": "json",
                    "error": str(e),
                }
            )]


# ============================================
# Text Chunking
# ============================================

class TextChunker:
    """Split text into chunks for embedding."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
    
    def chunk(self, text: str) -> list[str]:
        """Split text into chunks based on strategy."""
        if self.strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(text)
        elif self.strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentence(text)
        elif self.strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(text)
        elif self.strategy == ChunkingStrategy.MARKDOWN:
            return self._chunk_markdown(text)
        elif self.strategy == ChunkingStrategy.CODE:
            return self._chunk_code(text)
        else:
            return self._chunk_fixed_size(text)
    
    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Chunk multiple documents."""
        chunked = []
        for doc in documents:
            chunks = self.chunk(doc.content)
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{doc.id}_{i:04d}"
                chunk_doc = Document(
                    id=chunk_id,
                    content=chunk_text,
                    metadata={
                        **doc.metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "parent_id": doc.id,
                    }
                )
                chunked.append(chunk_doc)
        return chunked
    
    def _chunk_fixed_size(self, text: str) -> list[str]:
        """Split text into fixed-size chunks with overlap."""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to find a good break point (space, newline)
            if end < len(text):
                # Look for break point in last 20% of chunk
                break_zone_start = end - int(self.chunk_size * 0.2)
                for break_char in ["\n\n", "\n", ". ", " "]:
                    break_pos = text.rfind(break_char, break_zone_start, end)
                    if break_pos > break_zone_start:
                        end = break_pos + len(break_char)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            if start < 0:
                start = 0
        
        return chunks
    
    def _chunk_by_sentence(self, text: str) -> list[str]:
        """Split text by sentences, grouping into chunks."""
        # Simple sentence splitting
        sentence_pattern = re.compile(r"(?<=[.!?])\s+")
        sentences = sentence_pattern.split(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep last sentence for overlap
                if self.chunk_overlap > 0 and current_chunk:
                    current_chunk = [current_chunk[-1]]
                    current_length = len(current_chunk[0])
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _chunk_by_paragraph(self, text: str) -> list[str]:
        """Split text by paragraphs, grouping into chunks."""
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_length = len(para)
            
            if current_length + para_length > self.chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(para)
            current_length += para_length + 2
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    def _chunk_markdown(self, text: str) -> list[str]:
        """Split markdown by sections and code blocks."""
        # Split by headers and code blocks
        pattern = re.compile(
            r"(```[\s\S]*?```|^#{1,6}\s+.+$)",
            re.MULTILINE
        )
        
        parts = pattern.split(text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            part_length = len(part)
            
            # Keep code blocks together
            is_code_block = part.startswith("```")
            
            if current_length + part_length > self.chunk_size and current_chunk and not is_code_block:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(part)
            current_length += part_length + 2
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    def _chunk_code(self, text: str) -> list[str]:
        """Split code by functions/classes/blocks."""
        # Try to split by function/class definitions
        # This is a simplified version
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line)
            
            # Check if this is a new definition
            is_definition = bool(re.match(r"^\s*(def|class|function|const|let|var|public|private|async)\s+", line))
            
            if is_definition and current_length > self.chunk_size // 2 and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(line)
            current_length += line_length + 1
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks


# ============================================
# Embedding Providers
# ============================================

class EmbeddingProviderBase(ABC):
    """Base class for embedding providers."""
    
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        pass
    
    @abstractmethod
    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        pass


class OpenAIEmbedding(EmbeddingProviderBase):
    """OpenAI embedding provider."""
    
    MODELS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._dimensions = self.MODELS.get(model, 1536)
    
    def get_dimensions(self) -> int:
        return self._dimensions
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": texts,
                    "model": self.model,
                },
            )
            
            if response.status_code != 200:
                raise ValueError(f"OpenAI embedding error: {response.status_code} - {response.text}")
            
            result = response.json()
            embeddings = [item["embedding"] for item in result["data"]]
            return embeddings


class GoogleEmbedding(EmbeddingProviderBase):
    """Google Gemini embedding provider."""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-004"):
        self.api_key = api_key or os.getenv("GOOGLE_GENERATIVE_AI_API_KEY")
        self.model = model
        self._dimensions = 768  # Default for Google embeddings
    
    def get_dimensions(self) -> int:
        return self._dimensions
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx
        
        if not self.api_key:
            raise ValueError("Google API key not configured")
        
        embeddings = []
        
        async with httpx.AsyncClient(timeout=60) as client:
            for text in texts:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1/models/{self.model}:embedContent",
                    params={"key": self.api_key},
                    json={
                        "model": f"models/{self.model}",
                        "content": {"parts": [{"text": text}]},
                    },
                )
                
                if response.status_code != 200:
                    raise ValueError(f"Google embedding error: {response.status_code} - {response.text}")
                
                result = response.json()
                embeddings.append(result["embedding"]["values"])
        
        return embeddings


class OllamaEmbedding(EmbeddingProviderBase):
    """Ollama local embedding provider."""
    
    def __init__(self, base_url: str = None, model: str = "nomic-embed-text"):
        self.base_url = base_url or os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        self.model = model
        self._dimensions = 768  # Default, varies by model
    
    def get_dimensions(self) -> int:
        return self._dimensions
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx
        
        embeddings = []
        
        async with httpx.AsyncClient(timeout=120) as client:
            for text in texts:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text,
                    },
                )
                
                if response.status_code != 200:
                    raise ValueError(f"Ollama embedding error: {response.status_code} - {response.text}")
                
                result = response.json()
                embeddings.append(result["embedding"])
        
        return embeddings


# ============================================
# Vector Store
# ============================================

class VectorStore(ABC):
    """Base class for vector stores."""
    
    @abstractmethod
    async def add(self, documents: list[Document]) -> None:
        """Add documents to the store."""
        pass
    
    @abstractmethod
    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    async def delete(self, document_ids: list[str]) -> None:
        """Delete documents by ID."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all documents."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Get document count."""
        pass


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store using cosine similarity."""
    
    def __init__(self):
        self.documents: dict[str, Document] = {}
    
    async def add(self, documents: list[Document]) -> None:
        for doc in documents:
            if doc.embedding is None:
                raise ValueError(f"Document {doc.id} has no embedding")
            self.documents[doc.id] = doc
    
    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        if not self.documents:
            return []
        
        # Calculate cosine similarity
        results = []
        for doc in self.documents.values():
            if doc.embedding:
                score = self._cosine_similarity(query_embedding, doc.embedding)
                results.append(SearchResult(document=doc, score=score))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Add ranks
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1
        
        return results[:top_k]
    
    async def delete(self, document_ids: list[str]) -> None:
        for doc_id in document_ids:
            self.documents.pop(doc_id, None)
    
    async def clear(self) -> None:
        self.documents.clear()
    
    def count(self) -> int:
        return len(self.documents)
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        return dot_product / (magnitude_a * magnitude_b)


class ChromaVectorStore(VectorStore):
    """ChromaDB vector store for persistent storage."""
    
    def __init__(
        self,
        collection_name: str = "default",
        persist_directory: str = "data/rag/chroma",
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._client = None
        self._collection = None
    
    def _get_collection(self):
        """Lazy initialization of ChromaDB client and collection."""
        if self._collection is None:
            try:
                import chromadb
                from chromadb.config import Settings
                
                # Create persist directory
                os.makedirs(self.persist_directory, exist_ok=True)
                
                self._client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(anonymized_telemetry=False),
                )
                
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                
            except ImportError:
                raise ImportError("chromadb not installed. Run: pip install chromadb")
        
        return self._collection
    
    async def add(self, documents: list[Document]) -> None:
        collection = self._get_collection()
        
        ids = [doc.id for doc in documents]
        embeddings = [doc.embedding for doc in documents]
        contents = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        # ChromaDB is synchronous, run in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
            )
        )
    
    async def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        collection = self._get_collection()
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        )
        
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc = Document(
                    id=doc_id,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                )
                # Convert distance to similarity (ChromaDB returns distance)
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance  # For cosine distance
                search_results.append(SearchResult(document=doc, score=score, rank=i + 1))
        
        return search_results
    
    async def delete(self, document_ids: list[str]) -> None:
        collection = self._get_collection()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: collection.delete(ids=document_ids)
        )
    
    async def clear(self) -> None:
        if self._client:
            self._client.delete_collection(self.collection_name)
            self._collection = None
            self._get_collection()  # Recreate
    
    def count(self) -> int:
        collection = self._get_collection()
        return collection.count()


# ============================================
# RAG Manager
# ============================================

class RAGManager:
    """
    Main RAG system manager.
    
    Coordinates document loading, chunking, embedding, storage, and retrieval.
    """
    
    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        
        # Initialize components
        self._loaders: list[DocumentLoader] = [
            TextLoader(),
            MarkdownLoader(),
            CodeLoader(),
            PDFLoader(),
            JSONLoader(),
        ]
        
        self._chunker = TextChunker(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            strategy=self.config.chunking_strategy,
        )
        
        self._embedding_provider: Optional[EmbeddingProviderBase] = None
        self._vector_store: Optional[VectorStore] = None
        self._llm_provider: Optional[Callable] = None
        
        # Stats
        self._indexed_count = 0
        self._query_count = 0
    
    def _get_embedding_provider(self) -> EmbeddingProviderBase:
        """Lazy initialization of embedding provider."""
        if self._embedding_provider is None:
            if self.config.embedding_provider == EmbeddingProvider.OPENAI:
                self._embedding_provider = OpenAIEmbedding(
                    model=self.config.embedding_model
                )
            elif self.config.embedding_provider == EmbeddingProvider.GOOGLE:
                self._embedding_provider = GoogleEmbedding(
                    model=self.config.embedding_model
                )
            elif self.config.embedding_provider == EmbeddingProvider.OLLAMA:
                self._embedding_provider = OllamaEmbedding(
                    model=self.config.embedding_model
                )
            else:
                # Default to OpenAI
                self._embedding_provider = OpenAIEmbedding()
        
        return self._embedding_provider
    
    def _get_vector_store(self) -> VectorStore:
        """Lazy initialization of vector store."""
        if self._vector_store is None:
            # Try ChromaDB first, fall back to in-memory
            try:
                import chromadb
                self._vector_store = ChromaVectorStore(
                    collection_name=self.config.collection_name,
                    persist_directory=self.config.persist_directory,
                )
                logger.info("Using ChromaDB vector store")
            except ImportError:
                logger.info("ChromaDB not available, using in-memory vector store")
                self._vector_store = InMemoryVectorStore()
        
        return self._vector_store
    
    def set_llm_provider(self, provider: Callable) -> None:
        """Set the LLM provider for generation."""
        self._llm_provider = provider
    
    def _get_loader(self, source: str) -> Optional[DocumentLoader]:
        """Find appropriate loader for source."""
        for loader in self._loaders:
            if loader.supports(source):
                return loader
        return None
    
    async def index_file(
        self,
        file_path: str,
        metadata: dict = None,
    ) -> int:
        """
        Index a single file.
        
        Args:
            file_path: Path to the file
            metadata: Additional metadata
            
        Returns:
            Number of chunks indexed
        """
        loader = self._get_loader(file_path)
        if not loader:
            raise ValueError(f"Unsupported file type: {file_path}")
        
        # Load document
        documents = loader.load(file_path)
        
        # Add custom metadata
        if metadata:
            for doc in documents:
                doc.metadata.update(metadata)
        
        # Chunk documents
        chunked = self._chunker.chunk_documents(documents)
        
        # Generate embeddings
        embedding_provider = self._get_embedding_provider()
        texts = [doc.content for doc in chunked]
        
        # Batch embeddings
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await embedding_provider.embed(batch)
            all_embeddings.extend(batch_embeddings)
        
        for doc, embedding in zip(chunked, all_embeddings):
            doc.embedding = embedding
        
        # Store
        vector_store = self._get_vector_store()
        await vector_store.add(chunked)
        
        self._indexed_count += len(chunked)
        logger.info(f"Indexed {len(chunked)} chunks from {file_path}")
        
        return len(chunked)
    
    async def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        extensions: set[str] = None,
        ignore_patterns: list[str] = None,
    ) -> int:
        """
        Index all files in a directory.
        
        Args:
            directory: Path to directory
            recursive: Whether to search recursively
            extensions: File extensions to include (None = all supported)
            ignore_patterns: Glob patterns to ignore
            
        Returns:
            Total number of chunks indexed
        """
        import fnmatch
        
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        ignore_patterns = ignore_patterns or [
            "*.pyc", "__pycache__", ".git", "node_modules",
            ".env", "*.lock", "*.log",
        ]
        
        # Collect supported extensions
        supported_extensions = set()
        for loader in self._loaders:
            if hasattr(loader, "EXTENSIONS"):
                supported_extensions.update(loader.EXTENSIONS)
        
        if extensions:
            supported_extensions = extensions & supported_extensions
        
        # Find files
        files = []
        pattern = "**/*" if recursive else "*"
        
        for file_path in path.glob(pattern):
            if not file_path.is_file():
                continue
            
            # Check extension
            if file_path.suffix.lower() not in supported_extensions:
                continue
            
            # Check ignore patterns
            rel_path = str(file_path.relative_to(path))
            ignored = any(fnmatch.fnmatch(rel_path, p) for p in ignore_patterns)
            if ignored:
                continue
            
            files.append(str(file_path))
        
        # Index files
        total_chunks = 0
        for file_path in files:
            try:
                chunks = await self.index_file(file_path)
                total_chunks += chunks
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
        
        logger.info(f"Indexed {total_chunks} chunks from {len(files)} files in {directory}")
        return total_chunks
    
    async def index_text(
        self,
        text: str,
        doc_id: str = None,
        metadata: dict = None,
    ) -> int:
        """
        Index raw text content.
        
        Args:
            text: Text content to index
            doc_id: Optional document ID
            metadata: Additional metadata
            
        Returns:
            Number of chunks indexed
        """
        doc = Document(
            id=doc_id or hashlib.md5(text.encode()).hexdigest()[:16],
            content=text,
            metadata=metadata or {"source": "manual", "type": "text"},
        )
        
        # Chunk
        chunked = self._chunker.chunk_documents([doc])
        
        # Embed
        embedding_provider = self._get_embedding_provider()
        texts = [d.content for d in chunked]
        embeddings = await embedding_provider.embed(texts)
        
        for d, emb in zip(chunked, embeddings):
            d.embedding = emb
        
        # Store
        vector_store = self._get_vector_store()
        await vector_store.add(chunked)
        
        self._indexed_count += len(chunked)
        return len(chunked)
    
    async def index_url(
        self,
        url: str,
        metadata: dict = None,
    ) -> int:
        """
        Index content from a URL.
        
        Args:
            url: URL to fetch and index
            metadata: Additional metadata
            
        Returns:
            Number of chunks indexed
        """
        import httpx
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
        
        # Determine content type
        content_type = response.headers.get("content-type", "")
        
        meta = metadata or {}
        meta["source"] = url
        meta["content_type"] = content_type
        meta["type"] = "url"
        
        return await self.index_text(content, metadata=meta)
    
    async def search(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: dict = None,
    ) -> list[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Metadata filters
            
        Returns:
            List of search results
        """
        top_k = top_k or self.config.top_k
        
        # Generate query embedding
        embedding_provider = self._get_embedding_provider()
        query_embedding = (await embedding_provider.embed([query]))[0]
        
        # Search
        vector_store = self._get_vector_store()
        results = await vector_store.search(query_embedding, top_k=top_k)
        
        # Filter by threshold
        results = [r for r in results if r.score >= self.config.similarity_threshold]
        
        # Filter by metadata
        if filter_metadata:
            results = [
                r for r in results
                if all(r.document.metadata.get(k) == v for k, v in filter_metadata.items())
            ]
        
        self._query_count += 1
        return results
    
    async def query(
        self,
        question: str,
        top_k: int = None,
        include_sources: bool = None,
        system_prompt: str = None,
    ) -> RAGResponse:
        """
        Query with RAG - retrieves relevant context and generates answer.
        
        Args:
            question: User's question
            top_k: Number of documents to retrieve
            include_sources: Whether to include source information
            system_prompt: Custom system prompt
            
        Returns:
            RAGResponse with answer and sources
        """
        top_k = top_k or self.config.top_k
        include_sources = include_sources if include_sources is not None else self.config.include_sources
        
        # Retrieve relevant documents
        results = await self.search(question, top_k=top_k)
        
        if not results:
            return RAGResponse(
                answer="I couldn't find any relevant information to answer your question.",
                sources=[],
                context="",
            )
        
        # Build context
        context_parts = []
        for i, result in enumerate(results):
            source_info = result.document.metadata.get("source", "unknown")
            context_parts.append(f"[Document {i+1}] (Source: {source_info})\n{result.document.content}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate answer
        if self._llm_provider:
            default_system = """You are a helpful assistant that answers questions based on the provided context.
Use the context to answer the question accurately. If the context doesn't contain enough information,
say so honestly. Always cite sources when possible.

Context:
{context}
"""
            
            system = (system_prompt or default_system).format(context=context)
            
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ]
            
            answer = await self._llm_provider(messages)
        else:
            # No LLM provider, return context summary
            answer = f"Found {len(results)} relevant documents:\n\n"
            for i, result in enumerate(results):
                answer += f"{i+1}. {result.document.content[:200]}...\n\n"
        
        return RAGResponse(
            answer=answer,
            sources=results if include_sources else [],
            context=context,
            metadata={
                "query": question,
                "num_results": len(results),
            }
        )
    
    async def delete_documents(
        self,
        document_ids: list[str] = None,
        filter_metadata: dict = None,
    ) -> int:
        """
        Delete documents from the index.
        
        Args:
            document_ids: Specific document IDs to delete
            filter_metadata: Delete documents matching metadata
            
        Returns:
            Number of documents deleted
        """
        vector_store = self._get_vector_store()
        
        if document_ids:
            await vector_store.delete(document_ids)
            return len(document_ids)
        
        # TODO: Implement metadata-based deletion
        return 0
    
    async def clear(self) -> None:
        """Clear all indexed documents."""
        vector_store = self._get_vector_store()
        await vector_store.clear()
        self._indexed_count = 0
        logger.info("RAG index cleared")
    
    def get_stats(self) -> dict:
        """Get RAG system statistics."""
        vector_store = self._get_vector_store()
        return {
            "indexed_documents": vector_store.count(),
            "total_indexed": self._indexed_count,
            "total_queries": self._query_count,
            "config": {
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap,
                "chunking_strategy": self.config.chunking_strategy.value,
                "embedding_provider": self.config.embedding_provider.value,
                "embedding_model": self.config.embedding_model,
                "top_k": self.config.top_k,
                "similarity_threshold": self.config.similarity_threshold,
            },
        }


# ============================================
# Global Instance
# ============================================

_rag_manager: Optional[RAGManager] = None


def get_rag_manager(config: RAGConfig = None) -> RAGManager:
    """Get the global RAG manager instance."""
    global _rag_manager
    
    if _rag_manager is None:
        # Load config from environment
        from ..utils.config import settings
        
        # Determine embedding provider
        embedding_provider = EmbeddingProvider.OPENAI
        embedding_model = "text-embedding-3-small"
        
        if getattr(settings, 'openai_api_key', None):
            embedding_provider = EmbeddingProvider.OPENAI
            embedding_model = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
        elif getattr(settings, 'google_generative_ai_api_key', None):
            embedding_provider = EmbeddingProvider.GOOGLE
            embedding_model = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-004")
        elif getattr(settings, 'ollama_enabled', False):
            embedding_provider = EmbeddingProvider.OLLAMA
            embedding_model = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
        
        default_config = RAGConfig(
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "50")),
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            top_k=int(os.getenv("RAG_TOP_K", "5")),
            similarity_threshold=float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7")),
            persist_directory=os.getenv("RAG_PERSIST_DIR", "data/rag"),
            collection_name=os.getenv("RAG_COLLECTION", "default"),
        )
        
        _rag_manager = RAGManager(config or default_config)
        
        # Set LLM provider
        try:
            from .llm_providers import get_llm_manager
            llm_manager = get_llm_manager()
            llm_func = llm_manager.get_llm_provider_function()
            if llm_func:
                _rag_manager.set_llm_provider(llm_func)
        except Exception as e:
            logger.warning(f"Failed to set LLM provider for RAG: {e}")
        
        logger.info(f"RAG manager initialized with {embedding_provider.value} embeddings")
    
    return _rag_manager


def reset_rag_manager() -> None:
    """Reset the RAG manager instance."""
    global _rag_manager
    _rag_manager = None


__all__ = [
    # Enums
    "ChunkingStrategy",
    "EmbeddingProvider",
    # Data classes
    "Document",
    "SearchResult",
    "RAGConfig",
    "RAGResponse",
    # Document loaders
    "DocumentLoader",
    "TextLoader",
    "MarkdownLoader",
    "CodeLoader",
    "PDFLoader",
    "JSONLoader",
    # Chunking
    "TextChunker",
    # Embedding
    "EmbeddingProviderBase",
    "OpenAIEmbedding",
    "GoogleEmbedding",
    "OllamaEmbedding",
    # Vector stores
    "VectorStore",
    "InMemoryVectorStore",
    "ChromaVectorStore",
    # Manager
    "RAGManager",
    "get_rag_manager",
    "reset_rag_manager",
]

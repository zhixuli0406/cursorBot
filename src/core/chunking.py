"""
Message Chunking System for CursorBot

Provides:
- Long message splitting
- Smart chunking with context preservation
- Code block aware splitting
- Telegram/Discord message limits handling
"""

import re
from dataclasses import dataclass
from typing import Iterator, Optional

from ..utils.logger import logger


@dataclass
class ChunkConfig:
    """Configuration for message chunking."""
    max_length: int = 4000  # Telegram limit is 4096
    min_chunk_size: int = 100  # Minimum chunk size
    overlap: int = 0  # Characters to overlap between chunks
    preserve_code_blocks: bool = True  # Keep code blocks intact
    preserve_paragraphs: bool = True  # Split at paragraph boundaries
    add_continuation: bool = True  # Add "..." at chunk boundaries
    continuation_prefix: str = "..."
    continuation_suffix: str = " ..."


class MessageChunker:
    """
    Smart message chunking for Telegram and Discord.
    """
    
    # Telegram limits
    TELEGRAM_MESSAGE_LIMIT = 4096
    TELEGRAM_CAPTION_LIMIT = 1024
    
    # Discord limits
    DISCORD_MESSAGE_LIMIT = 2000
    DISCORD_EMBED_LIMIT = 4096
    
    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()
    
    def chunk_message(
        self,
        text: str,
        max_length: int = None,
    ) -> list[str]:
        """
        Split a long message into chunks.
        
        Args:
            text: Text to split
            max_length: Maximum chunk length
        
        Returns:
            List of text chunks
        """
        max_len = max_length or self.config.max_length
        
        if len(text) <= max_len:
            return [text]
        
        # Try smart splitting first
        if self.config.preserve_code_blocks:
            chunks = self._split_preserving_code_blocks(text, max_len)
            if chunks:
                return chunks
        
        if self.config.preserve_paragraphs:
            chunks = self._split_at_paragraphs(text, max_len)
            if chunks:
                return chunks
        
        # Fall back to sentence splitting
        chunks = self._split_at_sentences(text, max_len)
        if chunks:
            return chunks
        
        # Last resort: hard split
        return self._hard_split(text, max_len)
    
    def chunk_for_telegram(self, text: str) -> list[str]:
        """Chunk message for Telegram."""
        return self.chunk_message(text, self.TELEGRAM_MESSAGE_LIMIT - 100)
    
    def chunk_for_discord(self, text: str) -> list[str]:
        """Chunk message for Discord."""
        return self.chunk_message(text, self.DISCORD_MESSAGE_LIMIT - 100)
    
    def _split_preserving_code_blocks(
        self,
        text: str,
        max_len: int,
    ) -> Optional[list[str]]:
        """Split text while preserving code blocks."""
        # Find all code blocks
        code_block_pattern = r'```[\s\S]*?```'
        parts = []
        last_end = 0
        
        for match in re.finditer(code_block_pattern, text):
            # Add text before code block
            if match.start() > last_end:
                parts.append(("text", text[last_end:match.start()]))
            
            # Add code block
            parts.append(("code", match.group()))
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            parts.append(("text", text[last_end:]))
        
        # Build chunks
        chunks = []
        current_chunk = ""
        
        for part_type, content in parts:
            if part_type == "code":
                # Code block - try to keep intact
                if len(current_chunk) + len(content) <= max_len:
                    current_chunk += content
                else:
                    # Save current chunk and start new one with code
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    if len(content) <= max_len:
                        current_chunk = content
                    else:
                        # Code block too long, split it
                        code_chunks = self._split_long_code_block(content, max_len)
                        chunks.extend(code_chunks[:-1])
                        current_chunk = code_chunks[-1] if code_chunks else ""
            else:
                # Regular text
                if len(current_chunk) + len(content) <= max_len:
                    current_chunk += content
                else:
                    # Need to split
                    remaining = content
                    while remaining:
                        space_left = max_len - len(current_chunk)
                        
                        if space_left >= self.config.min_chunk_size:
                            # Add what fits
                            split_point = self._find_split_point(remaining, space_left)
                            current_chunk += remaining[:split_point]
                            remaining = remaining[split_point:]
                        
                        if remaining or len(current_chunk) >= max_len:
                            chunks.append(current_chunk.strip())
                            current_chunk = ""
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else None
    
    def _split_long_code_block(self, code_block: str, max_len: int) -> list[str]:
        """Split a long code block into multiple blocks."""
        # Extract language and content
        match = re.match(r'```(\w*)\n?([\s\S]*?)```', code_block)
        if not match:
            return self._hard_split(code_block, max_len)
        
        lang = match.group(1)
        content = match.group(2)
        
        # Calculate available space for content
        wrapper_len = len(f"```{lang}\n```")
        content_max = max_len - wrapper_len - 20  # Buffer
        
        # Split content by lines
        lines = content.split("\n")
        chunks = []
        current_lines = []
        current_len = 0
        
        for line in lines:
            if current_len + len(line) + 1 <= content_max:
                current_lines.append(line)
                current_len += len(line) + 1
            else:
                if current_lines:
                    chunk_content = "\n".join(current_lines)
                    chunks.append(f"```{lang}\n{chunk_content}\n```")
                current_lines = [line]
                current_len = len(line)
        
        if current_lines:
            chunk_content = "\n".join(current_lines)
            chunks.append(f"```{lang}\n{chunk_content}\n```")
        
        return chunks
    
    def _split_at_paragraphs(self, text: str, max_len: int) -> Optional[list[str]]:
        """Split text at paragraph boundaries."""
        paragraphs = text.split("\n\n")
        
        if len(paragraphs) == 1:
            return None
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_len:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                if len(para) <= max_len:
                    current_chunk = para
                else:
                    # Paragraph too long, split further
                    sub_chunks = self._split_at_sentences(para, max_len)
                    if sub_chunks:
                        chunks.extend(sub_chunks[:-1])
                        current_chunk = sub_chunks[-1]
                    else:
                        current_chunk = para[:max_len]
                        chunks.append(current_chunk)
                        current_chunk = para[max_len:]
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else None
    
    def _split_at_sentences(self, text: str, max_len: int) -> Optional[list[str]]:
        """Split text at sentence boundaries."""
        # Simple sentence detection
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_endings.split(text)
        
        if len(sentences) == 1:
            return None
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_len:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else None
    
    def _hard_split(self, text: str, max_len: int) -> list[str]:
        """Hard split at max length, trying to break at words."""
        chunks = []
        
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break
            
            # Find split point
            split_point = self._find_split_point(text, max_len)
            chunks.append(text[:split_point].strip())
            text = text[split_point:].strip()
        
        return chunks
    
    def _find_split_point(self, text: str, max_len: int) -> int:
        """Find a good split point near max_len."""
        if len(text) <= max_len:
            return len(text)
        
        # Try to split at word boundary
        split_point = max_len
        
        # Look for space before max_len
        space_pos = text.rfind(" ", 0, max_len)
        if space_pos > max_len // 2:
            split_point = space_pos
        
        # Look for newline
        newline_pos = text.rfind("\n", 0, max_len)
        if newline_pos > max_len // 2:
            split_point = newline_pos
        
        return split_point
    
    def add_chunk_indicators(
        self,
        chunks: list[str],
        format_str: str = "[{current}/{total}]",
    ) -> list[str]:
        """Add chunk indicators to each chunk."""
        total = len(chunks)
        return [
            f"{format_str.format(current=i+1, total=total)}\n{chunk}"
            for i, chunk in enumerate(chunks)
        ]
    
    def estimate_chunks(self, text: str, max_length: int = None) -> int:
        """Estimate how many chunks a text will produce."""
        max_len = max_length or self.config.max_length
        if len(text) <= max_len:
            return 1
        return (len(text) // max_len) + 1


def chunk_message(
    text: str,
    max_length: int = 4000,
    preserve_code: bool = True,
) -> list[str]:
    """
    Convenience function to chunk a message.
    
    Args:
        text: Text to chunk
        max_length: Maximum chunk length
        preserve_code: Preserve code blocks
    
    Returns:
        List of chunks
    """
    config = ChunkConfig(
        max_length=max_length,
        preserve_code_blocks=preserve_code,
    )
    chunker = MessageChunker(config)
    return chunker.chunk_message(text)


def iter_chunks(
    text: str,
    max_length: int = 4000,
) -> Iterator[str]:
    """
    Iterate over chunks of a message.
    
    Args:
        text: Text to chunk
        max_length: Maximum chunk length
    
    Yields:
        Text chunks
    """
    chunks = chunk_message(text, max_length)
    yield from chunks


__all__ = [
    "ChunkConfig",
    "MessageChunker",
    "chunk_message",
    "iter_chunks",
]

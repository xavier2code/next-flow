"""Memory service module: unified entry point for all memory operations.

Per D-18, D-21: MemoryService is the single entry point. Nodes call MemoryService
methods, never Redis or Store directly.
"""

from app.services.memory.embedder import get_embedder
from app.services.memory.long_term import LongTermMemory
from app.services.memory.service import MemoryService
from app.services.memory.short_term import ShortTermMemory

__all__ = ["MemoryService", "ShortTermMemory", "LongTermMemory", "get_embedder"]

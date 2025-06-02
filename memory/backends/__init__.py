"""
Memory backend implementations for the memory manager.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

@dataclass
class SessionData:
    """Session data structure"""
    session_id: str
    created_at: datetime
    last_activity: datetime
    status: str
    input_data: Dict[str, Any]
    agent_results: Dict[str, Any]
    metadata: Dict[str, Any]

class MemoryBackend(ABC):
    """Abstract base class for memory backends"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the memory backend"""
        pass
    
    @abstractmethod
    async def store_session(self, session_data: SessionData) -> None:
        """Store session data"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session data"""
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session data"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete session data"""
        pass
    
    @abstractmethod
    async def list_sessions(self, limit: int = 100) -> List[SessionData]:
        """List all sessions"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if backend is connected"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connections"""
        pass

"""
In-memory backend implementation for the memory manager.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from . import MemoryBackend, SessionData

class InMemoryBackend(MemoryBackend):
    """In-memory storage backend"""
    
    def __init__(self, max_sessions: int = 1000, session_ttl: int = 3600):
        self.sessions: Dict[str, SessionData] = {}
        self.max_sessions = max_sessions
        self.session_ttl = session_ttl
        self.logger = logging.getLogger("memory.in_memory")
        self._cleanup_task = None
    
    async def initialize(self) -> None:
        """Initialize in-memory backend"""
        self.logger.info("🧠 Initializing in-memory storage")
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
    
    async def store_session(self, session_data: SessionData) -> None:
        """Store session in memory"""
        # Clean up if at capacity
        if len(self.sessions) >= self.max_sessions:
            await self._cleanup_oldest_sessions()
        
        self.sessions[session_data.session_id] = session_data
        self.logger.debug(f"Stored session {session_data.session_id}")
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session from memory"""
        session = self.sessions.get(session_id)
        if session and not self._is_expired(session):
            return session
        elif session:
            # Remove expired session
            del self.sessions[session_id]
        return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session data"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.last_activity = datetime.now()
            self.logger.debug(f"Updated session {session_id}")
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session from memory"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.debug(f"Deleted session {session_id}")
    
    async def list_sessions(self, limit: int = 100) -> List[SessionData]:
        """List sessions"""
        sessions = list(self.sessions.values())
        # Remove expired sessions
        valid_sessions = [s for s in sessions if not self._is_expired(s)]
        # Sort by last activity
        valid_sessions.sort(key=lambda x: x.last_activity, reverse=True)
        return valid_sessions[:limit]
    
    async def is_connected(self) -> bool:
        """Check if backend is available"""
        return True
    
    async def close(self) -> None:
        """Close backend"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        self.sessions.clear()
        self.logger.info("🧠 In-memory storage closed")
    
    def _is_expired(self, session: SessionData) -> bool:
        """Check if session is expired"""
        expiry_time = session.last_activity + timedelta(seconds=self.session_ttl)
        return datetime.now() > expiry_time
    
    async def _cleanup_expired_sessions(self):
        """Periodically clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                expired_sessions = [
                    sid for sid, session in self.sessions.items()
                    if self._is_expired(session)
                ]
                for session_id in expired_sessions:
                    del self.sessions[session_id]
                
                if expired_sessions:
                    self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
    
    async def _cleanup_oldest_sessions(self):
        """Clean up oldest sessions when at capacity"""
        if len(self.sessions) >= self.max_sessions:
            # Sort by last activity and remove oldest 10%
            sessions_by_age = sorted(
                self.sessions.items(),
                key=lambda x: x[1].last_activity
            )
            
            to_remove = max(1, len(sessions_by_age) // 10)
            for session_id, _ in sessions_by_age[:to_remove]:
                del self.sessions[session_id]
            
            self.logger.info(f"Cleaned up {to_remove} oldest sessions")

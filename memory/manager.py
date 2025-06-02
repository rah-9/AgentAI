"""
Memory Manager for Invoice Processing System
Handles session storage, agent results, and data persistence
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import uuid

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

class MemoryManager:
    """Main memory manager class"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backend: Optional[MemoryBackend] = None
        self.logger = logging.getLogger("memory.manager")
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize memory manager"""
        backend_type = self.config.get("type", "in_memory")
        
        if backend_type == "in_memory":
            self.backend = InMemoryBackend(
                max_sessions=self.config.get("max_sessions", 1000),
                session_ttl=self.config.get("session_ttl", 3600)
            )
        else:
            raise ValueError(f"Unsupported memory backend: {backend_type}")
        
        await self.backend.initialize()
        self.logger.info(f"✅ Memory manager initialized with {backend_type} backend")
    
    async def create_session(self, input_data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session_data = SessionData(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            status="created",
            input_data=input_data,
            agent_results={},
            metadata=metadata or {}
        )
        
        async with self._lock:
            await self.backend.store_session(session_data)
        
        self.logger.info(f"📝 Created session {session_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session = await self.backend.get_session(session_id)
        if session:
            return {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "status": session.status,
                "input_data": session.input_data,
                "agent_results": session.agent_results,
                "metadata": session.metadata
            }
        return None
    
    async def update_session_status(self, session_id: str, status: str) -> None:
        """Update session status"""
        await self.backend.update_session(session_id, {"status": status})
        self.logger.debug(f"Updated session {session_id} status to {status}")
    
    async def store_agent_result(self, session_id: str, agent_name: str, result: Dict[str, Any]) -> None:
        """Store agent processing result"""
        session = await self.backend.get_session(session_id)
        if session:
            session.agent_results[agent_name] = {
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            await self.backend.update_session(session_id, {
                "agent_results": session.agent_results
            })
            self.logger.debug(f"Stored {agent_name} result for session {session_id}")
    
    async def get_agent_result(self, session_id: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get specific agent result"""
        session = await self.backend.get_session(session_id)
        if session and agent_name in session.agent_results:
            return session.agent_results[agent_name]
        return None
    
    async def list_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List recent sessions"""
        sessions = await self.backend.list_sessions(limit)
        return [
            {
                "session_id": s.session_id,
                "created_at": s.created_at.isoformat(),
                "last_activity": s.last_activity.isoformat(),
                "status": s.status,
                "agent_count": len(s.agent_results)
            }
            for s in sessions
        ]
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        await self.backend.delete_session(session_id)
        self.logger.info(f"🗑️ Deleted session {session_id}")
    
    async def is_connected(self) -> bool:
        """Check if memory backend is connected"""
        if self.backend:
            return await self.backend.is_connected()
        return False
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get memory usage metrics"""
        sessions = await self.backend.list_sessions(1000)
        
        total_sessions = len(sessions)
        status_counts = {}
        for session in sessions:
            status = session.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "status_distribution": status_counts,
            "backend_type": self.config.get("type", "unknown"),
            "backend_connected": await self.is_connected(),
            "memory_config": {
                "max_sessions": self.config.get("max_sessions", 1000),
                "session_ttl": self.config.get("session_ttl", 3600)
            }
        }
    
    async def close(self) -> None:
        """Close memory manager"""
        if self.backend:
            await self.backend.close()
        self.logger.info("🧠 Memory manager closed")

    def log_trace(self, source, classification, extracted_fields, actions_triggered, agent_trace):
        import json
        import time
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'source': source,
            'classification': classification,
            'extracted_fields': extracted_fields,
            'actions_triggered': actions_triggered,
            'agent_trace': agent_trace
        }
        with open('trace.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')


"""
Memory management system for the invoice processing application.
Handles session storage, agent results, and data persistence.
"""

from .manager import MemoryManager, SessionData
from .backends.in_memory import InMemoryBackend
from .backends import MemoryBackend
from .schemas import (
    SessionStatus,
    AgentStatus,
    MemoryBackendType,
    CreateSessionRequest,
    UpdateSessionRequest,
    StoreAgentResultRequest,
    SessionDataModel,
    AgentResult,
    SessionResponse,
    SessionSummaryResponse,
    AgentResultResponse,
    ListSessionsResponse,
    MemoryMetricsResponse,
    InMemoryBackendConfig,
    RedisBackendConfig,
    MongoBackendConfig,
    PostgreSQLBackendConfig,
    MemoryManagerConfig,
    ErrorResponse,
    ValidationErrorResponse,
    SessionQueryParams,
    HealthCheckResponse,
    SessionEvent,
    AgentEvent,
    validate_session_data,
    validate_agent_result,
    serialize_session_for_api
)

__all__ = [
    'MemoryManager',
    'SessionData',
    'InMemoryBackend',
    'MemoryBackend',
    'SessionStatus',
    'AgentStatus',
    'MemoryBackendType',
    'CreateSessionRequest',
    'UpdateSessionRequest',
    'StoreAgentResultRequest',
    'SessionDataModel',
    'AgentResult',
    'SessionResponse',
    'SessionSummaryResponse',
    'AgentResultResponse',
    'ListSessionsResponse',
    'MemoryMetricsResponse',
    'InMemoryBackendConfig',
    'RedisBackendConfig',
    'MongoBackendConfig',
    'PostgreSQLBackendConfig',
    'MemoryManagerConfig',
    'ErrorResponse',
    'ValidationErrorResponse',
    'SessionQueryParams',
    'HealthCheckResponse',
    'SessionEvent',
    'AgentEvent',
    'validate_session_data',
    'validate_agent_result',
    'serialize_session_for_api'
]

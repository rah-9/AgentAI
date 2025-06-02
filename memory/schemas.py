"""
Data schemas and validation models for Memory Manager
Defines Pydantic models for type safety and validation
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import uuid


class SessionStatus(str, Enum):
    """Session status enumeration"""
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AgentStatus(str, Enum):
    """Agent processing status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class MemoryBackendType(str, Enum):
    """Supported memory backend types"""
    IN_MEMORY = "in_memory"
    REDIS = "redis"
    MONGODB = "mongodb"
    POSTGRESQL = "postgresql"


# Request/Response Models

class CreateSessionRequest(BaseModel):
    """Request model for creating a new session"""
    input_data: Dict[str, Any] = Field(..., description="Input data for the session")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")
    session_ttl: Optional[int] = Field(None, ge=60, le=86400, description="Session TTL in seconds (60s - 24h)")
    
    class Config:
        schema_extra = {
            "example": {
                "input_data": {
                    "user_query": "Analyze this document",
                    "document_url": "https://example.com/doc.pdf",
                    "analysis_type": "comprehensive"
                },
                "metadata": {
                    "user_id": "user123",
                    "priority": "high",
                    "source": "web_interface"
                },
                "session_ttl": 3600
            }
        }


class UpdateSessionRequest(BaseModel):
    """Request model for updating session data"""
    status: Optional[SessionStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('metadata')
    def validate_metadata(cls, v):
        if v is not None and not isinstance(v, dict):
            raise ValueError('metadata must be a dictionary')
        return v


class StoreAgentResultRequest(BaseModel):
    """Request model for storing agent results"""
    agent_name: str = Field(..., min_length=1, max_length=100, description="Name of the agent")
    result: Dict[str, Any] = Field(..., description="Agent processing result")
    status: AgentStatus = Field(default=AgentStatus.SUCCESS, description="Agent processing status")
    execution_time: Optional[float] = Field(None, ge=0, description="Execution time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if status is error")
    
    @validator('error_message')
    def validate_error_message(cls, v, values):
        if values.get('status') == AgentStatus.ERROR and not v:
            raise ValueError('error_message is required when status is error')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "agent_name": "document_analyzer",
                "result": {
                    "summary": "Document contains financial analysis...",
                    "key_points": ["Revenue increased by 15%", "New market expansion"],
                    "confidence_score": 0.92
                },
                "status": "success",
                "execution_time": 2.34
            }
        }


# Core Data Models

class AgentResult(BaseModel):
    """Agent result data model"""
    result: Dict[str, Any] = Field(..., description="Agent processing result")
    status: AgentStatus = Field(default=AgentStatus.SUCCESS)
    timestamp: datetime = Field(default_factory=datetime.now)
    execution_time: Optional[float] = Field(None, ge=0)
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class SessionDataModel(BaseModel):
    """Complete session data model"""
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    status: SessionStatus = Field(default=SessionStatus.CREATED)
    input_data: Dict[str, Any] = Field(..., description="Original input data")
    agent_results: Dict[str, AgentResult] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_ttl: Optional[int] = Field(None, ge=60, le=86400)
    
    @validator('session_id')
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('session_id must be a valid UUID')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_timestamps(cls, values):
        created_at = values.get('created_at')
        last_activity = values.get('last_activity')
        
        if created_at and last_activity and last_activity < created_at:
            raise ValueError('last_activity cannot be before created_at')
        
        return values
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


# Response Models

class SessionResponse(BaseModel):
    """Session data response model"""
    session_id: str
    created_at: str  # ISO format
    last_activity: str  # ISO format
    status: SessionStatus
    input_data: Dict[str, Any]
    agent_results: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any]
    agent_count: int = Field(..., description="Number of agents that have processed this session")
    
    @validator('agent_count', pre=True, always=True)
    def calculate_agent_count(cls, v, values):
        agent_results = values.get('agent_results', {})
        return len(agent_results)


class SessionSummaryResponse(BaseModel):
    """Lightweight session summary for listing"""
    session_id: str
    created_at: str  # ISO format
    last_activity: str  # ISO format
    status: SessionStatus
    agent_count: int
    metadata_keys: List[str] = Field(..., description="Available metadata keys")


class AgentResultResponse(BaseModel):
    """Agent result response model"""
    result: Dict[str, Any]
    status: AgentStatus
    timestamp: str  # ISO format
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class ListSessionsResponse(BaseModel):
    """Response for listing sessions"""
    sessions: List[SessionSummaryResponse]
    total_count: int
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=100, ge=1, le=1000)
    has_more: bool


class MemoryMetricsResponse(BaseModel):
    """Memory system metrics response"""
    total_sessions: int = Field(ge=0)
    active_sessions: int = Field(ge=0)
    status_distribution: Dict[SessionStatus, int]
    backend_type: MemoryBackendType
    backend_connected: bool
    memory_config: Dict[str, Any]
    uptime_seconds: Optional[float] = None
    last_cleanup: Optional[str] = None  # ISO format


# Configuration Models

class InMemoryBackendConfig(BaseModel):
    """In-memory backend configuration"""
    type: Literal["in_memory"] = "in_memory"
    max_sessions: int = Field(default=1000, ge=1, le=100000)
    session_ttl: int = Field(default=3600, ge=60, le=86400)
    cleanup_interval: int = Field(default=300, ge=60, le=3600)


class RedisBackendConfig(BaseModel):
    """Redis backend configuration"""
    type: Literal["redis"] = "redis"
    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0)
    password: Optional[str] = None
    connection_pool_size: int = Field(default=10, ge=1, le=100)
    session_ttl: int = Field(default=3600, ge=60, le=86400)


class MongoBackendConfig(BaseModel):
    """MongoDB backend configuration"""
    type: Literal["mongodb"] = "mongodb"
    connection_string: str
    database_name: str = Field(default="invoice_processing")
    collection_name: str = Field(default="sessions")
    session_ttl: int = Field(default=3600, ge=60, le=86400)


class PostgreSQLBackendConfig(BaseModel):
    """PostgreSQL backend configuration"""
    type: Literal["postgresql"] = "postgresql"
    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    database: str
    username: str
    password: str
    table_name: str = Field(default="sessions")
    connection_pool_size: int = Field(default=5, ge=1, le=20)
    session_ttl: int = Field(default=3600, ge=60, le=86400)


class MemoryManagerConfig(BaseModel):
    """Main memory manager configuration"""
    backend: Union[
        InMemoryBackendConfig,
        RedisBackendConfig,
        MongoBackendConfig,
        PostgreSQLBackendConfig
    ] = Field(..., discriminator='type')
    enable_metrics: bool = Field(default=True)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")


# Error Models

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    session_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "validation_error"
    message: str
    details: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# Query Models

class SessionQueryParams(BaseModel):
    """Query parameters for session listing"""
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    status: Optional[SessionStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    sort_by: str = Field(default="last_activity", pattern="^(created_at|last_activity|status)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    
    @validator('created_before')
    def validate_date_range(cls, v, values):
        created_after = values.get('created_after')
        if created_after and v and v <= created_after:
            raise ValueError('created_before must be after created_after')
        return v


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    backend_connected: bool
    total_sessions: int
    version: str = "1.0.0"


# Event Models (for potential event-driven features)

class SessionEvent(BaseModel):
    """Session lifecycle event"""
    event_type: str = Field(..., pattern="^(created|updated|completed|failed|deleted)$")
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class AgentEvent(BaseModel):
    """Agent processing event"""
    event_type: str = Field(..., pattern="^(started|completed|failed|timeout)$")
    session_id: str
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


# Utility functions for schema validation

def validate_session_data(data: Dict[str, Any]) -> SessionDataModel:
    """Validate and convert dictionary to SessionDataModel"""
    return SessionDataModel(**data)


def validate_agent_result(data: Dict[str, Any]) -> AgentResult:
    """Validate and convert dictionary to AgentResult"""
    return AgentResult(**data)


def serialize_session_for_api(session: SessionDataModel) -> SessionResponse:
    """Convert SessionDataModel to API response format"""
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        last_activity=session.last_activity.isoformat(),
        status=session.status,
        input_data=session.input_data,
        agent_results={
            name: {
                "result": result.result,
                "status": result.status,
                "timestamp": result.timestamp.isoformat(),
                "execution_time": result.execution_time,
                "error_message": result.error_message,
                "retry_count": result.retry_count
            }
            for name, result in session.agent_results.items()
        },
        metadata=session.metadata
    )

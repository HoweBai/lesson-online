"""API schemas for tutorial-related endpoints."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TutorialStatus(str, Enum):
    DRAFT = "draft"
    REVIEWING = "reviewing"
    PUBLISHED = "published"
    RETIRED = "retired"


class OutlineStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ChapterStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateOutlineRequest(BaseModel):
    """Request body for generating a course outline."""
    claude_config_id: str = Field(..., description="ID of the Claude configuration to use")
    profile_id: str = Field(..., description="ID of the user profile")
    topics: List[str] = Field(
        ...,
        description="Topics to include in the outline",
        example=["algorithm_analysis", "sorting_algorithms", "data_structures"]
    )


class OutlineStatusResponse(BaseModel):
    """Response for checking outline generation status."""
    task_id: str
    status: OutlineStatus
    progress: int = Field(..., ge=0, le=100)
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    outline_data: Optional[Dict[str, Any]] = None


class ConfirmOutlineRequest(BaseModel):
    """Request to confirm an generated outline and create a tutorial."""
    selected_chapters: List[int] = Field(
        default_factory=list,
        description="Chapters to initially generate (empty means all)"
    )
    title: Optional[str] = Field(None, description="Custom title for the tutorial")
    description: Optional[str] = Field(None, description="Description for the tutorial")


class GenerateNextChapterRequest(BaseModel):
    """Request to generate the next chapter in a tutorial."""
    pass


class ChapterStatusResponse(BaseModel):
    """Response for checking chapter generation status."""
    tutorial_id: str
    chapter_number: int
    status: ChapterStatus
    progress: int = Field(..., ge=0, le=100)
    content_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    chapter_content: Optional[Dict[str, Any]] = None


class TutorialSummary(BaseModel):
    """Summary view of a tutorial (used in lists)."""
    id: str
    title: str
    description: Optional[str] = None
    owner_id: str
    is_public: bool
    status: TutorialStatus
    total_chapters: Optional[int] = None
    current_chapter: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TutorialDetail(TutorialSummary):
    """Detailed view of a tutorial including outline and chapter list."""
    outline: Optional[Dict[str, Any]] = None
    chapters: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class ChapterSummary(BaseModel):
    """Summary of a single chapter."""
    id: str
    tutorial_id: str
    chapter_number: int
    title: str
    status: ChapterStatus
    generated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_reading_min: Optional[int] = None

    class Config:
        from_attributes = True


class TaskLogSummary(BaseModel):
    """Summary of a background task log entry."""
    id: str
    task_type: str
    status: str
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ClaudeConfigRequest(BaseModel):
    """Request to save a Claude API configuration."""
    base_url: str = Field(..., description="API base URL (e.g., https://api.anthropic.com)")
    api_key: str = Field(..., description="API key")
    model_name: Optional[str] = Field("claude-3-opus-20240925", description="Model name")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    is_default: bool = Field(False, description="Set as default configuration")


class ClaudeConfigResponse(BaseModel):
    """Response for Claude API configuration."""
    id: str
    user_id: str
    base_url: str
    model_name: Optional[str] = None
    system_prompt: Optional[str] = None
    is_default: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True

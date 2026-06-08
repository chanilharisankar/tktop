from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )


@dataclass
class ToolCall:
    name: str
    id: str


@dataclass
class Turn:
    number: int
    timestamp: datetime
    role: str
    model: str | None
    usage: TokenUsage
    tool_calls: list[ToolCall] = field(default_factory=list)
    content_preview: str = ""


@dataclass
class Alert:
    severity: str
    type: str
    description: str
    detected_at: datetime


@dataclass
class ToolStat:
    name: str
    calls: int = 0
    turns_present: int = 0


@dataclass
class SessionInfo:
    id: str
    pid: int
    agent_type: str
    project_path: str
    model: str
    status: str
    started_at: datetime
    updated_at: datetime
    version: str = ""
    title: str = ""


@dataclass
class SessionMetrics:
    session: SessionInfo
    turns: list[Turn] = field(default_factory=list)
    total_usage: TokenUsage = field(default_factory=TokenUsage)
    total_cost: float = 0.0
    tool_stats: dict[str, ToolStat] = field(default_factory=dict)
    alerts: list[Alert] = field(default_factory=list)
    tokens_per_turn: list[int] = field(default_factory=list)

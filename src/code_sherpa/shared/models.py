"""공통 데이터 모델 정의."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# ============================================================
# 공통 Enum
# ============================================================


class Severity(Enum):
    """리뷰 코멘트 심각도."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ChangeType(Enum):
    """파일 변경 타입."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class OutputFormat(Enum):
    """출력 형식."""

    CONSOLE = "console"
    JSON = "json"
    MARKDOWN = "markdown"


# ============================================================
# Git 관련 모델
# ============================================================


@dataclass
class Commit:
    """커밋 정보."""

    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime


@dataclass
class DiffHunk:
    """Diff hunk (변경 블록)."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: str


@dataclass
class FileDiff:
    """파일별 diff 정보."""

    path: Path
    change_type: ChangeType
    old_path: Path | None = None  # renamed인 경우
    additions: int = 0
    deletions: int = 0
    hunks: list[DiffHunk] = field(default_factory=list)


@dataclass
class DiffStats:
    """Diff 통계."""

    files_changed: int
    total_additions: int
    total_deletions: int


@dataclass
class ParsedDiff:
    """파싱된 diff 전체."""

    files: list[FileDiff]
    stats: DiffStats
    raw: str = ""


# ============================================================
# 분석 관련 모델
# ============================================================


@dataclass
class FileStats:
    """파일 통계."""

    path: Path
    lines: int
    language: str
    size_bytes: int


@dataclass
class LanguageStats:
    """언어별 통계."""

    language: str
    files: int
    lines: int
    percentage: float


@dataclass
class RepoSummary:
    """저장소 요약."""

    path: Path
    name: str
    total_files: int
    total_lines: int
    languages: list[LanguageStats]
    recent_commits: list[Commit]
    summary: str = ""  # AI 생성 요약


@dataclass
class FileExplanation:
    """파일 설명."""

    path: Path
    language: str
    lines: int
    purpose: str
    key_elements: list[str]
    explanation: str


@dataclass
class StructureNode:
    """구조 분석 노드."""

    name: str
    path: Path
    node_type: str  # "file" | "directory" | "module"
    children: list["StructureNode"] = field(default_factory=list)


@dataclass
class Dependency:
    """의존성 정보."""

    source: Path
    target: Path
    dependency_type: str  # "import" | "include" | "require"


@dataclass
class StructureAnalysis:
    """구조 분석 결과."""

    root: StructureNode
    dependencies: list[Dependency]
    entry_points: list[Path]


@dataclass
class QualityIssue:
    """코드 품질 이슈."""

    path: Path
    line: int | None
    issue_type: str
    message: str
    severity: Severity


@dataclass
class QualityReport:
    """코드 품질 리포트."""

    complexity_score: float
    issues: list[QualityIssue]
    summary: str = ""


# ============================================================
# 리뷰 관련 모델
# ============================================================


@dataclass
class ReviewComment:
    """리뷰 코멘트."""

    agent: str
    file: str
    line: int | None
    severity: Severity
    category: str
    message: str
    suggestion: str | None = None


@dataclass
class AgentReview:
    """에이전트별 리뷰 결과."""

    agent_name: str
    comments: list[ReviewComment]
    summary: str = ""


@dataclass
class ReviewResult:
    """전체 리뷰 결과."""

    diff_summary: DiffStats
    agent_reviews: list[AgentReview]
    total_comments: int
    by_severity: dict[str, int] = field(default_factory=dict)
    summary: str = ""  # AI 종합 요약

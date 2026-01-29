"""출력 포매터 모듈."""

import json
from abc import ABC, abstractmethod
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from code_sherpa.shared.models import (
    AgentReview,
    FileExplanation,
    QualityReport,
    RepoSummary,
    ReviewResult,
    Severity,
)


class BaseFormatter(ABC):
    """출력 포매터 추상 클래스."""

    @abstractmethod
    def format(self, data: Any) -> str:
        """데이터를 포맷된 문자열로 변환.

        Args:
            data: 포맷할 데이터 객체

        Returns:
            포맷된 문자열
        """
        ...

    def _get_formatter_method(self, data: Any) -> str:
        """데이터 타입에 맞는 포맷 메서드 호출."""
        formatters = {
            RepoSummary: self._format_repo_summary,
            ReviewResult: self._format_review_result,
            FileExplanation: self._format_file_explanation,
            QualityReport: self._format_quality_report,
            AgentReview: self._format_agent_review,
        }

        formatter = formatters.get(type(data))
        if formatter:
            return formatter(data)
        return self._format_generic(data)

    @abstractmethod
    def _format_repo_summary(self, data: RepoSummary) -> str:
        """RepoSummary 포맷."""
        ...

    @abstractmethod
    def _format_review_result(self, data: ReviewResult) -> str:
        """ReviewResult 포맷."""
        ...

    @abstractmethod
    def _format_file_explanation(self, data: FileExplanation) -> str:
        """FileExplanation 포맷."""
        ...

    @abstractmethod
    def _format_quality_report(self, data: QualityReport) -> str:
        """QualityReport 포맷."""
        ...

    @abstractmethod
    def _format_agent_review(self, data: AgentReview) -> str:
        """AgentReview 포맷."""
        ...

    @abstractmethod
    def _format_generic(self, data: Any) -> str:
        """일반 데이터 포맷."""
        ...


class ConsoleFormatter(BaseFormatter):
    """Rich를 사용한 터미널 출력 포매터."""

    def __init__(self) -> None:
        self.console = Console(record=True)

    def format(self, data: Any) -> str:
        """데이터를 Rich 포맷으로 콘솔에 출력하고 문자열 반환."""
        return self._get_formatter_method(data)

    def _format_repo_summary(self, data: RepoSummary) -> str:
        """RepoSummary를 Rich 포맷으로 출력."""
        # 헤더 패널
        self.console.print(
            Panel(
                f"[bold blue]{data.name}[/bold blue]\n[dim]{data.path}[/dim]",
                title="Repository Summary",
                border_style="blue",
            )
        )

        # 통계 테이블
        stats_table = Table(title="Statistics", show_header=True)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        stats_table.add_row("Total Files", str(data.total_files))
        stats_table.add_row("Total Lines", f"{data.total_lines:,}")
        self.console.print(stats_table)

        # 언어 테이블
        if data.languages:
            lang_table = Table(title="Languages", show_header=True)
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Files", style="green")
            lang_table.add_column("Lines", style="green")
            lang_table.add_column("Percentage", style="yellow")

            for lang in data.languages:
                lang_table.add_row(
                    lang.language,
                    str(lang.files),
                    f"{lang.lines:,}",
                    f"{lang.percentage:.1f}%",
                )
            self.console.print(lang_table)

        # 최근 커밋
        if data.recent_commits:
            self.console.print("\n[bold]Recent Commits[/bold]")
            for commit in data.recent_commits[:5]:
                date_str = commit.date.strftime("%Y-%m-%d")
                self.console.print(
                    f"  [dim]{commit.short_hash}[/dim] {commit.message[:60]} "
                    f"[dim]({commit.author}, {date_str})[/dim]"
                )

        # AI 요약
        if data.summary:
            self.console.print(
                Panel(data.summary, title="AI Summary", border_style="green")
            )

        return self.console.export_text()

    def _format_review_result(self, data: ReviewResult) -> str:
        """ReviewResult를 Rich 포맷으로 출력."""
        # 헤더
        self.console.print(
            Panel("[bold]Code Review Results[/bold]", border_style="blue")
        )

        # Diff 통계
        stats_table = Table(title="Diff Statistics", show_header=True)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        stats_table.add_row("Files Changed", str(data.diff_summary.files_changed))
        stats_table.add_row(
            "Additions", f"[green]+{data.diff_summary.total_additions}[/green]"
        )
        stats_table.add_row(
            "Deletions", f"[red]-{data.diff_summary.total_deletions}[/red]"
        )
        self.console.print(stats_table)

        # 심각도별 통계
        if data.by_severity:
            severity_table = Table(title="Issues by Severity", show_header=True)
            severity_table.add_column("Severity", style="cyan")
            severity_table.add_column("Count", style="green")

            severity_colors = {
                "error": "red",
                "warning": "yellow",
                "info": "blue",
            }

            for severity, count in data.by_severity.items():
                color = severity_colors.get(severity, "white")
                label = f"[{color}]{severity.upper()}[/{color}]"
                severity_table.add_row(label, str(count))
            self.console.print(severity_table)

        # 에이전트별 리뷰
        for agent_review in data.agent_reviews:
            self._format_agent_review(agent_review)

        # 종합 요약
        if data.summary:
            self.console.print(
                Panel(data.summary, title="Overall Summary", border_style="green")
            )

        return self.console.export_text()

    def _format_agent_review(self, data: AgentReview) -> str:
        """AgentReview를 Rich 포맷으로 출력."""
        self.console.print(
            f"\n[bold magenta]{data.agent_name}[/bold magenta] "
            f"[dim]({len(data.comments)} comments)[/dim]"
        )

        severity_styles = {
            Severity.ERROR: "red",
            Severity.WARNING: "yellow",
            Severity.INFO: "blue",
        }

        for comment in data.comments:
            style = severity_styles.get(comment.severity, "white")
            location = f"{comment.file}"
            if comment.line:
                location += f":{comment.line}"

            severity_label = f"[{style}][{comment.severity.value}][/{style}]"
            self.console.print(f"  {severity_label} ", end="")
            self.console.print(f"[dim]{location}[/dim]")
            self.console.print(f"    {comment.message}")
            if comment.suggestion:
                suggestion_text = f"[green]Suggestion:[/green] {comment.suggestion}"
                self.console.print(f"    {suggestion_text}")

        if data.summary:
            self.console.print(f"  [dim]Summary: {data.summary}[/dim]")

        return self.console.export_text()

    def _format_file_explanation(self, data: FileExplanation) -> str:
        """FileExplanation을 Rich 포맷으로 출력."""
        self.console.print(
            Panel(
                f"[bold]{data.path.name}[/bold]\n"
                f"[dim]{data.path}[/dim]\n"
                f"Language: [cyan]{data.language}[/cyan] | "
                f"Lines: [green]{data.lines}[/green]",
                title="File Information",
                border_style="blue",
            )
        )

        self.console.print(f"\n[bold]Purpose[/bold]\n{data.purpose}")

        if data.key_elements:
            self.console.print("\n[bold]Key Elements[/bold]")
            for element in data.key_elements:
                self.console.print(f"  - {element}")

        self.console.print(
            Panel(data.explanation, title="Explanation", border_style="green")
        )

        return self.console.export_text()

    def _format_quality_report(self, data: QualityReport) -> str:
        """QualityReport를 Rich 포맷으로 출력."""
        # 복잡도 점수
        if data.complexity_score < 30:
            score_color = "green"
        elif data.complexity_score < 60:
            score_color = "yellow"
        else:
            score_color = "red"
        score_text = f"[{score_color}]{data.complexity_score:.1f}[/{score_color}]"
        self.console.print(
            Panel(
                f"Complexity Score: {score_text}",
                title="Quality Report",
                border_style="blue",
            )
        )

        # 이슈 테이블
        if data.issues:
            issues_table = Table(title="Issues", show_header=True)
            issues_table.add_column("File", style="cyan")
            issues_table.add_column("Line", style="dim")
            issues_table.add_column("Type", style="magenta")
            issues_table.add_column("Severity")
            issues_table.add_column("Message")

            severity_styles = {
                Severity.ERROR: "red",
                Severity.WARNING: "yellow",
                Severity.INFO: "blue",
            }

            for issue in data.issues:
                style = severity_styles.get(issue.severity, "white")
                issues_table.add_row(
                    str(issue.path),
                    str(issue.line) if issue.line else "-",
                    issue.issue_type,
                    Text(issue.severity.value, style=style),
                    issue.message,
                )
            self.console.print(issues_table)

        if data.summary:
            self.console.print(
                Panel(data.summary, title="Summary", border_style="green")
            )

        return self.console.export_text()

    def _format_generic(self, data: Any) -> str:
        """일반 데이터를 Rich 포맷으로 출력."""
        if hasattr(data, "__dict__"):
            self.console.print(Panel(str(data.__dict__), title=type(data).__name__))
        else:
            self.console.print(str(data))
        return self.console.export_text()


class JSONFormatter(BaseFormatter):
    """JSON 출력 포매터 (파이프라인 친화적)."""

    def __init__(self, indent: int = 2) -> None:
        self.indent = indent

    def format(self, data: Any) -> str:
        """데이터를 JSON 문자열로 변환."""
        return self._get_formatter_method(data)

    def _to_serializable(self, obj: Any) -> Any:
        """객체를 JSON 직렬화 가능한 형태로 변환."""
        from dataclasses import asdict, is_dataclass
        from datetime import datetime
        from enum import Enum
        from pathlib import Path

        if is_dataclass(obj) and not isinstance(obj, type):
            return {k: self._to_serializable(v) for k, v in asdict(obj).items()}
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, list):
            return [self._to_serializable(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._to_serializable(v) for k, v in obj.items()}
        return obj

    def _to_json(self, data: Any) -> str:
        """객체를 JSON 문자열로 변환하는 헬퍼."""
        return json.dumps(
            self._to_serializable(data),
            indent=self.indent,
            ensure_ascii=False,
        )

    def _format_repo_summary(self, data: RepoSummary) -> str:
        """RepoSummary를 JSON으로 변환."""
        return self._to_json(data)

    def _format_review_result(self, data: ReviewResult) -> str:
        """ReviewResult를 JSON으로 변환."""
        return self._to_json(data)

    def _format_file_explanation(self, data: FileExplanation) -> str:
        """FileExplanation을 JSON으로 변환."""
        return self._to_json(data)

    def _format_quality_report(self, data: QualityReport) -> str:
        """QualityReport를 JSON으로 변환."""
        return self._to_json(data)

    def _format_agent_review(self, data: AgentReview) -> str:
        """AgentReview를 JSON으로 변환."""
        return self._to_json(data)

    def _format_generic(self, data: Any) -> str:
        """일반 데이터를 JSON으로 변환."""
        return self._to_json(data)


class MarkdownFormatter(BaseFormatter):
    """Markdown 출력 포매터."""

    def format(self, data: Any) -> str:
        """데이터를 Markdown 문자열로 변환."""
        return self._get_formatter_method(data)

    def _format_repo_summary(self, data: RepoSummary) -> str:
        """RepoSummary를 Markdown으로 변환."""
        lines = [
            f"# {data.name}",
            "",
            f"> {data.path}",
            "",
            "## Statistics",
            "",
            f"- **Total Files**: {data.total_files}",
            f"- **Total Lines**: {data.total_lines:,}",
            "",
        ]

        if data.languages:
            lines.extend(
                [
                    "## Languages",
                    "",
                    "| Language | Files | Lines | Percentage |",
                    "|----------|-------|-------|------------|",
                ]
            )
            for lang in data.languages:
                pct = f"{lang.percentage:.1f}%"
                lines.append(
                    f"| {lang.language} | {lang.files} | {lang.lines:,} | {pct} |"
                )
            lines.append("")

        if data.recent_commits:
            lines.extend(
                [
                    "## Recent Commits",
                    "",
                ]
            )
            for commit in data.recent_commits[:5]:
                date_str = commit.date.strftime("%Y-%m-%d")
                author_date = f"*{commit.author}, {date_str}*"
                lines.append(
                    f"- `{commit.short_hash}` {commit.message} ({author_date})"
                )
            lines.append("")

        if data.summary:
            lines.extend(
                [
                    "## Summary",
                    "",
                    data.summary,
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_review_result(self, data: ReviewResult) -> str:
        """ReviewResult를 Markdown으로 변환."""
        lines = [
            "# Code Review Results",
            "",
            "## Diff Statistics",
            "",
            f"- **Files Changed**: {data.diff_summary.files_changed}",
            f"- **Additions**: +{data.diff_summary.total_additions}",
            f"- **Deletions**: -{data.diff_summary.total_deletions}",
            "",
        ]

        if data.by_severity:
            lines.extend(
                [
                    "## Issues by Severity",
                    "",
                ]
            )
            for severity, count in data.by_severity.items():
                emoji = {"error": "X", "warning": "!", "info": "i"}.get(severity, "-")
                lines.append(f"- **{severity.upper()}** [{emoji}]: {count}")
            lines.append("")

        for agent_review in data.agent_reviews:
            lines.append(self._format_agent_review(agent_review))

        if data.summary:
            lines.extend(
                [
                    "## Overall Summary",
                    "",
                    data.summary,
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_agent_review(self, data: AgentReview) -> str:
        """AgentReview를 Markdown으로 변환."""
        lines = [
            f"### {data.agent_name}",
            "",
            f"*{len(data.comments)} comments*",
            "",
        ]

        severity_markers = {
            Severity.ERROR: "[ERROR]",
            Severity.WARNING: "[WARNING]",
            Severity.INFO: "[INFO]",
        }

        for comment in data.comments:
            marker = severity_markers.get(comment.severity, "[-]")
            location = f"`{comment.file}`"
            if comment.line:
                location += f" (line {comment.line})"

            lines.append(f"- **{marker}** {location}")
            lines.append(f"  - {comment.message}")
            if comment.suggestion:
                lines.append(f"  - *Suggestion*: {comment.suggestion}")
            lines.append("")

        if data.summary:
            lines.extend(
                [
                    f"**Summary**: {data.summary}",
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_file_explanation(self, data: FileExplanation) -> str:
        """FileExplanation을 Markdown으로 변환."""
        lines = [
            f"# {data.path.name}",
            "",
            f"> {data.path}",
            "",
            f"- **Language**: {data.language}",
            f"- **Lines**: {data.lines}",
            "",
            "## Purpose",
            "",
            data.purpose,
            "",
        ]

        if data.key_elements:
            lines.extend(
                [
                    "## Key Elements",
                    "",
                ]
            )
            for element in data.key_elements:
                lines.append(f"- {element}")
            lines.append("")

        lines.extend(
            [
                "## Explanation",
                "",
                data.explanation,
                "",
            ]
        )

        return "\n".join(lines)

    def _format_quality_report(self, data: QualityReport) -> str:
        """QualityReport를 Markdown으로 변환."""
        lines = [
            "# Quality Report",
            "",
            f"**Complexity Score**: {data.complexity_score:.1f}",
            "",
        ]

        if data.issues:
            lines.extend(
                [
                    "## Issues",
                    "",
                    "| File | Line | Type | Severity | Message |",
                    "|------|------|------|----------|---------|",
                ]
            )
            for issue in data.issues:
                line_str = str(issue.line) if issue.line else "-"
                lines.append(
                    f"| {issue.path} | {line_str} | {issue.issue_type} | "
                    f"{issue.severity.value} | {issue.message} |"
                )
            lines.append("")

        if data.summary:
            lines.extend(
                [
                    "## Summary",
                    "",
                    data.summary,
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_generic(self, data: Any) -> str:
        """일반 데이터를 Markdown으로 변환."""
        if hasattr(data, "__dict__"):
            lines = [f"# {type(data).__name__}", ""]
            for key, value in data.__dict__.items():
                lines.append(f"- **{key}**: {value}")
            return "\n".join(lines)
        return f"```\n{data}\n```"


def get_formatter(format_type: str = "console") -> BaseFormatter:
    """포매터 팩토리 함수.

    Args:
        format_type: 출력 형식 ("console", "json", "markdown")

    Returns:
        해당 형식의 포매터 인스턴스

    Raises:
        ValueError: 지원하지 않는 형식인 경우
    """
    formatters = {
        "console": ConsoleFormatter,
        "json": JSONFormatter,
        "markdown": MarkdownFormatter,
    }

    formatter_class = formatters.get(format_type.lower())
    if formatter_class is None:
        supported = ", ".join(formatters.keys())
        msg = f"Unsupported format type: {format_type}. Supported: {supported}"
        raise ValueError(msg)

    return formatter_class()

"""BaseAgent 테스트."""

import json
from unittest.mock import MagicMock, patch

import pytest

from code_sherpa.review.agents.base import BaseAgent
from code_sherpa.shared.models import (
    AgentReview,
    ChangeType,
    DiffHunk,
    DiffStats,
    FileDiff,
    ParsedDiff,
    Severity,
)


class ConcreteAgent(BaseAgent):
    """테스트용 구체 에이전트 구현."""

    name = "test_agent"
    description = "테스트 에이전트"
    prompt_name = "review/architect"

    async def review(
        self, diff: ParsedDiff, context: dict | None = None
    ) -> AgentReview:
        """테스트용 리뷰 구현."""
        return AgentReview(
            agent_name=self.name,
            comments=[],
            summary="테스트 요약",
        )


@pytest.fixture
def mock_llm():
    """Mock LLM fixture."""
    return MagicMock()


@pytest.fixture
def sample_diff() -> ParsedDiff:
    """샘플 ParsedDiff fixture."""
    return ParsedDiff(
        files=[
            FileDiff(
                path="test.py",
                change_type=ChangeType.MODIFIED,
                additions=5,
                deletions=2,
                hunks=[
                    DiffHunk(
                        old_start=1,
                        old_count=10,
                        new_start=1,
                        new_count=13,
                        content="+def new_function():\n+    pass",
                    )
                ],
            )
        ],
        stats=DiffStats(files_changed=1, total_additions=5, total_deletions=2),
        raw="--- a/test.py\n+++ b/test.py\n+def new_function():\n+    pass",
    )


class TestBaseAgent:
    """BaseAgent 테스트."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """BaseAgent는 직접 인스턴스화할 수 없음."""
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore

    def test_concrete_agent_can_be_instantiated(self, mock_llm) -> None:
        """구체 클래스는 인스턴스화 가능."""
        with patch("code_sherpa.review.agents.base.get_llm", return_value=mock_llm):
            agent = ConcreteAgent()
            assert agent.name == "test_agent"
            assert agent.description == "테스트 에이전트"

    def test_agent_with_custom_llm(self, mock_llm) -> None:
        """커스텀 LLM 주입."""
        agent = ConcreteAgent(llm=mock_llm)
        assert agent.llm is mock_llm

    def test_agent_with_default_llm(self) -> None:
        """기본 LLM 사용."""
        mock_llm = MagicMock()
        with patch("code_sherpa.review.agents.base.get_llm", return_value=mock_llm):
            agent = ConcreteAgent()
            assert agent.llm is mock_llm


class TestParseResponse:
    """응답 파싱 테스트."""

    def test_parse_json_array_response(self, mock_llm) -> None:
        """JSON 배열 응답 파싱."""
        agent = ConcreteAgent(llm=mock_llm)

        response = json.dumps(
            [
                {
                    "file": "test.py",
                    "line": 10,
                    "severity": "ERROR",
                    "category": "security",
                    "message": "SQL injection risk",
                    "suggestion": "Use parameterized queries",
                }
            ]
        )

        comments = agent._parse_llm_response(response)

        assert len(comments) == 1
        assert comments[0].file == "test.py"
        assert comments[0].line == 10
        assert comments[0].severity == Severity.ERROR
        assert comments[0].category == "security"
        assert comments[0].message == "SQL injection risk"
        assert comments[0].suggestion == "Use parameterized queries"

    def test_parse_json_with_comments_key(self, mock_llm) -> None:
        """comments 키가 있는 JSON 응답 파싱."""
        agent = ConcreteAgent(llm=mock_llm)

        response = json.dumps(
            {
                "comments": [
                    {
                        "file": "main.py",
                        "line": 5,
                        "severity": "WARNING",
                        "category": "performance",
                        "message": "N+1 query detected",
                    }
                ],
                "summary": "성능 이슈 발견",
            }
        )

        comments = agent._parse_llm_response(response)

        assert len(comments) == 1
        assert comments[0].file == "main.py"
        assert comments[0].severity == Severity.WARNING

    def test_parse_json_in_code_block(self, mock_llm) -> None:
        """코드 블록 내 JSON 파싱."""
        agent = ConcreteAgent(llm=mock_llm)

        response = """Here is my analysis:

```json
[
    {
        "file": "app.py",
        "line": 20,
        "severity": "INFO",
        "category": "readability",
        "message": "Consider using a more descriptive variable name"
    }
]
```

This concludes my review."""

        comments = agent._parse_llm_response(response)

        assert len(comments) == 1
        assert comments[0].file == "app.py"
        assert comments[0].severity == Severity.INFO

    def test_parse_invalid_json_falls_back_to_text(self, mock_llm) -> None:
        """잘못된 JSON은 텍스트 파싱으로 폴백."""
        agent = ConcreteAgent(llm=mock_llm)

        response = "This is a plain text review without any structured data."

        comments = agent._parse_llm_response(response)

        assert len(comments) == 1
        assert comments[0].file == "general"
        assert comments[0].severity == Severity.INFO
        assert "plain text review" in comments[0].message

    def test_parse_empty_response(self, mock_llm) -> None:
        """빈 응답 처리."""
        agent = ConcreteAgent(llm=mock_llm)

        comments = agent._parse_llm_response("")

        assert len(comments) == 0

    def test_parse_missing_fields_uses_defaults(self, mock_llm) -> None:
        """필드 누락 시 기본값 사용."""
        agent = ConcreteAgent(llm=mock_llm)

        response = json.dumps(
            [
                {
                    "message": "Some issue found",
                }
            ]
        )

        comments = agent._parse_llm_response(response)

        assert len(comments) == 1
        assert comments[0].file == "unknown"
        assert comments[0].line is None
        assert comments[0].severity == Severity.INFO
        assert comments[0].category == "general"


class TestBuildPrompt:
    """프롬프트 빌드 테스트."""

    def test_build_prompt_with_raw_diff(self, mock_llm, sample_diff) -> None:
        """raw diff가 있으면 그것을 사용."""
        agent = ConcreteAgent(llm=mock_llm)

        with patch("code_sherpa.review.agents.base.load_prompt") as mock_load:
            mock_load.return_value = "formatted prompt"
            agent._build_prompt(sample_diff)

            mock_load.assert_called_once()
            call_kwargs = mock_load.call_args[1]
            assert sample_diff.raw in call_kwargs["diff"]

    def test_build_prompt_with_context(self, mock_llm, sample_diff) -> None:
        """컨텍스트가 있으면 포함."""
        agent = ConcreteAgent(llm=mock_llm)

        context = {"files": {"test.py": "def existing(): pass"}}

        with patch("code_sherpa.review.agents.base.load_prompt") as mock_load:
            mock_load.return_value = "formatted prompt"
            agent._build_prompt(sample_diff, context)

            call_kwargs = mock_load.call_args[1]
            assert "test.py" in call_kwargs["file_context"]


class TestExtractSummary:
    """요약 추출 테스트."""

    def test_extract_summary_from_json(self, mock_llm) -> None:
        """JSON에서 summary 추출."""
        agent = ConcreteAgent(llm=mock_llm)

        response = json.dumps({"comments": [], "summary": "모든 코드가 깔끔합니다."})

        summary = agent._extract_summary(response)

        assert summary == "모든 코드가 깔끔합니다."

    def test_extract_summary_from_text(self, mock_llm) -> None:
        """텍스트에서 Summary 섹션 추출."""
        agent = ConcreteAgent(llm=mock_llm)

        response = """## Analysis

Some detailed analysis here.

## Summary
The code looks good overall with minor improvements needed.

## Recommendations
..."""

        summary = agent._extract_summary(response)

        assert "code looks good" in summary

    def test_extract_summary_returns_empty_when_not_found(self, mock_llm) -> None:
        """요약이 없으면 빈 문자열."""
        agent = ConcreteAgent(llm=mock_llm)

        response = "Just some random text without a summary section."

        summary = agent._extract_summary(response)

        assert summary == ""

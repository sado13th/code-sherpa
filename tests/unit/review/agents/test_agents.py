"""개별 에이전트 테스트."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_sherpa.review.agents import (
    AGENT_REGISTRY,
    ArchitectAgent,
    JuniorAgent,
    PerformanceAgent,
    SecurityAgent,
    get_agent,
    get_available_agents,
)
from code_sherpa.shared.models import (
    ChangeType,
    DiffHunk,
    DiffStats,
    FileDiff,
    ParsedDiff,
)


@pytest.fixture
def mock_llm():
    """Mock LLM fixture."""
    llm = MagicMock()
    llm.complete.return_value = json.dumps(
        {
            "comments": [
                {
                    "file": "test.py",
                    "line": 10,
                    "severity": "WARNING",
                    "category": "test",
                    "message": "Test issue",
                    "suggestion": "Fix it",
                }
            ],
            "summary": "Test summary",
        }
    )
    return llm


@pytest.fixture
def sample_diff() -> ParsedDiff:
    """샘플 ParsedDiff fixture."""
    return ParsedDiff(
        files=[
            FileDiff(
                path=Path("test.py"),
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


class TestArchitectAgent:
    """ArchitectAgent 테스트."""

    def test_agent_attributes(self, mock_llm) -> None:
        """에이전트 속성 확인."""
        agent = ArchitectAgent(llm=mock_llm)
        assert agent.name == "architect"
        assert "설계 패턴" in agent.description
        assert agent.prompt_name == "review/architect"

    @pytest.mark.asyncio
    async def test_review_returns_agent_review(self, mock_llm, sample_diff) -> None:
        """review()가 AgentReview 반환."""
        agent = ArchitectAgent(llm=mock_llm)

        result = await agent.review(sample_diff)

        assert result.agent_name == "architect"
        assert len(result.comments) == 1
        assert result.summary == "Test summary"

    @pytest.mark.asyncio
    async def test_review_handles_llm_error(self, sample_diff) -> None:
        """LLM 호출 실패 처리."""
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = Exception("API Error")

        agent = ArchitectAgent(llm=mock_llm)
        result = await agent.review(sample_diff)

        assert result.agent_name == "architect"
        assert len(result.comments) == 0
        assert "실패" in result.summary

    @pytest.mark.asyncio
    async def test_review_with_context(self, mock_llm, sample_diff) -> None:
        """컨텍스트와 함께 리뷰."""
        agent = ArchitectAgent(llm=mock_llm)

        context = {"files": {"test.py": "existing code"}}
        result = await agent.review(sample_diff, context)

        assert result.agent_name == "architect"
        mock_llm.complete.assert_called_once()


class TestSecurityAgent:
    """SecurityAgent 테스트."""

    def test_agent_attributes(self, mock_llm) -> None:
        """에이전트 속성 확인."""
        agent = SecurityAgent(llm=mock_llm)
        assert agent.name == "security"
        assert "보안" in agent.description
        assert agent.prompt_name == "review/security"

    @pytest.mark.asyncio
    async def test_review_returns_agent_review(self, mock_llm, sample_diff) -> None:
        """review()가 AgentReview 반환."""
        agent = SecurityAgent(llm=mock_llm)

        result = await agent.review(sample_diff)

        assert result.agent_name == "security"
        assert len(result.comments) == 1

    @pytest.mark.asyncio
    async def test_default_summary_for_no_comments(self, sample_diff) -> None:
        """코멘트 없을 때 기본 요약."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = json.dumps({"comments": []})

        agent = SecurityAgent(llm=mock_llm)
        result = await agent.review(sample_diff)

        assert "취약점이 발견되지 않았습니다" in result.summary


class TestPerformanceAgent:
    """PerformanceAgent 테스트."""

    def test_agent_attributes(self, mock_llm) -> None:
        """에이전트 속성 확인."""
        agent = PerformanceAgent(llm=mock_llm)
        assert agent.name == "performance"
        assert "알고리즘" in agent.description
        assert agent.prompt_name == "review/performance"

    @pytest.mark.asyncio
    async def test_review_returns_agent_review(self, mock_llm, sample_diff) -> None:
        """review()가 AgentReview 반환."""
        agent = PerformanceAgent(llm=mock_llm)

        result = await agent.review(sample_diff)

        assert result.agent_name == "performance"
        assert len(result.comments) == 1

    @pytest.mark.asyncio
    async def test_default_summary_with_issues(self, sample_diff) -> None:
        """이슈가 있을 때 기본 요약."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = json.dumps(
            {
                "comments": [
                    {
                        "file": "test.py",
                        "severity": "ERROR",
                        "category": "performance",
                        "message": "O(n^2) complexity",
                    },
                    {
                        "file": "test.py",
                        "severity": "WARNING",
                        "category": "performance",
                        "message": "Consider caching",
                    },
                ]
            }
        )

        agent = PerformanceAgent(llm=mock_llm)
        result = await agent.review(sample_diff)

        assert "심각한 성능 이슈 1건" in result.summary
        assert "성능 주의 1건" in result.summary


class TestJuniorAgent:
    """JuniorAgent 테스트."""

    def test_agent_attributes(self, mock_llm) -> None:
        """에이전트 속성 확인."""
        agent = JuniorAgent(llm=mock_llm)
        assert agent.name == "junior"
        assert "가독성" in agent.description
        assert agent.prompt_name == "review/junior"

    @pytest.mark.asyncio
    async def test_review_returns_agent_review(self, mock_llm, sample_diff) -> None:
        """review()가 AgentReview 반환."""
        agent = JuniorAgent(llm=mock_llm)

        result = await agent.review(sample_diff)

        assert result.agent_name == "junior"
        assert len(result.comments) == 1

    @pytest.mark.asyncio
    async def test_default_summary_for_no_comments(self, sample_diff) -> None:
        """코멘트 없을 때 기본 요약."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = json.dumps({"comments": []})

        agent = JuniorAgent(llm=mock_llm)
        result = await agent.review(sample_diff)

        assert "특별한 이슈가 발견되지 않았습니다" in result.summary


class TestAgentRegistry:
    """에이전트 레지스트리 테스트."""

    def test_registry_contains_all_agents(self) -> None:
        """레지스트리에 모든 에이전트가 등록됨."""
        expected_agents = {"architect", "security", "performance", "junior"}
        assert set(AGENT_REGISTRY.keys()) == expected_agents

    def test_get_available_agents_returns_sorted_list(self) -> None:
        """get_available_agents()가 정렬된 목록 반환."""
        agents = get_available_agents()
        assert agents == sorted(agents)
        assert "architect" in agents
        assert "security" in agents
        assert "performance" in agents
        assert "junior" in agents


class TestGetAgent:
    """get_agent 팩토리 함수 테스트."""

    def test_get_architect_agent(self, mock_llm) -> None:
        """ArchitectAgent 반환."""
        agent = get_agent("architect", llm=mock_llm)
        assert isinstance(agent, ArchitectAgent)

    def test_get_security_agent(self, mock_llm) -> None:
        """SecurityAgent 반환."""
        agent = get_agent("security", llm=mock_llm)
        assert isinstance(agent, SecurityAgent)

    def test_get_performance_agent(self, mock_llm) -> None:
        """PerformanceAgent 반환."""
        agent = get_agent("performance", llm=mock_llm)
        assert isinstance(agent, PerformanceAgent)

    def test_get_junior_agent(self, mock_llm) -> None:
        """JuniorAgent 반환."""
        agent = get_agent("junior", llm=mock_llm)
        assert isinstance(agent, JuniorAgent)

    def test_case_insensitive_name(self, mock_llm) -> None:
        """에이전트 이름은 대소문자 구분 없음."""
        agent1 = get_agent("Architect", llm=mock_llm)
        agent2 = get_agent("ARCHITECT", llm=mock_llm)
        agent3 = get_agent("architect", llm=mock_llm)

        assert isinstance(agent1, ArchitectAgent)
        assert isinstance(agent2, ArchitectAgent)
        assert isinstance(agent3, ArchitectAgent)

    def test_invalid_agent_raises_error(self) -> None:
        """잘못된 에이전트 이름은 에러."""
        with pytest.raises(ValueError) as exc_info:
            get_agent("invalid-agent")

        assert "지원하지 않는 에이전트" in str(exc_info.value)
        assert "architect" in str(exc_info.value)

    def test_get_agent_with_default_llm(self) -> None:
        """기본 LLM 사용."""
        mock_llm = MagicMock()
        with patch("code_sherpa.review.agents.base.get_llm", return_value=mock_llm):
            agent = get_agent("architect")
            assert agent.llm is mock_llm

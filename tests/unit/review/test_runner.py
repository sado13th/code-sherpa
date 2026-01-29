"""Review Runner 및 Summarizer 테스트."""

import pytest

from code_sherpa.shared.models import (
    AgentReview,
    DiffHunk,
    DiffStats,
    FileDiff,
    ChangeType,
    ParsedDiff,
    ReviewComment,
    ReviewResult,
    Severity,
)
from code_sherpa.review.runner import (
    ReviewRunner,
    ReviewSummarizer,
    run_review,
    run_review_sync,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_diff():
    """샘플 ParsedDiff."""
    return ParsedDiff(
        files=[
            FileDiff(
                path="src/main.py",
                change_type=ChangeType.MODIFIED,
                additions=5,
                deletions=2,
                hunks=[
                    DiffHunk(
                        old_start=1,
                        old_count=5,
                        new_start=1,
                        new_count=8,
                        content="-old\n+new",
                    )
                ],
            )
        ],
        stats=DiffStats(
            files_changed=1,
            total_additions=5,
            total_deletions=2,
        ),
        raw="diff --git a/src/main.py b/src/main.py\n-old\n+new",
    )


@pytest.fixture
def sample_agent_review():
    """샘플 AgentReview."""
    return AgentReview(
        agent_name="architect",
        comments=[
            ReviewComment(
                agent="architect",
                file="src/main.py",
                line=10,
                severity=Severity.WARNING,
                category="design",
                message="Consider using dependency injection.",
                suggestion="Use constructor injection.",
            ),
            ReviewComment(
                agent="architect",
                file="src/main.py",
                line=20,
                severity=Severity.INFO,
                category="naming",
                message="Method name could be clearer.",
                suggestion=None,
            ),
        ],
        summary="Good structure overall.",
    )


@pytest.fixture
def sample_review_result(sample_agent_review):
    """샘플 ReviewResult."""
    return ReviewResult(
        diff_summary=DiffStats(
            files_changed=2,
            total_additions=10,
            total_deletions=5,
        ),
        agent_reviews=[
            sample_agent_review,
            AgentReview(
                agent_name="security",
                comments=[
                    ReviewComment(
                        agent="security",
                        file="src/auth.py",
                        line=15,
                        severity=Severity.ERROR,
                        category="auth",
                        message="Password stored in plaintext.",
                        suggestion="Use bcrypt for hashing.",
                    ),
                ],
                summary="Security issue found.",
            ),
        ],
        total_comments=3,
        by_severity={"error": 1, "warning": 1, "info": 1},
        summary="",
    )


@pytest.fixture
def mock_llm(mocker):
    """Mock LLM."""
    mock = mocker.MagicMock()
    mock.chat.return_value = "Test summary"
    return mock


@pytest.fixture
def mock_agent(mocker, sample_agent_review):
    """Mock agent."""
    mock = mocker.AsyncMock()
    mock.name = "architect"
    mock.review.return_value = sample_agent_review
    return mock


# ============================================================
# ReviewRunner Tests
# ============================================================


class TestReviewRunnerInit:
    """ReviewRunner 초기화 테스트."""

    def test_default_agents(self):
        """기본 에이전트 목록."""
        runner = ReviewRunner()
        assert runner.agent_names == ["architect", "security"]

    def test_custom_agents(self):
        """커스텀 에이전트 목록."""
        runner = ReviewRunner(agents=["junior", "performance"])
        assert runner.agent_names == ["junior", "performance"]

    def test_default_parallel(self):
        """기본 병렬 실행 설정."""
        runner = ReviewRunner()
        assert runner.parallel is True

    def test_custom_parallel(self):
        """커스텀 병렬 설정."""
        runner = ReviewRunner(parallel=False)
        assert runner.parallel is False


class TestReviewRunnerAgents:
    """ReviewRunner 에이전트 프로퍼티 테스트."""

    def test_agents_lazy_init(self, mocker):
        """에이전트 lazy initialization."""
        mocker.patch(
            "code_sherpa.review.runner.get_agent",
            return_value=mocker.MagicMock(),
        )
        runner = ReviewRunner(agents=["architect"])

        # 접근 전에는 None
        assert runner._agents is None

        # 접근 후 초기화
        agents = runner.agents
        assert runner._agents is not None
        assert len(agents) == 1

    def test_agents_cached(self, mocker):
        """에이전트 캐싱."""
        mock_get_agent = mocker.patch(
            "code_sherpa.review.runner.get_agent",
            return_value=mocker.MagicMock(),
        )
        runner = ReviewRunner(agents=["architect"])

        # 두 번 접근해도 한 번만 생성
        _ = runner.agents
        _ = runner.agents
        assert mock_get_agent.call_count == 1


class TestReviewRunnerEmptyResult:
    """빈 결과 테스트."""

    def test_empty_result(self):
        """빈 결과 반환."""
        runner = ReviewRunner()
        result = runner._empty_result()

        assert result.diff_summary.files_changed == 0
        assert result.total_comments == 0
        assert result.summary == "리뷰할 변경사항이 없습니다."


class TestReviewRunnerAggregateResults:
    """결과 집계 테스트."""

    def test_aggregate_total_comments(self, sample_diff, sample_agent_review):
        """총 코멘트 수 집계."""
        runner = ReviewRunner()
        reviews = [sample_agent_review]

        result = runner._aggregate_results(sample_diff, reviews)

        assert result.total_comments == 2

    def test_aggregate_by_severity(self, sample_diff, sample_agent_review):
        """심각도별 집계."""
        runner = ReviewRunner()
        reviews = [sample_agent_review]

        result = runner._aggregate_results(sample_diff, reviews)

        assert result.by_severity["warning"] == 1
        assert result.by_severity["info"] == 1

    def test_aggregate_empty_reviews(self, sample_diff):
        """빈 리뷰 집계."""
        runner = ReviewRunner()
        result = runner._aggregate_results(sample_diff, [])

        assert result.total_comments == 0
        assert result.by_severity == {}


class TestReviewRunnerParallel:
    """병렬 실행 테스트."""

    @pytest.mark.asyncio
    async def test_run_parallel_success(self, mocker, sample_diff, sample_agent_review):
        """병렬 실행 성공."""
        mock_agent = mocker.AsyncMock()
        mock_agent.name = "architect"
        mock_agent.review.return_value = sample_agent_review

        runner = ReviewRunner()
        runner._agents = [mock_agent]

        reviews = await runner._run_parallel(sample_diff, None)

        assert len(reviews) == 1
        assert reviews[0].agent_name == "architect"

    @pytest.mark.asyncio
    async def test_run_parallel_with_error(self, mocker, sample_diff):
        """병렬 실행 중 에러 처리."""
        mock_agent = mocker.AsyncMock()
        mock_agent.name = "architect"
        mock_agent.review.side_effect = Exception("Test error")

        runner = ReviewRunner()
        runner._agents = [mock_agent]

        reviews = await runner._run_parallel(sample_diff, None)

        assert len(reviews) == 1
        assert "오류 발생" in reviews[0].summary


class TestReviewRunnerSequential:
    """순차 실행 테스트."""

    @pytest.mark.asyncio
    async def test_run_sequential_success(self, mocker, sample_diff, sample_agent_review):
        """순차 실행 성공."""
        mock_agent = mocker.AsyncMock()
        mock_agent.name = "architect"
        mock_agent.review.return_value = sample_agent_review

        runner = ReviewRunner()
        runner._agents = [mock_agent]

        reviews = await runner._run_sequential(sample_diff, None)

        assert len(reviews) == 1
        assert reviews[0].agent_name == "architect"

    @pytest.mark.asyncio
    async def test_run_sequential_with_error(self, mocker, sample_diff):
        """순차 실행 중 에러 처리."""
        mock_agent = mocker.AsyncMock()
        mock_agent.name = "architect"
        mock_agent.review.side_effect = Exception("Test error")

        runner = ReviewRunner()
        runner._agents = [mock_agent]

        reviews = await runner._run_sequential(sample_diff, None)

        assert len(reviews) == 1
        assert "오류 발생" in reviews[0].summary


class TestReviewRunnerListAgents:
    """사용 가능한 에이전트 목록 테스트."""

    def test_list_available_agents(self):
        """사용 가능한 에이전트 목록."""
        agents = ReviewRunner.list_available_agents()

        assert "architect" in agents
        assert "security" in agents
        assert "performance" in agents
        assert "junior" in agents


# ============================================================
# ReviewSummarizer Tests
# ============================================================


class TestReviewSummarizerInit:
    """ReviewSummarizer 초기화 테스트."""

    def test_lazy_llm_init(self, mocker):
        """LLM lazy initialization."""
        mocker.patch("code_sherpa.review.runner.get_llm")
        summarizer = ReviewSummarizer()

        assert summarizer._llm is None


class TestReviewSummarizerFormatAgentReviews:
    """에이전트 리뷰 포맷팅 테스트."""

    def test_format_with_comments(self, sample_agent_review):
        """코멘트가 있는 리뷰 포맷."""
        summarizer = ReviewSummarizer()
        text = summarizer._format_agent_reviews([sample_agent_review])

        assert "### architect" in text
        assert "[WARNING]" in text
        assert "[INFO]" in text
        assert "src/main.py" in text
        assert "dependency injection" in text

    def test_format_empty_comments(self):
        """빈 코멘트 포맷."""
        summarizer = ReviewSummarizer()
        empty_review = AgentReview(
            agent_name="architect",
            comments=[],
            summary="",
        )
        text = summarizer._format_agent_reviews([empty_review])

        assert "### architect" in text
        assert "*No issues found.*" in text


class TestReviewSummarizerFallback:
    """폴백 요약 테스트."""

    def test_fallback_with_errors(self, sample_review_result):
        """에러가 있는 경우 폴백."""
        summarizer = ReviewSummarizer()
        summary = summarizer._generate_fallback_summary(sample_review_result)

        assert "3개의 코멘트" in summary
        assert "ERROR: 1개" in summary
        assert "병합 전 ERROR 이슈를 해결" in summary

    def test_fallback_with_warnings_only(self):
        """경고만 있는 경우 폴백."""
        summarizer = ReviewSummarizer()
        result = ReviewResult(
            diff_summary=DiffStats(1, 5, 2),
            agent_reviews=[],
            total_comments=2,
            by_severity={"warning": 2},
            summary="",
        )
        summary = summarizer._generate_fallback_summary(result)

        assert "WARNING: 2개" in summary
        assert "검토하는 것이 좋습니다" in summary

    def test_fallback_with_info_only(self):
        """정보만 있는 경우 폴백."""
        summarizer = ReviewSummarizer()
        result = ReviewResult(
            diff_summary=DiffStats(1, 5, 2),
            agent_reviews=[],
            total_comments=1,
            by_severity={"info": 1},
            summary="",
        )
        summary = summarizer._generate_fallback_summary(result)

        assert "INFO: 1개" in summary
        assert "병합 가능합니다" in summary


class TestReviewSummarizerSummarize:
    """요약 생성 테스트."""

    @pytest.mark.asyncio
    async def test_summarize_empty_reviews(self):
        """빈 리뷰 요약."""
        summarizer = ReviewSummarizer()
        result = ReviewResult(
            diff_summary=DiffStats(0, 0, 0),
            agent_reviews=[],
            total_comments=0,
            by_severity={},
            summary="",
        )

        updated = await summarizer.summarize(result)
        assert updated is result  # 동일 객체 반환

    @pytest.mark.asyncio
    async def test_summarize_with_llm(self, mocker, sample_review_result, mock_llm):
        """LLM으로 요약 생성."""
        summarizer = ReviewSummarizer(llm=mock_llm)

        updated = await summarizer.summarize(sample_review_result)

        assert updated.summary == "Test summary"
        mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_llm_error_fallback(self, mocker, sample_review_result):
        """LLM 에러 시 폴백."""
        mock_llm = mocker.MagicMock()
        mock_llm.chat.side_effect = Exception("LLM error")

        summarizer = ReviewSummarizer(llm=mock_llm)
        updated = await summarizer.summarize(sample_review_result)

        assert "3개의 코멘트" in updated.summary


# ============================================================
# Top-level Function Tests
# ============================================================


class TestRunReview:
    """run_review 함수 테스트."""

    @pytest.mark.asyncio
    async def test_run_review_empty_diff(self, mocker, tmp_path):
        """빈 diff 리뷰."""
        # Git repo 생성
        mocker.patch(
            "code_sherpa.review.runner.GitClient"
        ).return_value.get_diff.return_value = ""

        result = await run_review(path=tmp_path)

        assert result.total_comments == 0
        assert result.summary == "리뷰할 변경사항이 없습니다."

    @pytest.mark.asyncio
    async def test_run_review_with_agents(self, mocker, tmp_path, sample_agent_review):
        """에이전트로 리뷰."""
        mocker.patch(
            "code_sherpa.review.runner.GitClient"
        ).return_value.get_diff.return_value = "diff --git a/test.py"

        mock_parser = mocker.patch("code_sherpa.review.runner.DiffParser")
        mock_parser.return_value.parse.return_value = ParsedDiff(
            files=[],
            stats=DiffStats(1, 5, 2),
            raw="",
        )

        mock_get_agent = mocker.patch("code_sherpa.review.runner.get_agent")
        mock_agent = mocker.AsyncMock()
        mock_agent.name = "architect"
        mock_agent.review.return_value = sample_agent_review
        mock_get_agent.return_value = mock_agent

        result = await run_review(
            path=tmp_path,
            agents=["architect"],
            summarize=False,
        )

        assert result.total_comments == 2


class TestRunReviewSync:
    """run_review_sync 함수 테스트."""

    def test_run_review_sync(self, mocker, tmp_path):
        """동기 버전 테스트."""
        mocker.patch(
            "code_sherpa.review.runner.GitClient"
        ).return_value.get_diff.return_value = ""

        result = run_review_sync(path=tmp_path)

        assert result.total_comments == 0

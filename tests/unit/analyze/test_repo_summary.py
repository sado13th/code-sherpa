"""RepoSummarizer 테스트."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_sherpa.analyze.repo_summary import (
    RepoSummarizer,
    _count_lines_in_file,
    _format_commits_for_prompt,
    _format_languages_for_prompt,
)
from code_sherpa.shared.models import Commit, LanguageStats, RepoSummary


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """테스트용 Git 저장소를 생성합니다."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Git 초기화
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # 샘플 파일 생성
    (repo_path / "main.py").write_text("print('hello')\nprint('world')\n")
    (repo_path / "utils.py").write_text("def helper():\n    pass\n")
    (repo_path / "app.js").write_text("console.log('test');\n")

    # 커밋
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


class TestHelperFunctions:
    """헬퍼 함수 테스트."""

    def test_count_lines_in_file(self, tmp_path: Path) -> None:
        """파일 라인 수 계산."""
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\nline3\n")

        result = _count_lines_in_file(test_file)
        assert result == 3

    def test_count_lines_empty_file(self, tmp_path: Path) -> None:
        """빈 파일 라인 수."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        result = _count_lines_in_file(test_file)
        assert result == 0

    def test_count_lines_nonexistent_file(self, tmp_path: Path) -> None:
        """존재하지 않는 파일은 0 반환."""
        nonexistent = tmp_path / "nonexistent.py"

        result = _count_lines_in_file(nonexistent)
        assert result == 0

    def test_format_languages_for_prompt(self) -> None:
        """언어 통계 포맷팅."""
        languages = [
            LanguageStats(language="Python", files=5, lines=100, percentage=50.0),
            LanguageStats(language="JavaScript", files=3, lines=60, percentage=30.0),
        ]

        result = _format_languages_for_prompt(languages)
        assert "Python: 50.0%" in result
        assert "JavaScript: 30.0%" in result

    def test_format_commits_for_prompt_empty(self) -> None:
        """빈 커밋 목록 포맷팅."""
        result = _format_commits_for_prompt([])
        assert result == "No commits found."

    def test_format_commits_for_prompt(self) -> None:
        """커밋 목록 포맷팅."""

        commits = [
            Commit(
                hash="abc1234567890",
                short_hash="abc1234",
                message="Test commit",
                author="Test User",
                date=datetime(2024, 1, 15, tzinfo=UTC),
            ),
        ]

        result = _format_commits_for_prompt(commits)
        assert "[abc1234]" in result
        assert "2024-01-15" in result
        assert "Test commit" in result


class TestRepoSummarizer:
    """RepoSummarizer 테스트."""

    def test_init_default(self) -> None:
        """기본 초기화."""
        summarizer = RepoSummarizer()
        assert summarizer._llm is None
        assert summarizer._config is not None

    def test_init_with_llm(self) -> None:
        """LLM과 함께 초기화."""
        mock_llm = MagicMock()
        summarizer = RepoSummarizer(llm=mock_llm)
        assert summarizer._llm == mock_llm

    @pytest.mark.asyncio
    async def test_summarize_returns_repo_summary(self, git_repo: Path) -> None:
        """summarize()가 RepoSummary 반환."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = "This is a test repository summary."

        summarizer = RepoSummarizer(llm=mock_llm)
        result = await summarizer.summarize(git_repo)

        assert isinstance(result, RepoSummary)
        assert result.path == git_repo
        assert result.name == git_repo.name
        assert result.total_files == 3  # main.py, utils.py, app.js
        assert result.total_lines > 0
        assert len(result.languages) > 0
        assert result.summary == "This is a test repository summary."

    @pytest.mark.asyncio
    async def test_summarize_calculates_language_stats(self, git_repo: Path) -> None:
        """summarize()가 언어 통계 계산."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Summary"

        summarizer = RepoSummarizer(llm=mock_llm)
        result = await summarizer.summarize(git_repo)

        # Python과 JavaScript 파일이 있어야 함
        language_names = [lang.language for lang in result.languages]
        assert "Python" in language_names
        assert "JavaScript" in language_names

    @pytest.mark.asyncio
    async def test_summarize_gets_recent_commits(self, git_repo: Path) -> None:
        """summarize()가 최근 커밋 가져옴."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Summary"

        summarizer = RepoSummarizer(llm=mock_llm)
        result = await summarizer.summarize(git_repo)

        assert len(result.recent_commits) >= 1
        assert result.recent_commits[0].message == "Initial commit"

    @pytest.mark.asyncio
    async def test_summarize_calls_llm_with_prompt(self, git_repo: Path) -> None:
        """summarize()가 프롬프트로 LLM 호출."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = "AI generated summary"

        summarizer = RepoSummarizer(llm=mock_llm)
        await summarizer.summarize(git_repo)

        mock_llm.complete.assert_called_once()
        prompt = mock_llm.complete.call_args[0][0]
        assert "Repository" in prompt or "Total Files" in prompt

    def test_summarize_sync(self, git_repo: Path) -> None:
        """summarize_sync() 동기 호출."""
        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Summary"

        summarizer = RepoSummarizer(llm=mock_llm)
        result = summarizer.summarize_sync(git_repo)

        assert isinstance(result, RepoSummary)
        assert result.path == git_repo

    @pytest.mark.asyncio
    async def test_summarize_with_exclude_patterns(self, git_repo: Path) -> None:
        """제외 패턴이 적용되는지 확인."""
        # node_modules 디렉토리 생성
        node_modules = git_repo / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.json").write_text('{"name": "test"}')

        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Summary"

        summarizer = RepoSummarizer(llm=mock_llm)
        result = await summarizer.summarize(git_repo)

        # node_modules는 기본적으로 제외되어야 함
        # 총 파일 수가 3 (main.py, utils.py, app.js)이어야 함
        assert result.total_files == 3

    @pytest.mark.asyncio
    async def test_lazy_llm_initialization(self, git_repo: Path) -> None:
        """LLM이 지연 초기화되는지 확인."""
        with patch("code_sherpa.analyze.repo_summary.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.complete.return_value = "Summary"
            mock_get_llm.return_value = mock_llm

            summarizer = RepoSummarizer()  # LLM 없이 초기화
            assert summarizer._llm is None

            await summarizer.summarize(git_repo)

            # get_llm이 호출되어야 함
            mock_get_llm.assert_called_once()

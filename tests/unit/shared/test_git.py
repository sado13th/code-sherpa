"""GitClient 테스트."""

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from code_sherpa.shared.git import (
    EXTENSION_LANGUAGE_MAP,
    GitClient,
    InvalidRepositoryError,
)
from code_sherpa.shared.models import Commit


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
    # GPG 서명 비활성화 (테스트 환경용)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # 샘플 파일 생성
    (repo_path / "main.py").write_text("print('hello')\n")
    (repo_path / "utils.py").write_text("def helper(): pass\n")
    (repo_path / "app.js").write_text("console.log('test');\n")
    (repo_path / "styles.css").write_text("body { margin: 0; }\n")
    (repo_path / "README.md").write_text("# Test\n")

    # 커밋
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def git_client(git_repo: Path) -> GitClient:
    """테스트용 GitClient 인스턴스를 반환합니다."""
    return GitClient(git_repo)


class TestGitClientInit:
    """GitClient 초기화 테스트."""

    def test_init_with_valid_repo(self, git_repo: Path) -> None:
        """유효한 저장소로 초기화."""
        client = GitClient(git_repo)
        assert client.path == git_repo

    def test_init_with_string_path(self, git_repo: Path) -> None:
        """문자열 경로로 초기화."""
        client = GitClient(str(git_repo))
        assert client.path == git_repo

    def test_init_with_invalid_repo(self, tmp_path: Path) -> None:
        """유효하지 않은 저장소로 초기화 시 예외."""
        invalid_path = tmp_path / "not_a_repo"
        invalid_path.mkdir()

        with pytest.raises(InvalidRepositoryError):
            GitClient(invalid_path)


class TestIsValidRepo:
    """is_valid_repo 메서드 테스트."""

    def test_valid_repo(self, git_client: GitClient) -> None:
        """유효한 저장소 확인."""
        assert git_client.is_valid_repo() is True


class TestGetDiff:
    """get_diff 메서드 테스트."""

    def test_diff_no_changes(self, git_client: GitClient, git_repo: Path) -> None:
        """변경사항 없을 때 빈 diff."""
        diff = git_client.get_diff()
        assert diff == ""

    def test_diff_unstaged_changes(self, git_client: GitClient, git_repo: Path) -> None:
        """unstaged 변경사항 diff."""
        (git_repo / "main.py").write_text("print('changed')\n")

        diff = git_client.get_diff(staged=False)
        assert "changed" in diff
        assert "main.py" in diff

    def test_diff_staged_changes(self, git_client: GitClient, git_repo: Path) -> None:
        """staged 변경사항 diff."""
        (git_repo / "main.py").write_text("print('staged')\n")
        subprocess.run(
            ["git", "add", "main.py"], cwd=git_repo, check=True, capture_output=True
        )

        diff = git_client.get_diff(staged=True)
        assert "staged" in diff

    def test_diff_commit_range(self, git_client: GitClient, git_repo: Path) -> None:
        """커밋 범위 diff."""
        # 새 커밋 생성
        (git_repo / "new_file.py").write_text("new content\n")
        subprocess.run(
            ["git", "add", "new_file.py"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        diff = git_client.get_diff(commit_range="HEAD~1..HEAD")
        assert "new_file.py" in diff


class TestGetFileList:
    """get_file_list 메서드 테스트."""

    def test_get_all_files(self, git_client: GitClient, git_repo: Path) -> None:
        """모든 추적 파일 목록."""
        files = git_client.get_file_list()
        filenames = [f.name for f in files]

        assert "main.py" in filenames
        assert "utils.py" in filenames
        assert "app.js" in filenames
        assert "styles.css" in filenames
        assert "README.md" in filenames

    def test_get_files_with_exclude(
        self, git_client: GitClient, git_repo: Path
    ) -> None:
        """제외 패턴으로 필터링."""
        files = git_client.get_file_list(exclude_patterns=["*.py"])
        filenames = [f.name for f in files]

        assert "main.py" not in filenames
        assert "utils.py" not in filenames
        assert "app.js" in filenames

    def test_get_files_multiple_exclude_patterns(
        self, git_client: GitClient, git_repo: Path
    ) -> None:
        """여러 제외 패턴."""
        files = git_client.get_file_list(exclude_patterns=["*.py", "*.js"])
        filenames = [f.name for f in files]

        assert "main.py" not in filenames
        assert "app.js" not in filenames
        assert "styles.css" in filenames

    def test_files_are_absolute_paths(
        self, git_client: GitClient, git_repo: Path
    ) -> None:
        """파일 경로가 절대경로인지 확인."""
        files = git_client.get_file_list()
        for f in files:
            assert f.is_absolute()


class TestCountFiles:
    """count_files 메서드 테스트."""

    def test_count_files(self, git_client: GitClient) -> None:
        """파일 수 카운트."""
        count = git_client.count_files()
        assert count == 5  # main.py, utils.py, app.js, styles.css, README.md


class TestDetectLanguages:
    """detect_languages 메서드 테스트."""

    def test_detect_languages(self, git_client: GitClient) -> None:
        """언어 감지."""
        languages = git_client.detect_languages()

        assert languages.get("Python") == 2  # main.py, utils.py
        assert languages.get("JavaScript") == 1  # app.js
        assert languages.get("CSS") == 1  # styles.css
        assert languages.get("Markdown") == 1  # README.md

    def test_extension_language_map_coverage(self) -> None:
        """주요 확장자 매핑 확인."""
        assert EXTENSION_LANGUAGE_MAP[".py"] == "Python"
        assert EXTENSION_LANGUAGE_MAP[".js"] == "JavaScript"
        assert EXTENSION_LANGUAGE_MAP[".ts"] == "TypeScript"
        assert EXTENSION_LANGUAGE_MAP[".java"] == "Java"
        assert EXTENSION_LANGUAGE_MAP[".go"] == "Go"
        assert EXTENSION_LANGUAGE_MAP[".rs"] == "Rust"


class TestGetRecentCommits:
    """get_recent_commits 메서드 테스트."""

    def test_get_commits(self, git_client: GitClient) -> None:
        """최근 커밋 목록."""
        commits = git_client.get_recent_commits()

        assert len(commits) == 1
        assert commits[0].message == "Initial commit"
        assert isinstance(commits[0], Commit)

    def test_commit_has_required_fields(self, git_client: GitClient) -> None:
        """커밋 필드 확인."""
        commits = git_client.get_recent_commits()
        commit = commits[0]

        assert len(commit.hash) == 40
        assert len(commit.short_hash) == 7
        assert commit.message == "Initial commit"
        assert commit.author == "Test User"
        assert isinstance(commit.date, datetime)

    def test_multiple_commits(self, git_client: GitClient, git_repo: Path) -> None:
        """여러 커밋 가져오기."""
        # 추가 커밋 생성
        (git_repo / "file2.py").write_text("content\n")
        subprocess.run(
            ["git", "add", "file2.py"], cwd=git_repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Second commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        commits = git_client.get_recent_commits(count=2)
        assert len(commits) == 2
        assert commits[0].message == "Second commit"
        assert commits[1].message == "Initial commit"

    def test_commit_count_limit(self, git_client: GitClient, git_repo: Path) -> None:
        """커밋 수 제한."""
        # 추가 커밋 생성
        for i in range(5):
            (git_repo / f"file{i}.txt").write_text(f"content {i}\n")
            subprocess.run(
                ["git", "add", f"file{i}.txt"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i}"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )

        commits = git_client.get_recent_commits(count=3)
        assert len(commits) == 3


class TestGetCurrentBranch:
    """get_current_branch 메서드 테스트."""

    def test_get_default_branch(self, git_client: GitClient) -> None:
        """기본 브랜치 이름."""
        branch = git_client.get_current_branch()
        # Git 버전에 따라 기본 브랜치가 main 또는 master
        assert branch in ["main", "master"]

    def test_get_feature_branch(self, git_client: GitClient, git_repo: Path) -> None:
        """feature 브랜치 이름."""
        subprocess.run(
            ["git", "checkout", "-b", "feature/test"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        branch = git_client.get_current_branch()
        assert branch == "feature/test"

    def test_detached_head(self, git_client: GitClient, git_repo: Path) -> None:
        """detached HEAD 상태."""
        # HEAD 커밋 해시 가져오기
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_hash = result.stdout.strip()

        # detached HEAD로 체크아웃
        subprocess.run(
            ["git", "checkout", commit_hash],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        branch = git_client.get_current_branch()
        assert branch == commit_hash[:7]

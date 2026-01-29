"""Git 클라이언트 모듈."""

import fnmatch
from datetime import UTC
from pathlib import Path

from git import InvalidGitRepositoryError, Repo
from git.exc import GitCommandError

from code_sherpa.shared.models import Commit


class GitError(Exception):
    """Git 관련 에러."""

    pass


class InvalidRepositoryError(GitError):
    """유효하지 않은 Git 저장소 에러."""

    pass


# 확장자 -> 언어 매핑
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript (JSX)",
    ".tsx": "TypeScript (TSX)",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".scala": "Scala",
    ".r": "R",
    ".R": "R",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".pl": "Perl",
    ".pm": "Perl",
    ".sh": "Shell",
    ".bash": "Bash",
    ".zsh": "Zsh",
    ".fish": "Fish",
    ".ps1": "PowerShell",
    ".lua": "Lua",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "Config",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".txt": "Text",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".dart": "Dart",
    ".elm": "Elm",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hrl": "Erlang",
    ".hs": "Haskell",
    ".ml": "OCaml",
    ".mli": "OCaml",
    ".clj": "Clojure",
    ".cljs": "ClojureScript",
    ".jl": "Julia",
    ".nim": "Nim",
    ".zig": "Zig",
    ".v": "V",
    ".d": "D",
    ".f90": "Fortran",
    ".f95": "Fortran",
    ".f03": "Fortran",
    ".asm": "Assembly",
    ".s": "Assembly",
    ".proto": "Protocol Buffers",
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    ".dockerfile": "Dockerfile",
    ".tf": "Terraform",
    ".hcl": "HCL",
    ".makefile": "Makefile",
}


class GitClient:
    """Git 저장소 클라이언트."""

    def __init__(self, path: str | Path = ".") -> None:
        """Git 저장소를 엽니다.

        Args:
            path: Git 저장소 경로. 기본값은 현재 디렉토리.

        Raises:
            InvalidRepositoryError: 유효하지 않은 Git 저장소인 경우.
        """
        self._path = Path(path).resolve()
        try:
            self._repo = Repo(self._path)
        except InvalidGitRepositoryError as e:
            raise InvalidRepositoryError(
                f"유효하지 않은 Git 저장소입니다: {self._path}"
            ) from e

    @property
    def path(self) -> Path:
        """저장소 경로를 반환합니다."""
        return self._path

    def is_valid_repo(self) -> bool:
        """유효한 Git 저장소인지 확인합니다.

        Returns:
            유효한 저장소이면 True, 아니면 False.
        """
        try:
            # bare 저장소가 아니고 git_dir이 존재하면 유효
            return not self._repo.bare and self._repo.git_dir is not None
        except Exception:
            return False

    def get_diff(self, staged: bool = False, commit_range: str | None = None) -> str:
        """Git diff를 가져옵니다.

        Args:
            staged: True이면 staged 변경사항만, False이면 unstaged 변경사항.
            commit_range: 커밋 범위 (예: "HEAD~3..HEAD", "main..feature").
                         지정하면 staged 인자는 무시됩니다.

        Returns:
            diff 문자열.

        Raises:
            GitError: Git 명령 실행 실패 시.
        """
        try:
            if commit_range:
                # 커밋 범위 diff
                return self._repo.git.diff(commit_range)
            elif staged:
                # staged 변경사항
                return self._repo.git.diff("--cached")
            else:
                # unstaged 변경사항
                return self._repo.git.diff()
        except GitCommandError as e:
            raise GitError(f"diff 가져오기 실패: {e}") from e

    def get_file_list(self, exclude_patterns: list[str] | None = None) -> list[Path]:
        """Git에서 추적하는 파일 목록을 가져옵니다.

        Args:
            exclude_patterns: 제외할 파일 패턴 목록 (fnmatch 패턴).

        Returns:
            추적 파일의 Path 목록.

        Raises:
            GitError: Git 명령 실행 실패 시.
        """
        try:
            # ls-files로 추적 파일 목록 가져오기
            output = self._repo.git.ls_files()
            if not output:
                return []

            files = output.split("\n")
            exclude_patterns = exclude_patterns or []

            result: list[Path] = []
            for file in files:
                if not file:
                    continue

                # 제외 패턴 체크
                excluded = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(file, pattern):
                        excluded = True
                        break

                if not excluded:
                    result.append(self._path / file)

            return result
        except GitCommandError as e:
            raise GitError(f"파일 목록 가져오기 실패: {e}") from e

    def count_files(self) -> int:
        """추적 파일 수를 반환합니다.

        Returns:
            추적 파일 수.
        """
        return len(self.get_file_list())

    def detect_languages(self) -> dict[str, int]:
        """확장자별 파일 수를 반환합니다.

        Returns:
            언어 이름 -> 파일 수 딕셔너리.
        """
        files = self.get_file_list()
        language_counts: dict[str, int] = {}

        for file in files:
            ext = file.suffix.lower()
            # Makefile, Dockerfile 등 확장자 없는 특수 파일 처리
            if not ext:
                name = file.name.lower()
                if name == "makefile":
                    ext = ".makefile"
                elif name == "dockerfile":
                    ext = ".dockerfile"

            language = EXTENSION_LANGUAGE_MAP.get(ext, "Other")
            language_counts[language] = language_counts.get(language, 0) + 1

        return language_counts

    def get_recent_commits(self, count: int = 10) -> list[Commit]:
        """최근 커밋 목록을 가져옵니다.

        Args:
            count: 가져올 커밋 수. 기본값 10.

        Returns:
            Commit 객체 목록.

        Raises:
            GitError: Git 명령 실행 실패 시.
        """
        try:
            commits: list[Commit] = []
            for git_commit in self._repo.iter_commits(max_count=count):
                # committed_datetime은 timezone-aware datetime
                commit_date = git_commit.committed_datetime
                # timezone-aware가 아닌 경우 UTC로 처리
                if commit_date.tzinfo is None:
                    commit_date = commit_date.replace(tzinfo=UTC)

                commit = Commit(
                    hash=git_commit.hexsha,
                    short_hash=git_commit.hexsha[:7],
                    message=git_commit.message.strip(),
                    author=str(git_commit.author),
                    date=commit_date,
                )
                commits.append(commit)

            return commits
        except GitCommandError as e:
            raise GitError(f"커밋 목록 가져오기 실패: {e}") from e
        except Exception as e:
            # 빈 저장소 등의 경우
            if "does not have any commits" in str(e):
                return []
            raise GitError(f"커밋 목록 가져오기 실패: {e}") from e

    def get_current_branch(self) -> str:
        """현재 브랜치 이름을 반환합니다.

        Returns:
            현재 브랜치 이름. detached HEAD 상태이면 커밋 해시 반환.

        Raises:
            GitError: Git 명령 실행 실패 시.
        """
        try:
            if self._repo.head.is_detached:
                return self._repo.head.commit.hexsha[:7]
            return self._repo.active_branch.name
        except GitCommandError as e:
            raise GitError(f"현재 브랜치 가져오기 실패: {e}") from e
        except TypeError:
            # 빈 저장소의 경우
            return "main"

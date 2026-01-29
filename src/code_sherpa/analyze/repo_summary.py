"""저장소 요약 분석 모듈."""

from pathlib import Path

from code_sherpa.prompts import load_prompt
from code_sherpa.shared.config import AnalyzeConfig, AppConfig
from code_sherpa.shared.git import GitClient
from code_sherpa.shared.llm import BaseLLM, get_llm
from code_sherpa.shared.models import Commit, LanguageStats, RepoSummary


def _count_lines_in_file(file_path: Path) -> int:
    """파일의 라인 수를 계산합니다.

    Args:
        file_path: 파일 경로

    Returns:
        라인 수. 읽기 실패 시 0 반환.
    """
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _format_languages_for_prompt(languages: list[LanguageStats]) -> str:
    """언어 통계를 프롬프트용 문자열로 포맷합니다.

    Args:
        languages: 언어 통계 목록

    Returns:
        포맷된 문자열 (예: "Python: 45.2%, JavaScript: 30.1%")
    """
    parts = [f"{lang.language}: {lang.percentage:.1f}%" for lang in languages]
    return ", ".join(parts)


def _format_commits_for_prompt(commits: list[Commit]) -> str:
    """커밋 목록을 프롬프트용 문자열로 포맷합니다.

    Args:
        commits: 커밋 목록

    Returns:
        포맷된 문자열
    """
    if not commits:
        return "No commits found."

    lines = []
    for commit in commits:
        date_str = commit.date.strftime("%Y-%m-%d")
        lines.append(f"- [{commit.short_hash}] {date_str}: {commit.message}")
    return "\n".join(lines)


class RepoSummarizer:
    """저장소 요약 분석기.

    Git 저장소를 분석하여 구조, 언어 통계, 최근 커밋 정보 등을
    포함한 요약 정보를 생성합니다.
    """

    def __init__(
        self,
        llm: BaseLLM | None = None,
        config: AppConfig | None = None,
    ) -> None:
        """RepoSummarizer를 초기화합니다.

        Args:
            llm: LLM 인스턴스. None이면 config에 따라 자동 생성.
            config: 애플리케이션 설정. None이면 기본값 사용.
        """
        self._config = config or AppConfig()
        self._llm = llm
        self._analyze_config: AnalyzeConfig = self._config.analyze

    def _get_llm(self) -> BaseLLM:
        """LLM 인스턴스를 반환합니다 (지연 초기화)."""
        if self._llm is None:
            llm_config = self._config.llm
            self._llm = get_llm(
                provider=llm_config.provider,
                model=llm_config.model,
                max_tokens=llm_config.max_tokens,
                temperature=llm_config.temperature,
            )
        return self._llm

    def _calculate_language_stats(
        self, git_client: GitClient, total_lines: int
    ) -> list[LanguageStats]:
        """언어별 통계를 계산합니다.

        Args:
            git_client: GitClient 인스턴스
            total_lines: 총 라인 수

        Returns:
            언어별 통계 목록 (비율 내림차순 정렬)
        """
        files = git_client.get_file_list(
            exclude_patterns=self._analyze_config.exclude_patterns
        )

        # 언어별 라인 수 계산
        language_lines: dict[str, int] = {}
        language_files: dict[str, int] = {}

        from code_sherpa.shared.git import EXTENSION_LANGUAGE_MAP

        for file_path in files:
            ext = file_path.suffix.lower()
            if not ext:
                name = file_path.name.lower()
                if name == "makefile":
                    ext = ".makefile"
                elif name == "dockerfile":
                    ext = ".dockerfile"

            language = EXTENSION_LANGUAGE_MAP.get(ext, "Other")
            lines = _count_lines_in_file(file_path)

            language_lines[language] = language_lines.get(language, 0) + lines
            language_files[language] = language_files.get(language, 0) + 1

        # LanguageStats 목록 생성
        stats: list[LanguageStats] = []
        for language, lines in language_lines.items():
            percentage = (lines / total_lines * 100) if total_lines > 0 else 0.0
            stats.append(
                LanguageStats(
                    language=language,
                    files=language_files.get(language, 0),
                    lines=lines,
                    percentage=percentage,
                )
            )

        # 비율 내림차순 정렬
        stats.sort(key=lambda x: x.percentage, reverse=True)
        return stats

    async def summarize(self, path: Path) -> RepoSummary:
        """저장소를 분석하여 요약 정보를 반환합니다.

        Args:
            path: 분석할 저장소 경로

        Returns:
            RepoSummary 객체

        Raises:
            InvalidRepositoryError: 유효하지 않은 Git 저장소인 경우
        """
        # 절대 경로로 변환
        path = path.resolve()

        # Git 클라이언트 초기화
        git_client = GitClient(path)

        # 파일 목록 가져오기
        files = git_client.get_file_list(
            exclude_patterns=self._analyze_config.exclude_patterns
        )
        total_files = len(files)

        # 총 라인 수 계산
        total_lines = sum(_count_lines_in_file(f) for f in files)

        # 최근 커밋 가져오기
        recent_commits = git_client.get_recent_commits(count=10)

        # 언어 통계 계산
        languages = self._calculate_language_stats(git_client, total_lines)

        # LLM으로 요약 생성
        llm = self._get_llm()
        prompt = load_prompt(
            "analyze/repo_summary",
            total_files=total_files,
            total_lines=total_lines,
            languages=_format_languages_for_prompt(languages),
            recent_commits=_format_commits_for_prompt(recent_commits),
        )
        summary = llm.complete(prompt)

        return RepoSummary(
            path=path,
            name=path.name,
            total_files=total_files,
            total_lines=total_lines,
            languages=languages,
            recent_commits=recent_commits,
            summary=summary,
        )

    def summarize_sync(self, path: Path) -> RepoSummary:
        """저장소를 동기적으로 분석하여 요약 정보를 반환합니다.

        async 환경이 아닐 때 사용합니다.

        Args:
            path: 분석할 저장소 경로

        Returns:
            RepoSummary 객체
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.summarize(path))

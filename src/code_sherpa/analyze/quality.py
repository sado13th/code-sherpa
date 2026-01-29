"""코드 품질 분석 모듈."""

import re
from pathlib import Path

from code_sherpa.shared.git import EXTENSION_LANGUAGE_MAP
from code_sherpa.shared.llm import BaseLLM, get_llm
from code_sherpa.shared.models import QualityIssue, QualityReport, Severity

# 복잡도 측정을 위한 패턴
COMPLEXITY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "conditional": [
        re.compile(r"\bif\b"),
        re.compile(r"\belif\b"),
        re.compile(r"\belse\b"),
        re.compile(r"\bswitch\b"),
        re.compile(r"\bcase\b"),
        re.compile(r"\?\s*:"),  # 삼항 연산자
    ],
    "loop": [
        re.compile(r"\bfor\b"),
        re.compile(r"\bwhile\b"),
        re.compile(r"\bdo\b"),
    ],
    "exception": [
        re.compile(r"\btry\b"),
        re.compile(r"\bcatch\b"),
        re.compile(r"\bexcept\b"),
        re.compile(r"\bfinally\b"),
    ],
    "logical": [
        re.compile(r"\b(and|or|&&|\|\|)\b"),
    ],
}

# 품질 이슈 패턴
QUALITY_ISSUE_PATTERNS: list[tuple[str, re.Pattern[str], str, Severity]] = [
    (
        "long_line",
        re.compile(r"^.{121,}$", re.MULTILINE),
        "Line exceeds 120 characters",
        Severity.WARNING,
    ),
    (
        "todo_comment",
        re.compile(r"#\s*TODO\b|//\s*TODO\b|/\*\s*TODO\b", re.IGNORECASE),
        "TODO comment found",
        Severity.INFO,
    ),
    (
        "fixme_comment",
        re.compile(r"#\s*FIXME\b|//\s*FIXME\b|/\*\s*FIXME\b", re.IGNORECASE),
        "FIXME comment found",
        Severity.WARNING,
    ),
    (
        "hack_comment",
        re.compile(r"#\s*HACK\b|//\s*HACK\b|/\*\s*HACK\b", re.IGNORECASE),
        "HACK comment found - technical debt indicator",
        Severity.WARNING,
    ),
    (
        "hardcoded_password",
        re.compile(
            r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']+["\']',
            re.IGNORECASE,
        ),
        "Potential hardcoded password detected",
        Severity.ERROR,
    ),
    (
        "hardcoded_secret",
        re.compile(
            r'(?:secret|api_key|apikey|token)\s*[=:]\s*["\'][^"\']+["\']',
            re.IGNORECASE,
        ),
        "Potential hardcoded secret/API key detected",
        Severity.ERROR,
    ),
    (
        "debug_statement",
        re.compile(r"\bconsole\.log\(|print\s*\(|debugger\b"),
        "Debug statement found",
        Severity.INFO,
    ),
    (
        "empty_except",
        re.compile(r"except\s*:\s*\n\s*pass\b|except\s*:\s*\n\s*\.\.\."),
        "Empty except block - may hide errors",
        Severity.WARNING,
    ),
    (
        "magic_number",
        re.compile(r"(?<![0-9])[2-9]\d{2,}(?![0-9])"),  # 3자리 이상 숫자
        "Magic number detected - consider using named constant",
        Severity.INFO,
    ),
]

# 긴 함수 감지를 위한 언어별 함수 패턴
FUNCTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "Python": re.compile(
        r"^\s*(?:async\s+)?def\s+(\w+)\s*\(",
        re.MULTILINE,
    ),
    "JavaScript": re.compile(
        r"^\s*(?:async\s+)?(?:function\s+(\w+)|(\w+)\s*[=:]\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))",
        re.MULTILINE,
    ),
    "TypeScript": re.compile(
        r"^\s*(?:async\s+)?(?:function\s+(\w+)|(\w+)\s*[=:]\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))",
        re.MULTILINE,
    ),
    "Go": re.compile(
        r"^\s*func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
        re.MULTILINE,
    ),
    "Java": re.compile(
        r"^\s*(?:public|private|protected|static|\s)+[\w<>[\]]+\s+(\w+)\s*\(",
        re.MULTILINE,
    ),
}

# 긴 함수 임계값 (라인 수)
LONG_FUNCTION_THRESHOLD = 50


def _detect_language(file_path: Path) -> str:
    """파일 확장자로 언어를 감지합니다."""
    ext = file_path.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "Unknown")


def _calculate_cyclomatic_complexity(content: str) -> int:
    """순환 복잡도를 계산합니다.

    간단한 휴리스틱 기반 계산:
    - 기본값 1
    - 조건문, 반복문, 논리 연산자마다 +1

    Args:
        content: 소스 코드 내용

    Returns:
        복잡도 점수
    """
    complexity = 1  # 기본값

    for category, patterns in COMPLEXITY_PATTERNS.items():
        for pattern in patterns:
            matches = pattern.findall(content)
            complexity += len(matches)

    return complexity


def _find_long_functions(
    content: str,
    language: str,
    file_path: Path,
) -> list[QualityIssue]:
    """긴 함수를 찾습니다.

    Args:
        content: 소스 코드 내용
        language: 프로그래밍 언어
        file_path: 파일 경로

    Returns:
        긴 함수 관련 QualityIssue 목록
    """
    issues: list[QualityIssue] = []

    pattern = FUNCTION_PATTERNS.get(language)
    if not pattern:
        return issues

    matches = list(pattern.finditer(content))

    for i, match in enumerate(matches):
        # 함수 이름 추출 (그룹 중 첫 번째 non-None 값)
        func_name = None
        for group in match.groups():
            if group:
                func_name = group
                break

        if not func_name:
            continue

        # 시작 라인 계산
        start_line = content[: match.start()].count("\n") + 1

        # 다음 함수 시작 또는 파일 끝까지의 라인 수 계산
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(content)

        func_content = content[match.start() : end_pos]
        func_lines = func_content.count("\n") + 1

        if func_lines > LONG_FUNCTION_THRESHOLD:
            issues.append(
                QualityIssue(
                    path=file_path,
                    line=start_line,
                    issue_type="long_function",
                    message=f"Function '{func_name}' has {func_lines} lines "
                    f"(threshold: {LONG_FUNCTION_THRESHOLD})",
                    severity=Severity.WARNING,
                )
            )

    return issues


def _find_pattern_issues(
    content: str,
    file_path: Path,
) -> list[QualityIssue]:
    """패턴 기반 품질 이슈를 찾습니다.

    Args:
        content: 소스 코드 내용
        file_path: 파일 경로

    Returns:
        QualityIssue 목록
    """
    issues: list[QualityIssue] = []

    for issue_type, pattern, message, severity in QUALITY_ISSUE_PATTERNS:
        for match in pattern.finditer(content):
            # 라인 번호 계산
            line_num = content[: match.start()].count("\n") + 1

            issues.append(
                QualityIssue(
                    path=file_path,
                    line=line_num,
                    issue_type=issue_type,
                    message=message,
                    severity=severity,
                )
            )

    return issues


def _calculate_quality_score(
    complexity: int,
    issues: list[QualityIssue],
    total_lines: int,
) -> float:
    """품질 점수를 계산합니다.

    0-100 스케일, 높을수록 좋음.

    Args:
        complexity: 전체 복잡도
        issues: 발견된 이슈 목록
        total_lines: 총 라인 수

    Returns:
        품질 점수 (0-100)
    """
    if total_lines == 0:
        return 100.0

    # 기본 점수 100에서 감점
    score = 100.0

    # 복잡도 감점 (라인당 복잡도)
    complexity_per_line = complexity / total_lines
    if complexity_per_line > 0.5:
        score -= min(20, (complexity_per_line - 0.5) * 40)

    # 이슈별 감점
    for issue in issues:
        if issue.severity == Severity.ERROR:
            score -= 5
        elif issue.severity == Severity.WARNING:
            score -= 2
        else:  # INFO
            score -= 0.5

    return max(0, min(100, score))


class QualityAnalyzer:
    """코드 품질 분석기.

    복잡도, 이슈 감지, 개선 제안을 포함한 품질 분석을 수행합니다.
    """

    def __init__(
        self,
        llm: BaseLLM | None = None,
        max_file_size_kb: int = 500,
    ) -> None:
        """QualityAnalyzer를 초기화합니다.

        Args:
            llm: LLM 인스턴스. None이면 기본 설정으로 자동 생성.
            max_file_size_kb: 분석 가능한 최대 파일 크기 (KB)
        """
        self._llm = llm
        self._max_file_size_kb = max_file_size_kb

    def _get_llm(self) -> BaseLLM:
        """LLM 인스턴스를 반환합니다 (지연 초기화)."""
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def _analyze_file(self, file_path: Path) -> tuple[int, list[QualityIssue], int]:
        """단일 파일을 분석합니다.

        Args:
            file_path: 파일 경로

        Returns:
            (복잡도, 이슈 목록, 라인 수) 튜플
        """
        try:
            # 파일 크기 확인
            file_size_kb = file_path.stat().st_size / 1024
            if file_size_kb > self._max_file_size_kb:
                return 0, [], 0

            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = len(content.splitlines())

            if lines == 0:
                return 0, [], 0

            language = _detect_language(file_path)

            # 복잡도 계산
            complexity = _calculate_cyclomatic_complexity(content)

            # 이슈 감지
            issues: list[QualityIssue] = []
            issues.extend(_find_pattern_issues(content, file_path))
            issues.extend(_find_long_functions(content, language, file_path))

            return complexity, issues, lines

        except (OSError, UnicodeDecodeError):
            return 0, [], 0

    def _generate_summary(
        self,
        score: float,
        issues: list[QualityIssue],
        total_files: int,
    ) -> str:
        """분석 결과 요약을 생성합니다.

        Args:
            score: 품질 점수
            issues: 전체 이슈 목록
            total_files: 분석된 파일 수

        Returns:
            요약 문자열
        """
        error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)
        info_count = sum(1 for i in issues if i.severity == Severity.INFO)

        if score >= 90:
            quality_grade = "Excellent"
        elif score >= 75:
            quality_grade = "Good"
        elif score >= 60:
            quality_grade = "Fair"
        elif score >= 40:
            quality_grade = "Needs Improvement"
        else:
            quality_grade = "Poor"

        summary_parts = [
            f"Quality Score: {score:.1f}/100 ({quality_grade})",
            f"Files Analyzed: {total_files}",
            f"Issues Found: {len(issues)} total "
            f"({error_count} errors, {warning_count} warnings, {info_count} info)",
        ]

        if error_count > 0:
            summary_parts.append(
                "\nCritical issues require immediate attention, "
                "particularly potential security concerns."
            )

        if warning_count > 5:
            summary_parts.append(
                "\nConsider addressing the warnings to improve code maintainability."
            )

        return "\n".join(summary_parts)

    async def analyze(
        self,
        path: Path,
        exclude_patterns: list[str] | None = None,
    ) -> QualityReport:
        """코드 품질을 분석합니다.

        Args:
            path: 분석할 디렉토리 또는 파일 경로
            exclude_patterns: 제외할 파일/디렉토리 패턴

        Returns:
            QualityReport 객체
        """
        import fnmatch

        # 절대 경로로 변환
        path = path.resolve()

        # 기본 제외 패턴
        default_patterns = [
            "node_modules",
            ".git",
            "__pycache__",
            "*.pyc",
            "vendor",
            ".venv",
            "venv",
            "dist",
            "build",
            "*.min.js",
            "*.min.css",
        ]
        exclude_patterns = exclude_patterns or default_patterns

        # 분석할 파일 목록 수집
        files_to_analyze: list[Path] = []

        if path.is_file():
            files_to_analyze = [path]
        else:
            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue

                # 제외 패턴 확인
                excluded = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(file_path.name, pattern):
                        excluded = True
                        break
                    if pattern in str(file_path):
                        excluded = True
                        break

                if excluded:
                    continue

                # 코드 파일만 분석
                language = _detect_language(file_path)
                if language != "Unknown":
                    files_to_analyze.append(file_path)

        # 파일별 분석
        total_complexity = 0
        all_issues: list[QualityIssue] = []
        total_lines = 0

        for file_path in files_to_analyze:
            complexity, issues, lines = self._analyze_file(file_path)
            total_complexity += complexity
            all_issues.extend(issues)
            total_lines += lines

        # 품질 점수 계산
        score = _calculate_quality_score(total_complexity, all_issues, total_lines)

        # 요약 생성
        summary = self._generate_summary(score, all_issues, len(files_to_analyze))

        return QualityReport(
            complexity_score=total_complexity,
            issues=all_issues,
            summary=summary,
        )

    def analyze_sync(
        self,
        path: Path,
        exclude_patterns: list[str] | None = None,
    ) -> QualityReport:
        """코드 품질을 동기적으로 분석합니다.

        Args:
            path: 분석할 디렉토리 또는 파일 경로
            exclude_patterns: 제외할 파일/디렉토리 패턴

        Returns:
            QualityReport 객체
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.analyze(path, exclude_patterns)
        )

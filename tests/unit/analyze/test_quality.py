"""QualityAnalyzer 테스트."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from code_sherpa.analyze.quality import (
    LONG_FUNCTION_THRESHOLD,
    QualityAnalyzer,
    _calculate_cyclomatic_complexity,
    _calculate_quality_score,
    _detect_language,
    _find_long_functions,
    _find_pattern_issues,
)
from code_sherpa.shared.models import QualityIssue, QualityReport, Severity


class TestHelperFunctions:
    """헬퍼 함수 테스트."""

    def test_detect_language(self) -> None:
        """언어 감지."""
        assert _detect_language(Path("test.py")) == "Python"
        assert _detect_language(Path("test.js")) == "JavaScript"
        assert _detect_language(Path("test.xyz")) == "Unknown"

    def test_calculate_cyclomatic_complexity_simple(self) -> None:
        """간단한 코드 복잡도."""
        content = "print('hello')"
        complexity = _calculate_cyclomatic_complexity(content)
        assert complexity == 1  # 기본값

    def test_calculate_cyclomatic_complexity_conditionals(self) -> None:
        """조건문 복잡도."""
        content = """
if condition:
    do_something()
elif other:
    do_other()
else:
    do_default()
"""
        complexity = _calculate_cyclomatic_complexity(content)
        assert complexity > 1

    def test_calculate_cyclomatic_complexity_loops(self) -> None:
        """반복문 복잡도."""
        content = """
for item in items:
    while condition:
        process(item)
"""
        complexity = _calculate_cyclomatic_complexity(content)
        assert complexity >= 3  # 기본 + for + while

    def test_find_pattern_issues_todo(self, tmp_path: Path) -> None:
        """TODO 코멘트 감지."""
        content = "# TODO: Fix this later"
        file_path = tmp_path / "test.py"

        issues = _find_pattern_issues(content, file_path)

        todo_issues = [i for i in issues if i.issue_type == "todo_comment"]
        assert len(todo_issues) == 1
        assert todo_issues[0].severity == Severity.INFO

    def test_find_pattern_issues_fixme(self, tmp_path: Path) -> None:
        """FIXME 코멘트 감지."""
        content = "// FIXME: Critical bug"
        file_path = tmp_path / "test.js"

        issues = _find_pattern_issues(content, file_path)

        fixme_issues = [i for i in issues if i.issue_type == "fixme_comment"]
        assert len(fixme_issues) == 1
        assert fixme_issues[0].severity == Severity.WARNING

    def test_find_pattern_issues_hardcoded_password(self, tmp_path: Path) -> None:
        """하드코딩된 비밀번호 감지."""
        content = 'password = "secret123"'
        file_path = tmp_path / "test.py"

        issues = _find_pattern_issues(content, file_path)

        password_issues = [i for i in issues if i.issue_type == "hardcoded_password"]
        assert len(password_issues) == 1
        assert password_issues[0].severity == Severity.ERROR

    def test_find_pattern_issues_hardcoded_api_key(self, tmp_path: Path) -> None:
        """하드코딩된 API 키 감지."""
        content = 'api_key = "sk-123456789"'
        file_path = tmp_path / "test.py"

        issues = _find_pattern_issues(content, file_path)

        api_issues = [i for i in issues if i.issue_type == "hardcoded_secret"]
        assert len(api_issues) == 1
        assert api_issues[0].severity == Severity.ERROR

    def test_find_pattern_issues_debug_statement(self, tmp_path: Path) -> None:
        """디버그 구문 감지."""
        content = "print('debug info')"
        file_path = tmp_path / "test.py"

        issues = _find_pattern_issues(content, file_path)

        debug_issues = [i for i in issues if i.issue_type == "debug_statement"]
        assert len(debug_issues) >= 1

    def test_find_long_functions_python(self, tmp_path: Path) -> None:
        """긴 Python 함수 감지."""
        # LONG_FUNCTION_THRESHOLD + 10 라인의 함수 생성
        lines = ["def long_function():"]
        for i in range(LONG_FUNCTION_THRESHOLD + 10):
            lines.append(f"    x = {i}")

        content = "\n".join(lines)
        file_path = tmp_path / "test.py"

        issues = _find_long_functions(content, "Python", file_path)

        assert len(issues) >= 1
        assert issues[0].issue_type == "long_function"
        assert issues[0].severity == Severity.WARNING
        assert "long_function" in issues[0].message

    def test_find_long_functions_short_function(self, tmp_path: Path) -> None:
        """짧은 함수는 감지 안 함."""
        content = """
def short_function():
    x = 1
    return x
"""
        file_path = tmp_path / "test.py"

        issues = _find_long_functions(content, "Python", file_path)
        assert issues == []

    def test_calculate_quality_score_perfect(self) -> None:
        """완벽한 코드 점수."""
        score = _calculate_quality_score(
            complexity=5,
            issues=[],
            total_lines=100,
        )
        assert score >= 90

    def test_calculate_quality_score_with_errors(self) -> None:
        """에러 있는 코드 점수."""
        issues = [
            QualityIssue(
                path=Path("test.py"),
                line=1,
                issue_type="error",
                message="Error",
                severity=Severity.ERROR,
            )
            for _ in range(5)
        ]

        score = _calculate_quality_score(
            complexity=10,
            issues=issues,
            total_lines=100,
        )
        assert score < 90  # 에러로 인해 감점

    def test_calculate_quality_score_empty_file(self) -> None:
        """빈 파일은 100점."""
        score = _calculate_quality_score(
            complexity=0,
            issues=[],
            total_lines=0,
        )
        assert score == 100.0


class TestQualityAnalyzer:
    """QualityAnalyzer 테스트."""

    def test_init_default(self) -> None:
        """기본 초기화."""
        analyzer = QualityAnalyzer()
        assert analyzer._llm is None
        assert analyzer._max_file_size_kb == 500

    def test_init_with_llm(self) -> None:
        """LLM과 함께 초기화."""
        mock_llm = MagicMock()
        analyzer = QualityAnalyzer(llm=mock_llm)
        assert analyzer._llm == mock_llm

    @pytest.mark.asyncio
    async def test_analyze_returns_quality_report(self, tmp_path: Path) -> None:
        """analyze()가 QualityReport 반환."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(tmp_path)

        assert isinstance(result, QualityReport)
        assert result.complexity_score >= 0
        assert isinstance(result.issues, list)
        assert isinstance(result.summary, str)

    @pytest.mark.asyncio
    async def test_analyze_single_file(self, tmp_path: Path) -> None:
        """단일 파일 분석."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# TODO: implement\nprint('hello')\n")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(test_file)

        assert isinstance(result, QualityReport)
        # TODO 이슈가 감지되어야 함
        todo_issues = [i for i in result.issues if i.issue_type == "todo_comment"]
        assert len(todo_issues) >= 1

    @pytest.mark.asyncio
    async def test_analyze_directory(self, tmp_path: Path) -> None:
        """디렉토리 분석."""
        (tmp_path / "main.py").write_text("print('hello')\n")
        (tmp_path / "utils.py").write_text("def helper(): pass\n")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(tmp_path)

        assert isinstance(result, QualityReport)
        assert "Files Analyzed" in result.summary

    @pytest.mark.asyncio
    async def test_analyze_with_exclude_patterns(self, tmp_path: Path) -> None:
        """제외 패턴 적용."""
        (tmp_path / "main.py").write_text("print('hello')\n")

        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.js").write_text("// TODO: fix")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(tmp_path, exclude_patterns=["node_modules"])

        # node_modules의 TODO가 감지되지 않아야 함
        for issue in result.issues:
            assert "node_modules" not in str(issue.path)

    @pytest.mark.asyncio
    async def test_analyze_detects_security_issues(self, tmp_path: Path) -> None:
        """보안 이슈 감지."""
        test_file = tmp_path / "config.py"
        test_file.write_text('PASSWORD = "supersecret"\n')

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(test_file)

        # 하드코딩된 비밀번호 감지
        password_issues = [
            i for i in result.issues if i.issue_type == "hardcoded_password"
        ]
        assert len(password_issues) >= 1
        assert password_issues[0].severity == Severity.ERROR

    @pytest.mark.asyncio
    async def test_analyze_calculates_complexity(self, tmp_path: Path) -> None:
        """복잡도 계산."""
        test_file = tmp_path / "complex.py"
        test_file.write_text("""
def complex_function():
    if condition:
        if nested:
            for item in items:
                while running:
                    process()
""")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(test_file)

        # 복잡도가 1보다 커야 함 (조건문, 반복문)
        assert result.complexity_score > 1

    @pytest.mark.asyncio
    async def test_analyze_generates_summary(self, tmp_path: Path) -> None:
        """요약 생성."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(test_file)

        assert result.summary != ""
        assert "Quality Score" in result.summary

    def test_analyze_sync(self, tmp_path: Path) -> None:
        """analyze_sync() 동기 호출."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        analyzer = QualityAnalyzer()
        result = analyzer.analyze_sync(test_file)

        assert isinstance(result, QualityReport)

    @pytest.mark.asyncio
    async def test_analyze_skips_non_code_files(self, tmp_path: Path) -> None:
        """코드가 아닌 파일 건너뛰기."""
        (tmp_path / "readme.txt").write_text("Just text")
        (tmp_path / "main.py").write_text("print('hello')")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(tmp_path)

        # Unknown 언어 파일의 이슈가 없어야 함
        for issue in result.issues:
            assert issue.path.suffix != ".txt"

    @pytest.mark.asyncio
    async def test_analyze_skips_large_files(self, tmp_path: Path) -> None:
        """큰 파일 건너뛰기."""
        large_file = tmp_path / "large.py"
        # 2KB 파일 생성
        large_file.write_text("x = 1\n" * 500)

        analyzer = QualityAnalyzer(max_file_size_kb=1)  # 1KB 제한
        result = await analyzer.analyze(tmp_path)

        # large.py의 이슈가 없어야 함
        for issue in result.issues:
            assert issue.path.name != "large.py"

    @pytest.mark.asyncio
    async def test_analyze_empty_directory(self, tmp_path: Path) -> None:
        """빈 디렉토리 분석."""
        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(tmp_path)

        assert isinstance(result, QualityReport)
        assert result.issues == []
        assert "Files Analyzed: 0" in result.summary

    @pytest.mark.asyncio
    async def test_analyze_quality_grades(self, tmp_path: Path) -> None:
        """품질 등급 확인."""
        # 깨끗한 코드
        test_file = tmp_path / "clean.py"
        test_file.write_text("def clean(): return 1\n")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(test_file)

        # Excellent 또는 Good 등급이어야 함
        assert "Excellent" in result.summary or "Good" in result.summary

    @pytest.mark.asyncio
    async def test_analyze_issue_line_numbers(self, tmp_path: Path) -> None:
        """이슈 라인 번호 확인."""
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\n# TODO: fix\nline4\n")

        analyzer = QualityAnalyzer()
        result = await analyzer.analyze(test_file)

        todo_issues = [i for i in result.issues if i.issue_type == "todo_comment"]
        if todo_issues:
            assert todo_issues[0].line == 3  # TODO는 3번째 줄

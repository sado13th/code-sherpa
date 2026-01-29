"""FileExplainer 테스트."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_sherpa.analyze.file_explainer import (
    FileExplainer,
    _count_lines,
    _detect_language,
    _extract_key_elements_from_response,
    _extract_purpose_from_response,
)
from code_sherpa.shared.models import FileExplanation


class TestHelperFunctions:
    """헬퍼 함수 테스트."""

    def test_detect_language_python(self) -> None:
        """Python 파일 언어 감지."""
        assert _detect_language(Path("test.py")) == "Python"

    def test_detect_language_javascript(self) -> None:
        """JavaScript 파일 언어 감지."""
        assert _detect_language(Path("test.js")) == "JavaScript"

    def test_detect_language_typescript(self) -> None:
        """TypeScript 파일 언어 감지."""
        assert _detect_language(Path("test.ts")) == "TypeScript"

    def test_detect_language_makefile(self) -> None:
        """Makefile 언어 감지."""
        assert _detect_language(Path("Makefile")) == "Makefile"

    def test_detect_language_dockerfile(self) -> None:
        """Dockerfile 언어 감지."""
        assert _detect_language(Path("Dockerfile")) == "Dockerfile"

    def test_detect_language_unknown(self) -> None:
        """알 수 없는 확장자."""
        assert _detect_language(Path("test.xyz")) == "Unknown"

    def test_count_lines(self) -> None:
        """라인 수 계산."""
        assert _count_lines("line1\nline2\nline3") == 3

    def test_count_lines_empty(self) -> None:
        """빈 문자열 라인 수."""
        assert _count_lines("") == 0

    def test_extract_purpose_from_response(self) -> None:
        """응답에서 Purpose 추출."""
        response = """### Purpose
This file handles user authentication.

### Key Elements
- UserAuth class
"""
        result = _extract_purpose_from_response(response)
        assert "user authentication" in result.lower()

    def test_extract_purpose_fallback_to_first_paragraph(self) -> None:
        """Purpose 섹션 없으면 첫 문단 반환."""
        response = """This is the main entry point.

It handles all requests."""
        result = _extract_purpose_from_response(response)
        assert "main entry point" in result

    def test_extract_key_elements_from_response(self) -> None:
        """응답에서 Key Elements 추출."""
        response = """### Purpose
Test purpose.

### Key Elements
- Class: UserAuth
- Function: authenticate()
- Constant: MAX_RETRIES

### Detailed Explanation
More details here.
"""
        result = _extract_key_elements_from_response(response)
        assert len(result) == 3
        assert "Class: UserAuth" in result
        assert "Function: authenticate()" in result

    def test_extract_key_elements_empty(self) -> None:
        """Key Elements 섹션 없으면 빈 목록."""
        response = "Just some text without sections."
        result = _extract_key_elements_from_response(response)
        assert result == []


class TestFileExplainer:
    """FileExplainer 테스트."""

    def test_init_default(self) -> None:
        """기본 초기화."""
        explainer = FileExplainer()
        assert explainer._llm is None
        assert explainer._max_file_size_kb == 500

    def test_init_with_llm(self) -> None:
        """LLM과 함께 초기화."""
        mock_llm = MagicMock()
        explainer = FileExplainer(llm=mock_llm)
        assert explainer._llm == mock_llm

    def test_init_with_custom_max_size(self) -> None:
        """커스텀 최대 파일 크기."""
        explainer = FileExplainer(max_file_size_kb=1000)
        assert explainer._max_file_size_kb == 1000

    @pytest.mark.asyncio
    async def test_explain_returns_file_explanation(self, tmp_path: Path) -> None:
        """explain()이 FileExplanation 반환."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    print('Hello')\n")

        mock_llm = MagicMock()
        mock_llm.complete.return_value = """### Purpose
A simple greeting function.

### Key Elements
- Function: hello()
"""

        explainer = FileExplainer(llm=mock_llm)
        result = await explainer.explain(test_file)

        assert isinstance(result, FileExplanation)
        assert result.path == test_file
        assert result.language == "Python"
        assert result.lines == 2

    @pytest.mark.asyncio
    async def test_explain_detects_language(self, tmp_path: Path) -> None:
        """explain()이 언어 감지."""
        js_file = tmp_path / "app.js"
        js_file.write_text("const x = 1;\n")

        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Explanation"

        explainer = FileExplainer(llm=mock_llm)
        result = await explainer.explain(js_file)

        assert result.language == "JavaScript"

    @pytest.mark.asyncio
    async def test_explain_file_not_found(self, tmp_path: Path) -> None:
        """존재하지 않는 파일."""
        nonexistent = tmp_path / "nonexistent.py"

        explainer = FileExplainer()
        with pytest.raises(FileNotFoundError):
            await explainer.explain(nonexistent)

    @pytest.mark.asyncio
    async def test_explain_file_too_large(self, tmp_path: Path) -> None:
        """파일 크기 초과."""
        large_file = tmp_path / "large.py"
        # 1KB 이상의 콘텐츠 생성
        large_file.write_text("x" * 2000)

        explainer = FileExplainer(max_file_size_kb=1)  # 1KB 제한
        with pytest.raises(ValueError) as exc_info:
            await explainer.explain(large_file)

        assert "제한을 초과" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_explain_calls_llm_with_prompt(self, tmp_path: Path) -> None:
        """explain()이 프롬프트로 LLM 호출."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Explanation"

        explainer = FileExplainer(llm=mock_llm)
        await explainer.explain(test_file)

        mock_llm.complete.assert_called_once()
        prompt = mock_llm.complete.call_args[0][0]
        assert "test.py" in prompt or "Python" in prompt

    def test_explain_sync(self, tmp_path: Path) -> None:
        """explain_sync() 동기 호출."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Explanation"

        explainer = FileExplainer(llm=mock_llm)
        result = explainer.explain_sync(test_file)

        assert isinstance(result, FileExplanation)

    @pytest.mark.asyncio
    async def test_explain_extracts_purpose(self, tmp_path: Path) -> None:
        """explain()이 purpose 추출."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        mock_llm = MagicMock()
        mock_llm.complete.return_value = """### Purpose
This handles authentication.

### Key Elements
- Class: Auth
"""

        explainer = FileExplainer(llm=mock_llm)
        result = await explainer.explain(test_file)

        assert "authentication" in result.purpose.lower()

    @pytest.mark.asyncio
    async def test_explain_extracts_key_elements(self, tmp_path: Path) -> None:
        """explain()이 key_elements 추출."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        mock_llm = MagicMock()
        mock_llm.complete.return_value = """### Purpose
Test purpose.

### Key Elements
- Class: UserModel
- Function: validate()
"""

        explainer = FileExplainer(llm=mock_llm)
        result = await explainer.explain(test_file)

        assert len(result.key_elements) == 2
        assert "Class: UserModel" in result.key_elements

    @pytest.mark.asyncio
    async def test_lazy_llm_initialization(self, tmp_path: Path) -> None:
        """LLM이 지연 초기화되는지 확인."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        with patch("code_sherpa.analyze.file_explainer.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.complete.return_value = "Explanation"
            mock_get_llm.return_value = mock_llm

            explainer = FileExplainer()  # LLM 없이 초기화
            assert explainer._llm is None

            await explainer.explain(test_file)

            mock_get_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_explain_with_non_utf8_file(self, tmp_path: Path) -> None:
        """UTF-8이 아닌 파일 처리."""
        test_file = tmp_path / "test.py"
        # Latin-1 인코딩 문자
        test_file.write_bytes(b"# Comment with \xe9\n")

        mock_llm = MagicMock()
        mock_llm.complete.return_value = "Explanation"

        explainer = FileExplainer(llm=mock_llm)
        result = await explainer.explain(test_file)

        assert isinstance(result, FileExplanation)

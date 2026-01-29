"""파일 설명 분석 모듈."""

import re
from pathlib import Path

from code_sherpa.prompts import load_prompt
from code_sherpa.shared.git import EXTENSION_LANGUAGE_MAP
from code_sherpa.shared.llm import BaseLLM, get_llm
from code_sherpa.shared.models import FileExplanation


def _detect_language(file_path: Path) -> str:
    """파일 확장자로 언어를 감지합니다.

    Args:
        file_path: 파일 경로

    Returns:
        언어 이름
    """
    ext = file_path.suffix.lower()

    # 확장자 없는 특수 파일 처리
    if not ext:
        name = file_path.name.lower()
        if name == "makefile":
            return "Makefile"
        elif name == "dockerfile":
            return "Dockerfile"
        elif name in ("gemfile", "rakefile"):
            return "Ruby"
        elif name in (".bashrc", ".bash_profile", ".zshrc"):
            return "Shell"

    return EXTENSION_LANGUAGE_MAP.get(ext, "Unknown")


def _count_lines(content: str) -> int:
    """문자열의 라인 수를 계산합니다.

    Args:
        content: 파일 내용

    Returns:
        라인 수
    """
    if not content:
        return 0
    return len(content.splitlines())


def _extract_key_elements_from_response(response: str) -> list[str]:
    """LLM 응답에서 핵심 요소 목록을 추출합니다.

    Args:
        response: LLM 응답 문자열

    Returns:
        핵심 요소 목록
    """
    elements: list[str] = []

    # "Key Elements" 섹션 찾기
    key_elements_match = re.search(
        r"(?:###?\s*)?Key Elements\s*\n(.*?)(?=\n###?\s|\n\n###?|\Z)",
        response,
        re.IGNORECASE | re.DOTALL,
    )

    if key_elements_match:
        section = key_elements_match.group(1)
        # 불릿 포인트 추출
        bullets = re.findall(r"^\s*[-*]\s*(.+)$", section, re.MULTILINE)
        elements.extend([b.strip() for b in bullets if b.strip()])

    return elements


def _extract_purpose_from_response(response: str) -> str:
    """LLM 응답에서 목적(Purpose) 섹션을 추출합니다.

    Args:
        response: LLM 응답 문자열

    Returns:
        목적 설명
    """
    # "Purpose" 섹션 찾기
    purpose_match = re.search(
        r"(?:###?\s*)?Purpose\s*\n(.*?)(?=\n###?\s|\n\n###?|\Z)",
        response,
        re.IGNORECASE | re.DOTALL,
    )

    if purpose_match:
        return purpose_match.group(1).strip()

    # Purpose 섹션이 없으면 첫 문단 반환
    paragraphs = response.strip().split("\n\n")
    if paragraphs:
        return paragraphs[0].strip()

    return ""


class FileExplainer:
    """파일 설명 생성기.

    소스 코드 파일을 분석하여 목적, 핵심 요소, 상세 설명을
    포함한 설명을 생성합니다.
    """

    def __init__(
        self,
        llm: BaseLLM | None = None,
        max_file_size_kb: int = 500,
    ) -> None:
        """FileExplainer를 초기화합니다.

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

    def _read_file_content(self, file_path: Path) -> str:
        """파일 내용을 읽습니다.

        Args:
            file_path: 파일 경로

        Returns:
            파일 내용

        Raises:
            FileNotFoundError: 파일이 존재하지 않는 경우
            ValueError: 파일 크기가 제한을 초과하는 경우
        """
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        # 파일 크기 확인
        file_size_kb = file_path.stat().st_size / 1024
        if file_size_kb > self._max_file_size_kb:
            raise ValueError(
                f"파일 크기가 제한을 초과합니다: {file_size_kb:.1f}KB > "
                f"{self._max_file_size_kb}KB"
            )

        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # UTF-8 실패 시 latin-1로 시도
            return file_path.read_text(encoding="latin-1")

    async def explain(self, file_path: Path) -> FileExplanation:
        """파일을 분석하여 설명을 생성합니다.

        Args:
            file_path: 분석할 파일 경로

        Returns:
            FileExplanation 객체

        Raises:
            FileNotFoundError: 파일이 존재하지 않는 경우
            ValueError: 파일 크기가 제한을 초과하는 경우
        """
        # 절대 경로로 변환
        file_path = file_path.resolve()

        # 파일 읽기
        content = self._read_file_content(file_path)
        lines = _count_lines(content)

        # 언어 감지
        language = _detect_language(file_path)

        # LLM으로 설명 생성
        llm = self._get_llm()
        prompt = load_prompt(
            "analyze/file_explain",
            file_path=str(file_path),
            language=language,
            lines=lines,
            content=content,
        )
        response = llm.complete(prompt)

        # 응답에서 구조화된 정보 추출
        purpose = _extract_purpose_from_response(response)
        key_elements = _extract_key_elements_from_response(response)

        return FileExplanation(
            path=file_path,
            language=language,
            lines=lines,
            purpose=purpose,
            key_elements=key_elements,
            explanation=response,
        )

    def explain_sync(self, file_path: Path) -> FileExplanation:
        """파일을 동기적으로 분석하여 설명을 생성합니다.

        async 환경이 아닐 때 사용합니다.

        Args:
            file_path: 분석할 파일 경로

        Returns:
            FileExplanation 객체
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.explain(file_path))

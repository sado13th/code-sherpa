"""리뷰 에이전트 베이스 클래스."""

import json
import logging
from abc import ABC, abstractmethod

from code_sherpa.prompts import load_prompt
from code_sherpa.shared.llm import BaseLLM, get_llm
from code_sherpa.shared.models import AgentReview, ParsedDiff, ReviewComment, Severity

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """리뷰 에이전트 베이스 클래스.

    모든 리뷰 에이전트는 이 클래스를 상속해야 합니다.
    각 에이전트는 특정 관점(보안, 성능, 아키텍처 등)에서 코드를 리뷰합니다.
    """

    name: str  # 에이전트 이름 (예: "architect", "security")
    description: str  # 에이전트 설명
    prompt_name: str  # 프롬프트 파일 이름 (예: "review/architect")

    def __init__(self, llm: BaseLLM | None = None) -> None:
        """에이전트 초기화.

        Args:
            llm: 사용할 LLM 인스턴스. None이면 기본 LLM 사용.
        """
        self.llm = llm or get_llm()

    @abstractmethod
    async def review(
        self, diff: ParsedDiff, context: dict | None = None
    ) -> AgentReview:
        """diff를 리뷰하여 AgentReview 반환.

        Args:
            diff: 파싱된 diff 정보
            context: 추가 컨텍스트 (파일 내용, 프로젝트 정보 등)

        Returns:
            에이전트 리뷰 결과
        """
        ...

    def _build_prompt(self, diff: ParsedDiff, context: dict | None = None) -> str:
        """리뷰 프롬프트 생성.

        Args:
            diff: 파싱된 diff 정보
            context: 추가 컨텍스트

        Returns:
            포맷된 프롬프트 문자열
        """
        # diff 텍스트 구성
        diff_text = diff.raw if diff.raw else self._format_diff(diff)

        # 파일 컨텍스트 구성
        file_context = ""
        if context and "files" in context:
            file_context = self._format_file_context(context["files"])

        return load_prompt(
            self.prompt_name,
            diff=diff_text,
            file_context=file_context or "No additional file context provided.",
        )

    def _format_diff(self, diff: ParsedDiff) -> str:
        """ParsedDiff를 텍스트 형식으로 변환.

        Args:
            diff: 파싱된 diff 정보

        Returns:
            diff 텍스트
        """
        lines = []
        for file_diff in diff.files:
            lines.append(f"--- a/{file_diff.path}")
            lines.append(f"+++ b/{file_diff.path}")
            for hunk in file_diff.hunks:
                lines.append(
                    f"@@ -{hunk.old_start},{hunk.old_count} "
                    f"+{hunk.new_start},{hunk.new_count} @@"
                )
                lines.append(hunk.content)
        return "\n".join(lines)

    def _format_file_context(self, files: dict[str, str]) -> str:
        """파일 컨텍스트를 포맷.

        Args:
            files: 파일 경로와 내용 매핑

        Returns:
            포맷된 파일 컨텍스트
        """
        lines = []
        for path, content in files.items():
            lines.append(f"### {path}")
            lines.append("```")
            lines.append(content)
            lines.append("```")
            lines.append("")
        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> list[ReviewComment]:
        """LLM 응답을 ReviewComment 리스트로 파싱.

        Args:
            response: LLM 응답 문자열

        Returns:
            파싱된 ReviewComment 리스트
        """
        comments = []

        # JSON 블록 추출 시도
        json_content = self._extract_json(response)

        if json_content:
            try:
                data = json.loads(json_content)
                if isinstance(data, list):
                    for item in data:
                        comment = self._parse_comment_dict(item)
                        if comment:
                            comments.append(comment)
                elif isinstance(data, dict) and "comments" in data:
                    for item in data["comments"]:
                        comment = self._parse_comment_dict(item)
                        if comment:
                            comments.append(comment)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패: {e}")
                # JSON 파싱 실패 시 텍스트 파싱 시도
                comments = self._parse_text_response(response)
        else:
            # JSON이 없으면 텍스트 파싱
            comments = self._parse_text_response(response)

        return comments

    def _extract_json(self, text: str) -> str | None:
        """텍스트에서 JSON 블록 추출.

        Args:
            text: 원본 텍스트

        Returns:
            JSON 문자열 또는 None
        """
        # ```json ... ``` 블록 찾기
        import re

        json_pattern = r"```json\s*([\s\S]*?)\s*```"
        match = re.search(json_pattern, text)
        if match:
            return match.group(1).strip()

        # [ ... ] 또는 { ... } 직접 찾기
        text = text.strip()
        if text.startswith("[") or text.startswith("{"):
            return text

        return None

    def _parse_comment_dict(self, item: dict) -> ReviewComment | None:
        """딕셔너리를 ReviewComment로 변환.

        Args:
            item: 코멘트 딕셔너리

        Returns:
            ReviewComment 또는 None
        """
        try:
            severity_str = item.get("severity", "INFO").upper()
            if severity_str in Severity.__members__:
                severity = Severity[severity_str]
            else:
                severity = Severity.INFO

            return ReviewComment(
                agent=self.name,
                file=item.get("file", "unknown"),
                line=item.get("line"),
                severity=severity,
                category=item.get("category", "general"),
                message=item.get("message", ""),
                suggestion=item.get("suggestion"),
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"코멘트 파싱 실패: {e}")
            return None

    def _parse_text_response(self, response: str) -> list[ReviewComment]:
        """텍스트 형식의 응답을 파싱.

        구조화되지 않은 응답에서 리뷰 코멘트를 추출합니다.

        Args:
            response: 텍스트 응답

        Returns:
            ReviewComment 리스트
        """
        # 기본 구현: 전체 응답을 하나의 코멘트로 처리
        if response.strip():
            return [
                ReviewComment(
                    agent=self.name,
                    file="general",
                    line=None,
                    severity=Severity.INFO,
                    category="general",
                    message=response.strip(),
                    suggestion=None,
                )
            ]
        return []

    def _extract_summary(self, response: str) -> str:
        """응답에서 요약 추출.

        Args:
            response: LLM 응답

        Returns:
            요약 문자열
        """
        # JSON에서 summary 필드 찾기
        json_content = self._extract_json(response)
        if json_content:
            try:
                data = json.loads(json_content)
                if isinstance(data, dict) and "summary" in data:
                    return data["summary"]
            except json.JSONDecodeError:
                pass

        # 텍스트에서 Summary 섹션 찾기
        import re

        summary_pattern = r"(?:^|\n)(?:##?\s*)?Summary:?\s*([\s\S]*?)(?:\n##|\n\n|$)"
        match = re.search(summary_pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return ""

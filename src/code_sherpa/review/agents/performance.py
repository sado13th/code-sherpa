"""성능 리뷰 에이전트."""

import logging

from code_sherpa.shared.llm import BaseLLM
from code_sherpa.shared.models import AgentReview, ParsedDiff

from .base import BaseAgent

logger = logging.getLogger(__name__)


class PerformanceAgent(BaseAgent):
    """성능 리뷰 에이전트.

    알고리즘 복잡도, 메모리 사용, I/O 최적화, 캐싱 등
    성능 관점에서 코드를 리뷰합니다.
    """

    name = "performance"
    description = "알고리즘 복잡도, 메모리 사용, I/O 최적화, 캐싱 리뷰"
    prompt_name = "review/performance"

    def __init__(self, llm: BaseLLM | None = None) -> None:
        """에이전트 초기화.

        Args:
            llm: 사용할 LLM 인스턴스. None이면 기본 LLM 사용.
        """
        super().__init__(llm)

    async def review(
        self, diff: ParsedDiff, context: dict | None = None
    ) -> AgentReview:
        """diff를 성능 관점에서 리뷰.

        Args:
            diff: 파싱된 diff 정보
            context: 추가 컨텍스트 (파일 내용, 프로젝트 정보 등)

        Returns:
            성능 리뷰 결과
        """
        logger.info(f"[{self.name}] 성능 리뷰 시작")

        # 프롬프트 생성
        prompt = self._build_prompt(diff, context)

        # LLM 호출
        try:
            response = self.llm.complete(prompt)
            logger.debug(f"[{self.name}] LLM 응답 수신")
        except Exception as e:
            logger.error(f"[{self.name}] LLM 호출 실패: {e}")
            return AgentReview(
                agent_name=self.name,
                comments=[],
                summary=f"리뷰 실패: {e}",
            )

        # 응답 파싱
        comments = self._parse_llm_response(response)
        summary = self._extract_summary(response)

        logger.info(f"[{self.name}] 리뷰 완료: {len(comments)}개 코멘트")

        return AgentReview(
            agent_name=self.name,
            comments=comments,
            summary=summary or self._generate_default_summary(comments),
        )

    def _generate_default_summary(self, comments: list) -> str:
        """기본 요약 생성.

        Args:
            comments: 리뷰 코멘트 목록

        Returns:
            요약 문자열
        """
        if not comments:
            return "성능 관점에서 특별한 이슈가 발견되지 않았습니다."

        error_count = sum(1 for c in comments if c.severity.value == "error")
        warning_count = sum(1 for c in comments if c.severity.value == "warning")
        info_count = sum(1 for c in comments if c.severity.value == "info")

        parts = []
        if error_count:
            parts.append(f"심각한 성능 이슈 {error_count}건")
        if warning_count:
            parts.append(f"성능 주의 {warning_count}건")
        if info_count:
            parts.append(f"최적화 제안 {info_count}건")

        return f"성능 리뷰 결과: {', '.join(parts)}"

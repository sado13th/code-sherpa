"""Review Runner - Multi-Agent 리뷰 실행기."""

import asyncio
import logging
from pathlib import Path

from code_sherpa.prompts import load_prompt
from code_sherpa.shared.git import GitClient
from code_sherpa.shared.llm import BaseLLM, get_llm
from code_sherpa.shared.models import (
    AgentReview,
    DiffStats,
    ParsedDiff,
    ReviewResult,
)

from .agents import BaseAgent, get_agent, get_available_agents
from .diff_parser import DiffParser

logger = logging.getLogger(__name__)


class ReviewRunner:
    """Multi-Agent 코드 리뷰 실행기.

    여러 에이전트를 사용하여 코드 변경사항을 리뷰하고
    결과를 종합합니다.
    """

    def __init__(
        self,
        agents: list[str] | None = None,
        llm: BaseLLM | None = None,
        parallel: bool = True,
    ) -> None:
        """ReviewRunner 초기화.

        Args:
            agents: 사용할 에이전트 이름 목록. None이면 기본 에이전트 사용.
            llm: 사용할 LLM 인스턴스. None이면 기본 LLM 사용.
            parallel: True면 에이전트를 병렬로 실행.
        """
        self.agent_names = agents or ["architect", "security"]
        self.llm = llm
        self.parallel = parallel
        self._diff_parser = DiffParser()
        self._agents: list[BaseAgent] | None = None

    @property
    def agents(self) -> list[BaseAgent]:
        """에이전트 인스턴스 목록."""
        if self._agents is None:
            self._agents = [get_agent(name, self.llm) for name in self.agent_names]
        return self._agents

    async def review(
        self,
        path: str | Path = ".",
        staged: bool = False,
        commit_range: str | None = None,
        context: dict | None = None,
    ) -> ReviewResult:
        """코드 변경사항을 리뷰합니다.

        Args:
            path: Git 저장소 경로.
            staged: True면 staged 변경사항만 리뷰.
            commit_range: 리뷰할 커밋 범위 (예: "HEAD~3..HEAD").
            context: 추가 컨텍스트 정보.

        Returns:
            ReviewResult 객체.
        """
        # Git diff 가져오기
        git = GitClient(path)
        diff_text = git.get_diff(staged=staged, commit_range=commit_range)

        if not diff_text.strip():
            return self._empty_result()

        # Diff 파싱
        parsed_diff = self._diff_parser.parse(diff_text)

        # 에이전트 리뷰 실행
        if self.parallel:
            agent_reviews = await self._run_parallel(parsed_diff, context)
        else:
            agent_reviews = await self._run_sequential(parsed_diff, context)

        # 결과 종합
        return self._aggregate_results(parsed_diff, agent_reviews)

    def review_sync(
        self,
        path: str | Path = ".",
        staged: bool = False,
        commit_range: str | None = None,
        context: dict | None = None,
    ) -> ReviewResult:
        """review()의 동기 버전."""
        return asyncio.run(self.review(path, staged, commit_range, context))

    async def review_diff(
        self,
        diff_text: str,
        context: dict | None = None,
    ) -> ReviewResult:
        """diff 텍스트를 직접 리뷰합니다.

        Args:
            diff_text: Git diff 텍스트.
            context: 추가 컨텍스트 정보.

        Returns:
            ReviewResult 객체.
        """
        if not diff_text.strip():
            return self._empty_result()

        parsed_diff = self._diff_parser.parse(diff_text)

        if self.parallel:
            agent_reviews = await self._run_parallel(parsed_diff, context)
        else:
            agent_reviews = await self._run_sequential(parsed_diff, context)

        return self._aggregate_results(parsed_diff, agent_reviews)

    async def _run_parallel(
        self,
        diff: ParsedDiff,
        context: dict | None,
    ) -> list[AgentReview]:
        """에이전트를 병렬로 실행.

        Args:
            diff: 파싱된 diff.
            context: 추가 컨텍스트.

        Returns:
            AgentReview 리스트.
        """
        tasks = [agent.review(diff, context) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        agent_reviews = []
        for result, agent in zip(results, self.agents):
            if isinstance(result, Exception):
                logger.error(f"에이전트 {agent.name} 리뷰 실패: {result}")
                # 실패한 에이전트는 빈 리뷰로 처리
                agent_reviews.append(
                    AgentReview(
                        agent_name=agent.name,
                        comments=[],
                        summary=f"리뷰 실행 중 오류 발생: {result}",
                    )
                )
            else:
                agent_reviews.append(result)

        return agent_reviews

    async def _run_sequential(
        self,
        diff: ParsedDiff,
        context: dict | None,
    ) -> list[AgentReview]:
        """에이전트를 순차적으로 실행.

        Args:
            diff: 파싱된 diff.
            context: 추가 컨텍스트.

        Returns:
            AgentReview 리스트.
        """
        agent_reviews = []
        for agent in self.agents:
            try:
                review = await agent.review(diff, context)
                agent_reviews.append(review)
            except Exception as e:
                logger.error(f"에이전트 {agent.name} 리뷰 실패: {e}")
                agent_reviews.append(
                    AgentReview(
                        agent_name=agent.name,
                        comments=[],
                        summary=f"리뷰 실행 중 오류 발생: {e}",
                    )
                )

        return agent_reviews

    def _aggregate_results(
        self,
        diff: ParsedDiff,
        agent_reviews: list[AgentReview],
    ) -> ReviewResult:
        """에이전트 리뷰 결과를 종합.

        Args:
            diff: 파싱된 diff.
            agent_reviews: 에이전트 리뷰 목록.

        Returns:
            종합된 ReviewResult.
        """
        # 전체 코멘트 수
        total_comments = sum(len(r.comments) for r in agent_reviews)

        # 심각도별 집계
        by_severity: dict[str, int] = {}
        for review in agent_reviews:
            for comment in review.comments:
                severity_key = comment.severity.value
                by_severity[severity_key] = by_severity.get(severity_key, 0) + 1

        return ReviewResult(
            diff_summary=diff.stats,
            agent_reviews=agent_reviews,
            total_comments=total_comments,
            by_severity=by_severity,
            summary="",  # Summarizer가 채움
        )

    def _empty_result(self) -> ReviewResult:
        """빈 결과 반환."""
        return ReviewResult(
            diff_summary=DiffStats(
                files_changed=0,
                total_additions=0,
                total_deletions=0,
            ),
            agent_reviews=[],
            total_comments=0,
            by_severity={},
            summary="리뷰할 변경사항이 없습니다.",
        )

    @staticmethod
    def list_available_agents() -> list[str]:
        """사용 가능한 에이전트 목록."""
        return get_available_agents()


class ReviewSummarizer:
    """리뷰 결과 종합기.

    여러 에이전트의 리뷰 결과를 종합하여
    하나의 요약을 생성합니다.
    """

    def __init__(self, llm: BaseLLM | None = None) -> None:
        """ReviewSummarizer 초기화.

        Args:
            llm: 사용할 LLM 인스턴스. None이면 기본 LLM 사용.
        """
        self._llm = llm

    @property
    def llm(self) -> BaseLLM:
        """LLM 인스턴스 (lazy initialization)."""
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    async def summarize(self, result: ReviewResult) -> ReviewResult:
        """리뷰 결과를 종합합니다.

        Args:
            result: 종합할 ReviewResult.

        Returns:
            요약이 추가된 ReviewResult.
        """
        if not result.agent_reviews:
            return result

        # 프롬프트 생성
        prompt = self._build_prompt(result)

        # LLM으로 요약 생성
        try:
            summary = self.llm.chat([{"role": "user", "content": prompt}])
            result.summary = summary.strip()
        except Exception as e:
            logger.error(f"요약 생성 실패: {e}")
            result.summary = self._generate_fallback_summary(result)

        return result

    def summarize_sync(self, result: ReviewResult) -> ReviewResult:
        """summarize()의 동기 버전."""
        return asyncio.run(self.summarize(result))

    def _build_prompt(self, result: ReviewResult) -> str:
        """요약 프롬프트 생성.

        Args:
            result: 리뷰 결과.

        Returns:
            프롬프트 문자열.
        """
        # 에이전트 리뷰 포맷팅
        agent_reviews_text = self._format_agent_reviews(result.agent_reviews)

        return load_prompt(
            "review/summary",
            files_changed=result.diff_summary.files_changed,
            additions=result.diff_summary.total_additions,
            deletions=result.diff_summary.total_deletions,
            agent_reviews=agent_reviews_text,
        )

    def _format_agent_reviews(self, reviews: list[AgentReview]) -> str:
        """에이전트 리뷰를 텍스트로 포맷.

        Args:
            reviews: 에이전트 리뷰 목록.

        Returns:
            포맷된 텍스트.
        """
        lines = []

        for review in reviews:
            lines.append(f"### {review.agent_name}")
            lines.append("")

            if review.comments:
                for comment in review.comments:
                    severity_label = f"[{comment.severity.value.upper()}]"
                    location = f"{comment.file}"
                    if comment.line:
                        location += f":{comment.line}"

                    lines.append(f"- {severity_label} {location}")
                    lines.append(f"  {comment.message}")
                    if comment.suggestion:
                        lines.append(f"  Suggestion: {comment.suggestion}")
                    lines.append("")
            else:
                lines.append("*No issues found.*")
                lines.append("")

            if review.summary:
                lines.append(f"**Summary**: {review.summary}")
                lines.append("")

        return "\n".join(lines)

    def _generate_fallback_summary(self, result: ReviewResult) -> str:
        """LLM 실패 시 폴백 요약 생성.

        Args:
            result: 리뷰 결과.

        Returns:
            폴백 요약 문자열.
        """
        total = result.total_comments
        errors = result.by_severity.get("error", 0)
        warnings = result.by_severity.get("warning", 0)
        infos = result.by_severity.get("info", 0)

        parts = [f"총 {total}개의 코멘트가 발견되었습니다."]

        if errors:
            parts.append(f"- ERROR: {errors}개")
        if warnings:
            parts.append(f"- WARNING: {warnings}개")
        if infos:
            parts.append(f"- INFO: {infos}개")

        if errors > 0:
            parts.append("\n병합 전 ERROR 이슈를 해결해야 합니다.")
        elif warnings > 0:
            parts.append("\nWARNING 이슈를 검토하는 것이 좋습니다.")
        else:
            parts.append("\n특별한 이슈 없이 병합 가능합니다.")

        return "\n".join(parts)


async def run_review(
    path: str | Path = ".",
    staged: bool = False,
    commit_range: str | None = None,
    agents: list[str] | None = None,
    parallel: bool = True,
    summarize: bool = True,
    llm: BaseLLM | None = None,
) -> ReviewResult:
    """코드 리뷰를 실행하고 결과를 반환합니다.

    이 함수는 ReviewRunner와 ReviewSummarizer를 조합하여
    전체 리뷰 워크플로우를 실행합니다.

    Args:
        path: Git 저장소 경로.
        staged: True면 staged 변경사항만 리뷰.
        commit_range: 리뷰할 커밋 범위.
        agents: 사용할 에이전트 이름 목록.
        parallel: True면 에이전트를 병렬로 실행.
        summarize: True면 결과를 종합.
        llm: 사용할 LLM 인스턴스.

    Returns:
        ReviewResult 객체.
    """
    runner = ReviewRunner(agents=agents, llm=llm, parallel=parallel)
    result = await runner.review(path, staged, commit_range)

    if summarize and result.total_comments > 0:
        summarizer = ReviewSummarizer(llm=llm)
        result = await summarizer.summarize(result)

    return result


def run_review_sync(
    path: str | Path = ".",
    staged: bool = False,
    commit_range: str | None = None,
    agents: list[str] | None = None,
    parallel: bool = True,
    summarize: bool = True,
    llm: BaseLLM | None = None,
) -> ReviewResult:
    """run_review()의 동기 버전."""
    return asyncio.run(
        run_review(path, staged, commit_range, agents, parallel, summarize, llm)
    )

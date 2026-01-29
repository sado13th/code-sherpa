"""Review agents - Multi-Agent 리뷰어들."""

from code_sherpa.shared.llm import BaseLLM

from .architect import ArchitectAgent
from .base import BaseAgent
from .junior import JuniorAgent
from .performance import PerformanceAgent
from .security import SecurityAgent

__all__ = [
    "BaseAgent",
    "ArchitectAgent",
    "SecurityAgent",
    "PerformanceAgent",
    "JuniorAgent",
    "AGENT_REGISTRY",
    "get_agent",
    "get_available_agents",
]

# 에이전트 레지스트리
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "architect": ArchitectAgent,
    "security": SecurityAgent,
    "performance": PerformanceAgent,
    "junior": JuniorAgent,
}


def get_agent(name: str, llm: BaseLLM | None = None) -> BaseAgent:
    """이름으로 에이전트 인스턴스 생성.

    Args:
        name: 에이전트 이름 (예: "architect", "security")
        llm: 사용할 LLM 인스턴스. None이면 기본 LLM 사용.

    Returns:
        BaseAgent 인스턴스

    Raises:
        ValueError: 지원하지 않는 에이전트 이름인 경우

    Examples:
        >>> agent = get_agent("architect")
        >>> agent = get_agent("security", llm=custom_llm)
    """
    name = name.lower()

    if name not in AGENT_REGISTRY:
        available = ", ".join(get_available_agents())
        raise ValueError(
            f"지원하지 않는 에이전트입니다: {name}. 사용 가능한 에이전트: {available}"
        )

    agent_class = AGENT_REGISTRY[name]
    return agent_class(llm=llm)


def get_available_agents() -> list[str]:
    """사용 가능한 에이전트 이름 목록 반환.

    Returns:
        에이전트 이름 목록

    Examples:
        >>> get_available_agents()
        ['architect', 'junior', 'performance', 'security']
    """
    return sorted(AGENT_REGISTRY.keys())

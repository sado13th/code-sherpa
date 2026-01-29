"""LLM adapters - LLM 제공자 어댑터."""

from .anthropic import AnthropicLLM
from .base import BaseLLM
from .openai import OpenAILLM

__all__ = ["BaseLLM", "OpenAILLM", "AnthropicLLM", "get_llm"]


def get_llm(provider: str = "openai", model: str | None = None, **kwargs) -> BaseLLM:
    """설정에 따라 적절한 LLM 인스턴스 반환.

    Args:
        provider: LLM 제공자. "openai" 또는 "anthropic".
        model: 사용할 모델명. None이면 제공자별 기본값 사용.
        **kwargs: LLM 생성에 전달할 추가 파라미터
            (api_key, max_tokens, temperature 등)

    Returns:
        BaseLLM 인스턴스

    Raises:
        ValueError: 지원하지 않는 제공자인 경우.

    Examples:
        >>> llm = get_llm("openai")
        >>> llm = get_llm("anthropic", model="claude-3-opus-20240229")
        >>> llm = get_llm("openai", temperature=0.7, max_tokens=2048)
    """
    provider = provider.lower()

    if provider == "openai":
        return OpenAILLM(model=model, **kwargs)
    elif provider == "anthropic":
        return AnthropicLLM(model=model, **kwargs)
    else:
        raise ValueError(
            f"지원하지 않는 LLM 제공자입니다: {provider}. "
            "'openai' 또는 'anthropic'을 사용하세요."
        )

"""OpenAI LLM 어댑터 구현."""

import os

from openai import OpenAI

from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI API를 사용하는 LLM 어댑터.

    환경변수 OPENAI_API_KEY에서 API 키를 로드합니다.
    """

    DEFAULT_MODEL = "gpt-4"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> None:
        """OpenAI LLM 초기화.

        Args:
            model: 사용할 모델명. 기본값은 gpt-4.
            api_key: API 키. None이면 환경변수에서 로드.
            max_tokens: 최대 토큰 수. 기본값 4096.
            temperature: 생성 온도. 기본값 0.3.

        Raises:
            ValueError: API 키가 설정되지 않은 경우.
        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. "
                "환경변수 OPENAI_API_KEY를 설정하거나 api_key 파라미터를 전달하세요."
            )

        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client = OpenAI(api_key=self._api_key)

    def complete(self, prompt: str, **kwargs) -> str:
        """단일 프롬프트에 대한 완성 응답 생성.

        내부적으로 chat API를 사용하여 구현합니다.

        Args:
            prompt: 입력 프롬프트
            **kwargs: 추가 파라미터 (temperature, max_tokens 등)

        Returns:
            생성된 텍스트 응답
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)

    def chat(self, messages: list[dict], **kwargs) -> str:
        """대화 형식의 메시지에 대한 응답 생성.

        Args:
            messages: 대화 메시지 목록
            **kwargs: 추가 파라미터 (temperature, max_tokens 등)

        Returns:
            생성된 텍스트 응답
        """
        temperature = kwargs.get("temperature", self._temperature)
        max_tokens = kwargs.get("max_tokens", self._max_tokens)

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""

    def get_model_name(self) -> str:
        """현재 사용 중인 모델 이름 반환.

        Returns:
            모델 이름 문자열
        """
        return self._model

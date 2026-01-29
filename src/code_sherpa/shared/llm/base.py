"""LLM 추상 베이스 클래스."""

from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """LLM 어댑터의 추상 베이스 클래스.

    모든 LLM 제공자 구현체는 이 클래스를 상속해야 합니다.
    """

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        """단일 프롬프트에 대한 완성 응답 생성.

        Args:
            prompt: 입력 프롬프트
            **kwargs: 추가 파라미터 (temperature, max_tokens 등)

        Returns:
            생성된 텍스트 응답
        """
        ...

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        """대화 형식의 메시지에 대한 응답 생성.

        Args:
            messages: 대화 메시지 목록
                각 메시지는 {"role": "user|assistant|system", "content": "..."} 형식
            **kwargs: 추가 파라미터 (temperature, max_tokens 등)

        Returns:
            생성된 텍스트 응답
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """현재 사용 중인 모델 이름 반환.

        Returns:
            모델 이름 문자열
        """
        ...

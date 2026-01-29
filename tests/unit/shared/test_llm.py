"""LLM 어댑터 테스트."""

from unittest.mock import MagicMock, patch

import pytest

from code_sherpa.shared.llm import AnthropicLLM, BaseLLM, OpenAILLM, get_llm


class TestBaseLLM:
    """BaseLLM 추상 클래스 테스트."""

    def test_cannot_instantiate_base_llm(self) -> None:
        """BaseLLM은 직접 인스턴스화할 수 없음."""
        with pytest.raises(TypeError):
            BaseLLM()  # type: ignore


class TestOpenAILLM:
    """OpenAILLM 테스트."""

    def test_init_without_api_key_raises_error(self) -> None:
        """API 키 없이 초기화하면 에러."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                OpenAILLM()

            assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_init_with_env_api_key(self) -> None:
        """환경변수에서 API 키 로드."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("code_sherpa.shared.llm.openai.OpenAI"):
                llm = OpenAILLM()
                assert llm._api_key == "test-key"

    def test_init_with_explicit_api_key(self) -> None:
        """명시적 API 키 전달."""
        with patch("code_sherpa.shared.llm.openai.OpenAI"):
            llm = OpenAILLM(api_key="explicit-key")
            assert llm._api_key == "explicit-key"

    def test_default_model(self) -> None:
        """기본 모델은 gpt-4."""
        with patch("code_sherpa.shared.llm.openai.OpenAI"):
            llm = OpenAILLM(api_key="test-key")
            assert llm.get_model_name() == "gpt-4"

    def test_custom_model(self) -> None:
        """커스텀 모델 설정."""
        with patch("code_sherpa.shared.llm.openai.OpenAI"):
            llm = OpenAILLM(api_key="test-key", model="gpt-4-turbo")
            assert llm.get_model_name() == "gpt-4-turbo"

    def test_complete_calls_chat(self) -> None:
        """complete()는 chat()을 호출."""
        with patch("code_sherpa.shared.llm.openai.OpenAI"):
            llm = OpenAILLM(api_key="test-key")
            llm.chat = MagicMock(return_value="response")  # type: ignore

            result = llm.complete("test prompt")

            llm.chat.assert_called_once_with(
                [{"role": "user", "content": "test prompt"}]
            )
            assert result == "response"

    def test_chat_returns_response(self) -> None:
        """chat()이 응답 반환."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test response"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("code_sherpa.shared.llm.openai.OpenAI", return_value=mock_client):
            llm = OpenAILLM(api_key="test-key")
            result = llm.chat([{"role": "user", "content": "hello"}])

            assert result == "test response"

    def test_chat_with_kwargs(self) -> None:
        """chat()에 추가 파라미터 전달."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("code_sherpa.shared.llm.openai.OpenAI", return_value=mock_client):
            llm = OpenAILLM(api_key="test-key")
            llm.chat(
                [{"role": "user", "content": "hello"}],
                temperature=0.7,
                max_tokens=2048,
            )

            mock_client.chat.completions.create.assert_called_once_with(
                model="gpt-4",
                messages=[{"role": "user", "content": "hello"}],
                temperature=0.7,
                max_tokens=2048,
            )


class TestAnthropicLLM:
    """AnthropicLLM 테스트."""

    def test_init_without_api_key_raises_error(self) -> None:
        """API 키 없이 초기화하면 에러."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                AnthropicLLM()

            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_init_with_env_api_key(self) -> None:
        """환경변수에서 API 키 로드."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("code_sherpa.shared.llm.anthropic.Anthropic"):
                llm = AnthropicLLM()
                assert llm._api_key == "test-key"

    def test_init_with_explicit_api_key(self) -> None:
        """명시적 API 키 전달."""
        with patch("code_sherpa.shared.llm.anthropic.Anthropic"):
            llm = AnthropicLLM(api_key="explicit-key")
            assert llm._api_key == "explicit-key"

    def test_default_model(self) -> None:
        """기본 모델은 claude-3-sonnet."""
        with patch("code_sherpa.shared.llm.anthropic.Anthropic"):
            llm = AnthropicLLM(api_key="test-key")
            assert "claude-3-sonnet" in llm.get_model_name()

    def test_custom_model(self) -> None:
        """커스텀 모델 설정."""
        with patch("code_sherpa.shared.llm.anthropic.Anthropic"):
            llm = AnthropicLLM(api_key="test-key", model="claude-3-opus-20240229")
            assert llm.get_model_name() == "claude-3-opus-20240229"

    def test_complete_calls_chat(self) -> None:
        """complete()는 chat()을 호출."""
        with patch("code_sherpa.shared.llm.anthropic.Anthropic"):
            llm = AnthropicLLM(api_key="test-key")
            llm.chat = MagicMock(return_value="response")  # type: ignore

            result = llm.complete("test prompt")

            llm.chat.assert_called_once_with(
                [{"role": "user", "content": "test prompt"}]
            )
            assert result == "response"

    def test_chat_returns_response(self) -> None:
        """chat()이 응답 반환."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="test response")]
        mock_client.messages.create.return_value = mock_response

        with patch(
            "code_sherpa.shared.llm.anthropic.Anthropic", return_value=mock_client
        ):
            llm = AnthropicLLM(api_key="test-key")
            result = llm.chat([{"role": "user", "content": "hello"}])

            assert result == "test response"

    def test_chat_handles_system_message(self) -> None:
        """chat()이 system 메시지를 별도 파라미터로 전달."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="response")]
        mock_client.messages.create.return_value = mock_response

        with patch(
            "code_sherpa.shared.llm.anthropic.Anthropic", return_value=mock_client
        ):
            llm = AnthropicLLM(api_key="test-key")
            llm.chat(
                [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "hello"},
                ]
            )

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["system"] == "You are helpful."
            assert call_kwargs["messages"] == [{"role": "user", "content": "hello"}]


class TestGetLLM:
    """get_llm 팩토리 함수 테스트."""

    def test_get_openai_llm(self) -> None:
        """OpenAI LLM 반환."""
        with patch("code_sherpa.shared.llm.openai.OpenAI"):
            llm = get_llm("openai", api_key="test-key")
            assert isinstance(llm, OpenAILLM)

    def test_get_anthropic_llm(self) -> None:
        """Anthropic LLM 반환."""
        with patch("code_sherpa.shared.llm.anthropic.Anthropic"):
            llm = get_llm("anthropic", api_key="test-key")
            assert isinstance(llm, AnthropicLLM)

    def test_case_insensitive_provider(self) -> None:
        """제공자 이름은 대소문자 구분 없음."""
        with patch("code_sherpa.shared.llm.openai.OpenAI"):
            llm1 = get_llm("OpenAI", api_key="test-key")
            llm2 = get_llm("OPENAI", api_key="test-key")

            assert isinstance(llm1, OpenAILLM)
            assert isinstance(llm2, OpenAILLM)

    def test_invalid_provider_raises_error(self) -> None:
        """잘못된 제공자 이름은 에러."""
        with pytest.raises(ValueError) as exc_info:
            get_llm("invalid-provider")

        assert "지원하지 않는 LLM 제공자" in str(exc_info.value)

    def test_get_llm_with_model(self) -> None:
        """모델 지정."""
        with patch("code_sherpa.shared.llm.openai.OpenAI"):
            llm = get_llm("openai", model="gpt-4-turbo", api_key="test-key")
            assert llm.get_model_name() == "gpt-4-turbo"

    def test_get_llm_with_kwargs(self) -> None:
        """추가 파라미터 전달."""
        with patch("code_sherpa.shared.llm.openai.OpenAI"):
            llm = get_llm(
                "openai", api_key="test-key", temperature=0.5, max_tokens=2000
            )
            assert llm._temperature == 0.5
            assert llm._max_tokens == 2000

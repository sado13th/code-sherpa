"""Prompts module - 프롬프트 템플릿 로더."""

from pathlib import Path


def load_prompt(name: str, **kwargs: str | int | float | list[str]) -> str:
    """프롬프트 템플릿 로드 및 변수 치환.

    Args:
        name: 프롬프트 이름 (예: "analyze/repo_summary")
        **kwargs: 템플릿 변수

    Returns:
        포맷된 프롬프트 문자열

    Raises:
        FileNotFoundError: 프롬프트 파일이 존재하지 않는 경우
        KeyError: 필수 템플릿 변수가 누락된 경우
    """
    prompts_dir = Path(__file__).parent
    prompt_path = prompts_dir / f"{name}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {name}.md")

    template = prompt_path.read_text(encoding="utf-8")

    # 리스트 값을 문자열로 변환
    formatted_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, list):
            formatted_kwargs[key] = "\n".join(str(item) for item in value)
        else:
            formatted_kwargs[key] = value

    try:
        return template.format(**formatted_kwargs)
    except KeyError as e:
        raise KeyError(f"Missing template variable: {e}") from e


def get_available_prompts() -> list[str]:
    """사용 가능한 프롬프트 목록 반환.

    Returns:
        프롬프트 이름 목록 (예: ["analyze/repo_summary", "review/security"])
    """
    prompts_dir = Path(__file__).parent
    prompts = []

    for md_file in prompts_dir.rglob("*.md"):
        # prompts 디렉토리 기준 상대 경로에서 확장자 제거
        relative_path = md_file.relative_to(prompts_dir)
        prompt_name = str(relative_path.with_suffix(""))
        prompts.append(prompt_name)

    return sorted(prompts)

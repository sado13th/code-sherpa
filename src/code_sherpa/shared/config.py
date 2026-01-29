"""Configuration management - YAML 설정 로더 및 스키마."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LLMConfig:
    """LLM 설정."""

    provider: str = "openai"
    model: str = "gpt-4"
    api_key_env: str = "OPENAI_API_KEY"
    max_tokens: int = 4096
    temperature: float = 0.3


@dataclass
class AnalyzeConfig:
    """분석 설정."""

    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "__pycache__",
            "*.pyc",
            "vendor",
            ".venv",
            "venv",
        ]
    )
    max_file_size_kb: int = 500
    languages: list[str] | None = None


@dataclass
class ReviewConfig:
    """리뷰 설정."""

    default_agents: list[str] = field(default_factory=lambda: ["architect", "security"])
    parallel: bool = True
    max_diff_lines: int = 1000


@dataclass
class OutputConfig:
    """출력 설정."""

    default_format: str = "console"
    color: bool = True
    save_reports: bool = False
    reports_dir: str = "./outputs/reports"


@dataclass
class AppConfig:
    """애플리케이션 전체 설정."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    analyze: AnalyzeConfig = field(default_factory=AnalyzeConfig)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def _dict_to_config(data: dict[str, Any]) -> AppConfig:
    """딕셔너리를 AppConfig로 변환."""
    return AppConfig(
        llm=LLMConfig(**data.get("llm", {})),
        analyze=AnalyzeConfig(**data.get("analyze", {})),
        review=ReviewConfig(**data.get("review", {})),
        output=OutputConfig(**data.get("output", {})),
    )


def load_config(config_path: Path | None = None) -> AppConfig:
    """설정 파일 로드.

    Args:
        config_path: 설정 파일 경로. None이면 기본 경로 탐색.

    Returns:
        AppConfig 인스턴스
    """
    # 설정 파일 탐색 순서
    search_paths = [
        config_path,
        Path.cwd() / ".code-sherpa.yaml",
        Path.cwd() / ".code-sherpa.yml",
        Path.home() / ".config" / "code-sherpa" / "config.yaml",
    ]

    for path in search_paths:
        if path and path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return _dict_to_config(data)

    # 설정 파일 없으면 기본값 사용
    return AppConfig()


def get_config_path() -> Path | None:
    """현재 사용 중인 설정 파일 경로 반환."""
    search_paths = [
        Path.cwd() / ".code-sherpa.yaml",
        Path.cwd() / ".code-sherpa.yml",
        Path.home() / ".config" / "code-sherpa" / "config.yaml",
    ]

    for path in search_paths:
        if path.exists():
            return path

    return None

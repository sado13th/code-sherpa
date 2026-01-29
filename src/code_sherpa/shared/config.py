"""Configuration management - YAML 설정 로더 및 스키마."""

import re
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
class ProjectConfig:
    """프로젝트 설정."""

    name: str
    path: str
    llm: LLMConfig | None = None
    analyze: AnalyzeConfig | None = None
    review: ReviewConfig | None = None


@dataclass
class AppConfig:
    """애플리케이션 전체 설정."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    analyze: AnalyzeConfig = field(default_factory=AnalyzeConfig)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    projects: dict[str, ProjectConfig] = field(default_factory=dict)


def _dict_to_config(data: dict[str, Any]) -> AppConfig:
    """딕셔너리를 AppConfig로 변환."""
    # 프로젝트 설정 파싱
    projects = {}
    for name, proj_data in data.get("projects", {}).items():
        projects[name] = ProjectConfig(
            name=name,
            path=proj_data.get("path", ""),
            llm=LLMConfig(**proj_data["llm"]) if proj_data.get("llm") else None,
            analyze=AnalyzeConfig(**proj_data["analyze"])
            if proj_data.get("analyze")
            else None,
            review=ReviewConfig(**proj_data["review"])
            if proj_data.get("review")
            else None,
        )

    return AppConfig(
        llm=LLMConfig(**data.get("llm", {})),
        analyze=AnalyzeConfig(**data.get("analyze", {})),
        review=ReviewConfig(**data.get("review", {})),
        output=OutputConfig(**data.get("output", {})),
        projects=projects,
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


def get_global_config_path() -> Path:
    """전역 설정 파일 경로 반환."""
    return Path.home() / ".config" / "code-sherpa" / "config.yaml"


def _validate_project_name(name: str) -> bool:
    """프로젝트 이름 유효성 검사.

    영문, 숫자, 하이픈만 허용.
    """
    return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-]*$", name))


def _load_global_config_raw() -> dict[str, Any]:
    """전역 설정 파일을 딕셔너리로 로드."""
    config_path = get_global_config_path()
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_global_config_raw(data: dict[str, Any]) -> None:
    """전역 설정 파일에 딕셔너리 저장."""
    config_path = get_global_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def add_project(name: str, path: str) -> None:
    """프로젝트 등록.

    Args:
        name: 프로젝트 이름 (영문, 숫자, 하이픈만)
        path: 프로젝트 경로

    Raises:
        ValueError: 유효하지 않은 이름 또는 이미 존재하는 프로젝트
    """
    if not _validate_project_name(name):
        raise ValueError(
            f"유효하지 않은 프로젝트 이름: {name} (영문, 숫자, 하이픈만 허용)"
        )

    data = _load_global_config_raw()
    projects = data.get("projects", {})

    if name in projects:
        raise ValueError(f"이미 존재하는 프로젝트: {name}")

    projects[name] = {"path": str(Path(path).resolve())}
    data["projects"] = projects
    _save_global_config_raw(data)


def remove_project(name: str) -> None:
    """프로젝트 등록 해제.

    Args:
        name: 프로젝트 이름

    Raises:
        ValueError: 존재하지 않는 프로젝트
    """
    data = _load_global_config_raw()
    projects = data.get("projects", {})

    if name not in projects:
        raise ValueError(f"존재하지 않는 프로젝트: {name}")

    del projects[name]
    data["projects"] = projects
    _save_global_config_raw(data)


def list_projects() -> list[tuple[str, str, bool]]:
    """등록된 프로젝트 목록 반환.

    Returns:
        (이름, 경로, 유효여부) 튜플 리스트
    """
    data = _load_global_config_raw()
    projects = data.get("projects", {})

    result = []
    for name, proj_data in projects.items():
        path = proj_data.get("path", "")
        is_valid = Path(path).exists() if path else False
        result.append((name, path, is_valid))

    return sorted(result, key=lambda x: x[0])


def get_project(name: str) -> ProjectConfig | None:
    """프로젝트 설정 반환.

    Args:
        name: 프로젝트 이름

    Returns:
        ProjectConfig 또는 None
    """
    config = load_config(get_global_config_path())
    return config.projects.get(name)


def get_config_for_project(project_name: str) -> tuple[AppConfig, Path]:
    """프로젝트에 대한 병합된 설정과 경로 반환.

    프로젝트별 설정이 있으면 기본 설정에 병합합니다.

    Args:
        project_name: 프로젝트 이름

    Returns:
        (AppConfig, 프로젝트 경로) 튜플

    Raises:
        ValueError: 존재하지 않는 프로젝트
    """
    base_config = load_config(get_global_config_path())
    project = base_config.projects.get(project_name)

    if not project:
        raise ValueError(f"존재하지 않는 프로젝트: {project_name}")

    project_path = Path(project.path)

    # 프로젝트별 설정 병합
    merged = AppConfig(
        llm=project.llm if project.llm else base_config.llm,
        analyze=project.analyze if project.analyze else base_config.analyze,
        review=project.review if project.review else base_config.review,
        output=base_config.output,
        projects=base_config.projects,
    )

    return merged, project_path

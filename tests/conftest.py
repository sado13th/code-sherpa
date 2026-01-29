"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_repo_path(tmp_path: Path) -> Path:
    """Create a sample git repository for testing."""
    repo_path = tmp_path / "sample_repo"
    repo_path.mkdir()

    # Create sample files
    (repo_path / "main.py").write_text("print('hello')\n")
    (repo_path / "utils.py").write_text("def helper(): pass\n")

    return repo_path


@pytest.fixture
def sample_config() -> dict:
    """Sample configuration for testing."""
    return {
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "api_key_env": "OPENAI_API_KEY",
            "max_tokens": 4096,
            "temperature": 0.3,
        },
        "analyze": {
            "exclude_patterns": ["node_modules", ".git"],
            "max_file_size_kb": 500,
        },
        "review": {
            "default_agents": ["architect", "security"],
            "parallel": True,
        },
        "output": {
            "default_format": "console",
            "color": True,
        },
    }

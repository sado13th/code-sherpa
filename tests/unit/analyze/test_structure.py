"""StructureAnalyzer 테스트."""

from pathlib import Path

from code_sherpa.analyze.structure import (
    StructureAnalyzer,
    _detect_language_from_path,
    _extract_imports,
    _is_entry_point,
    _should_exclude,
)
from code_sherpa.shared.models import StructureAnalysis


class TestHelperFunctions:
    """헬퍼 함수 테스트."""

    def test_detect_language_from_path(self) -> None:
        """파일 경로에서 언어 감지."""
        assert _detect_language_from_path(Path("test.py")) == "Python"
        assert _detect_language_from_path(Path("test.js")) == "JavaScript"
        assert _detect_language_from_path(Path("test.go")) == "Go"
        assert _detect_language_from_path(Path("test.xyz")) == "Unknown"

    def test_extract_imports_python(self) -> None:
        """Python import 추출."""
        content = """
import os
import sys
from pathlib import Path
from typing import Optional
"""
        imports = _extract_imports(content, "Python")
        assert "os" in imports
        assert "sys" in imports
        assert "pathlib" in imports
        assert "typing" in imports

    def test_extract_imports_javascript(self) -> None:
        """JavaScript import 추출."""
        content = """
import React from 'react';
import { useState } from 'react';
const fs = require('fs');
"""
        imports = _extract_imports(content, "JavaScript")
        assert "react" in imports
        assert "fs" in imports

    def test_extract_imports_go(self) -> None:
        """Go import 추출."""
        content = """
import "fmt"
import (
    "os"
    "strings"
)
"""
        imports = _extract_imports(content, "Go")
        assert "fmt" in imports
        # 블록 import도 일부 추출될 수 있음

    def test_extract_imports_unknown_language(self) -> None:
        """알 수 없는 언어는 빈 목록."""
        content = "some code"
        imports = _extract_imports(content, "Unknown")
        assert imports == []

    def test_is_entry_point_by_filename(self) -> None:
        """파일 이름으로 엔트리포인트 확인."""
        assert _is_entry_point(Path("main.py"), "", "Python") is True
        assert _is_entry_point(Path("app.py"), "", "Python") is True
        assert _is_entry_point(Path("index.js"), "", "JavaScript") is True
        assert _is_entry_point(Path("utils.py"), "", "Python") is False

    def test_is_entry_point_python_main(self) -> None:
        """Python __main__ 패턴으로 엔트리포인트 확인."""
        content = """
if __name__ == "__main__":
    main()
"""
        assert _is_entry_point(Path("script.py"), content, "Python") is True

    def test_is_entry_point_go_main(self) -> None:
        """Go main 함수로 엔트리포인트 확인."""
        content = """
package main

func main() {
    fmt.Println("Hello")
}
"""
        assert _is_entry_point(Path("script.go"), content, "Go") is True

    def test_should_exclude_by_name(self) -> None:
        """이름으로 제외 확인."""
        assert _should_exclude(Path("node_modules"), ["node_modules"]) is True
        assert _should_exclude(Path("src"), ["node_modules"]) is False

    def test_should_exclude_by_pattern(self) -> None:
        """패턴으로 제외 확인."""
        assert _should_exclude(Path("test.pyc"), ["*.pyc"]) is True
        assert _should_exclude(Path("test.py"), ["*.pyc"]) is False


class TestStructureAnalyzer:
    """StructureAnalyzer 테스트."""

    def test_init(self) -> None:
        """초기화."""
        analyzer = StructureAnalyzer()
        assert analyzer is not None

    def test_analyze_single_file(self, tmp_path: Path) -> None:
        """단일 파일 분석."""
        test_file = tmp_path / "main.py"
        test_file.write_text('if __name__ == "__main__":\n    print("hello")\n')

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        assert isinstance(result, StructureAnalysis)
        assert result.root.name == tmp_path.name
        assert len(result.root.children) == 1
        assert result.root.children[0].name == "main.py"

    def test_analyze_directory_structure(self, tmp_path: Path) -> None:
        """디렉토리 구조 분석."""
        # 디렉토리 구조 생성
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('main')")
        (src / "utils.py").write_text("def helper(): pass")

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_main.py").write_text("def test(): pass")

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        # 루트 노드 확인
        assert result.root.node_type == "directory"
        child_names = [c.name for c in result.root.children]
        assert "src" in child_names
        assert "tests" in child_names

    def test_analyze_python_module(self, tmp_path: Path) -> None:
        """Python 모듈(__init__.py) 감지."""
        package = tmp_path / "mypackage"
        package.mkdir()
        (package / "__init__.py").write_text("")
        (package / "module.py").write_text("class MyClass: pass")

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        # 패키지 노드가 "module" 타입이어야 함
        package_node = None
        for child in result.root.children:
            if child.name == "mypackage":
                package_node = child
                break

        assert package_node is not None
        assert package_node.node_type == "module"

    def test_analyze_finds_entry_points(self, tmp_path: Path) -> None:
        """엔트리포인트 찾기."""
        (tmp_path / "main.py").write_text('if __name__ == "__main__":\n    pass\n')
        (tmp_path / "utils.py").write_text("def helper(): pass")

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        assert len(result.entry_points) >= 1
        entry_point_names = [ep.name for ep in result.entry_points]
        assert "main.py" in entry_point_names

    def test_analyze_with_exclude_patterns(self, tmp_path: Path) -> None:
        """제외 패턴 적용."""
        (tmp_path / "main.py").write_text("print('hello')")

        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.json").write_text('{"name": "test"}')

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path, exclude_patterns=["node_modules"])

        child_names = [c.name for c in result.root.children]
        assert "node_modules" not in child_names
        assert "main.py" in child_names

    def test_analyze_excludes_hidden_files(self, tmp_path: Path) -> None:
        """숨김 파일 제외."""
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / ".hidden").write_text("hidden content")

        # 숨김 디렉토리
        hidden_dir = tmp_path / ".hidden_dir"
        hidden_dir.mkdir()
        (hidden_dir / "file.py").write_text("content")

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        # 루트 자식 중 숨김 파일/디렉토리 확인
        child_names = [c.name for c in result.root.children]
        assert ".hidden" not in child_names
        assert ".hidden_dir" not in child_names
        assert "main.py" in child_names

    def test_analyze_empty_directory(self, tmp_path: Path) -> None:
        """빈 디렉토리 분석."""
        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        assert result.root.name == tmp_path.name
        assert result.root.children == []
        assert result.entry_points == []

    def test_analyze_sorts_directories_first(self, tmp_path: Path) -> None:
        """디렉토리가 파일보다 먼저 정렬."""
        # 파일 먼저 생성
        (tmp_path / "zebra.py").write_text("pass")
        (tmp_path / "alpha.py").write_text("pass")

        # 디렉토리 생성
        (tmp_path / "beta").mkdir()
        (tmp_path / "beta" / "test.py").write_text("pass")

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        # 첫 번째 자식이 디렉토리여야 함
        if result.root.children:
            first_child = result.root.children[0]
            assert first_child.node_type == "directory" or first_child.name == "beta"

    def test_structure_node_has_correct_path(self, tmp_path: Path) -> None:
        """StructureNode 경로가 절대경로."""
        (tmp_path / "main.py").write_text("pass")

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        assert result.root.path.is_absolute()
        if result.root.children:
            assert result.root.children[0].path.is_absolute()

    def test_analyze_complex_structure(self, tmp_path: Path) -> None:
        """복잡한 구조 분석."""
        # 프로젝트 구조 생성
        src = tmp_path / "src"
        src.mkdir()

        pkg = src / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text('if __name__ == "__main__": pass')
        (pkg / "utils.py").write_text("import os\nfrom pathlib import Path")

        models = pkg / "models"
        models.mkdir()
        (models / "__init__.py").write_text("")
        (models / "user.py").write_text("class User: pass")

        analyzer = StructureAnalyzer()
        result = analyzer.analyze(tmp_path)

        assert isinstance(result, StructureAnalysis)
        assert result.root.node_type == "directory"

        # 엔트리포인트 확인
        entry_point_names = [ep.name for ep in result.entry_points]
        assert "main.py" in entry_point_names

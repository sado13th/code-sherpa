"""코드 구조 분석 모듈."""

import fnmatch
import re
from pathlib import Path

from code_sherpa.shared.git import EXTENSION_LANGUAGE_MAP
from code_sherpa.shared.models import Dependency, StructureAnalysis, StructureNode

# 언어별 import 패턴
IMPORT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "Python": [
        re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
        re.compile(r"^\s*from\s+([\w.]+)\s+import", re.MULTILINE),
    ],
    "JavaScript": [
        re.compile(r'^\s*import\s+.*?from\s+["\'](.+?)["\']', re.MULTILINE),
        re.compile(
            r'^\s*(?:const|let|var)\s+\w+\s*=\s*require\(["\'](.+?)["\']\)',
            re.MULTILINE,
        ),
    ],
    "TypeScript": [
        re.compile(r'^\s*import\s+.*?from\s+["\'](.+?)["\']', re.MULTILINE),
        re.compile(
            r'^\s*(?:const|let|var)\s+\w+\s*=\s*require\(["\'](.+?)["\']\)',
            re.MULTILINE,
        ),
    ],
    "Go": [
        re.compile(r'^\s*import\s+["\'](.+?)["\']', re.MULTILINE),
        re.compile(r'^\s*import\s+\w+\s+["\'](.+?)["\']', re.MULTILINE),
        re.compile(r'^\s+"(.+?)"', re.MULTILINE),  # import 블록 내부
    ],
    "Java": [
        re.compile(r"^\s*import\s+([\w.]+);", re.MULTILINE),
    ],
    "Rust": [
        re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE),
        re.compile(r"^\s*extern\s+crate\s+(\w+)", re.MULTILINE),
    ],
    "C": [
        re.compile(r'^\s*#include\s*[<"](.+?)[>"]', re.MULTILINE),
    ],
    "C++": [
        re.compile(r'^\s*#include\s*[<"](.+?)[>"]', re.MULTILINE),
    ],
    "Ruby": [
        re.compile(r"^\s*require\s+['\"](.+?)['\"]", re.MULTILINE),
        re.compile(r"^\s*require_relative\s+['\"](.+?)['\"]", re.MULTILINE),
    ],
}

# 언어별 엔트리포인트 패턴
ENTRY_POINT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "Python": [
        re.compile(r'if\s+__name__\s*==\s*["\']__main__["\']\s*:'),
    ],
    "JavaScript": [
        re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+main\s*\(", re.MULTILINE
        ),
        re.compile(r"^[^/]*module\.exports\s*=", re.MULTILINE),
    ],
    "TypeScript": [
        re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+main\s*\(", re.MULTILINE
        ),
        re.compile(r"^[^/]*module\.exports\s*=", re.MULTILINE),
    ],
    "Go": [
        re.compile(r"^\s*func\s+main\s*\(\s*\)", re.MULTILINE),
    ],
    "Java": [
        re.compile(r"public\s+static\s+void\s+main\s*\(\s*String"),
    ],
    "Rust": [
        re.compile(r"^\s*fn\s+main\s*\(\s*\)", re.MULTILINE),
    ],
    "C": [
        re.compile(r"^\s*int\s+main\s*\(", re.MULTILINE),
        re.compile(r"^\s*void\s+main\s*\(", re.MULTILINE),
    ],
    "C++": [
        re.compile(r"^\s*int\s+main\s*\(", re.MULTILINE),
        re.compile(r"^\s*void\s+main\s*\(", re.MULTILINE),
    ],
}

# 특별한 엔트리포인트 파일 이름
ENTRY_POINT_FILENAMES: set[str] = {
    "main.py",
    "app.py",
    "index.py",
    "__main__.py",
    "main.js",
    "index.js",
    "app.js",
    "main.ts",
    "index.ts",
    "app.ts",
    "main.go",
    "main.rs",
    "Main.java",
    "App.java",
    "main.c",
    "main.cpp",
}


def _detect_language_from_path(file_path: Path) -> str:
    """파일 경로에서 언어를 감지합니다."""
    ext = file_path.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "Unknown")


def _extract_imports(content: str, language: str) -> list[str]:
    """소스 코드에서 import 문을 추출합니다.

    Args:
        content: 소스 코드 내용
        language: 프로그래밍 언어

    Returns:
        import된 모듈/패키지 이름 목록
    """
    imports: list[str] = []
    patterns = IMPORT_PATTERNS.get(language, [])

    for pattern in patterns:
        matches = pattern.findall(content)
        imports.extend(matches)

    return list(set(imports))  # 중복 제거


def _is_entry_point(file_path: Path, content: str, language: str) -> bool:
    """파일이 엔트리포인트인지 확인합니다.

    Args:
        file_path: 파일 경로
        content: 파일 내용
        language: 프로그래밍 언어

    Returns:
        엔트리포인트이면 True
    """
    # 파일 이름으로 먼저 확인
    if file_path.name in ENTRY_POINT_FILENAMES:
        return True

    # 패턴으로 확인
    patterns = ENTRY_POINT_PATTERNS.get(language, [])
    for pattern in patterns:
        if pattern.search(content):
            return True

    return False


def _should_exclude(path: Path, exclude_patterns: list[str]) -> bool:
    """경로가 제외 패턴에 해당하는지 확인합니다.

    Args:
        path: 확인할 경로
        exclude_patterns: 제외 패턴 목록

    Returns:
        제외해야 하면 True
    """
    path_str = str(path)
    name = path.name

    for pattern in exclude_patterns:
        # 패턴이 디렉토리 이름인 경우
        if name == pattern:
            return True
        # fnmatch 패턴인 경우
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(path_str, pattern):
            return True
        # 경로 내에 패턴이 포함된 경우
        if f"/{pattern}/" in path_str or path_str.endswith(f"/{pattern}"):
            return True

    return False


class StructureAnalyzer:
    """코드 구조 분석기.

    디렉토리 구조, 의존성 관계, 엔트리포인트를 분석합니다.
    """

    def __init__(self) -> None:
        """StructureAnalyzer를 초기화합니다."""
        pass

    def _build_tree(
        self,
        path: Path,
        exclude_patterns: list[str],
        is_root: bool = True,
    ) -> StructureNode:
        """디렉토리 트리를 구축합니다.

        Args:
            path: 분석할 경로
            exclude_patterns: 제외 패턴 목록
            is_root: 루트 노드인지 여부

        Returns:
            StructureNode 트리
        """
        if path.is_file():
            return StructureNode(
                name=path.name,
                path=path,
                node_type="file",
                children=[],
            )

        children: list[StructureNode] = []

        # 디렉토리 내용 정렬 (디렉토리 먼저, 그 다음 파일)
        items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))

        for item in items:
            # 숨김 파일/디렉토리 건너뛰기
            if item.name.startswith("."):
                continue

            # 제외 패턴 확인
            if _should_exclude(item, exclude_patterns):
                continue

            if item.is_dir():
                # 재귀적으로 하위 디렉토리 분석
                child = self._build_tree(item, exclude_patterns, is_root=False)
                # 빈 디렉토리는 건너뛰기
                if child.children or child.node_type == "file":
                    children.append(child)
            else:
                # 파일 추가
                children.append(
                    StructureNode(
                        name=item.name,
                        path=item,
                        node_type="file",
                        children=[],
                    )
                )

        # 디렉토리가 Python 모듈인지 확인
        node_type = "directory"
        if (path / "__init__.py").exists():
            node_type = "module"

        return StructureNode(
            name=path.name,
            path=path,
            node_type=node_type,
            children=children,
        )

    def _extract_dependencies(
        self,
        node: StructureNode,
        base_path: Path,
    ) -> list[Dependency]:
        """트리에서 의존성을 추출합니다.

        Args:
            node: 분석할 노드
            base_path: 기준 경로 (상대 경로 계산용)

        Returns:
            Dependency 목록
        """
        dependencies: list[Dependency] = []

        if node.node_type == "file":
            language = _detect_language_from_path(node.path)

            try:
                content = node.path.read_text(encoding="utf-8", errors="ignore")
                imports = _extract_imports(content, language)

                for imp in imports:
                    # 상대 경로로 변환 시도 (같은 프로젝트 내 import만)
                    # 외부 패키지는 제외
                    if not imp.startswith(".") and "/" not in imp:
                        # 표준 라이브러리나 외부 패키지일 가능성이 높음
                        continue

                    dep = Dependency(
                        source=node.path,
                        target=Path(imp),  # 심볼릭 경로
                        dependency_type="import",
                    )
                    dependencies.append(dep)
            except OSError:
                pass

        # 하위 노드 재귀 처리
        for child in node.children:
            dependencies.extend(self._extract_dependencies(child, base_path))

        return dependencies

    def _find_entry_points(self, node: StructureNode) -> list[Path]:
        """엔트리포인트를 찾습니다.

        Args:
            node: 분석할 노드

        Returns:
            엔트리포인트 경로 목록
        """
        entry_points: list[Path] = []

        if node.node_type == "file":
            language = _detect_language_from_path(node.path)

            try:
                content = node.path.read_text(encoding="utf-8", errors="ignore")
                if _is_entry_point(node.path, content, language):
                    entry_points.append(node.path)
            except OSError:
                pass

        # 하위 노드 재귀 처리
        for child in node.children:
            entry_points.extend(self._find_entry_points(child))

        return entry_points

    def analyze(
        self,
        path: Path,
        exclude_patterns: list[str] | None = None,
    ) -> StructureAnalysis:
        """코드 구조를 분석합니다.

        Args:
            path: 분석할 디렉토리 경로
            exclude_patterns: 제외할 파일/디렉토리 패턴 목록

        Returns:
            StructureAnalysis 객체
        """
        # 절대 경로로 변환
        path = path.resolve()

        # 기본 제외 패턴
        default_patterns = [
            "node_modules",
            ".git",
            "__pycache__",
            "*.pyc",
            "vendor",
            ".venv",
            "venv",
            "dist",
            "build",
            ".idea",
            ".vscode",
        ]
        exclude_patterns = exclude_patterns or default_patterns

        # 트리 구축
        root = self._build_tree(path, exclude_patterns)

        # 의존성 추출
        dependencies = self._extract_dependencies(root, path)

        # 엔트리포인트 찾기
        entry_points = self._find_entry_points(root)

        return StructureAnalysis(
            root=root,
            dependencies=dependencies,
            entry_points=entry_points,
        )

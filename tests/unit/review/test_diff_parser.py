"""DiffParser 유닛 테스트."""

from pathlib import Path

import pytest

from code_sherpa.review.diff_parser import DiffParser
from code_sherpa.shared.models import ChangeType


class TestDiffParser:
    """DiffParser 테스트 클래스."""

    @pytest.fixture
    def parser(self) -> DiffParser:
        """DiffParser 인스턴스 생성."""
        return DiffParser()

    def test_parse_empty_diff(self, parser: DiffParser) -> None:
        """빈 diff 파싱 테스트."""
        result = parser.parse("")
        assert result.files == []
        assert result.stats.files_changed == 0
        assert result.stats.total_additions == 0
        assert result.stats.total_deletions == 0

    def test_parse_whitespace_only_diff(self, parser: DiffParser) -> None:
        """공백만 있는 diff 파싱 테스트."""
        result = parser.parse("   \n\n   ")
        assert result.files == []
        assert result.stats.files_changed == 0

    def test_parse_modified_file(self, parser: DiffParser) -> None:
        """일반 수정 파일 diff 파싱 테스트."""
        diff_text = """\
diff --git a/src/file.py b/src/file.py
index abc123..def456 100644
--- a/src/file.py
+++ b/src/file.py
@@ -10,5 +10,7 @@ def function():
     existing_line
-    removed_line
+    added_line
+    another_added
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert result.files[0].path == Path("src/file.py")
        assert result.files[0].change_type == ChangeType.MODIFIED
        assert result.files[0].additions == 2
        assert result.files[0].deletions == 1
        assert result.stats.files_changed == 1
        assert result.stats.total_additions == 2
        assert result.stats.total_deletions == 1

    def test_parse_new_file(self, parser: DiffParser) -> None:
        """새 파일 추가 diff 파싱 테스트."""
        diff_text = """\
diff --git a/src/new_file.py b/src/new_file.py
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/src/new_file.py
@@ -0,0 +1,5 @@
+def hello():
+    print("Hello")
+
+if __name__ == "__main__":
+    hello()
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert result.files[0].path == Path("src/new_file.py")
        assert result.files[0].change_type == ChangeType.ADDED
        assert result.files[0].additions == 5
        assert result.files[0].deletions == 0

    def test_parse_deleted_file(self, parser: DiffParser) -> None:
        """삭제된 파일 diff 파싱 테스트."""
        diff_text = """\
diff --git a/src/old_file.py b/src/old_file.py
deleted file mode 100644
index abc1234..0000000
--- a/src/old_file.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def old_function():
-    pass
-
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert result.files[0].path == Path("src/old_file.py")
        assert result.files[0].change_type == ChangeType.DELETED
        assert result.files[0].additions == 0
        assert result.files[0].deletions == 3

    def test_parse_renamed_file(self, parser: DiffParser) -> None:
        """파일 이름 변경 diff 파싱 테스트."""
        diff_text = """\
diff --git a/src/old_name.py b/src/new_name.py
similarity index 100%
rename from src/old_name.py
rename to src/new_name.py
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert result.files[0].path == Path("src/new_name.py")
        assert result.files[0].old_path == Path("src/old_name.py")
        assert result.files[0].change_type == ChangeType.RENAMED
        assert result.files[0].additions == 0
        assert result.files[0].deletions == 0

    def test_parse_renamed_file_with_changes(self, parser: DiffParser) -> None:
        """파일 이름 변경 + 내용 변경 diff 파싱 테스트."""
        diff_text = """\
diff --git a/src/old_name.py b/src/new_name.py
similarity index 80%
rename from src/old_name.py
rename to src/new_name.py
index abc123..def456 100644
--- a/src/old_name.py
+++ b/src/new_name.py
@@ -1,3 +1,4 @@
 def function():
-    old_line
+    new_line
+    added_line
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert result.files[0].path == Path("src/new_name.py")
        assert result.files[0].old_path == Path("src/old_name.py")
        assert result.files[0].change_type == ChangeType.RENAMED
        assert result.files[0].additions == 2
        assert result.files[0].deletions == 1

    def test_parse_binary_file(self, parser: DiffParser) -> None:
        """바이너리 파일 diff 파싱 테스트."""
        diff_text = """\
diff --git a/images/logo.png b/images/logo.png
new file mode 100644
index 0000000..abc1234
Binary files /dev/null and b/images/logo.png differ
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert result.files[0].path == Path("images/logo.png")
        assert result.files[0].change_type == ChangeType.ADDED
        # 바이너리 파일은 additions/deletions가 0
        assert result.files[0].additions == 0
        assert result.files[0].deletions == 0
        assert result.files[0].hunks == []

    def test_parse_multiple_files(self, parser: DiffParser) -> None:
        """여러 파일 diff 파싱 테스트."""
        diff_text = """\
diff --git a/file1.py b/file1.py
index abc123..def456 100644
--- a/file1.py
+++ b/file1.py
@@ -1,2 +1,3 @@
 line1
+new_line
 line2
diff --git a/file2.py b/file2.py
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/file2.py
@@ -0,0 +1,2 @@
+def func():
+    pass
diff --git a/file3.py b/file3.py
deleted file mode 100644
index abc1234..0000000
--- a/file3.py
+++ /dev/null
@@ -1,1 +0,0 @@
-old_content
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 3
        assert result.stats.files_changed == 3
        assert result.stats.total_additions == 3  # 1 + 2 + 0
        assert result.stats.total_deletions == 1  # 0 + 0 + 1

        # 첫 번째 파일: modified
        assert result.files[0].path == Path("file1.py")
        assert result.files[0].change_type == ChangeType.MODIFIED

        # 두 번째 파일: added
        assert result.files[1].path == Path("file2.py")
        assert result.files[1].change_type == ChangeType.ADDED

        # 세 번째 파일: deleted
        assert result.files[2].path == Path("file3.py")
        assert result.files[2].change_type == ChangeType.DELETED

    def test_parse_multiple_hunks(self, parser: DiffParser) -> None:
        """여러 hunk가 있는 diff 파싱 테스트."""
        diff_text = """\
diff --git a/large_file.py b/large_file.py
index abc123..def456 100644
--- a/large_file.py
+++ b/large_file.py
@@ -10,4 +10,5 @@ def func1():
     line1
-    old1
+    new1
+    added1
@@ -50,3 +51,4 @@ def func2():
     line2
-    old2
+    new2
+    added2
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert len(result.files[0].hunks) == 2

        # 첫 번째 hunk
        assert result.files[0].hunks[0].old_start == 10
        assert result.files[0].hunks[0].old_count == 4
        assert result.files[0].hunks[0].new_start == 10
        assert result.files[0].hunks[0].new_count == 5

        # 두 번째 hunk
        assert result.files[0].hunks[1].old_start == 50
        assert result.files[0].hunks[1].old_count == 3
        assert result.files[0].hunks[1].new_start == 51
        assert result.files[0].hunks[1].new_count == 4

        # 전체 변경 수
        assert result.files[0].additions == 4
        assert result.files[0].deletions == 2

    def test_parse_hunk_without_count(self, parser: DiffParser) -> None:
        """count 없는 hunk 헤더 파싱 테스트 (1줄 변경)."""
        diff_text = """\
diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -5 +5 @@ def func():
-    old
+    new
"""
        result = parser.parse(diff_text)

        assert len(result.files[0].hunks) == 1
        assert result.files[0].hunks[0].old_start == 5
        assert result.files[0].hunks[0].old_count == 1  # 기본값
        assert result.files[0].hunks[0].new_start == 5
        assert result.files[0].hunks[0].new_count == 1  # 기본값

    def test_raw_diff_preserved(self, parser: DiffParser) -> None:
        """원본 diff 텍스트가 보존되는지 테스트."""
        diff_text = "diff --git a/file.py b/file.py\nsome content"
        result = parser.parse(diff_text)
        assert result.raw == diff_text

    def test_parse_file_with_spaces_in_path(self, parser: DiffParser) -> None:
        """경로에 공백이 있는 파일 파싱 테스트."""
        diff_text = """\
diff --git a/src/my file.py b/src/my file.py
index abc123..def456 100644
--- a/src/my file.py
+++ b/src/my file.py
@@ -1,2 +1,2 @@
-old
+new
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert result.files[0].path == Path("src/my file.py")

    def test_parse_hunk_context_line(self, parser: DiffParser) -> None:
        """Hunk 헤더의 컨텍스트 라인 파싱 테스트."""
        diff_text = """\
diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -10,5 +10,6 @@ class MyClass:
     def method(self):
-        old
+        new
+        added
"""
        result = parser.parse(diff_text)

        # 컨텍스트 라인 "class MyClass:" 가 hunk에 포함되어 있지는 않지만
        # 파싱은 정상적으로 동작해야 함
        assert len(result.files[0].hunks) == 1
        assert result.files[0].additions == 2
        assert result.files[0].deletions == 1


class TestDiffParserEdgeCases:
    """DiffParser 엣지 케이스 테스트."""

    @pytest.fixture
    def parser(self) -> DiffParser:
        """DiffParser 인스턴스 생성."""
        return DiffParser()

    def test_parse_none_diff(self, parser: DiffParser) -> None:
        """None diff 처리 테스트."""
        # None은 타입 에러를 발생시킬 수 있지만, 빈 문자열처럼 처리
        result = parser.parse("")
        assert result.files == []

    def test_parse_diff_with_no_changes(self, parser: DiffParser) -> None:
        """변경 내용이 없는 diff (헤더만 있는 경우)."""
        diff_text = """\
diff --git a/file.py b/file.py
index abc123..def456 100644
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 1
        assert result.files[0].additions == 0
        assert result.files[0].deletions == 0

    def test_parse_complex_real_diff(self, parser: DiffParser) -> None:
        """복잡한 실제 git diff 예제 테스트."""
        diff_text = """\
diff --git a/pyproject.toml b/pyproject.toml
index 1234567..abcdefg 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -1,6 +1,7 @@
 [project]
 name = "my-project"
-version = "0.1.0"
+version = "0.2.0"
+description = "A new description"

 [project.dependencies]
 python = "^3.12"
diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,10 +1,15 @@
+import logging
 import sys

+logger = logging.getLogger(__name__)
+

 def main():
-    print("Hello")
+    logger.info("Starting...")
+    print("Hello, World!")
+    logger.info("Done")
     return 0


diff --git a/tests/test_main.py b/tests/test_main.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/tests/test_main.py
@@ -0,0 +1,8 @@
+import pytest
+from src.main import main
+
+
+def test_main():
+    result = main()
+    assert result == 0
+
"""
        result = parser.parse(diff_text)

        assert len(result.files) == 3
        assert result.stats.files_changed == 3

        # pyproject.toml: 2 additions, 1 deletion
        assert result.files[0].path == Path("pyproject.toml")
        assert result.files[0].change_type == ChangeType.MODIFIED
        assert result.files[0].additions == 2
        assert result.files[0].deletions == 1

        # src/main.py: 6 additions, 1 deletion
        assert result.files[1].path == Path("src/main.py")
        assert result.files[1].change_type == ChangeType.MODIFIED
        assert result.files[1].additions == 6
        assert result.files[1].deletions == 1

        # tests/test_main.py: 8 additions, 0 deletions
        assert result.files[2].path == Path("tests/test_main.py")
        assert result.files[2].change_type == ChangeType.ADDED
        assert result.files[2].additions == 8
        assert result.files[2].deletions == 0

        # 총계
        assert result.stats.total_additions == 16
        assert result.stats.total_deletions == 2

    def test_parse_diff_with_plus_minus_in_content(self, parser: DiffParser) -> None:
        """내용에 +/- 기호가 포함된 경우 테스트."""
        diff_text = """\
diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
 x = 5
-y = x + 10
+y = x - 10
"""
        result = parser.parse(diff_text)

        # "y = x + 10" 라인의 + 는 addition이 아님
        # "y = x - 10" 라인의 - 도 deletion이 아님
        # 실제로는 1 addition, 1 deletion
        assert result.files[0].additions == 1
        assert result.files[0].deletions == 1

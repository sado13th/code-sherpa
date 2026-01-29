"""Git diff 파서 모듈."""

import re
from pathlib import Path

from code_sherpa.shared.models import (
    ChangeType,
    DiffHunk,
    DiffStats,
    FileDiff,
    ParsedDiff,
)


class DiffParser:
    """Git diff 문자열을 ParsedDiff 객체로 변환하는 파서."""

    # Git diff 헤더 패턴
    _FILE_HEADER_PATTERN = re.compile(r"^diff --git a/(.*) b/(.*)$", re.MULTILINE)
    _NEW_FILE_PATTERN = re.compile(r"^new file mode", re.MULTILINE)
    _DELETED_FILE_PATTERN = re.compile(r"^deleted file mode", re.MULTILINE)
    _RENAME_FROM_PATTERN = re.compile(r"^rename from (.*)$", re.MULTILINE)
    _RENAME_TO_PATTERN = re.compile(r"^rename to (.*)$", re.MULTILINE)
    _SIMILARITY_PATTERN = re.compile(r"^similarity index (\d+)%$", re.MULTILINE)
    _BINARY_PATTERN = re.compile(r"^Binary files .* differ$", re.MULTILINE)

    # Hunk 헤더 패턴: @@ -old_start,old_count +new_start,new_count @@ context
    _HUNK_HEADER_PATTERN = re.compile(
        r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$", re.MULTILINE
    )

    def parse(self, diff_text: str) -> ParsedDiff:
        """
        Git diff 텍스트를 파싱하여 ParsedDiff 반환.

        Args:
            diff_text: git diff 명령의 출력 문자열

        Returns:
            ParsedDiff 객체 (files, stats, raw 포함)
        """
        if not diff_text or not diff_text.strip():
            return ParsedDiff(
                files=[],
                stats=DiffStats(
                    files_changed=0,
                    total_additions=0,
                    total_deletions=0,
                ),
                raw=diff_text,
            )

        file_diffs = self._split_into_file_diffs(diff_text)
        parsed_files = [self._parse_file_diff(fd) for fd in file_diffs]

        # 통계 집계
        total_additions = sum(f.additions for f in parsed_files)
        total_deletions = sum(f.deletions for f in parsed_files)

        return ParsedDiff(
            files=parsed_files,
            stats=DiffStats(
                files_changed=len(parsed_files),
                total_additions=total_additions,
                total_deletions=total_deletions,
            ),
            raw=diff_text,
        )

    def _split_into_file_diffs(self, diff_text: str) -> list[str]:
        """Diff 텍스트를 파일별로 분리."""
        # diff --git 으로 시작하는 부분을 기준으로 분리
        parts = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
        return [part for part in parts if part.strip().startswith("diff --git")]

    def _parse_file_diff(self, file_diff_text: str) -> FileDiff:
        """개별 파일 diff를 파싱."""
        # 파일 경로 추출
        header_match = self._FILE_HEADER_PATTERN.search(file_diff_text)
        if not header_match:
            raise ValueError("Invalid diff format: no file header found")

        new_path = header_match.group(2)

        # 변경 타입 감지
        change_type = self._detect_change_type(file_diff_text)

        # renamed인 경우 경로 처리
        old_path_result: Path | None = None
        if change_type == ChangeType.RENAMED:
            rename_from = self._RENAME_FROM_PATTERN.search(file_diff_text)
            rename_to = self._RENAME_TO_PATTERN.search(file_diff_text)
            if rename_from and rename_to:
                old_path_result = Path(rename_from.group(1))
                new_path = rename_to.group(1)

        # 바이너리 파일 체크
        is_binary = bool(self._BINARY_PATTERN.search(file_diff_text))

        # Hunk 파싱 (바이너리가 아닌 경우만)
        hunks: list[DiffHunk] = []
        additions = 0
        deletions = 0

        if not is_binary:
            hunks = self._parse_hunks(file_diff_text)
            additions, deletions = self._count_changes(hunks)

        return FileDiff(
            path=Path(new_path),
            change_type=change_type,
            old_path=old_path_result,
            additions=additions,
            deletions=deletions,
            hunks=hunks,
        )

    def _detect_change_type(self, file_diff_text: str) -> ChangeType:
        """파일 변경 타입 감지."""
        if self._NEW_FILE_PATTERN.search(file_diff_text):
            return ChangeType.ADDED
        if self._DELETED_FILE_PATTERN.search(file_diff_text):
            return ChangeType.DELETED
        is_rename = self._SIMILARITY_PATTERN.search(
            file_diff_text
        ) or self._RENAME_FROM_PATTERN.search(file_diff_text)
        if is_rename:
            return ChangeType.RENAMED
        return ChangeType.MODIFIED

    def _parse_hunks(self, file_diff_text: str) -> list[DiffHunk]:
        """Hunk 블록들을 파싱."""
        hunks: list[DiffHunk] = []

        # 모든 hunk 헤더 위치 찾기
        hunk_matches = list(self._HUNK_HEADER_PATTERN.finditer(file_diff_text))

        for i, match in enumerate(hunk_matches):
            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1

            # Hunk 내용 추출 (다음 hunk 또는 파일 끝까지)
            start_pos = match.end()
            if i + 1 < len(hunk_matches):
                end_pos = hunk_matches[i + 1].start()
            else:
                end_pos = len(file_diff_text)

            content = file_diff_text[start_pos:end_pos].strip()

            hunks.append(
                DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    content=content,
                )
            )

        return hunks

    def _count_changes(self, hunks: list[DiffHunk]) -> tuple[int, int]:
        """Hunk들에서 추가/삭제 라인 수 계산."""
        additions = 0
        deletions = 0

        for hunk in hunks:
            for line in hunk.content.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

        return additions, deletions

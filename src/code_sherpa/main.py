"""Code-Sherpa CLI 엔트리포인트."""

import click
from rich.console import Console

from code_sherpa import __version__
from code_sherpa.shared.config import (
    get_config_for_project,
    get_config_path,
    load_config,
)
from code_sherpa.shared.output import get_formatter

console = Console()


class Context:
    """CLI 컨텍스트."""

    def __init__(self):
        self.config = None
        self.format = "console"
        self.verbose = False
        self.project_name = None
        self.project_path = None


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="설정 파일 경로",
)
@click.option(
    "--project",
    "-p",
    type=str,
    help="사용할 프로젝트 이름",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["console", "json", "markdown"]),
    default="console",
    help="출력 형식",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="상세 출력",
)
@click.version_option(version=__version__, prog_name="code-sherpa")
@pass_context
def cli(
    ctx: Context,
    config: str | None,
    project: str | None,
    format: str,
    verbose: bool,
):
    """Code-Sherpa: Git 저장소 분석 및 AI 기반 Multi-Agent 코드 리뷰 도구."""
    from pathlib import Path

    ctx.format = format
    ctx.verbose = verbose
    ctx.project_name = project

    if project:
        # 프로젝트 지정 시 프로젝트 설정 로드
        try:
            ctx.config, ctx.project_path = get_config_for_project(project)
            # 경로 유효성 검사
            if not ctx.project_path.exists():
                console.print(
                    f"[yellow]경고:[/yellow] 프로젝트 경로가 존재하지 않습니다: "
                    f"{ctx.project_path}"
                )
        except ValueError as e:
            console.print(f"[red]오류:[/red] {e}")
            raise click.Abort()
    else:
        ctx.config = load_config(Path(config) if config else None)
        ctx.project_path = None


# ============================================================
# Analyze 명령어 그룹
# ============================================================


@cli.group()
@pass_context
def analyze(ctx: Context):
    """저장소 및 파일 분석."""
    pass


@analyze.command("repo")
@click.argument("path", default=None, type=click.Path(exists=True), required=False)
@pass_context
def analyze_repo(ctx: Context, path: str | None):
    """저장소 전체 요약 분석."""
    from pathlib import Path

    from code_sherpa.analyze import RepoSummarizer

    # 프로젝트 경로 우선, 없으면 인자, 없으면 현재 디렉토리
    target_path = ctx.project_path or (Path(path) if path else Path.cwd())
    console.print(f"[bold]저장소 분석:[/bold] {target_path}")

    try:
        summarizer = RepoSummarizer()
        result = summarizer.summarize_sync(target_path)

        formatter = get_formatter(ctx.format)
        output = formatter.format(result)
        if ctx.format == "console":
            # Console formatter already prints
            pass
        else:
            console.print(output)
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        raise click.Abort()


@analyze.command("file")
@click.argument("file_path", type=click.Path(exists=True))
@pass_context
def analyze_file(ctx: Context, file_path: str):
    """개별 파일 설명."""
    from pathlib import Path

    from code_sherpa.analyze import FileExplainer

    console.print(f"[bold]파일 분석:[/bold] {file_path}")

    try:
        explainer = FileExplainer()
        result = explainer.explain_sync(Path(file_path))

        formatter = get_formatter(ctx.format)
        output = formatter.format(result)
        if ctx.format != "console":
            console.print(output)
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        raise click.Abort()


@analyze.command("structure")
@click.argument("path", default=None, type=click.Path(exists=True), required=False)
@pass_context
def analyze_structure(ctx: Context, path: str | None):
    """코드 구조 분석."""
    from pathlib import Path

    from code_sherpa.analyze import StructureAnalyzer

    target_path = ctx.project_path or (Path(path) if path else Path.cwd())
    console.print(f"[bold]구조 분석:[/bold] {target_path}")

    try:
        analyzer = StructureAnalyzer()
        exclude_patterns = ctx.config.analyze.exclude_patterns if ctx.config else None
        result = analyzer.analyze(target_path, exclude_patterns=exclude_patterns)

        # 구조 출력 (트리 형식)
        _print_structure_tree(result.root)

        if result.entry_points:
            console.print("\n[bold]엔트리포인트:[/bold]")
            for ep in result.entry_points:
                console.print(f"  - {ep}")

        if result.dependencies and ctx.verbose:
            console.print(f"\n[bold]의존성:[/bold] {len(result.dependencies)}개")
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        raise click.Abort()


def _print_structure_tree(node, prefix: str = "", is_last: bool = True):
    """구조 트리 출력."""
    connector = "└── " if is_last else "├── "
    icon = "📁 " if node.node_type == "directory" else "📄 "
    if node.node_type == "module":
        icon = "📦 "
    console.print(f"{prefix}{connector}{icon}{node.name}")

    new_prefix = prefix + ("    " if is_last else "│   ")
    children = sorted(node.children, key=lambda x: (x.node_type != "directory", x.name))
    for i, child in enumerate(children):
        _print_structure_tree(child, new_prefix, i == len(children) - 1)


@analyze.command("quality")
@click.argument("path", default=None, type=click.Path(exists=True), required=False)
@pass_context
def analyze_quality(ctx: Context, path: str | None):
    """코드 품질 분석."""
    from pathlib import Path

    from code_sherpa.analyze import QualityAnalyzer

    target_path = ctx.project_path or (Path(path) if path else Path.cwd())
    console.print(f"[bold]품질 분석:[/bold] {target_path}")

    try:
        analyzer = QualityAnalyzer()
        result = analyzer.analyze_sync(target_path)

        formatter = get_formatter(ctx.format)
        output = formatter.format(result)
        if ctx.format != "console":
            console.print(output)
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        raise click.Abort()


# ============================================================
# Review 명령어
# ============================================================


@cli.command()
@click.argument("commit_range", required=False)
@click.option("--staged", is_flag=True, help="스테이지된 변경만 리뷰")
@click.option(
    "--agents",
    "-a",
    multiple=True,
    help="사용할 에이전트 (기본: architect, security)",
)
@click.option("--no-summary", is_flag=True, help="종합 요약 생성 안 함")
@click.option("--sequential", is_flag=True, help="에이전트를 순차적으로 실행")
@pass_context
def review(
    ctx: Context,
    commit_range: str | None,
    staged: bool,
    agents: tuple,
    no_summary: bool,
    sequential: bool,
):
    """AI 기반 Multi-Agent 코드 리뷰."""
    from code_sherpa.review import run_review_sync

    agent_list = list(agents) if agents else ctx.config.review.default_agents
    parallel = not sequential and ctx.config.review.parallel

    if staged:
        console.print("[bold]스테이지된 변경 리뷰[/bold]")
    elif commit_range:
        console.print(f"[bold]커밋 범위 리뷰:[/bold] {commit_range}")
    else:
        console.print("[bold]작업 디렉토리 변경 리뷰[/bold]")

    console.print(f"[dim]에이전트: {', '.join(agent_list)}[/dim]")

    # 프로젝트 경로 사용
    target_path = ctx.project_path or "."

    try:
        with console.status("[bold green]리뷰 진행 중..."):
            result = run_review_sync(
                path=target_path,
                staged=staged,
                commit_range=commit_range,
                agents=agent_list,
                parallel=parallel,
                summarize=not no_summary,
            )

        formatter = get_formatter(ctx.format)
        output = formatter.format(result)
        if ctx.format != "console":
            console.print(output)
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        if ctx.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise click.Abort()


# ============================================================
# Config 명령어 그룹
# ============================================================


@cli.group()
@pass_context
def config(ctx: Context):
    """설정 관리."""
    pass


@config.command("show")
@pass_context
def config_show(ctx: Context):
    """현재 설정 표시."""
    config_path = get_config_path()

    if config_path:
        console.print(f"[bold]설정 파일:[/bold] {config_path}")
    else:
        console.print("[dim]설정 파일 없음 (기본값 사용)[/dim]")

    console.print()
    console.print("[bold]LLM 설정:[/bold]")
    console.print(f"  Provider: {ctx.config.llm.provider}")
    console.print(f"  Model: {ctx.config.llm.model}")

    console.print()
    console.print("[bold]리뷰 설정:[/bold]")
    console.print(f"  기본 에이전트: {', '.join(ctx.config.review.default_agents)}")
    console.print(f"  병렬 실행: {ctx.config.review.parallel}")


@config.command("init")
@click.option("--force", is_flag=True, help="기존 파일 덮어쓰기")
@pass_context
def config_init(ctx: Context, force: bool):
    """설정 파일 초기화."""
    import shutil
    from pathlib import Path

    target = Path.cwd() / ".code-sherpa.yaml"
    example = Path(__file__).parent.parent.parent.parent / ".code-sherpa.yaml.example"

    if target.exists() and not force:
        console.print(f"[red]설정 파일이 이미 존재합니다:[/red] {target}")
        console.print("[dim]--force 옵션으로 덮어쓰기 가능[/dim]")
        return

    if example.exists():
        shutil.copy(example, target)
        console.print(f"[green]설정 파일 생성됨:[/green] {target}")
    else:
        console.print("[red]예제 설정 파일을 찾을 수 없습니다.[/red]")


# ============================================================
# Project 명령어 그룹
# ============================================================


@cli.group()
@pass_context
def project(ctx: Context):
    """프로젝트 관리."""
    pass


@project.command("add")
@click.argument("name")
@click.argument("path", type=click.Path(exists=True))
@pass_context
def project_add(ctx: Context, name: str, path: str):
    """프로젝트 등록."""
    from code_sherpa.shared.config import add_project

    try:
        add_project(name, path)
        console.print(f"[green]프로젝트 등록됨:[/green] {name} → {path}")
    except ValueError as e:
        console.print(f"[red]오류:[/red] {e}")
        raise click.Abort()


@project.command("remove")
@click.argument("name")
@pass_context
def project_remove(ctx: Context, name: str):
    """프로젝트 등록 해제."""
    from code_sherpa.shared.config import remove_project

    try:
        remove_project(name)
        console.print(f"[green]프로젝트 삭제됨:[/green] {name}")
    except ValueError as e:
        console.print(f"[red]오류:[/red] {e}")
        raise click.Abort()


@project.command("list")
@pass_context
def project_list(ctx: Context):
    """등록된 프로젝트 목록."""
    from code_sherpa.shared.config import list_projects

    projects = list_projects()

    if not projects:
        console.print("[dim]등록된 프로젝트가 없습니다.[/dim]")
        console.print("\n프로젝트 추가: code-sherpa project add <name> <path>")
        return

    console.print("[bold]등록된 프로젝트:[/bold]\n")
    for name, path, is_valid in projects:
        status = "" if is_valid else " [yellow](경로 없음)[/yellow]"
        console.print(f"  [cyan]{name:20}[/cyan] {path}{status}")

    console.print(f"\n총 {len(projects)}개 프로젝트")


@project.command("show")
@click.argument("name")
@pass_context
def project_show(ctx: Context, name: str):
    """프로젝트 상세 정보."""
    from pathlib import Path

    from code_sherpa.shared.config import get_project

    proj = get_project(name)

    if not proj:
        console.print(f"[red]존재하지 않는 프로젝트:[/red] {name}")
        raise click.Abort()

    path_exists = Path(proj.path).exists()
    path_status = "" if path_exists else " [yellow](경로 없음)[/yellow]"

    console.print(f"[bold]프로젝트:[/bold] {proj.name}")
    console.print(f"[bold]경로:[/bold] {proj.path}{path_status}")

    console.print("\n[bold]LLM 설정:[/bold]")
    if proj.llm:
        console.print(f"  Provider: {proj.llm.provider}")
        console.print(f"  Model: {proj.llm.model}")
    else:
        console.print("  [dim](기본값 사용)[/dim]")

    console.print("\n[bold]분석 설정:[/bold]")
    if proj.analyze:
        patterns = ", ".join(proj.analyze.exclude_patterns)
        console.print(f"  제외 패턴: {patterns}")
    else:
        console.print("  [dim](기본값 사용)[/dim]")

    console.print("\n[bold]리뷰 설정:[/bold]")
    if proj.review:
        agents = ", ".join(proj.review.default_agents)
        console.print(f"  기본 에이전트: {agents}")
        console.print(f"  병렬 실행: {proj.review.parallel}")
    else:
        console.print("  [dim](기본값 사용)[/dim]")


if __name__ == "__main__":
    cli()

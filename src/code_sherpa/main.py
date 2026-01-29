"""Code-Sherpa CLI 엔트리포인트."""

import click
from rich.console import Console

from code_sherpa import __version__
from code_sherpa.shared.config import get_config_path, load_config
from code_sherpa.shared.output import get_formatter

console = Console()


class Context:
    """CLI 컨텍스트."""

    def __init__(self):
        self.config = None
        self.format = "console"
        self.verbose = False


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="설정 파일 경로",
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
def cli(ctx: Context, config: str | None, format: str, verbose: bool):
    """Code-Sherpa: Git 저장소 분석 및 AI 기반 Multi-Agent 코드 리뷰 도구."""
    from pathlib import Path

    ctx.config = load_config(Path(config) if config else None)
    ctx.format = format
    ctx.verbose = verbose


# ============================================================
# Analyze 명령어 그룹
# ============================================================


@cli.group()
@pass_context
def analyze(ctx: Context):
    """저장소 및 파일 분석."""
    pass


@analyze.command("repo")
@click.argument("path", default=".", type=click.Path(exists=True))
@pass_context
def analyze_repo(ctx: Context, path: str):
    """저장소 전체 요약 분석."""
    from pathlib import Path

    from code_sherpa.analyze import RepoSummarizer

    console.print(f"[bold]저장소 분석:[/bold] {path}")

    try:
        summarizer = RepoSummarizer()
        result = summarizer.summarize_sync(Path(path))

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
@click.argument("path", default=".", type=click.Path(exists=True))
@pass_context
def analyze_structure(ctx: Context, path: str):
    """코드 구조 분석."""
    from pathlib import Path

    from code_sherpa.analyze import StructureAnalyzer

    console.print(f"[bold]구조 분석:[/bold] {path}")

    try:
        analyzer = StructureAnalyzer()
        exclude_patterns = ctx.config.analyze.exclude_patterns if ctx.config else None
        result = analyzer.analyze(Path(path), exclude_patterns=exclude_patterns)

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
@click.argument("path", default=".", type=click.Path(exists=True))
@pass_context
def analyze_quality(ctx: Context, path: str):
    """코드 품질 분석."""
    from pathlib import Path

    from code_sherpa.analyze import QualityAnalyzer

    console.print(f"[bold]품질 분석:[/bold] {path}")

    try:
        analyzer = QualityAnalyzer()
        result = analyzer.analyze_sync(Path(path))

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

    try:
        with console.status("[bold green]리뷰 진행 중..."):
            result = run_review_sync(
                path=".",
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


if __name__ == "__main__":
    cli()

# Code-Sherpa

Git 저장소 분석 및 AI 기반 Multi-Agent 코드 리뷰 CLI 도구

## 설치

```bash
# uv 사용 (권장)
uv sync

# pip 사용
pip install -e .
```

## 빠른 시작

```bash
# 저장소 구조 분석
code-sherpa analyze structure .

# 코드 품질 분석
code-sherpa analyze quality .

# AI 코드 리뷰 (staged 변경사항)
code-sherpa review --staged

# 특정 커밋 범위 리뷰
code-sherpa review HEAD~3..HEAD
```

## 기능

### 분석 (Analyze)

| 명령어 | 설명 |
|--------|------|
| `analyze repo <path>` | 저장소 전체 요약 (언어 통계, 최근 커밋, AI 요약) |
| `analyze file <file>` | 개별 파일 설명 (목적, 핵심 요소, 상세 설명) |
| `analyze structure <path>` | 코드 구조 트리 (모듈, 의존성, 엔트리포인트) |
| `analyze quality <path>` | 코드 품질 분석 (복잡도, 이슈 감지, 점수) |

### 리뷰 (Review)

Multi-Agent 시스템으로 다양한 관점에서 코드를 리뷰합니다:

| 에이전트 | 관점 |
|----------|------|
| `architect` | 설계 패턴, 모듈화, SOLID 원칙 |
| `security` | 보안 취약점, 인증, 데이터 보호 |
| `performance` | 알고리즘 복잡도, 메모리, I/O 최적화 |
| `junior` | 가독성, 네이밍, 문서화, 베스트 프랙티스 |

```bash
# 기본 에이전트로 리뷰 (architect, security)
code-sherpa review --staged

# 특정 에이전트 선택
code-sherpa review -a security -a performance

# 모든 에이전트 사용
code-sherpa review -a architect -a security -a performance -a junior
```

### 설정 (Config)

```bash
# 현재 설정 확인
code-sherpa config show

# 설정 파일 초기화
code-sherpa config init
```

## 설정 파일

`.code-sherpa.yaml` 파일로 설정을 관리합니다:

```yaml
llm:
  provider: openai          # openai 또는 anthropic
  model: gpt-4
  api_key_env: OPENAI_API_KEY
  max_tokens: 4096
  temperature: 0.3

analyze:
  exclude_patterns:
    - node_modules
    - .git
    - __pycache__
    - "*.pyc"
  max_file_size_kb: 500

review:
  default_agents:
    - architect
    - security
  parallel: true
  max_diff_lines: 1000

output:
  default_format: console   # console, json, markdown
  color: true
```

## 출력 형식

```bash
# 콘솔 출력 (기본)
code-sherpa analyze repo .

# JSON 출력 (파이프라인용)
code-sherpa -f json analyze repo . | jq '.languages'

# Markdown 출력
code-sherpa -f markdown review --staged > review.md
```

## 환경 변수

```bash
# OpenAI 사용 시
export OPENAI_API_KEY=sk-...

# Anthropic 사용 시
export ANTHROPIC_API_KEY=sk-ant-...
```

## 프로젝트 구조

```
src/code_sherpa/
├── main.py                 # CLI 엔트리포인트
├── analyze/                # 분석 모듈
│   ├── repo_summary.py     # 저장소 요약
│   ├── file_explainer.py   # 파일 설명
│   ├── structure.py        # 구조 분석
│   └── quality.py          # 품질 분석
├── review/                 # 리뷰 모듈
│   ├── diff_parser.py      # Diff 파서
│   ├── runner.py           # 리뷰 실행기
│   └── agents/             # 리뷰 에이전트
│       ├── base.py         # 베이스 클래스
│       ├── architect.py    # 아키텍처 에이전트
│       ├── security.py     # 보안 에이전트
│       ├── performance.py  # 성능 에이전트
│       └── junior.py       # 주니어 에이전트
├── shared/                 # 공유 모듈
│   ├── config.py           # 설정 관리
│   ├── models.py           # 데이터 모델
│   ├── git.py              # Git 클라이언트
│   ├── output.py           # 출력 포매터
│   └── llm/                # LLM 어댑터
│       ├── base.py         # 베이스 클래스
│       ├── openai.py       # OpenAI 어댑터
│       └── anthropic.py    # Anthropic 어댑터
└── prompts/                # 프롬프트 템플릿
    ├── analyze/            # 분석용 프롬프트
    └── review/             # 리뷰용 프롬프트
```

## 개발

```bash
# 의존성 설치
uv sync

# 테스트 실행
uv run pytest

# 린트 검사
uv run ruff check .

# 포맷 검사
uv run ruff format --check .
```

## 요구사항

- Python 3.12+
- Git

## 라이선스

MIT License

# Code-Sherpa 테스트 가이드

전역 설치 전에 로컬에서 code-sherpa를 테스트하는 방법을 설명합니다.

## 사전 준비

### 1. 의존성 설치

```bash
cd /Volumes/Projects/personal-projects/code-sherpa
uv sync
```

### 2. 환경 변수 설정

AI 기능(analyze repo, review)을 테스트하려면 LLM API 키가 필요합니다.

```bash
# OpenAI 사용 시
export OPENAI_API_KEY=sk-...

# 또는 Anthropic 사용 시
export ANTHROPIC_API_KEY=sk-ant-...
```

## 테스트 방법

### 방법 1: uv run 사용 (권장)

프로젝트 디렉토리에서:

```bash
# 도움말 확인
uv run code-sherpa --help

# 버전 확인
uv run code-sherpa --version
```

### 방법 2: python -m 사용

```bash
uv run python -m code_sherpa.main --help
```

### 방법 3: 다른 디렉토리에서 테스트

```bash
# 다른 프로젝트로 이동
cd ~/other-project

# code-sherpa 경로 지정하여 실행
uv run --project /Volumes/Projects/personal-projects/code-sherpa code-sherpa analyze structure .
```

## 기능별 테스트

### 1. 구조 분석 (LLM 불필요)

```bash
uv run code-sherpa analyze structure .
```

예상 출력:
```
구조 분석: .
└── 📁 code-sherpa
    ├── 📁 src
    │   └── 📦 code_sherpa
    │       ├── 📄 __init__.py
    │       ├── 📦 analyze
    ...
```

### 2. 품질 분석 (LLM 불필요)

```bash
uv run code-sherpa analyze quality .
```

예상 출력: 복잡도 점수, 코드 이슈 목록

### 3. 설정 확인 (LLM 불필요)

```bash
uv run code-sherpa config show
```

예상 출력:
```
설정 파일 없음 (기본값 사용)

LLM 설정:
  Provider: openai
  Model: gpt-4

리뷰 설정:
  기본 에이전트: architect, security
  병렬 실행: True
```

### 4. 저장소 요약 (LLM 필요)

```bash
uv run code-sherpa analyze repo .
```

### 5. 파일 설명 (LLM 필요)

```bash
uv run code-sherpa analyze file src/code_sherpa/main.py
```

### 6. 코드 리뷰 (LLM 필요)

```bash
# staged 변경사항 리뷰
uv run code-sherpa review --staged

# 특정 커밋 범위 리뷰
uv run code-sherpa review HEAD~1..HEAD

# 특정 에이전트만 사용
uv run code-sherpa review --staged -a security
```

## 출력 형식 테스트

```bash
# JSON 출력
uv run code-sherpa -f json analyze structure . | jq .

# Markdown 출력
uv run code-sherpa -f markdown analyze quality .
```

## 단위 테스트 실행

```bash
# 전체 테스트
uv run pytest

# 특정 모듈 테스트
uv run pytest tests/unit/analyze/
uv run pytest tests/unit/review/

# 상세 출력
uv run pytest -v

# 커버리지 포함
uv run pytest --cov=code_sherpa
```

## 린트 및 포맷 검사

```bash
# 린트 검사
uv run ruff check .

# 포맷 검사
uv run ruff format --check .

# 자동 수정
uv run ruff check --fix .
uv run ruff format .
```

## 문제 해결

### LLM API 키 오류

```
ValueError: OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.
```

→ 환경 변수 설정 확인:
```bash
echo $OPENAI_API_KEY
```

### 모듈 import 오류

```
ModuleNotFoundError: No module named 'code_sherpa'
```

→ 의존성 재설치:
```bash
uv sync
```

### Git 저장소 오류

```
InvalidRepositoryError: 유효하지 않은 Git 저장소입니다
```

→ Git 저장소 디렉토리에서 실행 확인:
```bash
git status
```

## 테스트 체크리스트

전역 설치 전 확인 사항:

- [ ] `uv run pytest` - 모든 테스트 통과 (222개)
- [ ] `uv run ruff check .` - 린트 오류 없음
- [ ] `uv run code-sherpa --help` - CLI 도움말 출력
- [ ] `uv run code-sherpa analyze structure .` - 구조 분석 작동
- [ ] `uv run code-sherpa analyze quality .` - 품질 분석 작동
- [ ] `uv run code-sherpa config show` - 설정 표시 작동
- [ ] (선택) LLM 기능 테스트 - API 키 설정 후 확인

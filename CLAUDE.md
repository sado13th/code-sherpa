# code-sherpa

## 개요

명령줄 인터페이스 도구.

## 기술 스택

- **프로젝트 유형**: CLI Tool
- **언어**: Python 3.12
- **패키지 매니저**: uv
- **테스트 프레임워크**: pytest
- **프로젝트 규모**: Standard (일반 구조)

## 명령어

### 설치
```bash
uv sync
```

### 개발
```bash
uv run python -m code_sherpa.main
```

### 테스트
```bash
uv run pytest
```

### 린트
```bash
uv run ruff check . && uv run ruff format --check .
```

## 프로젝트 구조

```
src/code_sherpa/  - 메인 소스 코드
tests/                - 테스트 파일
pyproject.toml        - 프로젝트 설정
```

## 코드 스타일

- 함수 시그니처에 타입 힌트 사용
- PEP 8 스타일 가이드 준수
- ruff로 린트 및 포맷팅
- 최대 줄 길이: 88자

## 규칙

- 프로젝트의 기존 패턴과 컨벤션을 따를 것
- 새로운 기능에는 테스트를 작성할 것
- 함수는 단일 책임 원칙을 지킬 것
- 의미 있는 변수명과 함수명을 사용할 것
- 공개 API와 복잡한 로직은 문서화할 것

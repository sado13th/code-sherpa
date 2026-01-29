#!/bin/bash

# Python 개발 환경 활성화 및 Claude 실행 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv"

# venv 존재 확인
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ .venv가 없습니다. 먼저 'uv sync'를 실행하세요."
    exit 1
fi

# venv 활성화
source "$VENV_PATH/bin/activate"
echo "✓ venv 활성화됨: $VIRTUAL_ENV"

# Claude 프로필 선택
echo ""
echo "Claude 프로필을 선택하세요:"
echo "  1) claude-work"
echo "  2) claude-personal"
echo ""
read -p "선택 (1/2): " choice

case $choice in
    1)
        echo ""
        echo "🚀 claude-work 실행..."
        claude-work
        ;;
    2)
        echo ""
        echo "🚀 claude-personal 실행..."
        claude-personal
        ;;
    *)
        echo "❌ 잘못된 선택입니다. 1 또는 2를 입력하세요."
        exit 1
        ;;
esac

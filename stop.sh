#!/bin/bash

# Python venv 비활성화 스크립트

if [ -n "$VIRTUAL_ENV" ]; then
    echo "✓ venv 비활성화: $VIRTUAL_ENV"
    deactivate
else
    echo "ℹ️  활성화된 venv가 없습니다."
fi

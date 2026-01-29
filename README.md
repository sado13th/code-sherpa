# code-sherpa

A Python project.

## Requirements

- Python 3.12+
- [mise](https://mise.jdx.dev/) (recommended for version management)

## Setup

```bash
# Install mise (if not already installed)
curl https://mise.run | sh

# Install dependencies
mise install\nuv sync
```

## Development

```bash
uv run python -m code_sherpa.main
```

## Testing

```bash
uv run pytest
```

## Project Structure

```
code-sherpa/
├── src/
│   └── code_sherpa/
│       ├── __init__.py
│       └── main.py
├── tests/
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

## License

This project is licensed under the NO LICENSE License.

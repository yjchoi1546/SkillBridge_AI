"""프롬프트 로더. 프롬프트 본문은 이 폴더의 .md 파일에 둔다.

    load_prompt("generation/analyze_request")  ->  prompts/generation/analyze_request.md
"""

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8")

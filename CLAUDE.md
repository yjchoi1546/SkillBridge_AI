# SkillBridge AI 협업 지침

3인 팀 프로젝트 (AI 개발자 2명 + 풀스택 1명). 각자 자기 로컬에서 Claude Code를 돌린다.
**한 저장소를 세 사람이 동시에 건드리므로, 폴더 소유권이 이 문서의 핵심이다.**

## 소유권

| 영역 | 담당 | 경로 |
| --- | --- | --- |
| AI-A (과제 생성) | AI 개발자 A (미정) | `ai/src/graphs/generation/`, `ai/src/datagen/`, `ai/src/prompts/generation/`, `ai/src/validation/spec_rules.py`, `ai/tests/generation/` |
| AI-B (평가) | AI 개발자 B (미정) | `ai/src/graphs/evaluation/`, `ai/src/sandbox/`, `ai/src/prompts/evaluation/`, `ai/src/validation/submission_rules.py`, `ai/tests/evaluation/` |
| AI 공용 | AI 두 명 합의 | `ai/` 의 나머지 (`schemas.py`, `api/`, `core/`, `llms/`, `benchmarks/`, `ai/tests/fixtures/` 등), `labs/`, `data/` |
| App | 풀스택 개발자 | `app/` (frontend + backend) |
| 공용 | 세 명 합의 | 루트 파일 (`main.py`, `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `.gitignore`), `.claude/` |

- AI-A / AI-B 는 서로의 영역을 읽기만 한다. App 과의 경계와 같은 규칙이다.
- AI 공용은 두 AI 담당 중 누구든 수정할 수 있지만, 수정 전에 상대 AI 담당과 합의한다.
  그중 `ai/src/schemas.py`, `ai/src/api/` 는 App 과의 접점이므로 App 담당과도 합의한다.
- `labs/` 노트북은 각자 이름 접두사를 붙여 만든다 (예: `labs/a_prompt_test.ipynb`). 남의 노트북은 수정하지 않는다.

## 경계 규칙 (가장 중요)

1. **담당이 아닌 영역의 파일은 읽기만 한다.** Edit / Write / NotebookEdit 금지.
   Bash·PowerShell로 우회하는 것도 금지 — `rm`, `mv`, `cp`, `>` 리다이렉트, `sed -i`,
   `Set-Content`, `Remove-Item`, 포매터/린터의 `--fix`를 상대 영역 경로에 실행하지 않는다.
2. 상대 영역에 문제가 보이면 **직접 고치지 말고, 무엇을 왜 바꿔야 하는지만 사용자에게 보고**한다.
   "제가 대신 수정해두겠습니다"는 이 프로젝트에서 금지된 행동이다.
3. **공용 파일은 수정 전에 사용자에게 팀원과 합의했는지 확인한다.**
   특히 `pyproject.toml` / `uv.lock`은 양쪽이 같이 쓰므로 말 없이 의존성을 추가하지 않는다.
4. 내 영역 안에서는 자유롭게 작업한다. 상대 영역과 맞추려고 내 코드를 임의로 리팩터링하지 않는다.
5. 경계 때문에 작업이 막히면, 막힌 지점까지 끝내고 **남은 부분과 이유를 명시**한다.
   경계를 넘어서 "완성"하지 않는다.

이 규칙은 `.claude/settings.local.json`의 권한 deny로도 이중 차단되어 있다
(설정 방법은 아래 "환경 세팅" 참고). 지침과 권한 중 하나라도 막으면 그건 하지 않는다.

## ai/ ↔ app/ 접점

두 영역이 서로의 내부 구현에 의존하지 않도록, 접점은 한 곳으로 고정한다.

- **`ai/src/api/` 가 AI 영역의 유일한 공개 진입점.**
  `app/backend`는 이 계층만 호출한다. `ai/src/graphs`, `ai/src/rag`, `ai/src/llms` 등
  내부 모듈을 app에서 직접 import 하지 않는다.
- 접점 시그니처(입출력 스키마)를 바꿔야 하면 **AI·App 합의 후** 변경한다. AI 담당이 먼저
  `ai/src/api/`에 새 형태를 추가하고, App 담당이 옮겨간 뒤 옛 형태를 제거한다.
- 공개 함수·입출력 타입·호출 순서는 [ai/CONTRACT.md](ai/CONTRACT.md)에 둔다.
  App 은 `.env` 에 `LLM_PROVIDER=fake` 를 두면 LLM 키 없이 실제와 같은 형태의 결과로 개발할 수 있다.
- 접점이 바뀌면 이 문서의 이 절과 `ai/CONTRACT.md` 를 같이 갱신한다.

## Git

커밋 메시지·브랜치 이름·작업 순서는 [CONTRIBUTING.md](CONTRIBUTING.md)를 따른다.
**작업은 `type/작업명` 브랜치에서 한다** (예: `feat/user-login`). PR·코드 리뷰는 없다.

- **작업 시작 전 최신 main 에서 브랜치를 딴다.** `git switch main` → `git pull origin main`
  → `git switch -c feat/기능명`. 낡은 main 에서 따면 merge 때 충돌이 커진다.
- **main 에 merge 하기 전 최신 main 을 브랜치에 반영**하고 충돌을 해결한다.
  merge 후 main 을 push 하고, 쓴 브랜치는 로컬·원격 모두 삭제한다.
- **한 커밋에 두 영역을 섞지 않는다.** 공용 파일 변경은 별도 커밋으로 분리한다.
- force push는 금지 — 상대 커밋을 날린다. push 가 거부되면 pull 로 최신을 받은 뒤 다시 push 한다.
- 커밋·push·merge는 사용자가 요청할 때만 한다. Claude가 알아서 하지 않는다.

## 명령어

Python은 `uv`로 관리한다 (`uv.lock` 기준, Python 3.12+).

```bash
uv sync                  # 의존성 설치
uv run python main.py    # 실행
uv run pytest            # 테스트 (LLM 은 가짜 모드라 키·비용 없음)
```

- `ai/`: `ai/requirements.txt`는 Docker 이미지용이다. 로컬 개발은 위 `uv`를 쓴다.
- `app/`: 스택 미정 (TBD). 정해지면 App 담당이 [app/CLAUDE.md](app/CLAUDE.md)에 명령어를 적는다.

## 환경 세팅 (각자 클론 후 1회)

`.claude/settings.local.json`은 gitignore 되어 있어 사람마다 다르게 둘 수 있다.
자기 역할에 맞는 템플릿을 복사한다.

```powershell
# AI 개발자 A (과제 생성)
Copy-Item .claude/templates/settings.ai-a.json .claude/settings.local.json

# AI 개발자 B (평가)
Copy-Item .claude/templates/settings.ai-b.json .claude/settings.local.json

# App 담당 (풀스택)
Copy-Item .claude/templates/settings.app.json .claude/settings.local.json
```

AI 역할(A/B)이 정해지기 전에는 `settings.ai.json`(app/ 만 차단)을 임시로 쓴다.

복사 후 **Claude Code를 재시작**해야 권한 설정이 적용된다.
적용 확인: `/permissions`에 상대 영역 deny 규칙이 보이면 정상.

## 기타

- 이 문서는 모든 세션 컨텍스트에 로드된다. 길어지지 않게 관리한다.
- 영역별 상세 규칙은 [ai/CLAUDE.md](ai/CLAUDE.md), [app/CLAUDE.md](app/CLAUDE.md)에 둔다.
  해당 폴더에서 작업할 때 자동으로 함께 로드된다.
- `.env`는 커밋하지 않는다. 필요한 키가 생기면 `.env.example`에 키 이름만 추가한다.

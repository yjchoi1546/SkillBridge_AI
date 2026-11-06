# .claude/templates

클론 후 자기 역할에 맞는 파일을 `.claude/settings.local.json`으로 복사한다.
`settings.local.json`은 gitignore 되므로 사람마다 다르게 유지된다.

```powershell
# AI 개발자 A (과제 생성) — app/ + AI-B 영역 수정 차단
Copy-Item .claude/templates/settings.ai-a.json .claude/settings.local.json

# AI 개발자 B (평가) — app/ + AI-A 영역 수정 차단
Copy-Item .claude/templates/settings.ai-b.json .claude/settings.local.json

# App 담당 (풀스택) — ai/, labs/, data/ 수정 차단
Copy-Item .claude/templates/settings.app.json .claude/settings.local.json

# AI 역할(A/B) 정하기 전 임시 — app/ 만 차단
Copy-Item .claude/templates/settings.ai.json .claude/settings.local.json
```

영역 경로는 루트 `CLAUDE.md`의 소유권 표와 맞춘다. 표를 바꾸면 이 템플릿들도 같이 고친다.

복사 후 **Claude Code 재시작**. `/permissions`에서 deny 규칙이 보이면 적용된 것이다.

## 알아둘 것

- 경로의 앞 `/`는 파일시스템 루트가 아니라 **프로젝트 루트** 기준이다 (`Edit(/app/**)` = `<repo>/app/**`).
- `Edit(...)` 규칙 하나가 Edit / Write / MultiEdit / NotebookEdit을 모두 커버한다.
  `Write(...)`, `NotebookEdit(...)`으로 따로 쓰면 Claude Code가 무시하고 경고만 낸다.
- 이 deny는 파일 도구와, Claude Code가 인식하는 셸 파일 명령(`cat`, `sed`, `tee`, `> file` 등)까지 막는다.
  하지만 **파이썬/노드 스크립트가 내부에서 파일을 쓰는 것처럼 간접적인 경로는 막지 못한다.**
  그래서 루트 `CLAUDE.md`의 경계 규칙이 여전히 1차 방어선이다.
- 공용 파일(`pyproject.toml` 등)은 일부러 차단하지 않았다. 양쪽이 수정해야 하는 파일이라,
  차단 대신 "합의 후 수정" 지침으로 다룬다. AI 공용(`ai/src/schemas.py`, `api/`, `core/` 등)도 같은 이유로 차단하지 않는다.

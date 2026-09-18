# app/ — App 영역 (frontend + backend)

담당: 팀원 (App 담당). **AI 담당의 Claude는 이 폴더를 읽기만 한다.**
전체 경계 규칙은 루트 [CLAUDE.md](../CLAUDE.md) 참고.

## 구조

```
app/
  backend/    API 서버
  frontend/   UI
```

## 스택 / 명령어

**TBD** — 아직 미정. App 담당이 정한 뒤 이 절을 채운다. 최소한 아래를 적어둔다.

- backend: 프레임워크, 실행 명령, 테스트 명령
- frontend: 프레임워크, 패키지 매니저, dev / build / test 명령
- 로컬에서 frontend ↔ backend 를 같이 띄우는 방법, 포트

스택이 정해지기 전까지는 Claude가 임의로 프레임워크를 골라 스캐폴딩하지 않는다.
먼저 사용자에게 무엇으로 갈지 묻는다.

## 규칙

- **AI 호출은 `ai/src/api/` 만 통해서 한다.** `ai/src/graphs`, `ai/src/rag`, `ai/src/llms` 등
  내부 모듈을 직접 import 하지 않는다. 필요한 기능이 `api/`에 없으면, 직접 만들지 말고
  "AI 쪽에 어떤 진입점이 필요하다"고 사용자에게 보고한다.
- `ai/` 안의 어떤 파일도 수정하지 않는다. 시그니처가 안 맞아도 고치지 않고 보고한다.
- 시크릿은 `.env`로 주입하고 커밋하지 않는다. 키가 늘면 `.env.example`에 이름만 추가한다.
- frontend가 JS/TS로 가면 `package.json` / lock 파일은 `app/frontend/` 안에 둔다.
  루트를 JS 프로젝트로 만들지 않는다 (루트는 Python/uv 소유).

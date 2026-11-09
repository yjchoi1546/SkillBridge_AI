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

사용자 결정: **React + TypeScript + Vite / Spring Boot + Java 21**, DB 접속 정보는 추후 제공.

- frontend (`frontend/`): `npm ci`, `npm run dev` (5173), `npm run build`, `npm run test:e2e`.
- backend (`backend/`): Maven `mvn spring-boot:run` (8080), `mvn test`.
- 팀원용 Windows x64 실행은 `START.cmd`, 종료는 `STOP.cmd`, 코드 갱신 후에는 `RESTART.cmd`.
  도구 자동 설치·빌드·포트 선택·브라우저 열기를 처리한다. 기본은 로컬 H2 + fake AI.
- 서버 모드가 기본이며 `/api`를 Spring으로 프록시한다. `VITE_API_MODE=browser`는 독립 UI 데모다.
- Windows 실행: 루트에서 `powershell -ExecutionPolicy Bypass -File app/scripts/start-frontend.ps1`.
  별도 터미널에서 `start-backend.ps1`를 시작한다. `-Server`는 호환 옵션, `-Browser`는 브라우저 데모다.
- 서버는 JDBC로 계정·세션·워크스페이스를 저장한다. 기본 H2 파일 DB, PostgreSQL은 접속 정보 수령 후 검증한다.
- `scripts/setup-ai.ps1`은 Python과 의존성을 app 내부에 설치한다. 공유 lockfile은 `--locked`로 유지한다.
- Spring은 `backend/ai_bridge.py`의 고정 JSON 경계로 기존 `ai.src.api` v2만 호출한다.
  기본 공급자는 `fake`다. `SKILLBRIDGE_AI_MODE=demo`는 Python을 호출하지 않는다.
- `SKILLBRIDGE_TEST_PYTHON=true`로 백엔드 테스트를 실행하면 실제 Python 연결 전체 흐름도 검증한다.
- 계획·API·연동 대기 항목은 [docs/architecture.md](docs/architecture.md), 실행 안내는 [README.md](README.md).

## 규칙

- **AI 호출은 `ai/src/api/` 만 통해서 한다.** `ai/src/graphs`, `ai/src/rag`, `ai/src/llms` 등
  내부 모듈을 직접 import 하지 않는다. 필요한 기능이 `api/`에 없으면, 직접 만들지 말고
  "AI 쪽에 어떤 진입점이 필요하다"고 사용자에게 보고한다.
- `ai/` 안의 어떤 파일도 수정하지 않는다. 시그니처가 안 맞아도 고치지 않고 보고한다.
- 시크릿은 `.env`로 주입하고 커밋하지 않는다. 키가 늘면 `.env.example`에 이름만 추가한다.
- frontend가 JS/TS로 가면 `package.json` / lock 파일은 `app/frontend/` 안에 둔다.
  루트를 JS 프로젝트로 만들지 않는다 (루트는 Python/uv 소유).

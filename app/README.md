# SkillBridge AI 웹

React + TypeScript + Vite / Spring Boot + Java 21 기반 실무 과제 플랫폼입니다.
기본 실행은 **서버 계정 + JDBC 영속 저장 + Python AI 공개 API**를 사용합니다.
LLM 공급자는 기본 `fake`이며 API 키나 과금 없이 고정 예시 결과를 돌려줍니다.

## 팀원용: 더블클릭으로 시작 (Windows x64)

웹 개발 도구를 따로 설치하지 않아도 됩니다. 저장소를 받은 뒤 **`app` 폴더의 `START.cmd`를 더블클릭**하세요.

1. 처음 실행하면 필요한 Node.js·JDK 21·Maven·uv·Python과 패키지를 자동으로 준비합니다. 인터넷 연결이 필요하며 몇 분 걸릴 수 있습니다.
2. 서버 준비가 끝나면 브라우저가 자동으로 열립니다. 화면에서 개인 또는 기업 계정을 만들어 사용하세요.
3. 종료할 때는 **`STOP.cmd`**, `git pull`로 코드를 받은 뒤에는 **`RESTART.cmd`**를 더블클릭합니다.

| 파일 | 하는 일 |
| --- | --- |
| [START.cmd](START.cmd) | 자동 준비 → 서버 실행 → 브라우저 열기. 이미 실행 중이면 기존 화면 열기 |
| [STOP.cmd](STOP.cmd) | 실행 파일이 띄운 서버 종료. 계정과 저장된 작업은 보존 |
| [RESTART.cmd](RESTART.cmd) | 서버 종료 → 최신 코드·의존성 반영 → 다시 실행 |

관리자 권한이나 전역 PATH 설정이 필요하지 않습니다. 도구는 `app/.tools`, 캐시와 로그는 `app/.cache`에 보관합니다.
기본 주소는 웹 `http://127.0.0.1:5173`, 백엔드 `http://127.0.0.1:18080`이며 포트가 사용 중이면 빈 포트를 자동으로 찾습니다.
실제로 열린 주소는 실행 창의 `Ready:` 메시지에 표시됩니다. 실행 창을 닫아도 서버는 동작합니다.

**팀원용 실행은 로컬 H2 DB + `fake` AI를 사용하므로 DB 접속 정보나 LLM API 키가 필요 없습니다.**
각자 PC에 계정과 데이터가 따로 저장됩니다. 같은 프로젝트를 공유하는 온라인 서버는 아닙니다.
실제 AI 개발 설정을 사용하려면 아래 수동 실행 방식을 이용하세요.

실패하면 실행 창이 열려 있어 오류를 확인할 수 있습니다. `START.cmd`를 다시 실행해 재시도하세요.
자세한 기록은 `app/.cache/launcher.log`, `backend-server-error.log`, `frontend-server-error.log`에 있습니다.
기존 수동 실행 서버가 같은 DB를 사용 중이라면 해당 서버를 먼저 종료해야 합니다.

다운로드 출처: [Node.js](https://nodejs.org/en/download/archive/v22.23.4),
[Eclipse Temurin JDK API](https://github.com/adoptium/api.adoptium.net/blob/main/docs/cookbook.adoc),
[Apache Maven](https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/),
[uv 공식 릴리스](https://github.com/astral-sh/uv/releases/tag/0.12.15).
새 도구의 ZIP은 공식 배포 체크섬을 확인한 뒤 압축을 풉니다.

## 개발자용: 수동 실행

프로젝트 루트 `C:\ai_platform_project`에서 AI 실행 환경을 한 번 준비합니다.
`uv`가 필요하며 Python·패키지·캐시는 `app/.tools`, `app/.cache`에 설치합니다.
공용 `pyproject.toml`, `uv.lock`과 시스템 Python 설정은 변경하지 않습니다.

```powershell
powershell -ExecutionPolicy Bypass -File app/scripts/setup-ai.ps1

# 터미널 1: 백엔드
powershell -ExecutionPolicy Bypass -File app/scripts/start-backend.ps1

# 터미널 2: 프론트엔드 (서버 모드가 기본)
powershell -ExecutionPolicy Bypass -File app/scripts/start-frontend.ps1
```

브라우저에서 http://127.0.0.1:5173 에 접속한 뒤 개인 또는 기업으로 가입합니다.
서로 다른 계정으로 로그인해 생성·공개·제출·기업 검토를 체험합니다.
비밀번호는 10자 이상, UTF-8 기준 72바이트 이하입니다.
Node.js 22.12 이상, JDK 21, Maven 3.9 이상이 필요합니다.
스크립트는 `app/.tools`의 기존 도구를 우선 사용합니다.

8080 포트를 다른 프로그램이 사용한다면 백엔드에 `-Port 18080`, 프론트엔드에 `-ApiPort 18080`을 붙입니다.
기존 `-Server` 옵션도 지원합니다. 종료는 각 터미널의 `Ctrl+C`입니다.

서버 없이 UI만 체험하려면 다음을 실행합니다. 브라우저 데모 데이터는 localStorage에 저장되며 실제 계정과 별개입니다.

```powershell
powershell -ExecutionPolicy Bypass -File app/scripts/start-frontend.ps1 -Browser
```

## 현재 구현

| 영역 | 동작 |
| --- | --- |
| 계정 | 개인·기업 회원가입/로그인, BCrypt 비밀번호, DB에 해시로 저장하는 8시간 세션, 로그아웃 |
| 저장 | 기본 H2 파일 DB `app/backend/.data/skillbridge`, 계정·세션·프로젝트·제출·작업 보존 |
| AI | Spring → 고정 Python 브리지 → `ai.src.api` v2. 기본 `fake`, 실제 LLM 호출 없음 |
| 기업 | 요청·첨부·민감 단어·일반화 설정, 추가 질문 응답, 초안 생성/수정/재시도/공개/모집 마감 |
| 개인 | 검색·필터·신청, 과정·참고자료·AI 사용 기록, 파일 제출, 후속 답변, 리포트·포트폴리오 |
| 검토 | AI 평가 초안 확인, 기업 피드백, 최종 리포트 확정 |
| 공개 검사 | 지정 민감 단어·연락처·키 형태의 규칙 검사와 AI 유출 검사 결과 반영, 실패 시 공개 차단 |

원문·첨부·민감 단어·유출 검사 상세는 작성 기업만 조회합니다.
실행하지 않은 테스트와 가짜 평가 결과는 미검증으로 표시합니다. 제출 코드는 App에서 실행하지 않습니다.
AI의 추가 질문·후속 질문 API는 현재 빈 목록을 반환할 수 있습니다. 후속 질문이 없으면 App 기본 질문을 제공합니다.

## 설정

Spring 설정은 셸 환경변수로 전달합니다. 저장소 루트 `.env`를 Spring이 자동으로 읽지는 않습니다.

| 변수 | 기본값 / 용도 |
| --- | --- |
| `SKILLBRIDGE_AI_MODE` | `python`; `demo`는 Python 없이 데모 워커 사용 |
| `LLM_PROVIDER` | `fake`; 실제 공급자 사용 시 AI 담당의 모델·키 설정 필요 |
| `SKILLBRIDGE_PYTHON` | `uv`; 직접 Python 실행 파일 경로도 가능 |
| `SKILLBRIDGE_AI_TIMEOUT` | 호출당 240초 |
| `SKILLBRIDGE_DATABASE_URL` | H2 파일 DB JDBC URL |
| `SKILLBRIDGE_DATABASE_USER`, `SKILLBRIDGE_DATABASE_PASSWORD` | 기본 `sa` / 빈 비밀번호 |
| `SKILLBRIDGE_SEED_DEMO_DATA` | `true`; 새 저장소 초기화 시 샘플 프로젝트 추가 |
| `SKILLBRIDGE_DEMO_ENABLED` | `false`; 별도 개발용 데모 로그인 API 허용 여부 |

PostgreSQL은 `SPRING_PROFILES_ACTIVE=postgres`와 `SKILLBRIDGE_DB_HOST`, `SKILLBRIDGE_DB_PORT`,
`SKILLBRIDGE_DB_NAME`, `SKILLBRIDGE_DB_USER`, `SKILLBRIDGE_DB_PASSWORD`, `SKILLBRIDGE_DB_SSLMODE`로 연결합니다.
프로필의 기본 SSL 방식은 `require`이며 샘플 데이터와 데모 로그인은 꺼집니다. 실제 DB 접속 검증은 아직 하지 않았습니다.

## 검증

```powershell
# 독립된 메모리 DB: 계정·권한·저장 복구·API·공개 검사
powershell -ExecutionPolicy Bypass -File app/scripts/start-backend.ps1 -Test

# setup-ai.ps1 실행 후: 실제 Java/Python 경계 전체 흐름 (LLM은 fake)
$env:SKILLBRIDGE_TEST_PYTHON='true'
powershell -ExecutionPolicy Bypass -File app/scripts/start-backend.ps1 -Test
Remove-Item Env:SKILLBRIDGE_TEST_PYTHON

cd app/frontend
npm run build
# 인증 UI: 모의 API 사용
$env:VITE_API_MODE='server'
npm run test:e2e -- tests/auth.spec.ts
# 브라우저 데모 흐름
$env:VITE_API_MODE='browser'
npm run test:e2e -- tests/workspace.spec.ts
```

브라우저 테스트는 설치된 Google Chrome을 사용합니다. 테스트용 Vite 포트는 `SB_TEST_URL`로 바꿀 수 있습니다.
운영 DB는 테스트에 사용하지 않습니다. 상세 구조와 제한은 [architecture.md](docs/architecture.md)에 있습니다.

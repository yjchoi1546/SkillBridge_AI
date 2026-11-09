# 웹 구현 구조와 남은 작업

2026-11-09 기준. React + TypeScript + Vite / Spring Boot + Java 21.
실행과 설정은 [README](../README.md)를 참고합니다. AI 공개 계약과 공용 파일은 변경하지 않았습니다.

## 실행 구조

```text
React / TypeScript / Vite :5173
  ├ server (기본) → /api 프록시 → Spring Boot :8080
  │                              ├ DemoAuth: 실제 계정·해시 세션, 선택적 개발용 데모 로그인
  │                              ├ WorkspaceService: 소유권·상태 전환·작업 큐
  │                              ├ DemoRepository: JDBC 스냅샷 저장
  │                              ├ DisclosureScanner: 공개본 규칙 검사
  │                              └ PythonAiGateway → 고정 JSON 브리지 → ai.src.api v2
  └ browser → localStorage 독립 UI 데모
```

기본 DB는 `backend/.data/skillbridge`의 H2 파일입니다. 계정·세션은 개별 테이블,
프로젝트·신청·제출·초안 버전·작업은 `workspace_state`의 버전 1 JSON 스냅샷으로 저장합니다.
PostgreSQL JDBC 드라이버와 프로필도 준비되어 있지만 실제 DB 접속 검증은 남아 있습니다.
이 저장 방식은 단일 Spring 인스턴스의 제한된 개발 환경을 전제로 합니다.

워크스페이스 변경은 서비스 잠금 안에서 전체 스냅샷을 한 트랜잭션으로 저장합니다.
저장 실패 시 DB는 롤백하고 워크스페이스 요청과 진행 중 응답을 503으로 차단해 미커밋 상태가 노출되지 않게 합니다.
연결·저장 공간을 복구한 뒤 서버를 재시작해야 합니다. 계정 API는 별도로 동작합니다.
`DemoRepository`는 JDBC 예외 변환을 직접 사용하므로 필드 접근을 가로막는 Spring Repository 프록시를 만들지 않습니다.

## 팀원용 Windows 실행기

`app/START.cmd`가 `scripts/start-app.ps1`을 실행합니다. 필요한 도구를 공식 ZIP·체크섬으로
`app/.tools`에 준비하고 Python 환경과 웹 의존성을 맞춘 뒤 Maven으로 실행 JAR를 만듭니다.
Java와 Vite를 숨김 프로세스로 실행하고 프록시 상태를 확인한 후 브라우저를 엽니다.
기본 포트는 18080/5173이며 사용 중이면 다음 빈 포트를 선택합니다.
팀원용 실행은 로컬 H2와 fake 공급자를 명시적으로 사용합니다.

`app/.cache/app-runtime.json`에는 서버 PID·시작 시각·주소만 보관합니다.
실행 잠금으로 동시 시작/종료를 막고, 이미 정상 실행 중이면 해당 주소를 다시 엽니다.
`STOP.cmd`는 PID와 시작 시각이 일치하는 서버 및 자식 프로세스만 종료합니다.
`RESTART.cmd`는 종료 후 최신 코드로 다시 빌드합니다. 진행 중 작업은 재시작 복구 규칙을 따릅니다.
도구·로그·실행 상태·DB는 Git에서 제외하며, 사용 방법은 README 첫 부분에 있습니다.

실행기 검증: 실제 CMD 실행, 중복 시작/종료, 프로세스 시작 시각 검사, 동시 실행 잠금,
포트 충돌 상황에서의 재시작과 프록시 연결, 저장 프로젝트 유지 확인.
새 uv ZIP 다운로드·체크섬·압축 해제와 Node/JDK/Maven 공식 배포 정보 조회도 확인했습니다.
모든 도구가 없는 별도 Windows PC에서의 전체 설치 검증은 남아 있습니다.

## 계정과 공개 경계

개인/기업 유형은 가입한 계정에 고정합니다. 비밀번호는 BCrypt로 저장하고, 난수 세션 토큰은
DB에 SHA-256 해시로만 보관합니다. 8시간 뒤 만료되며 로그아웃하면 해당 세션을 삭제합니다.
실패한 로그인은 이메일별로 제한합니다. 프론트는 탭의 sessionStorage에 토큰을 보관합니다.
데모 로그인 API는 기본 비활성화이며 실제 계정과 별도 개발용 신원을 사용합니다.

원문·첨부·민감 단어·질문 답변·유출 검사 상세는 작성 기업만 조회합니다.
공개 프로젝트와 중첩 과제·평가 기준·테스트 DTO는 허용 필드만 깊은 복사로 구성합니다.
개인 제출물은 본인과 해당 프로젝트 기업만 조회할 수 있고 기업은 평가 완료 후 검토합니다.
역할 전환이나 세션 변경 뒤 도착한 이전 응답은 프론트 상태에 반영하지 않습니다.
서버 오류 시 브라우저 데모 데이터로 전환하지 않습니다.

## 화면

| 경로 | 동작 |
| --- | --- |
| `/login`, `/register` | 로그인·개인/기업 가입, 안전한 내부 경로 복귀 |
| `/` | 계정별 대시보드 |
| `/projects`, `/projects/:id` | 공개 탐색·필터·명세·신청 |
| `/my/projects`, `/work/:id` | 수행 현황·과정·파일 제출·후속 답변 |
| `/my/reports`, `/reports/:id` | 기업 확정 리포트·다운로드·포트폴리오 |
| `/company/requests/new` | 비공개 원문·첨부·민감 단어·일반화 설정 |
| `/company/projects`, `/company/projects/:id` | 추가 질문·생성·수정·버전·공개·마감 |
| `/company/reviews` | 평가 완료 제출물·기업 피드백·리포트 확정 |

모바일 메뉴·계정·안내·알림은 접근 가능한 대화상자로 제공합니다.

## 주요 HTTP API

| Method | 경로 | 동작 |
| --- | --- | --- |
| GET | `/api/health` | JDBC·AI 모드·공급자 정보 |
| POST | `/api/auth/register`, `/api/auth/login` | 가입 또는 로그인 → 세션 |
| GET/POST | `/api/auth/me`, `/api/auth/logout` | 세션 확인 / 종료 |
| POST | `/api/auth/demo` | 명시적으로 활성화한 개발 환경에서만 |
| GET | `/api/projects`, `/api/projects/:id` | 공개 DTO |
| GET | `/api/projects/participating` | 본인의 참여 프로젝트 (마감 후에도 조회) |
| GET | `/api/company/projects`, `/api/company/projects/:id` | 작성 기업 전용 |
| POST | `/api/company/requests` | 생성 작업 등록, 202 |
| POST | `/api/company/projects/:id/clarifications` | 추가 질문 답변, 202 |
| POST | `/api/company/projects/:id/revise`, `retry` | 수정 / 실패 재시도, 202 |
| POST | `/api/company/projects/:id/publish`, `close` | 공개 / 모집 마감 |
| GET | `/api/company/projects/:id/versions` | 작성 기업의 초안 버전 |
| GET/POST | `/api/applications` | 신청 목록 / 신청 |
| GET | `/api/applications/:id` | 본인의 기록 |
| POST | `/api/applications/:id/work`, `submit` | 저장 / 제출·후속 질문 작업 |
| POST | `/api/applications/:id/answers` | 답변과 평가 작업, 202 |
| GET | `/api/company/submissions`, `/api/company/submissions/:id` | 해당 기업의 평가 완료 제출 |
| POST | `/api/company/submissions/:id/finalize` | 기업 피드백·리포트 확정 |
| POST | `/api/applications/:id/portfolio` | 본인의 확정 리포트 추가 |
| GET | `/api/jobs/:id` | 작업 등록자 전용, 원문 제외 |

인증은 `Authorization: Bearer <서버 발급 토큰>`을 사용합니다.
요청 본문은 2,100,000바이트까지, 기업 첨부는 최대 3개·총 1,050,000바이트,
제출 파일은 최대 12개·총 200,000자까지 허용합니다.

## AI v2 연결

`setup-ai.ps1`은 `app/.tools/python`, `app/.tools/ai-venv`와 `app/.cache/uv`를 사용합니다.
`uv sync --locked`로 공유 lockfile을 유지하고 공개 API import를 검사합니다.
Java는 저장소 루트를 cwd로 고정하여 `uv run --frozen --no-sync python -m app.backend.ai_bridge`를 실행합니다.
`SKILLBRIDGE_PYTHON`으로 직접 Python 실행 파일을 지정할 수도 있습니다.
실행 파일·연산 이름은 HTTP 입력에서 받지 않습니다.

브리지는 `clarify`, `generate`, `revise`, `followup`, `evaluate` 연산을 지원합니다.
첨부 Base64는 원본 바이트로 복원하고, 과정·참고자료·AI 사용·후속 답변을 v2 스키마에 전달합니다.
호출별 기본 제한 시간은 240초, 입력 2.1MB, 출력 3MB입니다. 오류·초과 시 프로세스 트리를 종료합니다.
기본 `LLM_PROVIDER=fake`는 실제 Python 파이프라인을 고정 응답으로 검증하며 외부 LLM이나 추적을 호출하지 않습니다.
추가 질문 API는 현재 빈 리스트를 반환할 수 있으며, 후속 질문이 비어 있으면 App 기본 질문을 사용합니다.
App은 제출 코드를 실행하지 않습니다. 샌드박스 실행은 AI-B 담당의 구현과 결과를 따릅니다.

고정 2개 워커·최대 20개 대기열을 사용하며 프론트는 2.5초 간격으로 상태를 확인합니다.
작업과 중간 상태는 DB에 저장합니다. 재시작하면 진행 중 생성은 실패·재시도 가능 상태,
후속 질문은 재제출 가능 상태, 평가는 답변 재전송 가능 상태로 복구합니다. 자동 재실행은 하지 않습니다.

공개 전에 민감 단어·연락처·식별자·키 형태를 검사하고 AI `LeakReport`와 결합합니다.
AI 검사가 `not_checked`면 규칙 검사가 통과해도 전체 결과는 `unchecked`입니다.
실패나 발견 항목이 있으면 공개를 차단합니다. 규칙 검사는 완전한 비식별 보장이 아닙니다.
`fake`의 평가 기준은 모두 `unverified`로 표시합니다.

## 검증 범위와 남은 작업

- 일반 백엔드 테스트: 인증·소유권·상태 전환·공개 DTO·파일 DB 복원·저장 실패 시 롤백과 응답 차단.
- `SKILLBRIDGE_TEST_PYTHON=true`: 실제 Java/Python 프로세스로 생성·수정·공개·제출·평가·리포트 확정 전체 흐름. LLM은 fake.
- Playwright: 모의 API 기반 인증 UI 3개, 브라우저 데모 흐름 4개. 이들은 실제 서버 연동 브라우저 테스트가 아닙니다.
- 다음 단계: PostgreSQL 실제 접속, 정규화 테이블·마이그레이션, 첨부 전용 파일 저장소, 다중 서버 작업 선점·멱등 처리.
- 실제 LLM·문서 분석·추가 질문·샌드박스·유출 검사 품질은 AI 담당과 별도 검증해야 합니다.
- 이메일 검증·비밀번호 재설정·분산 로그인 제한 등 운영 계정 기능은 남아 있습니다.
## 최근 검증 결과 (2026-11-09)

- TypeScript·Vite 프로덕션 빌드 성공.
- 백엔드 21개 테스트 통과. 실제 Java/Python 프로세스를 사용하는 fake 공급자 전체 흐름 1개 포함.
- 인증 UI 3개 통과 (모의 API), 브라우저 데모 4개 통과. 데모의 중복 링크 선택자는 탐색 메뉴로 범위를 고정해 재검증.
- 모바일 가입 화면 캡처 확인, 가로 넘침 검사 통과. 테스트용 서버 종료 완료.
- PostgreSQL 실제 연결과 실제 LLM 공급자는 이번 검증 범위에 포함하지 않음.

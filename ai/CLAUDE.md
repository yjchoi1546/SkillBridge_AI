# ai/ — AI 영역

담당: yjchoi (AI 담당). **App 담당의 Claude는 이 폴더를 읽기만 한다.**
전체 경계 규칙은 루트 [CLAUDE.md](../CLAUDE.md) 참고.

## 구조

제안서의 4단계 워크플로는 사람 단계(기업 검토 → 청년 수행)를 사이에 두고 두 번 돈다.
그래서 그래프를 둘로 나눈다.

```text
ai/src/
  api/          app/backend 가 호출하는 유일한 공개 진입점
                generate_project / revise_project / evaluate_submission (+ 에러 타입)
  schemas.py    ai↔app 계약 타입 정의 (api/schemas.py 로 공개). 바꾸면 app 과 합의
  graphs/
    generation/ 그래프 ① 기업 요청 → 과제 초안 (STEP 1~3)
                analyze_request → design_project → design_dataset → design_evaluation
                → validate_draft ─(오류)→ design_project 재시도
    evaluation/ 그래프 ② 제출물 → 테스트 + AI 평가 초안 (STEP 4)
                check_submission ─(형식 미충족)→ build_report
                                 └→ run_tests → draft_review → build_report
  llms/         LLM 래퍼. 공급자는 .env 의 LLM_PROVIDER 로 교체 (openai/anthropic/google_genai)
  prompts/      프롬프트 .md 파일 + load_prompt()
  validation/   LLM 없는 규칙 검증 (과제 초안 필수 항목, 제출물 형식)
  datagen/      LLM 이 설계한 DatasetSpec 으로 CSV 를 seed 고정 생성
  sandbox/      참여자 코드 격리 실행 (현재 미구현 — NotConfiguredRunner)
  core/         config.py(환경변수는 여기서만) / errors.py / tracing.py(Langfuse)
  benchmarks/   우리 AI 품질 측정 (KPI). 청년 제출물 평가와 혼동 금지
ai/tests/       테스트, fixtures/requests.jsonl (샘플 기업 요청)
ai/Dockerfile, ai/requirements.txt   배포 이미지용
```

### 스택이 바뀌어도 수정 범위가 한 곳에 머물게

- LLM 공급자·모델 → `.env` + `llms/`. 노드는 `generate_structured(task, Schema, system, user)` 만 쓴다.
- LangGraph → `graphs/*/graph.py` 만 import 한다. 노드는 `async (state) -> dict` 순수 함수.
- 백엔드 프레임워크 / DB → AI 는 모른다. `api/` 는 Pydantic 입출력의 async 함수일 뿐이고 저장은 app 이 한다.
- 내부 모듈은 `ai/src/schemas.py` 를 import 한다. `api` 를 import 하면 순환 import 가 생긴다.
- 트레이싱(Langfuse) → `core/tracing.py` 만 langfuse 를 import 한다. 자체 모니터링으로 바꿀 때 이 파일만 교체.

### 트레이싱 (Langfuse)

- 공개 API 1회 = 트레이스 1개 (`generate-project` / `revise-project` / `evaluate-submission`).
  그 아래 LangGraph 노드 span, 그 아래 LLM generation(모델·토큰·비용)이 자동으로 붙는다.
- 새 그래프를 만들면 `ainvoke(config={"callbacks": langchain_callbacks(), "run_name": ...})` 를 넘긴다.
- 새 공개 API 는 `trace_run(...)` 으로 감싸고, root input 에는 리뷰어가 볼 핵심만 넣는다 (큰 본문 X).
- LANGFUSE 키가 없으면 트레이싱만 꺼지고 앱은 정상 동작한다. 스크립트·노트북은 끝에 `flush_tracing()`.
- 이메일·전화번호·주민번호·API 키 형태는 전송 전에 마스킹된다. `user_id`/`session_id` 는 마스킹 대상이 아니므로
  실명·연락처가 아닌 내부 ID 만 넘긴다.

`labs/`는 실험용 노트북 자리다. 실험이 검증되면 `ai/src/`로 옮기고, 노트북은 남기지 않는다.

## 규칙

- **설정·시크릿은 `core/config.py` 경유.** 모듈 안에서 `os.environ`을 직접 읽지 않는다.
- **프롬프트는 `prompts/`에.** 노드·에이전트 코드에 프롬프트 문자열을 박지 않는다.
- LangGraph 상태는 `graphs/state.py`의 State 타입에만 추가한다. 노드가 State 스키마를
  암묵적으로 확장하지 않는다.
- 노드 하나당 책임 하나. 분기 로직은 `routers.py`로 뺀다.
- 외부에 노출할 함수가 생기면 `api/`에 얇은 래퍼를 두고, 내부 모듈 경로를 노출하지 않는다.
- 의존성 추가는 루트 `pyproject.toml`(uv)에 한다. 추가 전 사용자에게 확인한다 —
  공용 파일이라 팀원 환경에도 영향이 간다.
- `ai/requirements.txt`는 Docker 전용이다. 로컬 개발 의존성과 혼동하지 않는다.

## 프롬프트 엔지니어링 / LLM 작업

LLM 모델 선택·가격·API 파라미터·캐싱을 다룰 때는 추측하지 말고 `claude-api` 스킬을 먼저 읽는다.

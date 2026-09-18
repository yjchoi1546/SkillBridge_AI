# ai/ — AI 영역

담당: yjchoi (AI 담당). **App 담당의 Claude는 이 폴더를 읽기만 한다.**
전체 경계 규칙은 루트 [CLAUDE.md](../CLAUDE.md) 참고.

## 구조

```
ai/src/
  api/        app/backend 가 호출하는 유일한 공개 진입점
  graphs/     LangGraph — main_graph.py(조립), state.py(State), routers.py(분기), nodes/
  agents/     에이전트 정의
  rag/        ingestion(loader→chunker→indexer) / embedding / retrieval(retriever→reranker)
  llms/       모델 클라이언트 래퍼
  prompts/    프롬프트 (코드에 문자열로 하드코딩하지 않는다)
  tools/      툴 정의
  memory/     checkpointer(대화 상태) / store(장기 메모리)
  core/       config.py — 설정·환경변수는 전부 여기로 모은다
  eval/       평가
ai/tests/     테스트
ai/Dockerfile, ai/requirements.txt   배포 이미지용
```

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

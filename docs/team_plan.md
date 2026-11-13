# 역할 분담과 다음 작업 (2026-11-12)

세 명이 같이 보는 문서다. AI-A / AI-B 담당을 정하고, 아래 순서대로 진행한다.
과제 품질 목표는 [example_project.md](example_project.md), 폴더 소유권은 루트 [CLAUDE.md](../CLAUDE.md) 를 따른다.

## 0. 지금 결정할 것

| 항목 | 결정할 내용 | 누가 |
| --- | --- | --- |
| A / B 담당자 | 아래 표를 보고 AI 두 명이 나눈다. 정해지면 `CLAUDE.md` 소유권 표의 "(미정)" 을 이름으로 바꾼다 | AI 두 명 |
| 샌드박스 방식 | Rockchip 보드는 쓰지 않는 방향 (대회 조건에 없으면). Pyodide 와 Docker 중 실험 후 결정 | B |
| ~~스키마 v3~~ | **확정** — [ai/CONTRACT.md](../ai/CONTRACT.md) "v2 → v3 변경점" | 세 명 |
| **계약 v4 (제안)** | 난이도 제거, 요청 1건 = 고품질 과제 1개 (자료실형), 설계 설명 문항 3~5개(500자) — [contract_v4_proposal.md](contract_v4_proposal.md) 8절 | **세 명** |
| 남은 계약 미결 항목 | 첨부 문서 바이트/텍스트, 도메인 태그 자유 입력/고정 목록 ([ai/CONTRACT.md](../ai/CONTRACT.md)) | 세 명 |

## 1. A 와 B 비교

| | **AI-A (과제 생성)** | **AI-B (평가)** |
| --- | --- | --- |
| 한 줄 요약 | 기업 요청 → 실무 수준 과제 + 데이터 + 정답 | 청년 제출물 → 테스트 실행 + AI 평가 초안 |
| 사용자 | 기업 회원 (요청 → 검토 → 승인) | 개인 회원 (제출 → 후속 질문 → 결과) |
| 맡는 그래프 | ① 생성: 요청 분석 → 과제 설계 → 데이터 설계 → 평가 설계 → 검증 | ② 평가: 형식 확인 → 테스트 실행 → AI 평가 초안 → 리포트 |
| 주요 폴더 | `graphs/generation/`, `prompts/generation/`, `datagen/`, `validation/spec_rules.py` | `graphs/evaluation/`, `prompts/evaluation/`, `sandbox/`, `validation/submission_rules.py` |
| 일의 성격 | 프롬프트 설계, 데이터 생성 로직, 유출 검사 | 코드 격리 실행, 채점 로직, 평가 프롬프트 |
| 맞는 사람 | 기획·도메인 감각, 프롬프트 다루기를 좋아하는 사람 | 백엔드·인프라 경험, 보안 감각이 있는 사람 |
| 시연에서 보이는 것 | 한 줄 요청이 실무 과제로 바뀌는 장면 | 제출하면 테스트가 돌고 평가가 나오는 장면 |
| 가장 큰 위험 | LLM 결과 품질이 들쭉날쭉함 | 샌드박스 구현 난이도, 시연 환경 문제 |

## 2. AI-A 작업

| # | 작업 | 내용 | 관련 파일 | 난이도 |
| --- | --- | --- | --- | --- |
| A1 | 되묻는 질문 | 입력 질문 5개 중 빈 칸을 찾아 되묻기 (`ask_clarifying_questions`) | `graphs/generation/`, 프롬프트 | 중 |
| A2 | 요청 분석 강화 | 결정권자·규칙·데이터 문제 추출, 입력에 없는 규칙은 `(가정)` 표시 | `analyze_request` | 중 |
| A3 | 세계관·시나리오 설계 | 가상 회사, 기준일, 부서 / 난이도별 시나리오 3종, 완성·미완성 예시 | `design_project` | 상 |
| A4 | 데이터 생성 확장 | CSV 여러 개, 숨은 함정(중복·표기 변형·누락)을 seed 고정으로 심기 | `datagen/`, `design_dataset` | 상 |
| A5 | **정답 계산** | 생성 데이터로 auto 테스트 정답을 미리 계산. **B 가 받아서 씀** | `datagen/`, `design_evaluation` | 중 |
| A6 | 유출 검사 | 공개본에 민감 단어·원문 고유명사·원문 수치가 남았는지 → `LeakReport` | 새 노드 | 중 |
| A7 | 자동 검증 규칙 | 시나리오 3종·가정 표시·기준일이 없으면 다시 만들게 함 | `spec_rules.py` | 하 |
| A8 | 모범 예시 프롬프트 | 예시 과제를 생성 프롬프트에 few-shot 으로 넣기 | `prompts/generation/` | 하 |

## 3. AI-B 작업

| # | 작업 | 내용 | 관련 파일 | 난이도 |
| --- | --- | --- | --- | --- |
| B1 | 격리 방식 결정 | Pyodide / Docker 작은 실험 후 결정 | `labs/b_*.ipynb` | 중 |
| B2 | 실행 하네스 | 제출 코드 실행 → 결과 파일 수집 → A 의 정답과 비교 → `TestResult` | `sandbox/` | 상 |
| B3 | 샌드박스 구현 | 네트워크 차단, 실행 시간·메모리 제한 실행기로 `get_runner()` 교체 | `sandbox/` | 상 |
| B4 | 제출물 형식 검사 | 필수 제출물·파일 형식 확인 | `submission_rules.py` | 하 |
| B5 | 후속 질문 | 제출 코드·과정 기록을 보고 본인이 풀었는지 확인하는 질문 (`generate_followup_questions`) | `graphs/evaluation/`, 프롬프트 | 중 |
| B6 | AI 평가 초안 강화 | 평가 기준별 충족, 시나리오 대응, 가정 구분 여부 판정 | `draft_review` | 중 |
| B7 | 숨은 함정 채점 | 함정을 잡았는지 테스트·평가에 반영 | `run_tests`, `draft_review` | 중 |

## 4. 같이 할 것

| 작업 | 내용 | 합의 |
| --- | --- | --- |
| 스키마 v3 | **확정.** 시나리오, 규칙, 데이터 여러 개, 숨은 함정·정답(`evaluation_key`) | 세 명 (App 화면·DB 영향) |
| 정답 형식 약속 | A 가 만드는 정답을 B 가 읽는 형태 (A5 ↔ B2 접점) | A·B |
| 가짜 응답 갱신 | 스키마가 바뀌면 `ai/src/llms/fake.py` 도 같이 갱신 | A·B |
| 품질 측정 | 필수 항목 충족률, AI·기업 평가 일치도 등 (`ai/src/benchmarks/`) | A·B |

## 5. 진행 순서

1. A / B 담당 정하기 → `CLAUDE.md` 갱신, 각자 권한 템플릿 복사 후 Claude Code 재시작
2. **스키마 v3 와 정답 형식 먼저 합의** — B 는 A 의 정답(A5)이 있어야 채점을 완성할 수 있다
3. 그동안 B 는 격리 방식 실험(B1)·형식 검사(B4), A 는 요청 분석(A2)·검증 규칙(A7) 부터
4. 스키마 v3 반영 후 A3~A5 / B2~B3 본 작업

## 6. App 담당에게 전달

- 공용 `.claude/settings.json` 에 있던 `Edit(/ai/**)`, `Edit(/labs/**)`, `Edit(/data/**)` 차단 규칙을 뺐다.
  이 규칙이 공용 파일에 있으면 AI 담당도 `ai/` 를 수정할 수 없다.
  같은 규칙은 `settings.app.json` 템플릿에 있으니 **`.claude/templates/settings.app.json` 을 `.claude/settings.local.json` 으로 복사**하고 Claude Code 를 재시작해 주세요.
- `app/START.cmd`: pwsh 7 터미널에서 실행하면 `Get-FileHash` 를 못 찾아 실패한다.
  `powershell.exe` 줄 위에 `set "PSModulePath="` 추가 필요 (`RESTART.cmd`, `STOP.cmd` 도 같은 방식이면 동일).
- `app/scripts/setup-ai.ps1`: 저장소가 exFAT/FAT32 드라이브에 있으면 uv 의 Python 설치가 정션 생성에서 실패한다.
  `UV_PYTHON_INSTALL_DIR` 을 `$env:LOCALAPPDATA` 아래로 옮기는 것을 제안.
- 스키마 v3 확정 ([ai/CONTRACT.md](../ai/CONTRACT.md)): 과제 상세 화면에 세계관·규칙((가정) 배지)·시나리오·완성/미완성 예시·데이터 한계 표시.
  `evaluation_key` 는 비공개 저장 후 기업 화면에만 숨은 함정 표시, `evaluate_submission` 에 그대로 전달.
  `draft.datasets` 로 옮겨 가면 알려 주세요 (그 뒤 `dataset` 제거).

# AI ↔ App 계약 (v2 — 수정 의견은 언제든 환영, 바꿀 때는 세 명 합의)

App(백엔드)이 AI 를 부르는 방법. 코드 정의는 [src/schemas.py](src/schemas.py), 함수는 [src/api/](src/api/).
App 은 `from ai.src.api import ...` 로만 가져온다. 모든 함수는 `async` 이고 1~3분 걸릴 수 있으니
**백그라운드 작업으로 돌리고 프론트는 상태를 폴링**한다.

## 호출 순서

```text
[과제 생성]
  기업 등록 → ask_clarifying_questions(request)
                ├ 질문 있음 → 기업 답변 → request.clarifications 에 담아 다시 호출하거나 바로 생성
                └ 질문 없음 ↓
              generate_project(request)        → GenerationResult(draft, leak_report)
  기업 검토 → revise_project(request, draft, feedback) → GenerationResult   (반복)
  기업 승인 → app 이 draft 를 공개 (leak_report 는 계속 기업 전용)

[제출물 평가]
  개인 제출 → generate_followup_questions(task, submission) → list[FollowupQuestion]
  개인 답변 → submission.followup_answers 에 담아
              evaluate_submission(task, dataset, submission) → EvaluationReport
  기업 검토 → app 이 기업 피드백을 붙여 최종 리포트 확정
```

### LLM 키 없이 개발하기 (가짜 모드)

`.env` 에 `LLM_PROVIDER=fake` 를 두면 모든 함수가 LLM 을 부르지 않고 고정된 예시 결과를 바로 돌려준다
(지점별 매출 보고서 과제 3개, 샘플 CSV, 평가 초안). 비용 0, 키 불필요. 결과 형태는 실제와 같으므로
App 화면·DB·작업 큐를 이걸로 먼저 만들고, 결제 후 `openai` 등으로 바꾸면 된다.

`user_id`(회원 ID), `session_id`(프로젝트 ID)를 넘기면 Langfuse 트레이스가 프로젝트 단위로 묶인다.
실명·이메일은 넘기지 않는다.

## v1 → v2 변경점

| 타입 / 함수 | 변경 | 기존 코드 영향 |
| --- | --- | --- |
| `ProjectRequest` | `documents`, `sensitive_terms`, `generalization`, `clarifications` 추가 | 없음 (기본값 있음) |
| `CompanyDocument` | 신규. 첨부 문서 원본 바이트 | — |
| `ProjectDraft` | `domain_tags` 추가 | 없음 |
| `LeakReport`, `LeakFinding` | 신규. 공개본 유출 검사 결과 (기업 전용) | — |
| `generate_project`, `revise_project` | 반환형 `ProjectDraft` → **`GenerationResult`** | **있음** — `.draft` 로 꺼낸다 |
| `ask_clarifying_questions` | 신규 (AI-A). 구현 전엔 항상 빈 리스트 | — |
| `Submission` | `references`, `process_log`, `ai_usage`, `followup_answers` 추가 | 없음 |
| `generate_followup_questions` | 신규 (AI-B). 구현 전엔 항상 빈 리스트 | — |

아직 구현 안 된 기능도 **시그니처는 확정 형태로 열어 두었다.** App 은 지금부터 이 형태로 화면·DB 를 짜면 되고,
AI 쪽 구현이 들어와도 App 코드는 바뀌지 않는다.

## App 이 지켜야 할 것

- **원문은 기업 본인만.** `ProjectRequest` 전체(요청 원문, `documents`, `sensitive_terms`, `clarifications`)와
  `LeakReport` 는 개인 회원 API 응답에 절대 포함하지 않는다. 개인에게는 승인된 `ProjectDraft` 만.
- `CompanyDocument.content` 는 원본 바이트다. DB 컬럼보다는 파일 저장소에 두고, 호출할 때 읽어서 넘긴다.
- `LeakReport.status == "failed"` 인 초안은 승인 버튼을 막거나 경고를 띄운다. `"not_checked"` 는 아직 검사기가
  없다는 뜻이다 (AI-A 구현 전).
- `Submission.process_log` 의 질문은 App 화면이 정한다. 권장 질문:
  1. 처음 문제를 보고 세운 가설이나 접근 방법은?
  2. 시도했다가 버린 방법과 그 이유는?
  3. 가장 막혔던 지점과 어떻게 풀었는지?
  4. 결과를 어떻게 검증했는지?
- 과정 기록 에디터의 붙여넣기 비율·작성 시간 같은 정보는 **기업에게 참고로만** 보여준다. AI 에는 넘기지 않고,
  자동 감점에도 쓰지 않는다 (AI 작성 여부를 정확히 판별할 방법이 없어 공정성 문제가 생긴다).

## 아직 정하지 않은 것

- **자동 테스트 형식** — `TestCase` 에 정답값 필드(`expected` 등)를 추가할지. AI-B 샌드박스 방식이 정해지면 v3 로 추가.
- **`CompanyDocument` 를 바이트로 받을지 텍스트로 받을지** — 지금은 바이트(문서 해석은 AI 가 담당).
- **도메인 태그 목록** — 자유 입력으로 둘지, 고정 목록(제조/금융/커머스/…)으로 둘지. 필터 UI 와 같이 정한다.

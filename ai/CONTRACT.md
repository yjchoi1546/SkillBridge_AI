# AI ↔ App 계약 (v4 — 수정 의견은 언제든 환영, 바꿀 때는 세 명 합의)

App(백엔드)이 AI 를 부르는 방법. 코드 정의는 [src/schemas.py](src/schemas.py), 함수는 [src/api/](src/api/).
App 은 `from ai.src.api import ...` 로만 가져온다. 모든 함수는 `async` 이고 1~3분 걸릴 수 있으니
**백그라운드 작업으로 돌리고 프론트는 상태를 폴링**한다.

## 호출 순서

```text
[과제 생성]
  기업 등록 → ask_clarifying_questions(request)
                ├ 질문 있음 → 기업 답변 → request.clarifications 에 담아 다시 호출하거나 바로 생성
                └ 질문 없음 ↓
              generate_project(request)        → GenerationResult(draft, leak_report, evaluation_key)
  기업 검토 → revise_project(request, draft, feedback) → GenerationResult   (반복)
  기업 승인 → app 이 draft 를 공개 (leak_report·evaluation_key 는 계속 기업 전용)

[제출물 평가]
  개인 제출 → generate_followup_questions(task, submission, project=draft) → list[FollowupQuestion]
  개인 답변 → submission.followup_answers 에 담아
              evaluate_submission(task, dataset, submission, project=draft,
                                  evaluation_key=저장해 둔 것) → EvaluationReport
              (v4 전환 기간: task·dataset 은 draft.tasks[0]·draft.dataset 을 넘기면 된다)
  기업 검토 → app 이 기업 피드백을 붙여 최종 리포트 확정
```

### LLM 키 없이 개발하기 (가짜 모드)

`.env` 에 `LLM_PROVIDER=fake` 를 두면 모든 함수가 LLM 을 부르지 않고 고정된 예시 결과를 바로 돌려준다
(지점별 매출 자료실형 과제 1개 — CSV·문서 여러 개, 평가 초안). 비용 0, 키 불필요. 결과 형태는 실제와 같으므로
App 화면·DB·작업 큐를 이걸로 먼저 만들고, 결제 후 `openai` 등으로 바꾸면 된다.

`user_id`(회원 ID), `session_id`(프로젝트 ID)를 넘기면 Langfuse 트레이스가 프로젝트 단위로 묶인다.
실명·이메일은 넘기지 않는다.

## v3 → v4 변경점 (난이도 없는 자료실형 과제)

설계 배경·화면 영향은 [docs/contract_v4_proposal.md](../docs/contract_v4_proposal.md) (세 명 합의 완료).
요청 1건 = 과제 1개. 회사 자료를 통째로 주고 "이런 문제가 있다, 풀어 보라" 로 제시한다. **추가 필드는 모두 기본값이 있다.**

| 타입 / 함수 | 추가·변경 | App 할 일 |
| --- | --- | --- |
| `ProjectDraft.problem` (`ProblemStatement`) | `situation`, `tensions`, `mission`, `scope_guide` | 과제 상세 맨 위에 표시 |
| `ProjectDraft.documents` (`MaterialDocument`) | `filename`, `title`, `kind`(`policy`/`record`/`opinion`/`external`), `content`(마크다운), `description` | 자료실 파일 목록 + 문서 보기. `kind` 배지 (규정 / 기록 / 부서 의견 / 외부 정보) |
| `ProjectDraft.datasets` | 이제 **여러 개**. `DatasetColumn.references` 로 표 사이 연결 표시 (예: `stores.store_code`) | 파일 목록 + 내려받기 |
| `BusinessRule.category` | `authority`(승인) / `calculation`(계산) / `business`(업무 기준) | 규칙 표를 종류별로 묶기 |
| `ProjectDraft.required_demos` (`Scenario`) | 시연할 상황 `normal` / `changed` / `exception` 하나씩 | 과제 상세에 표시 |
| `ProjectDraft.start_guide` (`StartGuide`) | `open_points`, `questions`, `first_files` | 과제 상세에 표시 |
| `ProjectDraft.design_questions` (`DesignQuestion`) | 설계 설명 문항 3~5개 (`id`, `title`, `prompts`, `required`, `max_chars`=500) | 제출 화면에 문항별 입력칸·글자 수, 필수 문항 비면 제출 막기 |
| `ProjectDraft.skills`, `estimated_effort`, `deliverables`, `review_criteria`, `done_examples`, `not_done_examples`, `tests` | 과제 단위로 올라옴 | 과제 상세에 표시 (난이도 탭 대신) |
| `Submission.design_answers` (`DesignAnswer`) | `question_id`, `answer` | 제출할 때 채워 보냄 |
| `generate_followup_questions`, `evaluate_submission` | `project=` 선택 인자 (과제 전체) | 평가 호출에 draft 를 넘김 |
| `ProjectRequest.company_name`, `generalization` | **기본값이 바뀜: `low` = 실제 회사명 사용.** `medium`/`high` = 가상 기업. 회사명이 없거나 민감 단어에 있으면 자동으로 가상 기업. 실제 회사명일 때는 모든 문서·CSV 에 '합성 자료' 표시, 외부 기사 문서 없음 | 요청 때 **회사 이름을 `company_name` 으로 넘김.** 요청 화면에 "가상 기업으로 만들기" 선택지 (지금 `WorkspaceService` 는 `low` 를 `medium` 으로 바꿔 보냄) |
| `ProjectDraft.tasks`, `dataset`, `Difficulty` | **제거 예정.** 전환 기간에는 v4 과제로 만든 호환용 3개를 계속 채운다 | v4 화면으로 옮긴 뒤 알려 주면 AI 가 지운다 |

## v2 → v3 변경점 (실무 수준 과제)

기준 예시는 [docs/example_project.md](../docs/example_project.md). **모든 필드에 기본값이 있어 v2 코드는 그대로 동작한다.**

| 타입 / 함수 | 추가 | 공개 범위 | App 할 일 |
| --- | --- | --- | --- |
| `ProjectRequest.intake` (`CompanyIntake`) | 질문 5개: `problem`, `decision_maker`, `rules`, `data_sources`, `success_criteria` (모두 문자열, 빈 칸 허용) | 기업 전용 | 요청 화면을 질문별 입력칸으로 (선택) |
| `ClarifyingQuestion.slot` | 어느 빈 칸을 채우는 질문인지 (`InputSlot`) | 기업 전용 | 답변을 해당 칸 옆에 표시 (선택) |
| `ProjectDraft.context` (`ProjectContext`) | 가상 회사 `company`, 기준일 `reference_date`, `background`, `facts`, `departments` | 공개 | 과제 상세에 세계관 표시 |
| `ProjectDraft.rules` (`BusinessRule`) | `id`, `text`, `source`(`company`/`assumed`), `note` | 공개 | `assumed` 에 **(가정)** 배지 |
| `TaskSpec.scenarios` (`Scenario`) | 난이도마다 `kind` = `normal` / `changed` / `exception` 하나씩, `situation`, `expected` | 공개 | 난이도 탭에 시나리오 표 |
| `TaskSpec.done_examples`, `not_done_examples` | 완성 / 미완성 예시 | 공개 | 난이도 탭에 표시 |
| `ProjectDraft.datasets` | 데이터 파일 전체. **`datasets[0]` = `dataset`** | 공개 | 파일 목록 다운로드. 옮겨 간 뒤 알려 주면 `dataset` 제거 (v4) |
| `SampleDataset.description` | 파일 설명 (예: 조건 변경 시나리오용 정정본) | 공개 | 다운로드 목록에 표시 |
| `ProjectDraft.data_notes` | 참여자에게 미리 알리는 데이터 한계 | 공개 | 데이터 명세 아래 표시 |
| `GenerationResult.evaluation_key` (`EvaluationKey`) | `hidden_checks`(숨은 함정), `answers`(auto 테스트 정답 `TestAnswer`) | **기업·평가 전용** | 비공개 저장, 기업 화면에만 함정 표시, 평가 시 그대로 전달 |
| `evaluate_submission(..., evaluation_key=)` | 선택 인자. 없으면 v2 처럼 동작 | — | `ai_bridge` evaluate 에 전달 |

현재 채워지는 정도 (가짜 모드는 전부 예시 값이 있다):
- 실제 LLM: `context`, `rules`, `scenarios`, 완성·미완성 예시, `data_notes` 는 생성 프롬프트로 채운다. `intake`·`slot` 은 AI-A 다음 작업.
- `datasets` 는 아직 1개. 여러 파일과 숨은 함정(중복 행·표기 변형 등)은 AI-A 데이터 생성 확장 후.
- `hidden_checks` 는 지금 결측·이상치만. `answers` 는 빈 목록 (AI-A 정답 계산 후). 정답 비교는 AI-B 샌드박스 구현 후.

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

- **원문은 기업 본인만.** `ProjectRequest` 전체(요청 원문, `intake`, `documents`, `sensitive_terms`, `clarifications`)와
  `LeakReport`, **`EvaluationKey`(숨은 함정·정답)** 는 개인 회원 API 응답에 절대 포함하지 않는다. 개인에게는 승인된 `ProjectDraft` 만.
- 정답·숨은 함정은 `ProjectDraft` / `TaskSpec` 밖(`GenerationResult.evaluation_key`)에만 둔다. App 이 `draft.tasks` 를
  그대로 공개해도 정답이 새지 않게 하려는 것이다. 반대로 `evaluation_key` 를 공개 데이터에 합치지 않는다.
- `CompanyDocument.content` 는 원본 바이트다. DB 컬럼보다는 파일 저장소에 두고, 호출할 때 읽어서 넘긴다.
- `LeakReport.status == "failed"` 인 초안은 승인 버튼을 막거나 경고를 띄운다. 지금은 기업이 지정한 민감 단어(`sensitive_terms`)가
  공개본(문서·CSV 포함)에 남았는지 검사한다. 남아 있어도 생성은 성공하고 `failed` 와 위치(`findings`)를 돌려준다.
  원문 고유명사·수치 비교는 이후 추가 (AI-A). `"not_checked"` 는 더 이상 나오지 않는다.
- `Submission.process_log` 의 질문은 App 화면이 정한다. 권장 질문:
  1. 처음 문제를 보고 세운 가설이나 접근 방법은?
  2. 시도했다가 버린 방법과 그 이유는?
  3. 가장 막혔던 지점과 어떻게 풀었는지?
  4. 결과를 어떻게 검증했는지?
- 과정 기록 에디터의 붙여넣기 비율·작성 시간 같은 정보는 **기업에게 참고로만** 보여준다. AI 에는 넘기지 않고,
  자동 감점에도 쓰지 않는다 (AI 작성 여부를 정확히 판별할 방법이 없어 공정성 문제가 생긴다).

## 아직 정하지 않은 것

- **정답 비교 방식** — 정답은 v3 `EvaluationKey.answers` (`TestAnswer.expected` 는 JSON 값)로 정했다.
  참여자 출력 파일을 어떻게 읽어 비교할지(파일 이름, 표 비교 규칙)는 AI-B 샌드박스와 AI-A 정답 계산이 맞춘다. App 영향 없음.
- **`CompanyDocument` 를 바이트로 받을지 텍스트로 받을지** — 지금은 바이트(문서 해석은 AI 가 담당).
- **도메인 태그 목록** — 자유 입력으로 둘지, 고정 목록(제조/금융/커머스/…)으로 둘지. 필터 UI 와 같이 정한다.

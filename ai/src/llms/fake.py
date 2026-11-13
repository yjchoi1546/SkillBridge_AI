"""가짜 LLM 응답 (`LLM_PROVIDER=fake`).

LLM 키·비용 없이 그래프 전체를 끝까지 돌리기 위한 고정 응답이다. 쓰는 곳:
- App 담당이 결제 없이 화면·흐름을 개발할 때
- pytest (ai/tests/conftest.py 가 자동으로 켠다)

응답은 스키마 **클래스 이름**으로 찾는다. 노드가 새 스키마로 generate_structured 를 부르기 시작하면
여기에 같은 이름의 응답을 추가해야 가짜 모드가 계속 동작한다 (없으면 어떤 이름이 빠졌는지 에러로 알려준다).
내용은 ai/tests/fixtures/requests.jsonl 첫 번째 요청(지점별 매출 보고서)에 맞춘 v4 자료실형 과제 예시다.
"""

from typing import Any, TypeVar

from pydantic import BaseModel

from ..core.errors import ConfigError

T = TypeVar("T", bound=BaseModel)

_RESPONSES: dict[str, dict[str, Any]] = {
    # graphs/generation — analyze_request
    "ProblemAnalysis": {
        "problem": "지점별 매출을 매주 엑셀로 수작업 취합해 보고서 작성에 시간이 많이 든다.",
        "goals": ["주간 보고서 작성 시간을 1시간 이내로 단축", "집계 오류 제거"],
        "constraints": ["참여자는 합성 데이터만 사용한다", "(추정) 결과물은 엑셀 또는 표 형태가 필요하다"],
        "required_skills": ["pandas 데이터 집계", "데이터 정제", "보고서 자동 생성"],
        "decision_maker": "",
        "rules": [
            {"text": "지점별 주간 매출 합계를 보고한다", "source": "company", "evidence": "지점별 매출 보고서"},
            {"text": "전주 대비 20% 이상 하락한 지점을 따로 표시한다", "source": "assumed", "evidence": "보고서의 쓰임새가 입력에 없어 가정"},
        ],
        "data_sources": ["지점별 매출 엑셀 파일 (매주 취합)"],
        "data_issues": ["매출 결측", "입력 실수로 인한 이상치"],
        "success_criteria": [],
        "missing": ["decision_maker", "rules", "success_criteria"],
    },
    # graphs/generation — design_world
    "WorldPlan": {
        "title": "지점 매출 하락 보고와 재고 재배치 결정 흐름 만들기",
        "summary": "13개 지점의 일 판매 기록으로 매주 하락 지점을 가려 본부장 결정과 물류 재배치까지 잇는 과제다. "
        "자료에는 중복·누락·표기 변형이 섞여 있고, 부서마다 원하는 결론이 다르다.",
        "domain_tags": ["유통", "리테일"],
        "skills": ["pandas", "SQL", "업무 규칙 설계", "워크플로 자동화"],
        "estimated_effort": "1~2주, 하루 2~3시간",
        "context": {
            "company": "온새리빙 (가상 기업) — 생활용품 오프라인 매장 13곳을 운영하는 체인",
            "reference_date": "2026-04-06(월) 09:00 — 지난주(3/30~4/5) 실적으로 보고 대상 지점을 정하는 시점",
            "background": "월요일 오전 보고가 늦거나 틀리면 본부장 결정이 하루 밀리고, 수요일 물류 배차를 놓쳐 하락 지점이 한 주 더 방치된다.",
            "facts": [
                "지점 13곳 (수도권 7, 영남 6)",
                "판매 기록 기간 2026-03-09 ~ 2026-04-05",
                "금액은 원 단위, 부가세 제외",
                "물류 배차는 매주 수요일 1회",
            ],
            "departments": [
                {"name": "영업관리팀 (보고서 작성)", "goal": "월요일 10시 전 정확한 보고", "constraint": "담당 2명, 지점 양식이 제각각"},
                {"name": "지역본부장 (결정권자)", "goal": "하락 지점에 빠르게 조치", "constraint": "화요일까지 결정해야 수요일 배차에 반영"},
                {"name": "물류팀", "goal": "배차 비용 절감", "constraint": "트럭 1대당 최대 3개 지점, 주 1회"},
                {"name": "마케팅팀", "goal": "프로모션으로 매출 회복", "constraint": "프로모션 재고는 물류 재배치와 같은 창고 재고를 쓴다"},
            ],
        },
        "problem": {
            "situation": "3월 마지막 주에 영남 일부 지점 매출이 크게 줄었다는 말이 돌지만, 집계가 POS 화면과 맞지 않고 "
            "하루치 자료가 빠진 지점도 있어 어느 지점이 정말 하락했는지 아무도 확신하지 못한다.",
            "tensions": [
                "물류팀은 배차를 줄이고 싶고, 마케팅팀은 같은 창고 재고로 프로모션을 하고 싶다",
                "영업관리팀은 빨리 보고하고 싶지만 자료 확인에 반나절이 걸린다",
            ],
            "mission": "지점별 주간 순매출로 보고 대상 지점을 근거와 함께 가려내고, 본부장 승인·거절에 따라 재배치 작업과 지점 상태가 "
            "실제로 바뀌는 흐름을 만들어 시연한다. 보고서나 차트만으로는 완성이 아니다.",
            "scope_guide": "수도권 2곳과 영남 2곳, 최근 2주로 시작해 보고 → 승인 → 작업 생성까지 먼저 완성한다.",
        },
        "rules": [
            {"id": "R1", "text": "전주 대비 순매출이 20% 이상 줄어든 지점은 본부장 보고 대상", "source": "company", "category": "business"},
            {"id": "R2", "text": "순매출 = 총매출(gross_sales) − 반품(returns), 원 단위, 부가세 제외", "source": "company", "category": "calculation"},
            {"id": "R3", "text": "자료가 빠진 날이 있는 주는 하락 판정에서 빼고 '확인 필요' 로 표시", "source": "assumed",
             "note": "누락 처리 기준이 요청에 없어 가정", "category": "business"},
            {"id": "R4", "text": "재배치 1건당 재고 금액 500만 원 이하는 물류팀장 전결, 초과는 본부장 승인", "source": "assumed",
             "note": "승인 한도가 요청에 없어 가정", "category": "authority"},
            {"id": "R5", "text": "같은 창고 재고로 프로모션이 잡힌 주에는 금액과 관계없이 본부장 승인 (R4 보다 우선)", "source": "assumed",
             "note": "부서 간 재고 충돌을 막기 위한 가정", "category": "authority"},
            {"id": "R6", "text": "주간 = 월요일 시작 ISO 주", "source": "assumed", "category": "calculation"},
        ],
        "story": [
            "3월 31일 POS 재전송으로 같은 판매 행이 두 번 들어감",
            "지난주 강남점 행 일부에 지점명이 '강남 점', '강남' 으로 다르게 적힘",
            "4월 2일 대구동성로점 하루치 판매가 통째로 빠짐",
            "지난주 울산점 판매 행이 크게 줄어 실제 하락",
        ],
    },
    # graphs/generation — design_data
    "DataPlan": {
        "tables": [
            {
                "name": "stores", "description": "지점 목록", "kind": "master", "rows": 13,
                "columns": [
                    {"name": "store_code", "dtype": "string", "description": "지점 코드", "gen": "id", "prefix": "ST-"},
                    {"name": "store_name", "dtype": "string", "description": "지점명", "gen": "list",
                     "choices": ["강남점", "잠실점", "홍대점", "분당점", "일산점", "수원점", "인천점",
                                 "서면점", "해운대점", "대구동성로점", "울산점", "창원점", "김해점"]},
                    {"name": "region", "dtype": "string", "description": "지역본부", "gen": "list",
                     "choices": ["수도권"] * 7 + ["영남"] * 6},
                ],
            },
            {
                "name": "products", "description": "상품 목록", "kind": "master", "rows": 8,
                "columns": [
                    {"name": "product_code", "dtype": "string", "description": "상품 코드", "gen": "id", "prefix": "PD-"},
                    {"name": "product_name", "dtype": "string", "description": "상품명", "gen": "list",
                     "choices": ["주방세제", "섬유유연제", "욕실화", "수납함", "행주 세트", "디퓨저", "물티슈", "밀폐용기"]},
                    {"name": "unit_price", "dtype": "int", "description": "판매가(원)", "gen": "int", "min": 3000, "max": 25000},
                ],
            },
            {
                "name": "sales_daily", "description": "지점별 일 판매 기록", "kind": "transaction", "rows": 1800, "sort_by": "sale_date",
                "columns": [
                    {"name": "sale_date", "dtype": "date", "description": "판매일", "gen": "date", "start": "2026-03-09", "end": "2026-04-05"},
                    {"name": "store_code", "dtype": "string", "description": "지점 코드", "gen": "ref", "ref": "stores.store_code"},
                    {"name": "store_name", "dtype": "string", "description": "지점명 (POS 입력값)", "gen": "lookup",
                     "via": "store_code", "ref": "stores.store_name"},
                    {"name": "product_code", "dtype": "string", "description": "상품 코드", "gen": "ref", "ref": "products.product_code"},
                    {"name": "unit_price", "dtype": "int", "description": "판매가(원)", "gen": "lookup",
                     "via": "product_code", "ref": "products.unit_price"},
                    {"name": "qty", "dtype": "int", "description": "수량", "gen": "int", "min": 1, "max": 30},
                    {"name": "gross_sales", "dtype": "int", "description": "총매출(원)", "gen": "derived", "expr": "qty * unit_price"},
                    {"name": "returns", "dtype": "int", "description": "반품(원)", "gen": "int", "min": 0, "max": 20000},
                ],
            },
            {
                "name": "transfer_requests", "description": "재고 재배치 요청 이력", "kind": "event", "rows": 24, "sort_by": "requested_at",
                "columns": [
                    {"name": "request_id", "dtype": "string", "description": "요청 ID", "gen": "id", "prefix": "TR-"},
                    {"name": "requested_at", "dtype": "date", "description": "요청일", "gen": "date", "start": "2026-01-05", "end": "2026-03-30"},
                    {"name": "store_code", "dtype": "string", "description": "받는 지점", "gen": "ref", "ref": "stores.store_code"},
                    {"name": "amount_krw", "dtype": "int", "description": "재고 금액(원)", "gen": "int", "min": 800000, "max": 9000000},
                    {"name": "status", "dtype": "string", "description": "처리 상태", "gen": "choice",
                     "choices": ["완료", "승인 대기", "반려"], "weights": [0.7, 0.2, 0.1]},
                ],
            },
        ],
        "facts": [
            {"id": "H1", "title": "3월 31일 POS 재전송으로 같은 판매 행이 두 번", "kind": "duplicate_rows", "table": "sales_daily",
             "date_column": "sale_date", "date_from": "2026-03-31", "date_to": "2026-03-31", "count": 15,
             "how_to_check": "중복 제거 후 3월 31일 행 수, 지점별 순매출이 정답과 같은지"},
            {"id": "H2", "title": "강남점 지점명 표기 변형", "kind": "name_variants", "table": "sales_daily",
             "where": [{"column": "store_code", "value": "ST-001"}], "date_column": "sale_date", "date_from": "2026-03-30",
             "column": "store_name", "variants": ["강남 점", "강남"], "rate": 0.4,
             "how_to_check": "지점명이 아닌 store_code 로 묶었는지 (지점 수 13)"},
            {"id": "H3", "title": "4월 2일 대구동성로점 하루치 누락", "kind": "drop_rows", "table": "sales_daily",
             "where": [{"column": "store_code", "value": "ST-010"}], "date_column": "sale_date",
             "date_from": "2026-04-02", "date_to": "2026-04-02",
             "how_to_check": "0 으로 보고 하락 판정하지 않고 '확인 필요' 로 보류했는지 (R3)"},
            {"id": "H4", "title": "지난주 울산점 판매 행이 크게 줄어 실제 하락", "kind": "drop_rows", "table": "sales_daily",
             "where": [{"column": "store_code", "value": "ST-011"}], "date_column": "sale_date",
             "date_from": "2026-03-30", "date_to": "2026-04-05", "count": 15,
             "how_to_check": "울산점이 R1 보고 대상에 들어갔는지"},
        ],
    },
    # graphs/generation — write_documents
    "DocumentSet": {
        "documents": [
            {"filename": "data_dictionary.md", "title": "자료 설명서", "kind": "record", "description": "파일·열·단위와 표 사이 연결",
             "content": "# 자료 설명서\n\n기준일 2026-04-06. 금액은 원 단위, 부가세 제외.\n\n"
             "| 파일 | 내용 | 연결 |\n| --- | --- | --- |\n| stores.csv | 지점 13곳 | store_code |\n"
             "| products.csv | 상품 8종 | product_code |\n"
             "| sales_daily.csv | 일 판매 기록 | store_code → stores, product_code → products |\n"
             "| transfer_requests.csv | 재고 재배치 요청 이력 | store_code → stores |\n\n"
             "- sales_daily 의 store_name 은 POS 에 입력된 값 그대로다. 기준은 store_code.\n- 주간은 월요일 시작 (R6)."},
            {"filename": "approval_policy.md", "title": "재고 재배치 승인 기준", "kind": "policy", "description": "R4·R5 승인 경로",
             "content": "# 재고 재배치 승인 기준 (2026-02 개정)\n\n1. 재배치 1건당 재고 금액 500만 원 이하: 물류팀장 전결 (R4)\n"
             "2. 500만 원 초과: 지역본부장 승인 (R4)\n"
             "3. **같은 창고 재고로 프로모션이 잡힌 주**에는 금액과 관계없이 지역본부장 승인 (R5, 1·2항보다 우선)\n"
             "4. 화요일 18시까지 승인된 건만 수요일 배차에 반영한다."},
            {"filename": "weekly_report_rule.md", "title": "주간 매출 보고 기준", "kind": "policy", "description": "R1~R3 보고·계산 기준",
             "content": "# 주간 매출 보고 기준\n\n- 순매출 = 총매출 − 반품 (R2)\n- 전주 대비 순매출 20% 이상 감소 지점은 본부장 보고 (R1)\n"
             "- 자료가 빠진 날이 있는 주는 판정에서 빼고 '확인 필요' 표시 (R3)\n- 보고 마감: 매주 월요일 10:00"},
            {"filename": "meeting_notes_0403.md", "title": "4/3 영업·물류·마케팅 회의록", "kind": "opinion", "description": "부서별 의견",
             "content": "# 4/3 주간 회의록 (작성: 영업관리팀)\n\n- 영업관리: 지난주 집계가 POS 화면 합계와 몇 군데 안 맞는다. 원인은 아직 모름.\n"
             "- 영남본부: 울산점은 근처 경쟁 매장 개점 영향 같다. 재배치가 급하다.\n"
             "- 물류: 이번 주 트럭이 2대뿐이라 6곳 넘게는 못 간다.\n"
             "- 마케팅: 다음 주 같은 창고 재고로 디퓨저 프로모션 예정. 재고를 빼면 곤란.\n- 결론 없음. 월요일 보고 보고 다시 논의."},
            {"filename": "news_local_competitor.md", "title": "지역 신문 — 울산 신규 생활용품 매장", "kind": "external",
             "description": "확인 안 된 외부 기사",
             "content": "# 울산에 대형 생활용품 매장 문 열어\n\n지난달 말 울산 시내에 대형 생활용품 매장이 문을 연 것으로 알려졌다. "
             "인근 상권 매출에 영향이 있을 것이라는 관측이 나온다. (회사 공식 확인 자료 아님)"},
        ],
    },
    # graphs/generation — finish_project
    "ProjectFinish": {
        "required_demos": [
            {"kind": "normal", "situation": "2026-04-06 월요일, 지난주(3/30~4/5) sales_daily.csv 로 주간 보고",
             "expected": "보고 대상 지점과 근거(증감률, 적용 규칙)가 나오고, 승인 요청이 만들어진다"},
            {"kind": "changed", "situation": "화요일 오전, 3월 31일 자료가 중복 전송이었다는 영업관리팀 정정이 도착",
             "expected": "다시 계산해 판정이 바뀐 지점과 이유를 보여 주고, 이미 만든 승인 요청을 갱신하거나 취소한다"},
            {"kind": "exception", "situation": "대구동성로점 4월 2일 자료가 없고, 본부장이 울산점 재배치를 마케팅 재고 충돌로 거절",
             "expected": "누락 지점은 '확인 필요' 로 보류하고 확인 요청을 남기며, 거절된 건은 대안과 상태 변경으로 이어진다"},
        ],
        "start_guide": {
            "open_points": [
                "집계가 POS 화면과 맞지 않는 이유는 자료에 적혀 있지 않다",
                "울산점 하락 원인이 경쟁 매장인지 확인된 바 없다",
                "물류 트럭이 몇 대인지 주마다 다르다",
            ],
            "questions": [
                "보고 대상을 정하려면 어떤 계산이 먼저 맞아야 하나?",
                "정보가 빠진 지점은 어떻게 표시하고 누구에게 물어야 하나?",
                "R5 가 R4 보다 우선하는 상황은 언제 생기나?",
            ],
            "first_files": ["data_dictionary.md", "weekly_report_rule.md", "sales_daily.csv"],
        },
        "deliverables": ["실행 가능한 코드 또는 화면", "시연 기록 (상황 3개)", "설계 설명"],
        "design_questions": [
            {"id": "q_target", "title": "무엇을 풀었나",
             "prompts": ["본부장의 어떤 결정을 돕기로 했나요?", "보고·재배치 중 어디에 집중했고 왜인가요?"]},
            {"id": "q_flow", "title": "어떻게 동작하나",
             "prompts": ["판매 기록을 받아 어떤 순서로 보고 대상과 작업을 만드나요?", "승인·거절이 들어오면 상태가 어떻게 바뀌나요?"]},
            {"id": "q_basis", "title": "무엇을 근거로 했나",
             "prompts": ["어떤 파일·규칙을 썼나요?", "누락·불일치는 어떻게 처리했나요?", "회의록 의견과 데이터 사실을 어떻게 나눴나요?"]},
            {"id": "q_departments", "title": "다른 부서에 미치는 영향",
             "prompts": ["재배치 결정이 물류·마케팅의 목표나 제약을 어떻게 바꾸나요?"]},
        ],
        "review_criteria": [
            {"criterion": "집계 정확성", "description": "정제 후 지점별 주간 순매출이 정답과 같다", "auto_checkable": True},
            {"criterion": "규칙·승인 반영", "description": "R1~R5 를 판정과 승인 경로에 반영했다", "auto_checkable": False},
            {"criterion": "예외 처리", "description": "누락·정정·거절에서 보류·재계산·대안으로 이어진다", "auto_checkable": False},
            {"criterion": "근거와 가정 구분", "description": "데이터 사실, 부서 의견, 본인 가정을 구분해 표시했다", "auto_checkable": False},
            {"criterion": "실제 동작", "description": "판단 결과에 따라 요청·작업·상태가 실제로 바뀐다", "auto_checkable": False},
        ],
        "done_examples": [
            "승인 거절을 넣으면 재배치 작업 상태가 '보류' 로 바뀌고 다음 주 재검토 작업이 생긴다",
            "같은 입력이면 같은 보고 대상이 나온다",
        ],
        "not_done_examples": ["증감률 차트와 권고문만 있고 상태가 바뀌지 않는다", "누락된 날을 0 으로 계산해 하락으로 보고했다"],
        "tests": [
            {"id": "T1", "description": "중복 제거 후 3월 31일 판매 행 수가 정답과 같다", "kind": "auto"},
            {"id": "T2", "description": "지점별 주간 순매출(3/30~4/5)이 정답과 ±1원 이내", "kind": "auto"},
            {"id": "T3", "description": "누락 지점을 '확인 필요' 로 보류했다", "kind": "manual"},
        ],
        "data_notes": ["store_name 은 POS 입력값이라 표기가 통일되어 있지 않을 수 있다. 기준은 store_code."],
    },
    # graphs/evaluation — draft_review
    "ReviewDraft": {
        "ai_review": [
            {"criterion": "집계 정확성", "status": "unverified", "comment": "[가짜 모드] 자동 테스트 미실행"},
            {"criterion": "문제 접근 과정", "status": "met", "comment": "[가짜 모드] 접근 이유가 서술되어 있음"},
        ],
        "ai_summary": "[가짜 모드] 실제 LLM 평가가 아닌 고정 응답입니다.",
        "improvements": ["[가짜 모드] 이상치 처리 기준을 근거와 함께 적어 보세요."],
    },
}


def fake_response(schema: type[T]) -> T:
    data = _RESPONSES.get(schema.__name__)
    if data is None:
        raise ConfigError(
            f"가짜 모드에 {schema.__name__} 응답이 없습니다. ai/src/llms/fake.py 의 _RESPONSES 에 추가하세요."
        )
    return schema.model_validate(data)

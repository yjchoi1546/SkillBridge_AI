"""가짜 LLM 응답 (`LLM_PROVIDER=fake`).

LLM 키·비용 없이 그래프 전체를 끝까지 돌리기 위한 고정 응답이다. 쓰는 곳:
- App 담당이 결제 없이 화면·흐름을 개발할 때
- pytest (ai/tests/conftest.py 가 자동으로 켠다)

응답은 스키마 **클래스 이름**으로 찾는다. 노드가 새 스키마로 generate_structured 를 부르기 시작하면
여기에 같은 이름의 응답을 추가해야 가짜 모드가 계속 동작한다 (없으면 어떤 이름이 빠졌는지 에러로 알려준다).
내용은 ai/tests/fixtures/requests.jsonl 첫 번째 요청(지점별 매출 보고서)에 맞춘 예시다.
"""

from typing import Any, TypeVar

from pydantic import BaseModel

from ..core.errors import ConfigError

T = TypeVar("T", bound=BaseModel)

_COMMON_TASK = {
    "scope": "제공된 합성 매출 데이터만 사용한다. 외부 데이터 수집은 선택 사항이다.",
    "deliverables": ["실행 가능한 Python 코드", "결과 보고서(마크다운)"],
}

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
    # graphs/generation — design_project
    "ProjectOutline": {
        "title": "지점별 주간 매출 보고서 자동화",
        "summary": "여러 지점의 일별 매출 데이터를 정제·집계해 주간 보고서를 자동으로 만든다.",
        "context": {
            "company": "온새리빙 (가상 기업) — 생활용품 오프라인 매장 체인",
            "reference_date": "2026-04-01(수) 09:00 — 1분기(1~3월) 지점별 주간 매출 보고서를 만드는 시점",
            "background": "영업관리팀이 지점별 엑셀을 손으로 합치느라 보고가 늦고, 숫자가 틀리면 본부장의 지점 점검 결정이 한 주 밀린다.",
            "facts": ["지점 4곳 (강남·홍대·부산·대전)", "데이터 기간 2026-01-01 ~ 2026-03-31", "금액 단위 원"],
            "departments": [
                {"name": "영업관리팀 (보고서 작성)", "goal": "매주 정확한 보고서를 빠르게", "constraint": "담당 2명, 지점 양식이 제각각"},
                {"name": "지역본부장 (결정권자, 가정)", "goal": "하락 지점을 빨리 찾아 점검", "constraint": "보고서를 받은 날 점검 지점을 정한다"},
            ],
        },
        "rules": [
            {"id": "R1", "text": "지점별 주간 매출 합계를 보고한다", "source": "company"},
            {"id": "R2", "text": "전주 대비 20% 이상 하락한 지점은 따로 표시한다", "source": "assumed", "note": "보고서의 쓰임새가 요청에 없어 가정. 기업 확인 필요"},
            {"id": "R3", "text": "매출이 비어 있는 날은 0 으로 채우지 않고 '확인 필요' 로 표시한다", "source": "assumed", "note": "결측 처리 기준이 요청에 없어 가정"},
        ],
        "data_notes": ["매출 금액은 원 단위 정수다.", "같은 날 같은 지점의 행이 여러 개일 수 있다 (판매 건 단위)."],
        "tasks": [
            {
                **_COMMON_TASK,
                "difficulty": "beginner",
                "title": "지점별 주간 매출 합계 구하기",
                "goal": "지점·주차별 매출 합계 표를 만든다.",
                "steps": ["CSV 불러오기", "날짜를 주차로 변환", "지점·주차별 합계 집계"],
                "skills": ["Python", "pandas"],
                "scenarios": [
                    {"kind": "normal", "situation": "3월 마지막 주 집계", "expected": "4개 지점의 주간 매출 표"},
                    {"kind": "changed", "situation": "주 시작 요일을 일요일에서 월요일로 바꿔 달라는 요청", "expected": "주차 기준을 바꿔 다시 집계하고 바뀐 기준을 메모에 기록"},
                    {"kind": "exception", "situation": "매출이 비어 있는 행 발견", "expected": "0 으로 채우지 않고 건수를 세어 메모에 기록 (R3)"},
                ],
                "done_examples": ["코드를 다시 돌리면 같은 표가 나온다", "결측 행 수가 메모에 있다"],
                "not_done_examples": ["엑셀에서 손으로 고친 표만 있다", "지점이 4개가 아니다"],
            },
            {
                **_COMMON_TASK,
                "difficulty": "intermediate",
                "title": "결측·이상치 처리 후 매출 집계",
                "goal": "결측치와 이상치를 처리한 뒤 지점별 주간 매출과 전주 대비 증감률을 구한다.",
                "steps": ["결측치 확인·처리", "이상치 기준 정의·처리", "증감률 계산"],
                "skills": ["Python", "pandas", "데이터 정제"],
                "scenarios": [
                    {"kind": "normal", "situation": "3월 마지막 주 증감률 계산", "expected": "지점별 증감률과 20% 이상 하락 지점 표시 (R2)"},
                    {"kind": "changed", "situation": "본부장이 하락 기준을 20% 에서 15% 로 낮춤", "expected": "다시 판정하고 새로 포함된 지점을 표시"},
                    {"kind": "exception", "situation": "평소의 5배가 넘는 매출 행", "expected": "그대로 합산하지 않고 이상치로 보류, 확인 요청 문구 작성"},
                ],
                "done_examples": ["이상치 판단 기준이 숫자로 적혀 있다", "가정 규칙(R2·R3)을 (가정) 으로 구분해 적었다"],
                "not_done_examples": ["증감률 표만 있고 하락 지점 표시가 없다", "이상치를 지웠는데 이유가 없다"],
            },
            {
                **_COMMON_TASK,
                "difficulty": "advanced",
                "title": "주간 매출 보고서 자동 생성 파이프라인",
                "goal": "CSV 를 넣으면 정제·집계·요약까지 한 번에 보고서를 만드는 스크립트를 작성한다.",
                "steps": ["정제·집계 함수화", "보고서 템플릿 작성", "실행 스크립트로 묶기"],
                "skills": ["Python", "pandas", "자동화"],
                "scenarios": [
                    {"kind": "normal", "situation": "새 주차 CSV 를 넣고 실행", "expected": "정제·집계·하락 표시가 들어간 보고서 파일 생성"},
                    {"kind": "changed", "situation": "지난주 매출 정정본이 뒤늦게 도착", "expected": "다시 실행해 판정이 바뀐 지점과 이유를 보고서에 표시"},
                    {"kind": "exception", "situation": "한 지점의 한 주 데이터가 통째로 없음", "expected": "보고서를 멈추지 않고 그 지점만 '확인 필요' 로 보류, 영업관리팀 확인 요청"},
                ],
                "done_examples": ["명령 한 줄로 보고서가 다시 만들어진다", "정정 전후 차이가 보고서에 보인다"],
                "not_done_examples": ["노트북 셀을 순서대로 눌러야만 동작한다", "데이터가 빠지면 오류로 멈춘다"],
            },
        ],
    },
    # datagen — design_dataset
    "DatasetSpec": {
        "filename": "branch_sales_sample.csv",
        "n_rows": 200,
        "columns": [
            {"name": "date", "dtype": "date", "description": "판매일", "start_date": "2026-01-01", "end_date": "2026-03-31"},
            {"name": "branch", "dtype": "string", "description": "지점명", "choices": ["강남점", "홍대점", "부산점", "대전점"]},
            {"name": "sales", "dtype": "int", "description": "일 매출(원)", "min": 300000, "max": 3000000, "null_rate": 0.03, "anomaly_rate": 0.02},
        ],
    },
    # graphs/generation — design_evaluation (과제마다 한 번씩 호출된다)
    "TaskEvaluation": {
        "rubric": [
            {"criterion": "집계 정확성", "description": "지점·주차별 합계가 정답과 일치한다.", "auto_checkable": True},
            {"criterion": "문제 접근 과정", "description": "처리 방법을 선택한 이유를 설명한다.", "auto_checkable": False},
        ],
        "tests": [
            {"id": "t1", "description": "지점·주차별 합계가 정답값과 일치한다.", "kind": "auto"},
            {"id": "t2", "description": "보고서에 처리 과정이 설명되어 있다.", "kind": "manual"},
        ],
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

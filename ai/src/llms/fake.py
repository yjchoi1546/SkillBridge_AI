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
    },
    # graphs/generation — design_project
    "ProjectOutline": {
        "title": "지점별 주간 매출 보고서 자동화",
        "summary": "여러 지점의 일별 매출 데이터를 정제·집계해 주간 보고서를 자동으로 만든다.",
        "tasks": [
            {
                **_COMMON_TASK,
                "difficulty": "beginner",
                "title": "지점별 주간 매출 합계 구하기",
                "goal": "지점·주차별 매출 합계 표를 만든다.",
                "steps": ["CSV 불러오기", "날짜를 주차로 변환", "지점·주차별 합계 집계"],
                "skills": ["Python", "pandas"],
            },
            {
                **_COMMON_TASK,
                "difficulty": "intermediate",
                "title": "결측·이상치 처리 후 매출 집계",
                "goal": "결측치와 이상치를 처리한 뒤 지점별 주간 매출과 전주 대비 증감률을 구한다.",
                "steps": ["결측치 확인·처리", "이상치 기준 정의·처리", "증감률 계산"],
                "skills": ["Python", "pandas", "데이터 정제"],
            },
            {
                **_COMMON_TASK,
                "difficulty": "advanced",
                "title": "주간 매출 보고서 자동 생성 파이프라인",
                "goal": "CSV 를 넣으면 정제·집계·요약까지 한 번에 보고서를 만드는 스크립트를 작성한다.",
                "steps": ["정제·집계 함수화", "보고서 템플릿 작성", "실행 스크립트로 묶기"],
                "skills": ["Python", "pandas", "자동화"],
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

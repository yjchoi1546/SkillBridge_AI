"""우리 AI 의 품질 측정 (오프라인). 청년 제출물 평가(graphs/evaluation)와는 다르다.

제안서 MVP 성과 지표 중 AI 쪽에서 측정할 것:
- KPI 01 과제 명세 필수 항목 충족률   — validation.check_draft 통과율
- KPI 02 AI 생성 과제의 기업 수정·승인율 — app 로그 필요
- KPI 06 AI 평가와 기업 평가의 일치도    — CriterionVerdict vs 기업 판정
- KPI 09 요청당 AI 비용과 생성 오류율     — 공급자별 비교 (LLM_PROVIDER 바꿔가며)

입력 샘플: ai/tests/fixtures/requests.jsonl
"""

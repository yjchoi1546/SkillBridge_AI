import type { Project, Task } from './types';

export const sampleCsv = 'date,branch,category,sales\n2026-10-01,branch_A,online,1240000\n2026-10-01,branch_B,offline,980000\n2026-10-02,branch_A,online,1380000\n2026-10-02,branch_B,offline,1050000\n2026-10-03,branch_A,offline,1120000\n';
export const tasks: Task[] = [
  { difficulty: 'beginner', title: '매출 CSV 정제 및 자동 집계', goal: '누락·중복 데이터를 정제하고 지점별 매출을 집계하는 재현 가능한 파이프라인을 만듭니다.', steps: ['샘플 데이터의 구조와 결측·중복을 확인합니다.', '정제 기준을 정의하고 지점별·날짜별 매출을 집계합니다.', '실행 방법과 검증 결과를 보고서로 정리합니다.'], deliverables: ['실행 코드 (.py 또는 .ipynb)', '결과 보고서와 실행 안내 (.md)'], skills: ['Python', 'Pandas', 'CSV'] },
  { difficulty: 'intermediate', title: '지점별 매출 대시보드 제작', goal: '매출 지표를 비교하고 기간·지점별로 탐색할 수 있는 대시보드를 만듭니다.', steps: ['데이터 정제와 주요 지표를 정의합니다.', '지점·기간 필터와 매출 차트를 구현합니다.', '사용자 관점에서 결과를 설명합니다.'], deliverables: ['대시보드 소스 코드', '지표 정의와 실행 안내 (.md)'], skills: ['Python', 'SQL', 'Streamlit'] },
  { difficulty: 'advanced', title: '이상 매출 탐지 및 알림 설계', goal: '이상 패턴 탐지 기준을 설명하고 정상·이상 사례를 검증합니다.', steps: ['기준선과 이상치 판단 기준을 설계합니다.', '탐지 파이프라인과 알림 규칙을 구현합니다.', '오탐·미탐과 한계를 분석합니다.'], deliverables: ['탐지 코드', '검증 결과와 설계 보고서 (.md)'], skills: ['Python', 'Scikit-learn', 'SQL'] },
];
const base = { status: 'PUBLISHED', duration: '2주', deadline: '2026-12-06', applicants: 12, tasks, dataset: sampleCsv, purpose: '학습·역량 검증', terms: '참여 비용과 금전 보상이 없는 학습용 과제입니다. 결과물의 권리는 작성자에게 있으며, 기업의 상업적 이용은 별도 합의가 필요합니다.' } as const;
export const seedProjects: Project[] = [
  { ...base, id: 'sales-report', title: '흩어진 매출 데이터,\n하나의 인사이트로', company: '브릿지커머스', domain: '데이터 분석', summary: '반복되는 엑셀 작업을 줄이고, 지점별 매출을 한눈에 파악할 수 있는 자동화 파이프라인을 만들어 보세요.', skills: ['Python', 'Pandas', 'CSV'], difficulty: 'beginner', color: 'purple', mark: 'B' },
  { ...base, id: 'support-ai', title: '고객 문의를 이해하는\nAI 분류 도우미', company: '커넥트랩', domain: 'AI · 머신러닝', summary: '합성 고객 문의를 유형별로 분류하고, 담당 팀에 연결하는 AI 서비스의 첫 단계를 설계합니다.', skills: ['Python', 'NLP', 'LLM'], difficulty: 'intermediate', color: 'blue', mark: 'c', applicants: 8, duration: '3주', tasks: [
    { difficulty: 'beginner', title: '문의 데이터 탐색 및 규칙 분류', goal: '문의 유형을 정의하고 규칙 기반 분류기를 만듭니다.', steps: ['문의 데이터 탐색', '분류 규칙 작성', '오분류 분석'], deliverables: ['분류 코드', '분석 보고서'], skills: ['Python', 'NLP'] },
    { difficulty: 'intermediate', title: 'AI 고객 문의 분류기', goal: '분류 정확도와 한계를 설명하는 AI 분류 파이프라인을 구현합니다.', steps: ['분류 기준 정의', '분류기 구현', '유형별 오류 분석'], deliverables: ['소스 코드', '평가 보고서'], skills: ['Python', 'NLP', 'LLM'] },
    { difficulty: 'advanced', title: '분류 신뢰도와 담당 팀 라우팅', goal: '불확실한 문의의 수동 검토와 담당 팀 라우팅을 설계합니다.', steps: ['신뢰도 기준 설정', '라우팅 구현', '수동 검토 사례 정리'], deliverables: ['라우팅 코드', '설계 보고서'], skills: ['Python', 'NLP', 'LLM'] },
  ], dataset: 'id,inquiry,category\n1,배송 상태를 알고 싶어요,shipping\n2,결제를 취소하고 싶어요,payment\n3,상품 사용법이 궁금해요,product\n' },
  { ...base, id: 'inventory', title: '부족해지기 전에,\n스마트 재고 알림', company: '그로브리테일', domain: '백엔드 개발', summary: '재고 흐름을 분석하고 부족이 예상되는 상품을 미리 알려주는 작은 서비스를 구현합니다.', skills: ['Java', 'Spring Boot', 'SQL'], difficulty: 'intermediate', color: 'green', mark: 'g', applicants: 16, tasks: [
    { difficulty: 'beginner', title: '상품 재고 조회 API', goal: '상품별 재고를 조회하는 API를 구현합니다.', steps: ['데이터 모델 정의', '조회 API 구현', '예외 처리 검증'], deliverables: ['소스 코드', 'API 명세'], skills: ['Java', 'Spring Boot'] },
    { difficulty: 'intermediate', title: '재고 부족 알림 서비스', goal: '임계값을 기반으로 재고 부족을 탐지하는 서비스를 구현합니다.', steps: ['재고 변화 분석', '임계값 알림 구현', '중복 알림 방지'], deliverables: ['소스 코드', '테스트와 실행 안내'], skills: ['Java', 'Spring Boot', 'SQL'] },
    { difficulty: 'advanced', title: '동시 주문과 재고 일관성', goal: '동시 요청 환경에서 재고 일관성을 검증합니다.', steps: ['경쟁 상태 재현', '일관성 제어 구현', '부하 테스트 분석'], deliverables: ['소스 코드', '검증 보고서'], skills: ['Java', 'Spring Boot', 'SQL'] },
  ], dataset: 'product_id,stock,threshold\nP001,42,10\nP002,8,15\nP003,64,20\n' },
  { ...base, id: 'web-dashboard', title: '숫자가 이야기가 되는\n서비스 대시보드', company: '오빗스튜디오', domain: '프론트엔드 개발', summary: '서비스 이용 데이터를 읽기 쉬운 화면으로 바꾸고, 반응형 대시보드의 사용성을 고민합니다.', skills: ['React', 'TypeScript', 'CSS'], difficulty: 'beginner', color: 'orange', mark: 'o', applicants: 9, tasks: [
    { difficulty: 'beginner', title: '서비스 지표 카드와 표', goal: '합성 이용 데이터를 접근성 있는 카드와 표로 표현합니다.', steps: ['지표 정의', '카드와 표 구현', '반응형 검증'], deliverables: ['React 소스 코드', '실행 안내'], skills: ['React', 'CSS'] },
    { difficulty: 'intermediate', title: '필터와 시각화 대시보드', goal: '기간별 필터와 차트를 구현합니다.', steps: ['데이터 가공', '필터와 차트 구현', '빈 상태 검증'], deliverables: ['소스 코드', '설계 설명'], skills: ['React', 'TypeScript'] },
    { difficulty: 'advanced', title: '대규모 데이터 탐색 UI', goal: '성능과 접근성을 고려한 데이터 탐색 화면을 만듭니다.', steps: ['성능 기준 설정', '가상 목록 구현', '성능·접근성 분석'], deliverables: ['소스 코드', '검증 보고서'], skills: ['React', 'TypeScript', 'CSS'] },
  ], dataset: 'date,visitors,signups\n2026-10-01,1240,82\n2026-10-02,1380,95\n2026-10-03,1120,76\n' },
];

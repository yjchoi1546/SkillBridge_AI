import { test, expect } from '@playwright/test';

test.skip(process.env.VITE_API_MODE !== 'browser', '브라우저 데모 흐름은 VITE_API_MODE=browser에서 확인합니다.');

test('개인 제출부터 기업 피드백, 포트폴리오까지 연결된다', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: '김브릿지님, 반가워요 👋' })).toBeVisible();
  await page.getByRole('link', { name: '이어서 하기' }).click();
  await page.getByLabel('문제 해결 과정').fill('CSV의 누락값과 중복을 확인하고 정제 규칙을 정의했습니다. 지점별 집계 결과를 수작업 계산과 비교했습니다.');
  await page.getByLabel('참고자료 목록').fill('Pandas 공식 문서');
  await page.getByLabel('AI 사용 공개').fill('사용하지 않음');
  await page.locator('input[type=file]').setInputFiles({ name: 'solution.py', mimeType: 'text/plain', buffer: Buffer.from('print("demo")') });
  await page.getByRole('button', { name: '중간 저장' }).click();
  await page.reload();
  await expect(page.getByLabel('문제 해결 과정')).toHaveValue(/CSV의 누락값/);
  await page.getByRole('button', { name: '최종 제출', exact: true }).click();
  await page.getByRole('button', { name: '제출 확정', exact: true }).click();
  const answers = page.locator('.followup-panel textarea');
  for (let i=0; i<3; i++) await answers.nth(i).fill('데이터의 특성과 예외 조건을 확인하고 기대 결과와 실제 결과를 비교하여 직접 검증했습니다.');
  await page.getByRole('button', { name: '답변 제출하고 평가 시작' }).click();
  await expect(page.getByRole('heading', { name: '기업의 피드백을 기다리고 있어요' })).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: '회원 유형 전환' }).click();
  await page.getByRole('button', { name: /업무를 프로젝트로 만들기/ }).click();
  await page.getByRole('link', { name: '제출물 검토', exact: true }).click();
  await page.locator('.work-list-item').first().click();
  await page.getByLabel('최종 피드백').fill('과정과 근거를 명확하게 설명했습니다. 다음에는 데이터가 늘어났을 때의 성능도 검증해 주세요.');
  await page.getByRole('button', { name: '피드백 등록 · 리포트 확정' }).click();
  await page.getByRole('button', { name: '회원 유형 전환' }).click();
  await page.getByRole('button', { name: /나의 실무 경험 시작하기/ }).click();
  await page.getByRole('navigation', { name: '주요 메뉴' }).getByRole('link', { name: '결과 리포트', exact: true }).click();
  await page.locator('.report-card').first().click();
  await expect(page.getByText('과정과 근거를 명확하게 설명했습니다.', { exact: false })).toBeVisible();
  await expect(page.getByText('미검증', { exact: true })).toHaveCount(6);
  await page.getByRole('button', { name: '포트폴리오에 추가', exact: true }).click();
  await expect(page.getByRole('button', { name: '포트폴리오에 추가됨' })).toBeDisabled();
  expect(errors).toEqual([]);
});

test('기업 원문은 공개 화면에 노출되지 않고 생성과 공개를 거친다', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: '회원 유형 전환' }).click();
  await page.getByRole('button', { name: /업무를 프로젝트로 만들기/ }).click();
  await page.getByRole('link', { name: '새 업무 요청 작성' }).click();
  await page.getByLabel('해결하고 싶은 업무').fill('고객사 SECRET-NAME의 주간 매출 보고서 정제와 집계를 자동화하고 싶습니다.');
  await page.getByLabel('공개하면 안 되는 단어').fill('SECRET-NAME');
  await page.getByRole('button', { name: 'AI 과제 초안 준비하기' }).click();
  await expect(page.getByRole('heading', { name: '공개 과제 명세' })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole('button', { name: '공개 승인' })).toBeDisabled();
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: '공개 승인' }).click();
  await page.getByRole('link', { name: '공개 화면 보기' }).click();
  await expect(page.locator('main')).not.toContainText('SECRET-NAME');
});

test('검색·필터·빈 결과와 모바일 레이아웃을 확인한다', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/projects');
  const projectCount = await page.locator('.project-card').count();
  await page.getByRole('button', { name: '백엔드 개발', exact: true }).click();
  await expect(page.locator('.project-card')).toHaveCount(1);
  await page.getByLabel('프로젝트 키워드 검색').fill('없는 프로젝트');
  await expect(page.getByRole('heading', { name: '조건에 맞는 프로젝트가 없어요' })).toBeVisible();
  await page.getByRole('button', { name: '필터 초기화' }).click();
  await expect(page.locator('.project-card')).toHaveCount(projectCount);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: '메뉴 열기' }).click();
  await expect(page.getByRole('link', { name: '내 프로젝트' })).toBeVisible();
  await page.getByRole('button', { name: '메뉴 닫기' }).click();
  await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true, animations: 'disabled' });
});

test('데스크톱 대시보드 화면', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: '김브릿지님, 반가워요 👋' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('desktop.png'), fullPage: true, animations: 'disabled' });
});

import { test, expect } from '@playwright/test';

test.skip(process.env.VITE_API_MODE === 'browser', '실제 계정 UI는 서버 모드에서 확인합니다.');

test.beforeEach(async ({ page }) => {
  const tokens = new Map<string, { token: string; name: string; role: string }>();
  const accounts = new Map<string, { password: string; name: string; role: string }>();
  await page.route('**/api/**', async route => {
    const request = route.request(); const path = new URL(request.url()).pathname;
    const json = (body: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    const token = request.headers().authorization?.replace('Bearer ', '') || '';
    if (path === '/api/health') return json({ status: 'UP', storage: 'test', ai: 'demo' });
    if (path === '/api/auth/register') {
      const input = request.postDataJSON();
      if (accounts.has(input.email)) return json({ message: '이미 등록된 이메일입니다.' }, 409);
      accounts.set(input.email, input);
      const session = { token: `test-session-${tokens.size}`, name: input.name, role: input.role }; tokens.set(session.token, session); return json(session, 201);
    }
    if (path === '/api/auth/login') {
      const input = request.postDataJSON(); const account = accounts.get(input.email);
      if (!account || account.password !== input.password) return json({ message: '이메일 또는 비밀번호가 올바르지 않습니다.' }, 401);
      const session = { token: `test-session-${tokens.size}`, name: account.name, role: account.role }; tokens.set(session.token, session); return json(session);
    }
    if (path === '/api/auth/me') return tokens.has(token) ? json(tokens.get(token)) : json({ message: '로그인이 필요합니다.' }, 401);
    if (path === '/api/auth/logout') { tokens.delete(token); return route.fulfill({ status: 204 }); }
    if (path === '/api/projects') return json([]);
    if (['/api/applications', '/api/projects/participating', '/api/company/projects', '/api/company/submissions'].includes(path)) return tokens.has(token) ? json([]) : json({ message: '로그인이 필요합니다.' }, 401);
    return json({ message: '이 테스트에서 지원하지 않는 API입니다.' }, 404);
  });
});

test('개인 회원가입·세션 복원·로그아웃·재로그인 UI (모의 API)', async ({ page }) => {
  await page.goto('/my/projects');
  await expect(page.getByRole('heading', { name: '다시 만나 반가워요' })).toBeVisible();
  await expect(page).toHaveURL(/\/login\?redirect=/);
  await page.getByRole('link', { name: '회원가입', exact: true }).click();
  await page.getByLabel('이름', { exact: true }).fill('테스트참여자');
  await page.getByLabel('이메일', { exact: true }).fill('learner@example.test');
  await page.getByLabel('비밀번호', { exact: true }).fill('test-password-123');
  await page.getByRole('button', { name: '계정 만들기' }).click();
  await expect(page).toHaveURL(/\/my\/projects$/);
  await expect(page.getByRole('heading', { name: '경험을 쌓아가는 중' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: '경험을 쌓아가는 중' })).toBeVisible();
  await page.getByRole('button', { name: '내 계정', exact: true }).click();
  await expect(page.getByText('회원 유형은 가입한 계정에 연결됩니다.', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: '나의 실무 경험 시작하기', exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: '로그아웃', exact: true }).click();
  await expect(page.getByRole('heading', { name: '다시 만나 반가워요' })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('skillbridge-session'))).toBeNull();
  await page.getByLabel('이메일', { exact: true }).fill('learner@example.test');
  await page.getByLabel('비밀번호', { exact: true }).fill('incorrect-password');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('이메일 또는 비밀번호');
  await page.getByLabel('비밀번호', { exact: true }).fill('test-password-123');
  await page.getByRole('button', { name: '로그인', exact: true }).click();
  await expect(page.getByRole('heading', { name: '테스트참여자님, 반가워요 👋' })).toBeVisible();
});

test('기업 가입과 공개 탐색, 모바일 인증 화면 (모의 API)', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/projects');
  await expect(page.getByRole('heading', { name: '가능성을 넓히는 프로젝트' })).toBeVisible();
  await page.getByRole('link', { name: '시작하기', exact: true }).click();
  await page.getByRole('radio', { name: /기업 회원/ }).check();
  await page.getByLabel('기업명', { exact: true }).fill('테스트기업');
  await page.getByLabel('이메일', { exact: true }).fill('company@example.test');
  await page.getByLabel('비밀번호', { exact: true }).fill('test-company-password');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('register-mobile.png'), fullPage: true, animations: 'disabled' });
  await page.getByRole('button', { name: '계정 만들기' }).click();
  await expect(page.getByRole('heading', { name: '테스트기업님, 반가워요 👋' })).toBeVisible();
  await page.goto('/my/projects');
  await expect(page).toHaveURL(/\/company\/projects$/);
});

test('세션 만료와 안전한 로그인 이동 경로 (모의 API)', async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem('skillbridge-session', 'expired-session'));
  await page.goto('/login?redirect=//outside.example');
  await expect(page.getByRole('heading', { name: '다시 만나 반가워요' })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('skillbridge-session'))).toBeNull();
  await page.getByRole('link', { name: '회원가입', exact: true }).click();
  await page.getByLabel('이름', { exact: true }).fill('안전한사용자');
  await page.getByLabel('이메일', { exact: true }).fill('redirect@example.test');
  await page.getByLabel('비밀번호', { exact: true }).fill('safe-password-123');
  await page.getByRole('button', { name: '계정 만들기' }).click();
  await expect.poll(() => new URL(page.url()).pathname).toBe('/');
  expect(new URL(page.url()).hostname).toBe('127.0.0.1');
});

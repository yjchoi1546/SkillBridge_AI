import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { seedProjects, tasks, sampleCsv } from './data';
import type { Application, Difficulty, NewRequest, Project, Registration, Role, RuntimeInfo, Session, Submission } from './types';

const serverMode = import.meta.env.VITE_API_MODE !== 'browser';
const key = 'skillbridge-demo-v1';
const sessionKey = 'skillbridge-session';
const guestSession: Session = { token: '', name: '방문자', role: 'PERSON' };
function storedToken() { try { return sessionStorage.getItem(sessionKey) || ''; } catch { return ''; } }
function persistToken(token: string) { try { if (token) sessionStorage.setItem(sessionKey, token); else sessionStorage.removeItem(sessionKey); } catch { /* The current tab still works when storage is unavailable. */ } }
class HttpError extends Error { constructor(message: string, readonly status: number) { super(message); } }
interface State { projects: Project[]; applications: Application[] }
const initial: State = { projects: seedProjects, applications: [{ id: 'app-sales', projectId: 'sales-report', difficulty: 'beginner', status: 'WORKING', process: '', references: '', aiUsage: '', files: {}, questions: [], answers: [], feedback: '', portfolio: false }] };
function load(): State {
  try { const saved = localStorage.getItem(key); return saved ? JSON.parse(saved) as State : structuredClone(initial); }
  catch { return structuredClone(initial); }
}
const demoSession = (role: Role): Session => ({ token: 'browser-demo', name: role === 'PERSON' ? '김브릿지' : '브릿지커머스', role });
interface Store extends State {
  session: Session; authenticated: boolean; mode: 'browser' | 'server'; error: string; loading: boolean; runtime: RuntimeInfo | null;
  login: (email: string, password: string) => Promise<void>; register: (input: Registration) => Promise<void>; logout: () => Promise<void>;
  switchRole: (role: Role) => Promise<void>; refresh: () => Promise<void>;
  createRequest: (input: NewRequest) => Promise<string>;
  answerClarifications: (id: string, answers: string[]) => Promise<void>;
  revise: (id: string, feedback: string) => Promise<void>; publish: (id: string) => Promise<void>; retry: (id: string) => Promise<void>; closeProject: (id: string) => Promise<void>;
  apply: (projectId: string, difficulty: Difficulty) => Promise<string>;
  saveWork: (id: string, input: Submission) => Promise<void>;
  submit: (id: string, input: Submission) => Promise<void>;
  answer: (id: string, answers: string[]) => Promise<void>;
  finalize: (id: string, feedback: string) => Promise<void>;
  portfolio: (id: string) => Promise<void>;
}
const Context = createContext<Store | null>(null);
export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>(() => serverMode ? { projects: [], applications: [] } : load());
  const [session, setSession] = useState<Session>(serverMode ? guestSession : demoSession('PERSON'));
  const [authenticated, setAuthenticated] = useState(!serverMode);
  const [runtime, setRuntime] = useState<RuntimeInfo | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(serverMode);
  const tokenRef = useRef(serverMode ? storedToken() : '');
  const sessionRef = useRef(session);
  const request = useCallback(async <T,>(path: string, method = 'GET', body?: unknown): Promise<T> => {
    const response = await fetch(`/api${path}`, { method, headers: { 'Content-Type': 'application/json', ...(tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {}) }, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
    if (!response.ok) { let message = `요청에 실패했습니다 (${response.status})`; try { message = (await response.json()).message || message; } catch { /* non-JSON gateway error */ } throw new HttpError(message, response.status); }
    return response.status === 204 ? undefined as T : response.json() as Promise<T>;
  }, []);
  const refresh = useCallback(async () => {
    if (!serverMode) return;
    const requestToken = tokenRef.current;
    const company = sessionRef.current.role === 'COMPANY';
    const [publicProjects, privateProjects, applications] = await Promise.all([
      request<Project[]>('/projects'),
      requestToken ? request<Project[]>(company ? '/company/projects' : '/projects/participating') : Promise.resolve([]),
      requestToken ? request<Application[]>(company ? '/company/submissions' : '/applications') : Promise.resolve([]),
    ]);
    const projects = new Map(publicProjects.map(p => [p.id, { ...p, owned: false }]));
    privateProjects.forEach(p => projects.set(p.id, { ...p, owned: company }));
    if (tokenRef.current === requestToken) { setState({ projects: [...projects.values()], applications }); setError(''); }
  }, [request]);
  const clearSession = useCallback(() => {
    tokenRef.current = ''; persistToken(''); sessionRef.current = guestSession;
    setSession(guestSession); setAuthenticated(false); setState({ projects: [], applications: [] });
  }, []);
  const acceptSession = async (next: Session) => {
    tokenRef.current = next.token; persistToken(next.token); sessionRef.current = next;
    setSession(next); setAuthenticated(true); setState({ projects: [], applications: [] });
    await refresh();
  };
  useEffect(() => {
    if (!serverMode) { try { localStorage.setItem(key, JSON.stringify(state)); } catch { setError('브라우저 저장 공간이 부족합니다. 첨부 파일을 줄여 주세요.'); } }
  }, [state]);
  useEffect(() => {
    if (!serverMode) return;
    let active = true;
    (async () => {
      try {
        const health = await request<RuntimeInfo>('/health'); if (active) setRuntime(health);
        if (tokenRef.current) {
          try { const restored = await request<Session>('/auth/me'); if (!active) return; sessionRef.current = restored; setSession(restored); setAuthenticated(true); }
          catch (e) { if (e instanceof HttpError && e.status === 401) { if (active) clearSession(); } else throw e; }
        }
        if (active) await refresh();
      } catch (e) { if (active) setError(e instanceof Error ? e.message : '서버에 연결하지 못했습니다.'); }
      finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [request, refresh, clearSession]);
  useEffect(() => {
    if (!serverMode) return;
    if (loading) return;
    const tick = () => { const token = tokenRef.current; refresh().catch(e => { if (tokenRef.current !== token) return; if (e instanceof HttpError && e.status === 401) { clearSession(); setError('로그인이 만료되었습니다. 다시 로그인해 주세요.'); } else setError(e.message); }); };
    const interval = setInterval(tick, 2500); return () => clearInterval(interval);
  }, [refresh, loading, clearSession]);
  // Restore pending browser-demo jobs after a refresh. No external AI call is made.
  useEffect(() => {
    if (serverMode) return;
    const interval = setInterval(() => setState(s => {
      if (!s.projects.some(p => p.status === 'GENERATING') && !s.applications.some(a => a.status === 'EVALUATING')) return s;
      return { projects: s.projects.map(p => p.status === 'GENERATING' ? { ...p, status: 'DRAFT' } : p), applications: s.applications.map(a => a.status === 'EVALUATING' ? { ...a, status: 'REVIEW', evaluation: { summary: '데모 평가 초안입니다. 실제 코드 실행과 AI 평가는 수행하지 않았습니다. 기업의 검토가 필요합니다.', criteria: ['집계 정확성', '요구사항 충족', '재현 가능성'].map(name => ({ name, status: 'unverified', comment: '실제 평가 연동 전 · 기업 확인 필요' })) } } : a) };
    }), 3500);
    return () => clearInterval(interval);
  }, []);
  const updateApp = (id: string, patch: Partial<Application>) => setState(s => ({ ...s, applications: s.applications.map(a => a.id === id ? { ...a, ...patch } : a) }));
  const updateProject = (id: string, patch: Partial<Project>) => setState(s => ({ ...s, projects: s.projects.map(p => p.id === id ? { ...p, ...patch } : p) }));
  const mutate = async (path: string, body?: unknown) => { await request(path, 'POST', body ?? {}); await refresh(); };
  const value: Store = {
    ...state, session, authenticated, runtime, mode: serverMode ? 'server' : 'browser', error, loading, refresh,
    login: async (email, password) => { await acceptSession(await request<Session>('/auth/login', 'POST', { email, password })); },
    register: async input => { await acceptSession(await request<Session>('/auth/register', 'POST', input)); },
    logout: async () => { try { if (serverMode && tokenRef.current) await request('/auth/logout', 'POST'); } finally { clearSession(); await refresh(); } },
    switchRole: async role => {
      if (serverMode) throw new Error('회원 유형은 계정에 연결되어 있습니다. 다른 계정으로 로그인해 주세요.');
      else setSession(demoSession(role));
    },
    createRequest: async input => {
      if (serverMode) { const p = await request<Project>('/company/requests', 'POST', input); await refresh(); return p.id; }
      const id = crypto.randomUUID();
      const project: Project = { id, title: `${input.jobRole} 실무 프로젝트`, company: '브릿지커머스', domain: input.jobRole, summary: '업무 데이터를 정제하고 분석 결과를 재현 가능한 결과물로 만드는 데모 과제입니다. 실제 AI 생성 결과는 연동 후 제공됩니다.', skills: ['Python', 'CSV'], difficulty: 'beginner', duration: '2주', deadline: '2026-12-06', applicants: 0, status: 'GENERATING', color: 'purple', mark: 'B', tasks: structuredClone(tasks), dataset: sampleCsv, purpose: '학습·역량 검증', terms: seedProjects[0].terms, requestText: input.requestText, sensitiveWords: input.sensitiveWords, generalization: input.generalization, revision: 1 };
      project.attachments = input.attachments;
      setState(s => ({ ...s, projects: [project, ...s.projects] })); return id;
    },
    answerClarifications: async (id, answers) => { if (serverMode) await mutate(`/company/projects/${id}/clarifications`, { answers }); else updateProject(id, { status: 'GENERATING' }); },
    revise: async (id, feedback) => { if (serverMode) await mutate(`/company/projects/${id}/revise`, { feedback }); else setState(s => ({ ...s, projects: s.projects.map(p => p.id === id ? { ...p, status: 'GENERATING', feedback, revision: (p.revision ?? 1) + 1 } : p) })); },
    publish: async id => { if (serverMode) await mutate(`/company/projects/${id}/publish`); else updateProject(id, { status: 'PUBLISHED' }); },
    closeProject: async id => { if (serverMode) await mutate(`/company/projects/${id}/close`); else updateProject(id, { status: 'CLOSED' }); },
    retry: async id => { if (serverMode) await mutate(`/company/projects/${id}/retry`); else updateProject(id, { status: 'GENERATING', error: undefined }); },
    apply: async (projectId, difficulty) => {
      if (serverMode) { const a = await request<Application>('/applications', 'POST', { projectId, difficulty }); await refresh(); return a.id; }
      const existing = state.applications.find(a => a.projectId === projectId); if (existing) return existing.id;
      const a: Application = { id: crypto.randomUUID(), projectId, difficulty, status: 'WORKING', process: '', references: '', aiUsage: '', files: {}, questions: [], answers: [], feedback: '', portfolio: false };
      setState(s => ({ ...s, applications: [...s.applications, a] })); return a.id;
    },
    saveWork: async (id, input) => { if (serverMode) await mutate(`/applications/${id}/work`, input); else updateApp(id, input); },
    submit: async (id, input) => {
      if (serverMode) await mutate(`/applications/${id}/submit`, input);
      else updateApp(id, { ...input, status: 'FOLLOWUP', questions: [`${Object.keys(input.files)[0] || '제출 파일'}에서 가장 중요한 설계 선택과 그 이유를 설명해 주세요.`, '다른 입력이나 예외 상황에서 결과를 어떻게 검증했나요?', 'AI 또는 참고자료를 활용한 부분과 직접 검증한 부분을 구분해 주세요.'], answers: ['', '', ''] });
    },
    answer: async (id, answers) => { if (serverMode) await mutate(`/applications/${id}/answers`, { answers }); else updateApp(id, { answers, status: 'EVALUATING' }); },
    finalize: async (id, feedback) => { if (serverMode) await mutate(`/company/submissions/${id}/finalize`, { feedback }); else updateApp(id, { feedback, status: 'FINALIZED' }); },
    portfolio: async id => { if (serverMode) await mutate(`/applications/${id}/portfolio`); else updateApp(id, { portfolio: true }); },
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export const useStore = () => { const value = useContext(Context); if (!value) throw new Error('StoreProvider is required'); return value; };

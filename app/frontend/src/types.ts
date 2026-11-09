export type Role = 'PERSON' | 'COMPANY';
export type Difficulty = 'beginner' | 'intermediate' | 'advanced';
export type ProjectStatus = 'GENERATING' | 'NEEDS_CLARIFICATION' | 'DRAFT' | 'PUBLISHED' | 'CLOSED' | 'FAILED';
export type ApplicationStatus = 'WORKING' | 'QUESTIONING' | 'FOLLOWUP' | 'EVALUATING' | 'REVIEW' | 'FINALIZED';
export interface Session { token: string; name: string; role: Role }
export interface Registration { email: string; password: string; name: string; role: Role }
export interface RuntimeInfo { status: string; storage: string; ai: string; demoEnabled?: boolean }
export interface Task { difficulty: Difficulty; title: string; goal: string; steps: string[]; deliverables: string[]; skills: string[] }
export interface Project {
  id: string; title: string; company: string; domain: string; summary: string; skills: string[];
  difficulty: Difficulty; duration: string; deadline: string; applicants: number; status: ProjectStatus;
  color: string; mark: string; tasks: Task[]; dataset: string; purpose: string;
  terms: string; requestText?: string; sensitiveWords?: string; generalization?: string;
  feedback?: string; revision?: number; error?: string; jobId?: string;
  attachments?: { name: string; contentBase64: string }[];
  owned?: boolean; engine?: 'demo' | 'python';
  disclosure?: { status: 'clear' | 'blocked' | 'unchecked'; findings: string[] };
  aiProvider?: string; clarifyingQuestions?: { id: string; question: string; reason: string }[];
}
export interface Submission { files: Record<string, string>; process: string; references: string; aiUsage: string }
export interface Application {
  id: string; projectId: string; difficulty: Difficulty; status: ApplicationStatus;
  process: string; references: string; aiUsage: string; files: Record<string, string>;
  questions: string[]; answers: string[]; feedback: string; portfolio: boolean;
  error?: string; questionSource?: 'template' | 'ai';
  evaluation?: { summary: string; criteria: { name: string; status: string; comment: string }[]; demo?: boolean; source?: 'demo' | 'python'; tests?: { testId: string; passed: boolean | null; detail: string }[] };
}
export interface NewRequest { requestText: string; jobRole: string; sensitiveWords: string; generalization: string; attachments: { name: string; contentBase64: string }[] }
export const difficultyLabel: Record<Difficulty, string> = { beginner: '초급', intermediate: '중급', advanced: '고급' };
export const statusLabel: Record<ProjectStatus | ApplicationStatus, string> = {
  GENERATING: '생성 중', NEEDS_CLARIFICATION: '추가 정보 필요', DRAFT: '초안 검토', PUBLISHED: '모집 중', CLOSED: '마감', FAILED: '생성 실패',
  WORKING: '수행 중', QUESTIONING: '질문 준비 중', FOLLOWUP: '후속 질문', EVALUATING: '평가 중', REVIEW: '기업 검토', FINALIZED: '리포트 확정',
};

import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownToLine, ArrowRight, Bookmark, Check, Clock3, Users, X } from 'lucide-react';
import type { Project } from './types';
import { difficultyLabel } from './types';

export function notify(message: string, error = false) { window.dispatchEvent(new CustomEvent('sb-toast', { detail: { message, error } })); }
export function useAction() {
  const [busy, setBusy] = useState(false);
  async function run(action: () => Promise<unknown>, success?: string) {
    setBusy(true);
    try { await action(); if (success) notify(success); }
    catch (error) { notify(error instanceof Error ? error.message : '처리 중 오류가 발생했습니다.', true); }
    finally { setBusy(false); }
  }
  return { busy, run };
}
export function Toasts() {
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const listener = (event: Event) => { setToast((event as CustomEvent).detail); clearTimeout(timer); timer = setTimeout(() => setToast(null), 4500); };
    window.addEventListener('sb-toast', listener); return () => { window.removeEventListener('sb-toast', listener); clearTimeout(timer); };
  }, []);
  return toast && <div role={toast.error ? 'alert' : 'status'} className={`toast ${toast.error ? 'toast-error' : ''}`}><Check size={18} />{toast.message}<button aria-label="알림 닫기" onClick={() => setToast(null)}><X size={16} /></button></div>;
}
export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { const el = dialog.current; el?.showModal(); return () => el?.close(); }, []);
  return <dialog className="modal" ref={dialog} onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}><div className="modal-title"><h2>{title}</h2><button className="icon-button" aria-label="닫기" onClick={onClose}><X size={20} /></button></div>{children}</dialog>;
}
export function Empty({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty"><div className="empty-symbol">↗</div><h3>{title}</h3><p>{description}</p>{action}</div>;
}
export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
export function CompanyMark({ project, small = false }: { project: Project; small?: boolean }) {
  return <span className={`company-mark ${project.color} ${small ? 'small' : ''}`}>{project.mark}</span>;
}
export function ProjectCard({ project, saved, onSave }: { project: Project; saved?: boolean; onSave?: () => void }) {
  return <article className="project-card">
    <div className="card-top"><span className={`badge level-${project.difficulty}`}>{difficultyLabel[project.difficulty]}</span><button className={`icon-button bookmark ${saved ? 'is-saved' : ''}`} aria-label={saved ? '관심 프로젝트 해제' : '관심 프로젝트 저장'} aria-pressed={!!saved} onClick={onSave}><Bookmark size={18} fill={saved ? 'currentColor' : 'none'} /></button></div>
    <Link to={`/projects/${project.id}`} className="card-main"><span className="domain-label">{project.domain}</span><h3>{project.title.split('\n').map((line, i) => <span key={i}>{line}<br /></span>)}</h3><p>{project.summary}</p></Link>
    <div className="tags">{project.skills.slice(0, 3).map(s => <span key={s}>{s}</span>)}</div>
    <div className="card-meta"><span><Clock3 size={13} />{project.duration}</span><span><Users size={13} />{project.applicants}명 참여</span><span className="recruiting"><i /> 모집 중</span></div>
    <div className="company-row"><CompanyMark project={project} small /><span>{project.company}</span><Link to={`/projects/${project.id}`} aria-label={`${project.title.replace('\n', ' ')} 자세히 보기`}><ArrowRight size={17} /></Link></div>
  </article>;
}
export function download(filename: string, body: string, type = 'text/plain;charset=utf-8') {
  const url = URL.createObjectURL(new Blob(['\uFEFF', body], { type }));
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function Dataset({ csv }: { csv: string }) {
  const rows = csv.trim().split(/\r?\n/).slice(0, 5).map(row => row.split(','));
  return <section className="panel"><div className="section-heading"><div><h3>실습 데이터</h3><p>기업 원문을 포함하지 않는 합성 샘플 데이터입니다.</p></div><button className="button secondary compact" onClick={() => download('sample_data.csv', csv, 'text/csv;charset=utf-8')}><ArrowDownToLine size={15} />CSV 다운로드</button></div><div className="table-scroll"><table><thead><tr>{rows[0]?.map((c, i) => <th key={i}>{c}</th>)}</tr></thead><tbody>{rows.slice(1).map((row, i) => <tr key={i}>{row.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody></table></div></section>;
}

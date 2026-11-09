import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, Building2, Check, Eye, EyeOff, ShieldCheck, Sparkles, UserRound } from 'lucide-react';
import { useStore } from '../store';
import type { Role } from '../types';
import '../auth.css';

function destination(value: string | null) {
  return value?.startsWith('/') && !value.startsWith('//') && !/[\\\u0000-\u001f\u007f]/.test(value) && !/^\/(login|register)(\?|$)/.test(value) ? value : '/';
}

export function AuthPage({ kind }: { kind: 'login' | 'register' }) {
  const { authenticated, login, register } = useStore(); const navigate = useNavigate(); const [params] = useSearchParams();
  const [role, setRole] = useState<Role>('PERSON'); const [name, setName] = useState(''); const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const registration = kind === 'register'; const next = destination(params.get('redirect'));
  useEffect(() => { setError(''); setPassword(''); setVisible(false); }, [kind]);
  if (authenticated) return <Navigate to={next} replace />;
  return <div className="auth-layout"><section className="auth-story"><span className="auth-kicker"><Sparkles size={15} />EXPERIENCE BECOMES EVIDENCE</span><h1>나의 다음 기회는,<br />해낸 경험에서 시작됩니다.</h1><p>기업의 실제 업무를 프로젝트로 경험하고,<br />과정과 피드백이 담긴 나만의 기록을 쌓아보세요.</p><div className="auth-journey">{['나에게 맞는 실무 프로젝트 발견', '문제 해결 과정과 결과물 기록', '기업 검토를 거친 결과 리포트'].map((text, i) => <div key={text}><span>{i === 2 ? <Check size={13} /> : i + 1}</span>{text}</div>)}</div><Link to="/projects">먼저 프로젝트 둘러보기<ArrowRight size={15} /></Link><div className="auth-story-art" aria-hidden="true"><div className="auth-art-card"><span><Sparkles size={17} />MY NEXT POSSIBILITY</span><div className="auth-art-bars"><i /><i /><i /><i /><i /></div><strong>경험을 연결하고, 가능성을 넓히다.</strong></div><span className="auth-art-orbit" /></div></section><section className="auth-form-panel"><span className="eyebrow">WELCOME TO SKILLBRIDGE</span><h2>{registration ? '새로운 경험을 시작하세요' : '다시 만나 반가워요'}</h2><p className="auth-subtitle">{registration ? '개인 또는 기업 계정을 만들고 워크스페이스를 열어보세요.' : '내 계정으로 로그인하고 진행하던 경험을 이어가세요.'}</p><form onSubmit={async e => {
    e.preventDefault(); setError('');
    if (registration && new TextEncoder().encode(password).length > 72) { setError('비밀번호는 UTF-8 기준 72바이트 이하여야 합니다. 한글 등은 여러 바이트로 계산됩니다.'); return; }
    setBusy(true);
    try {
      if (registration) await register({ name: name.trim(), email: email.trim().toLowerCase(), password, role });
      else await login(email.trim().toLowerCase(), password);
      navigate(next, { replace: true });
    } catch (failure) { setError(failure instanceof Error ? failure.message : '요청을 처리하지 못했습니다. 다시 시도해 주세요.'); }
    finally { setBusy(false); }
  }}><fieldset disabled={busy}>{registration && <><div className="auth-role-options" role="group" aria-label="회원 유형"><label className={role === 'PERSON' ? 'selected' : ''}><input type="radio" name="role" checked={role === 'PERSON'} onChange={() => setRole('PERSON')} /><UserRound size={21} /><strong>개인 회원</strong><small>실무 경험을 쌓고 싶어요</small></label><label className={role === 'COMPANY' ? 'selected' : ''}><input type="radio" name="role" checked={role === 'COMPANY'} onChange={() => setRole('COMPANY')} /><Building2 size={21} /><strong>기업 회원</strong><small>업무 과제를 개설하고 싶어요</small></label></div><label className="field"><span>{role === 'COMPANY' ? '기업명' : '이름'}</span><input autoComplete={role === 'COMPANY' ? 'organization' : 'name'} required minLength={2} maxLength={100} value={name} onChange={e => setName(e.target.value)} placeholder={role === 'COMPANY' ? '기업 또는 팀 이름' : '워크스페이스에서 사용할 이름'} /></label></>}<label className="field"><span>이메일</span><input type="email" autoComplete="email" required maxLength={255} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" /></label><div className="field"><label htmlFor="auth-password">비밀번호</label><div className="auth-password-field"><input id="auth-password" aria-describedby={registration ? 'auth-password-note' : undefined} type={visible ? 'text' : 'password'} autoComplete={registration ? 'new-password' : 'current-password'} required minLength={registration ? 10 : undefined} maxLength={72} value={password} onChange={e => setPassword(e.target.value)} placeholder={registration ? '10자 이상으로 입력하세요' : '비밀번호를 입력하세요'} /><button type="button" aria-label={visible ? '비밀번호 숨기기' : '비밀번호 표시'} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={17} /> : <Eye size={17} />}</button></div>{registration && <small id="auth-password-note" className="field-note">10자 이상 · UTF-8 기준 72바이트 이하. 다른 사이트와 다른 비밀번호를 사용하세요.</small>}</div>{error && <div className="auth-error" role="alert">{error}</div>}<button className="button primary auth-submit" type="submit" disabled={busy}>{busy ? '처리하는 중…' : registration ? '계정 만들기' : '로그인'}<ArrowRight size={16} /></button></fieldset></form><div className="auth-switch">{registration ? '이미 계정이 있으신가요?' : '아직 계정이 없으신가요?'}<Link to={`${registration ? '/login' : '/register'}${params.get('redirect') ? `?redirect=${encodeURIComponent(next)}` : ''}`}>{registration ? '로그인' : '회원가입'}</Link></div><div className="auth-security"><ShieldCheck size={16} /><p>회원 유형과 프로젝트 권한은 계정별로 관리합니다.<br />기업 원문과 제출물은 허용된 사용자에게만 제공됩니다.</p></div></section></div>;
}

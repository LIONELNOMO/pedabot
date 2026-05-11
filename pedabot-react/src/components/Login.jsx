import React, { useState } from 'react';
import { useApp } from '../context/AppContext';

const API_URL = import.meta.env.VITE_API_URL;

const DEMO_ACCOUNTS = [
  { nom: 'Prof. Demo',  email: 'demo@pedabot.com',  password: 'demo123' },
  { nom: 'M. Kamga',   email: 'kamga@pedabot.com', password: 'demo123' },
  { nom: 'Mme Ngono',  email: 'ngono@pedabot.com', password: 'demo123' },
];

export default function Login() {
  const { loginUser } = useApp();
  const [tab, setTab] = useState('login');
  const [nom, setNom]           = useState('');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm]   = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  const reset = () => { setNom(''); setEmail(''); setPassword(''); setConfirm(''); setError(''); };
  const switchTab = (t) => { setTab(t); reset(); };
  const fillDemo = (d) => { setEmail(d.email); setPassword(d.password); setError(''); };

  const doClose = (userData, token) => {
    setIsClosing(true);
    setTimeout(() => loginUser(userData, token), 480);
  };

  const handleGuest = () => {
    doClose({ id: 0, email: '', nom: 'Invité' }, 'guest');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    if (!email || !password) { setError('Remplissez tous les champs.'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || 'Erreur de connexion.'); return; }
      doClose(data.user, data.token);
    } catch { setError('Impossible de contacter le serveur.'); }
    finally { setLoading(false); }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (!nom || !email || !password || !confirm) { setError('Remplissez tous les champs.'); return; }
    if (password !== confirm) { setError('Les mots de passe ne correspondent pas.'); return; }
    if (password.length < 6) { setError('Mot de passe trop court (6 caractères minimum).'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nom, email, password })
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || 'Erreur lors de la création du compte.'); return; }
      doClose(data.user, data.token);
    } catch { setError('Impossible de contacter le serveur.'); }
    finally { setLoading(false); }
  };

  return (
    <div id="pg-login" className={isClosing ? 'out' : ''}>

      {/* ════ PANNEAU GAUCHE ════ */}
      <div className="ll-panel">
        <div className="ll-orb ll-orb1"></div>
        <div className="ll-orb ll-orb2"></div>
        <div className="ll-orb ll-orb3"></div>
        <div className="ll-orb ll-orb4"></div>
        <div className="ll-grid"></div>

        {/* Particules flottantes */}
        {[...Array(14)].map((_, i) => (
          <span key={i} className="ll-particle" style={{
            left: `${8 + (i * 6.5) % 86}%`,
            animationDelay: `${(i * 0.7) % 7}s`,
            animationDuration: `${5 + (i * 1.1) % 5}s`,
            width: `${3 + (i % 3) * 2}px`,
            height: `${3 + (i % 3) * 2}px`,
            opacity: 0.15 + (i % 4) * 0.1,
          }}/>
        ))}

        {/* Badges flottants animés */}
        <div className="ll-badge ll-badge1">◈ IA Pédagogique</div>
        <div className="ll-badge ll-badge2">≡ 40 Patterns</div>
        <div className="ll-badge ll-badge3">★ Export PDF</div>

        <div className="ll-content">
          <div className="ll-logo-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
            </svg>
          </div>

          <h1 className="ll-title">Péda<span>Bot</span></h1>
          <p className="ll-tagline">
            Transformez vos cours en exercices pédagogiques intelligents en quelques secondes.
          </p>

          <div className="ll-features">
            <div className="ll-feat">
              <span className="ll-feat-icon">◈</span>
              <div>
                <div className="ll-feat-title">40 patterns de détection</div>
                <div className="ll-feat-desc">Définitions, causes, syntaxe, comparaisons…</div>
              </div>
            </div>
            <div className="ll-feat">
              <span className="ll-feat-icon">≡</span>
              <div>
                <div className="ll-feat-title">Import multi-format</div>
                <div className="ll-feat-desc">PDF, Word, texte brut</div>
              </div>
            </div>
            <div className="ll-feat">
              <span className="ll-feat-icon">★</span>
              <div>
                <div className="ll-feat-title">3 niveaux d'exercices</div>
                <div className="ll-feat-desc">Facile, Moyen, Difficile ou Progressif</div>
              </div>
            </div>
          </div>

          <div className="ll-dots">
            <span className="ll-dot active"></span>
            <span className="ll-dot"></span>
            <span className="ll-dot"></span>
          </div>
        </div>
      </div>

      {/* ════ PANNEAU DROIT ════ */}
      <div className="lr-panel">
        <div className="lr-inner">

          {/* Logo top */}
          <div className="lr-top">
            <div className="lr-logo">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
              </svg>
            </div>
            <span className="lr-brand">Péda<b>Bot</b></span>
          </div>

          <h2 className="lr-heading">
            {tab === 'login' ? 'Bon retour 👋' : 'Créer un compte'}
          </h2>
          <p className="lr-sub">
            {tab === 'login' ? 'Connectez-vous à votre espace enseignant.' : 'Rejoignez PédaBot gratuitement.'}
          </p>

          {/* Tabs */}
          <div className="auth-tabs">
            <button className={`auth-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => switchTab('login')}>
              Se connecter
            </button>
            <button className={`auth-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => switchTab('register')}>
              S'inscrire
            </button>
          </div>

          {/* Formulaire connexion */}
          {tab === 'login' && (
            <form onSubmit={handleLogin} className="auth-form">
              <label className="llabel">Email</label>
              <input className="linput" type="email" placeholder="votre@email.com"
                value={email} onChange={e => setEmail(e.target.value)} />

              <label className="llabel">Mot de passe</label>
              <input className="linput" type="password" placeholder="••••••••"
                value={password} onChange={e => setPassword(e.target.value)} />

              {error && <div className="auth-error">⚠ {error}</div>}

              <button className="btn-cta" type="submit" disabled={loading}>
                {loading ? '◌ Connexion…' : 'Se connecter →'}
              </button>

              <div className="auth-divider"><span>accès rapide</span></div>
              <div className="demo-grid">
                {DEMO_ACCOUNTS.map(d => (
                  <button key={d.email} type="button" className="demo-btn" onClick={() => fillDemo(d)}>
                    <span className="demo-avatar">{d.nom.substring(0, 2).toUpperCase()}</span>
                    <span className="demo-name">{d.nom}</span>
                  </button>
                ))}
              </div>
            </form>
          )}

          {/* Formulaire inscription */}
          {tab === 'register' && (
            <form onSubmit={handleRegister} className="auth-form">
              <label className="llabel">Nom complet</label>
              <input className="linput" type="text" placeholder="M. Kamga, Mme Ebolo…"
                value={nom} onChange={e => setNom(e.target.value)} />

              <label className="llabel">Email</label>
              <input className="linput" type="email" placeholder="votre@email.com"
                value={email} onChange={e => setEmail(e.target.value)} />

              <label className="llabel">Mot de passe</label>
              <input className="linput" type="password" placeholder="Minimum 6 caractères"
                value={password} onChange={e => setPassword(e.target.value)} />

              <label className="llabel">Confirmer le mot de passe</label>
              <input className="linput" type="password" placeholder="Répétez le mot de passe"
                value={confirm} onChange={e => setConfirm(e.target.value)} />

              {error && <div className="auth-error">⚠ {error}</div>}

              <button className="btn-cta" type="submit" disabled={loading}>
                {loading ? '◌ Création…' : 'Créer mon compte →'}
              </button>
            </form>
          )}

          {import.meta.env.VITE_GUEST_MODE === 'true' && (
            <button className="btn-guest" type="button" onClick={handleGuest}>
              Continuer sans compte →
            </button>
          )}

        </div>
      </div>
    </div>
  );
}

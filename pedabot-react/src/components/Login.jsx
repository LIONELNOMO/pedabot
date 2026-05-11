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
  const [tab, setTab]           = useState('login');   // 'login' | 'register'
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
    } catch {
      setError('Impossible de contacter le serveur.');
    } finally {
      setLoading(false);
    }
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
    } catch {
      setError('Impossible de contacter le serveur.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div id="pg-login" className={isClosing ? 'out' : ''}>
      <div className="login-bg-circle c1"></div>
      <div className="login-bg-circle c2"></div>

      <div className="lcard">
        {/* Logo + titre */}
        <div className="llogo">
          <svg viewBox="0 0 24 24">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
          </svg>
        </div>
        <h1 className="ltitle">Péda<span>Bot</span></h1>
        <p className="lsub">Assistant intelligent de consolidation pédagogique</p>

        {/* Tabs */}
        <div className="auth-tabs">
          <button className={`auth-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => switchTab('login')}>
            Se connecter
          </button>
          <button className={`auth-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => switchTab('register')}>
            Créer un compte
          </button>
        </div>

        {/* Formulaire connexion */}
        {tab === 'login' && (
          <form onSubmit={handleLogin}>
            <label className="llabel">Email</label>
            <input className="linput" type="email" placeholder="votre@email.com"
              value={email} onChange={e => setEmail(e.target.value)} />

            <label className="llabel">Mot de passe</label>
            <input className="linput" type="password" placeholder="••••••••"
              value={password} onChange={e => setPassword(e.target.value)} />

            {error && <div className="auth-error">{error}</div>}

            <button className="btn-cta" type="submit" disabled={loading}>
              {loading ? '◌ Connexion en cours…' : 'Se connecter →'}
            </button>

            {/* Comptes démo */}
            <div className="auth-divider"><span>ou tester avec un compte démo</span></div>
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
          <form onSubmit={handleRegister}>
            <label className="llabel">Votre nom complet</label>
            <input className="linput" type="text" placeholder="Ex : M. Kamga, Mme Ebolo..."
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

            {error && <div className="auth-error">{error}</div>}

            <button className="btn-cta" type="submit" disabled={loading}>
              {loading ? '◌ Création en cours…' : 'Créer mon compte →'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

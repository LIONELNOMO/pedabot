import React, { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL;

export default function ElevePage({ token }) {
  const [state, setState]       = useState('loading'); // loading | ready | submitted | error
  const [data, setData]         = useState(null);
  const [prenom, setPrenom]     = useState('');
  const [reponses, setReponses] = useState('');
  const [sending, setSending]   = useState(false);
  const [prenomError, setPrenomError] = useState('');

  useEffect(() => {
    fetch(`${API_URL}/api/eleve/${token}`)
      .then(r => r.json())
      .then(d => {
        if (d.detail) { setState('error'); return; }
        setData(d);
        setState('ready');
      })
      .catch(() => setState('error'));
  }, [token]);

  const handleSubmit = async () => {
    if (!prenom.trim()) { setPrenomError('Entrez votre prénom pour continuer.'); return; }
    if (!reponses.trim()) { setPrenomError('Écrivez vos réponses avant de soumettre.'); return; }
    setPrenomError('');
    setSending(true);
    try {
      const res = await fetch(`${API_URL}/api/eleve/${token}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eleve_prenom: prenom.trim(), reponses: reponses.trim() }),
      });
      if (res.ok) setState('submitted');
      else setPrenomError('Erreur lors de l\'envoi. Réessayez.');
    } catch {
      setPrenomError('Impossible de contacter le serveur.');
    } finally {
      setSending(false);
    }
  };

  const lvlLabel = (level) =>
    level === 'facile' ? 'Niveau Facile' : level === 'moyen' ? 'Niveau Moyen' : 'Niveau Avancé';
  const lvlClass = (level) =>
    level === 'facile' ? 'easy' : level === 'moyen' ? 'med' : 'hard';

  if (state === 'loading') return (
    <div className="ep-shell">
      <div className="ep-loading">◌ Chargement de l'exercice…</div>
    </div>
  );

  if (state === 'error') return (
    <div className="ep-shell">
      <div className="ep-error-box">
        <div className="ep-error-icon">⚠</div>
        <h2>Lien invalide</h2>
        <p>Ce lien est introuvable ou a expiré. Demandez un nouveau lien à votre enseignant.</p>
      </div>
    </div>
  );

  if (state === 'submitted') return (
    <div className="ep-shell">
      <div className="ep-success-box">
        <div className="ep-success-icon">✓</div>
        <h2>Copie envoyée !</h2>
        <p>Merci <strong>{prenom}</strong>, votre réponse a bien été transmise à {data?.teacher_nom}.</p>
        <p className="ep-success-sub">Vous pouvez fermer cette page.</p>
      </div>
    </div>
  );

  const ex = data.exercise;

  return (
    <div className="ep-shell">
      {/* Header */}
      <header className="ep-header">
        <div className="ep-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" width="22" height="22">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
          </svg>
          <span>Péda<b>Bot</b></span>
        </div>
        <div className="ep-teacher">Exercice de <strong>{data.teacher_nom}</strong></div>
      </header>

      <div className="ep-body">
        {/* Exercice */}
        <div className="ep-card">
          <span className={`exlvl ${lvlClass(ex.level)}`}>{lvlLabel(ex.level)}</span>
          <h1 className="ep-title">{ex.title}</h1>
          <div className="ep-content" dangerouslySetInnerHTML={{ __html: ex.body }} />
          {ex.code && <pre className="ep-code">{ex.code}</pre>}
        </div>

        {/* Zone de réponse */}
        <div className="ep-answer-box">
          <h2 className="ep-answer-title">Votre réponse</h2>

          <label className="ep-label">Votre prénom *</label>
          <input
            className="ep-input"
            type="text"
            placeholder="Ex : Jean-Paul, Amina…"
            value={prenom}
            onChange={e => { setPrenom(e.target.value); setPrenomError(''); }}
          />

          <label className="ep-label" style={{ marginTop: '16px' }}>Vos réponses *</label>
          <textarea
            className="ep-textarea"
            placeholder={"Répondez ici à chaque question…\n\nQuestion 1 : …\nQuestion 2 : …"}
            value={reponses}
            onChange={e => setReponses(e.target.value)}
            rows={10}
          />

          {prenomError && <div className="ep-field-error">⚠ {prenomError}</div>}

          <button className="ep-submit" onClick={handleSubmit} disabled={sending}>
            {sending ? '◌ Envoi en cours…' : '✓ Soumettre ma copie'}
          </button>
        </div>
      </div>
    </div>
  );
}

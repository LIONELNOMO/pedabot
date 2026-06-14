import React, { useState, useEffect, useMemo } from 'react';
import { useApp } from '../context/AppContext';

const API_URL = import.meta.env.VITE_API_URL;

const DIFF_LABEL = { facile: 'Facile', moyen: 'Moyen', difficile: 'Difficile', progressif: 'Progressif' };
const DIFF_CLASS = { facile: 'easy', moyen: 'med', difficile: 'hard', progressif: 'hard' };

export default function EleveDashboard() {
  const { user, token, logoutUser } = useApp();
  const [view, setView]         = useState('list');
  const [filter, setFilter]     = useState('tous');
  const [exercises, setExercises] = useState(null);
  const [selected, setSelected] = useState(null);
  const [reponses, setReponses] = useState('');
  const [sending, setSending]   = useState(false);
  const [error, setError]       = useState('');

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const loadExercises = async () => {
    setExercises(null);
    try {
      const res  = await fetch(`${API_URL}/api/mes-exercices`, { headers });
      const data = await res.json();
      setExercises(Array.isArray(data) ? data : []);
    } catch {
      setExercises([]);
    }
  };

  useEffect(() => { loadExercises(); }, []);

  const openExercise = async (ex) => {
    try {
      const res  = await fetch(`${API_URL}/api/exercice/${ex.id}`, { headers });
      const data = await res.json();
      setSelected(data);
      setReponses(data.reponses || '');
      setView(data.submitted ? 'corrige' : 'exercise');
    } catch {
      setError('Impossible de charger cet exercice.');
    }
  };

  const handleSubmit = async () => {
    if (!reponses.trim()) { setError('Écrivez vos réponses avant de soumettre.'); return; }
    setSending(true);
    setError('');
    try {
      const res = await fetch(`${API_URL}/api/exercice/${selected.id}/submit`, {
        method: 'POST', headers,
        body: JSON.stringify({ reponses: reponses.trim() }),
      });
      if (res.ok) {
        setSelected(prev => ({ ...prev, submitted: true, reponses: reponses.trim() }));
        setView('corrige');
        loadExercises();
      } else {
        const d = await res.json();
        setError(d.detail || 'Erreur lors de la soumission.');
      }
    } catch { setError('Impossible de contacter le serveur.'); }
    finally { setSending(false); }
  };

  const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'long' }) : '';
  const fmtFull = (iso) => iso ? new Date(iso).toLocaleString('fr-FR') : '';
  const prenom = user?.nom?.split(' ')[0] || 'Élève';

  // ─── Stats ───
  const stats = useMemo(() => {
    if (!Array.isArray(exercises)) return { total: 0, todo: 0, done: 0 };
    const total = exercises.length;
    const done  = exercises.filter(e => e.submitted).length;
    return { total, done, todo: total - done };
  }, [exercises]);

  // ─── Filtrage ───
  const filtered = useMemo(() => {
    if (!Array.isArray(exercises)) return [];
    if (filter === 'todo') return exercises.filter(e => !e.submitted);
    if (filter === 'done') return exercises.filter(e => e.submitted);
    return exercises;
  }, [exercises, filter]);

  return (
    <div className="ed-shell">

      {/* ── HEADER ── */}
      <header className="ed-header">
        <div className="ed-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" width="20" height="20">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
          </svg>
          <span>Péda<b>Bot</b></span>
          <span className="ed-role-badge">Espace Élève</span>
        </div>
        <div className="ed-user">
          <div className="ed-avatar">{prenom.substring(0, 2).toUpperCase()}</div>
          <span className="ed-username">{user?.nom}</span>
          <button className="ed-logout" onClick={logoutUser}>Déconnexion</button>
        </div>
      </header>

      <div className="ed-body">

        {/* ════ VUE LISTE ════ */}
        {view === 'list' && (
          <>
            {/* Bannière de bienvenue */}
            <div className="ed-hero">
              <div className="ed-hero-text">
                <div className="ed-hero-greeting">Bonjour <strong>{prenom}</strong> 👋</div>
                <div className="ed-hero-sub">
                  {stats.todo > 0
                    ? <>Vous avez <strong>{stats.todo}</strong> exercice{stats.todo > 1 ? 's' : ''} à faire. Bon courage !</>
                    : stats.total > 0
                      ? <>Tout est à jour. Beau travail !</>
                      : <>Aucun exercice pour le moment. Votre enseignant vous en enverra bientôt.</>}
                </div>
              </div>
              <div className="ed-hero-illus" aria-hidden>
                <svg viewBox="0 0 64 64" width="80" height="80" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 18h40v36H12z" opacity=".15" fill="currentColor"/>
                  <path d="M12 18h40v36H12z"/>
                  <path d="M20 28h24M20 36h24M20 44h16"/>
                  <path d="M52 18l-8-8H20l-8 8" />
                </svg>
              </div>
            </div>

            {/* Cartes stats */}
            <div className="ed-stats">
              <div className="ed-stat">
                <div className="ed-stat-num">{stats.total}</div>
                <div className="ed-stat-lbl">Total</div>
              </div>
              <div className="ed-stat todo">
                <div className="ed-stat-num">{stats.todo}</div>
                <div className="ed-stat-lbl">À faire</div>
              </div>
              <div className="ed-stat done">
                <div className="ed-stat-num">{stats.done}</div>
                <div className="ed-stat-lbl">Soumis</div>
              </div>
            </div>

            {/* Filtres */}
            <div className="ed-section-title">
              <span>Mes exercices</span>
              <button className="ed-refresh" onClick={loadExercises} title="Actualiser">↻</button>
            </div>

            <div className="ed-filters">
              <button className={`ed-filter ${filter === 'tous' ? 'active' : ''}`} onClick={() => setFilter('tous')}>
                Tous ({stats.total})
              </button>
              <button className={`ed-filter ${filter === 'todo' ? 'active' : ''}`} onClick={() => setFilter('todo')}>
                À faire ({stats.todo})
              </button>
              <button className={`ed-filter ${filter === 'done' ? 'active' : ''}`} onClick={() => setFilter('done')}>
                Soumis ({stats.done})
              </button>
            </div>

            {/* États */}
            {exercises === null && <div className="ed-empty">◌ Chargement…</div>}

            {Array.isArray(exercises) && exercises.length === 0 && (
              <div className="ed-empty-state">
                <div className="ed-empty-icon">≡</div>
                <h3>Aucun exercice pour l'instant</h3>
                <p>Quand votre enseignant vous enverra un devoir, il apparaîtra ici. Restez à l'écoute !</p>
              </div>
            )}

            {Array.isArray(exercises) && exercises.length > 0 && filtered.length === 0 && (
              <div className="ed-empty">Aucun exercice dans cette catégorie.</div>
            )}

            {filtered.map(ex => (
              <div key={ex.id} className={`ed-card ${ex.submitted ? 'submitted' : ''}`}>
                <div className="ed-card-left">
                  <span className={`exlvl ${DIFF_CLASS[ex.difficulty] || 'easy'}`}>
                    {DIFF_LABEL[ex.difficulty] || ex.difficulty || '—'}
                  </span>
                  <div className="ed-card-titre">{ex.titre}</div>
                  <div className="ed-card-meta">
                    De <strong>{ex.teacher_nom}</strong> · {fmtDate(ex.created_at)}
                  </div>
                </div>
                <div className="ed-card-right">
                  {ex.submitted
                    ? <span className="ed-tag done">✓ Soumis</span>
                    : <span className="ed-tag todo">À faire</span>
                  }
                  <button className="ed-open-btn" onClick={() => openExercise(ex)}>
                    {ex.submitted ? 'Voir corrigé →' : 'Commencer →'}
                  </button>
                </div>
              </div>
            ))}

            {/* Section conseils */}
            {Array.isArray(exercises) && exercises.length > 0 && (
              <div className="ed-tips">
                <div className="ed-tips-title">★ Conseils</div>
                <ul className="ed-tips-list">
                  <li>Prenez le temps de lire l'énoncé en entier avant de répondre.</li>
                  <li>Une fois soumise, votre copie ne peut plus être modifiée.</li>
                  <li>Votre enseignant peut vous envoyer un retour : pensez à revenir consulter vos devoirs corrigés.</li>
                </ul>
              </div>
            )}
          </>
        )}

        {/* ════ VUE EXERCICE ════ */}
        {view === 'exercise' && selected && (
          <>
            <button className="ed-back" onClick={() => { setView('list'); setError(''); }}>‹ Mes exercices</button>
            <div className="ed-ex-card">
              <span className={`exlvl ${DIFF_CLASS[selected.exercise?.level] || 'easy'}`}>
                {DIFF_LABEL[selected.exercise?.level] || selected.exercise?.level || '—'}
              </span>
              <h2 className="ed-ex-titre">{selected.titre}</h2>
              <div className="ed-ex-meta">Exercice de <strong>{selected.teacher_nom}</strong></div>
              <div className="ed-ex-body" dangerouslySetInnerHTML={{ __html: selected.exercise?.body }} />
              {selected.exercise?.code && <pre className="ed-ex-code">{selected.exercise.code}</pre>}
            </div>

            <div className="ed-answer-card">
              <h3 className="ed-answer-title">Votre réponse</h3>
              <textarea
                className="ed-textarea"
                placeholder={"Répondez à chaque question ici…\n\nQuestion 1 : …\nQuestion 2 : …"}
                value={reponses}
                onChange={e => { setReponses(e.target.value); setError(''); }}
                rows={10}
              />
              {error && <div className="ed-error">⚠ {error}</div>}
              <button className="ed-submit" onClick={handleSubmit} disabled={sending}>
                {sending ? '◌ Envoi…' : '✓ Soumettre ma copie'}
              </button>
            </div>
          </>
        )}

        {/* ════ VUE CORRIGÉ ════ */}
        {view === 'corrige' && selected && (
          <>
            <button className="ed-back" onClick={() => { setView('list'); }}>‹ Mes exercices</button>

            <div className="ed-corrige-banner">
              ✓ Copie soumise{selected.submitted_at ? ` le ${fmtFull(selected.submitted_at)}` : ''}
            </div>

            <div className="ed-ex-card">
              <span className={`exlvl ${DIFF_CLASS[selected.exercise?.level] || 'easy'}`}>
                {DIFF_LABEL[selected.exercise?.level] || selected.exercise?.level || '—'}
              </span>
              <h2 className="ed-ex-titre">{selected.titre}</h2>
              <div className="ed-ex-meta">Exercice de <strong>{selected.teacher_nom}</strong></div>
              <div className="ed-ex-body" dangerouslySetInnerHTML={{ __html: selected.exercise?.body }} />
              {selected.exercise?.code && <pre className="ed-ex-code">{selected.exercise.code}</pre>}
            </div>

            <div className="ed-answer-card">
              <h3 className="ed-answer-title">Votre réponse soumise</h3>
              <div className="ed-rep-display">{selected.reponses}</div>
            </div>

            {/* Feedback du prof */}
            {selected.feedback ? (
              <div className="ed-feedback-card">
                <div className="ed-feedback-head">
                  <span className="ed-feedback-avatar">{(selected.teacher_nom || 'P').substring(0, 2).toUpperCase()}</span>
                  <div>
                    <div className="ed-feedback-from">Retour de <strong>{selected.teacher_nom}</strong></div>
                    <div className="ed-feedback-date">{fmtFull(selected.feedback_at)}</div>
                  </div>
                </div>
                <div className="ed-feedback-body">{selected.feedback}</div>
              </div>
            ) : (
              <div className="ed-feedback-waiting">
                ◌ En attente du retour de votre enseignant…
              </div>
            )}
          </>
        )}

      </div>
    </div>
  );
}

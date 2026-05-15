import React, { useState } from 'react';
import { useApp } from '../context/AppContext';

const API_URL = import.meta.env.VITE_API_URL;

// ══════════════════════════════════════
//  SOUS-COMPOSANTS (un par type interactif)
//  React ne fait aucune logique d'analyse !
// ══════════════════════════════════════

// ----- MESSAGE TEXTE / HTML -----
function TextMessage({ msg, isBot, initial }) {
  return (
    <div className={`mrow ${isBot ? 'bot' : 'user'}`}>
      <div className={`mavatar ${isBot ? 'bot' : 'usr'}`}>{initial}</div>
      {msg.html ? (
        <div className="mbubble" dangerouslySetInnerHTML={{ __html: msg.text }}></div>
      ) : (
        <div className="mbubble">{msg.text}</div>
      )}
    </div>
  );
}

// ----- TYPING DOTS -----
function TypingMessage() {
  return (
    <div className="typing">
      <div className="mavatar bot">PB</div>
      <div className="tdots"><span></span><span></span><span></span></div>
    </div>
  );
}

// ----- SECTIONS CHECKBOXES -----
function SectionsMessage({ msg }) {
  const { setStep, setWizardDraft, addMessage } = useApp();
  const [checkedIdxs, setCheckedIdxs] = useState(msg.sections.map((_, i) => i));
  const [confirmed, setConfirmed] = useState(false);

  const toggleCheck = (idx) => {
    if (confirmed) return;
    if (checkedIdxs.includes(idx)) setCheckedIdxs(checkedIdxs.filter(i => i !== idx));
    else setCheckedIdxs([...checkedIdxs, idx]);
  };

  const handleConfirm = () => {
    if (checkedIdxs.length === 0) {
      alert("△ Sélectionnez au moins une section.");
      return;
    }
    setConfirmed(true);
    const chosen = msg.sections.filter((_, i) => checkedIdxs.includes(i));
    setWizardDraft(prev => ({ ...prev, selSections: chosen }));

    addMessage({ type: 'typing', sender: 'bot' });
    setTimeout(() => {
      addMessage({ type: 'difficulty', sender: 'bot' });
      setStep('WAIT_DIFF');
    }, 700);
  };

  return (
    <div className="mrow bot">
      <div className="mavatar bot">PB</div>
      <div className="mbubble">
        ≡ J'ai détecté <strong>{msg.sections.length} partie{msg.sections.length > 1 ? 's' : ''}</strong> dans votre cours.<br/>
        Cochez celles sur lesquelles créer des exercices :
        <div className="chklist">
          {msg.sections.map((s, i) => (
            <label key={i} className="chkitem">
              <input
                type="checkbox"
                checked={checkedIdxs.includes(i)}
                onChange={() => toggleCheck(i)}
                disabled={confirmed}
              />
              <span className="section-num">{s.num || '§'}</span>
              <span>{s.title}</span>
            </label>
          ))}
        </div>
        <button className="confirm-btn" onClick={handleConfirm} disabled={confirmed}>
          {confirmed ? `✓ ${checkedIdxs.length} section(s) confirmée(s)` : 'Confirmer la sélection →'}
        </button>
      </div>
    </div>
  );
}

// ----- DIFFICULTÉ -----
function DifficultyMessage() {
  const { setStep, setWizardDraft, addMessage, wizardDraft } = useApp();
  const [selected, setSelected] = useState(null);

  const pickDiff = (key, label) => {
    setSelected(key);
    setWizardDraft(prev => ({ ...prev, difficulty: key }));
    addMessage({ type: 'text', sender: 'user', text: label });

    addMessage({ type: 'typing', sender: 'bot' });
    setTimeout(() => {
      setStep('WAIT_CONFIRM');
      addMessage({ type: 'recap', sender: 'bot' });
    }, 700);
  };

  const diffs = [
    { key: 'facile', label: '● Facile', desc: 'Reconnaissance & QCM' },
    { key: 'moyen', label: '◆ Moyen', desc: 'Complétion de code' },
    { key: 'difficile', label: '▲ Difficile', desc: 'Production autonome' },
    { key: 'progressif', label: '» Progressif', desc: 'Les 3 niveaux' }
  ];

  const selCount = wizardDraft.selSections ? wizardDraft.selSections.length : 0;

  return (
    <div className="mrow bot">
      <div className="mavatar bot">PB</div>
      <div className="mbubble">
        Excellent ! 🎯 Pour les <strong>{selCount} section(s)</strong> retenues,<br/>
        quel niveau de difficulté souhaitez-vous ?
        <div className="bbtns">
          {diffs.map(d => (
            <button
              key={d.key}
              className={`bbtn ${selected === d.key ? 'sel' : ''}`}
              title={d.desc}
              onClick={() => pickDiff(d.key, d.label)}
              disabled={selected !== null}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ----- RÉCAPITULATIF -----
function RecapMessage() {
  const { setStep, wizardDraft, addMessage, setWizardDraft } = useApp();
  const [confirmed, setConfirmed] = useState(false);

  const secList = wizardDraft.selSections
    ? wizardDraft.selSections.map(s => `${s.num ? s.num + ' — ' : ''}${s.title}`).join(', ')
    : '—';
  const langLabel = wizardDraft.lang === 'algo' ? 'Algorithmique' : wizardDraft.lang === 'python' ? 'Python' : 'JavaScript';

  const handleGenerate = () => {
    setConfirmed(true);
    addMessage({ type: 'text', sender: 'bot', text: '◈ Génération des exercices en cours…' });
    addMessage({ type: 'typing', sender: 'bot' });

    // ══════ APPEL PYTHON : /api/generate ══════
    const payload = {
      exName: wizardDraft.exName,
      difficulty: wizardDraft.difficulty,
      lang: wizardDraft.lang,
      appro: false,
      sections: wizardDraft.selSections
    };

    fetch(`${API_URL}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
      setStep('DONE');
      const exCount = data.exercises ? data.exercises.length : 0;
      const secCount = wizardDraft.selSections ? wizardDraft.selSections.length : 0;

      // Sauvegarder les stats dans le context pour le RightPanel
      setWizardDraft(prev => ({ ...prev, exCount, secCount }));

      addMessage({ type: 'text', sender: 'bot', text: `★ <strong>${exCount} exercice${exCount > 1 ? 's' : ''}</strong> générés pour <em>"${wizardDraft.exName}"</em> !`, html: true });

      if (data.exercises) {
        data.exercises.forEach(ex => {
          addMessage({ type: 'exercise', sender: 'bot', exercise: ex });
        });
      }
      addMessage({ type: 'text', sender: 'bot', text: `✓ Terminé ! Exportez vos exercices en PDF depuis le panneau de droite.`, html: true });
    })
    .catch(err => {
      console.error("Erreur génération:", err);
      setStep('DONE');
      addMessage({ type: 'text', sender: 'bot', text: 'Le service est temporairement indisponible. Veuillez réessayer dans quelques instants.', html: false });
    });
  };

  const handleRestart = () => {
    setConfirmed(true);
    addMessage({type:'text', sender:'bot', text:'D\'accord, recommençons ! Modifiez votre cours si nécessaire et cliquez de nouveau sur <strong>"Analyser le cours"</strong>.', html:true});
    setStep('IDLE');
  };

  return (
    <div className="mrow bot">
      <div className="mavatar bot">PB</div>
      <div className="mbubble">
        ≡ <strong>Récapitulatif avant génération</strong>
        <br/><br/>
        <strong>Nom :</strong> {wizardDraft.exName}<br/>
        <strong>Sections :</strong> {secList}<br/>
        <strong>Difficulté :</strong> {wizardDraft.difficulty}<br/>
        <strong>Syntaxe :</strong> {langLabel}<br/><br/>
        Tout est correct ?
        <div className="bbtns">
          <button className="bbtn ok" disabled={confirmed} onClick={handleGenerate}>✓ Générer les exercices</button>
          <button className="bbtn no" disabled={confirmed} onClick={handleRestart}>← Recommencer</button>
        </div>
      </div>
    </div>
  );
}

// ----- EXERCISE CARD -----
function ExerciseMessage({ msg }) {
  const { exercise } = msg;
  const { token: authToken, wizardDraft } = useApp();
  const [modal, setModal]       = useState(false);
  const [eleves, setEleves]     = useState(null);   // null | 'loading' | []
  const [selected, setSelected] = useState([]);     // emails cochés
  const [status, setStatus]     = useState(null);   // null | 'loading' | 'ok' | 'error'

  const lvlClass = exercise.level === 'facile' ? 'easy' : exercise.level === 'moyen' ? 'med' : 'hard';
  const lvlLabel = exercise.level === 'facile' ? 'Niveau Facile' : exercise.level === 'moyen' ? 'Niveau Moyen' : 'Niveau Avancé';

  const openModal = async () => {
    if (authToken === 'guest') { alert('Créez un compte pour envoyer des exercices.'); return; }
    setModal(true);
    setStatus(null);
    setSelected([]);
    setEleves('loading');
    try {
      const res  = await fetch(`${API_URL}/api/eleves`, { headers: { Authorization: `Bearer ${authToken}` } });
      const data = await res.json();
      setEleves(Array.isArray(data) ? data : []);
    } catch { setEleves([]); }
  };

  const toggleEleve = (email) => {
    setSelected(prev => prev.includes(email) ? prev.filter(e => e !== email) : [...prev, email]);
  };

  const handleAssign = async () => {
    if (selected.length === 0) { setStatus('error'); return; }
    setStatus('loading');
    try {
      const res = await fetch(`${API_URL}/api/exercises/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({
          titre:      exercise.title,
          exercise,
          lang:       wizardDraft.lang || '',
          difficulty: exercise.level || '',
          emails:     selected,
        }),
      });
      setStatus(res.ok ? 'ok' : 'error');
    } catch { setStatus('error'); }
  };

  return (
    <div className="mrow bot">
      <div className="mavatar bot">PB</div>
      <div className="excard">
        <span className={`exlvl ${lvlClass}`}>{lvlLabel}</span>
        <div className="extitle">{exercise.title}</div>
        <div className="exbody" dangerouslySetInnerHTML={{__html: exercise.body}}></div>
        {exercise.code && <div className="excode">{exercise.code}</div>}
        <button className="share-btn" onClick={openModal}>✉ Envoyer aux élèves</button>
      </div>

      {modal && (
        <div className="share-overlay" onClick={() => setModal(false)}>
          <div className="share-modal" onClick={e => e.stopPropagation()}>
            <div className="sm-head">
              <span className="sm-title">Envoyer aux élèves</span>
              <button className="sm-close" onClick={() => setModal(false)}>✕</button>
            </div>

            {status === 'ok' ? (
              <div className="sm-ok">
                ✓ Exercice envoyé à {selected.length} élève{selected.length > 1 ? 's' : ''} ! Ils le verront en se connectant.
              </div>
            ) : (
              <>
                {eleves === 'loading' && <div className="sm-loading">◌ Chargement des élèves…</div>}

                {Array.isArray(eleves) && eleves.length === 0 && (
                  <div className="sm-hint">Aucun élève inscrit pour l'instant. Les élèves doivent créer un compte avec le rôle "Élève".</div>
                )}

                {Array.isArray(eleves) && eleves.length > 0 && (
                  <>
                    <div className="sm-label">Sélectionnez les élèves :</div>
                    <div className="sm-eleve-list">
                      {eleves.map(e => (
                        <label key={e.email} className={`sm-eleve-row ${selected.includes(e.email) ? 'checked' : ''}`}>
                          <input
                            type="checkbox"
                            checked={selected.includes(e.email)}
                            onChange={() => toggleEleve(e.email)}
                          />
                          <div className="sm-eleve-avatar">{e.nom.substring(0, 2).toUpperCase()}</div>
                          <div className="sm-eleve-info">
                            <span className="sm-eleve-nom">{e.nom}</span>
                            <span className="sm-eleve-email">{e.email}</span>
                          </div>
                        </label>
                      ))}
                    </div>

                    {status === 'error' && (
                      <div className="sm-error">⚠ Sélectionnez au moins un élève.</div>
                    )}

                    <div className="sm-footer">
                      <span className="sm-count">
                        {selected.length > 0 ? `${selected.length} élève${selected.length > 1 ? 's' : ''} sélectionné${selected.length > 1 ? 's' : ''}` : 'Aucun élève sélectionné'}
                      </span>
                      <button className="sm-send-btn" onClick={handleAssign} disabled={status === 'loading'}>
                        {status === 'loading' ? '◌ Envoi…' : '✓ Envoyer'}
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════
//  COMPOSANT PRINCIPAL — DISPATCHER
// ══════════════════════════════════════
export default function MessageItem({ msg }) {
  const { user } = useApp();

  const isBot = msg.sender === 'bot';
  const initial = isBot ? 'PB' : (user?.nom || 'P').substring(0, 2).toUpperCase();

  switch (msg.type) {
    case 'typing':
      return <TypingMessage />;
    case 'sections':
      return <SectionsMessage msg={msg} />;
    case 'difficulty':
      return <DifficultyMessage />;
    case 'recap':
      return <RecapMessage />;
    case 'exercise':
      return <ExerciseMessage msg={msg} />;
    case 'text':
    default:
      return <TextMessage msg={msg} isBot={isBot} initial={initial} />;
  }
}

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
  const lvlClass = exercise.level === 'facile' ? 'easy' : exercise.level === 'moyen' ? 'med' : 'hard';
  const lvlLabel = exercise.level === 'facile' ? 'Niveau Facile' : exercise.level === 'moyen' ? 'Niveau Moyen' : 'Niveau Avancé';

  return (
    <div className="mrow bot">
      <div className="mavatar bot">PB</div>
      <div className="excard">
        <span className={`exlvl ${lvlClass}`}>{lvlLabel}</span>
        <div className="extitle">{exercise.title}</div>
        <div className="exbody" dangerouslySetInnerHTML={{__html: exercise.body}}></div>
        {exercise.code && <div className="excode">{exercise.code}</div>}
      </div>
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

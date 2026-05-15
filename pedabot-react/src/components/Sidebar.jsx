import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';

// ══════════════════════════════════════
//  SIDEBAR — Appelle le backend Python pour TOUT
//  React ne fait aucune logique d'analyse !
// ══════════════════════════════════════

const API_URL = import.meta.env.VITE_API_URL;

export default function Sidebar() {
  const { setStep, addMessage, wizardDraft, setWizardDraft, step } = useApp();
  const [activeTab, setActiveTab] = useState('saisir');
  const [courseText, setCourseText] = useState('');
  const [isAnalyzed, setIsAnalyzed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Quand resetSession remet step à IDLE, on réinitialise la sidebar
  useEffect(() => {
    if (step === 'IDLE') {
      setCourseText('');
      setIsAnalyzed(false);
      setActiveTab('saisir');
    }
  }, [step]);

  const analyzeCourse = async () => {
    if (courseText.trim().length < 20) {
      addMessage({ type: 'text', sender: 'bot', text: 'Veuillez d\'abord saisir votre cours dans le panneau de gauche avant de lancer l\'analyse.' });
      return;
    }

    // Si déjà analysé → on repart de zéro proprement
    if (isAnalyzed) {
      setIsAnalyzed(false);
      setStep('IDLE');
      setMessages([]);
      setWizardDraft({ exName: '', sections: [], selSections: [], difficulty: '', lang: 'algo' });
    }

    setIsLoading(true);

    // Message utilisateur
    addMessage({ type: 'text', sender: 'user', text: '≡ Cours soumis pour analyse.' });
    // Typing indicator
    addMessage({ type: 'typing', sender: 'bot' });

    try {
      // ══════ APPEL PYTHON : /api/analyze ══════
      const res = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ courseText: courseText.trim() })
      });

      if (!res.ok) {
        throw new Error(`Erreur serveur : ${res.status}`);
      }

      const data = await res.json();
      // data = { lang: "algo", langLabel: "Algorithmique", sections: [{num, title, content}, ...] }

      setIsAnalyzed(true);
      setWizardDraft(prev => ({
        ...prev,
        lang: data.lang,
        sections: data.sections,
        courseText: courseText,
        courseName: data.courseName || ''
      }));

      setStep('WAIT_NAME');

      const courseNameLine = data.courseName
        ? `Votre leçon s'appelle : <strong>${data.courseName}</strong><br>`
        : '';
      const sectionsLine = data.sections.length > 0
        ? `<strong>${data.sections.length}</strong> section${data.sections.length > 1 ? 's' : ''} repérée${data.sections.length > 1 ? 's' : ''}.<br><br>`
        : '<br>';

      addMessage({
        type: 'text',
        sender: 'bot',
        text: `✓ Cours reçu et analysé !<br><br>
               ${courseNameLine}
               ${sectionsLine}
               Quel <strong>nom</strong> voulez-vous donner à cette série d'exercices ?<br>
               <small style="color:var(--text-3)">Ex : TP Boucles — Seconde A, Consolidation Chapitre 3…</small>`,
        html: true
      });

    } catch (err) {
      console.error('Erreur analyse:', err);
      addMessage({
        type: 'text',
        sender: 'bot',
        text: `Le service est temporairement indisponible. Veuillez réessayer dans quelques instants.`,
        html: false
      });
    } finally {
      setIsLoading(false);
    }
  };

  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState('');

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsExtracting(true);
    setExtractError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_URL}/api/extract`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        setExtractError(data.detail || 'Erreur lors de l\'extraction.');
        return;
      }

      setCourseText(data.text);
      setActiveTab('saisir');
    } catch (err) {
      setExtractError('Service temporairement indisponible. Veuillez réessayer dans quelques instants.');
    } finally {
      setIsExtracting(false);
      e.target.value = '';
    }
  };

  return (
    <aside className="sidebar">
      <div className="sb-head">
        <div className="sb-htitle">
          <div className="sb-icon">≡</div>
          Votre cours
        </div>
        <div className="tabs">
          <button className={`tab ${activeTab === 'saisir' ? 'on' : ''}`} onClick={() => setActiveTab('saisir')}>✎ Saisir</button>
          <button className={`tab ${activeTab === 'import' ? 'on' : ''}`} onClick={() => setActiveTab('import')}>⊕ Importer</button>
        </div>
      </div>

      {/* ── ONGLET SAISIR ── */}
      <div className="sb-body" style={{ display: activeTab === 'saisir' ? 'flex' : 'none', flexDirection: 'column' }}>
        <textarea
          className="course-ta"
          placeholder={`Copiez votre cours ici...\n\nExemple :\nI. La Boucle POUR\nUtilisée quand le nombre de répétitions\nest connu à l'avance...\n\nII. La Boucle TANT QUE\nLa condition est vérifiée avant chaque\ntour de boucle...\n\nIII. Les Alternatives SI/SINON\nPermet de choisir entre deux actions\nselon une condition...`}
          value={courseText}
          onChange={(e) => setCourseText(e.target.value)}
        />
        {isAnalyzed && (
          <>
            <div className="sb-ok show">✓ Cours analysé avec succès</div>
            <div className="lang-badge">
              <div className="lang-dot"></div>
              Syntaxe détectée : <strong>{wizardDraft.lang === 'algo' ? 'Algorithmique' : wizardDraft.lang === 'python' ? 'Python' : 'JavaScript'}</strong>
            </div>
          </>
        )}
        <button className="analyze-btn" onClick={analyzeCourse} disabled={isLoading || step === 'DONE'}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <polyline points="9 11 12 14 22 4"/>
            <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
          </svg>
          {isLoading ? '◌ Analyse en cours...' : isAnalyzed ? '✓ Cours analysé' : 'Analyser le cours'}
        </button>
      </div>

      {/* ── ONGLET IMPORTER ── */}
      <div className="sb-body" style={{ display: activeTab === 'import' ? 'flex' : 'none', flexDirection: 'column' }}>
        <label className="upload-zone" style={{ display: 'block', opacity: isExtracting ? 0.6 : 1, pointerEvents: isExtracting ? 'none' : 'auto' }}>
          <div className="uz-icon">{isExtracting ? '◌' : '⊕'}</div>
          <div className="uz-text">{isExtracting ? 'Extraction en cours…' : 'Cliquer pour importer'}</div>
          <div className="uz-hint">PDF, Word (.docx), TXT — max 10 Mo</div>
          <input type="file" accept=".pdf,.docx,.txt" style={{ display: 'none' }} onChange={handleFileUpload} disabled={isExtracting} />
        </label>
        {extractError && (
          <div style={{ marginTop: '8px', padding: '8px 12px', background: 'var(--danger-bg)', color: 'var(--danger)', borderRadius: '8px', fontSize: '13px' }}>
            ⚠ {extractError}
          </div>
        )}
      </div>
    </aside>
  );
}

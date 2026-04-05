import React, { useState } from 'react';
import { useApp } from '../context/AppContext';

// ══════════════════════════════════════
//  SIDEBAR — Appelle le backend Python pour TOUT
//  React ne fait aucune logique d'analyse !
// ══════════════════════════════════════

const API_URL = 'https://pedabot6backend.onrender.com';

export default function Sidebar() {
  const { setStep, addMessage, wizardDraft, setWizardDraft } = useApp();
  const [activeTab, setActiveTab] = useState('saisir');
  const [courseText, setCourseText] = useState('');
  const [isAnalyzed, setIsAnalyzed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const analyzeCourse = async () => {
    if (courseText.trim().length < 20) {
      alert("△ Saisissez votre cours avant d'analyser.");
      return;
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
        courseText: courseText
      }));

      setStep('WAIT_NAME');

      addMessage({
        type: 'text',
        sender: 'bot',
        text: `✓ Cours reçu et analysé !<br><br>
               Syntaxe détectée : <code>${data.langLabel}</code><br>
               ${data.sections.length > 0 ? `<strong>${data.sections.length}</strong> grande${data.sections.length > 1 ? 's' : ''} section${data.sections.length > 1 ? 's' : ''} repérée${data.sections.length > 1 ? 's' : ''}.<br><br>` : ''}
               Quel <strong>nom</strong> voulez-vous donner à cette série d'exercices ?<br>
               <small style="color:var(--text-3)">Ex : TP Boucles — Seconde A, Consolidation Chapitre 3…</small>`,
        html: true
      });

    } catch (err) {
      console.error('Erreur analyse:', err);
      addMessage({
        type: 'text',
        sender: 'bot',
        text: `⚠️ <strong>Erreur de connexion</strong> au serveur Python.<br>
               Vérifiez que le backend tourne sur le port 8000.<br>
               <small style="color:var(--text-3)">Lancez : uvicorn main:app --reload dans le dossier backend/</small>`,
        html: true
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setCourseText(`I. Introduction — ${file.name}\nContenu extrait automatiquement depuis le fichier.\n\nII. Concepts principaux\nSection principale du cours importé.\n\nIII. Exercices et applications\nExemples pratiques et cas d'usage.`);
    setActiveTab('saisir');
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
      
      <div className="sb-body">
        <div style={{ display: activeTab === 'saisir' ? 'block' : 'none' }}>
          <textarea 
            className="course-ta" 
            placeholder={`Copiez votre cours ici...\n\nExemple :\nI. La Boucle POUR\nUtilisée quand le nombre de répétitions\nest connu à l'avance...\n\nII. La Boucle TANT QUE\nLa condition est vérifiée avant chaque\ntour de boucle...\n\nIII. Les Alternatives SI/SINON\nPermet de choisir entre deux actions\nselon une condition...`}
            value={courseText}
            onChange={(e) => setCourseText(e.target.value)}
          ></textarea>
        </div>
        
        <div style={{ display: activeTab === 'import' ? 'block' : 'none' }}>
          <label className="upload-zone" style={{ display: 'block' }}>
            <div className="uz-icon">⊕</div>
            <div className="uz-text">Cliquer pour importer</div>
            <div className="uz-hint">PDF, Word (.docx) — max 10 Mo</div>
            <input type="file" accept=".pdf,.docx,.doc,.txt" style={{ display: 'none' }} onChange={handleFileUpload} />
          </label>
        </div>

        {isAnalyzed && (
          <>
            <div className="sb-ok show">✓ Cours analysé avec succès</div>
            <div className="lang-badge">
              <div className="lang-dot"></div>
              Syntaxe détectée : <strong>{wizardDraft.lang === 'algo' ? 'Algorithmique' : wizardDraft.lang === 'python' ? 'Python' : 'JavaScript'}</strong>
            </div>
          </>
        )}

        <button className="analyze-btn" onClick={analyzeCourse} disabled={isAnalyzed || isLoading}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <polyline points="9 11 12 14 22 4"/>
            <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
          </svg>
          {isLoading ? "◌ Analyse en cours..." : isAnalyzed ? "✓ Cours analysé" : "Analyser le cours"}
        </button>
      </div>
    </aside>
  );
}

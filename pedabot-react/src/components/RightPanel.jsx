import React from 'react';
import { useApp } from '../context/AppContext';

export default function RightPanel() {
  const { wizardDraft, toggleAppro, step, messages } = useApp();

  // Stats dynamiques
  const exCount = wizardDraft.exCount || 0;
  const secCount = wizardDraft.secCount || 0;

  // Progress logic fidèle au HTML original
  let progressPct = 0;
  let progressTxt = 'En attente...';
  let tipTxt = 'Commencez par charger votre cours dans le panneau de gauche.';
  
  if (step === 'WAIT_NAME') { progressPct = 20; progressTxt = 'Nommage des exercices'; tipTxt = 'Donnez un nom clair à votre série, ex : "TP Boucles — Seconde A".'; }
  else if (step === 'WAIT_SECTIONS') { progressPct = 40; progressTxt = 'Sélection des sections'; tipTxt = 'Sélectionnez les parties sur lesquelles les élèves ont le plus besoin de consolidation.'; }
  else if (step === 'WAIT_DIFF') { progressPct = 60; progressTxt = 'Niveau de difficulté'; tipTxt = 'Le niveau "Progressif" combine reconnaissance, complétion et production autonome.'; }
  else if (step === 'WAIT_CONFIRM') { progressPct = 80; progressTxt = 'Validation'; tipTxt = 'Vérifiez le récapitulatif avant de lancer la génération.'; }
  else if (step === 'DONE') { progressPct = 100; progressTxt = 'Exercices générés'; tipTxt = 'Cliquez "Approfondir" sur un exercice pour en générer une version plus complexe.'; }

  const handleExportPDF = () => {
    // Collect exercises from messages
    const exercises = messages.filter(msg => msg.type === 'exercise').map(msg => msg.exercise);
    if (exercises.length === 0) return;

    const styles = `
      body { font-family: 'DM Sans', sans-serif; color: #0F172A; line-height: 1.6; padding: 40px; background: #fff; }
      header { text-align: center; margin-bottom: 40px; border-bottom: 2px solid #E2E8F0; padding-bottom: 20px; }
      h1 { font-family: 'Outfit', sans-serif; font-size: 28px; color: #1E52C4; margin: 0 0 10px 0; }
      .meta { font-size: 13px; color: #64748B; }
      .meta span { font-weight: 700; color: #0F172A; }
      .card { border: 1px solid #CBD5E1; border-left: 4px solid #2B6BE6; border-radius: 12px; padding: 20px; margin-bottom: 24px; page-break-inside: avoid; }
      .lvl { display: inline-block; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; padding: 4px 8px; border-radius: 5px; margin-bottom: 12px; }
      .lvl.easy { background: #DCFCE7; color: #166534; }
      .lvl.med { background: #FEF9C3; color: #713F12; }
      .lvl.hard { background: #FEE2E2; color: #991B1B; }
      .card-title { font-family: 'Outfit', sans-serif; font-size: 16px; font-weight: 700; margin-bottom: 12px; }
      .card-body { font-size: 14px; margin-bottom: 12px; }
      pre { background: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; border-radius: 8px; font-family: 'DM Mono', monospace; font-size: 13px; white-space: pre-wrap; margin: 0; }
      footer { text-align: center; font-size: 11px; color: #94A3B8; margin-top: 50px; border-top: 1px solid #E2E8F0; padding-top: 20px; }
      @media print { body { padding: 0; } }
    `;

    let body = '';
    exercises.forEach((ex) => {
      const lvlClass = ex.level === 'facile' ? 'easy' : ex.level === 'moyen' ? 'med' : 'hard';
      const lvlLabel = ex.level === 'facile' ? 'Niveau Facile' : ex.level === 'moyen' ? 'Niveau Moyen' : 'Niveau Avancé';

      body += `<div class="card">`;
      body += `<span class="lvl ${lvlClass}">${lvlLabel}</span>`;
      body += `<div class="card-title">${ex.title}</div>`;
      body += `<div class="card-body">${ex.body}</div>`;
      if (ex.code) {
        body += `<pre>${ex.code}</pre>`;
      }
      body += `</div>`;
    });

    const date = new Date().toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
    const secNames = wizardDraft.selSections && wizardDraft.selSections.length > 0 
      ? wizardDraft.selSections.map(s => s.title).join(', ') 
      : '—';

    const langLabel = wizardDraft.lang === 'algo' ? 'Algorithmique' : wizardDraft.lang === 'python' ? 'Python' : 'JavaScript';
    const diffLabel = wizardDraft.difficulty || '—';

    const html = `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>${wizardDraft.exName || 'Exercices PédaBot'}</title>
  <style>${styles}</style>
</head>
<body>
  <header>
    <h1>${wizardDraft.exName || 'Exercices générés'}</h1>
    <div class="meta">
      Généré par <span>PédaBot</span> &nbsp;·&nbsp; ${date}
      &nbsp;·&nbsp; Syntaxe&nbsp;: <span>${langLabel}</span>
      &nbsp;·&nbsp; Sections&nbsp;: <span>${secNames}</span>
      &nbsp;·&nbsp; Difficulté&nbsp;: <span>${diffLabel}</span>
    </div>
  </header>
  ${body}
  <footer>Généré automatiquement par PédaBot — Assistant de consolidation pédagogique</footer>
</body>
</html>`;

    const win = window.open('', '_blank');
    if (win) {
      win.document.write(html);
      win.document.close();
      win.focus();
      setTimeout(() => win.print(), 600);
    } else {
      alert("La fenêtre d'exportation a été bloquée par votre navigateur.");
    }
  };

  return (
    <aside className="rpanel">
      {/* Approfondissement */}
      <div>
        <div className="rp-sec-title">Mode de génération</div>
        <button className={`appro-toggle ${wizardDraft.appro ? 'on' : ''}`} onClick={toggleAppro}>
          <div className="appro-trow">
            <span className="appro-tname">Approfondissement</span>
            <div className="tpill"></div>
          </div>
          <div className="appro-tdesc">Active des exercices complexes avec cas limites et défis bonus</div>
        </button>
      </div>

      <div className="rp-divider"></div>

      {/* Stats réactives */}
      <div>
        <div className="rp-sec-title">Session en cours</div>
        <div className="stats-grid">
          <div className="stat-box">
            <div className="stat-num">{exCount}</div>
            <div className="stat-lbl">Exercices générés</div>
          </div>
          <div className="stat-box">
            <div className="stat-num">{secCount}</div>
            <div className="stat-lbl">Sections couvertes</div>
          </div>
        </div>
      </div>

      {/* Progression */}
      <div>
        <div className="rp-sec-title">Progression du wizard</div>
        <div className="prog-box">
          <div className="prog-row">
            <span>{progressTxt}</span>
            <span className="prog-pct">{progressPct}%</span>
          </div>
          <div className="prog-track">
            <div className="prog-fill" style={{ width: `${progressPct}%` }}></div>
          </div>
        </div>
      </div>

      <div className="rp-divider"></div>

      {/* Conseil */}
      <div className="tip-card">
        <div className="tip-title">★ Conseil pédagogique</div>
        <div className="tip-body">{tipTxt}</div>
      </div>

      {/* Export PDF */}
      <button className={`export-btn ${step === 'DONE' ? '' : 'hidden'}`} onClick={handleExportPDF}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        Exporter en PDF
      </button>
    </aside>
  );
}


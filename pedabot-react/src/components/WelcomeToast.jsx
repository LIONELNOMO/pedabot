import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';

export default function WelcomeToast() {
  const { user, showWelcome, dismissWelcome } = useApp();
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    if (!showWelcome) { setLeaving(false); return; }
    const leaveTimer = setTimeout(() => setLeaving(true), 3200);
    const hideTimer  = setTimeout(() => dismissWelcome(),  3700);
    return () => { clearTimeout(leaveTimer); clearTimeout(hideTimer); };
  }, [showWelcome]);

  if (!showWelcome || !user) return null;

  const prenom = user.nom ? user.nom.split(' ')[0] : 'Enseignant';
  const isNew  = user._isNew;

  return (
    <div className={`welcome-toast ${leaving ? 'welcome-toast--out' : ''}`}>
      <div className="wt-avatar">
        {prenom.substring(0, 2).toUpperCase()}
      </div>
      <div className="wt-body">
        <div className="wt-title">
          {isNew ? '🎉 Compte créé !' : '👋 Bon retour !'}&nbsp;
          <strong>Bienvenue, {prenom} !</strong>
        </div>
        <div className="wt-sub">
          {isNew
            ? 'Votre espace enseignant est prêt. Bonne création !'
            : 'Votre espace enseignant vous attend.'}
        </div>
      </div>
      <button className="wt-close" onClick={() => { setLeaving(true); setTimeout(dismissWelcome, 400); }}>
        ✕
      </button>
      <div className="wt-bar" />
    </div>
  );
}

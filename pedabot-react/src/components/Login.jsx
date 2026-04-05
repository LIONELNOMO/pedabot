import React, { useState } from 'react';
import { useApp } from '../context/AppContext';

export default function Login() {
  const { setUser } = useApp();
  const [inputValue, setInputValue] = useState('');
  const [isClosing, setIsClosing] = useState(false);

  const handleLogin = () => {
    setIsClosing(true);
    setTimeout(() => {
      setUser(inputValue.trim() || 'Professeur');
    }, 480); // Correspond au temps de transition CSS
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  return (
    <div id="pg-login" className={isClosing ? 'out' : ''}>
      <div className="login-bg-circle c1"></div>
      <div className="login-bg-circle c2"></div>
      
      <div className="lcard">
        <div className="llogo">
          <svg viewBox="0 0 24 24">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
          </svg>
        </div>
        
        <h1 className="ltitle">Péda<span>Bot</span></h1>
        <p className="lsub">
          Assistant intelligent de consolidation pédagogique<br />
          Système éducatif francophone — Afrique Centrale
        </p>

        <label className="llabel">Votre nom</label>
        <input 
          className="linput" 
          type="text" 
          placeholder="Ex : M. Kamga, Mme Ngono..." 
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        <label className="llabel">Vous êtes</label>
        <div className="role-grid">
          <div className="role-btn sel">
            <div className="role-icon">◈</div>
            <div className="role-name">Enseignant</div>
            <div className="role-desc">Créer des exercices</div>
          </div>
          <div className="role-btn dis">
            <div className="role-icon">◎</div>
            <div className="role-name">Élève</div>
            <div className="role-desc">Accéder aux TPs</div>
            <span className="soon">Bientôt</span>
          </div>
        </div>
        
        <button className="btn-cta" onClick={handleLogin}>
          Accéder à l'espace enseignant →
        </button>
      </div>
    </div>
  );
}

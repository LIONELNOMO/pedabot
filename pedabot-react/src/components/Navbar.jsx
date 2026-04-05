import React from 'react';
import { useApp } from '../context/AppContext';

export default function Navbar() {
  const { user, theme, toggleDark, step } = useApp();

  // On convertit le texte du state "step" en numéro pour l'UI (1 à 4)
  const getStepNumber = () => {
    switch(step) {
      case 'WAIT_NAME': 
      case 'WAIT_SECTIONS': return 2;
      case 'WAIT_DIFF': return 3;
      case 'WAIT_CONFIRM': 
      case 'DONE': return 4;
      default: return 1;
    }
  };

  const stepNum = getStepNumber();

  return (
    <nav className="navbar">
      <div className="nlogo">
        <svg viewBox="0 0 24 24">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
      </div>
      <span className="nbrand">Péda<b>Bot</b></span>
      <span className="nbadge">Espace Enseignant</span>
      
      <div className="nsep"></div>
      
      <div className="nstep-track">
        <div className={`nstep ${stepNum >= 1 ? (stepNum === 1 ? 'active' : 'done') : ''}`} title="Cours">1</div>
        <div className={`nstep-line ${stepNum > 1 ? 'done' : ''}`}></div>
        
        <div className={`nstep ${stepNum >= 2 ? (stepNum === 2 ? 'active' : 'done') : ''}`} title="Nom & Sections">2</div>
        <div className={`nstep-line ${stepNum > 2 ? 'done' : ''}`}></div>
        
        <div className={`nstep ${stepNum >= 3 ? (stepNum === 3 ? 'active' : 'done') : ''}`} title="Difficulté">3</div>
        <div className={`nstep-line ${stepNum > 3 ? 'done' : ''}`}></div>
        
        <div className={`nstep ${stepNum >= 4 ? (stepNum === 4 ? 'active' : 'done') : ''}`} title="Génération">4</div>
      </div>
      
      <button className="dark-toggle" onClick={toggleDark} title="Changer de thème">
        <span className="dt-icon">{theme === 'dark' ? '○' : '◑'}</span>
        <span>{theme === 'dark' ? 'Mode jour' : 'Mode nuit'}</span>
      </button>
      
      <div className="nsep"></div>
      
      <div className="nuser">
        <div className="navatar">{user.substring(0, 2).toUpperCase()}</div>
        <span className="nname">{user}</span>
      </div>
    </nav>
  );
}

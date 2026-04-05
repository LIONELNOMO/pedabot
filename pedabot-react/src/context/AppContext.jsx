import React, { createContext, useState, useContext, useEffect } from 'react';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState('');
  const [theme, setTheme] = useState(localStorage.getItem('pedabot-theme') || 'light');
  
  // Appliquer le thème au body (effet de bord React)
  useEffect(() => {
    if (theme === 'dark') {
      document.body.classList.add('dark');
    } else {
      document.body.classList.remove('dark');
    }
    localStorage.setItem('pedabot-theme', theme);
  }, [theme]);

  // État du Wizard
  const [step, setStep] = useState('IDLE'); // IDLE, WAIT_NAME, WAIT_SECTIONS, WAIT_DIFF, WAIT_CONFIRM, DONE
  
  // Rééquivalent de "S"
  const [wizardDraft, setWizardDraft] = useState({
    exName: '',
    sections: [],
    selSections: [],
    difficulty: '',
    lang: 'algo',
    appro: false
  });

  // Gérer l'approfondissement sur le body pour la variante css
  useEffect(() => {
    if (wizardDraft.appro) {
      document.body.classList.add('appro-active');
    } else {
      document.body.classList.remove('appro-active');
    }
  }, [wizardDraft.appro]);

  // Historique conversationnel
  const [messages, setMessages] = useState([]);

  // Méthodes métier simulées (Futures requêtes API Python)
  const addMessage = (msgObj) => {
    setMessages((prev) => [...prev, msgObj]);
  };

  const toggleAppro = () => {
    setWizardDraft((prev) => ({ ...prev, appro: !prev.appro }));
  };
  
  const toggleDark = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <AppContext.Provider value={{
      user, setUser,
      theme, toggleDark,
      step, setStep,
      wizardDraft, setWizardDraft,
      messages, addMessage,
      toggleAppro
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => useContext(AppContext);

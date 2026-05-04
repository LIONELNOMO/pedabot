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
    lang: 'algo'
  });

  // Historique conversationnel
  const [messages, setMessages] = useState([]);

  // Méthodes métier simulées (Futures requêtes API Python)
  const addMessage = (msgObj) => {
    setMessages((prev) => [...prev, msgObj]);
  };

  const resetSession = () => {
    setStep('IDLE');
    setMessages([]);
    setWizardDraft({ exName: '', sections: [], selSections: [], difficulty: '', lang: 'algo' });
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
      resetSession
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => useContext(AppContext);

import React, { createContext, useState, useContext, useEffect } from 'react';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [theme, setTheme] = useState(localStorage.getItem('pedabot-theme') || 'light');

  // Auth — charger depuis localStorage au démarrage
  const [user, setUser]   = useState(() => {
    try { return JSON.parse(localStorage.getItem('pedabot-user')) || null; } catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem('pedabot-token') || null);

  // Appliquer le thème
  useEffect(() => {
    document.body.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('pedabot-theme', theme);
  }, [theme]);

  // État du Wizard
  const [step, setStep] = useState('IDLE');
  const [wizardDraft, setWizardDraft] = useState({
    exName: '', sections: [], selSections: [], difficulty: '', lang: 'algo'
  });
  const [messages, setMessages] = useState([]);

  const addMessage = (msgObj) => setMessages(prev => [...prev, msgObj]);

  const resetSession = () => {
    setStep('IDLE');
    setMessages([]);
    setWizardDraft({ exName: '', sections: [], selSections: [], difficulty: '', lang: 'algo' });
  };

  const toggleDark = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');

  // Connexion — stocker user + token
  const loginUser = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem('pedabot-user', JSON.stringify(userData));
    localStorage.setItem('pedabot-token', authToken);
  };

  // Déconnexion — tout effacer
  const logoutUser = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('pedabot-user');
    localStorage.removeItem('pedabot-token');
    resetSession();
  };

  return (
    <AppContext.Provider value={{
      user, token, loginUser, logoutUser,
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

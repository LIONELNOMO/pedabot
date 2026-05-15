import React, { useState, useEffect } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import ElevePage from './components/ElevePage';
import WelcomeToast from './components/WelcomeToast';
import { useApp } from './context/AppContext';

function App() {
  const { user } = useApp();
  const [eleveToken, setEleveToken] = useState(() => {
    const h = window.location.hash;
    return h.startsWith('#eleve/') ? h.slice(7) : null;
  });

  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash;
      setEleveToken(h.startsWith('#eleve/') ? h.slice(7) : null);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  if (eleveToken) return <ElevePage token={eleveToken} />;

  return (
    <>
      {!user ? <Login /> : <Dashboard />}
      <WelcomeToast />
    </>
  );
}

export default App;

import React from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import EleveDashboard from './components/EleveDashboard';
import WelcomeToast from './components/WelcomeToast';
import { useApp } from './context/AppContext';

function App() {
  const { user } = useApp();

  if (!user) return <Login />;

  return (
    <>
      {user.role === 'eleve' ? <EleveDashboard /> : <Dashboard />}
      <WelcomeToast />
    </>
  );
}

export default App;

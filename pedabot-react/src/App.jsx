import React from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import { useApp } from './context/AppContext';

function App() {
  const { user } = useApp();

  return (
    <>
      {!user ? <Login /> : <Dashboard />}
    </>
  );
}

export default App;

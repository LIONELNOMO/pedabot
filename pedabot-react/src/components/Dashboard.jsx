import React from 'react';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';
import RightPanel from './RightPanel';

export default function Dashboard() {
  return (
    <div id="pg-app" className="show">
      <Navbar />
      <div className="app-body">
        <Sidebar />
        <ChatArea />
        <RightPanel />
      </div>
    </div>
  );
}

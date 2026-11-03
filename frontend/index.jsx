import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './components/HomePage';
import AdminDashboard from './components/AdminDashboard';
import BrokerApp from './components/broker/BrokerApp';
import './components/HomePage.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
const brokerPanelEnabled = import.meta.env.VITE_BROKER_PANEL_ENABLED === 'true';
root.render(
  <React.StrictMode>
    <Router>
      <Routes>
        <Route path="/admin" element={<AdminDashboard />} />
        {brokerPanelEnabled && <Route path="/broker/*" element={<BrokerApp />} />}
        <Route path="/*" element={<HomePage />} />
      </Routes>
    </Router>
  </React.StrictMode>
);

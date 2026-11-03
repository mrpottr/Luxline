import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './components/HomePage';
import AdminDashboard from './components/AdminDashboard';
import { BrokerApp, BuyerReviewScreen, isBrokerPanelEnabled } from './components/broker';
import './components/HomePage.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
const brokerPanelEnabled = isBrokerPanelEnabled(import.meta.env.VITE_BROKER_PANEL_ENABLED);
root.render(
  <React.StrictMode>
    <Router>
      <Routes>
        <Route path="/admin" element={<AdminDashboard />} />
        {brokerPanelEnabled && <Route path="/broker/*" element={<BrokerApp />} />}
        {brokerPanelEnabled && <Route path="/buyer/reviews" element={<BuyerReviewScreen />} />}
        <Route path="/*" element={<HomePage />} />
      </Routes>
    </Router>
  </React.StrictMode>
);

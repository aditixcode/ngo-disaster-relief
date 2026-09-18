import React from 'react';
import {
  ExternalLink,
  Activity,
  LogOut,
  RefreshCw,
  SlidersHorizontal,
} from 'lucide-react';

export default function Header({
  activeTabTitle,
  isLiveMode,
  setIsLiveMode,
  apiOnline,
  onRefresh,
  onLogout,
}) {
  const API_DOCS_URL = 'https://ngo-disaster-relief-gwgp87qqh-aditi-2a39.vercel.app/docs';

  return (
    <header className="top-header">
      <div className="header-left">
        <h1 className="header-page-title">
          NGO Disaster Relief Dashboard
          <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-muted)', marginLeft: '10px' }}>
            / {activeTabTitle}
          </span>
        </h1>

        <div className={`status-pill ${apiOnline && isLiveMode ? 'online' : 'demo'}`}>
          <span className="status-dot"></span>
          <span>
            {apiOnline && isLiveMode ? 'API Connected (Live)' : 'Presentation Mode (Demo Data)'}
          </span>
        </div>
      </div>

      <div className="header-right">
        {/* Toggle Live vs Presentation Data */}
        <button
          className="mode-toggle-btn"
          onClick={() => setIsLiveMode(!isLiveMode)}
          title="Switch between Live FastAPI backend data and high-fidelity presentation demo data"
        >
          <SlidersHorizontal size={14} />
          <span>{isLiveMode ? 'Switch to Demo Data' : 'Try Live API'}</span>
        </button>

        {/* Refresh API Data */}
        <button
          className="mode-toggle-btn"
          onClick={onRefresh}
          title="Refresh data from server"
        >
          <RefreshCw size={14} />
        </button>

        {/* API Documentation Button required by user */}
        <a
          href={API_DOCS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="doc-btn"
          title="Open interactive FastAPI Swagger documentation on Vercel"
        >
          <ExternalLink size={15} />
          <span>Open API Documentation</span>
        </a>

        {/* User Profile */}
        <div className="user-profile">
          <div className="user-avatar">AR</div>
          <div className="user-info">
            <span className="user-name">Dr. Aisha Rahman</span>
            <span className="user-role">Operations Commander (ADMIN)</span>
          </div>
        </div>

        {/* Logout */}
        <button
          className="logout-btn"
          onClick={onLogout}
          title="Sign out of relief console"
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}

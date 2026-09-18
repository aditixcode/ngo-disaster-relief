import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import OverviewSection from './components/OverviewSection';
import DisastersSection from './components/DisastersSection';
import InventorySection from './components/InventorySection';
import VolunteersSection from './components/VolunteersSection';
import BeneficiariesSection from './components/BeneficiariesSection';
import DistributionCentersSection from './components/DistributionCentersSection';
import DistributionSection from './components/DistributionSection';
import DonationsSection from './components/DonationsSection';
import ReportsSection from './components/ReportsSection';

import {
  initialDisasters,
  initialInventory,
  initialVolunteers,
  initialBeneficiaries,
  initialCenters,
  initialDistributions,
  initialDonations,
} from './data/demoData';

import { apiClient } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isLiveMode, setIsLiveMode] = useState(false); // default to reliable presentation demo mode
  const [apiOnline, setApiOnline] = useState(false);
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  // Core domain states
  const [disasters, setDisasters] = useState(initialDisasters);
  const [inventory, setInventory] = useState(initialInventory);
  const [volunteers, setVolunteers] = useState(initialVolunteers);
  const [beneficiaries, setBeneficiaries] = useState(initialBeneficiaries);
  const [centers, setCenters] = useState(initialCenters);
  const [distributions, setDistributions] = useState(initialDistributions);
  const [donations, setDonations] = useState(initialDonations);

  // Check health on mount and periodically
  const checkBackendHealth = async () => {
    const health = await apiClient.checkHealth();
    setApiOnline(health.online);

    if (isLiveMode && health.online) {
      // Attempt live fetch
      const d = await apiClient.getDisasters();
      if (d.isLive) setDisasters(d.data);

      const inv = await apiClient.getInventory();
      if (inv.isLive) setInventory(inv.data);

      const ben = await apiClient.getBeneficiaries();
      if (ben.isLive) setBeneficiaries(ben.data);

      const c = await apiClient.getDistributionCenters();
      if (c.isLive) setCenters(c.data);

      const dist = await apiClient.getDistributions();
      if (dist.isLive) setDistributions(dist.data);
    } else if (!isLiveMode) {
      // Restore rich presentation data
      setDisasters(initialDisasters);
      setInventory(initialInventory);
      setVolunteers(initialVolunteers);
      setBeneficiaries(initialBeneficiaries);
      setCenters(initialCenters);
      setDistributions(initialDistributions);
      setDonations(initialDonations);
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, [isLiveMode]);

  // Tab titles map
  const tabTitles = {
    dashboard: 'Operations Command Center',
    disasters: 'Disaster Relief Management',
    volunteers: 'Volunteer Force & Task Assignments',
    donations: 'Donations & Pledges Ledger',
    inventory: 'Relief Inventory & Warehouse Staging',
    beneficiaries: 'Beneficiary Registration & Eligibility',
    centers: 'Distribution Centers & Logistics Hubs',
    distribution: 'Resource Distribution Tracking',
    reports: 'Summary & Operational Analytics',
  };

  const counts = {
    disasters: `${disasters.filter((d) => d.status === 'ACTIVE').length} Active`,
    volunteers: `${volunteers.length}`,
    donations: `$184k`,
    inventory: `${inventory.length} Batches`,
    beneficiaries: `${beneficiaries.length}`,
    centers: `${centers.length} Hubs`,
    distributions: `${distributions.length}`,
  };

  return (
    <div className="app-container">
      {/* 1. Left Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        counts={counts}
      />

      {/* 2. Main Content Wrapper */}
      <div className="main-wrapper">
        {/* Top Header */}
        <Header
          activeTabTitle={tabTitles[activeTab] || 'Dashboard'}
          isLiveMode={isLiveMode}
          setIsLiveMode={setIsLiveMode}
          apiOnline={apiOnline}
          onRefresh={checkBackendHealth}
          onLogout={() => setShowLogoutModal(true)}
        />

        {/* Dynamic Section Render */}
        <main className="content-body">
          {activeTab === 'dashboard' && (
            <OverviewSection
              disasters={disasters}
              inventory={inventory}
              volunteers={volunteers}
              beneficiaries={beneficiaries}
              donations={donations}
              centers={centers}
              distributions={distributions}
              onNavigate={(tab) => setActiveTab(tab)}
            />
          )}

          {activeTab === 'disasters' && (
            <DisastersSection disasters={disasters} />
          )}

          {activeTab === 'volunteers' && (
            <VolunteersSection volunteers={volunteers} />
          )}

          {activeTab === 'donations' && (
            <DonationsSection donations={donations} />
          )}

          {activeTab === 'inventory' && (
            <InventorySection inventory={inventory} />
          )}

          {activeTab === 'beneficiaries' && (
            <BeneficiariesSection beneficiaries={beneficiaries} />
          )}

          {activeTab === 'centers' && (
            <DistributionCentersSection centers={centers} />
          )}

          {activeTab === 'distribution' && (
            <DistributionSection distributions={distributions} />
          )}

          {activeTab === 'reports' && (
            <ReportsSection
              disasters={disasters}
              inventory={inventory}
              volunteers={volunteers}
              distributions={distributions}
              donations={donations}
            />
          )}
        </main>
      </div>

      {/* Logout Confirmation Modal */}
      {showLogoutModal && (
        <div className="modal-backdrop" onClick={() => setShowLogoutModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Sign Out of Relief Operations</h3>
            </div>
            <div className="modal-body">
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                Are you sure you want to end your active command session as{' '}
                <strong>Dr. Aisha Rahman (ADMIN)</strong>?
              </p>
              <div
                style={{
                  marginTop: '14px',
                  padding: '12px',
                  borderRadius: '8px',
                  background: '#f8fafc',
                  border: '1px solid var(--border-color)',
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                }}
              >
                ℹ️ To authenticate or test JWT role tokens, use the interactive{' '}
                <a
                  href="https://ngo-disaster-relief-gwgp87qqh-aditi-2a39.vercel.app/docs"
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: 'var(--primary)', fontWeight: '600' }}
                >
                  Swagger UI Authorize
                </a>{' '}
                button.
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => setShowLogoutModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                style={{ backgroundColor: 'var(--danger)' }}
                onClick={() => {
                  setShowLogoutModal(false);
                  alert('You have logged out. Reloading presentation view.');
                }}
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import React from 'react';
import {
  LayoutDashboard,
  Flame,
  Users2,
  HeartHandshake,
  Warehouse,
  UserCheck,
  Building2,
  Truck,
  BarChart3,
  ShieldCheck,
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, counts }) {
  const navItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: LayoutDashboard,
      badge: 'Live',
    },
    {
      id: 'disasters',
      label: 'Disasters',
      icon: Flame,
      badge: counts.disasters || '3 Active',
    },
    {
      id: 'volunteers',
      label: 'Volunteers',
      icon: Users2,
      badge: counts.volunteers || '142',
    },
    {
      id: 'donations',
      label: 'Donations',
      icon: HeartHandshake,
      badge: counts.donations || '$184k',
    },
    {
      id: 'inventory',
      label: 'Relief Inventory',
      icon: Warehouse,
      badge: counts.inventory || '7 Batches',
    },
    {
      id: 'beneficiaries',
      label: 'Beneficiaries',
      icon: UserCheck,
      badge: counts.beneficiaries || '3.8k',
    },
    {
      id: 'centers',
      label: 'Distribution Centers',
      icon: Building2,
      badge: counts.centers || '5 Hubs',
    },
    {
      id: 'distribution',
      label: 'Resource Distribution',
      icon: Truck,
      badge: counts.distributions || 'Active',
    },
    {
      id: 'reports',
      label: 'Reports & Analytics',
      icon: BarChart3,
      badge: 'Aggregated',
    },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-badge">
          <div className="brand-icon">
            <ShieldCheck size={24} />
          </div>
          <div>
            <div className="brand-title">ReliefOps Core</div>
            <div className="brand-subtitle">NGO Disaster Management</div>
          </div>
        </div>
      </div>

      <div className="nav-section">
        <div className="nav-category">Command Modules</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.badge && <span className="nav-badge">{item.badge}</span>}
            </button>
          );
        })}
      </div>

      <div className="sidebar-footer">
        <div className="system-card">
          <div className="system-card-title">Database Engine</div>
          <div className="system-card-desc">PostgreSQL / Neon DB</div>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
            FastAPI REST Backend v1.0
          </div>
        </div>
      </div>
    </aside>
  );
}

import React from 'react';
import {
  Flame,
  Users,
  UserCheck,
  Package,
  HeartHandshake,
  Building2,
  TrendingUp,
  AlertCircle,
  ArrowRight,
  Truck,
  Layers,
} from 'lucide-react';

export default function OverviewSection({
  disasters,
  inventory,
  volunteers,
  beneficiaries,
  donations,
  centers,
  distributions,
  onNavigate,
}) {
  // Compute key KPI metrics
  const activeDisastersCount = disasters.filter((d) => d.status === 'ACTIVE').length;
  const activeVolunteersCount = volunteers.filter((v) => v.assignment_status === 'ACTIVE').length;
  const verifiedBeneficiariesCount = beneficiaries.filter((b) => b.registration_status === 'VERIFIED').length;
  const storedInventoryUnits = inventory
    .filter((i) => i.status === 'STORED')
    .reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);
  
  const totalMonetaryDonations = donations
    .filter((d) => d.donation_type === 'MONEY' && d.status !== 'CANCELLED')
    .reduce((sum, d) => sum + (Number(d.amount) || 0), 0);

  const activeCentersCount = centers.filter((c) => c.status === 'ACTIVE').length;

  return (
    <div>
      {/* Urgent Operational Incident Alert */}
      <div className="alert-banner">
        <div className="alert-banner-left">
          <div className="alert-icon">
            <AlertCircle size={24} />
          </div>
          <div>
            <div className="alert-heading">
              CRITICAL NOTICE: Cyclone Vardah Relief - Sector 4 Priority Dispatch Active
            </div>
            <div className="alert-subtext">
              High-priority water and medical kit requests dispatched to Marina Staging Depot. 12 volunteer units deployed.
            </div>
          </div>
        </div>
        <button
          className="btn-primary"
          onClick={() => onNavigate('distribution')}
          style={{ padding: '8px 14px', fontSize: '12px' }}
        >
          <span>View Dispatches</span>
          <ArrowRight size={14} />
        </button>
      </div>

      {/* Overview 6 KPI Cards (As required by prompt) */}
      <div className="kpi-grid">
        {/* 1. Active Disasters */}
        <div className="kpi-card" onClick={() => onNavigate('disasters')} style={{ cursor: 'pointer' }}>
          <div className="kpi-header">
            <span className="kpi-title">Active Disasters</span>
            <div className="kpi-icon-wrapper" style={{ background: '#fee2e2', color: '#dc2626' }}>
              <Flame size={20} />
            </div>
          </div>
          <div className="kpi-value">{activeDisastersCount}</div>
          <div className="kpi-meta">
            <TrendingUp size={13} style={{ color: '#dc2626' }} />
            <span>{disasters.length} total recorded operations</span>
          </div>
        </div>

        {/* 2. Registered Volunteers */}
        <div className="kpi-card" onClick={() => onNavigate('volunteers')} style={{ cursor: 'pointer' }}>
          <div className="kpi-header">
            <span className="kpi-title">Volunteers</span>
            <div className="kpi-icon-wrapper" style={{ background: '#e0e7ff', color: '#4338ca' }}>
              <Users size={20} />
            </div>
          </div>
          <div className="kpi-value">{volunteers.length}</div>
          <div className="kpi-meta">
            <span style={{ color: '#059669', fontWeight: '600' }}>{activeVolunteersCount}</span> deployed on active tasks
          </div>
        </div>

        {/* 3. Total Beneficiaries */}
        <div className="kpi-card" onClick={() => onNavigate('beneficiaries')} style={{ cursor: 'pointer' }}>
          <div className="kpi-header">
            <span className="kpi-title">Beneficiaries</span>
            <div className="kpi-icon-wrapper" style={{ background: '#ecfdf5', color: '#059669' }}>
              <UserCheck size={20} />
            </div>
          </div>
          <div className="kpi-value">{beneficiaries.length}</div>
          <div className="kpi-meta">
            <span style={{ color: '#059669', fontWeight: '600' }}>{verifiedBeneficiariesCount}</span> verified & eligible for aid
          </div>
        </div>

        {/* 4. Available Inventory */}
        <div className="kpi-card" onClick={() => onNavigate('inventory')} style={{ cursor: 'pointer' }}>
          <div className="kpi-header">
            <span className="kpi-title">Available Inventory</span>
            <div className="kpi-icon-wrapper" style={{ background: '#eff6ff', color: '#2563eb' }}>
              <Package size={20} />
            </div>
          </div>
          <div className="kpi-value">
            {storedInventoryUnits.toLocaleString()} <span style={{ fontSize: '15px', fontWeight: '500' }}>units</span>
          </div>
          <div className="kpi-meta">
            <span>STORED status across {inventory.length} warehouse batches</span>
          </div>
        </div>

        {/* 5. Total Donations */}
        <div className="kpi-card" onClick={() => onNavigate('donations')} style={{ cursor: 'pointer' }}>
          <div className="kpi-header">
            <span className="kpi-title">Total Donations</span>
            <div className="kpi-icon-wrapper" style={{ background: '#fdf4ff', color: '#a21caf' }}>
              <HeartHandshake size={20} />
            </div>
          </div>
          <div className="kpi-value">
            ${totalMonetaryDonations.toLocaleString()}
          </div>
          <div className="kpi-meta">
            <span>+ {donations.filter(d => d.donation_type === 'MATERIAL').length} material pledges</span>
          </div>
        </div>

        {/* 6. Distribution Centers */}
        <div className="kpi-card" onClick={() => onNavigate('centers')} style={{ cursor: 'pointer' }}>
          <div className="kpi-header">
            <span className="kpi-title">Distribution Hubs</span>
            <div className="kpi-icon-wrapper" style={{ background: '#fef3c7', color: '#d97706' }}>
              <Building2 size={20} />
            </div>
          </div>
          <div className="kpi-value">{centers.length}</div>
          <div className="kpi-meta">
            <span style={{ color: '#059669', fontWeight: '600' }}>{activeCentersCount} Active</span>, {centers.filter(c => c.status === 'FULL').length} at capacity
          </div>
        </div>
      </div>

      {/* Grid: Active Operations Quick View & Recent Field Dispatches */}
      <div className="grid-2">
        {/* Active Disasters Preview Card */}
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <Flame size={18} style={{ color: 'var(--primary)' }} />
              <h3 className="card-title">Priority Emergency Operations</h3>
            </div>
            <button className="btn-secondary" onClick={() => onNavigate('disasters')} style={{ fontSize: '12px', padding: '5px 10px' }}>
              View All
            </button>
          </div>
          <div className="card-body" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {disasters.slice(0, 3).map((d) => (
                <div
                  key={d.id}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    background: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '14px', color: 'var(--text-primary)' }}>
                      {d.name}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      📍 {d.location}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className={`badge badge-${d.status.toLowerCase()}`}>
                      {d.status}
                    </span>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Since {new Date(d.start_date).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Live Warehouse Intake & Storage Preview */}
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <Layers size={18} style={{ color: 'var(--primary)' }} />
              <h3 className="card-title">Warehouse Stock Health</h3>
            </div>
            <button className="btn-secondary" onClick={() => onNavigate('inventory')} style={{ fontSize: '12px', padding: '5px 10px' }}>
              View Inventory
            </button>
          </div>
          <div className="card-body" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {inventory.slice(0, 4).map((item) => {
                const pct = Math.min(100, Math.round((item.quantity / item.original_quantity) * 100));
                return (
                  <div key={item.id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: '600', marginBottom: '5px' }}>
                      <span>{item.item_name}</span>
                      <span style={{ color: 'var(--text-secondary)' }}>
                        {item.quantity.toLocaleString()} / {item.original_quantity.toLocaleString()} {item.unit} ({pct}% remaining)
                      </span>
                    </div>
                    <div className="progress-bar-bg">
                      <div
                        className="progress-bar-fill"
                        style={{
                          width: `${pct}%`,
                          background: pct < 20 ? 'var(--danger)' : pct < 50 ? 'var(--warning)' : 'var(--primary)',
                        }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

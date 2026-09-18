import React, { useState } from 'react';
import {
  Building2,
  Search,
  MapPin,
  Clock,
  Phone,
  CheckCircle2,
  AlertOctagon,
  XCircle,
} from 'lucide-react';

export default function DistributionCentersSection({ centers }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filtered = centers.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.address.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.disaster_name && c.disaster_name.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title-group">
          <Building2 size={20} style={{ color: '#d97706' }} />
          <h2 className="card-title">Distribution Centers & Logistics Hubs</h2>
          <span className="card-badge">{filtered.length} Staging Hubs</span>
        </div>
      </div>

      <div className="card-body">
        {/* Search and Filters */}
        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by center name, address or disaster..."
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-pills">
            {['ALL', 'ACTIVE', 'FULL', 'INACTIVE'].map((st) => (
              <button
                key={st}
                className={`filter-btn ${statusFilter === st ? 'active' : ''}`}
                onClick={() => setStatusFilter(st)}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Center Cards Grid */}
        <div className="grid-2">
          {filtered.map((center) => {
            const cap = center.capacity || 500;
            const current = center.current_throughput || 0;
            const utilPct = Math.min(100, Math.round((current / cap) * 100));

            let statusColor = '#059669';
            let statusBg = '#ecfdf5';
            let statusBorder = '#a7f3d0';

            if (center.status === 'FULL') {
              statusColor = '#d97706';
              statusBg = '#fffbeb';
              statusBorder = '#fde68a';
            } else if (center.status === 'INACTIVE') {
              statusColor = '#dc2626';
              statusBg = '#fef2f2';
              statusBorder = '#fecaca';
            }

            return (
              <div
                key={center.id}
                style={{
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  padding: '20px',
                  backgroundColor: '#ffffff',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>
                      {center.name}
                    </h3>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Operation: <span style={{ fontWeight: '600', color: 'var(--text-secondary)' }}>{center.disaster_name || `Disaster #${center.disaster_id}`}</span>
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: '11.5px',
                      fontWeight: '700',
                      padding: '3px 10px',
                      borderRadius: '9999px',
                      color: statusColor,
                      backgroundColor: statusBg,
                      border: `1px solid ${statusBorder}`,
                    }}
                  >
                    {center.status}
                  </span>
                </div>

                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                    <MapPin size={14} style={{ color: 'var(--primary)' }} />
                    <span>{center.address}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                    <Clock size={14} style={{ color: 'var(--text-muted)' }} />
                    <span>{center.operating_hours || '07:00 - 19:00 Daily'}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Phone size={14} style={{ color: 'var(--text-muted)' }} />
                    <span>{center.contact_number || '+91-44-2345-0000'}</span>
                  </div>
                </div>

                {/* Capacity Meter */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', marginBottom: '5px' }}>
                    <span>Capacity Processing:</span>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {current} / {cap} households ({utilPct}%)
                    </span>
                  </div>
                  <div className="progress-bar-bg">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${utilPct}%`,
                        background: utilPct >= 100 ? 'var(--warning)' : 'var(--primary)',
                      }}
                    ></div>
                  </div>
                </div>

                <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                  {center.status === 'ACTIVE' && (
                    <span style={{ color: '#059669', fontWeight: '600' }}>
                      ✓ Hub is operational and eligible for relief dispatches.
                    </span>
                  )}
                  {center.status === 'FULL' && (
                    <span style={{ color: '#d97706', fontWeight: '600' }}>
                      ⚠ Throughput capacity reached. New dispatches rerouted.
                    </span>
                  )}
                  {center.status === 'INACTIVE' && (
                    <span style={{ color: '#dc2626', fontWeight: '600' }}>
                      ✕ Facility closed / offline. Distributions blocked.
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

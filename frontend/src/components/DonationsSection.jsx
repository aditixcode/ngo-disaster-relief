import React, { useState } from 'react';
import {
  HeartHandshake,
  Search,
  DollarSign,
  Package,
  Calendar,
  CheckCircle,
  Clock,
} from 'lucide-react';

export default function DonationsSection({ donations }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');

  const filtered = donations.filter((d) => {
    const matchesSearch =
      d.donor_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.item_name && d.item_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (d.disaster_name && d.disaster_name.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesType = typeFilter === 'ALL' || d.donation_type === typeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title-group">
          <HeartHandshake size={20} style={{ color: '#a21caf' }} />
          <h2 className="card-title">Donations & Contributions Ledger</h2>
          <span className="card-badge">{filtered.length} Contributions</span>
        </div>
      </div>

      <div className="card-body">
        {/* Search and Filters */}
        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by donor name, commodity, disaster..."
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-pills">
            {['ALL', 'MONEY', 'MATERIAL'].map((t) => (
              <button
                key={t}
                className={`filter-btn ${typeFilter === t ? 'active' : ''}`}
                onClick={() => setTypeFilter(t)}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Tabular View */}
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Donor Name</th>
                <th>Donation Type</th>
                <th>Contribution Details</th>
                <th>Target Disaster</th>
                <th>Status</th>
                <th>Pledged / Received Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => {
                const isMoney = d.donation_type === 'MONEY';
                return (
                  <tr key={d.id}>
                    <td style={{ fontWeight: '600' }}>#{d.id}</td>
                    <td className="table-primary-text">{d.donor_name}</td>
                    <td>
                      <span
                        style={{
                          fontSize: '11.5px',
                          fontWeight: '700',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          backgroundColor: isMoney ? '#eff6ff' : '#fdf4ff',
                          color: isMoney ? '#1d4ed8' : '#86198f',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        {isMoney ? <DollarSign size={12} /> : <Package size={12} />}
                        {d.donation_type}
                      </span>
                    </td>
                    <td style={{ fontWeight: '700', fontSize: '13.5px', color: isMoney ? '#059669' : 'var(--text-primary)' }}>
                      {isMoney
                        ? `$${Number(d.amount).toLocaleString()}`
                        : `${d.quantity.toLocaleString()} ${d.unit} of ${d.item_name}`}
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>
                      {d.disaster_name}
                    </td>
                    <td>
                      <span className={`badge ${d.status === 'RECEIVED' ? 'badge-active' : 'badge-pending'}`}>
                        {d.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {new Date(d.date).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            No donations match your query.
          </div>
        )}
      </div>
    </div>
  );
}

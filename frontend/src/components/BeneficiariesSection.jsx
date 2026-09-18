import React, { useState } from 'react';
import {
  UserCheck,
  Search,
  MapPin,
  Heart,
  ShieldAlert,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react';

export default function BeneficiariesSection({ beneficiaries }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [vulnerabilityFilter, setVulnerabilityFilter] = useState('ALL');

  const categories = ['ALL', 'LOW_INCOME', 'ELDERLY', 'CHILDREN', 'PREGNANT', 'DISABLED'];

  const filtered = beneficiaries.filter((b) => {
    const matchesSearch =
      b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      b.address.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (b.required_resources && b.required_resources.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus = statusFilter === 'ALL' || b.registration_status === statusFilter;
    const matchesVuln = vulnerabilityFilter === 'ALL' || b.vulnerability_category === vulnerabilityFilter;

    return matchesSearch && matchesStatus && matchesVuln;
  });

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title-group">
          <UserCheck size={20} style={{ color: 'var(--success)' }} />
          <h2 className="card-title">Beneficiaries Registration & Verification</h2>
          <span className="card-badge">{filtered.length} Households</span>
        </div>
      </div>

      <div className="card-body">
        {/* Search & Filter Controls */}
        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by beneficiary name, address, or requested aid..."
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-pills">
            {['ALL', 'VERIFIED', 'PENDING', 'INACTIVE'].map((st) => (
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

        {/* Vulnerability Category Pills */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
          {categories.map((vuln) => (
            <button
              key={vuln}
              className={`filter-btn ${vulnerabilityFilter === vuln ? 'active' : ''}`}
              style={{ fontSize: '12px', padding: '5px 12px' }}
              onClick={() => setVulnerabilityFilter(vuln)}
            >
              {vuln.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Table View */}
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Beneficiary / Household</th>
                <th>Location / Camp</th>
                <th>Household Size</th>
                <th>Vulnerability Category</th>
                <th>Verification Status</th>
                <th>Eligibility for Relief</th>
                <th>Required Aid</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((b) => {
                let statusBadge = 'badge-verified';
                if (b.registration_status === 'VERIFIED') statusBadge = 'badge-active';
                if (b.registration_status === 'PENDING') statusBadge = 'badge-pending';
                if (b.registration_status === 'INACTIVE') statusBadge = 'badge-resolved';

                return (
                  <tr key={b.id}>
                    <td style={{ fontWeight: '600' }}>#{b.id}</td>
                    <td className="table-primary-text">
                      <div>{b.name}</div>
                      <div className="table-sub-text">📞 {b.contact_number}</div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <MapPin size={13} style={{ color: 'var(--text-muted)' }} />
                        <span>{b.address}</span>
                      </div>
                    </td>
                    <td style={{ fontWeight: '600', textAlign: 'center' }}>
                      {b.household_size} members
                    </td>
                    <td>
                      <span style={{ fontSize: '11.5px', fontWeight: '600', padding: '3px 8px', borderRadius: '6px', background: '#fef3c7', color: '#92400e' }}>
                        {b.vulnerability_category.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${statusBadge}`}>
                        {b.registration_status}
                      </span>
                    </td>
                    <td>
                      {b.registration_status === 'VERIFIED' ? (
                        <span style={{ color: '#059669', fontWeight: '600', fontSize: '12.5px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle size={14} /> Eligible for Aid
                        </span>
                      ) : (
                        <span style={{ color: '#94a3b8', fontSize: '12.5px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Clock size={14} /> Gated (Unverified)
                        </span>
                      )}
                    </td>
                    <td style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                      {b.required_resources || 'Standard Emergency Kit'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            No beneficiary records match the current criteria.
          </div>
        )}
      </div>
    </div>
  );
}

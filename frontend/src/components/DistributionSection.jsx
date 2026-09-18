import React, { useState } from 'react';
import {
  Truck,
  Search,
  CheckCircle2,
  Calendar,
  Building,
  User,
  ShieldCheck,
} from 'lucide-react';

export default function DistributionSection({ distributions }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = distributions.filter((d) => {
    return (
      d.item_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.beneficiary_name && d.beneficiary_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (d.center_name && d.center_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (d.distributed_by && d.distributed_by.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  });

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title-group">
          <Truck size={20} style={{ color: 'var(--primary)' }} />
          <h2 className="card-title">Resource Distribution Ledger (Stage 10 Audit)</h2>
          <span className="card-badge">{filtered.length} Dispatches</span>
        </div>
      </div>

      <div className="card-body">
        {/* Search */}
        <div className="filter-bar">
          <div className="search-input-wrap" style={{ maxWidth: '480px' }}>
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by relief item, recipient, hub or authorized officer..."
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            🔒 Immutable Audit Trail (Pessimistic Row Lock & Transaction Wrapped)
          </div>
        </div>

        {/* Tabular Distribution Ledger */}
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Dispatch ID</th>
                <th>Resource Distributed</th>
                <th>Quantity</th>
                <th>Recipient Beneficiary</th>
                <th>Staging Depot Hub</th>
                <th>Authorized By</th>
                <th>Timestamp (UTC)</th>
                <th>Audit Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                    #DIS-{item.id}
                  </td>
                  <td className="table-primary-text">
                    {item.item_name}
                  </td>
                  <td style={{ fontWeight: '700', color: 'var(--primary)' }}>
                    {item.quantity} {item.unit}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <User size={13} style={{ color: 'var(--text-muted)' }} />
                      <span style={{ fontWeight: '500' }}>{item.beneficiary_name}</span>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <Building size={13} style={{ color: 'var(--text-muted)' }} />
                      <span>{item.center_name}</span>
                    </div>
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {item.distributed_by}
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {new Date(item.distributed_at).toLocaleString()}
                  </td>
                  <td>
                    <span className="badge badge-active">
                      <ShieldCheck size={12} />
                      <span>VERIFIED</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            No distribution transactions match your search.
          </div>
        )}
      </div>
    </div>
  );
}

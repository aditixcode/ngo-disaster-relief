import React, { useState } from 'react';
import {
  Flame,
  Search,
  MapPin,
  Calendar,
  AlertTriangle,
  Users,
  Building,
  Plus,
} from 'lucide-react';

export default function DisastersSection({ disasters, onAddDisaster }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [viewMode, setViewMode] = useState('cards'); // 'cards' | 'table'

  const filtered = disasters.filter((d) => {
    const matchesSearch =
      d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.description && d.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = statusFilter === 'ALL' || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title-group">
          <Flame size={20} style={{ color: '#dc2626' }} />
          <h2 className="card-title">Disasters & Relief Operations</h2>
          <span className="card-badge">{filtered.length} Recorded</span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn-secondary ${viewMode === 'cards' ? 'active' : ''}`}
            onClick={() => setViewMode('cards')}
            style={{ fontSize: '12px', padding: '6px 12px' }}
          >
            Card Grid
          </button>
          <button
            className={`btn-secondary ${viewMode === 'table' ? 'active' : ''}`}
            onClick={() => setViewMode('table')}
            style={{ fontSize: '12px', padding: '6px 12px' }}
          >
            Tabular View
          </button>
        </div>
      </div>

      <div className="card-body">
        {/* Search & Filter Controls */}
        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by disaster name, location or keyword..."
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-pills">
            {['ALL', 'ACTIVE', 'CONTAINED', 'RESOLVED'].map((st) => (
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

        {/* View Mode: Cards */}
        {viewMode === 'cards' && (
          <div className="grid-2">
            {filtered.map((disaster) => (
              <div key={disaster.id} className="disaster-card">
                <div className="disaster-card-top">
                  <div>
                    <h3 className="disaster-name">{disaster.name}</h3>
                    <div className="disaster-location" style={{ marginTop: '4px' }}>
                      <MapPin size={14} style={{ color: 'var(--primary)' }} />
                      <span>{disaster.location}</span>
                    </div>
                  </div>
                  <span className={`badge badge-${disaster.status.toLowerCase()}`}>
                    {disaster.status}
                  </span>
                </div>

                <p className="disaster-desc">{disaster.description}</p>

                <div className="disaster-meta-footer">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <Calendar size={13} />
                    <span>Commenced: {new Date(disaster.start_date).toLocaleDateString()}</span>
                  </div>
                  {disaster.end_date && (
                    <div style={{ fontSize: '11px', color: '#64748b' }}>
                      Resolved: {new Date(disaster.end_date).toLocaleDateString()}
                    </div>
                  )}
                  {disaster.affected_population && (
                    <div style={{ fontWeight: '600', color: 'var(--text-secondary)' }}>
                      👥 {disaster.affected_population} affected
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* View Mode: Table */}
        {viewMode === 'table' && (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Disaster Name</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Start Date</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: '600' }}>#{d.id}</td>
                    <td className="table-primary-text">{d.name}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <MapPin size={13} style={{ color: 'var(--text-muted)' }} />
                        <span>{d.location}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-${d.status.toLowerCase()}`}>
                        {d.status}
                      </span>
                    </td>
                    <td>{new Date(d.start_date).toLocaleDateString()}</td>
                    <td style={{ maxWidth: '320px', whiteSpace: 'normal', fontSize: '12.5px' }}>
                      {d.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            No disasters match your current search or status filter.
          </div>
        )}
      </div>
    </div>
  );
}

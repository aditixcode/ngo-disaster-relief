import React, { useState } from 'react';
import {
  Users2,
  Search,
  CheckCircle,
  Clock,
  Briefcase,
  Flame,
  Shield,
} from 'lucide-react';

export default function VolunteersSection({ volunteers }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [taskFilter, setTaskFilter] = useState('ALL');

  const filtered = volunteers.filter((v) => {
    const matchesSearch =
      v.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.task_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.disaster_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (v.skills && v.skills.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesTask = taskFilter === 'ALL' || v.task_status === taskFilter;
    return matchesSearch && matchesTask;
  });

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title-group">
          <Users2 size={20} style={{ color: '#4338ca' }} />
          <h2 className="card-title">Volunteer Deployment & Task Tracking</h2>
          <span className="card-badge">{filtered.length} Volunteers Active</span>
        </div>
      </div>

      <div className="card-body">
        {/* Search & Status Filters */}
        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by volunteer name, task, disaster, or skills..."
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-pills">
            {['ALL', 'IN_PROGRESS', 'COMPLETED', 'PENDING'].map((st) => (
              <button
                key={st}
                className={`filter-btn ${taskFilter === st ? 'active' : ''}`}
                onClick={() => setTaskFilter(st)}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Volunteers Table */}
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Volunteer</th>
                <th>Assigned Disaster</th>
                <th>Current Task Assignment</th>
                <th>Task Lifecycle</th>
                <th>Deployment Status</th>
                <th>Skills & Cadre</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => {
                let taskBadgeClass = 'badge-pending';
                if (v.task_status === 'COMPLETED') taskBadgeClass = 'badge-active';
                if (v.task_status === 'IN_PROGRESS') taskBadgeClass = 'badge-verified';

                return (
                  <tr key={v.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            background: '#e0e7ff',
                            color: '#3730a3',
                            fontWeight: '700',
                            fontSize: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          {v.name.split(' ').map((n) => n[0]).join('')}
                        </div>
                        <div>
                          <div className="table-primary-text">{v.name}</div>
                          <div className="table-sub-text">{v.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontWeight: '500' }}>
                        <Flame size={14} style={{ color: '#dc2626' }} />
                        <span>{v.disaster_name}</span>
                      </div>
                    </td>
                    <td style={{ maxWidth: '280px', whiteSpace: 'normal' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                        <Briefcase size={14} style={{ color: 'var(--primary)', marginTop: '2px', flexShrink: 0 }} />
                        <span style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: '500' }}>
                          {v.task_title}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${taskBadgeClass}`}>
                        {v.task_status.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-active">
                        {v.assignment_status}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        {v.skills || 'General Relief'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            No volunteers found matching your query.
          </div>
        )}
      </div>
    </div>
  );
}

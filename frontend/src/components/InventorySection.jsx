import React, { useState } from 'react';
import {
  Warehouse,
  Search,
  Package,
  Layers,
  CheckCircle2,
  Clock,
  Archive,
} from 'lucide-react';

export default function InventorySection({ inventory }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');

  const categories = ['ALL', 'Food & Nutrition', 'Water & Sanitation', 'Medical Supplies', 'Shelter & Bedding'];

  const filtered = inventory.filter((item) => {
    const matchesSearch =
      item.item_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.category && item.category.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (item.warehouse_location && item.warehouse_location.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesStatus = statusFilter === 'ALL' || item.status === statusFilter;
    const matchesCategory = categoryFilter === 'ALL' || item.category === categoryFilter;

    return matchesSearch && matchesStatus && matchesCategory;
  });

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title-group">
          <Warehouse size={20} style={{ color: 'var(--primary)' }} />
          <h2 className="card-title">Relief Inventory & Warehouse Staging</h2>
          <span className="card-badge">{filtered.length} Batches</span>
        </div>
      </div>

      <div className="card-body">
        {/* Filter Controls */}
        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by relief item name, warehouse location..."
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-pills">
            {['ALL', 'STORED', 'RECEIVED', 'DISTRIBUTED'].map((st) => (
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

        {/* Category Filter Pills */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
          {categories.map((cat) => (
            <button
              key={cat}
              className={`filter-btn ${categoryFilter === cat ? 'active' : ''}`}
              style={{ fontSize: '12px', padding: '5px 12px' }}
              onClick={() => setCategoryFilter(cat)}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Tabular Inventory with Visual Progress Bars */}
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Batch ID</th>
                <th>Item Name</th>
                <th>Category</th>
                <th>Current Stock</th>
                <th>Original Intake</th>
                <th>Distribution Progress</th>
                <th>Status</th>
                <th>Warehouse Location</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const orig = Number(item.original_quantity) || 1;
                const remaining = Number(item.quantity) || 0;
                const distributed = Math.max(0, orig - remaining);
                const distributedPct = Math.min(100, Math.round((distributed / orig) * 100));

                let badgeClass = 'badge-active';
                if (item.status === 'RECEIVED') badgeClass = 'badge-pending';
                if (item.status === 'DISTRIBUTED') badgeClass = 'badge-resolved';

                return (
                  <tr key={item.id}>
                    <td style={{ fontWeight: '600' }}>#{item.id}</td>
                    <td className="table-primary-text">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Package size={15} style={{ color: 'var(--primary)' }} />
                        <span>{item.item_name}</span>
                      </div>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)', background: '#f1f5f9', padding: '3px 8px', borderRadius: '6px' }}>
                        {item.category || 'General Supplies'}
                      </span>
                    </td>
                    <td style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                      {remaining.toLocaleString()} {item.unit}
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>
                      {orig.toLocaleString()} {item.unit}
                    </td>
                    <td>
                      {/* Visual Progress Bar required by prompt */}
                      <div className="progress-container">
                        <div className="progress-label">
                          <span>{distributedPct}% Disbursed</span>
                          <span>{distributed.toLocaleString()} {item.unit}</span>
                        </div>
                        <div className="progress-bar-bg">
                          <div
                            className="progress-bar-fill"
                            style={{
                              width: `${distributedPct}%`,
                              background: distributedPct === 100 
                                ? 'linear-gradient(90deg, #059669, #10b981)' 
                                : 'linear-gradient(90deg, #2563eb, #38bdf8)',
                            }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${badgeClass}`}>
                        {item.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
                      📍 {item.warehouse_location || 'Central Warehouse'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            No relief inventory items match the selected filter.
          </div>
        )}
      </div>
    </div>
  );
}

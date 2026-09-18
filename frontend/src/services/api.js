// API Integration Service with Graceful Fallback to Presentation Demo Data
import {
  initialDisasters,
  initialInventory,
  initialVolunteers,
  initialBeneficiaries,
  initialCenters,
  initialDistributions,
  initialDonations,
} from '../data/demoData';

// Priority: local backend or configured environment URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export const apiClient = {
  // Test connection to backend health endpoint
  async checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        return { online: true, data };
      }
      return { online: false, error: `HTTP ${res.status}` };
    } catch (err) {
      return { online: false, error: err.message };
    }
  },

  // Fetch disasters with fallback
  async getDisasters() {
    try {
      const res = await fetch(`${API_BASE}/disasters`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return { data, isLive: true };
        }
      }
    } catch (e) {
      // Graceful fallback to rich presentation data
    }
    return { data: initialDisasters, isLive: false };
  },

  // Fetch inventory with fallback
  async getInventory(disasterId = null) {
    try {
      const url = disasterId 
        ? `${API_BASE}/inventory?disaster_id=${disasterId}` 
        : `${API_BASE}/inventory`;
      const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return { data, isLive: true };
        }
      }
    } catch (e) {
      // Fallback
    }
    return { data: initialInventory, isLive: false };
  },

  // Fetch beneficiaries with fallback
  async getBeneficiaries() {
    try {
      const res = await fetch(`${API_BASE}/beneficiaries`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return { data, isLive: true };
        }
      }
    } catch (e) {
      // Fallback
    }
    return { data: initialBeneficiaries, isLive: false };
  },

  // Fetch distribution centers with fallback
  async getDistributionCenters() {
    try {
      const res = await fetch(`${API_BASE}/distribution-centers`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return { data, isLive: true };
        }
      }
    } catch (e) {
      // Fallback
    }
    return { data: initialCenters, isLive: false };
  },

  // Fetch distribution records with fallback
  async getDistributions() {
    try {
      const res = await fetch(`${API_BASE}/distributions`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return { data, isLive: true };
        }
      }
    } catch (e) {
      // Fallback
    }
    return { data: initialDistributions, isLive: false };
  },
};

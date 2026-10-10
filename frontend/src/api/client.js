import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// Attach Authorization Bearer token from sessionStorage
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('case_connect_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: auto-logout on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      sessionStorage.removeItem('case_connect_token');
      sessionStorage.removeItem('case_connect_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// 1. Auth API
export const authApi = {
  login: async (username, password) => {
    const res = await api.post('/auth/login', { username, password });
    if (res.data.access_token) {
      sessionStorage.setItem('case_connect_token', res.data.access_token);
      sessionStorage.setItem('case_connect_user', JSON.stringify(res.data.user));
    }
    return res.data;
  },
  getMe: async () => {
    const res = await api.get('/auth/me');
    return res.data;
  },
  logout: async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      sessionStorage.removeItem('case_connect_token');
      sessionStorage.removeItem('case_connect_user');
    }
  },
};

// Dynamic Runtime Analysis API (Zero Hardcoding)
export const dynamicAnalysisApi = {
  analyseFile: async (file, onUploadProgress, caseId = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (caseId) {
      formData.append('case_id', caseId);
    }
    const res = await api.post('/analytics/analyse-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000, // 3 minutes timeout for heavy OCR or deep analysis
      onUploadProgress,
    });
    return res.data;
  },
  analyseText: async (title, text, caseId = null) => {
    const payload = { title, text };
    if (caseId) {
      payload.case_id = caseId;
    }
    const res = await api.post('/analytics/analyse-text', payload, {
      timeout: 120000, // 2 minutes timeout
    });
    return res.data;
  },
};

// 2. Cases API
export const casesApi = {
  list: async (search, priority) => {
    const params = {};
    if (search) params.search = search;
    if (priority && priority !== 'all') params.priority = priority;
    const res = await api.get('/cases', { params });
    return res.data;
  },
  get: async (caseId) => {
    const res = await api.get(`/cases/${caseId}`);
    return res.data;
  },
  create: async (caseData) => {
    const res = await api.post('/cases', caseData);
    return res.data;
  },
  delete: async (caseId) => {
    const res = await api.delete(`/cases/${caseId}`);
    return res.data;
  },
  addMember: async (caseId, userId, role = 'investigator') => {
    const res = await api.post(`/cases/${caseId}/members`, { user_id: userId, role });
    return res.data;
  },
  removeMember: async (caseId, userId) => {
    const res = await api.delete(`/cases/${caseId}/members/${userId}`);
    return res.data;
  },
  getSettings: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/settings`);
    return res.data;
  },
  updateSettings: async (caseId, settings) => {
    const res = await api.put(`/cases/${caseId}/settings`, settings);
    return res.data;
  },
  recomputeAnalytics: async (caseId) => {
    const res = await api.post(`/cases/${caseId}/settings/recompute`);
    return res.data;
  },
  getSavedViews: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/saved-views`);
    return res.data;
  },
  createSavedView: async (caseId, payload) => {
    const res = await api.post(`/cases/${caseId}/saved-views`, payload);
    return res.data;
  },
  seedHawala: async () => {
    const res = await api.post('/cases/seed/hawala');
    return res.data;
  },
  deleteSavedView: async (caseId, viewId) => {
    const res = await api.delete(`/cases/${caseId}/saved-views/${viewId}`);
    return res.data;
  },
};


// 3. Evidence API
export const evidenceApi = {
  list: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/evidence`);
    return res.data;
  },
  upload: async (caseId, formData, onUploadProgress) => {
    const res = await api.post(`/cases/${caseId}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    });
    return res.data;
  },
  verify: async (evidenceId) => {
    const res = await api.post(`/evidence/${evidenceId}/verify`);
    return res.data;
  },
  delete: async (evidenceId) => {
    const res = await api.delete(`/evidence/${evidenceId}`);
    return res.data;
  },
  preview: async (evidenceId) => {
    const res = await api.get(`/evidence/${evidenceId}/preview`);
    return res.data;
  },
  confirmMapping: async (evidenceId, mappingData) => {
    const res = await api.post(`/evidence/${evidenceId}/mapping`, mappingData);
    return res.data;
  },
  startIngest: async (evidenceId) => {
    const res = await api.post(`/evidence/${evidenceId}/ingest`);
    return res.data;
  },
  getJob: async (jobId) => {
    const res = await api.get(`/jobs/${jobId}`);
    return res.data;
  },
  getQuality: async (evidenceId) => {
    const res = await api.get(`/evidence/${evidenceId}/quality`);
    return res.data;
  },
};

// 4. Audit API
export const auditApi = {
  verify: async () => {
    const res = await api.get('/audit/verify');
    return res.data;
  },
  logs: async (limit = 50, offset = 0) => {
    const res = await api.get('/audit/logs', { params: { limit, offset } });
    return res.data;
  },
};

// 5. Graph API
export const graphApi = {
  search: async (caseId, { q, hops = 1, view = 'entity', limit = 200 } = {}) => {
    const params = { hops, view, limit };
    if (q) params.q = q;
    const res = await api.get(`/cases/${caseId}/graph/search`, { params });
    return res.data;
  },
  findPath: async (caseId, fromKey, toKey, view = 'entity') => {
    const params = { from_key: fromKey, to_key: toKey, view };
    const res = await api.get(`/cases/${caseId}/graph/path`, { params });
    return res.data;
  },
  createLink: async (caseId, sourceId, targetId, linkType = 'USES') => {
    const res = await api.post(`/cases/${caseId}/links`, {
      source_entity_id: sourceId,
      target_entity_id: targetId,
      link_type: linkType,
    });
    return res.data;
  },
  deleteLink: async (caseId, linkId) => {
    const res = await api.delete(`/cases/${caseId}/links/${linkId}`);
    return res.data;
  },
  rebuild: async (caseId) => {
    const res = await api.post(`/cases/${caseId}/graph/rebuild`);
    return res.data;
  },
};

// 6. Money Trail API
export const moneyApi = {
  getTrail: async (caseId, { account, minAmount = 0, hops = 2, direction = 'both', limit = 200 } = {}) => {
    const params = { min_amount: minAmount, hops, direction, limit };
    if (account) params.account = account;
    const res = await api.get(`/cases/${caseId}/money-trail`, { params });
    return res.data;
  },
  getTxnVolume: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/analytics/txn-volume`);
    return res.data;
  },
  listTransactions: async (caseId, { account, minAmount, limit = 100, offset = 0 } = {}) => {
    const params = { limit, offset };
    if (account) params.account = account;
    if (minAmount !== undefined && minAmount !== null) params.min_amount = minAmount;
    const res = await api.get(`/cases/${caseId}/transactions`, { params });
    return res.data;
  },
};

// 7. Document Extraction & NLP Review API
export const extractionApi = {
  extract: async (evidenceId) => {
    const res = await api.post(`/evidence/${evidenceId}/extract`);
    return res.data;
  },
  list: async (caseId, { status, type, minConf, evidenceId, limit = 200, offset = 0 } = {}) => {
    const params = { limit, offset };
    if (status) params.status = status;
    if (type) params.type = type;
    if (minConf !== undefined && minConf !== null) params.min_conf = minConf;
    if (evidenceId) params.evidence_id = evidenceId;
    const res = await api.get(`/cases/${caseId}/extracted`, { params });
    return res.data;
  },
  getText: async (evidenceId) => {
    const res = await api.get(`/evidence/${evidenceId}/text`);
    return res.data;
  },
  update: async (extractedId, { status, normalizedValue } = {}) => {
    const res = await api.patch(`/extracted/${extractedId}`, {
      status,
      normalized_value: normalizedValue,
    });
    return res.data;
  },
  createManual: async (caseId, manualData) => {
    const res = await api.post(`/cases/${caseId}/extracted`, manualData);
    return res.data;
  },
  approveAll: async (caseId, threshold = 0.8) => {
    const res = await api.post(`/cases/${caseId}/extracted/approve-all`, null, {
      params: { threshold },
    });
    return res.data;
  },
};

// 7b. Entity Matching & Master Profiles (Phase 7 - Hero Feature #1) API
export const matchesApi = {
  listMatches: async (caseId, { level, status, limit = 50, offset = 0 } = {}) => {
    const params = { limit, offset };
    if (level) params.level = level;
    if (status) params.status = status;
    const res = await api.get(`/cases/${caseId}/matches`, { params });
    return res.data;
  },
  generateMatches: async (caseId) => {
    const res = await api.post(`/cases/${caseId}/matches/generate`);
    return res.data;
  },
  approveMatch: async (matchId) => {
    const res = await api.post(`/matches/${matchId}/approve`);
    return res.data;
  },
  rejectMatch: async (matchId) => {
    const res = await api.post(`/matches/${matchId}/reject`);
    return res.data;
  },
  undoMatch: async (matchId) => {
    const res = await api.post(`/matches/${matchId}/undo`);
    return res.data;
  },
  listProfiles: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/profiles`);
    return res.data;
  },
  getProfileDetail: async (caseId, profileId) => {
    const res = await api.get(`/cases/${caseId}/profiles/${profileId}`);
    return res.data;
  },
  getCrossCaseAlerts: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/cross-case-alerts`);
    return res.data;
  },
};

// 8. Reports & Section 63 BSA 2023 Export API
export const reportsApi = {
  create: async (caseId, reportData) => {
    const res = await api.post(`/cases/${caseId}/reports`, reportData);
    return res.data;
  },
  list: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/reports`);
    return res.data;
  },
  download: async (reportId, filename = 'report.pdf') => {
    const res = await api.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  exportJson: async (caseId, filename = 'case_export.json') => {
    const res = await api.get(`/cases/${caseId}/export/json`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

// 9. Analytics & Lead Advisor (Hero Feature #3) API
export const analyticsApi = {
  getOverview: async (caseId, { fromDate, toDate } = {}) => {
    const params = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const res = await api.get(`/cases/${caseId}/analytics/overview`, { params });
    return res.data;
  },
  getCallsPerDay: async (caseId, { phone, fromDate, toDate } = {}) => {
    const params = {};
    if (phone) params.phone = phone;
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const res = await api.get(`/cases/${caseId}/analytics/calls-per-day`, { params });
    return res.data;
  },
  getTxnVolume: async (caseId, { account, fromDate, toDate } = {}) => {
    const params = {};
    if (account) params.account = account;
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const res = await api.get(`/cases/${caseId}/analytics/txn-volume`, { params });
    return res.data;
  },
  getTopEntities: async (caseId, { metric = 'degree', limit = 10 } = {}) => {
    const res = await api.get(`/cases/${caseId}/analytics/top-entities`, {
      params: { metric, limit },
    });
    return res.data;
  },
  getCommunities: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/analytics/communities`);
    return res.data;
  },
  getDegreeDistribution: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/analytics/degree-distribution`);
    return res.data;
  },
  getCallHeatmap: async (caseId) => {
    const res = await api.get(`/cases/${caseId}/analytics/call-heatmap`);
    return res.data;
  },
  getAlerts: async (caseId, { severity, patternType, recompute = false } = {}) => {
    const params = { recompute };
    if (severity) params.severity = severity;
    if (patternType) params.pattern_type = patternType;
    const res = await api.get(`/cases/${caseId}/alerts`, { params });
    return res.data;
  },
  getLeads: async (caseId, { level, limit = 50 } = {}) => {
    const params = { limit };
    if (level) params.level = level;
    const res = await api.get(`/cases/${caseId}/leads`, { params });
    return res.data;
  },
  recordLeadDecision: async (caseId, leadId, { decision, notes }) => {
    const res = await api.post(`/cases/${caseId}/leads/${leadId}/decision`, {
      decision,
      notes,
    });
    return res.data;
  },
  getEntityWhy: async (caseId, entityId) => {
    const res = await api.get(`/cases/${caseId}/entities/${entityId}/why`);
    return res.data;
  },
  getProvenance: async (caseId, { nodeId, edgeId } = {}) => {
    const params = {};
    if (nodeId) params.node_id = nodeId;
    if (edgeId) params.edge_id = edgeId;
    const res = await api.get(`/cases/${caseId}/provenance`, { params });
    return res.data;
  },
  getTxnsPerDay: async (caseId, { account, fromDate, toDate } = {}) => {
    const params = {};
    if (account) params.account = account;
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const res = await api.get(`/cases/${caseId}/analytics/txns-per-day`, { params });
    return res.data;
  },
  getTimeline: async (caseId, { entity, type, fromDate, toDate, limit = 500 } = {}) => {
    const params = { limit };
    if (entity) params.entity = entity;
    if (type) params.type = type;
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    const res = await api.get(`/cases/${caseId}/timeline`, { params });
    return res.data;
  },
};

// 11. AI & Gemini Copilot API
export const aiApi = {
  getStatus: async () => {
    const res = await api.get('/ai/status');
    return res.data;
  },
  getBrief: async (caseId) => {
    const res = await api.post(`/ai/cases/${caseId}/brief`);
    return res.data;
  },
  askCopilot: async (caseId, query) => {
    const res = await api.post(`/ai/cases/${caseId}/copilot`, { query });
    return res.data;
  },
};

export const getHealth = async () => {
  try {
    const res = await api.get('/health');
    return res.data;
  } catch (error) {
    return {
      status: 'offline',
      sqlite: 'unreachable',
      neo4j: 'unreachable',
      error: error.message,
    };
  }
};

export default api;

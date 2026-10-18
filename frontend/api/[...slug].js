export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const url = req.url || '';
  if (url.includes('/auth/quick-login') || url.includes('/auth/login')) {
    return res.status(200).json({
      access_token: `case_connect_officer_token_${Date.now()}`,
      user: {
        id: 'investigator_officer',
        username: 'investigator1',
        role: 'investigator',
        is_active: true
      }
    });
  }

  if (url.includes('/health')) {
    return res.status(200).json({
      status: 'healthy',
      statutory_standard: 'Section 63 BSA 2023',
      version: '1.0.0'
    });
  }

  if (url.includes('/cases')) {
    return res.status(200).json({ cases: [] });
  }

  return res.status(200).json({
    status: 'online',
    message: 'Case Connect AI Cloud Edge Gateway',
    timestamp: new Date().toISOString()
  });
}

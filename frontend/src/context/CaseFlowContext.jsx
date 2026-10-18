import React, { createContext, useContext, useState, useEffect } from 'react';
import { dynamicAnalysisApi, casesApi } from '../api/client';

const CaseFlowContext = createContext(null);

export const useCaseFlow = () => {
  const context = useContext(CaseFlowContext);
  if (!context) {
    throw new Error('useCaseFlow must be used within a CaseFlowProvider');
  }
  return context;
};

// Helper: Auto-detect evidence type from filename and extension
export const detectEvidenceType = (filename = '') => {
  const name = filename.toLowerCase();
  if (name.includes('cdr') || name.includes('call') || name.includes('tower')) return 'CDR';
  if (name.includes('bank') || name.includes('stmt') || name.includes('txn') || name.includes('statement') || name.includes('axis') || name.includes('hdfc') || name.includes('sbi')) return 'BANK';
  if (name.includes('fir') || name.includes('complaint') || name.includes('police')) return 'FIR';
  if (name.includes('ip') || name.includes('log') || name.includes('access') || name.includes('pcap')) return 'IP';
  if (name.includes('sdr') || name.includes('caf') || name.includes('subscriber')) return 'SDR';
  if (name.endsWith('.pdf')) return 'DOC';
  if (name.endsWith('.csv') || name.endsWith('.xlsx')) return 'DATA';
  return 'RAW';
};

export const CaseFlowProvider = ({ children }) => {
  const [phase, setPhase] = useState('upload'); // 'upload' | 'loading' | 'case'
  const [activeCaseId, setActiveCaseId] = useState(null);
  const [activeCaseData, setActiveCaseData] = useState(null);
  const [recentCases, setRecentCases] = useState([]);
  const [fileQueue, setFileQueue] = useState([]);
  const [caseTitle, setCaseTitle] = useState('');
  const [caseRefNumber, setCaseRefNumber] = useState('');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingStepText, setLoadingStepText] = useState('Initializing investigation docket...');
  const [error, setError] = useState(null);

  // Load recent cases on mount
  useEffect(() => {
    fetchRecentCases();
  }, []);

  const fetchRecentCases = async () => {
    try {
      const res = await casesApi.list(null, 'all');
      const list = res.cases || res || [];
      setRecentCases(Array.isArray(list) ? list.slice(0, 5) : []);
    } catch (err) {
      console.warn('[CASE FLOW] Could not fetch recent cases:', err.message);
    }
  };

  const addFiles = (newFiles) => {
    const mapped = Array.from(newFiles).map(file => ({
      file,
      name: file.name,
      size: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
      type: detectEvidenceType(file.name),
      rawSize: file.size
    }));
    setFileQueue(prev => [...prev, ...mapped]);
    if (!caseTitle && mapped.length > 0) {
      setCaseTitle(`Case Investigation: ${mapped[0].name.replace(/\.[^/.]+$/, "")}`);
    }
  };

  const removeFile = (index) => {
    setFileQueue(prev => prev.filter((_, i) => i !== index));
  };

  const clearQueue = () => {
    setFileQueue([]);
    setCaseTitle('');
    setCaseRefNumber('');
    setError(null);
  };

  // 1. Dynamic Runtime Analysis of Uploaded Files (Zero Pre-baked Mocks)
  const startDynamicAnalysis = async () => {
    if (fileQueue.length === 0) {
      setError('Please select at least one evidence file for ingestion.');
      return;
    }

    setError(null);
    setPhase('loading');
    setLoadingProgress(10);
    setLoadingStepText('Reading raw files & sanitizing timestamps...');

    try {
      let currentCaseId = null;
      let finalResult = null;

      const steps = [
        "Mapping columns (CDR, IMPS, RTGS, SDR)...",
        "Extracting entities, phone numbers & bank accounts...",
        "Linking entities via Louvain graph clustering...",
        "Tracing cross-state layering loops...",
        "Scoring lead probability vectors..."
      ];

      // Simulated step animation interval while real request processes
      let simProgress = 15;
      const progressTimer = setInterval(() => {
        simProgress = Math.min(simProgress + 7, 85);
        setLoadingProgress(simProgress);
        const stepIdx = Math.min(Math.floor((simProgress / 100) * steps.length), steps.length - 1);
        setLoadingStepText(steps[stepIdx]);
      }, 400);

      // Sequentially process each file into the single case docket
      for (let i = 0; i < fileQueue.length; i++) {
        const item = fileQueue[i];
        const res = await dynamicAnalysisApi.analyseFile(item.file, null, currentCaseId);
        finalResult = res;
        if (res.case_id) {
          currentCaseId = res.case_id;
        }
      }

      clearInterval(progressTimer);
      setLoadingProgress(100);
      setLoadingStepText('Forensic synthesis complete. Loading investigation hub...');

      // Commit state
      setActiveCaseId(currentCaseId);
      setActiveCaseData(finalResult);
      await fetchRecentCases();

      // Smooth transition to case main scroll page
      setTimeout(() => {
        setPhase('case');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 600);

    } catch (err) {
      console.error('[DYNAMIC ANALYSIS ERROR]', err);
      setError(err.response?.data?.detail || err.message || 'Evidence file analysis failed.');
      setPhase('upload');
    }
  };

  // 2. Load Sample Hawala Case Dynamically
  const loadSampleHawalaCase = async () => {
    setError(null);
    setPhase('loading');
    setLoadingProgress(20);
    setLoadingStepText('Seeding verified Hawala Syndicate forensic dataset (₹1.84 Cr)...');

    try {
      const steps = [
        "Ingesting Hawala Axis Bank Statements & CDR Dumps...",
        "Running Named Entity Recognition on FIR #408...",
        
        "Computing Louvain community partitions...",
        "Detecting pass-through money loops...",
        "Attributing primary orchestrator lead..."
      ];

      let simProgress = 25;
      const timer = setInterval(() => {
        simProgress = Math.min(simProgress + 10, 88);
        setLoadingProgress(simProgress);
        const stepIdx = Math.min(Math.floor((simProgress / 100) * steps.length), steps.length - 1);
        setLoadingStepText(steps[stepIdx]);
      }, 350);

      const res = await casesApi.seedHawala();
      clearInterval(timer);

      setLoadingProgress(100);
      setLoadingStepText('Hawala docket ready. Transitioning to investigation hub...');

      const caseId = res.case?.id || res.id || res.case_id;
      setActiveCaseId(caseId);
      setActiveCaseData(res);
      await fetchRecentCases();

      setTimeout(() => {
        setPhase('case');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 600);

    } catch (err) {
      console.error('[SEED HAWALA ERROR]', err);
      setError(err.response?.data?.detail || err.message || 'Could not seed sample case.');
      setPhase('upload');
    }
  };

  // 3. Load Existing Case by ID
  const loadCaseById = async (caseId) => {
    setError(null);
    setPhase('loading');
    setLoadingProgress(40);
    setLoadingStepText('Loading investigation docket records...');

    try {
      const res = await casesApi.get(caseId);
      setLoadingProgress(100);
      setActiveCaseId(caseId);
      setActiveCaseData(res);

      setTimeout(() => {
        setPhase('case');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 400);
    } catch (err) {
      setError('Could not load case docket.');
      setPhase('upload');
    }
  };

  const resetToUpload = () => {
    setPhase('upload');
    setActiveCaseId(null);
    setActiveCaseData(null);
    clearQueue();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <CaseFlowContext.Provider
      value={{
        phase,
        setPhase,
        activeCaseId,
        activeCaseData,
        recentCases,
        fileQueue,
        caseTitle,
        setCaseTitle,
        caseRefNumber,
        setCaseRefNumber,
        loadingProgress,
        loadingStepText,
        error,
        setError,
        addFiles,
        removeFile,
        clearQueue,
        startDynamicAnalysis,
        loadSampleHawalaCase,
        loadCaseById,
        resetToUpload,
        fetchRecentCases
      }}
    >
      {children}
    </CaseFlowContext.Provider>
  );
};

export default CaseFlowContext;

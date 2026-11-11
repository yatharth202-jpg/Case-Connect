import React, { useState, useEffect, useRef } from 'react';
import { Eye, Check, AlertCircle, FileText, Edit3, ShieldCheck, Lock, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { extractionV2Api } from '../../api/client';

export default function OcrReviewScreen({ caseId, evidenceList = [], isViewer = false }) {
  const [selectedEvidenceId, setSelectedEvidenceId] = useState('');
  const [pages, setPages] = useState([]);
  const [selectedPageNo, setSelectedPageNo] = useState(1);
  const [ocrData, setOcrData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeWordId, setActiveWordId] = useState(null);
  const [editedWords, setEditedWords] = useState({});
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState('');

  // Auto-select first PDF or image evidence file
  useEffect(() => {
    if (evidenceList.length > 0 && !selectedEvidenceId) {
      const docEv = evidenceList.find(e => {
        const name = (e.filename || e.name || '').toLowerCase();
        return name.endsWith('.pdf') || name.endsWith('.jpg') || name.endsWith('.png') || name.endsWith('.tiff');
      });
      if (docEv) {
        setSelectedEvidenceId(docEv.id);
      } else {
        setSelectedEvidenceId(evidenceList[0].id);
      }
    }
  }, [evidenceList]);

  useEffect(() => {
    if (selectedEvidenceId) {
      loadPages(selectedEvidenceId);
    }
  }, [selectedEvidenceId]);

  useEffect(() => {
    if (selectedEvidenceId && selectedPageNo) {
      loadPageOcr(selectedEvidenceId, selectedPageNo);
    }
  }, [selectedEvidenceId, selectedPageNo]);

  const loadPages = async (evId) => {
    try {
      const res = await extractionV2Api.getPages(evId);
      const list = res.pages || res || [];
      const pgList = Array.isArray(list) ? list : [];
      setPages(pgList);
      if (pgList.length > 0) {
        setSelectedPageNo(pgList[0].page_number || 1);
      }
    } catch (e) {
      setPages([]);
    }
  };

  const loadPageOcr = async (evId, pgNo) => {
    setLoading(true);
    setSaveSuccess('');
    try {
      const res = await extractionV2Api.getPageOcr(evId, pgNo);
      setOcrData(res);
      setEditedWords({});
    } catch (e) {
      setOcrData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleWordEdit = (wordId, newText) => {
    setEditedWords(prev => ({
      ...prev,
      [wordId]: newText,
    }));
  };

  const handleSaveCorrection = async () => {
    if (Object.keys(editedWords).length === 0) return;
    setSaving(true);
    try {
      await extractionV2Api.submitCorrection(selectedEvidenceId, selectedPageNo, {
        corrections: editedWords,
      });
      setSaveSuccess('Officer correction locked and registered in golden claims.');
      setTimeout(() => setSaveSuccess(''), 3000);
      loadPageOcr(selectedEvidenceId, selectedPageNo);
    } catch (err) {
      alert('Failed to submit correction: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  const currentPageMeta = pages.find(p => p.page_number === selectedPageNo) || {};
  const words = ocrData?.words || [];
  const lowConfidenceCount = words.filter(w => (w.conf || w.confidence || 1) < 0.6).length;

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Evidence Document & Page Selector Toolbar */}
      <div className="p-4 rounded-2xl glass-sm border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <label className="text-muted text-[11px] uppercase">Document:</label>
          <select
            value={selectedEvidenceId}
            onChange={(e) => setSelectedEvidenceId(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-black/50 border border-white/10 text-text text-xs focus:outline-none focus:border-accent"
          >
            {evidenceList.map(e => (
              <option key={e.id} value={e.id}>{e.filename || e.name || e.id}</option>
            ))}
          </select>
        </div>

        {/* Page Switcher */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <button
              disabled={selectedPageNo <= 1}
              onClick={() => setSelectedPageNo(p => Math.max(1, p - 1))}
              className="p-1.5 rounded-lg border border-white/10 text-muted hover:text-text disabled:opacity-30"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="text-text font-semibold px-2">Page {selectedPageNo} of {pages.length || 1}</span>
            <button
              disabled={selectedPageNo >= pages.length}
              onClick={() => setSelectedPageNo(p => p + 1)}
              className="p-1.5 rounded-lg border border-white/10 text-muted hover:text-text disabled:opacity-30"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Quality Chips */}
          <div className="flex items-center gap-2">
            {currentPageMeta.quality_score !== undefined && (
              <span className="px-2 py-0.5 rounded text-[10px] bg-white/5 border border-white/10 text-muted">
                Quality: {Math.round(currentPageMeta.quality_score * 100)}%
              </span>
            )}
            {lowConfidenceCount > 0 && (
              <span className="px-2 py-0.5 rounded text-[10px] bg-amber-950/60 text-amber-300 border border-amber-800">
                {lowConfidenceCount} Low-Conf Words
              </span>
            )}
            {currentPageMeta.is_handwritten && (
              <span className="px-2 py-0.5 rounded text-[10px] bg-rose-950/60 text-rose-300 border border-rose-800">
                Handwriting Review
              </span>
            )}
          </div>
        </div>
      </div>

      {saveSuccess && (
        <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800 text-emerald-300 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>{saveSuccess}</span>
        </div>
      )}

      {/* Dual Panel Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* LEFT: Page Canvas / Word Bounding Boxes View */}
        <div className="p-5 rounded-2xl glass border border-white/10 flex flex-col space-y-3 min-h-[500px]">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div className="font-serif text-sm text-text font-bold">
              Page Visual Word Layout
            </div>
            <span className="text-[10px] text-muted">Hover word to inspect box</span>
          </div>

          <div className="flex-1 rounded-xl bg-black/40 border border-white/5 p-4 overflow-y-auto relative min-h-[420px] flex flex-wrap content-start gap-1.5">
            {loading ? (
              <div className="w-full py-28 text-center text-muted">
                <div className="inline-block animate-spin w-5 h-5 border-2 border-white/20 border-t-accent rounded-full mb-2" />
                <p>Rendering OCR word bounding spans...</p>
              </div>
            ) : words.length === 0 ? (
              <div className="w-full py-28 text-center text-muted italic">
                No OCR bounding words detected for this page.
              </div>
            ) : (
              words.map((w, idx) => {
                const conf = w.conf !== undefined ? w.conf : w.confidence !== undefined ? w.confidence : 0.9;
                const isSelected = activeWordId === idx;
                const isLow = conf < 0.6;

                return (
                  <span
                    key={idx}
                    onMouseEnter={() => setActiveWordId(idx)}
                    onClick={() => setActiveWordId(idx)}
                    className={`inline-block px-1.5 py-0.5 rounded cursor-pointer transition-all text-xs ${
                      isSelected
                        ? 'bg-accent text-ink font-bold shadow-md scale-105'
                        : isLow
                        ? 'bg-amber-950/50 text-amber-300 border border-amber-800/60'
                        : 'bg-white/5 text-text hover:bg-white/15'
                    }`}
                    title={`Word: "${w.text}" · Confidence: ${Math.round(conf * 100)}%`}
                  >
                    {editedWords[idx] || w.text}
                  </span>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT: Editable Transcript & Corrections */}
        <div className="p-5 rounded-2xl glass border border-white/10 flex flex-col space-y-3 min-h-[500px]">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div className="font-serif text-sm text-text font-bold">
              Forensic Officer Transcript & Corrections
            </div>
            <span className="text-[10px] text-muted">Highest Trust Claim Layer</span>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto max-h-[460px]">
            {activeWordId !== null && words[activeWordId] && (
              <div className="p-3.5 rounded-xl bg-accent/10 border border-accent/30 space-y-2">
                <div className="flex justify-between items-center text-accent text-[11px] font-bold">
                  <span>SELECTED WORD #{activeWordId + 1}</span>
                  <span>Confidence: {Math.round((words[activeWordId].conf || 0.9) * 100)}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={editedWords[activeWordId] !== undefined ? editedWords[activeWordId] : words[activeWordId].text}
                    onChange={(e) => handleWordEdit(activeWordId, e.target.value)}
                    className="flex-1 px-3 py-1.5 rounded-lg bg-black/50 border border-accent text-text text-xs focus:outline-none"
                    placeholder="Correct text..."
                  />
                  <span className="text-[10px] text-muted shrink-0">Press Save below</span>
                </div>
              </div>
            )}

            <div className="p-3.5 rounded-xl bg-black/30 border border-white/5 text-text text-xs leading-relaxed space-y-2">
              <div className="text-[10px] text-muted uppercase tracking-wider font-semibold">
                Complete Extracted Text
              </div>
              <div className="whitespace-pre-wrap font-sans text-xs text-text/90">
                {ocrData?.raw_text || words.map((w, i) => editedWords[i] || w.text).join(' ') || 'No extracted text found.'}
              </div>
            </div>
          </div>

          {/* Action buttons */}
          {!isViewer && (
            <div className="pt-2 flex justify-end gap-2 border-t border-white/10">
              <button
                type="button"
                disabled={saving || Object.keys(editedWords).length === 0}
                onClick={handleSaveCorrection}
                className="px-4 py-2 bg-accent text-ink font-semibold rounded-xl hover:bg-accent/90 disabled:opacity-40 transition-colors flex items-center gap-1.5 text-xs"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Save Officer Claim</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

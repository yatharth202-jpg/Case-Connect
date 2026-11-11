import React, { useState, useEffect, useRef } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  Video,
  FileAudio,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Edit3,
  Save,
  Filter,
  RefreshCw,
} from "lucide-react";
import { extractionV2Api } from "../../api/client";

export default function MediaReviewScreen({ evidenceId, caseId }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [transcriptData, setTranscriptData] = useState(null);
  const [filterReviewOnly, setFilterReviewOnly] = useState(false);
  const [editingSegmentId, setEditingSegmentId] = useState(null);
  const [editText, setEditText] = useState("");
  const [editNote, setEditNote] = useState("");
  const [savingId, setSavingId] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  const mediaRef = useRef(null);

  useEffect(() => {
    loadTranscript();
  }, [evidenceId, filterReviewOnly]);

  const loadTranscript = async () => {
    if (!evidenceId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await extractionV2Api.getMediaTranscript(evidenceId, filterReviewOnly);
      setTranscriptData(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load media transcript.");
    } finally {
      setLoading(false);
    }
  };

  const handleSeek = (sec) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = sec;
      mediaRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleStartEdit = (seg) => {
    setEditingSegmentId(seg.id);
    setEditText(seg.text);
    setEditNote(seg.officer_note || "");
  };

  const handleSaveCorrection = async (segId) => {
    setSavingId(segId);
    try {
      await extractionV2Api.updateMediaSegment(segId, {
        text: editText,
        officer_note: editNote,
        is_reviewed: true,
      });
      setEditingSegmentId(null);
      await loadTranscript();
    } catch (err) {
      alert(err?.response?.data?.detail || "Failed to save officer correction.");
    } finally {
      setSavingId(null);
    }
  };

  const formatTimestamp = (totalSec) => {
    const mins = Math.floor(totalSec / 60);
    const secs = Math.floor(totalSec % 60);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  if (loading) {
    return (
      <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-lg">
        <RefreshCw className="w-8 h-8 mx-auto animate-spin text-cyan-400 mb-3" />
        <p className="text-sm text-slate-400">Loading timestamped media transcript...</p>
      </div>
    );
  }

  const segments = transcriptData?.segments || [];
  const pendingCount = transcriptData?.pending_review_count || 0;

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-slate-900/80 border border-slate-800 rounded-lg">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-cyan-950/60 border border-cyan-800/50 rounded-md">
            <Volume2 className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              Forensic Media Intelligence
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                {segments.length} segments
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Offline Speech-to-Text & Video Keyframe Provenance
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setFilterReviewOnly(!filterReviewOnly)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md border flex items-center gap-1.5 transition-colors ${
              filterReviewOnly
                ? "bg-amber-950/70 border-amber-600 text-amber-200"
                : "bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700"
            }`}
          >
            <Filter className="w-3.5 h-3.5" />
            {filterReviewOnly ? "Showing Flagged Only" : `Review Queue (${pendingCount})`}
          </button>
          <button
            onClick={loadTranscript}
            className="p-1.5 bg-slate-800 border border-slate-700 text-slate-300 hover:text-slate-100 rounded-md transition-colors"
            title="Refresh transcript"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-lg flex items-start gap-3 text-red-200 text-xs">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold mb-0.5">Media Extraction Notice</p>
            <p className="text-red-300/90">{error}</p>
          </div>
        </div>
      )}

      {/* Media Player Section */}
      <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg space-y-3">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            Current Time: <span className="font-mono text-cyan-400">{formatTimestamp(currentTime)}</span>
          </span>
          <span className="text-[11px] text-slate-500">
            Click any transcript timestamp to seek playback
          </span>
        </div>
        <audio
          ref={mediaRef}
          controls
          className="w-full h-10 accent-cyan-500 rounded bg-slate-950"
          onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        />
      </div>

      {/* Transcript Segments List */}
      {segments.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/40 border border-dashed border-slate-800 rounded-lg">
          <FileAudio className="w-10 h-10 mx-auto text-slate-600 mb-2.5" />
          <h4 className="text-sm font-medium text-slate-300">No Transcript Segments Available</h4>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Run media extraction on this evidence file to populate timestamped speech-to-text units.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {segments.map((seg) => {
            const isEditing = editingSegmentId === seg.id;
            const isCurrent = currentTime >= seg.start_sec && currentTime <= seg.end_sec;

            return (
              <div
                key={seg.id}
                className={`p-3.5 rounded-lg border transition-all ${
                  isCurrent
                    ? "bg-cyan-950/30 border-cyan-500/50 ring-1 ring-cyan-500/30"
                    : seg.needs_review && !seg.is_reviewed
                    ? "bg-amber-950/20 border-amber-900/40"
                    : "bg-slate-900/50 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSeek(seg.start_sec)}
                      className="px-2 py-0.5 rounded bg-slate-800 hover:bg-cyan-950/60 hover:text-cyan-300 text-slate-300 text-xs font-mono border border-slate-700 hover:border-cyan-700 flex items-center gap-1 transition-colors"
                      title="Seek to this timestamp"
                    >
                      <Play className="w-2.5 h-2.5 text-cyan-400 fill-cyan-400" />
                      {formatTimestamp(seg.start_sec)} - {formatTimestamp(seg.end_sec)}
                    </button>

                    {seg.needs_review && !seg.is_reviewed && (
                      <span className="px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 text-[11px] font-medium flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3 text-amber-400" />
                        Low Confidence ({Math.round(seg.confidence * 100)}%)
                      </span>
                    )}

                    {seg.is_reviewed && (
                      <span className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-[11px] font-medium flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        Officer Reviewed
                      </span>
                    )}
                  </div>

                  {!isEditing && (
                    <button
                      onClick={() => handleStartEdit(seg)}
                      className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors"
                      title="Edit transcript text"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {isEditing ? (
                  <div className="space-y-2 mt-2">
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      rows={2}
                      className="w-full p-2 text-xs bg-slate-950 border border-slate-700 rounded text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
                    />
                    <input
                      type="text"
                      placeholder="Officer review note or justification..."
                      value={editNote}
                      onChange={(e) => setEditNote(e.target.value)}
                      className="w-full p-2 text-xs bg-slate-950 border border-slate-700 rounded text-slate-300 focus:outline-none focus:border-cyan-500"
                    />
                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        onClick={() => setEditingSegmentId(null)}
                        className="px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 rounded border border-slate-700"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSaveCorrection(seg.id)}
                        disabled={savingId === seg.id}
                        className="px-3 py-1 text-xs font-medium text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded flex items-center gap-1 disabled:opacity-50"
                      >
                        <Save className="w-3 h-3" />
                        {savingId === seg.id ? "Saving..." : "Save Correction"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs text-slate-200 leading-relaxed font-sans">{seg.text}</p>
                    {seg.officer_note && (
                      <p className="text-[11px] text-slate-400 mt-1.5 italic bg-slate-950/40 p-1.5 rounded border border-slate-800/80">
                        Officer note: {seg.officer_note}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

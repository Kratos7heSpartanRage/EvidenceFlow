import { AlertCircle, Ban, Check } from 'lucide-react';
import { useState } from 'react';
import type { EntityId } from '../../types/api';
import { Criterion } from '../../types/api';
import { Modal } from './Modal';

interface ReasonModalProps {
  isOpen: boolean;
  onClose: () => void;
  criteria: Criterion[];
  recordTitle?: string;
  onConfirm: (data: { criterion_id?: EntityId | null; reason_text: string; note?: string; }) => void;
}

export function ReasonModal({ isOpen, onClose, criteria, recordTitle, onConfirm }: ReasonModalProps) {
  const [selectedCriterionId, setSelectedCriterionId] = useState<EntityId | null>(null);
  const [customReason, setCustomReason] = useState('');
  const [note, setNote] = useState('');

  const excludeCriteria = criteria.filter(c => c.kind === 'exclude' && c.is_active);

  const isValid = selectedCriterionId !== null || customReason.trim().length > 0;

  const handleConfirm = () => {
    if (!isValid) return;

    let finalReason = customReason.trim();
    if (!finalReason && selectedCriterionId) {
      const crit = criteria.find(c => c.id === selectedCriterionId);
      finalReason = crit ? `${crit.label}: ${crit.reason}` : 'Excluded per protocol criteria';
    }

    onConfirm({
      criterion_id: selectedCriterionId,
      reason_text: finalReason,
      note: note.trim() || undefined
    });

    // Reset
    setSelectedCriterionId(null);
    setCustomReason('');
    setNote('');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Exclusion Reason Required"
      description="Every excluded study must have an explicit reason documented for systematic auditability."
    >
      {recordTitle && (
        <div className="p-3 bg-slate-100 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-lg text-xs text-slate-700 dark:text-slate-300">
          <span className="text-slate-500 dark:text-slate-400 font-semibold block mb-0.5">Target Record:</span>
          <span className="line-clamp-2 italic">{recordTitle}</span>
        </div>
      )}

      {/* Select protocol criterion */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between">
          <span>Standard Protocol Criterion (Select One):</span>
          <span className="text-[10px] text-teal-600 dark:text-teal-400 font-medium">Step 0 Criteria</span>
        </label>
        <div className="grid gap-2 max-h-48 overflow-y-auto pr-1">
          {excludeCriteria.map(c => {
            const isSelected = selectedCriterionId === c.id;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedCriterionId(isSelected ? null : c.id)}
                className={`w-full text-left p-2.5 rounded-lg border text-xs transition-all flex items-start justify-between gap-2 ${isSelected
                    ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-500/60 text-rose-800 dark:text-rose-200 shadow-sm'
                    : 'bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
              >
                <div>
                  <div className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                    <span>{c.label}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono">{c.code}</span>
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{c.reason}</div>
                </div>
                {isSelected && <Check className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* Custom Reason */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
          Or Specific / Custom Reason:
        </label>
        <textarea
          value={customReason}
          onChange={(e) => setCustomReason(e.target.value)}
          placeholder="e.g. Pediatric cohort with mean age 14.2 years; fails adult inclusion criteria..."
          className="w-full px-3 py-2 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-xs text-slate-900 dark:text-slate-200 focus:outline-none focus:border-teal-500 min-h-[60px]"
        />
      </div>

      {/* Reviewer Note */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
          Additional Reviewer Note (Optional):
        </label>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Optional notes for co-reviewers..."
          className="w-full px-3 py-2 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg text-xs text-slate-900 dark:text-slate-200 focus:outline-none focus:border-teal-500"
        />
      </div>

      {/* Validation Warning */}
      {!isValid && (
        <div className="flex items-center gap-2 p-2 rounded bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/40 text-amber-800 dark:text-amber-300 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-amber-500" />
          <span>You must select a criterion or enter a custom reason before submitting.</span>
        </div>
      )}

      {/* Footer Actions */}
      <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-200 dark:border-slate-800">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={!isValid}
          onClick={handleConfirm}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all shadow ${isValid
              ? 'bg-rose-600 hover:bg-rose-500 text-white cursor-pointer shadow-rose-950/50'
              : 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-300 dark:border-slate-700'
            }`}
        >
          <Ban className="w-3.5 h-3.5" />
          <span>Confirm Exclusion</span>
        </button>
      </div>
    </Modal>
  );
}

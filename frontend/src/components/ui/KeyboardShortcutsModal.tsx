import React from 'react';
import { Modal } from './Modal';
import { Command, CheckCircle, XCircle, HelpCircle, ArrowRight, ArrowLeft } from 'lucide-react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  const shortcuts = [
    { key: 'I', label: 'Include', desc: 'Accept study into systematic review synthesis', icon: CheckCircle, color: 'text-emerald-400' },
    { key: 'E', label: 'Exclude', desc: 'Exclude study (prompts for mandatory reason)', icon: XCircle, color: 'text-rose-400' },
    { key: 'M', label: 'Maybe', desc: 'Flag for secondary review or ambiguous eligibility', icon: HelpCircle, color: 'text-amber-400' },
    { key: 'N', label: 'Next Record', desc: 'Navigate forward in screening queue', icon: ArrowRight, color: 'text-slate-300' },
    { key: 'P', label: 'Previous Record', desc: 'Navigate backward in screening queue', icon: ArrowLeft, color: 'text-slate-300' },
    { key: '?', label: 'Shortcuts Help', desc: 'Open this hotkey reference modal', icon: Command, color: 'text-brand-400' }
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Keyboard Shortcuts"
      description="Accelerate your systematic abstract screening without leaving the keyboard."
    >
      <div className="space-y-3">
        {shortcuts.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.key}
              className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800"
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${s.color}`} />
                <div>
                  <div className="text-xs font-semibold text-slate-200">{s.label}</div>
                  <div className="text-[11px] text-slate-400">{s.desc}</div>
                </div>
              </div>
              <kbd className="px-2.5 py-1 text-xs font-mono font-bold text-slate-100 bg-slate-800 border border-slate-700 rounded shadow-inner">
                {s.key}
              </kbd>
            </div>
          );
        })}
      </div>
      <div className="text-center pt-2 text-xs text-slate-400">
        Press <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">Esc</kbd> to close.
      </div>
    </Modal>
  );
}

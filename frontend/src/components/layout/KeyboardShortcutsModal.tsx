import React from "react";
import { Modal, Button } from "../ui";

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SHORTCUTS_LIST = [
  {
    keys: ["Ctrl", "K"],
    altKeys: ["⌘", "K"],
    description: "Open Global AI Command Center",
    category: "AI & Search",
  },
  {
    keys: ["/"],
    description: "Focus search / command bar",
    category: "AI & Search",
  },
  {
    keys: ["G", "O"],
    description: "Navigate to Command Overview (/dashboard)",
    category: "Navigation",
  },
  {
    keys: ["G", "C"],
    description: "Navigate to Check-In Desk (/checkin)",
    category: "Navigation",
  },
  {
    keys: ["G", "M"],
    description: "Navigate to Merchandise Counter (/merchandise)",
    category: "Navigation",
  },
  {
    keys: ["G", "R"],
    description: "Navigate to Reports Catalog (/reports)",
    category: "Navigation",
  },
  {
    keys: ["?"],
    description: "Toggle this Keyboard Shortcuts Help Overlay",
    category: "Help",
  },
  {
    keys: ["Esc"],
    description: "Close active modal, drawer, or dropdown",
    category: "General",
  },
];

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="FestOS Keyboard Shortcuts"
      size="md"
    >
      <div className="space-y-4" data-testid="keyboard-shortcuts-modal">
        <p className="text-xs text-slate-400">
          Navigate and command FestOS under live event pressure using rapid keyboard chords.
        </p>

        <div className="space-y-3">
          {SHORTCUTS_LIST.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-lg border border-slate-800 bg-slate-900/60 text-xs"
            >
              <div className="text-slate-200 font-medium">
                {item.description}
              </div>

              <div className="flex items-center gap-1 font-mono">
                {item.altKeys && (
                  <>
                    {item.altKeys.map((k, i) => (
                      <kbd
                        key={i}
                        className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-[11px] text-slate-300 font-bold"
                      >
                        {k}
                      </kbd>
                    ))}
                    <span className="text-slate-500 text-[10px] mx-1">or</span>
                  </>
                )}
                {item.keys.map((k, i) => (
                  <kbd
                    key={i}
                    className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-[11px] text-slate-300 font-bold"
                  >
                    {k}
                  </kbd>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end pt-2 border-t border-slate-800">
          <Button variant="outline" size="sm" onClick={onClose}>
            Got it (Esc)
          </Button>
        </div>
      </div>
    </Modal>
  );
};

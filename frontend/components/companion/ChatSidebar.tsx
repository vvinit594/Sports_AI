"use client";

import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { useCompanion } from "@/hooks/useCompanion";

export function ChatSidebar() {
  const {
    conversations,
    active,
    newConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
    clearAll,
  } = useCompanion();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--ink-2)]">
      <div className="border-b border-white/10 p-4">
        <Button fullWidth onClick={newConversation}>
          <Plus size={16} aria-hidden />
          New conversation
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {conversations.length === 0 ? (
          <p className="px-2 text-sm text-muted">No conversations yet.</p>
        ) : (
          <ul className="space-y-1">
            {conversations.map((conversation) => {
              const selected = conversation.id === active?.id;
              return (
                <li key={conversation.id}>
                  {editingId === conversation.id ? (
                    <form
                      className="rounded-2xl border border-[var(--red)] bg-black/40 p-2"
                      onSubmit={(event) => {
                        event.preventDefault();
                        renameConversation(conversation.id, draft);
                        setEditingId(null);
                      }}
                    >
                      <label className="sr-only" htmlFor={`rename-${conversation.id}`}>
                        Rename conversation
                      </label>
                      <input
                        id={`rename-${conversation.id}`}
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        className="h-9 w-full rounded-xl border border-white/10 bg-black/40 px-3 text-sm"
                        autoFocus
                      />
                      <div className="mt-2 flex gap-2">
                        <button type="submit" className="text-xs text-[var(--electric)]">
                          Save
                        </button>
                        <button
                          type="button"
                          className="text-xs text-muted"
                          onClick={() => setEditingId(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div
                      className={`flex items-start gap-2 rounded-2xl px-3 py-2 ${
                        selected
                          ? "border border-[var(--red)] bg-[var(--red)]/10"
                          : "border border-transparent hover:bg-white/5"
                      }`}
                    >
                      <button
                        type="button"
                        className="min-w-0 flex-1 text-left"
                        onClick={() => selectConversation(conversation.id)}
                      >
                        <span className="block truncate text-sm font-medium">
                          {conversation.title}
                        </span>
                        <span className="block text-[11px] text-muted">
                          {new Date(conversation.updatedAt).toLocaleString()}
                        </span>
                      </button>
                      <button
                        type="button"
                        className="text-[11px] text-white/50 hover:text-white"
                        onClick={() => {
                          setEditingId(conversation.id);
                          setDraft(conversation.title);
                        }}
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        aria-label={`Delete ${conversation.title}`}
                        className="text-white/40 hover:text-red-300"
                        onClick={() => deleteConversation(conversation.id)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <div className="border-t border-white/10 p-4">
        {confirmClear ? (
          <div className="space-y-2 text-sm">
            <p>Clear every conversation on this device?</p>
            <div className="flex gap-2">
              <Button
                variant="primary"
                onClick={() => {
                  clearAll();
                  setConfirmClear(false);
                }}
              >
                Confirm
              </Button>
              <Button variant="ghost" onClick={() => setConfirmClear(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="outline" fullWidth onClick={() => setConfirmClear(true)}>
            Clear all
          </Button>
        )}
      </div>
    </div>
  );
}

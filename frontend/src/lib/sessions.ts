/** Demo conversation ids per customer, kept in localStorage and read with useSyncExternalStore. */

const KEY = "kaampilot.sessions";
const EVENT = "kaampilot:sessions";
const EMPTY = "{}";

function newConversationId(customerId: string) {
  return `c_${customerId}_${Math.random().toString(36).slice(2, 10)}`;
}

function read(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? EMPTY);
  } catch {
    return {};
  }
}

function write(sessions: Record<string, string>) {
  localStorage.setItem(KEY, JSON.stringify(sessions));
  window.dispatchEvent(new Event(EVENT));
}

export function subscribe(callback: () => void) {
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

/** Snapshot as a string so React can compare it cheaply. Creates missing ids on first read. */
export function snapshotFor(customerIds: string[]) {
  return () => {
    const sessions = read();
    const missing = customerIds.filter((id) => !sessions[id]);
    if (missing.length) {
      for (const id of missing) sessions[id] = newConversationId(id);
      localStorage.setItem(KEY, JSON.stringify(sessions));
    }
    return localStorage.getItem(KEY) ?? EMPTY;
  };
}

export const serverSnapshot = () => EMPTY;

export function resetConversation(customerId: string) {
  write({ ...read(), [customerId]: newConversationId(customerId) });
}

"use client";

/**
 * Offline draft store + sync queue (IndexedDB).
 *
 * Drafts remember the server row_version they were based on. On reconnect the
 * queue replays each draft; a 409 CONFLICT_STALE_VERSION response is kept for
 * the conflict-resolution screen — the server is never silently overwritten.
 * No authentication data is ever stored here.
 */

const DB_NAME = "drukagrilink-offline";
const STORE = "drafts";

export interface OfflineDraft {
  id: string; // local uuid
  kind: "harvest_listing_update" | "harvest_listing_create" | "collection_record";
  path: string;
  method: "POST" | "PATCH";
  payload: Record<string, unknown>;
  baseRowVersion?: number;
  createdAt: string;
  status: "queued" | "conflict" | "failed";
  conflict?: { serverState: Record<string, unknown>; serverRowVersion: number };
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) {
        request.result.createObjectStore(STORE, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore<T>(
  mode: IDBTransactionMode,
  fn: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await openDb();
  return new Promise<T>((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const request = fn(tx.objectStore(STORE));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function saveDraft(draft: OfflineDraft): Promise<void> {
  await withStore("readwrite", (store) => store.put(draft));
}

export async function listDrafts(): Promise<OfflineDraft[]> {
  return withStore("readonly", (store) => store.getAll() as IDBRequest<OfflineDraft[]>);
}

export async function deleteDraft(id: string): Promise<void> {
  await withStore("readwrite", (store) => store.delete(id));
}

/** Replay queued drafts. Returns ids that conflicted (kept for resolution). */
export async function syncDrafts(
  apiFn: (path: string, options: { method: string; body: unknown }) => Promise<unknown>,
): Promise<{ synced: number; conflicts: number }> {
  const drafts = await listDrafts();
  let synced = 0;
  let conflicts = 0;
  for (const draft of drafts) {
    if (draft.status === "conflict") {
      conflicts += 1;
      continue;
    }
    try {
      await apiFn(draft.path, {
        method: draft.method,
        body: { ...draft.payload, expected_row_version: draft.baseRowVersion },
      });
      await deleteDraft(draft.id);
      synced += 1;
    } catch (error) {
      const apiError = error as {
        status?: number;
        error?: {
          code?: string;
          server_state?: Record<string, unknown>;
          server_row_version?: number;
        };
      };
      if (apiError.status === 409 && apiError.error?.code === "CONFLICT_STALE_VERSION") {
        draft.status = "conflict";
        draft.conflict = {
          serverState: apiError.error.server_state ?? {},
          serverRowVersion: apiError.error.server_row_version ?? 0,
        };
        await saveDraft(draft);
        conflicts += 1;
      }
      // network failures: leave queued for automatic retry on next sync
    }
  }
  return { synced, conflicts };
}

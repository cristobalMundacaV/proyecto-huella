export const evidenceDetailPath = (evidenceId, workId) => workId
  ? `/obras/${encodeURIComponent(workId)}/evidencias/${encodeURIComponent(evidenceId)}`
  : `/datos/evidencias/${encodeURIComponent(evidenceId)}`;

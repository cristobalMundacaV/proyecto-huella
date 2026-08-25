export function createOrganizationRequestTracker() {
  let generation = 0;
  let controller = null;

  return {
    start() {
      controller?.abort();
      controller = new AbortController();
      generation += 1;
      return { requestId: generation, signal: controller.signal };
    },

    isCurrent(requestId) {
      return requestId === generation;
    },

    invalidate() {
      controller?.abort();
      controller = null;
      generation += 1;
    },
  };
}

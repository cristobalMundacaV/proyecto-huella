import assert from "node:assert/strict";
import test from "node:test";

import { createOrganizationRequestTracker } from "./organizationRequestTracker.js";

test("una nueva resolución invalida y aborta la anterior", () => {
  const tracker = createOrganizationRequestTracker();
  const first = tracker.start();
  const second = tracker.start();

  assert.equal(first.signal.aborted, true);
  assert.equal(second.signal.aborted, false);
  assert.equal(tracker.isCurrent(first.requestId), false);
  assert.equal(tracker.isCurrent(second.requestId), true);
});

test("invalidar una resolución impide que una respuesta tardía actualice estado", () => {
  const tracker = createOrganizationRequestTracker();
  const request = tracker.start();

  tracker.invalidate();

  assert.equal(request.signal.aborted, true);
  assert.equal(tracker.isCurrent(request.requestId), false);
});

test("diez resoluciones consecutivas dejan vigente únicamente la última", () => {
  const tracker = createOrganizationRequestTracker();
  const requests = Array.from({ length: 10 }, () => tracker.start());
  const latest = requests.at(-1);

  requests.slice(0, -1).forEach((request) => {
    assert.equal(request.signal.aborted, true);
    assert.equal(tracker.isCurrent(request.requestId), false);
  });
  assert.equal(latest.signal.aborted, false);
  assert.equal(tracker.isCurrent(latest.requestId), true);
});

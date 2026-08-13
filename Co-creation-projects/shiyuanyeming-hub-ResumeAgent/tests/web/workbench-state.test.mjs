import test from "node:test";
import assert from "node:assert/strict";

import {
  baseSelection,
  createGenerationGate,
  storeBaseSelection,
} from "../../resume_agent/web/workbench-state.js";


test("generation gates reject stale async commits", () => {
  const gate = createGenerationGate();
  const first = gate.next();
  const second = gate.next();

  assert.equal(gate.isCurrent(first), false);
  assert.equal(gate.isCurrent(second), true);
  assert.equal(gate.current(), second);
});


test("base selections preserve only experience, session, and version ids", () => {
  const state = { factBaseId: "base-1", experienceId: "legacy-experience" };
  assert.deepEqual(baseSelection(state, "base-1"), { experienceId: "legacy-experience" });

  storeBaseSelection(state, "base-1", {
    experienceId: "experience-1",
    sessionId: "session-1",
    versionId: "version-1",
    candidateAnswer: "private answer",
    markdown: "private draft",
  });

  assert.deepEqual(baseSelection(state, "base-1"), {
    experienceId: "experience-1",
    sessionId: "session-1",
    versionId: "version-1",
  });
  assert.equal("candidateAnswer" in state.baseSelections["base-1"], false);
  assert.equal("markdown" in state.baseSelections["base-1"], false);
});

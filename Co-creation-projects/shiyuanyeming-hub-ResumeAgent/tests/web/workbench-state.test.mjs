import test from "node:test";
import assert from "node:assert/strict";

import {
  baseSelection,
  createGenerationGate,
  createTransitionGate,
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


test("transition gates keep the latest intent active until it finishes", () => {
  const gate = createTransitionGate();
  const first = gate.begin();
  const second = gate.begin();

  assert.equal(gate.isTransitioning(), true);
  assert.equal(gate.finish(first), false);
  assert.equal(gate.isTransitioning(), true);
  assert.equal(gate.finish(second), true);
  assert.equal(gate.isTransitioning(), false);
});


test("cancel invalidates an in-flight transition immediately", () => {
  const gate = createTransitionGate();
  const pending = gate.begin();

  gate.cancel();

  assert.equal(gate.isCurrent(pending), false);
  assert.equal(gate.finish(pending), false);
  assert.equal(gate.isTransitioning(), false);
});


test("preview generation rejects an older response for the same version", () => {
  const previewGate = createGenerationGate();
  const committed = [];
  const firstPreview = previewGate.next();
  const refreshedPreview = previewGate.next();

  if (previewGate.isCurrent(refreshedPreview)) committed.push("new-style-preview");
  if (previewGate.isCurrent(firstPreview)) committed.push("old-style-preview");

  assert.deepEqual(committed, ["new-style-preview"]);
});


test("language generation makes the last rapid intent win", () => {
  const languageGate = createGenerationGate();
  let committedLocale = "zh";
  const japaneseIntent = languageGate.next();
  const englishIntent = languageGate.next();

  if (languageGate.isCurrent(englishIntent)) committedLocale = "en";
  if (languageGate.isCurrent(japaneseIntent)) committedLocale = "ja";

  assert.equal(committedLocale, "en");
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

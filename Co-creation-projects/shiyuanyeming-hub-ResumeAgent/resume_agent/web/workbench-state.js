const SELECTION_KEYS = ["experienceId", "sessionId", "versionId"];

export function createGenerationGate() {
  let generation = 0;
  return {
    next() {
      generation += 1;
      return generation;
    },
    current() {
      return generation;
    },
    isCurrent(candidate) {
      return candidate === generation;
    },
  };
}

export function baseSelection(state, baseId) {
  const saved = state.baseSelections?.[baseId];
  if (saved) return { ...saved };
  if (state.factBaseId !== baseId) return {};
  return Object.fromEntries(
    SELECTION_KEYS
      .filter((key) => typeof state[key] === "string" && state[key])
      .map((key) => [key, state[key]]),
  );
}

export function storeBaseSelection(state, baseId, selection) {
  const safeSelection = Object.fromEntries(
    SELECTION_KEYS
      .filter((key) => typeof selection[key] === "string" && selection[key])
      .map((key) => [key, selection[key]]),
  );
  state.baseSelections = {
    ...(state.baseSelections || {}),
    [baseId]: safeSelection,
  };
  return safeSelection;
}

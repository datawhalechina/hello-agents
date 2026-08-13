import test from "node:test";
import assert from "node:assert/strict";

import {
  ApiError,
  createApi,
  sanitizeUiState,
} from "../../resume_agent/web/api.js";


test("createFactBase posts the target contract", async () => {
  const calls = [];
  const api = createApi(async (url, init) => {
    calls.push([url, init]);
    return new Response(
      JSON.stringify({ id: "base-1", target: { role: "分析师" }, experiences: [] }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    );
  });

  await api.createFactBase({
    role: "分析师",
    country: "日本",
    languages: ["zh", "ja", "en"],
  });

  assert.equal(calls[0][0], "/fact-bases");
  assert.equal(calls[0][1].method, "POST");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    target: {
      role: "分析师",
      country: "日本",
      languages: ["zh", "ja", "en"],
    },
  });
});


test("addExperience posts only organization and role", async () => {
  const calls = [];
  const api = createApi(async (url, init) => {
    calls.push([url, init]);
    return new Response(JSON.stringify({ id: "base-1" }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  });

  await api.addExperience("base-1", {
    organization: "星河科技",
    role: "数据分析实习生",
  });

  assert.equal(calls[0][0], "/fact-bases/base-1/experiences");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    organization: "星河科技",
    role: "数据分析实习生",
  });
});


test("503 becomes a safe unavailable error", async () => {
  const api = createApi(async () => new Response(
    JSON.stringify({ detail: "secret provider response" }),
    { status: 503, headers: { "Content-Type": "application/json" } },
  ));

  await assert.rejects(
    api.health(),
    (error) => error instanceof ApiError
      && error.category === "unavailable"
      && !error.message.includes("secret"),
  );
});


test("network failures become safe transport errors", async () => {
  const api = createApi(async () => {
    throw new TypeError("private host name");
  });

  await assert.rejects(
    api.listFactBases(),
    (error) => error instanceof ApiError
      && error.category === "transport"
      && !error.message.includes("private"),
  );
});


test("sanitizeUiState keeps selection fields and drops credentials", () => {
  assert.deepEqual(
    sanitizeUiState({
      factBaseId: "base-1",
      experienceId: "experience-1",
      sessionId: "session-1",
      versionId: "version-1",
      locale: "ja",
      tab: "facts",
      apiKey: "secret",
      candidateAnswer: "private answer",
    }),
    {
      factBaseId: "base-1",
      experienceId: "experience-1",
      sessionId: "session-1",
      versionId: "version-1",
      locale: "ja",
      tab: "facts",
    },
  );
});


test("interview methods use exact session contracts", async () => {
  const calls = [];
  const api = createApi(async (url, init = {}) => {
    calls.push([url, init]);
    return new Response(JSON.stringify({ id: "result" }), {
      status: init.method === "POST" && url === "/sessions" ? 201 : 200,
      headers: { "Content-Type": "application/json" },
    });
  });

  await api.listSessions("base-1", "experience-1");
  await api.createSession("base-1", "experience-1");
  await api.getSession("session-1");
  await api.currentQuestion("session-1");
  await api.answer("session-1", "我搭建了看板");
  await api.confirmProposal("session-1", "proposal-1");
  await api.rejectProposal("session-1", "proposal-2");
  await api.recordUnknown("session-1", "result");

  assert.equal(calls[0][0], "/fact-bases/base-1/sessions?experience_id=experience-1");
  assert.deepEqual(JSON.parse(calls[1][1].body), {
    fact_base_id: "base-1",
    active_experience_id: "experience-1",
  });
  assert.equal(calls[2][0], "/sessions/session-1");
  assert.equal(calls[3][0], "/sessions/session-1/current-question");
  assert.deepEqual(JSON.parse(calls[4][1].body), { message: "我搭建了看板" });
  assert.equal(calls[5][0], "/sessions/session-1/proposals/proposal-1/confirm");
  assert.equal(calls[6][0], "/sessions/session-1/proposals/proposal-2/reject");
  assert.deepEqual(JSON.parse(calls[7][1].body), { dimension: "result" });
});


test("fact methods update profile and request quality", async () => {
  const calls = [];
  const api = createApi(async (url, init = {}) => {
    calls.push([url, init]);
    return new Response(JSON.stringify({}), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  const profile = {
    name: "王明",
    email: "wang@example.com",
    phone: "13800000000",
    location: "东京",
    links: ["https://example.com"],
  };

  await api.updateProfile("base-1", profile);
  await api.experienceQuality("base-1", "experience-1");

  assert.equal(calls[0][1].method, "PATCH");
  assert.deepEqual(JSON.parse(calls[0][1].body), profile);
  assert.equal(calls[1][0], "/fact-bases/base-1/experiences/experience-1/quality");
});

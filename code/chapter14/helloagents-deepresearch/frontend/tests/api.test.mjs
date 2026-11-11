import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createServer } from "vite";

let vite;
let runResearchStream;

before(async () => {
  vite = await createServer({
    configFile: false,
    optimizeDeps: { noDiscovery: true },
    server: { middlewareMode: true, watch: null },
    appType: "custom"
  });
  ({ runResearchStream } = await vite.ssrLoadModule("/src/services/api.ts"));
});

after(async () => {
  await vite?.close();
});

function respondWith(t, chunks) {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    }
  });
  t.mock.method(globalThis, "fetch", async () => new Response(body));
}

test("rejects EOF before a terminal research event", async (t) => {
  respondWith(t, ['data: {"type":"status","message":"searching"}\n\n']);
  const events = [];

  await assert.rejects(
    runResearchStream({ topic: "example" }, (event) => events.push(event)),
    /研究响应中断/
  );
  assert.deepEqual(events, [{ type: "status", message: "searching" }]);
});

test("does not accept an unterminated done frame at EOF", async (t) => {
  respondWith(t, ['data: {"type":"done"}\n']);
  const events = [];

  await assert.rejects(
    runResearchStream({ topic: "example" }, (event) => events.push(event)),
    /研究响应中断/
  );
  assert.deepEqual(events, []);
});

test("delivers a terminal event split across reads", async (t) => {
  for (const terminal of [
    { type: "done" },
    { type: "error", detail: "search failed" }
  ]) {
    await t.test(terminal.type, async (caseContext) => {
      respondWith(caseContext, [
        'data: {"type":"status"}\n\ndata: ',
        JSON.stringify(terminal) + "\n",
        "\n"
      ]);
      const events = [];

      await runResearchStream({ topic: "example" }, (event) => events.push(event));
      assert.deepEqual(events, [{ type: "status" }, terminal]);
    });
  }
});

export function createApi(fetchImpl = globalThis.fetch) {
  return { fetch: fetchImpl };
}

import "@testing-library/jest-dom/vitest";

import { afterAll, afterEach, beforeAll } from "vitest";

import { resetCars } from "./src/mocks/handlers";
import { server } from "./src/mocks/server";

/**
 * jsdom supplies its own `AbortSignal`, but the `fetch` available under Node is
 * undici's, which rejects any signal that is not a Node `AbortSignal`. Apollo
 * attaches one for request cancellation, so every query otherwise fails in
 * jsdom with "Expected signal to be an instance of AbortSignal".
 *
 * The wrapper has to be installed *after* `server.listen()`, because MSW
 * replaces `globalThis.fetch` with its own interceptor at that point and the
 * signal has to be gone before that interceptor builds a Request.
 *
 * Dropping the signal costs request cancellation, which no test depends on.
 * The workaround lives here rather than in the Apollo client so application
 * code stays free of test-environment concerns.
 */
function stripAbortSignal(): void {
  const intercepted = globalThis.fetch;
  globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    if (init && "signal" in init) {
      const { signal: _cancellation, ...rest } = init;
      return intercepted(input, rest);
    }
    return intercepted(input, init);
  }) as typeof globalThis.fetch;
}

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
  stripAbortSignal();
});

afterEach(() => {
  server.resetHandlers();
  resetCars();
});

afterAll(() => server.close());

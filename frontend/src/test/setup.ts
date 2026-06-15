import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// No real network in unit tests — fail loudly if a test forgets to mock.
if (!globalThis.fetch) {
  globalThis.fetch = vi.fn(() => Promise.reject(new Error("fetch not mocked in test"))) as unknown as typeof fetch;
}

afterEach(() => {
  cleanup();
});

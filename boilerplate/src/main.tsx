import { ApolloProvider } from "@apollo/client/react";
import CssBaseline from "@mui/material/CssBaseline";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { createApolloClient } from "./apollo/client";
import { App } from "./App";

function render() {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <ApolloProvider client={createApolloClient()}>
        <CssBaseline />
        <App />
      </ApolloProvider>
    </StrictMode>,
  );
}

/**
 * Start the mock API before rendering, so the first query is intercepted.
 *
 * If the Service Worker cannot register - some sandboxed or restricted
 * browsers refuse to fetch it - the app still renders. GraphQL requests will
 * then fail visibly rather than the whole page silently staying blank, which
 * is far easier to diagnose.
 */
async function start() {
  try {
    const { worker } = await import("./mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass" });
  } catch (error) {
    console.error("[mock api] could not start; requests will not be intercepted", error);
  }
  render();
}

void start();

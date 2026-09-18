/**
 * File: main.tsx
 * Purpose: Mount the React dashboard into the semantic HTML document shell.
 * Symbols and line locations: see docs/code-index.md; root is the required DOM mount element.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("Dashboard root element is missing");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

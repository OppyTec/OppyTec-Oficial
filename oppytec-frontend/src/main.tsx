import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";
import { getRuntimeEnv } from "@/shared/config/env";

// Validación Fail-Fast en el milisegundo 0 al inicializar el bundle en el navegador
getRuntimeEnv();

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root container '#root' not found in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);

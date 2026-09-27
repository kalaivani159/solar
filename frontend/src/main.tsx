import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import "./index.css";
import App from "./App.tsx";
import { FilterProvider } from "./state/filters.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <FilterProvider>
        <App />
      </FilterProvider>
    </BrowserRouter>
  </StrictMode>,
);

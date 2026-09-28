import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const manifest = document.getElementById("foundations-manifest");
if (manifest) {
  const path = window.location.pathname || "/";
  if (path.startsWith("/admin")) {
    manifest.setAttribute("href", "/admin-manifest.json");
  } else if (path.startsWith("/hr")) {
    manifest.setAttribute("href", "/hr-manifest.json");
  }
}

window.addEventListener("error", (event) => {
  if (
    event.error instanceof DOMException &&
    event.error.name === "DataCloneError" &&
    event.message &&
    event.message.includes("PerformanceServerTiming")
  ) {
    event.stopImmediatePropagation();
    event.preventDefault();
  }
}, true);

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/service-worker.js');
      await registration.update();
    } catch (error) {
      console.warn('Foundations app install service unavailable:', error);
    }
  });
}

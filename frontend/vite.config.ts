import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Local dev only, behind Docker: lets it accept requests via any
    // container-network hostname (e.g. host.docker.internal from an
    // automated browser test), not just localhost.
    allowedHosts: true,
  },
});

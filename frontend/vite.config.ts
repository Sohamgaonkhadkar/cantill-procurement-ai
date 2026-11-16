import path from "node:path";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
const root = path.dirname(fileURLToPath(import.meta.url));
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(root, "src") } },
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api": process.env.CORVO_DEV_API_PROXY ?? "http://127.0.0.1:8000",
      "/health": process.env.CORVO_DEV_API_PROXY ?? "http://127.0.0.1:8000",
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          three: [
            "three",
            "@react-three/fiber",
            "@react-three/drei",
            "@react-three/postprocessing",
          ],
        },
      },
    },
  },
});

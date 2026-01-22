import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),
      "@shared": path.resolve(import.meta.dirname, "shared"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      '/get-routes': { target: 'http://localhost:5000', changeOrigin: true, secure: false },
      '/reverse-geocode': { target: 'http://localhost:5000', changeOrigin: true, secure: false },
      '/health': { target: 'http://localhost:5000', changeOrigin: true, secure: false },
    },
  },
});

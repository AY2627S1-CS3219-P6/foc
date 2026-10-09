import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "^/v1/(orders|order-creations|admin/orders)([/?]|$)": {
        target: "http://localhost:8002",
        changeOrigin: true,
      },
      "/v1": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "^/api/v1/(categories|suppliers|admin/suppliers)([/?]|$)": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});

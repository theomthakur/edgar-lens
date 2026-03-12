import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brandInk: "#101828",
        brandMist: "#f5f7fa",
        brandSky: "#7dd3fc",
        brandSlate: "#475467",
      },
    },
  },
  plugins: [],
};

export default config;

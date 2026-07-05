/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        app: "var(--bg)",
        panel: "var(--panel)",
        panel2: "var(--panel2)",
        hair: "var(--hair)",
        chip: "var(--chip-bg)",
        line: { DEFAULT: "var(--border)", 2: "var(--border2)", 3: "var(--border3)" },
        head: { DEFAULT: "var(--head-bg)", line: "var(--head-border)" },
        fg: { DEFAULT: "var(--text)", 2: "var(--text2)" },
        sub: "var(--sub)",
        muted: "var(--muted)",
        accent: {
          DEFAULT: "var(--accent)",
          text: "var(--accent-text)",
          ink: "var(--accent-ink)",
          soft: "var(--accent-bg)",
          line: "var(--accent-border)",
        },
        score: {
          green: { DEFAULT: "var(--sc-green-fg)", soft: "var(--sc-green-bg)", line: "var(--sc-green-border)" },
          amber: { DEFAULT: "var(--sc-amber-fg)", soft: "var(--sc-amber-bg)", line: "var(--sc-amber-border)" },
          red: { DEFAULT: "var(--sc-red-fg)", soft: "var(--sc-red-bg)", line: "var(--sc-red-border)" },
          none: { DEFAULT: "var(--sc-null-fg)", soft: "var(--sc-null-bg)", line: "var(--sc-null-border)" },
        },
        pos: { DEFAULT: "var(--pos)", soft: "var(--pos-bg)", line: "var(--pos-border)" },
        neg: { DEFAULT: "var(--neg)", soft: "var(--neg-bg)", line: "var(--neg-border)" },
        warn: { DEFAULT: "var(--warn)", soft: "var(--warn-bg)", line: "var(--warn-border)" },
        "src-him": { dot: "var(--src-him-dot)", text: "var(--src-him-text)" },
        "src-rem": { dot: "var(--src-rem-dot)", text: "var(--src-rem-text)" },
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "none" },
        },
        "slide-in": {
          from: { transform: "translateX(100%)" },
          to: { transform: "none" },
        },
        "slide-out": {
          from: { transform: "none" },
          to: { transform: "translateX(100%)" },
        },
        "backdrop-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "backdrop-out": {
          from: { opacity: "1" },
          to: { opacity: "0" },
        },
      },
      animation: {
        "fade-in": "fade-in .25s ease",
        "slide-in": "slide-in .45s cubic-bezier(0.32, 0.72, 0, 1)",
        "slide-out": "slide-out .4s cubic-bezier(0.32, 0.72, 0, 1) forwards",
        "backdrop-in": "backdrop-in .35s ease",
        "backdrop-out": "backdrop-out .35s ease forwards",
      },
    },
  },
  plugins: [],
};

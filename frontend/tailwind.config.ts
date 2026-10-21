import type { Config } from "tailwindcss";

/**
 * Margin design tokens. One ink, warm paper, a highlighter for evidence, and three support states.
 * Colours are CSS variables (see globals.css) so dark mode is a token swap, not a second stylesheet.
 */
const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  // Absolute, so class scanning works regardless of the directory the dev server was started from.
  content: [`${__dirname}/src/**/*.{ts,tsx}`],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        paper: v("paper"),
        surface: v("surface"),
        sunk: v("sunk"),
        line: v("line"),
        ink: { DEFAULT: v("ink"), 2: v("ink-2"), 3: v("ink-3") },
        accent: { DEFAULT: v("accent"), soft: v("accent-soft"), ink: v("accent-ink") },
        mark: v("mark"),
        ok: { DEFAULT: v("ok"), soft: v("ok-soft") },
        warn: { DEFAULT: v("warn"), soft: v("warn-soft") },
        bad: { DEFAULT: v("bad"), soft: v("bad-soft") },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": ["11px", "16px"],
      },
      borderRadius: {
        card: "14px",
      },
      boxShadow: {
        card: "0 1px 0 rgb(var(--line) / 1), 0 1px 3px rgb(0 0 0 / 0.04)",
        lift: "0 12px 32px -12px rgb(0 0 0 / 0.18)",
        page: "0 1px 2px rgb(0 0 0 / 0.06), 0 8px 24px -8px rgb(0 0 0 / 0.12)",
      },
      keyframes: {
        shimmer: { "100%": { transform: "translateX(100%)" } },
        rise: { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: {
        rise: "rise .35s cubic-bezier(.2,.8,.2,1) both",
      },
    },
  },
  plugins: [],
} satisfies Config;

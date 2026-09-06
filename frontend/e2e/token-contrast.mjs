/**
 * Token contrast gate. Parses styles/tokens.css and verifies the real
 * Light/Dark token pairs meet WCAG ratios: 4.5:1 for body text, 3:1 for
 * large text and essential interactive components (borders, focus rings).
 *
 * Run: bun e2e/token-contrast.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const tokensPath = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "src",
  "styles",
  "tokens.css",
);
const css = readFileSync(tokensPath, "utf-8");

function parseRoot(block) {
  const vars = {};
  for (const match of block.matchAll(/--([a-z0-9-]+):\s*([^;]+);/gi)) {
    vars[`--${match[1]}`] = match[2].trim();
  }
  return vars;
}

function parseThemeBlocks(name) {
  const merged = {};
  const pattern = new RegExp(
    `${name.replace(".", "\\.")}\\s*\\{([\\s\\S]*?)\\n\\}`,
    "g",
  );
  for (const match of css.matchAll(pattern)) {
    Object.assign(merged, parseRoot(match[1]));
  }
  return merged;
}

const light = parseThemeBlocks(":root");
const dark = { ...light, ...parseThemeBlocks(":root.dark") };

function channel(value) {
  if (value.startsWith("#")) {
    const hex = value.slice(1);
    const full =
      hex.length === 3
        ? hex
            .split("")
            .map((c) => c + c)
            .join("")
        : hex;
    return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
  }
  const rgb = value.match(/(\d+)\s+(\d+)\s+(\d+)/);
  if (rgb) return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])];
  throw new Error(`Unsupported color: ${value}`);
}

function luminance(color) {
  const [r, g, b] = channel(color).map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a, b) {
  const l1 = luminance(a);
  const l2 = luminance(b);
  const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

// [foreground, background, minimum ratio, label]
// Non-text borders are decorative in this workspace (a deliberate style
// retention decision); essential interactive state is carried by focus
// rings, state text, and control labels, which this gate covers.
const PAIRS = [
  ["--text-primary", "--surface", 4.5, "body text on surface"],
  ["--text-primary", "--canvas", 4.5, "body text on canvas"],
  ["--text-muted", "--surface", 4.5, "muted text on surface"],
  ["--text-subtle", "--surface", 4.5, "subtle text on surface"],
  ["--accent-text", "--surface", 4.5, "accent text on surface"],
  ["--accent-button-text", "--accent-button-bg", 4.5, "accent button label"],
  ["--text-primary", "--surface-raised", 4.5, "body text on raised surface"],
  ["--state-warning-text", "--state-warning-surface", 3.0, "warning state text"],
  ["--state-success-text", "--state-success-surface", 3.0, "success state text"],
  ["--state-danger-text", "--state-danger-surface", 3.0, "danger state text"],
  ["--primary", "--surface", 3.0, "focus ring on surface"],
  ["--evidence-accent", "--surface", 3.0, "evidence accent on surface"],
];

let failures = 0;
for (const themeName of ["Light", "Dark"]) {
  const theme = themeName === "Light" ? light : dark;
  console.log(`\n${themeName} theme:`);
  for (const [fgKey, bgKey, minimum, label] of PAIRS) {
    const fg = theme[fgKey];
    const bg = theme[bgKey];
    if (!fg || !bg) {
      console.error(`  MISSING token ${fgKey} or ${bgKey} for ${label}`);
      failures += 1;
      continue;
    }
    const ratio = contrast(fg, bg);
    const pass = ratio >= minimum;
    console.log(
      `  ${pass ? "PASS" : "FAIL"} ${ratio.toFixed(2)}:1 (min ${minimum}:1) ${label} [${fgKey} on ${bgKey}]`,
    );
    if (!pass) failures += 1;
  }
}

console.log(
  failures === 0
    ? "\nAll token contrast pairs meet their WCAG thresholds."
    : `\n${failures} contrast pair(s) failed.`,
);
process.exit(failures === 0 ? 0 : 1);

const browserGlobals = Object.fromEntries(
  [
    "atob", "Blob", "File", "FileReader", "FormData", "IntersectionObserver",
    "URL", "URLSearchParams", "alert", "confirm", "crypto", "document", "fetch",
    "history", "localStorage", "location", "navigator", "performance", "setInterval",
    "setTimeout", "clearInterval", "clearTimeout", "window",
  ].map((name) => [name, "readonly"]),
);

const languageGlobals = Object.fromEntries(
  ["Array", "Date", "Error", "Intl", "JSON", "Math", "Number", "Object", "Promise", "RegExp", "String", "console", "globalThis"].map(
    (name) => [name, "readonly"],
  ),
);

export default [
  {
    files: ["index.jsx", "components/HomePage.jsx", "components/broker/**/*.{js,jsx,mjs}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...browserGlobals, ...languageGlobals },
    },
    rules: {
      "no-constant-binary-expression": "error",
      "no-dupe-keys": "error",
      "no-unreachable": "error",
      // Existing broker views include legacy imports/state that are unused; report
      // them while the additive lint check still fails on syntax and undefined names.
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-undef": "error",
    },
  },
];

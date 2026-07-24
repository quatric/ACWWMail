#!/usr/bin/env node
/*
 * Compile the .ksy files with the official Kaitai Struct compiler and report
 * per-language results.  Uses the JavaScript build, so no JVM is needed:
 *
 *     npm install kaitai-struct-compiler js-yaml
 *     node compile_ksy.js                 # check all languages, write nothing
 *     node compile_ksy.js -o out python   # emit Python parsers into ./out
 *
 * Note: kaitai-struct-compiler >= 0.11 exports the compiler object directly.
 * Older versions exported a constructor (`new KaitaiStructCompiler()`).
 */
const KSC = require("kaitai-struct-compiler");
const yaml = require("js-yaml");
const fs = require("fs");
const path = require("path");

const ALL_LANGS = [
  "python", "javascript", "java", "csharp", "cpp_stl", "go",
  "rust", "php", "ruby", "perl", "lua", "nim", "html",
];

const KSY = ["acww_forest_bbs.ksy", "acww_forest_mail.ksy"]
  .map((f) => path.join(__dirname, f));

const argv = process.argv.slice(2);
let outDir = null;
const i = argv.indexOf("-o");
if (i !== -1) {
  outDir = argv[i + 1];
  argv.splice(i, 2);
}
const langs = argv.length ? argv : ALL_LANGS;

if (outDir) fs.mkdirSync(outDir, { recursive: true });

(async () => {
  let bad = 0;
  for (const lang of langs) {
    const results = [];
    for (const f of KSY) {
      const spec = yaml.load(fs.readFileSync(f, "utf8"));
      try {
        const res = await KSC.compile(lang, spec, null, false);
        for (const [name, src] of Object.entries(res)) {
          if (outDir) fs.writeFileSync(path.join(outDir, name), src);
        }
        results.push(`${path.basename(f)}: ${Object.keys(res).length} file(s)`);
      } catch (e) {
        bad++;
        results.push(`${path.basename(f)}: FAIL ${e}`);
      }
    }
    console.log(`${lang.padEnd(12)} ${results.join("  |  ")}`);
  }
  console.log(bad ? `\n${bad} failure(s)` : "\nall targets compiled clean");
  process.exit(bad ? 1 : 0);
})();

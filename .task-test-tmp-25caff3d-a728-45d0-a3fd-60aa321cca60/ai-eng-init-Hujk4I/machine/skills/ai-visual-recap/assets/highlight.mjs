#!/usr/bin/env bun
// ai-visual-recap/assets/highlight.js — code colour for the recap artifact.
//
// The token classes are the blueprint's own — .c comment · .k keyword · .s string
// · .n number · .t type · .f call · .b strong — so a recap and the blueprint read
// the same and the CSS stays six lines. No dependency, no network, no runtime:
// run it while authoring and paste the output, so the artifact is static HTML that
// renders identically in every viewer, including one with JavaScript disabled.
//
//   bun highlight.js --lang ts excerpt.ts     → highlighted HTML on stdout
//   cat excerpt.ts | bun highlight.js --lang ts
//
// In a page it also colours every <pre data-lang="…"> on load, for artifacts that
// ship the script inline instead of pre-rendering the spans.
//
// A directory tree, a terminal transcript or plain output is NOT code: leave it
// un-highlighted (data-lang="text"), because colouring the wrong thing is noise.

const KEYWORDS =
  /\b(?:const|let|var|function|return|if|else|for|of|in|while|do|class|new|import|from|export|default|async|await|try|catch|finally|throw|typeof|instanceof|interface|type|extends|implements|public|private|protected|readonly|enum|switch|case|break|continue|yield|static|as|is|null|true|false|undefined|this|super|void|infer|keyof|satisfies|declare|namespace|def|elif|fi|then|done|esac|local|echo|exit|set|fi)\b/;

const TYPES =
  /\b(?:string|number|boolean|any|unknown|never|object|symbol|bigint|Array|Record|Promise|Map|Set|Date|JSON|Math|Object|String|Number|Boolean|Error|Bun|NodeJS|process|console)\b/;

/** Two comment dialects cover every language this recap ever quotes; a wrong
 *  dialect would colour a URL fragment as a comment, so the choice is explicit. */
const HASH_COMMENT = new Set(["sh", "bash", "zsh", "py", "python", "toml", "yaml", "yml", "rb", "make", "dockerfile"]);

function grammarFor(lang) {
  const comment = HASH_COMMENT.has(lang) ? String.raw`#[^\n]*` : String.raw`\/\/[^\n]*|\/\*[\s\S]*?\*\/`;
  const string = String.raw`"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|` + "`(?:[^`\\\\]|\\\\.)*`";
  return new RegExp(
    [
      `(?<comment>${comment})`,
      `(?<string>${string})`,
      String.raw`(?<number>\b\d[\d_]*(?:\.\d+)?\b)`,
      `(?<keyword>${KEYWORDS.source})`,
      `(?<type>${TYPES.source})`,
      String.raw`(?<call>\b[A-Za-z_$][\w$]*(?=\())`,
    ].join("|"),
    "g",
  );
}

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };

function escapeHtml(text) {
  return text.replace(/[&<>]/g, (char) => ESCAPES[char]);
}

const CLASSES = ["comment", "string", "number", "keyword", "type", "call"];
/** The blueprint's single-letter classes: one vocabulary across every artifact. */
const CLASS_BY_GROUP = { comment: "c", string: "s", number: "n", keyword: "k", type: "t", call: "f" };

export function highlight(code, lang = "ts") {
  if (lang === "text" || lang === "") return escapeHtml(code);
  const grammar = grammarFor(lang);
  let html = "";
  let consumed = 0;
  for (const match of code.matchAll(grammar)) {
    html += escapeHtml(code.slice(consumed, match.index));
    const group = CLASSES.find((name) => match.groups?.[name] !== undefined);
    html += group ? `<span class="${CLASS_BY_GROUP[group]}">${escapeHtml(match[0])}</span>` : escapeHtml(match[0]);
    consumed = match.index + match[0].length;
  }
  return html + escapeHtml(code.slice(consumed));
}

if (typeof window !== "undefined") {
  window["highlightCode"] = highlight;
  window.addEventListener("DOMContentLoaded", () => {
    for (const block of document.querySelectorAll("pre[data-lang]")) {
      const lang = block.getAttribute("data-lang");
      if (lang === "text") continue;
      block.innerHTML = highlight(block.textContent ?? "", lang);
    }
  });
}

if (typeof process !== "undefined" && process.argv?.[1]?.endsWith("highlight.js")) {
  const args = process.argv.slice(2);
  const langIndex = args.indexOf("--lang");
  const lang = langIndex === -1 ? "ts" : (args[langIndex + 1] ?? "ts");
  const file = args.filter((arg, index) => !arg.startsWith("--") && index !== langIndex + 1)[0];
  const source = file ? await Bun.file(file).text() : await new Response(Bun.stdin.stream()).text();
  process.stdout.write(highlight(source.replace(/\n$/, ""), lang) + "\n");
}

/**
 * Highlight.js language definition for Phantom dual-layer Python.
 *
 * Extends Highlight.js's built-in Python grammar with rules for the Phantom
 * instruction layer (`#: phantom:<version>`), block markers (`#:ws:begin`,
 * `#:ws:end`, `#:zw:begin`, `#:zw:end`, `#:phantom:hybrid`), and instruction
 * identifiers.
 *
 * Usage:
 *   import hljs from "highlight.js";
 *   import phantom from "./scripts/syntax/phantom.hljs.js";
 *   hljs.registerLanguage("phantom", phantom);
 */

const PHANTOM_INSTRUCTIONS = [
  "event\\.declare",
  "event\\.on",
  "diagnostic\\.note",
  "diagnostic\\.warn",
  "counter\\.create",
  "counter\\.increment",
  "counter\\.decrement",
  "counter\\.reset",
  "meta\\.author",
  "meta\\.version",
  "meta\\.license",
  "meta\\.tags",
  "meta\\.description",
];

const PHANTOM_MARKERS = [
  "#:ws:begin",
  "#:ws:end",
  "#:zw:begin",
  "#:zw:end",
  "#:phantom:hybrid",
];

export default function phantom(hljs) {
  const pythonDef = hljs.getLanguage("python");
  const base = pythonDef ? pythonDef.rawDefinition || pythonDef : { contains: [] };

  const phantomBlockMarker = {
    className: "meta",
    begin: /#:(?:ws:begin|ws:end|zw:begin|zw:end|phantom:hybrid)\b/,
    relevance: 10,
  };

  const phantomInstructionLine = {
    className: "comment",
    begin: /#:\s*phantom:[0-9]+\.[0-9]+\.[0-9]+/,
    end: /$/,
    relevance: 10,
    contains: [
      {
        className: "number",
        begin: /\b[0-9]+\.[0-9]+\.[0-9]+\b/,
      },
      {
        className: "built_in",
        begin: new RegExp(`\\b(?:${PHANTOM_INSTRUCTIONS.join("|")})\\b`),
      },
      hljs.QUOTE_STRING_MODE,
      hljs.APOS_STRING_MODE,
      hljs.C_NUMBER_MODE,
    ],
  };

  return {
    name: "Phantom",
    aliases: ["phantom", "phantom-py"],
    keywords: base.keywords,
    contains: [
      phantomBlockMarker,
      phantomInstructionLine,
      ...(base.contains || []),
    ],
  };
}

export { PHANTOM_INSTRUCTIONS, PHANTOM_MARKERS };

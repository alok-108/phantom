/**
 * Prism.js language definition for Phantom (Python + Phantom instruction layer).
 *
 * Extends `Prism.languages.python` with token patterns for:
 * - Version prefix comments (`#: phantom:<version>`)
 * - Encoding / hybrid block markers (`#:ws:begin`, `#:ws:end`, `#:zw:begin`, `#:zw:end`, `#:phantom:hybrid`)
 * - Phantom instructions (`event.declare`, `event.on`, `diagnostic.note`, `diagnostic.warn`,
 *   `counter.create`, `counter.increment`, `counter.decrement`, `counter.reset`,
 *   `meta.author`, `meta.version`, `meta.license`, `meta.tags`, `meta.description`)
 */
(function (Prism) {
  "use strict";

  var phantom = Prism.languages.extend("python", {});
  Prism.languages.phantom = phantom;

  Prism.languages.insertBefore("phantom", "comment", {
    "phantom-marker": {
      pattern: /#:(?:ws:(?:begin|end)|zw:(?:begin|end)|phantom:hybrid)\b/,
      alias: "important"
    },
    "phantom-version": {
      pattern: /#:\s*phantom:\d+\.\d+\.\d+\b/,
      alias: "keyword"
    },
    "phantom-instruction": {
      pattern: /#:\s*(?:event\.(?:declare|on)|diagnostic\.(?:note|warn)|counter\.(?:create|increment|decrement|reset)|meta\.(?:author|version|license|tags|description))\b[^\r\n]*/,
      inside: {
        "keyword": /\b(?:event\.(?:declare|on)|diagnostic\.(?:note|warn)|counter\.(?:create|increment|decrement|reset)|meta\.(?:author|version|license|tags|description))\b/,
        "string": /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/,
        "number": /\b\d+(?:\.\d+)?\b/,
        "punctuation": /#:|[():,]/
      }
    }
  });
}(Prism));

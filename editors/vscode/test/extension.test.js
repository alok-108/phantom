'use strict';

/**
 * Exercises extension.js against a small fake of the `vscode` API. This checks our own logic
 * (what is reported where); it cannot prove conformance with the real API.
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const Module = require('node:module');
const fixtures = require('./fixtures.json');

function makeFakeVscode() {
  const registered = { commands: {}, hover: null };
  const diagnosticsByUri = new Map();
  const decorationsSet = [];
  const config = { enable: true };
  const subscriptions = [];

  class Range {
    constructor(sl, sc, el, ec) {
      Object.assign(this, { startLine: sl, startChar: sc, endLine: el, endChar: ec });
    }
  }
  class Diagnostic {
    constructor(range, message, severity) {
      Object.assign(this, { range, message, severity });
    }
  }
  class MarkdownString {
    constructor() {
      this.value = '';
    }
    appendMarkdown(s) {
      this.value += s;
    }
    appendCodeblock(s) {
      this.value += s;
    }
  }
  class Hover {
    constructor(contents) {
      this.contents = contents;
    }
  }

  const output = { lines: [], clear() { this.lines = []; }, appendLine(l) { this.lines.push(l); }, show() {}, dispose() {} };
  const editors = [];

  const vscode = {
    Range,
    Diagnostic,
    MarkdownString,
    Hover,
    ThemeColor: class { constructor(id) { this.id = id; } },
    OverviewRulerLane: { Right: 4 },
    DiagnosticSeverity: { Error: 0, Warning: 1 },
    languages: {
      createDiagnosticCollection: () => ({
        set: (uri, list) => diagnosticsByUri.set(uri.toString(), list),
        delete: (uri) => diagnosticsByUri.delete(uri.toString()),
        dispose() {},
      }),
      registerHoverProvider: (selector, provider) => {
        registered.hover = provider;
        return { dispose() {} };
      },
    },
    window: {
      createOutputChannel: () => output,
      createTextEditorDecorationType: () => ({ dispose() {} }),
      get visibleTextEditors() { return editors; },
      activeTextEditor: null,
      onDidChangeVisibleTextEditors: () => ({ dispose() {} }),
    },
    commands: {
      registerCommand: (id, fn) => {
        registered.commands[id] = fn;
        return { dispose() {} };
      },
    },
    workspace: {
      textDocuments: [],
      getConfiguration: () => ({ get: (key, dflt) => (key in config ? config[key] : dflt) }),
      onDidOpenTextDocument: () => ({ dispose() {} }),
      onDidChangeTextDocument: () => ({ dispose() {} }),
      onDidCloseTextDocument: () => ({ dispose() {} }),
      onDidChangeConfiguration: () => ({ dispose() {} }),
    },
  };
  return { vscode, registered, diagnosticsByUri, decorationsSet, config, output, editors, subscriptions };
}

function fakeDocument(lines, languageId = 'python') {
  return {
    languageId,
    uri: { toString: () => 'file:///fake.py' },
    fileName: 'fake.py',
    lineCount: lines.length,
    lineAt: (i) => ({ text: lines[i] }),
  };
}

function load(fake) {
  const originalLoad = Module._load;
  Module._load = function (request, ...rest) {
    return request === 'vscode' ? fake.vscode : originalLoad.call(this, request, ...rest);
  };
  try {
    delete require.cache[require.resolve('../extension.js')];
    return require('../extension.js');
  } finally {
    Module._load = originalLoad;
  }
}

function activate(fake, document) {
  fake.vscode.workspace.textDocuments = [document];
  const extension = load(fake);
  extension.activate({ subscriptions: fake.subscriptions });
  return extension;
}

const hidden = fixtures.cases.find((c) => c.name === 'simple');

test('a hidden whitespace block produces a warning with its decoded text', () => {
  const fake = makeFakeVscode();
  const document = fakeDocument(['import os', ...hidden.whitespace, 'print(1)']);
  activate(fake, document);
  const [diag] = fake.diagnosticsByUri.get('file:///fake.py');
  assert.equal(diag.severity, fake.vscode.DiagnosticSeverity.Warning);
  assert.match(diag.message, /whitespace block, decodes to: phantom:0\.1\.0 meta\.author\("Ada"\)/);
  assert.equal(diag.range.startLine, 1);
  assert.equal(diag.range.endLine, hidden.whitespace.length);
  assert.equal(diag.source, 'phantom');
});

test('an undecodable block is an error', () => {
  const fake = makeFakeVscode();
  const broken = fixtures.invalid[0];
  activate(fake, fakeDocument(broken.lines));
  const [diag] = fake.diagnosticsByUri.get('file:///fake.py');
  assert.equal(diag.severity, fake.vscode.DiagnosticSeverity.Error);
});

test('a bidirectional control is an error and a stray zero-width character a warning', () => {
  const fake = makeFakeVscode();
  const rlo = String.fromCodePoint(0x202e);
  const zwsp = String.fromCodePoint(0x200b);
  activate(fake, fakeDocument(['a = "x' + rlo + '"', 'b = 1' + zwsp]));
  const found = fake.diagnosticsByUri.get('file:///fake.py');
  assert.deepEqual(found.map((d) => d.severity), [fake.vscode.DiagnosticSeverity.Error, fake.vscode.DiagnosticSeverity.Warning]);
  assert.match(found[0].message, /U\+202E/);
});

test('a clean file has no diagnostics', () => {
  const fake = makeFakeVscode();
  activate(fake, fakeDocument(['print(1)']));
  assert.deepEqual(fake.diagnosticsByUri.get('file:///fake.py'), []);
});

test('files that are not Python are ignored', () => {
  const fake = makeFakeVscode();
  activate(fake, fakeDocument(hidden.whitespace, 'markdown'));
  assert.equal(fake.diagnosticsByUri.has('file:///fake.py'), false);
});

test('phantom.enable = false switches the analysis off', () => {
  const fake = makeFakeVscode();
  fake.config.enable = false;
  activate(fake, fakeDocument(hidden.whitespace));
  assert.equal(fake.diagnosticsByUri.has('file:///fake.py'), false);
});

test('hover inside a block shows the decoded instruction, outside it shows nothing', () => {
  const fake = makeFakeVscode();
  const document = fakeDocument(['x = 1', ...hidden.zero_width]);
  activate(fake, document);
  const inside = fake.registered.hover.provideHover(document, { line: 2 });
  assert.match(inside.contents.value, /meta\.author\("Ada"\)/);
  assert.equal(fake.registered.hover.provideHover(document, { line: 0 }), undefined);
});

test('the command lists decoded instructions of the active file', () => {
  const fake = makeFakeVscode();
  const document = fakeDocument([...hidden.whitespace]);
  activate(fake, document);
  fake.vscode.window.activeTextEditor = { document };
  fake.registered.commands['phantom.showDecoded']();
  assert.ok(fake.output.lines.some((l) => l.includes('[ws]') && l.includes('meta.author("Ada")')));
});

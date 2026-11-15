'use strict';

/**
 * Phantom for VS Code: makes the invisible layer visible.
 *
 * - highlights `#:ws:` / `#:zw:` blocks and shows what they decode to on hover;
 * - lists every hidden block, and every stray invisible / bidirectional character
 *   (the checks of `phantom check --strict`) in the Problems panel;
 * - a command prints all decoded hidden instructions of the active file.
 *
 * It only reads the document. It never runs Python or Phantom.
 */

const vscode = require('vscode');
const { findBlocks, findStrayInvisibles, hex } = require('./src/decode');

const DEBOUNCE_MS = 300;

function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection('phantom');
  const output = vscode.window.createOutputChannel('Phantom');
  const blockDecoration = vscode.window.createTextEditorDecorationType({
    isWholeLine: true,
    backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
    overviewRulerColor: new vscode.ThemeColor('editorWarning.foreground'),
    overviewRulerLane: vscode.OverviewRulerLane.Right,
  });
  const analyses = new Map(); // document uri -> { blocks, stray }
  const timers = new Map();

  const enabled = () => vscode.workspace.getConfiguration('phantom').get('enable', true);

  function linesOf(document) {
    const lines = [];
    for (let i = 0; i < document.lineCount; i += 1) {
      lines.push(document.lineAt(i).text);
    }
    return lines;
  }

  function analyse(document) {
    const key = document.uri.toString();
    if (document.languageId !== 'python' || !enabled()) {
      analyses.delete(key);
      diagnostics.delete(document.uri);
      return;
    }
    const lines = linesOf(document);
    const blocks = findBlocks(lines);
    const stray = findStrayInvisibles(lines, blocks);
    analyses.set(key, { blocks, stray });

    const found = [];
    for (const block of blocks) {
      const range = new vscode.Range(block.beginLine, 0, block.endLine, lines[block.endLine].length);
      const label = block.kind === 'ws' ? 'whitespace' : 'zero-width';
      if (block.error) {
        found.push(new vscode.Diagnostic(range, `Phantom ${label} block: ${block.error}`, vscode.DiagnosticSeverity.Error));
      } else {
        const what = block.instructions.join(' | ');
        found.push(
          new vscode.Diagnostic(
            range,
            `Hidden Phantom ${label} block, decodes to: ${what}`,
            vscode.DiagnosticSeverity.Warning,
          ),
        );
      }
    }
    for (const item of stray) {
      const range = new vscode.Range(item.line, item.character, item.line, item.character + (item.codePoint > 0xffff ? 2 : 1));
      const message = item.bidi
        ? `Bidirectional control ${hex(item.codePoint)} can make code display differently from how it executes`
        : `Invisible character ${hex(item.codePoint)} outside a zero-width block`;
      found.push(
        new vscode.Diagnostic(range, message, item.bidi ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning),
      );
    }
    for (const d of found) {
      d.source = 'phantom';
    }
    diagnostics.set(document.uri, found);
    decorate(document);
  }

  function decorate(document) {
    const analysis = analyses.get(document.uri.toString());
    for (const editor of vscode.window.visibleTextEditors) {
      if (editor.document !== document) {
        continue;
      }
      const ranges = analysis
        ? analysis.blocks.map((b) => new vscode.Range(b.beginLine, 0, b.endLine, 0))
        : [];
      editor.setDecorations(blockDecoration, ranges);
    }
  }

  function schedule(document) {
    const key = document.uri.toString();
    clearTimeout(timers.get(key));
    timers.set(key, setTimeout(() => analyse(document), DEBOUNCE_MS));
  }

  const hover = vscode.languages.registerHoverProvider(
    { language: 'python' },
    {
      provideHover(document, position) {
        const analysis = analyses.get(document.uri.toString());
        const block = analysis && analysis.blocks.find((b) => position.line >= b.beginLine && position.line <= b.endLine);
        if (!block) {
          return undefined;
        }
        const text = new vscode.MarkdownString();
        text.appendMarkdown(`**Hidden Phantom ${block.kind === 'ws' ? 'whitespace' : 'zero-width'} block**\n\n`);
        if (block.error) {
          text.appendMarkdown(`Cannot decode: ${block.error}`);
        } else {
          text.appendCodeblock(block.instructions.join('\n'), 'text');
        }
        return new vscode.Hover(text);
      },
    },
  );

  const command = vscode.commands.registerCommand('phantom.showDecoded', () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      return;
    }
    analyse(editor.document);
    const analysis = analyses.get(editor.document.uri.toString());
    output.clear();
    output.appendLine(`Hidden Phantom blocks in ${editor.document.fileName}`);
    if (!analysis || analysis.blocks.length === 0) {
      output.appendLine('  (none)');
    } else {
      for (const block of analysis.blocks) {
        const where = `line ${block.beginLine + 1}-${block.endLine + 1}`;
        if (block.error) {
          output.appendLine(`  [${block.kind}] ${where}: ERROR ${block.error}`);
        } else {
          block.instructions.forEach((text) => output.appendLine(`  [${block.kind}] ${where}: ${text}`));
        }
      }
    }
    output.show(true);
  });

  context.subscriptions.push(
    diagnostics,
    output,
    blockDecoration,
    hover,
    command,
    vscode.workspace.onDidOpenTextDocument(analyse),
    vscode.workspace.onDidChangeTextDocument((e) => schedule(e.document)),
    vscode.workspace.onDidCloseTextDocument((document) => {
      analyses.delete(document.uri.toString());
      diagnostics.delete(document.uri);
    }),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('phantom.enable')) {
        vscode.workspace.textDocuments.forEach(analyse);
      }
    }),
    vscode.window.onDidChangeVisibleTextEditors(() => vscode.workspace.textDocuments.forEach(decorate)),
  );
  vscode.workspace.textDocuments.forEach(analyse);
}

function deactivate() {}

module.exports = { activate, deactivate };

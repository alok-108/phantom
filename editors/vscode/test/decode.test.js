'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fixtures = require('./fixtures.json');
const { decodeWhitespace, decodeZeroWidth, findBlocks, findStrayInvisibles } = require('../src/decode');

for (const c of fixtures.cases) {
  test(`whitespace block decodes like Python: ${c.name}`, () => {
    const blocks = findBlocks(c.whitespace);
    assert.equal(blocks.length, 1);
    assert.equal(blocks[0].kind, 'ws');
    assert.equal(blocks[0].error, null);
    assert.deepEqual(blocks[0].instructions, c.instructions);
    assert.equal(blocks[0].beginLine, 0);
    assert.equal(blocks[0].endLine, c.whitespace.length - 1);
  });

  test(`zero-width block decodes like Python: ${c.name}`, () => {
    const blocks = findBlocks(c.zero_width);
    assert.equal(blocks.length, 1);
    assert.equal(blocks[0].kind, 'zw');
    assert.equal(blocks[0].error, null);
    assert.deepEqual(blocks[0].instructions, c.instructions);
  });
}

for (const c of fixtures.invalid) {
  test(`broken block is an error, as in Python: ${c.name}`, () => {
    assert.ok(c.python_errors.length >= 1, 'the Python parser must report this case too');
    const blocks = findBlocks(c.lines);
    assert.equal(blocks.length, 1);
    assert.ok(blocks[0].error, `expected an error, got instructions ${JSON.stringify(blocks[0].instructions)}`);
    assert.deepEqual(blocks[0].instructions, []);
  });
}

for (const c of fixtures.stray) {
  test(`stray invisible characters match the strict audit: ${c.name}`, () => {
    const blocks = findBlocks(c.lines);
    const found = findStrayInvisibles(c.lines, blocks).map((f) => [f.line + 1, f.character]);
    assert.deepEqual(found, c.expected);
  });
}

test('decodeWhitespace rejects a line that is not 8 characters', () => {
  assert.throws(() => decodeWhitespace([' \t']), /expected exactly 8/);
});

test('decodeWhitespace rejects an empty list', () => {
  assert.throws(() => decodeWhitespace([]), /empty/i);
});

test('decodeZeroWidth rejects an incomplete group', () => {
  const zwsp = String.fromCodePoint(0x200b);
  assert.throws(() => decodeZeroWidth(zwsp.repeat(3)), /multiple of 4/);
});

test('decodeZeroWidth names a rejected code point', () => {
  assert.throws(() => decodeZeroWidth(String.fromCodePoint(0x2060)), /U\+2060/);
});

test('bidirectional controls are flagged as bidi', () => {
  const line = 'x = "a' + String.fromCodePoint(0x202e) + 'b"';
  const [item] = findStrayInvisibles([line], []);
  assert.equal(item.bidi, true);
  assert.equal(item.character, 6);
});

test('text without hidden blocks has no blocks', () => {
  assert.deepEqual(findBlocks(['print(1)', '# #:ws:begin is only a mention']), []);
});

test('a visible comment on a block marker line is not a marker', () => {
  assert.deepEqual(findBlocks(['#:zw:begin  # note']), []);
});

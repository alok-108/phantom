'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const run = require('../maintainer-inbox.js');

const HOURS = 60 * 60 * 1000;
const ago = (hours) => new Date(Date.now() - hours * HOURS).toISOString();

function makePr(number, login, { hoursOld = 100, draft = false, type = 'User', sha = `sha${number}` } = {}) {
  return {
    number, title: `PR ${number}`, draft, created_at: ago(hoursOld), html_url: `https://example.test/pull/${number}`,
    user: { login, type }, head: { sha },
  };
}

function makeGithub({ pulls = [], blockedShas = [], blockedAgeHours = 1, reviews = {}, comments = {}, pool = 12, existingIssue = null, inboxComments = [] }) {
  const calls = { created: [], updated: [], commented: [] };
  const LIST = Symbol('pulls'), REVIEWS = Symbol('reviews'), COMMENTS = Symbol('comments'), ISSUES = Symbol('issues');
  const github = {
    rest: {
      pulls: { list: LIST, listReviews: REVIEWS },
      issues: {
        listComments: COMMENTS,
        listForRepo: ISSUES,
        create: async (a) => { calls.created.push(a); return { data: { number: 99, ...a } }; },
        update: async (a) => { calls.updated.push(a); return { data: a }; },
        createComment: async (a) => { calls.commented.push(a); return { data: a }; },
      },
      actions: {
        listWorkflowRunsForRepo: async ({ head_sha }) => ({
          data: {
            workflow_runs: blockedShas.includes(head_sha)
              ? [{ conclusion: 'action_required', created_at: ago(blockedAgeHours) }]
              : [{ conclusion: 'success', created_at: ago(blockedAgeHours) }],
          },
        }),
      },
      search: { issuesAndPullRequests: async () => ({ data: { total_count: pool } }) },
    },
    paginate: async (fn, args) => {
      if (fn === LIST) return pulls;
      if (fn === REVIEWS) return reviews[args.pull_number] || [];
      if (fn === COMMENTS) return args.issue_number === 99 || (existingIssue && args.issue_number === existingIssue.number)
        ? inboxComments : comments[args.issue_number] || [];
      if (fn === ISSUES) return existingIssue ? [existingIssue] : [];
      throw new Error('unexpected paginate');
    },
  };
  return { github, calls };
}

const context = { repo: { owner: 'o', repo: 'r' } };
const env = (extra = {}) => ({ MAINTAINERS: 'boss', REVIEW_AFTER_HOURS: '48', APPROVAL_ALERT_AFTER_HOURS: '24', POOL_MINIMUM: '10', DRY_RUN: 'false', ...extra });

test('a pull request whose CI needs approval is listed and the maintainer is pinged once', async () => {
  const { github, calls } = makeGithub({ pulls: [makePr(5, 'newbie', { hoursOld: 3 })], blockedShas: ['sha5'] });
  const result = await run({ github, context, core: {}, env: env() });
  assert.equal(result.awaitingCi, 1);
  assert.equal(calls.created.length, 1);
  assert.match(calls.created[0].body, /CI waiting for approval \(1\)/);
  assert.match(calls.created[0].body, /#5 PR 5 \(@newbie\)/);
  assert.deepEqual(calls.created[0].assignees, ['boss']);
  assert.equal(calls.commented.length, 1);
  // Don't assert an exact hour count on a fixture built milliseconds ago: floor() makes it 0h.
  assert.match(calls.commented[0].body, /@boss #5 \(@newbie\): CI has been waiting for your approval for \d+h/);
});

test('an existing inbox is updated and a pull request already pinged is not pinged again', async () => {
  const existingIssue = { number: 7, body: `${run.MARK}\nold`, pull_request: undefined };
  const marker = '<!-- phantom:inbox-ping:5 -->';
  const { github, calls } = makeGithub({
    pulls: [makePr(5, 'newbie')], blockedShas: ['sha5'], existingIssue, inboxComments: [{ body: `${marker}\nping` }],
  });
  await run({ github, context, core: {}, env: env() });
  assert.equal(calls.created.length, 0);
  assert.equal(calls.updated.length, 1);
  assert.equal(calls.updated[0].issue_number, 7);
  assert.equal(calls.commented.length, 0);
});

test('maintainers, drafts and bots are never listed', async () => {
  const { github } = makeGithub({
    pulls: [makePr(1, 'boss'), makePr(2, 'newbie', { draft: true }), makePr(3, 'dependabot[bot]', { type: 'Bot' })],
    blockedShas: ['sha1', 'sha2', 'sha3'],
  });
  const result = await run({ github, context, core: {}, env: env({ DRY_RUN: 'true' }) });
  assert.equal(result.awaitingCi, 0);
  assert.equal(result.awaitingReview, 0);
});

test('a pull request without any maintainer response is listed only after the threshold', async () => {
  const { github } = makeGithub({ pulls: [makePr(10, 'a', { hoursOld: 10 }), makePr(11, 'b', { hoursOld: 50 })] });
  const result = await run({ github, context, core: {}, env: env({ DRY_RUN: 'true' }) });
  assert.equal(result.awaitingReview, 1);
});

test('a maintainer review or comment clears the "no response" entry', async () => {
  const { github } = makeGithub({
    pulls: [makePr(10, 'a', { hoursOld: 100 }), makePr(11, 'b', { hoursOld: 100 })],
    reviews: { 10: [{ user: { login: 'boss' } }] },
    comments: { 11: [{ user: { login: 'boss' } }] },
  });
  const result = await run({ github, context, core: {}, env: env({ DRY_RUN: 'true' }) });
  assert.equal(result.awaitingReview, 0);
});

test('a small beginner-issue pool is called out, a healthy one is not', async () => {
  const low = makeGithub({ pool: 3 });
  const lowResult = await run({ github: low.github, context, core: {}, env: env() });
  assert.equal(lowResult.poolSize, 3);
  assert.match(low.calls.created[0].body, /Unclaimed `good first issue`s: 3 \(below 10: please file more\)/);

  const ok = makeGithub({ pool: 25 });
  await run({ github: ok.github, context, core: {}, env: env() });
  assert.match(ok.calls.created[0].body, /The pool is healthy/);
});

test('a dry run changes nothing', async () => {
  const { github, calls } = makeGithub({ pulls: [makePr(5, 'newbie')], blockedShas: ['sha5'] });
  await run({ github, context, core: {}, env: env({ DRY_RUN: 'true' }) });
  assert.deepEqual([calls.created.length, calls.updated.length, calls.commented.length], [0, 0, 0]);
});

test('an approval request shows how long it has been waiting', async () => {
  const { github, calls } = makeGithub({
    pulls: [makePr(5, 'newbie', { hoursOld: 3 })], blockedShas: ['sha5'], blockedAgeHours: 3,
  });
  await run({ github, context, core: {}, env: env() });
  assert.match(calls.created[0].body, /#5 PR 5 \(@newbie\) - waiting 3h/);
  assert.doesNotMatch(calls.created[0].body, /:warning:/);
  assert.match(calls.commented[0].body, /CI has been waiting for your approval for 3h/);
});

test('an approval request past the alert threshold is called out and mentions the maintainers', async () => {
  const { github, calls } = makeGithub({
    pulls: [makePr(5, 'newbie', { hoursOld: 50 })], blockedShas: ['sha5'], blockedAgeHours: 50,
  });
  const result = await run({ github, context, core: {}, env: env() });
  assert.equal(result.awaitingCi, 1);
  assert.equal(result.overdueCi, 1);
  assert.match(calls.created[0].body, /#5 PR 5 \(@newbie\) - waiting 50h :warning:/);
  assert.match(calls.created[0].body, /1 of these has been waiting 24h or more/);
  assert.match(calls.created[0].body, /most likely reason someone gives up/);
  // The overdue warning must ping, not just sit in the issue body.
  assert.match(calls.created[0].body, /@boss/);
});

test('approval requests are listed longest-waiting first', async () => {
  const { github, calls } = makeGithub({
    pulls: [makePr(1, 'quick', { hoursOld: 2 }), makePr(2, 'stuck', { hoursOld: 90 })],
    blockedShas: ['sha1', 'sha2'], blockedAgeHours: 2,
  });
  // Give the two PRs different approval ages by overriding the runs response per sha.
  const runList = github.rest.actions.listWorkflowRunsForRepo;
  github.rest.actions.listWorkflowRunsForRepo = async ({ head_sha }) => {
    const res = await runList({ head_sha });
    res.data.workflow_runs[0].created_at = ago(head_sha === 'sha2' ? 90 : 2);
    return res;
  };
  await run({ github, context, core: {}, env: env() });
  const body = calls.created[0].body;
  assert.ok(body.indexOf('#2') < body.indexOf('#1'), 'the longest wait should be listed first');
});

test('a bot is skipped even when the payload omits user.type', async () => {
  // GitHub App and github-actions[bot] authors sometimes arrive without type: 'Bot'.
  const { github } = makeGithub({
    pulls: [makePr(1, 'github-actions[bot]', { type: undefined }), makePr(2, 'dependabot[bot]', { type: undefined })],
    blockedShas: ['sha1', 'sha2'],
  });
  const result = await run({ github, context, core: {}, env: env({ DRY_RUN: 'true' }) });
  assert.equal(result.awaitingCi, 0);
  assert.equal(result.awaitingReview, 0);
});

test('an approval request with no usable timestamp is listed without a bogus age', async () => {
  const { github, calls } = makeGithub({ pulls: [makePr(5, 'newbie')], blockedShas: ['sha5'] });
  github.rest.actions.listWorkflowRunsForRepo = async () => ({
    data: { workflow_runs: [{ conclusion: 'action_required' }] }, // no created_at at all
  });
  const result = await run({ github, context, core: {}, env: env() });
  // Being unable to age it must not silently hide a contributor who is waiting...
  assert.equal(result.awaitingCi, 1);
  // ...and it must not be treated as ancient, or this warns forever.
  assert.equal(result.overdueCi, 0);
  assert.match(calls.created[0].body, /#5 PR 5 \(@newbie\) - waiting for approval \(age unknown\)/);
  assert.doesNotMatch(calls.created[0].body, /:warning:/);
  assert.doesNotMatch(calls.created[0].body, /waiting 2\d\d\d\d\d h/);
  assert.match(calls.commented[0].body, /CI is waiting for your approval/);
});

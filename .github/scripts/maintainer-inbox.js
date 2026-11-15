'use strict';

/**
 * Keeps one issue ("Maintainer inbox") up to date with what is waiting for a maintainer:
 *   - pull requests whose CI is waiting for approval (first-time contributors),
 *   - pull requests nobody on the maintainer list has looked at for a while,
 *   - how many unclaimed `good first issue`s are left (newcomers need a stocked pool).
 * It pings the maintainers once per waiting pull request. It only reads pull requests and
 * writes to its own issue; it never approves, merges or runs anything.
 *
 * An approval request is the one waiting state that only a maintainer can clear, and a
 * contributor cannot see that anything is happening. So the approval request section is
 * ordered by how long it has been waiting and shouts once it passes APPROVAL_ALERT_AFTER_HOURS.
 */

const MARK = '<!-- phantom:maintainer-inbox -->';
const HOUR = 60 * 60 * 1000;

function pingMarker(number) {
  return `<!-- phantom:inbox-ping:${number} -->`;
}

/**
 * True when a pull request author is a bot. `user.type === 'Bot'` is the field to trust, but it
 * is absent from some payloads (notably GitHub App / `github-actions[bot]` authors), so the
 * `[bot]` login suffix is the backstop. Miss it and a bot pull request is reported as a
 * contributor waiting on a maintainer.
 */
function isBot(user) {
  if (!user) return true;
  if (user.type === 'Bot') return true;
  return /\[bot\]$/i.test(user.login || '');
}

/** `@a @b` for the maintainer list, or an empty string when nobody is configured. */
function mentionsOf(maintainers) {
  return maintainers.map((m) => `@${m}`).join(' ');
}

/**
 * The time a run was created, or null when the payload does not carry a usable one.
 *
 * Do not default to `0` here: `Date.parse(0)` coerces to the string "0" and parses it as the
 * year 2000, so a missing timestamp would look like a 26-year-old approval request and put a
 * permanent warning on it.
 */
function runTimestamp(run) {
  const raw = run.created_at || run.updated_at;
  if (!raw) return null;
  const parsed = Date.parse(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

/** Hours since the oldest run in `runs` asked for approval, or null when none did. */
function approvalAgeHours(runs, now) {
  const waiting = runs.filter((r) => r.conclusion === 'action_required');
  if (waiting.length === 0) return null;
  const timestamps = waiting.map(runTimestamp).filter((t) => t !== null);
  // An unageable request is still a waiting contributor, so it counts as age 0 rather than
  // being dropped: it shows up in the list without an age or a warning.
  if (timestamps.length === 0) return 0;
  return Math.max(0, (now - Math.min(...timestamps)) / HOUR);
}

/** True when the age is known (not the "no timestamp" fallback of 0). */
function hasKnownAge(runs) {
  return runs.some((r) => r.conclusion === 'action_required' && runTimestamp(r) !== null);
}

async function run({ github, context, core, env }) {
  const { owner, repo } = context.repo;
  const maintainers = (env.MAINTAINERS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const title = env.TITLE || 'Maintainer inbox (automatic)';
  const reviewAfterHours = Number(env.REVIEW_AFTER_HOURS || 48);
  const approvalAlertAfterHours = Number(env.APPROVAL_ALERT_AFTER_HOURS || 24);
  const poolMinimum = Number(env.POOL_MINIMUM || 10);
  const dry = env.DRY_RUN === 'true';
  const now = Date.now();

  const pulls = await github.paginate(github.rest.pulls.list, { owner, repo, state: 'open', per_page: 100 });

  const awaitingCi = [];
  const awaitingReview = [];
  for (const pr of pulls) {
    if (pr.draft || isBot(pr.user) || maintainers.includes(pr.user.login)) continue;

    const runs = await github.rest.actions.listWorkflowRunsForRepo({
      owner, repo, head_sha: pr.head.sha, per_page: 50,
    });
    const approvalAge = approvalAgeHours(runs.data.workflow_runs, now);
    if (approvalAge !== null) {
      awaitingCi.push({ pr, approvalAge, ageKnown: hasKnownAge(runs.data.workflow_runs) });
    }

    const reviews = await github.paginate(github.rest.pulls.listReviews, { owner, repo, pull_number: pr.number, per_page: 100 });
    const comments = await github.paginate(github.rest.issues.listComments, { owner, repo, issue_number: pr.number, per_page: 100 });
    const touched = reviews.some((r) => maintainers.includes(r.user && r.user.login))
      || comments.some((c) => maintainers.includes(c.user && c.user.login));
    const ageHours = (now - Date.parse(pr.created_at)) / HOUR;
    if (!touched && ageHours >= reviewAfterHours) awaitingReview.push({ pr, ageHours });
  }

  // Longest wait first: the whole point of this section is to stop an approval request from
  // being overlooked, so it must not be ordered by whatever the API happened to return.
  awaitingCi.sort((a, b) => b.approvalAge - a.approvalAge);
  const overdueCi = awaitingCi.filter(({ approvalAge, ageKnown }) => ageKnown && approvalAge >= approvalAlertAfterHours);

  const pool = await github.rest.search.issuesAndPullRequests({
    q: `repo:${owner}/${repo} is:issue is:open label:"good first issue" no:assignee`,
    per_page: 1,
  });
  const poolSize = pool.data.total_count;

  const line = (pr, extra = '') => `- #${pr.number} ${pr.title} (@${pr.user.login})${extra} ${pr.html_url}`;
  const body = [
    MARK,
    '_This issue is maintained by the `maintainer-inbox` workflow (every 6 hours). It is safe to leave open._',
    '',
    `### CI waiting for approval (${awaitingCi.length})`,
    awaitingCi.length
      ? awaitingCi.map(({ pr, approvalAge, ageKnown }) => line(pr, ageKnown
        ? ` - waiting ${Math.floor(approvalAge)}h${approvalAge >= approvalAlertAfterHours ? ' :warning:' : ''}`
        : ' - waiting for approval (age unknown)')).join('\n')
      : '_nothing_',
    awaitingCi.length
      ? 'Open the pull request, skim the diff, then *Approve and run* on the Checks tab. First-time contributors drop out most often here.'
      : '',
    overdueCi.length
      ? `:warning: ${overdueCi.length} of these ${overdueCi.length === 1 ? 'has' : 'have'} been waiting ${approvalAlertAfterHours}h or more. A contributor sees no feedback at all while this is pending, so this is the most likely reason someone gives up. ${mentionsOf(maintainers)}`
      : '',
    '',
    `### No maintainer response for ${reviewAfterHours}h or more (${awaitingReview.length})`,
    awaitingReview.length
      ? awaitingReview.map(({ pr, ageHours }) => line(pr, ` - ${Math.floor(ageHours)}h old`)).join('\n')
      : '_nothing_',
    '',
    `### Unclaimed \`good first issue\`s: ${poolSize}${poolSize < poolMinimum ? ` (below ${poolMinimum}: please file more)` : ''}`,
    poolSize < poolMinimum
      ? 'A newcomer who finds no open beginner issue leaves. `pytest --cov=phantom --cov-report=term-missing` and the open ideas in docs/proposals are good sources.'
      : 'The pool is healthy.',
    '',
    `_Last updated: ${new Date(now).toISOString()}_`,
  ].join('\n');

  console.log(body);
  if (dry) {
    return { awaitingCi: awaitingCi.length, overdueCi: overdueCi.length, awaitingReview: awaitingReview.length, poolSize };
  }

  const open = await github.paginate(github.rest.issues.listForRepo, {
    owner, repo, state: 'open', labels: 'maintenance', per_page: 100,
  });
  let inbox = open.find((i) => !i.pull_request && i.body && i.body.includes(MARK));
  if (!inbox) {
    const created = await github.rest.issues.create({
      owner, repo, title, body, labels: ['maintenance'], assignees: maintainers,
    });
    inbox = created.data;
  } else {
    await github.rest.issues.update({ owner, repo, issue_number: inbox.number, body });
  }

  // Ping once per waiting pull request (however many reasons it has), so a notification
  // arrives without spamming.
  const existing = await github.paginate(github.rest.issues.listComments, {
    owner, repo, issue_number: inbox.number, per_page: 100,
  });
  const reasons = new Map();
  const add = (pr, text) => reasons.set(pr.number, { pr, texts: [...(reasons.get(pr.number)?.texts || []), text] });
  awaitingCi.forEach(({ pr, approvalAge, ageKnown }) => add(
    pr,
    ageKnown
      ? `CI has been waiting for your approval for ${Math.floor(approvalAge)}h`
      : 'CI is waiting for your approval',
  ));
  awaitingReview.forEach(({ pr }) => add(pr, 'has had no maintainer response yet'));
  const mentions = mentionsOf(maintainers);
  for (const [number, { pr, texts }] of reasons) {
    const marker = pingMarker(number);
    if (existing.some((c) => c.body && c.body.includes(marker))) continue;
    await github.rest.issues.createComment({
      owner, repo, issue_number: inbox.number,
      body: `${marker}
${mentions} #${number} (@${pr.user.login}): ${texts.join('; ')}: ${pr.html_url}`,
    });
  }
  return {
    awaitingCi: awaitingCi.length,
    overdueCi: overdueCi.length,
    awaitingReview: awaitingReview.length,
    poolSize,
    inbox: inbox.number,
  };
}

module.exports = run;
module.exports.MARK = MARK;

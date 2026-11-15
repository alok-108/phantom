# Maintainers

- @alok-108 - Alok - Project owner; reviews and merges pull requests, cuts releases

Maintainers review pull requests, triage issues, approve first-time-contributor CI runs and decide
on language proposals (see [docs/CONTRIBUTOR_GUIDE.md](docs/CONTRIBUTOR_GUIDE.md#8-proposing-a-language-change)).

## Becoming a maintainer

Regular, high-quality contributions (code, review, docs or research) over a few months, and an
invitation from the current maintainers. Nobody is listed here without their agreement.

## What maintainers promise contributors

- A first response on issues and pull requests, aiming for within a week. This is a volunteer project, so this is a goal, not a guarantee.
- Issues labelled `mentor available` get help with design questions and review.
- Feedback that is specific and kind; small pull requests are reviewed fastest.

## The maintainer inbox (automatic)

The `maintainer-inbox` workflow runs every six hours and keeps one issue, labelled `maintenance`, up to date with:

- pull requests whose CI is **waiting for approval** (the place where first-time contributors drop out);
- pull requests with **no maintainer response** for 48 hours;
- the number of unclaimed `good first issue`s (keep at least 10).

It pings the maintainers listed in the workflow's `MAINTAINERS` variable once per waiting pull request. It never approves, merges or runs anything. Run it by hand from the Actions tab (dry run is the default). When maintainers change, edit `MAINTAINERS` in `.github/workflows/maintainer-inbox.yml`.

# Maintaining the catalogue

This repository curates external engineering tools. AIPE-Registry describes AIPE
capabilities and supported integrations; catalogue inclusion is not AIPE support.
The two repositories deliberately remain independent.

Keep existing historical entries unless a reviewed change explains their unique
value and provenance. Do not label an old project abandoned based on age alone.
Record capabilities and limitations rather than promising one-to-one replacements.

Edit `catalogue/tools.json` (36 original rows retained, 11 additions). `license`
is a sourced assertion, not a licence grant by this repository. `NOASSERTION` and
`unverified` preserve uncertainty. GitHub's automated SPDX detection can refine
the generated audit but does not replace a release-specific legal review.
Hardware, data, application, documentation and dependency licences can differ.
FEMM is retained as source-available under Aladdin; MATLAB-dependent source
projects are retained without claiming a wholly open execution path.

Interfaces are discovery hints grounded in linked upstream pages, not tested AIPE
adapters. Review selected version, platform and actual operation before adoption.
For connectors edit `catalogue/connectors.json`: include version/platform claims,
API surface, security implications, direct CLI/API alternative and execution status.
Do not install/vendor MCP implementations as a side effect of catalogue curation.

Refresh public-source evidence explicitly (requires Python 3.10+ and authenticated
GitHub CLI; normal validation is offline):

```sh
python scripts/refresh_sources.py --network --as-of YYYY-MM-DD
python scripts/build_audit.py
python scripts/build_audit.py --check
python -m unittest discover -s tests -v
```

Use the actual review date. Review the snapshot and generated diff before a PR.
The refresh collects repository metadata/default-branch commit and HTTP status,
without executing project content. 404/410 observations need human review before
link edits; 403, rate limits, robots blocks, TLS failures and timeouts are
inconclusive, never evidence that a project is abandoned. A GitHub mirror's last
commit need not equal upstream activity; consult the primary site too.

The audit has a deterministic 365-day recent-commit heuristic; archival status is
explicit. Generated JSON preserves every source, check date and observed commit.
External evidence is a point-in-time observation and must be refreshed before
selecting production dependencies. No wall-clock/network input enters CI builds.

No repository-wide licence existed at audit time; rights remain `NOASSERTION`.
This change does not relicense inherited prose, screenshots or third-party work.

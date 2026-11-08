# Changelog

## Unreleased

- 30 impossible variants of the sdlc-eval-kit tasks, each checked to fail on the reference with exactly
  one test (`check-variants`).
- Three controls against test gaming (`prompt`, `readonly`, `sealed`) in an agent runner built on
  sdlc-eval-kit's, which stays unchanged.
- Sealed judge: pristine tests and config, steering files removed, JUnit-checked passes, unprivileged
  read-only container. Self-check: the workspace's own test run as the agent left it.
- Gaming verdicts (`code`, `tests`) and diff tags; RESULTS.md generator.
- Draft PREREGISTRATION.md.

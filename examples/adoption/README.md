# Sanitized read-only adoption fixtures

These are synthetic, non-production source trees for #22/#24. The smoke runner
copies them only into new temporary demo repositories and imports explicit
manifests. No actual application, personal data or cloud credentials are used.

- `spring-service`: Java 17 / Spring Boot 3.5.0 / Maven and a Cloud Run HTTP-service
  descriptor. Versions and architecture are **fixture declarations**, not detected
  runtime facts or recommendations for currently supported/patched versions.
- `python-service`: a small standard-library Python HTTP-service source fixture.
- Explicit manifests define stable repository/component/interface IDs. Git HEAD
  references are observed but unverified. No framework or behavior is inferred
  from the application source by this provider.

Nothing here is built, imported as executable Python/Java, started, migrated or
deployed by the adoption flow. Docker image tags and the fake registry reference
are illustrative, not resolved or approved artifact pins. This does not establish
Spring Boot 4 compatibility, successful application tests or Cloud Run deployment.

The generated `.ane/` metadata may live directly inside an explicitly selected
source repo or in a separate orchestration repository. The existing source trees
and Git HEADs must be unchanged by adoption/refresh/cleanup. A test-only external
empty commit may simulate a source revision change; that is not an ANE source edit.

```sh
uv run python scripts/adoption_smoke.py
```

Retain artifacts with `--output-dir NEW_DIRECTORY`. Review outputs and limitations
before using any workspace against a real repository. Read `docs/WORKSPACE.md` for
explicit initialization, preview/apply, drift refusal, cleanup and rollback.

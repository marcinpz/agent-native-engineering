# Illustrative test description — not an execution record

This artifact is sample data for the Living System Model fixture. No backend,
web application, mobile application, database, or integration test was executed
to produce it. It is not proof of system correctness and contains no test result.

## Proposed acceptance scenario

1. A signed-in user creates a note through the backend notes API.
2. The backend persists the note in the store.
3. The same user requests their notes from the web and mobile clients.
4. Both clients display the saved note; another user cannot retrieve it.

The scenario is declared intent. Authentication, implementation paths, persistence,
and cross-client behavior remain unverified. A future real execution should record
the source revision, timestamp, environment, command, and captured result in a new
evidence artifact rather than relabeling this description as an executed test.

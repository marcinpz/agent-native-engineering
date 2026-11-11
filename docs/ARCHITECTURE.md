# Architecture sketch

Human intent and artifacts -> requirement refinement -> Living System Model (typed, versioned graph) -> impact analysis and scoped agent context -> implementation across repositories -> tests/evidence -> model reconciliation -> generated documentation.

The model tracks intended, observed and verified states separately. A new agent should be able to ask what the system does, why a design exists, what components a requirement touches, and how to verify a proposed change.

Initial implementation is a CLI and open schema, not a platform service. Later adapters may connect to GitHub, OpenCode, CI, code parsers and documentation renderers.

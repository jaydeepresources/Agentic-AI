# Architecture Decision Record: ADR-001

## Title
Optional Local Plain-Text Persistence for TODO Items

## Status
Proposed

## Context
The Console TODO App must support core TODO operations (add, list, complete, delete) in a C++ console application. User Story 5 (low priority) requests that TODO items persist between application sessions. The BRD lists data persistence as optional or to be determined, and the epic plan marks EPIC-05 as optional and contingent on stakeholder approval. The storage format, target operating system, and C++ standard are unresolved. The BRD dependencies specify only a C++ compiler and standard C++ library; no external libraries or databases are specified.

## Decision
Persist TODO items to a local plain-text file only if EPIC-05 is approved by stakeholders. Use the C++ standard library for file I/O. Do not introduce external dependencies, databases, or cloud synchronization. If persistence is not approved, the application operates in-memory only for the session.

## Alternatives
1. **In-memory only (no persistence)**: Simplest implementation; aligns with BRD assumption that persistence is optional. Does not satisfy US-05 if approved.
2. **Plain-text local file**: Uses standard library file streams; human-readable; simple to implement and debug; no external dependencies. Format must be defined (e.g., one line per item with id, description, status).
3. **JSON local file**: Structured and extensible; requires parsing logic or a library. No JSON library is specified in BRD dependencies; implementing a parser adds complexity.
4. **Binary local file**: Compact; not human-readable; requires custom serialization. Adds complexity without a stated requirement.
5. **Database (e.g., SQLite)**: Over-engineered for a single-user console app; introduces external dependency not specified in BRD §8.
6. **Cloud synchronization**: Explicitly out of scope per BRD.

## Consequences
### Positive
- Aligns with BRD constraint to use C++ and standard library only.
- Avoids external dependencies and build complexity.
- Plain-text format is easy to inspect manually and matches the simplicity goal (NFR-03).
- Optional nature allows the team to deliver the MVP (EPIC-03 and EPIC-04) without persistence and add it later if approved.

### Negative
- Plain-text format requires custom parsing and error handling for malformed files.
- If the target operating system is not confirmed, file path conventions and line endings may vary.
- Deferring the persistence decision may require rework of the repository interface if added after EPIC-04.
- No defined storage location or file naming convention exists yet.

## Related Artifacts
- BRD §7 Assumptions: Data persistence is optional or to be determined.
- BRD §9 Open Questions: Should data persist between sessions? If so, what storage format?
- Epic Plan EPIC-05: Data Persistence (Optional).
- User Story US-05: Persist TODO items between sessions (Priority: Low).
- WBS work package 6.0: Data Persistence (Optional/Conditional).

## Review Required
Stakeholder sign-off on persistence inclusion and format is required during EPIC-01 (Requirements Validation & Scope Confirmation).

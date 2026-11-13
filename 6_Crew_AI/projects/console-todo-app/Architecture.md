# Solution Architecture: Console TODO App

## 1. Purpose and Scope
This architecture defines the structure of a simple console-styled TODO application implemented in C++, as specified in the Business Requirements Document (BRD), prioritized user stories, epic plan, and work breakdown structure (WBS). The application supports personal task management through a command-line interface.

## 2. Source Artifacts and Traceability
- BRD: Purpose, scope, functional requirements FR-01 to FR-04 (candidate), non-functional requirements NFR-01 to NFR-03, constraints, assumptions, dependencies, open questions.
- User Stories: US-01 (Add), US-02 (List), US-03 (Complete), US-04 (Delete), US-05 (Persist, low priority).
- Epic Plan: EPIC-01 through EPIC-06, sequence EPIC-01 → EPIC-02 → EPIC-03 → EPIC-04 → [EPIC-05 optional] → EPIC-06.
- WBS: Work packages 1.0 through 8.0, including domain model (id, description, status), console input parsing, and optional persistence.

## 3. Explicit Assumptions
The following assumptions are drawn from the BRD and PM artifacts and are not confirmed customer requirements:
- The application is single-user.
- No authentication or authorization is required.
- Data persistence is optional and contingent on stakeholder approval (EPIC-05).
- The target platform is a desktop operating system with a standard C++ compiler and terminal.
- Performance target of 2 seconds for task addition is assumed, not confirmed (US-01).
- The candidate functional requirements (add, list, complete, delete) are assumptions based on common TODO app behavior and must be validated in EPIC-01.

## 4. Unresolved Choices
The following decisions are open questions carried from the BRD and epic plan and must be resolved before detailed design:
- Specific TODO operations beyond add, list, complete, and delete (e.g., edit, prioritize, due dates are out of scope per epic plan).
- Data persistence format (plain text, JSON, binary) if persistence is approved.
- Target operating system (Windows, Linux, macOS).
- Preferred C++ standard (e.g., C++11, C++17, C++20).
- Required build system (CMake, Make, Visual Studio).
- Named stakeholders and product owner.

## 5. Components
The architecture is organized into the following logical components. Component boundaries reflect the WBS work packages and epic traceability.

### 5.1 Console UI / Input Parser
Responsible for rendering output to the terminal and parsing user input commands. Derived from BRD NFR-02 (console/terminal environment) and WBS work packages 4.1 and 4.5.

### 5.2 Command Processor
Coordinates user commands with domain logic and repository operations. Maps to WBS work packages 4.2, 5.2, and 5.4.

### 5.3 TODO Domain Model
Represents a TODO item. Based on WBS work package 3.1, the data structure includes:
- Identifier (id)
- Description
- Status (pending or completed)

### 5.4 In-Memory Repository
Holds TODO items in memory during application execution. Derived from WBS work package 3.2 and BRD assumption that persistence is optional.

### 5.5 Persistence Layer (Optional)
Loads and saves TODO items to local storage. Conditional on EPIC-05 and US-05. Storage format and location are unresolved.

### 5.6 Build and Toolchain
C++ compiler, standard library, and build system configuration. Derived from BRD §8 dependencies and WBS work package 2.0. Specific compiler and build system are unresolved.

## 6. Component Interactions
Interactions are limited to local, in-process communication within a single console process.

1. The user enters a command in the console terminal.
2. Console UI / Input Parser reads input and parses the command.
3. Command Processor invokes the appropriate operation on the TODO Domain Model and In-Memory Repository.
4. For add, list, complete, and delete operations, the repository updates the in-memory collection.
5. Console UI renders the result or status message to the terminal.
6. If the Persistence Layer is enabled, the repository loads items at startup and saves items after mutating operations.

No network, multi-user, or cloud interactions are in scope (BRD out-of-scope items).

## 7. Data
### 7.1 TODO Item
Fields are based on WBS work package 3.1:
- id: unique identifier for the item
- description: task description text
- status: pending or completed

### 7.2 Persistence Data (Optional)
If EPIC-05 is approved, TODO items are written to a local file. Format is unresolved (plain text, JSON, or binary). No database or cloud storage is in scope.

## 8. Security
- No authentication or authorization is required (BRD §7 assumption, epic plan assumptions).
- The application is single-user and executes locally.
- No network communication, cloud synchronization, or multi-user features are in scope (BRD out-of-scope).
- Specific security targets are not provided in the inputs.

## 9. Deployment
- Deliverable is a packaged console application executable for the target desktop operating system (WBS work package 8.1).
- Target operating system is unresolved.
- Runtime requires a standard C++ compiler environment and terminal/console (BRD §8).
- No installation of external libraries beyond the standard library is specified (BRD §8, epic plan EPIC-02 scope out).

## 10. Quality Attributes
Quality attributes are described only as far as the inputs justify:
- **Implementation language**: C++ (NFR-01, BRD §6).
- **Interface**: Console/terminal (NFR-02, BRD §6).
- **Simplicity**: Simple user interface (NFR-03, BRD §5).
- **Performance**: Task addition completes within 2 seconds (assumed target from US-01, to be confirmed).
- **Reliability**: No defined targets in the inputs.
- **Portability**: Target OS unresolved; terminal behavior varies by OS (EPIC-06 risk).
- **Security**: No defined targets; no auth required by assumption.

## 11. Risks
- Unresolved persistence mechanism may cause rework if added late (WBS risk).
- Target OS not confirmed may affect console behavior and packaging (WBS risk).
- C++ standard not specified may affect language feature usage (WBS risk).
- Performance targets are assumed, not validated (WBS risk).
- Scope creep risk: edit, prioritize, due dates are not in the approved scope (WBS risk).

---

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

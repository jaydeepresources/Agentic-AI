# WBS: Console TODO App

1.0 Project Initiation and Requirements Validation
   1.1 Stakeholder identification and confirmation
   1.2 Requirements validation workshop (BRD open questions)
   1.3 Scope sign-off (in-scope/out-of-scope confirmation)
   1.4 Decision on data persistence (include/exclude EPIC-05)
   1.5 Decision on target OS, C++ standard, and build system

2.0 Development Environment Setup
   2.1 C++ compiler selection and installation (GCC/Clang/MSVC)
   2.2 Build system configuration (CMake/Make/Visual Studio - TBD)
   2.3 Version control repository initialization
   2.4 Console/terminal runtime verification
   2.5 Initial project scaffold and hello-world build

3.0 Core Domain Model
   3.1 TODO item data structure (id, description, status)
   3.2 In-memory repository implementation
   3.3 Domain unit tests

4.0 Epic: Add and List (US-01, US-02)
   4.1 Console input parsing for add command
   4.2 Add TODO item business logic
   4.3 List all TODO items display
   4.4 Empty state message implementation
   4.5 Integration of add and list with console UI
   4.6 Acceptance criteria testing (US-01 AC1/AC2, US-02 AC1/AC2)

5.0 Epic: Complete and Delete (US-03, US-04)
   5.1 Item selection mechanism (by ID or index)
   5.2 Mark as completed logic
   5.3 Completed status visual distinction in list
   5.4 Delete item logic
   5.5 Post-deletion list verification
   5.6 Acceptance criteria testing (US-03 AC1/AC2, US-04 AC1/AC2)

6.0 Epic: Data Persistence (US-05) [Optional/Conditional]
   6.1 Persistence format decision (plain text/JSON/binary)
   6.2 Save TODO items to local file
   6.3 Load TODO items on startup
   6.4 Session-to-session retention testing
   6.5 Acceptance criteria testing (US-05 AC1)

7.0 Testing and Quality Assurance
   7.1 Functional test execution against all user stories
   7.2 Console UI simplicity review (NFR-03)
   7.3 Edge case and input validation testing
   7.4 Defect triage and fixes

8.0 Packaging and Release
   8.1 Executable build for target OS
   8.2 Release notes and usage instructions
   8.3 Final delivery to end user

## WBS Dependencies

- 2.0 depends on 1.5 (compiler/OS/build system decisions)
- 3.0 depends on 2.0
- 4.0 depends on 3.0
- 5.0 depends on 4.0
- 6.0 depends on 1.4 and 4.0/5.0; optional
- 7.0 depends on 4.0, 5.0, and 6.0 (if included)
- 8.0 depends on 7.0

## Risks (WBS Level)

- Unspecified persistence mechanism may cause rework if added late
- Target OS not confirmed may affect console behavior and packaging
- C++ standard not specified may affect language feature usage
- Performance targets are assumed, not validated
- Scope creep risk: edit, prioritize, due dates are not in the approved scope

## Estimates

All work package estimates are indicative because the BRD and user stories do not provide effort, duration, or sizing detail.

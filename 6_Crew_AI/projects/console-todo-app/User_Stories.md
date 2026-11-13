# Prioritized User Stories

## User Story 1 (Priority: High)
**As a** end user,
**I want to** add a new TODO item via the console,
**so that** I can track a task I need to complete.

### Acceptance Criteria
1. Given the application is running, when the user enters the add command with a task description, then the task is added to the TODO list.
2. Given the application is running, when the user adds a task, then the task is visible in the subsequent list view.
*Measurable: Task addition completes within 2 seconds (assumed performance target to be confirmed).*

## User Story 2 (Priority: High)
**As a** end user,
**I want to** view all TODO items in the console,
**so that** I can see my outstanding tasks.

### Acceptance Criteria
1. Given there are one or more TODO items, when the user requests the list, then all items are displayed in the console.
2. Given there are no TODO items, when the user requests the list, then an empty state message is displayed.
*Measurable: List displays all items without truncation (assumed).*

## User Story 3 (Priority: Medium)
**As a** end user,
**I want to** mark a TODO item as completed,
**so that** I can track progress.

### Acceptance Criteria
1. Given a pending TODO item exists, when the user selects it for completion, then the item status changes to completed.
2. Given a completed item, when the user views the list, then the item is visually distinguished as completed (e.g., strikethrough or status label).

## User Story 4 (Priority: Medium)
**As a** end user,
**I want to** delete a TODO item,
**so that** I can remove tasks that are no longer relevant.

### Acceptance Criteria
1. Given a TODO item exists, when the user issues a delete command for that item, then the item is removed from the list.
2. Given the list is viewed after deletion, then the deleted item no longer appears.

## User Story 5 (Priority: Low)
**As a** end user,
**I want to** have TODO items persist between application sessions,
**so that** I do not lose my task list when I close the program.

### Acceptance Criteria
1. Given the application is closed and reopened, when the user views the list, then previously added items are still present.
*This story is contingent on the open question regarding data persistence.*

*Prioritization is based on typical MVP ordering for a console TODO app and is not derived from customer input.*

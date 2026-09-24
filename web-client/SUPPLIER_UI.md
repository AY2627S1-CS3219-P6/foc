# Supplier UI requirement traceability

This maps the Supplier screens to the final product backlog and Milestone D2
point 5. The visual layout follows the shared [FoC Figma design](https://www.figma.com/design/1QaorStohl4p1T8PoC9YG5/CS3219---Project-6?node-id=0-1).
Only Supplier pages were added; sign-in and the existing profile remain User
Service pages.

| Backlog IDs | Supplier UI coverage | Boundary or remaining check |
| --- | --- | --- |
| `M2F1.1.1`–`M2F1.1.5` | Admin create form has required and optional fields, category choices from the API, paired coordinates/times, exact 24-hour `HH:mm`, and HTTP(S) URL validation. | Supplier Service validates again, generates ID and timestamps, and defaults status. |
| `M2F1.1.6`–`M2F1.1.7` | The form shows API duplicate and field errors without claiming success. | Normalized uniqueness and atomic rollback belong to the database/API. |
| `M2F1.2.1`–`M2F1.2.7` | Admin edit preloads the complete record; fields and categories can change, optional values can be cleared, status can change, and validation or load failures are displayed. ID and timestamps are read-only. | The API validates the merged row, rejects duplicates, and commits changes atomically. |
| `M2F1.3.1`–`M2F1.3.3` | Deactivate confirmation calls the current `DELETE` contract and refreshes the record. Inactive suppliers can be reactivated. | Permanent deletion of never-referenced suppliers and the Errand Service selection guard remain pending their service contract. |
| `M2F2.1.1`–`M2F2.1.4` | Normal list uses the active-only route; admin list uses the management route and includes status filtering. Both show required list fields and pagination/page-size controls when needed. | API enforces visibility and paging. The UI deliberately requests six rows per page for the layout; the API default remains 20 when omitted. |
| `M2F2.2.1`–`M2F2.2.3` | Detail view shows complete supplier data and handles not found, load failure, and retry states. | API supplies the record and sanitized error response. |
| `M2F3.1.1`–`M2F3.1.4` | Search automatically applies `q` for name, area, or pickup text after a short typing pause and trims whitespace. | API implements case-insensitive partial matching. |
| `M2F3.2.1`–`M2F3.2.4` | Category checkboxes send repeated `category` parameters; admin-only status combines with search. The separate exact-area filter was removed from the UI and API. | Backlog `M2F3.2.2` and the area portion of `M2F3.2.4` need revision for this simplified product scope. `q` still searches area text. |
| `M2F3.3.1`, `M2F3.4` | Name A–Z/Z–A controls and a clear empty-result state. | API provides stable ID tie-break sorting and the empty response. |
| `M2F4.1.1`–`M2F4.3.3` | Supplier pages require sign-in; management links and pages require Admin or Super Admin in the UI; every request sends the User Service access token. | Supplier Service verifies identity and fresh management permission for each request. UI role gating is for navigation, not the security boundary. |

## Nonfunctional requirements

| Backlog IDs | UI handling | Verification still needed |
| --- | --- | --- |
| `M2NFR1.1`–`M2NFR1.3`, `M2NFR2.1`–`M2NFR2.2` | List requests are paginated and show loading/error states. | Sprint 4 performance and scale targets need representative data and load tests; browser tests do not establish the percentile or concurrency targets. |
| `M2NFR3.1`–`M2NFR3.3` | Save success is shown only after an API response; validation/duplicate errors remain visible for correction. | Database uniqueness, durable commits, and rollback need service/database verification. |
| `M2NFR3.4` | Deactivating refreshes the admin view; normal browsing uses the active-only API. | Cross-client propagation within five seconds still needs a live integration test. |
| `M2NFR4.1`–`M2NFR4.2` | Unauthorized users cannot navigate to management screens from the client. | Current-permission checks before mutation remain the API's responsibility. |

## Milestone D2 point 5

The client provides live Supplier API screens for viewing, creating, editing,
deactivating, searching, filtering, sorting, and paginating. Layouts
were checked in browser tests at 375, 768, 1024, and 1440 pixel widths against
the supplied desktop and mobile Figma direction. Browser tests mock the API;
the root Compose stack is the path for a live local demonstration.

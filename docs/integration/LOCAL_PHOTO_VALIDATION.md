# Local photo + HIRA validation — 2026-10-19

## Commands and final outcomes (f7e0db7 baseline)

| Command / target | Final result |
| --- | --- |
| `python -m pytest backend/tests backend/services -q` | 214 passed, plus 5 passing subtests; 0 failed/skipped. One upstream Starlette TestClient deprecation warning |
| `pnpm test` | All seven existing frontend check groups passed (including 12 Current Intake/timeline and 10 UX cases) |
| `pnpm build` | TypeScript strict check and Vite production build passed, 43 modules |
| `node tests/photo-hira-integration.browser.cjs` | Eight integration scenario groups passed against local FastAPI + Vite; 0 runtime errors, 0 external API attempts |
| `node tests/image-review.browser.cjs` | Four original standalone image-review scenarios, family reset and keyboard checks passed; 0 API requests/runtime errors |
| Both browser suites | 360/390/768/1280px: document scroll width equals viewport width |
| `git diff --check` | Passed |

Backend was restarted from the final implementation before the final browser
runs. Integration routes used virtual fixtures and MockMfdsClient only. The
integrated browser suite blocked eight inherited Google-font requests before
network dispatch. No actual Gemini/MFDS invocation or credential use occurred.

Runtime: Python 3.12 environment, repository-declared backend requirements,
existing pnpm lockfile, existing Playwright installation and local Chromium.
The environment's optional browser tooling is not a new production dependency.

## Changed files

- Backend: `backend/api/main.py`, new `backend/api/photo_demo.py`,
  `backend/services/normalization/structured.py`, `backend/tests/test_photo_demo.py`.
- Frontend: `frontend/src/main.tsx`, `ImageReviewPanel.tsx`, `api.ts`, new
  `PhotoWorkflow.tsx`, `photoApi.ts`.
- Browser tests: `frontend/tests/image-review.browser.cjs`, new
  `frontend/tests/photo-hira-integration.browser.cjs`.
- Documentation: `docs/integration/TASK_D_WEEKLY_STATUS.md`, new
  `LOCAL_PHOTO_MOCK.md`, `LOCAL_PHOTO_VALIDATION.md`.

No shared Schema/API document, lockfile or dependency declaration was changed.

## Checks covered

- Virtual A JSON through the common adapter, candidate editing and immutable
  originals, formal B normalization, explicit final review, D comparison,
  independent Current Intake confirmation and previous/current timeline.
- Multiple products/compound ingredients; zero and high-precision decimal text.
- Null records, invalid quantity, failed extraction/retry, incomplete or duplicate
  reviews, mismatched IDs, same document on both sides, repeat groups and unknown
  strength all preserve source data and avoid fabricated comparison results.
- Family changes including A→B→A, extraction cancellation, late extraction and
  late normalization after editing. A new comparison resets intake confirmation.
- Real virtual XLSX upload through the existing HIRA parser/B/D pipeline and
  browser result/timeline, plus HIRA cancellation and late responses after family
  round trips.
- 360/390/768/1280px layouts; no unexpected runtime errors or external API attempts.
- Original standalone image-review browser checks remain a separate regression.

## Initial failures and corrections

- The first long browser run had an unbounded interceptor wait; the test harness
  now reports bounded request/response-wait failures rather than hanging.
- A completed integration run failed the final no-external-resource assertion
  because the pre-existing HTML imports a Google font. The suite now blocks all
  non-local resources and separately rejects unexpected external API attempts;
  it does not weaken business assertions or enable external APIs.
- Code inspection found duplicate candidate description/error DOM IDs when two
  review panels are present. Panel IDs are now namespaced while reducer keys
  remain unchanged; the browser suite asserts uniqueness.

## Known limits

No production photo protocol, null-record manual creation, automatic repeat
representative selection or cross-source reupload dedup policy was finalized.
Unresolved batches are held as a whole. Existing HIRA R1–R4 policy concerns remain.
No actual Gemini/MFDS calls, auth, permanent storage or deployment were run.

## Subsequent policy audit

See `TASK_D_POLICY_REVIEW.md` for the 214-item collection breakdown and why the
five nested unittest subtests must not be added as five independent test items.
The original 8-group browser evidence above belongs to the f7e0db7 baseline;
it is not a screenshot/video/trace archive.

The follow-up change fixes only mixed successful/FAILED candidate visibility and
confirmation blocking. Backend code is unchanged: 78 relevant backend items plus
5 nested subtests passed, without unnecessarily rerunning all 214. Frontend tests,
type check and build passed. The updated integration browser suite passed 9 groups
(the original 8 plus mixed-failure retention), and the standalone suite passed
its 4 cases. Both retained all 4 viewport checks and had 0 runtime errors.
The updated integration run blocked 9 inherited font requests, not 8, because
the new case navigates one additional time. No external API attempt occurred.

# TASK D weekly integration — 2026-10-19

> This file records the earlier `bcf4aba` preparation stage. For subsequent Mock
> end-to-end integration, see `LOCAL_PHOTO_MOCK.md` and `LOCAL_PHOTO_VALIDATION.md`.

## Local branch and source revisions

- Integration branch: `codex/task-d-weekly-integration`.
- Base: `codex/a-extraction-contract` at `4758dea4b7d42d573c5f850534e799bf4c49d39e`.
- B: local merge of `feature/data-backend` at `0721848aab2c4e41765ebd8e529e02d20613fe55`.
- C: local merge of `feature/frontend` at `f2f107a5eada991db9a2e9589a1ec9c2bea8aad0`.
- No remote push or merge into `main` / `develop` was performed.

## Implemented in this stage

1. B's repeat-dispensing report, reproduction cases and structured-input design
   tests are retained. The A-to-B prototype is still test-only; merging it does
   not create a production normalization entrypoint.
2. C's candidate image review component is mounted inside the existing photo
   upload area. HIRA analysis, normalization review, Current Intake and timeline
   features are retained. Family, source, date and file changes remount the image
   review session. The date default uses the Asia/Seoul date.
3. The frontend test command retains all existing integration checks and adds
   image-review checks. The optional browser test supports an explicit executable
   and selects photo mode instead of assuming it is the initial upload mode.
4. D's `backend.api.extraction_provider.extract_image_candidates` provides a
   callable Gemini-to-shared-adapter bridge. It validates caller context and basic
   image size/MIME before requests, uses the existing minimized prompt, sanitizes
   provider failures and returns unconfirmed candidates. It adds no HTTP endpoint
   and changes no shared Schema/API document.

The A branch's legacy files and JPG/MP4 assets were not imported. Its complete
latest commit is not an ancestor of this integration branch. The existing shared
parser understands legacy A `name` / `instructions` keys; provider tests exercise
that compatibility without assuming ambiguous dosage prose is a numeric dose.

## Running the checks

From the repository root, in a project Python environment:

```bash
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests backend/services -q
```

For an intentional live Gemini call, additionally install
`backend/services/extraction/requirements.txt` and supply `GEMINI_API_KEY` and
`YAKEUM_GEMINI_MODEL` through secure settings. Never put credential values in this
document. The callable takes image bytes, MIME type and `ExtractionContext`; it
is not connected to the browser or an upload endpoint yet.

From `frontend/`:

```bash
pnpm install --frozen-lockfile
pnpm test
pnpm build
pnpm dev --port 4190
```

In a second terminal, from `frontend/`, with Playwright and Chromium available:

```bash
YAKEUM_BROWSER_EXECUTABLE=/usr/bin/chromium node tests/image-review.browser.cjs
```

Use the browser executable installed on your own machine. Edge channel remains
the optional test's default when no executable is specified.

## Validation and limits

- Backend: 187 tests passed; pytest additionally reports 5 passing subtests.
- Frontend: contract, validation, API, integration-state, Current Intake/timeline,
  UX and image-review checks passed; TypeScript and Vite build passed (41 modules).
- The first browser run reached family switching, then failed because it expected
  the C-only consent heading. The selector was updated to accept the explicit
  demo-consent heading preserved in the integrated app. The final rerun passed:
  all 4 scenarios, family reset, cancellation, keyboard flow and 360/390/768/1280px
  layouts, with 0 API requests and 0 runtime errors.
- Gemini key/model and MFDS key were absent in the current process. No actual
  Gemini or MFDS call was executed. Provider tests use mocks and virtual bytes.
- Photo review still uses fixed Mock responses and local-only confirmations.
  There is no photo extraction HTTP route, confirmation storage or A-to-B runtime
  orchestration. HIRA's official-data lookup remains LOCAL_MOCK.
- Repeat-dispensing matching and unknown-strength reason policies remain open.
  This stage does not change reconciliation rules or shared contracts.

## Next integration work

Agree on the photo request/response envelope, candidate IDs, confirmation timing,
normalization entrypoint and missing-record behavior before adding a new API.
Then connect confirmed photo drafts to B and D, and exercise that full path.
Keep extraction confirmation separate from the user's current-intake decision.

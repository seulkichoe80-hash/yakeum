# TASK D: local Mock photo workflow

## Scope and source comparison

Work started from clean `codex/task-d-weekly-integration` at
`bcf4aba5c862debcdcfbaa50b277899e5f7c2c51`. A fresh fetch found these remote tips:

| Source | SHA | Relationship to starting HEAD |
| --- | --- | --- |
| A `feature/ai-extraction` | `fa475cf76bbd8d0dd09721dcb694dfa6409fdfb4` | Not an ancestor; legacy Gemini scripts and media are not imported |
| B `feature/data-backend` | `0721848aab2c4e41765ebd8e529e02d20613fe55` | Included |
| C `feature/frontend` | `f2f107a5eada991db9a2e9589a1ec9c2bea8aad0` | Included |
| `codex/a-extraction-contract` | `4758dea4b7d42d573c5f850534e799bf4c49d39e` | Included, along with earlier codex integration stages |

Commit ancestry and file differences were checked, not just names/dates. B and C
required no further merge. The A-team scripts have incompatible imports/output
and duplicate media; the existing common adapter and data-minimized prompt are
reused instead of copying those scripts wholesale. Unpushed work on team members'
computers cannot be observed. No push, PR or main/develop merge was performed.

## What runs

From **자료 등록 → photo source → 로컬 Mock 전체 연결 열기**:

1. Explicitly choose previous/current virtual source roles and dates.
2. Each panel requests a virtual A JSON fixture. Backend runs that JSON through
   the existing common extraction adapter. Images are not sent or read.
3. Review/edit each candidate and acknowledge the original. Original A results
   stay unchanged; edited snapshots are distinct. This is extraction review, not
   an intake decision or final normalized-data confirmation.
4. Request B normalization preview. `normalization/structured.py` is a real
   service entrypoint using B's matcher/name normalizer and an explicit injected
   client, not an import from the test-only design prototype.
5. Inspect original/edited/normalized snapshots and warnings. Explicitly confirm
   normalization, then run D's existing comparison and Current Intake builders.
6. Results and previous/current timeline are displayed. Intake starts UNKNOWN /
   PENDING. Only an explicit separate user action changes it; comparison results
   are not changed. Everything is ephemeral browser/request data.

The standalone C Mock remains available. HIRA keeps its existing endpoint,
response model, real XLSX parser, LOCAL_MOCK official lookup and result/timeline.
Pending HIRA requests now have abort plus generation checks: family A→B→A, file
changes and cancellation cannot revive an old response. Intake confirmation uses
the same current-first record identity as initialization.

## Local transport, not a new shared team contract

Two **experimental local-only Mock harness** routes were added:

- `POST /api/local-demo/photos/extract`: UUID family/document, source/date and a
  named virtual scenario. Response contains existing ExtractionResult objects.
- `POST /api/local-demo/photos/process`: explicit previous/current document
  descriptions plus indexed draft reviews; `normalization_confirmed=false`
  previews B results, `true` requests comparison after explicit final review.

Input models and bounds are defined in `backend/api/photo_demo.py`; client
transport is `frontend/src/photoApi.ts`. There is no uploaded image, provider
selection, live-key option or live fallback in these routes. The server recreates
original A fixtures from context rather than trusting client-supplied originals.
Same document/index deterministically recreates the same source and record IDs;
candidate position exists even when its record is null.

The transport envelope's `stage` (normalized/held/compared), snapshots and
`pending_decisions` describe local demo processing. They are **not** additions to
MedicationRecord, NormalizationResult or ReconciliationResult enums/fields.
`docs/API_CONTRACT.md`, `docs/DATA_SCHEMA.md` and HIRA response semantics remain
unchanged. No production photo endpoint has been settled. Do not deploy or treat
these routes as an authenticated record system.

## Policy memo: existing rules versus held proposals

| Topic | Existing rule / current code | Local harness behavior and unresolved decision |
| --- | --- | --- |
| Normalization timing | Exact order is open; B proposed normalize then re-normalize | Extraction acknowledgment → preview → explicit final review. A/B/D production timing still needs team agreement |
| Re-edit | B never makes a user confirmation | Any edit invalidates preview/comparison/intake. D calls B again; only explicit normalized-result review sets confirmed snapshots true |
| null record | Contract permits null; C has temporary drafts | Show and allow local inspection, but never fabricate a record/ID from the blank draft. Hold comparison; rerun extraction or defer. Manual record creation contract remains open |
| IDs and retry | System-owned IDs; reupload policy is TODO | Server adapter owns deterministic IDs per family/document/index. A new extraction in the UI starts a new document. No content hash, automatic deletion or cross-source dedup. Same previous/current document is held |
| Repeat dispensing | Preserve records; B repeat groups are diagnostic | Show all results and hold **both sides of the whole comparison**. No representative is chosen. Group/representative policy is not implemented as an agreement |
| Unknown strength/identity | Null is unknown; NEEDS_CONFIRMATION means absence from latest source | Preserve records and display a separate local processing hold. Never substitute a Reconciliation status/reason. Same-product conflicting ingredient lists are also held |

The conservative demo precondition requires both complete batches, all candidate
reviews, unambiguous Mock matches, known ingredient strengths/units and no repeat
groups. If any candidate is failed, absent, unconfirmed or unresolved, no D result
is generated at all. This deliberately prevents omission from turning into false
NEW / NOT_FOUND_IN_LATEST_SOURCE. Normalization and original snapshots still
remain inspectable. It is not a new clinical rule or production acceptance policy.

Empty ingredients remain empty (no guessed official enrichment); the service
reports PARTIAL when applicable. The minimum valid ingredient/identity policy,
production envelopes, candidate partial-success behavior, manual repair of null
records, request provenance and reupload dedup remain team decisions. HIRA's
existing repeat/unknown-strength behavior is unchanged; its known R1–R4 concerns
in B's reproduction report are not claimed fixed by this photo-only hold gate.

## Reproduce

Use the existing checkout and a project Python environment; no worktree is needed.

```bash
# repository root
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests backend/services -q
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

In a separate terminal:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm test
pnpm build
pnpm dev --port 4192
```

With Playwright and a local browser installed, from `frontend/`:

```bash
YAKEUM_TEST_URL=http://127.0.0.1:4192/ \
YAKEUM_TEST_PYTHON=/path/to/project/python \
YAKEUM_BROWSER_EXECUTABLE=/path/to/chromium \
node tests/photo-hira-integration.browser.cjs
```

On Windows set equivalent environment variables in PowerShell. Optional
`YAKEUM_PLAYWRIGHT_MODULE` selects an existing Playwright installation. The browser
suite creates and deletes virtual XLSX files in the OS temporary directory. It
uses the real local backend and blocks non-local font requests inherited from
the original HTML. It does not contact Gemini or MFDS.

## Validation

Results are recorded in `LOCAL_PHOTO_VALIDATION.md`. This stage intentionally
does not exercise actual Gemini/MFDS, login, access control, database persistence
or deployment. A successful Mock workflow is not evidence of live API readiness.

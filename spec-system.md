# PC8 Product Thinking Judge — System Spec

Version 1.4 · 15 October 2026

This document is the complete system specification for the PC8 Product Thinking
AI Judge backend. Implement exactly what is described. The rubric design baseline
is in the separate file "PC8 AI Builder Day --- Product Thin.md". Do not reopen
rubric decisions.

---

## 1. Tech Stack

| Component | Choice |
|---|---|
| Language | Python 3.11+ |
| Web framework | Flask |
| Scoring engine | jev.ai via `typesafe-sdk` pip package |
| Text extraction | `markitdown[pptx]` for native text; `python-pptx`, Pillow, and Tesseract for embedded image OCR; Poppler for rendered PDF pages; `pypdf` for page count/password checks |
| Deployment | Railway (from GitHub repo) |
| Storage | JSON on the Railway volume at `/data/results.json`; local default `results.json` |

### Dependencies (requirements.txt)
```
flask
typesafe-sdk
markitdown[pptx]
python-pptx
Pillow
pypdf[image]
```

Tesseract and Poppler are system dependencies; see README.md. The Dockerfile installs both for deployment.

---

## 2. File Structure

```
/
├── judge.py          # CLI scoring script
├── app.py            # Flask web app
├── storage.py        # shared locked, atomic result persistence
├── review.py         # human review policy and effective score calculation
├── requirements.txt
├── Dockerfile        # production dependencies and /data result path
├── railway.json      # build and healthcheck configuration
└── results.json      # local default; Railway stores this on the /data volume
```

No templates folder. All HTML is inline in `app.py` using `render_template_string`.

---

## 3. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TYPESAFE_API_KEY` | Yes | API key from jev-ai.pro |
| `RESULTS_PATH` | Optional locally | Result JSON path; local default `results.json`. Docker sets `/data/results.json`. |
| `CONFIDENCE_LOW_THRESHOLD` | Optional | Lower boundary of Medium confidence; default `0.50`. |
| `CONFIDENCE_HIGH_THRESHOLD` | Optional | Lower boundary of High confidence; default `0.80`. |
| `OCR_LANGUAGE` | Optional | Installed Tesseract language codes; default `eng`. |
| `PORT` | Railway only | Set automatically by Railway. Default to 5000 if absent. |
| `FLASK_ENV` | Optional | Set to `production` on Railway to disable debug mode. |

---

## 4. Jev.ai Integration

### Connection
```
Base URL: https://jev-ai.pro/api
Model:    jev-latest
SDK:      TypeSafeClient(api_key=..., base_url="https://jev-ai.pro/api")
```

**Important:** The user's API key is from jev-ai.pro, not api.typesafe.ai.
Always set `base_url` explicitly.

### Question type
All four criteria use the `Score` question type with 5 levels (ordered lowest to highest).

### The four questions

Each question has:
- `instructions`: the judging question + key constraints
- `criteria`: ordered list of 5 level descriptions (strings)

Judging questions and anchor descriptions must match rubric Section 5, allowing
only whitespace and score-label formatting differences. Every question includes
the shared judging instructions from rubric Sections 1, 3, 4, and 6, followed by
its criterion-specific constraints. These shared instructions are defined once
in `judge.py` as `COMMON_INSTRUCTIONS` and applied to all four questions.

### Response parsing

jev.ai returns a probability-weighted fractional score per question on its
zero-based 0–4 scale. Anchor position 0 represents rubric score 1; position 4
represents rubric score 5. Convert to the 1–5 scale before rounding.

```python
raw = response.answers[key].score        # API 0–4, e.g. 2.73
integer_score = max(1, min(5, round(raw + 1)))  # rubric 1–5: 4
probs = response.answers[key].probabilities  # dictionary keyed by API levels 0–4
distribution = [probs.get(str(k), probs.get(k, 0.0)) for k in range(5)]
confidence = response.answers[key].confidence        # float or None
band = confidence_band(confidence)  # low / medium / high / unavailable
borderline = band in ("low", "medium")
```

Store the API's confidence unchanged. It summarizes the full distribution;
it is not an individual level's probability. Results displays it as "Model
confidence" and separately displays the awarded score's probability from
`distribution[score - 1]`, matching that score's chart bar. Do not substitute
the largest probability for model confidence.

The `confidence_band` field is `low` below 0.50, `medium` from 0.50 up to
but excluding 0.80, or `high` at 0.80 and above by default. Missing or invalid
confidence is `unavailable`. The configurable thresholds must satisfy
`0 <= CONFIDENCE_LOW_THRESHOLD < CONFIDENCE_HIGH_THRESHOLD <= 1`.
The previous single `CONFIDENCE_THRESHOLD` setting is replaced by these two.

The `borderline` field is retained for compatibility as a review flag: true for
Medium and Low, false for High and Unavailable. Unavailable is explicitly
labeled in the UI and must not be interpreted as high confidence. Stored bands
and flags are recomputed from saved confidence whenever results are loaded,
without changing scores, raw values, distributions, or totals.

Band guidance is Routine review (High), Review recommended (Medium), Review
required before finalizing (Low), and Review manually (Unavailable). The human review workflow enforces required review of Low and Unavailable
criteria before finalization; Medium review remains recommended. Thresholds are initial policies, not accuracy guarantees.

Always return a single integer 1–5. Never return fractional scores to the UI.
The stored `raw` field retains the API's zero-based fractional value. Distribution
index 0 is rubric score 1, and index 4 is rubric score 5. Previously saved results
using the unshifted conversion need scores and totals recalculated from their
stored `raw` values, or must be rejudged, before comparing scores.

---

## 5. Data Schema

### Single result object (stored in results.json array)

```json
{
  "team": "Team Alpha",
  "file": "alpha_pitch.pptx",
  "judged_at": "2026-10-08T04:12:00+00:00",
  "raw_total": 13,
  "weighted_score": 26.0,
  "criteria": {
    "problem_and_user": {
      "score": 4,
      "raw": 2.821,
      "distribution": [0.02, 0.08, 0.19, 0.61, 0.10],
      "confidence": 0.84,
      "confidence_band": "high",
      "borderline": false
    },
    "problem_understanding": {
      "score": 3,
      "raw": 1.651,
      "distribution": [0.05, 0.22, 0.48, 0.21, 0.04],
      "confidence": 0.61,
      "confidence_band": "medium",
      "borderline": true
    },
    "outcomes": {
      "score": 4,
      "raw": 2.912,
      "distribution": [0.01, 0.05, 0.12, 0.68, 0.14],
      "confidence": 0.89,
      "confidence_band": "high",
      "borderline": false
    },
    "test_and_learn": {
      "score": 2,
      "raw": 0.943,
      "distribution": [0.22, 0.58, 0.15, 0.04, 0.01],
      "confidence": 0.79,
      "confidence_band": "medium",
      "borderline": true
    }
  }
}
```

### Computed fields
```
raw_total      = sum of four integer scores (range 4–20)
weighted_score = (raw_total / 20) * 40       (range 8.0–40.0)
```

### results.json
An array of result objects. Both apps use `storage.py` to append each judged
result, replacing duplicates matched by `file`. The entire read/update/write
operation is protected by a filesystem lock; the JSON file is atomically
replaced using a temporary file in the same directory, preserving other entries.
The parent directory is created on first save. Missing files return `[]`;
malformed existing JSON raises an error rather than being silently discarded.

`RESULTS_PATH` is configurable. Docker defaults to `/data/results.json`, on the
volume mounted at `/data` in Railway. Local runs default to `results.json` in
the current working directory. Uploaded documents and OCR intermediates remain
temporary files. Confidence flags/bands are refreshed after reading results.

When Railway provides `RAILWAY_VOLUME_MOUNT_PATH`, an unset `RESULTS_PATH`
defaults to `<mount>/results.json`, independent of the build method. Explicit
paths must resolve within that volume. If `RAILWAY_ENVIRONMENT_ID` is present
but no volume mount variable is available, storage raises an error instead of
using the ephemeral local fallback. Staged Railway volume additions must be
applied via Deploy Changes before they are attached to the running deployment.

---

## 6. Text Extraction

`extract_deck_content()` first extracts native slide text through the MarkItDown
CLI, then appends an OCR section for embedded raster images using Tesseract
(`--psm 11`). Each non-empty image transcription is labeled with its slide and
image number. No paraphrasing, spelling correction, or summarization is applied.

Image references are read from each slide's XML, including grouped pictures,
picture fills, and slide backgrounds. Image crop rectangles are respected and
transparent images are composited on white before OCR. Repeated images with
identical crops are OCR'd once per extraction, but retain each slide reference.

If Tesseract is absent when images are present, an image format is unsupported,
an image is linked rather than embedded, or OCR fails, extraction fails with an
explicit error identifying the slide/image instead of silently omitting it.
Decks without images do not require Tesseract.

OCR is best effort and cannot guarantee exact words. Review the extracted text
before scoring. Layout/master images, vector artwork, overlays, and the final
rendered slide appearance are outside this extraction path's coverage.

PDF uploads use `pypdf` to check encryption and page count. Every page is rendered
by Poppler (`pdftoppm -f N -l N -singlefile -r 300 -png`) and passed to Tesseract.
Output is labeled `Page N (OCR)`. Native text extraction and separate embedded
image OCR are not used for PDFs: this avoids scrambled font encodings and
repeated text from hidden OCR layers. OCR covers the rendered page, including
visible text, images, and vector artwork, without paraphrasing or correction.

Password-protected PDFs must be unlocked before upload. Missing Poppler,
malformed PDFs, rendering failures, or OCR failures raise explicit errors;
page failures include the page number. Pages are processed one at a time with
temporary images cleaned up after each page, including on failure. Rendering
and OCR each have a 120-second timeout per page. OCR can misread words or reading
order; the reviewer checks the editable preview. PDF extraction is slower than
native text extraction.

The CLI and both upload endpoints accept `.pptx` and `.pdf` case-insensitively.
Temporary files retain the uploaded extension so extraction selects the proper
format. Folder discovery accepts both formats under the same team naming rules.

In CLI mode and `/api/judge`, the extracted text is passed directly as the
`state` string to jev.ai. Do not automatically pre-process, truncate, or
summarise the extracted text.

The web UI uses `/api/extract` to populate an editable text panel. A reviewer
can correct the extracted text before submitting it to `/api/judge-text`.
That endpoint passes the submitted text unchanged to jev.ai, including
surrounding whitespace; use a whitespace-trimmed copy only to validate that
the input is non-empty. The Text preview page shows the original extraction,
which may differ from text edited on the Judge page.

---

## 7. judge.py — CLI Script

### Usage
```
python judge.py <path-to-file.pptx-or-pdf>      # judge one deck
python judge.py <path-to-folder>          # batch judge all teams
```

### Single file mode
1. Extract text from the `.pptx` or `.pdf`
2. Score via jev.ai
3. Build result object with team name derived from `pptx_path.stem`
4. Call `storage.store_result(result)` to save to the configured `RESULTS_PATH`
5. Under an exclusive lock, load existing results (empty list if not found)
6. Replace any entry with the same `file` value and append the new result
7. Atomically replace the JSON file before releasing the lock
8. Print formatted result to terminal

### Batch mode (folder)

**Folder structure expected:**
```
submissions/
├── Team Alpha/
│   └── pitch.pptx
├── Team Beta/
│   └── deck.pptx
```

Each direct subfolder = one team. The subfolder name becomes the `team` field.
If `.pptx` or `.pdf` files exist directly in root (no subfolders), use the filename stem as team name.
If a subfolder contains multiple supported files, judge each one separately.

**Processing:**
1. Discover all `(team_name, pptx_path)` pairs for `.pptx` and `.pdf` files
2. Load existing results from the configured `RESULTS_PATH`
3. For each pair, skip if `pptx_path.name` already in results
4. Judge and call `storage.store_result(result)` immediately after each team;
   update the in-memory results and already-judged filenames after each save
5. On error for one team: print error, continue to next team
6. Print summary at end: "{N} result(s) in {RESULTS_PATH}"

**Skipping already-judged files** prevents data loss if the script is interrupted
and rerun. Matched by filename only (not team name).

### Terminal output format (per deck)
```
[JUDGING] Team Alpha / alpha_pitch.pptx
  Extracting text...
  Sending to jev.ai...

================================================================
PRODUCT THINKING ASSESSMENT — Team Alpha
================================================================

PROBLEM & USER
  Score: 4  (4 - Strong)
  Distribution: L1:2%  L2:8%  L3:19%  L4:61%  L5:10%
  Confidence: 84%

PROBLEM UNDERSTANDING
  Score: 3  (3 - Good)  ⚠ medium confidence
  ...

Raw rubric score:           13/20
Weighted competition score: 26/40
================================================================
  ✓ Saved to results.json
```

---

## 8. app.py — Flask Web App

### Startup
```python
port = int(os.environ.get("PORT", 5000))
debug = os.environ.get("FLASK_ENV") != "production"
app.run(host="0.0.0.0", port=port, debug=debug)
```

### Routes

#### GET /
Renders the full single-page app HTML (all four pages as divs).

#### POST /api/judge
Accepts multipart form upload with field name `file`.

Validation:
- File must be present → 400 if missing
- File must have `.pptx` or `.pdf` extension (case-insensitive) → 400 if not

Processing:
1. Save uploaded file to a temp path
2. Extract native text and embedded image text via `extract_deck_content`
3. Score via jev.ai
4. Build and save result object
5. Return JSON result object
6. On any error → return `{"error": "..."}` with status 500

#### POST /api/judge-text
Accepts form fields: `text` (required), `team`, `filename`.

Validation:
- `text` must be non-empty → 400 if missing

Processing:
1. Score the provided text via jev.ai (no extraction step)
2. Build and save result object using `team` and `filename` form fields
3. Return JSON result object
4. On any error → return `{"error": "..."}` with status 500

#### POST /api/extract
Accepts multipart form upload with field name `file`.

Validation:
- File must be present → 400 if missing
- File must have `.pptx` or `.pdf` extension (case-insensitive) → 400 if not

Processing:
1. Save uploaded file to a temp path
2. Extract native text and embedded image text via `extract_deck_content`
3. Return `{"text": "<extracted markdown>"}` as JSON
4. On any error → return `{"error": "..."}` with status 500

#### GET /api/results
Returns summarized result objects as JSON, including effective scores and review
status, but omitting `assessed_text` and `review_history` (available via detail).
Returns `[]` if file not found.
Reads the configured storage path and refreshes confidence bands/review flags
before returning the response. The UI does not access a filesystem path directly.

### Imports from judge.py
`app.py` imports `extract_deck_content`, `score_deck`, `CRITERIA_ORDER`,
`SUPPORTED_EXTENSIONS`, and `CRITERIA` from `judge.py`. `review.py` supplies
the result-summary, review, finalization, and conflict-handling functions.
Do not duplicate the rubric definitions or jev.ai logic in `app.py`.

### Shared storage
Both apps import `storage.load_results` as `read_results` and use
`storage.store_result` for every judged result. Human review mutations use
`storage.update_result`, under the same exclusive lock and atomic replacement. Their `load_results` wrappers
refresh confidence flags after reading. Do not implement separate JSON writers
or an unlocked load/update/save sequence in either app. `judge.py` also uses
`storage.results_path` to report the actual save location in terminal output.

### Navigation
All four pages (Criteria, Results, Judge a deck, Text preview) are rendered as `<div>` elements
in a single HTML response. JavaScript shows/hides them on nav click. No separate
routes per page.

---

## 9. LLM Rationale Step (placeholder)

A second step after `score_deck()` is planned but not yet implemented.
It will accept a prompt and call an LLM to generate Evidence and Rationale
text for each criterion in the format defined in Section 9 of the rubric document.

Traceable evidence, rationale, and exceptional reviewer flags from rubric
Sections 7–9 are deferred to this step. Current UI flags indicate only the
computed `borderline` value; they are not the full rubric Reviewer Flags.
The scoring instructions already require using coherent evidence without
inventing a reconciliation of contradictory claims.

Add a `# TODO: LLM rationale step` comment in `judge.py` after the `score_deck()` call.

When implemented, add these fields to each criterion in the result schema:
```json
"evidence": "Slides 2 and 13 identify...",
"rationale": "The submission clearly identifies..."
```

Do not implement this step now.

---

## 10. Deployment (Railway)

1. Push `judge.py`, `app.py`, `storage.py`, `review.py`, `requirements.txt`, and `Dockerfile` to GitHub repo root
2. Railway builds the Dockerfile, installing Python dependencies, Tesseract, and Poppler, then starts `app.py`
   `railway.json` selects the Dockerfile builder and `/` startup healthcheck.
   Keep the service root at the repository root and clear custom build/start commands.
3. Set environment variables in Railway dashboard:
   - `TYPESAFE_API_KEY` = jev-ai.pro API key
   - `FLASK_ENV` = production
4. Generate domain: Railway Settings → Networking → Generate Domain
5. Attach the persistent volume to the app service at `/data`. The Dockerfile
   sets `RESULTS_PATH=/data/results.json`; clear any conflicting Railway override.
   Results written on the mounted volume survive deployments and restarts.
   Export and transfer existing ephemeral results before replacing the old
   container; attaching a volume does not migrate its old `results.json`.


## 11. Human review and score overrides

Prototype access is open, as requested; no password or authentication is required.
Every review/finalization requires a non-empty reviewer name (max 100 characters).
Names are self-reported. Review text and saved assessment text are escaped in UI.

AI `criteria[key].score`, `raw`, `distribution`, `confidence`, `raw_total`, and
`weighted_score` remain unchanged by human review. Add optional `human_review`
with `score` (integer 1–5), `status` (`confirmed` or `overridden`), `reviewer`,
`rationale`, `evidence_refs`, and `reviewed_at`. A reset removes the active human
review and restores pending status, but retains the audit event.

Derived fields include per-criterion `effective_score` and `review_status`;
result `effective_raw_total`, `effective_weighted_score` (sum × 2),
`pending_review` (unreviewed Medium/Low/Unavailable keys), `required_review`
(unreviewed Low/Unavailable keys), `review_revision`, and `submission_status`
(`provisional`, `reviewed` when all criteria reviewed, or `finalized`).
Leaderboard sorting and aggregate statistics use effective scores. Finalization
is only permitted when all four criteria exist and `required_review` is empty.
Medium reviews can remain pending after finalization. A human edit clears active
finalization and advances the review revision.

New web and CLI assessments save `assessed_text`, the exact extracted/edited text
passed to Jev. Existing results without text display a missing-text explanation.
The original uploaded document remains temporary; no document viewer is added.

### Review endpoints

- `GET /api/results/detail?file=<filename>` returns `{result, anchors}` with
  saved assessed text, audit history, and the five rubric descriptions per key.
  Missing submissions return 404.
- `POST /api/results/review` accepts JSON `file`, `judged_at`, `revision`,
  `reviewer`, `criterion`, `action` (`confirm`, `override`, `reset`). Overrides
  additionally require `score`, non-empty `rationale` (max 5000 characters), and
  non-empty `evidence_refs` (max 2000 characters). Confirm uses the original AI
  score regardless of the form score. Reset uses the original AI score/pending.
- `POST /api/results/finalize` accepts JSON `file`, `judged_at`, `revision`,
  `reviewer`. Finalization records the actor/time and effective total in history.
- Validation errors return 400; missing files 404; stale assessment timestamps or
  review revisions 409; storage write failures 500. Mutations perform the version
  check and write in a single locked transaction to prevent lost review updates.

`review_history` records actions, actors, timestamps, assessment timestamps,
previous/new review values, and prior finalization when applicable. Rejudging the
same filename clears active reviews/finalization and preserves history plus a
`rejudged` event containing the previous assessment (excluding nested history).
No previous override is automatically applied to a newly scored deck.

Human rationales are separate from the deferred LLM evidence/rationale step.

## 12. Deleting a result

`POST /api/results/delete` accepts JSON `file`, `judged_at`, and integer
`revision`. Under the same storage lock, locate the filename, verify the
assessment timestamp/review revision, remove that result, and atomically write
the remaining array. Deletion removes its saved text, scores, active human
reviews, finalization, and history. Other submissions remain unchanged.

Return `{"deleted": "<filename>"}` on success; 400 for malformed input, 404 for
a missing submission, 409 for a stale timestamp/revision, or 500 for a write
failure. Deleting the final result leaves `[]`. The same file can be judged
again after deletion. Deletion uses the prototype's existing open-access policy.

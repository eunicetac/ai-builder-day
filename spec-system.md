# PC8 Product Thinking Judge — System Spec

Version 1.1 · 9 October 2026

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
| Storage | Local filesystem (`results.json`); Railway filesystem is ephemeral |

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
├── requirements.txt
└── results.json      # written by judge.py, read by app.py (gitignored or committed)
```

No templates folder. All HTML is inline in `app.py` using `render_template_string`.

---

## 3. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TYPESAFE_API_KEY` | Yes | API key from jev-ai.pro |
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

jev.ai returns a probability-weighted fractional score per question.

```python
raw = response.answers[key].score        # float, e.g. 2.73
integer_score = max(1, min(5, round(raw)))
borderline = abs(raw - round(raw)) > 0.35
distribution = response.answers[key].probabilities   # list of 5 floats
confidence = response.answers[key].confidence        # float or None
```

Store the API's confidence unchanged. It summarizes the full distribution;
it is not an individual level's probability. Results displays it as "Model
confidence" and separately displays the awarded score's probability from
`distribution[score - 1]`, matching that score's chart bar. Do not substitute
the largest probability for model confidence.

Always return a single integer 1–5. Never return fractional scores to the UI.

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
      "raw": 3.821,
      "distribution": [0.02, 0.08, 0.19, 0.61, 0.10],
      "confidence": 0.84,
      "borderline": false
    },
    "problem_understanding": {
      "score": 3,
      "raw": 2.651,
      "distribution": [0.05, 0.22, 0.48, 0.21, 0.04],
      "confidence": 0.71,
      "borderline": true
    },
    "outcomes": {
      "score": 4,
      "raw": 3.912,
      "distribution": [0.01, 0.05, 0.12, 0.68, 0.14],
      "confidence": 0.89,
      "borderline": false
    },
    "test_and_learn": {
      "score": 2,
      "raw": 1.943,
      "distribution": [0.22, 0.58, 0.15, 0.04, 0.01],
      "confidence": 0.79,
      "borderline": false
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
An array of result objects. Written incrementally — appended after each team is judged.
Never fully overwritten; new results are appended and duplicates (matched by `file`) are replaced.

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
4. Load existing `results.json` (empty list if not found)
5. Remove any existing entry with the same `file` value
6. Append new result
7. Write `results.json`
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
2. Load existing `results.json`
3. For each pair, skip if `pptx_path.name` already in results
4. Judge, append result, write `results.json` immediately after each team
5. On error for one team: print error, continue to next team
6. Print summary at end: "{N} result(s) in results.json"

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
  Score: 3  (3 - Good)  ⚠ borderline
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
Returns the full `results.json` array as JSON.
Returns `[]` if file not found.

### Imports from judge.py
`app.py` imports `extract_deck_content`, `score_deck`, and `CRITERIA_ORDER` from `judge.py`.
Do not duplicate the rubric definitions or jev.ai logic in `app.py`.

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

1. Push `judge.py`, `app.py`, `requirements.txt`, and `Dockerfile` to GitHub repo root
2. Railway builds the Dockerfile, installing Python dependencies, Tesseract, and Poppler, then starts `app.py`
   `railway.json` selects the Dockerfile builder and `/` startup healthcheck.
   Keep the service root at the repository root and clear custom build/start commands.
3. Set environment variables in Railway dashboard:
   - `TYPESAFE_API_KEY` = jev-ai.pro API key
   - `FLASK_ENV` = production
4. Generate domain: Railway Settings → Networking → Generate Domain
5. `results.json` does not persist across Railway restarts. Commit it to the
   repo after running `judge.py` locally, or re-run judging after each deploy.

# ai-builder-day

Extracts native PPTX text with MarkItDown and transcribes embedded slide images
with Tesseract OCR. PDFs are rendered with Poppler at 300 DPI, then each visible
page is OCR'd. Both the CLI and web extraction use the same output, with slide
image or PDF page references and no summarization.

Install Python dependencies with `pip install -r requirements.txt`.
Install OCR/rendering tools locally with `brew install tesseract poppler` (macOS)
or `apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils` (Debian/Ubuntu).
The Dockerfile includes Tesseract and Poppler for Railway deployments.

## Railway

Deploy this repository from GitHub with the service root set to the repository
root. `railway.json` selects the Dockerfile and checks `/` after startup.
Tesseract, English OCR data, and Poppler are installed inside the Railway container;
you do not need Tesseract on your laptop to run the hosted app.

In Railway service Variables, set `TYPESAFE_API_KEY` to your jev.ai key.
`OCR_LANGUAGE=eng` is optional. The Dockerfile sets `FLASK_ENV=production`;
the app listens on `0.0.0.0` and Railway's `PORT` automatically.
Clear any custom Build or Start Command so Railway uses the Dockerfile's
build steps and `python app.py` command. Generate a public domain under
Settings → Networking, then upload a PPTX or PDF on Text preview to check OCR.

Attach the Railway volume to the app service at `/data`. The Dockerfile sets
`RESULTS_PATH=/data/results.json`, so results persist on that volume across
deployments and restarts. Clear any old Railway `RESULTS_PATH` override or set
it to `/data/results.json`. Both the CLI and web app share this storage path.
Local development defaults to `results.json`; override `RESULTS_PATH` if needed.
Result updates are locked and written atomically to support concurrent requests.
Uploaded files and OCR intermediates are temporary and are not stored on the volume.

Commit/push these changes and redeploy to enable the new path. Existing results
in the old container are not automatically migrated: export `/api/results`
before replacing it and transfer that JSON array to `/data/results.json`
before saving new results. Do not replace an existing populated volume file
with an old export; merge by filename instead. Configure volume backups in Railway.

Set `OCR_LANGUAGE` to installed Tesseract language codes (default `eng`, e.g.
`eng+chi_sim` after installing the corresponding language data).

OCR can misread small, blurred, handwritten, or stylized words; check the editable
preview before judging. Cropped images are OCR'd within their crop rectangle.
Extraction covers embedded raster images in slides, groups, picture fills, and
slide backgrounds. It does not render slides: image text inherited from layouts
or masters, vector artwork, and text covered by other shapes are not reliably
handled. Linked images and unsupported image formats produce an explicit error.

PDF files use the same upload, editable preview, judging, results, and CLI flows
as PPTX files. Each rendered page is OCR'd once, covering visible text, scans,
images, and vector text. This bypasses corrupt font-to-text mappings and avoids
combining hidden OCR layers with image transcriptions. Password-protected PDFs
must be unlocked first. Output is labeled `Page N (OCR)`. OCR may still misread
words or reading order; review the editable preview. Rendering/OCR takes longer
than native text extraction, particularly on long PDFs.

Confidence is shown in three bands: High (≥80%), Medium (50–<80%), and Low
(<50%). Missing/invalid confidence is Unavailable. Configure boundaries through
`CONFIDENCE_LOW_THRESHOLD` (default `0.50`) and `CONFIDENCE_HIGH_THRESHOLD`
(default `0.80`) in Railway Variables. The old `CONFIDENCE_THRESHOLD` setting
is no longer used. Boundaries must satisfy `0 <= LOW < HIGH <= 1`.

Saved results get their bands refreshed when loaded. Scores and totals stay
unchanged. The compatibility `borderline` flag now marks Medium/Low for review.
Band guidance is Routine review (High), Review recommended (Medium), and Review
required before finalizing (Low); the human review/finalization workflow is not
yet implemented. Calibrate these initial thresholds using human assessments.

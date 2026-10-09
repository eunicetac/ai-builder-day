# ai-builder-day

Extracts native PPTX text with MarkItDown and transcribes embedded slide images
with Tesseract OCR. Both the CLI and web extraction use this combined output.
Image text is labeled with slide and image numbers, without summarizing it.

Install Python dependencies with `pip install -r requirements.txt`.
Install Tesseract locally with `brew install tesseract` (macOS) or
`apt-get install tesseract-ocr tesseract-ocr-eng` (Debian/Ubuntu).
The Dockerfile includes Tesseract for Railway deployments.

## Railway

Deploy this repository from GitHub with the service root set to the repository
root. `railway.json` selects the Dockerfile and checks `/` after startup.
Tesseract and English OCR data are installed inside the Railway container;
you do not need Tesseract on your laptop to run the hosted app.

In Railway service Variables, set `TYPESAFE_API_KEY` to your jev.ai key.
`OCR_LANGUAGE=eng` is optional. The Dockerfile sets `FLASK_ENV=production`;
the app listens on `0.0.0.0` and Railway's `PORT` automatically.
Clear any custom Build or Start Command so Railway uses the Dockerfile's
build steps and `python app.py` command. Generate a public domain under
Settings → Networking, then upload a PPTX on Text preview to check OCR.

The OCR changes and deployment files must be committed and pushed before
Railway can build them. Results use the container filesystem and are lost
when it is replaced, unless you configure persistent storage separately.

Set `OCR_LANGUAGE` to installed Tesseract language codes (default `eng`, e.g.
`eng+chi_sim` after installing the corresponding language data).

OCR can misread small, blurred, handwritten, or stylized words; check the editable
preview before judging. Cropped images are OCR'd within their crop rectangle.
Extraction covers embedded raster images in slides, groups, picture fills, and
slide backgrounds. It does not render slides: image text inherited from layouts
or masters, vector artwork, and text covered by other shapes are not reliably
handled. Linked images and unsupported image formats produce an explicit error.

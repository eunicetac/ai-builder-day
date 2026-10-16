import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from pptx.oxml import parse_xml

import judge
import app
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject


def slide_with_image(blob, crop="", relationship='r:embed="rId1"'):
    element = parse_xml(
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<p:spTree><p:grpSp><p:pic><p:blipFill><a:blip {relationship}/>{crop}'
        '</p:blipFill></p:pic></p:grpSp></p:spTree></p:sld>'
    )
    return SimpleNamespace(element=element, part=SimpleNamespace(
        related_part=lambda relationship: SimpleNamespace(blob=blob)))


class ExtractionTests(unittest.TestCase):
    def test_native_text_and_ocr_are_preserved_with_slide_references(self):
        slides = [slide_with_image(b"image"), slide_with_image(b"image")]
        with patch.object(judge, "Presentation", return_value=SimpleNamespace(slides=slides)), \
                patch.object(judge, "ocr_image", return_value="Exact words: 42%") as ocr, \
                patch.object(judge.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stdout="Native words\n", stderr="")):
            text = judge.extract_deck_content(Path("deck.pptx"))
        self.assertTrue(text.startswith("Native words\n\n"))
        self.assertEqual(text.count("Exact words: 42%"), 2)
        self.assertIn("Slide 1 — Image 1", text)
        self.assertIn("Slide 2 — Image 1", text)
        ocr.assert_called_once_with(b"image", (0, 0, 0, 0))

    def test_crops_have_separate_cache_entries(self):
        slides = [slide_with_image(b"image"),
                  slide_with_image(b"image", '<a:srcRect l="25000"/>')]
        with patch.object(judge, "Presentation", return_value=SimpleNamespace(slides=slides)), \
                patch.object(judge, "ocr_image", return_value="text") as ocr:
            judge.extract_image_text(Path("deck.pptx"))
        self.assertEqual(ocr.call_count, 2)
        self.assertEqual(ocr.call_args.args[1], (0.25, 0, 0, 0))

    def test_linked_images_fail_explicitly(self):
        slide = slide_with_image(b"image", relationship='r:link="rId1"')
        with patch.object(judge, "Presentation", return_value=SimpleNamespace(slides=[slide])):
            with self.assertRaisesRegex(RuntimeError, "Slide 1: linked image"):
                judge.extract_image_text(Path("deck.pptx"))

    def test_missing_tesseract_fails_explicitly(self):
        with patch.object(judge.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Tesseract OCR is not installed"):
                judge.ocr_image(b"image", (0, 0, 0, 0))

    def test_ocr_receives_cropped_image_and_preserves_words(self):
        buffer = io.BytesIO()
        Image.new("RGBA", (100, 80), (0, 0, 0, 0)).save(buffer, format="PNG")

        def run(command, **kwargs):
            with Image.open(command[1]) as image:
                self.assertEqual(image.size, (75, 80))
                self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
            self.assertEqual(command[-2:], ["--psm", "11"])
            return subprocess.CompletedProcess(command, 0, "Exact words: 42%\n", "")

        with patch.object(judge.shutil, "which", return_value="tesseract"), \
                patch.object(judge.subprocess, "run", side_effect=run):
            self.assertEqual(judge.ocr_image(buffer.getvalue(), (0.25, 0, 0, 0)), "Exact words: 42%")


class PdfExtractionTests(unittest.TestCase):
    def make_pdf(self, path):
        writer = PdfWriter()
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        image = DecodedStreamObject()
        image.set_data(bytes([255, 255, 255] * 4))
        image.update({NameObject("/Type"): NameObject("/XObject"),
                      NameObject("/Subtype"): NameObject("/Image"),
                      NameObject("/Width"): NumberObject(2), NameObject("/Height"): NumberObject(2),
                      NameObject("/BitsPerComponent"): NumberObject(8),
                      NameObject("/ColorSpace"): NameObject("/DeviceRGB")})
        image_reference = writer._add_object(image)
        for index in range(2):
            page = writer.add_blank_page(width=300, height=300)
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
                NameObject("/XObject"): DictionaryObject({NameObject("/Im1"): image_reference})})
            content = DecodedStreamObject()
            native = b"BT /F1 12 Tf 10 280 Td (Native words: 42%) Tj ET\n" if index == 0 else b""
            content.set_data(native + b"q 100 0 0 100 10 10 cm /Im1 Do Q")
            page[NameObject("/Contents")] = writer._add_object(content)
        writer.write(path)

    def test_pdf_ocr_reads_rendered_pages_without_using_native_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deck.PDF"
            self.make_pdf(path)
            def render(command, **kwargs):
                page_number = command[command.index("-f") + 1]
                self.assertEqual(command[command.index("-l") + 1], page_number)
                self.assertIn("-singlefile", command)
                self.assertEqual(command[command.index("-r") + 1], "300")
                self.assertEqual(command[command.index("-scale-to") + 1], "2400")
                Path(command[-1]).with_suffix(".png").write_bytes(b"rendered page " + page_number.encode())
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(judge.shutil, "which", return_value="pdftoppm"), \
                    patch.object(judge.subprocess, "run", side_effect=render), \
                    patch("pypdf._page.PageObject.extract_text", side_effect=AssertionError("Do not use font codes")), \
                    patch.object(judge, "ocr_image", side_effect=["Book rooms with locals, rather than hotels.", "Image words: 99%"] ) as ocr:
                text = judge.extract_deck_content(path)
            self.assertNotIn("Native words: 42%", text)
            self.assertIn("Book rooms with locals, rather than hotels.", text)
            self.assertIn("Page 1 (OCR)", text)
            self.assertIn("Page 2 (OCR)", text)
            self.assertEqual(ocr.call_count, 2)
            self.assertEqual(ocr.call_args_list[0].args[0], b"rendered page 1")
            self.assertEqual(ocr.call_args_list[1].args[0], b"rendered page 2")

    def test_pdf_rendering_failure_identifies_page(self):
        reader = SimpleNamespace(is_encrypted=False, pages=[None])
        with patch.object(judge, "PdfReader", return_value=reader), \
                patch.object(judge.shutil, "which", return_value="pdftoppm"), \
                patch.object(judge.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "bad PDF")):
            with self.assertRaisesRegex(RuntimeError, "PDF page 1: PDF rendering failed: bad PDF"):
                judge.extract_pdf_content(Path("bad.pdf"))

    def test_password_protected_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locked.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            writer.encrypt("secret")
            writer.write(path)
            with self.assertRaisesRegex(RuntimeError, "password-protected"):
                judge.extract_deck_content(path)

    def test_upload_routes_accept_pdf_and_keep_temporary_extension(self):
        client = app.app.test_client()
        criteria = {key: {"score": 3} for key in judge.CRITERIA_ORDER}
        for route in ("/api/extract", "/api/judge"):
            with patch.object(app, "extract_deck_content", return_value="PDF words") as extract, \
                    patch.object(app, "score_deck", return_value=criteria), \
                    patch.object(app, "load_results", return_value=[]), \
                    patch.object(app, "store_result"):
                response = client.post(route, data={"file": (io.BytesIO(b"pdf"), "Alpha.PDF")})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(extract.call_args.args[0].suffix, ".pdf")
            if route == "/api/judge":
                self.assertEqual(response.json["file"], "Alpha.PDF")
                self.assertEqual(response.json["team"], "Alpha")
                self.assertEqual(response.json["weighted_score"], 24)
            response = client.post(route, data={"file": (io.BytesIO(b"bad"), "bad.txt")})
            self.assertEqual(response.status_code, 400)

    def test_mixed_cli_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("one.pptx", "two.PDF", "ignored.txt"):
                (root / name).touch()
            self.assertEqual({path.name for team, path in judge.discover_pairs(root)}, {"one.pptx", "two.PDF"})


if __name__ == "__main__":
    unittest.main()

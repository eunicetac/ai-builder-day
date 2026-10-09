import io
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from pptx.oxml import parse_xml

import judge


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


if __name__ == "__main__":
    unittest.main()

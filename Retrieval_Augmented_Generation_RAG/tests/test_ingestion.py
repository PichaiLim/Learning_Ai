"""
Unit tests for ingestion.py
Tests all functions: utility, PDF processing, OCR, markdown/manifest writing, and orchestration.
"""
import unittest
import tempfile
import shutil
import os
import sys
import json
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta

# Add parent directory to path to import ingestion
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Pre-mock external dependencies that may not be installed ──
# These must be mocked BEFORE importing ingestion so the top-level
# imports in ingestion.py don't raise ModuleNotFoundError.
for mod_name in ["requests", "fitz", "ollama", "PIL", "PIL.Image", "dotenv"]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Patch load_dotenv to be a no-op so it doesn't fail at import time
sys.modules["dotenv"].load_dotenv = MagicMock()

import ingestion

# Restore real hashlib / os / json / re that ingestion also imports
# (they are stdlib and always available, but just in case)
import importlib
importlib.reload(ingestion)  # re-import with mocks in place


# ─────────────────────────────────────────────────────────────
# 1. Utility Functions
# ─────────────────────────────────────────────────────────────

class TestNowIsoBkk(unittest.TestCase):
    """Tests for now_iso_bkk()."""

    def test_returns_iso_format_string(self):
        """Result should be a valid ISO 8601 string."""
        result = ingestion.now_iso_bkk()
        self.assertIsInstance(result, str)
        # Should be parseable by datetime
        parsed = datetime.fromisoformat(result)
        self.assertIsNotNone(parsed)

    def test_timezone_is_bangkok(self):
        """Timezone offset should be +07:00."""
        result = ingestion.now_iso_bkk()
        self.assertTrue(result.endswith("+07:00"))


class TestEnsureDir(unittest.TestCase):
    """Tests for ensure_dir()."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_new_directory(self):
        """Should create a directory that doesn't exist."""
        new_dir = os.path.join(self.temp_dir, "new_subdir", "deep")
        self.assertFalse(os.path.exists(new_dir))
        ingestion.ensure_dir(new_dir)
        self.assertTrue(os.path.isdir(new_dir))

    def test_existing_directory_no_error(self):
        """Should not raise when directory already exists."""
        ingestion.ensure_dir(self.temp_dir)  # already exists
        self.assertTrue(os.path.isdir(self.temp_dir))


class TestSlugifyFilename(unittest.TestCase):
    """Tests for slugify_filename()."""

    def test_removes_extension(self):
        """Should strip the file extension."""
        self.assertNotIn(".pdf", ingestion.slugify_filename("report.pdf"))

    def test_strips_directory_path(self):
        """Should only use the basename."""
        result = ingestion.slugify_filename("/some/path/to/report.pdf")
        self.assertEqual(result, "report")

    def test_replaces_special_characters(self):
        """Special chars (spaces, symbols) should become underscores."""
        result = ingestion.slugify_filename("my report (v2).pdf")
        # Should not contain spaces or parentheses
        self.assertNotIn(" ", result)
        self.assertNotIn("(", result)
        self.assertNotIn(")", result)

    def test_keeps_alphanumeric_and_hyphens(self):
        """Alphanumeric characters and hyphens should be preserved."""
        result = ingestion.slugify_filename("my-report_v2.pdf")
        self.assertEqual(result, "my-report_v2")

    def test_unicode_word_chars_preserved(self):
        """Thai/Unicode word characters should be preserved (\\w flag)."""
        result = ingestion.slugify_filename("เอกสาร.pdf")
        # Thai chars are \\w with re.UNICODE, so they should remain
        self.assertGreater(len(result), 0)


class TestSha1OfFile(unittest.TestCase):
    """Tests for sha1_of_file()."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_correct_hash(self):
        """Hash should match python hashlib sha1 of same content."""
        content = b"hello world test content"
        filepath = os.path.join(self.temp_dir, "test.bin")
        with open(filepath, "wb") as f:
            f.write(content)

        expected = hashlib.sha1(content).hexdigest()
        self.assertEqual(ingestion.sha1_of_file(filepath), expected)

    def test_empty_file(self):
        """Hash of empty file should match sha1 of empty bytes."""
        filepath = os.path.join(self.temp_dir, "empty.bin")
        with open(filepath, "wb") as f:
            pass  # empty

        expected = hashlib.sha1(b"").hexdigest()
        self.assertEqual(ingestion.sha1_of_file(filepath), expected)


# ─────────────────────────────────────────────────────────────
# 2. PDF Listing
# ─────────────────────────────────────────────────────────────

class TestListPdfs(unittest.TestCase):
    """Tests for list_pdfs()."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_finds_pdf_files(self):
        """Should return paths to .pdf files."""
        for name in ["a.pdf", "b.PDF", "c.txt", "d.png"]:
            with open(os.path.join(self.temp_dir, name), "w") as f:
                f.write("x")

        result = ingestion.list_pdfs(self.temp_dir)
        basenames = [os.path.basename(p) for p in result]
        self.assertIn("a.pdf", basenames)
        self.assertIn("b.PDF", basenames)
        self.assertNotIn("c.txt", basenames)
        self.assertNotIn("d.png", basenames)

    def test_finds_pdfs_in_subdirectories(self):
        """Should walk subdirectories."""
        subdir = os.path.join(self.temp_dir, "sub")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "nested.pdf"), "w") as f:
            f.write("x")

        result = ingestion.list_pdfs(self.temp_dir)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].endswith("nested.pdf"))

    def test_empty_directory(self):
        """Should return empty list when no PDFs exist."""
        result = ingestion.list_pdfs(self.temp_dir)
        self.assertEqual(result, [])

    def test_returns_sorted(self):
        """Result list should be sorted."""
        for name in ["c.pdf", "a.pdf", "b.pdf"]:
            with open(os.path.join(self.temp_dir, name), "w") as f:
                f.write("x")

        result = ingestion.list_pdfs(self.temp_dir)
        self.assertEqual(result, sorted(result))


# ─────────────────────────────────────────────────────────────
# 3. PDF → Images
# ─────────────────────────────────────────────────────────────

class TestPdfToImages(unittest.TestCase):
    """Tests for pdf_to_images() — mocks fitz (PyMuPDF)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("ingestion.fitz")
    def test_returns_page_info_list(self, mock_fitz):
        """Should return a list of dicts with page, image_path, width, height."""
        # Setup mock document with 2 pages
        mock_pix = MagicMock()
        mock_pix.width = 2550
        mock_pix.height = 3300
        mock_pix.save = MagicMock()

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)
        mock_doc.load_page.return_value = mock_page

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix.return_value = MagicMock()

        out_dir = os.path.join(self.temp_dir, "images")
        result = ingestion.pdf_to_images("fake.pdf", out_dir, dpi=300)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["page"], 1)
        self.assertEqual(result[1]["page"], 2)
        self.assertEqual(result[0]["width"], 2550)
        self.assertEqual(result[0]["height"], 3300)
        self.assertTrue(result[0]["image_path"].endswith(".png"))

    @patch("ingestion.fitz")
    def test_creates_output_directory(self, mock_fitz):
        """Should create the output directory."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=0)
        mock_fitz.open.return_value = mock_doc

        out_dir = os.path.join(self.temp_dir, "new_img_dir")
        ingestion.pdf_to_images("fake.pdf", out_dir)
        self.assertTrue(os.path.isdir(out_dir))

    @patch("ingestion.fitz")
    def test_closes_document(self, mock_fitz):
        """Should close the fitz document after processing."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=0)
        mock_fitz.open.return_value = mock_doc

        out_dir = os.path.join(self.temp_dir, "img")
        ingestion.pdf_to_images("fake.pdf", out_dir)
        mock_doc.close.assert_called_once()


# ─────────────────────────────────────────────────────────────
# 4. Image Resizing
# ─────────────────────────────────────────────────────────────

class TestResizeImage(unittest.TestCase):
    """Tests for resize_image() — mocks PIL."""

    @patch("ingestion.Image")
    def test_no_resize_when_within_limit(self, mock_Image):
        """Should return original path when image is small enough."""
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        mock_Image.open.return_value = mock_img

        result = ingestion.resize_image("photo.png", max_dim=1024)
        self.assertEqual(result, "photo.png")

    @patch("ingestion.Image")
    def test_resize_when_exceeds_limit(self, mock_Image):
        """Should resize and return new path with _resized suffix."""
        mock_img = MagicMock()
        mock_img.size = (2000, 1500)
        mock_resized = MagicMock()
        mock_img.resize.return_value = mock_resized
        mock_Image.open.return_value = mock_img
        mock_Image.LANCZOS = "LANCZOS"

        result = ingestion.resize_image("photo.png", max_dim=1024)
        self.assertTrue(result.endswith("_resized.png"))
        mock_img.resize.assert_called_once()
        mock_resized.save.assert_called_once()

    @patch("ingestion.Image")
    def test_resize_exact_boundary(self, mock_Image):
        """Image exactly at max_dim should NOT be resized."""
        mock_img = MagicMock()
        mock_img.size = (1024, 512)
        mock_Image.open.return_value = mock_img

        result = ingestion.resize_image("photo.png", max_dim=1024)
        self.assertEqual(result, "photo.png")


# ─────────────────────────────────────────────────────────────
# 5. OCR via Ollama
# ─────────────────────────────────────────────────────────────

class TestOcrImageViaOllama(unittest.TestCase):
    """Tests for ocr_image_via_ollama() — mocks ollama.Client and file I/O."""

    @patch("ingestion.ollama.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_bytes")
    def test_returns_markdown_text(self, mock_file, mock_client_cls):
        """Should return the content from ollama response."""
        mock_response = MagicMock()
        mock_response.message.content = "# OCR Result\nSome text"
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = ingestion.ocr_image_via_ollama(
            image_path="test.png",
            model="test-model",
            ollama_url="http://localhost:11434",
        )
        self.assertEqual(result, "# OCR Result\nSome text")

    @patch("ingestion.ollama.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_bytes")
    def test_client_created_with_correct_params(self, mock_file, mock_client_cls):
        """Should create Client with correct host and timeout."""
        mock_response = MagicMock()
        mock_response.message.content = "text"
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        mock_client_cls.return_value = mock_client

        ingestion.ocr_image_via_ollama(
            image_path="test.png",
            model="my-model",
            ollama_url="http://myhost:1234",
            timeout_sec=60,
        )
        mock_client_cls.assert_called_once_with(
            host="http://myhost:1234",
            timeout=60,
        )

    @patch("ingestion.ollama.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_bytes")
    def test_chat_called_with_model(self, mock_file, mock_client_cls):
        """Should call chat() with the specified model."""
        mock_response = MagicMock()
        mock_response.message.content = "text"
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        mock_client_cls.return_value = mock_client

        ingestion.ocr_image_via_ollama(
            image_path="test.png",
            model="my-model",
            ollama_url="http://localhost:11434",
        )
        call_kwargs = mock_client.chat.call_args
        self.assertEqual(call_kwargs.kwargs["model"], "my-model")

    @patch("ingestion.ollama.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_bytes")
    def test_timeout_error_propagates(self, mock_file, mock_client_cls):
        """TimeoutError from ollama should propagate to the caller."""
        mock_client = MagicMock()
        mock_client.chat.side_effect = TimeoutError("Request timed out")
        mock_client_cls.return_value = mock_client

        with self.assertRaises(TimeoutError) as ctx:
            ingestion.ocr_image_via_ollama(
                image_path="test.png",
                model="test-model",
                ollama_url="http://localhost:11434",
                timeout_sec=5,
            )
        self.assertIn("timed out", str(ctx.exception))

    @patch("ingestion.ollama.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_bytes")
    def test_connection_error_propagates(self, mock_file, mock_client_cls):
        """ConnectionError (server unreachable) should propagate to the caller."""
        mock_client = MagicMock()
        mock_client.chat.side_effect = ConnectionError("Connection refused")
        mock_client_cls.return_value = mock_client

        with self.assertRaises(ConnectionError):
            ingestion.ocr_image_via_ollama(
                image_path="test.png",
                model="test-model",
                ollama_url="http://localhost:99999",
                timeout_sec=10,
            )

    @patch("ingestion.ollama.Client")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_bytes")
    def test_custom_timeout_passed_to_client(self, mock_file, mock_client_cls):
        """The timeout_sec value should be forwarded to ollama.Client(timeout=...)."""
        mock_response = MagicMock()
        mock_response.message.content = "text"
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        mock_client_cls.return_value = mock_client

        ingestion.ocr_image_via_ollama(
            image_path="test.png",
            model="m",
            ollama_url="http://localhost:11434",
            timeout_sec=300,
        )
        # Verify the Client was created with timeout=300
        mock_client_cls.assert_called_once_with(
            host="http://localhost:11434",
            timeout=300,
        )



# ─────────────────────────────────────────────────────────────
# 6. Markdown & Manifest Writing
# ─────────────────────────────────────────────────────────────

class TestWritePageMarkdown(unittest.TestCase):
    """Tests for write_page_markdown()."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_writes_metadata_header_and_body(self):
        """File should contain HTML comment header with metadata + body text."""
        filepath = os.path.join(self.temp_dir, "page_001.md")
        metadata = {"source_file": "test.pdf", "page": 1}
        body = "# Hello World"

        ingestion.write_page_markdown(filepath, body, metadata)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("<!--", content)
        self.assertIn("source_file: test.pdf", content)
        self.assertIn("page: 1", content)
        self.assertIn("-->", content)
        self.assertIn("# Hello World", content)

    def test_ends_with_newline(self):
        """Output file should end with a newline."""
        filepath = os.path.join(self.temp_dir, "page.md")
        ingestion.write_page_markdown(filepath, "text", {"k": "v"})

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(content.endswith("\n"))


class TestWriteManifest(unittest.TestCase):
    """Tests for write_manifest()."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_writes_valid_json(self):
        """File should contain valid JSON matching the input dict."""
        filepath = os.path.join(self.temp_dir, "manifest.json")
        data = {"doc_id": "test_abc123", "pages_total": 5, "pages": []}

        ingestion.write_manifest(filepath, data)

        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        self.assertEqual(loaded["doc_id"], "test_abc123")
        self.assertEqual(loaded["pages_total"], 5)

    def test_handles_unicode(self):
        """Should write non-ASCII characters correctly (ensure_ascii=False)."""
        filepath = os.path.join(self.temp_dir, "manifest.json")
        data = {"title": "เอกสารทดสอบ"}

        ingestion.write_manifest(filepath, data)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("เอกสารทดสอบ", content)


# ─────────────────────────────────────────────────────────────
# 7. Ingest PDF (Orchestrator)
# ─────────────────────────────────────────────────────────────

class TestIngestPdf(unittest.TestCase):
    """Tests for ingest_pdf() — mocks all sub-functions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Create a dummy PDF so sha1_of_file can read it
        self.dummy_pdf = os.path.join(self.temp_dir, "test.pdf")
        with open(self.dummy_pdf, "wb") as f:
            f.write(b"%PDF-1.4 dummy content")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("ingestion.ocr_image_via_ollama")
    @patch("ingestion.pdf_to_images")
    def test_success_path_returns_manifest(self, mock_pdf_to_img, mock_ocr):
        """Should return a manifest dict with correct structure on success."""
        mock_pdf_to_img.return_value = [
            {"page": 1, "image_path": os.path.join(self.temp_dir, "img", "page_001.png"), "width": 100, "height": 200},
        ]
        mock_ocr.return_value = "# Page 1 content"

        output_root = os.path.join(self.temp_dir, "output")
        manifest = ingestion.ingest_pdf(
            pdf_path=self.dummy_pdf,
            output_root=output_root,
            model="test-model",
            dpi=150,
            ollama_url="http://localhost:11434",
        )

        self.assertIn("doc_id", manifest)
        self.assertIn("pages", manifest)
        self.assertEqual(manifest["pages_total"], 1)
        self.assertEqual(manifest["pages_ok"], 1)
        self.assertEqual(manifest["pages_error"], 0)
        self.assertEqual(manifest["dpi"], 150)
        self.assertEqual(manifest["ocr_model"], "test-model")

    @patch("ingestion.ocr_image_via_ollama")
    @patch("ingestion.pdf_to_images")
    def test_ocr_error_recorded_in_manifest(self, mock_pdf_to_img, mock_ocr):
        """When OCR fails, the page should be recorded with status=error."""
        mock_pdf_to_img.return_value = [
            {"page": 1, "image_path": os.path.join(self.temp_dir, "img", "page_001.png"), "width": 100, "height": 200},
        ]
        mock_ocr.side_effect = Exception("Model timeout")

        output_root = os.path.join(self.temp_dir, "output")
        manifest = ingestion.ingest_pdf(
            pdf_path=self.dummy_pdf,
            output_root=output_root,
            model="test-model",
        )

        self.assertEqual(manifest["pages_ok"], 0)
        self.assertEqual(manifest["pages_error"], 1)
        self.assertEqual(manifest["pages"][0]["status"], "error")
        self.assertIn("Model timeout", manifest["errors"][0]["error"])

    @patch("ingestion.ocr_image_via_ollama")
    @patch("ingestion.pdf_to_images")
    def test_manifest_json_written_to_disk(self, mock_pdf_to_img, mock_ocr):
        """Should write manifest.json to the document output directory."""
        mock_pdf_to_img.return_value = []
        output_root = os.path.join(self.temp_dir, "output")

        manifest = ingestion.ingest_pdf(
            pdf_path=self.dummy_pdf,
            output_root=output_root,
            model="test-model",
        )

        manifest_path = os.path.join(output_root, manifest["doc_id"], "manifest.json")
        self.assertTrue(os.path.exists(manifest_path))

        with open(manifest_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["doc_id"], manifest["doc_id"])


# ─────────────────────────────────────────────────────────────
# 8. Main Function
# ─────────────────────────────────────────────────────────────

class TestMain(unittest.TestCase):
    """Tests for main() — mocks argparse and ingest_pdf."""

    @patch("ingestion.ingest_pdf")
    @patch("ingestion.list_pdfs")
    @patch("ingestion.argparse.ArgumentParser.parse_args")
    def test_no_pdfs_found(self, mock_args, mock_list, mock_ingest):
        """When no PDFs are found, ingest_pdf should NOT be called."""
        mock_args.return_value = MagicMock(
            input="/tmp/in", output="/tmp/out",
            model="m", dpi=150, ollama_url="http://localhost:11434", sleep_sec=0.0,
        )
        mock_list.return_value = []

        ingestion.main()
        mock_ingest.assert_not_called()

    @patch("ingestion.ingest_pdf")
    @patch("ingestion.list_pdfs")
    @patch("ingestion.argparse.ArgumentParser.parse_args")
    @patch("ingestion.ensure_dir")
    def test_processes_each_pdf(self, mock_ensure, mock_args, mock_list, mock_ingest):
        """Should call ingest_pdf once per PDF found."""
        mock_args.return_value = MagicMock(
            input="/tmp/in", output="/tmp/out",
            model="m", dpi=150, ollama_url="http://localhost:11434", sleep_sec=0.0,
        )
        mock_list.return_value = ["/tmp/in/a.pdf", "/tmp/in/b.pdf"]
        mock_ingest.return_value = {
            "doc_id": "x", "pages_ok": 1, "pages_total": 1, "pages_error": 0,
        }

        ingestion.main()
        self.assertEqual(mock_ingest.call_count, 2)


if __name__ == "__main__":
    unittest.main()

# Walkthrough: Unit Tests for [ingestion.py](../ingestion.py)
## What was created
[test_ingestion.py](test_ingestion.py) — 33 unit tests across 10 test classes covering all 12 functions.

|Test Class | # Tests | What it tests |
|---|---|---|
|[TestNowIsoBkk](test_ingestion.py#L41)|2|ISO format + Bangkok timezone|
|[TestEnsureDir](test_ingestion.py#L68)|2|Dir creation, idempotency|
|[TestSlugifyFilename](test_ingestion.py#L94)|5|Path stripping, special chars, Unicode|
|[TestSha1OfFile](test_ingestion.py#L132)|2|Known hash, empty file|
|[TestListPdfs](test_ingestion.py#L159)|4|PDF discovery, subdirs, sorting|
|[TestPdfToImages](test_ingestion.py#L204)|3|Page info, dir creation, doc close|
|[TestResizeImage](test_ingestion.py#L239)|3|No-resize, resize, boundary|
|[TestOcrImageViaOllama](test_ingestion.py#L268)|3|Returns text, client params, model|
|[TestWritePageMarkdown](test_ingestion.py#L371)|2|Header + body, trailing newline|
|[TestWriteManifest](test_ingestion.py#L396)|2|Valid JSON, Unicode|
|[TestIngestPdf](test_ingestion.py#L422)|3|Success path, error recording, manifest file|
|[TestTimeoutErrorPropagates](test_ingestion.py#L454)|3|TimeoutError from ollama.Client.chat() bubbles up to the caller|
|[TestConnectionErrorPropagates](test_ingestion.py#L475)|3|ConnectionError (server unreachable) also propagates correctly|
|[TestCustomTimeoutPassedToClient](test_ingestion.py#L496)|3|The timeout_sec parameter is forwarded as timeout= to ollama.Client()|
|[TestMain](test_ingestion.py#L517)|2|No PDFs, multi-PDF processing|

## Test results
```bash
Ran 33 tests in 0.088s
OK
```

## How to run
```bash
cd "c:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG"
python -m unittest discover -s tests -p "test_ingestion.py" -v
```


----
---

## Task
### Create Unit Tests for ingestion.py

### Planning
 - [/] Read [ingestion.py](../ingestion.py) to identify all testable functions
 - [/] Review existing test patterns in [tests/](tests/) directory
 - [/] Write implementation plan
 - [/] Get user approval

### Execution
 - [/] Create [tests/test_ingestion.py](test_ingestion.py) with unit tests for:
    - [/] now_iso_bkk()
    - [/] ensure_dir()
    - [/] slugify_filename()
    - [/] sha1_of_file()
    - [/] list_pdfs()
    - [/] pdf_to_images()
    - [/] resize_image()
    - [/] ocr_image_via_ollama()
    - [/] write_page_markdown()
    - [/] write_manifest()
    - [/] ingest_pdf()
    - [/] main()

### Verification
 - [/] Run unit tests and verify all pass ✅ (33 tests, 0.088s)
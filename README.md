# PDF to Comments

A Python tool to extract and organize comments from marked-up PDF documents (typically theses) into structured markdown outputs for academic viva preparation and/or student feedback.

## Overview

When marking a thesis, comments are made using PDF annotation tools (highlights, ink annotations, etc.). This script extracts those comments and organizes them into three separate markdown files based on comment type.

### Comment Types

Comments are classified by their prefix:
- **`Q`** - Questions to ask during the viva examination
- **`Note`** - General observations or suggestions
- **`Correction`** / **`Error`** - Issues that must be addressed
- **`Typo`** - Minor typographical errors
- Comments without a prefix are assumed to be "Note" type

**Example**: In a thesis about photonic integrated circuitry, the text "PICs are good because light is faster than electricity" might be highlighted with the comment "Q - is this correct? Consider how a signal propagates." to remind the examiner to ask the student about this.

## Installation

### Requirements
- Python 3.7+
- PyMuPDF (fitz)

### Setup

1. Clone or download this repository
2. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```bash
python PDF_to_comments.py --pdf <path-to-pdf> --output_dir <output-directory>
```

### Arguments

- `--pdf` (required): Path to the annotated PDF file
- `--output_dir` (required): Directory where markdown files will be saved
- `--debug` (optional): Enable debug output to see detailed processing information

### Example

```bash
python PDF_to_comments.py --pdf thesis.pdf --output_dir ./outputs
```

### Debug Mode

To see detailed information about annotation processing:

```bash
python PDF_to_comments.py --pdf thesis.pdf --output_dir ./outputs --debug
```

Debug mode shows:
- Total annotations found
- Annotation types being processed
- Which annotations are skipped and why
- Chapter detection information

## Output Files

The script generates three markdown files:

### 1. `comments.md`
Contains **all comments** from the PDF, organized by page.

### 2. `student_corrections.md`
Contains only **Note**, **Correction**, **Error**, and **Typo** comments, organized by type. This file is intended for student feedback.

### 3. `examiner_questions.md`
Contains only **Question** (`Q`) comments, organized by page. This file is intended for viva preparation.

## Output Format

Comments are formatted as multi-level lists for easy reading:

```markdown
## Page 19

- **Page 19, Line 15**
  - Comment: Q - is this correct? Consider how a signal propagates.
  - Highlighted: faster than
  - Context: "PICs are good because light is faster than electricity"

```

### Format Details

- **Page number**: Section heading for grouping
- **Line number**: Estimated line position on the page
- **Comment**: The annotation text
- **Highlighted**: The text that was highlighted (if any)
- **Context**: Full lines (±1 line) around the highlighted text, with highlighted portion in bold

**Smart Context Display**:
- For long highlighted text (>150 chars): Only the highlighted text is shown
- For short highlighted text (<150 chars): Both highlighted text and surrounding context are shown
- For annotations without highlights: Only context is shown

## Features

### Annotation Type Support
- ✅ Text annotations (types 0, 1, 2)
- ✅ Highlights (type 8)
- ✅ Ink/pen annotations (type 15)

### Intelligent Processing
- **Complete extraction**: Ensures all annotations are captured (no silent drops)
- **Chapter detection**: Attempts to use PDF table of contents for chapter-based grouping (falls back to page grouping if unavailable)
- **Full-line context**: Extracts complete lines (full page width) for readable context
- **Smart truncation**: Limits long context while keeping highlighted portions visible
- **Markdown escaping**: Properly escapes special characters to avoid formatting issues

### Error Handling
- Validates PDF file existence
- Creates output directory if it doesn't exist
- Graceful handling of malformed annotations
- Clear error messages and progress feedback

## Testing

To test the script, run it on a sample PDF:

```bash
python PDF_to_comments.py --pdf your_thesis.pdf --output_dir ./working_outputs
```

This will extract comments and generate outputs in the `working_outputs/` directory.

## Project Structure

```
PDF_to_comments/
├── PDF_to_comments.py      # Main script
├── README.md               # This file
├── SECURITY.md             # Security policy and best practices
├── QUICKSTART.md           # Quick reference guide
├── DEVELOPMENT.md          # Development documentation
├── requirements.txt        # Python dependencies
└── working_outputs/        # Generated output files
    ├── comments.md
    ├── student_corrections.md
    └── examiner_questions.md
```

## Security

This tool includes multiple security features to ensure safe operation:

- **Path Validation**: Prevents path traversal attacks
- **Resource Limits**: Maximum file size (500 MB) and page count (10,000 pages)
- **Safe File Operations**: Proper error handling and encoding validation
- **Permission Checks**: Validates output directory access before writing

**Best Practices:**
- Only process PDF files from trusted sources
- Use a dedicated output directory with appropriate permissions
- Keep PyMuPDF updated for security patches
- Avoid using `--debug` flag with sensitive files

For complete security information, see [SECURITY.md](SECURITY.md).

## Technical Details

### Comment Extraction Process

1. **PDF Opening**: Opens the PDF and attempts to extract table of contents
2. **Annotation Processing**: Iterates through all pages, extracting annotations
3. **Text Extraction**: Gets highlighted text and surrounding context
4. **Classification**: Categorizes comments by type (Q, Note, Correction, etc.)
5. **Organization**: Groups comments by page or chapter
6. **Output Generation**: Creates three separate markdown files

### Line Number Estimation

Line numbers are estimated based on Y-coordinate position:
- Assumes typical academic paper line height (~20 pixels)
- Accounts for standard top margin (72 points = 1 inch)
- Provides approximate positioning for reference

### Context Extraction

- Extracts full page width (left to right)
- Captures ±1 line vertically around highlighted text
- Highlights the marked text in bold within context
- Truncates long context intelligently, keeping highlighted portion visible

## Development

### Code Structure

- `CommentType`: Enumeration of comment types
- `PDFComment`: Data class for individual comments
- `PDFCommentExtractor`: Handles PDF reading and annotation extraction
- `MarkdownGenerator`: Creates formatted markdown output files

### Adding New Features

The modular structure makes it easy to:
- Add new comment types (modify `CommentType` and `classify_comment()`)
- Change output format (modify `PDFComment.to_markdown()`)
- Adjust grouping logic (modify `MarkdownGenerator` methods)
- Support additional annotation types (modify `_process_annotation()`)

## Limitations

- Line numbers are estimates based on position
- Chapter detection depends on PDF table of contents being present
- Some PDF annotation types may not be supported
- Context extraction assumes standard academic paper formatting

## Version

Current version: 1.0.0 (October 2025)
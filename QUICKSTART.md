# Quick Start Guide

## Installation
```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

## Basic Usage
```bash
python PDF_to_comments.py --pdf your_thesis.pdf --output_dir ./outputs
```

## Output Files
- `comments.md` - All comments
- `student_corrections.md` - Feedback for student
- `examiner_questions.md` - Questions for viva

## Comment Types
In your PDF annotations, start comments with:
- `Q` - Question for viva
- `Note` - General observation
- `Correction` - Must fix
- `Error` - Must fix
- `Typo` - Minor typo
- (no prefix) - Treated as Note

## Example
Highlight text "less resistance" and add comment:
```
Q - what is the optical analog of "resistance"?
```

## Debug Mode
See detailed processing information:
```bash
python PDF_to_comments.py --pdf thesis.pdf --output_dir ./outputs --debug
```

## Testing
```bash
python PDF_to_comments.py --pdf your_thesis.pdf --output_dir ./working_outputs
```

## Support
See `README.md` for full documentation.

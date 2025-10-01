#!/usr/bin/env python3
"""
PDF to Comments Converter

This script extracts highlighted comments from a PDF document (typically a thesis)
and generates three markdown output files:
1. comments.md - All comments
2. student_corrections.md - Note, Correction, Error, and Typo comments
3. examiner_questions.md - Questions for the viva
"""

import argparse
import sys
import os
from pathlib import Path
import fitz  # PyMuPDF

# Security constants
MAX_PDF_SIZE_MB = 500  # Maximum PDF file size in MB
MAX_PAGE_COUNT = 10000  # Maximum number of pages to process


class CommentType:
    """Enum-like class for comment types"""
    QUESTION = "Q"
    NOTE = "Note"
    CORRECTION = "Correction"
    ERROR = "Error"
    TYPO = "Typo"


class PDFComment:
    """Represents a single comment extracted from the PDF"""
    
    def __init__(self, page_num, line_num, comment_text, highlighted_text, context_text, comment_type):
        self.page_num = page_num
        self.line_num = line_num
        self.comment_text = comment_text
        self.highlighted_text = highlighted_text
        self.context_text = context_text
        self.comment_type = comment_type
    
    def to_markdown(self):
        """Convert comment to markdown format using multi-level list"""
        output = f"- **Page {self.page_num}, Line {self.line_num}**\n"
        output += f"  - Comment: {self.comment_text}\n"
        
        # Only show highlighted text if it exists and is not too long
        if self.highlighted_text and len(self.highlighted_text.strip()) > 0:
            highlighted_clean = self.highlighted_text.strip()
            # If highlighted text is long (>150 chars), don't show context separately
            if len(highlighted_clean) > 150:
                output += f"  - Highlighted: {highlighted_clean}\n"
            else:
                # Show highlighted text
                output += f"  - Highlighted: {highlighted_clean}\n"
                # Only show context if it adds meaningful content beyond highlighted
                if self.context_text and len(self.context_text.strip()) > len(highlighted_clean) + 20:
                    output += f"  - Context: {self.context_text}\n"
        elif self.context_text:
            # No highlighted text, so show context
            output += f"  - Context: {self.context_text}\n"
        
        return output


class PDFCommentExtractor:
    """Extracts comments from a PDF file"""
    
    def __init__(self, pdf_path, debug=False):
        self.pdf_path = pdf_path
        self.comments = []
        self.doc = None
        self.debug = debug
        self.skipped_annotations = {}
        self.chapter_map = {}  # Maps page numbers to chapter names
    
    @staticmethod
    def _validate_path(file_path):
        """Validate file path to prevent path traversal attacks"""
        try:
            # Resolve to absolute path
            resolved_path = Path(file_path).resolve()
            
            # Check if path exists and is a file
            if not resolved_path.exists():
                return None, "File does not exist"
            
            if not resolved_path.is_file():
                return None, "Path is not a file"
            
            # Additional check: ensure it's actually a PDF by checking extension
            if resolved_path.suffix.lower() != '.pdf':
                return None, "File must be a PDF (.pdf extension)"
            
            return resolved_path, None
        except (ValueError, OSError) as e:
            return None, f"Invalid path: {str(e)}"
    
    @staticmethod
    def _check_file_size(file_path):
        """Check if file size is within acceptable limits"""
        try:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_PDF_SIZE_MB:
                return False, f"File size ({size_mb:.1f} MB) exceeds maximum allowed size ({MAX_PDF_SIZE_MB} MB)"
            return True, None
        except OSError as e:
            return False, f"Cannot read file size: {str(e)}"
    
    def open_pdf(self):
        """Open the PDF file with security validation"""
        try:
            # Validate path
            validated_path, error = self._validate_path(self.pdf_path)
            if error:
                print(f"Security Error: {error}", file=sys.stderr)
                return False
            
            # Check file size
            size_ok, error = self._check_file_size(validated_path)
            if not size_ok:
                print(f"Security Error: {error}", file=sys.stderr)
                return False
            
            if self.debug:
                print(f"Opening PDF: {validated_path.name}")
            else:
                print(f"Opening PDF: {validated_path.name}")
            
            self.doc = fitz.open(str(validated_path))
            
            # Check page count
            page_count = len(self.doc)
            if page_count > MAX_PAGE_COUNT:
                print(f"Security Error: Page count ({page_count}) exceeds maximum allowed ({MAX_PAGE_COUNT})", file=sys.stderr)
                self.doc.close()
                return False
            
            print(f"Successfully opened PDF with {page_count} pages")
            self._build_chapter_map()
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}", file=sys.stderr)
            if self.doc:
                self.doc.close()
            return False
    
    def _build_chapter_map(self):
        """Build a mapping of page numbers to chapter names from PDF outline"""
        try:
            toc = self.doc.get_toc()
            if not toc:
                if self.debug:
                    print("No table of contents found in PDF")
                return
            
            # TOC format: [[level, title, page_num], ...]
            # Build map where each page gets the most recent chapter heading
            current_chapter = "Unknown Chapter"
            for level, title, page_num in toc:
                if level <= 2:  # Consider level 1 and 2 as chapters
                    current_chapter = title
                # Map this page and all following pages to this chapter
                for p in range(page_num, len(self.doc) + 1):
                    if p not in self.chapter_map:
                        self.chapter_map[p] = current_chapter
            
            if self.debug and self.chapter_map:
                print(f"Built chapter map with {len(set(self.chapter_map.values()))} chapters")
        except Exception as e:
            if self.debug:
                print(f"Could not build chapter map: {e}")
    
    def get_chapter_for_page(self, page_num):
        """Get the chapter name for a given page number"""
        return self.chapter_map.get(page_num, f"Page {page_num}")
    
    def has_useful_chapters(self):
        """Check if chapter detection found multiple chapters"""
        unique_chapters = set(self.chapter_map.values())
        return len(unique_chapters) > 1
    
    def classify_comment(self, comment_text):
        """Classify a comment based on its starting text"""
        comment_text_upper = comment_text.strip().upper()
        
        if comment_text_upper.startswith("Q ") or comment_text_upper.startswith("Q-"):
            return CommentType.QUESTION
        elif comment_text_upper.startswith(CommentType.CORRECTION.upper()):
            return CommentType.CORRECTION
        elif comment_text_upper.startswith(CommentType.ERROR.upper()):
            return CommentType.ERROR
        elif comment_text_upper.startswith(CommentType.TYPO.upper()):
            return CommentType.TYPO
        elif comment_text_upper.startswith(CommentType.NOTE.upper()):
            return CommentType.NOTE
        else:
            # Default to Note if no prefix matches
            return CommentType.NOTE
    
    def extract_comments(self):
        """Extract all comments from the PDF"""
        if not self.doc:
            print("Error: PDF not opened", file=sys.stderr)
            return False
        
        print("Extracting comments from PDF...")
        comment_count = 0
        total_annotations = 0
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            print(f"Processing page {page_num + 1}/{len(self.doc)}...", end='\r')
            
            # Extract annotations (highlights, comments, etc.)
            annots = page.annots()
            if annots:
                for annot in annots:
                    total_annotations += 1
                    comment_count += self._process_annotation(page, page_num + 1, annot)
        
        print(f"\nExtracted {comment_count} comments from {len(self.doc)} pages")
        print(f"Total annotations found: {total_annotations}")
        
        if self.debug:
            print("\n=== Debug: Skipped Annotations ===")
            for reason, count in sorted(self.skipped_annotations.items()):
                print(f"  {reason}: {count}")
        
        return True
    
    def _process_annotation(self, page, page_num, annot):
        """Process a single annotation"""
        try:
            annot_type = annot.type[0]
            annot_type_name = annot.type[1] if len(annot.type) > 1 else "Unknown"
            
            if self.debug:
                print(f"\nPage {page_num}, Type: {annot_type} ({annot_type_name})")
                print(f"  Info: {annot.info}")
            
            # Include common annotation types:
            # 0, 1, 2: Text annotations
            # 8: Highlight
            # 15: Ink (pen/drawing annotations)
            if annot_type not in [0, 1, 2, 8, 15]:
                reason = f"Type {annot_type} ({annot_type_name}) not in allowed types"
                self.skipped_annotations[reason] = self.skipped_annotations.get(reason, 0) + 1
                if self.debug:
                    print(f"  SKIPPED: {reason}")
                return 0
            
            comment_text = annot.info.get("content", "").strip()
            if not comment_text:
                reason = f"No content text (Type {annot_type}: {annot_type_name})"
                self.skipped_annotations[reason] = self.skipped_annotations.get(reason, 0) + 1
                if self.debug:
                    print(f"  SKIPPED: {reason}")
                return 0
            rect = annot.rect
            highlighted_text = ""
            try:
                words = page.get_text("words", clip=rect)
                if words:
                    highlighted_text = " ".join([w[4] for w in words])
            except:
                pass
            context_text = self.get_context_text(page, rect, highlighted_text)
            line_num = self.estimate_line_number(page, rect)
            comment_type = self.classify_comment(comment_text)
            comment = PDFComment(
                page_num=page_num,
                line_num=line_num,
                comment_text=comment_text,
                highlighted_text=highlighted_text,
                context_text=context_text,
                comment_type=comment_type
            )
            self.comments.append(comment)
            return 1
        except Exception as e:
            print(f"\nWarning: Error processing annotation on page {page_num}: {e}", file=sys.stderr)
            return 0
    
    def get_context_text(self, page, rect, highlighted_text):
        """Extract context around highlighted text - full lines, ±1 line vertically"""
        try:
            # Get the Y position of the annotation
            y_center = (rect.y0 + rect.y1) / 2
            
            # Create a rectangle that spans the full page width, ±1 line vertically
            # Typical line height in academic PDFs is ~15-20 pixels
            line_height = 20
            context_rect = fitz.Rect(
                0,  # Left edge of page
                max(0, rect.y0 - line_height),  # 1 line above
                page.rect.width,  # Right edge of page
                min(page.rect.height, rect.y1 + line_height)  # 1 line below
            )
            
            # Extract text from this region
            context_text = page.get_text("text", clip=context_rect).strip()
            
            # Clean up: replace multiple spaces/newlines with single spaces
            context_text = " ".join(context_text.split())
            
            # If we have highlighted text, mark it in bold
            if highlighted_text:
                highlighted_clean = " ".join(highlighted_text.split())
                if highlighted_clean in context_text:
                    # Escape any existing asterisks in the highlighted text to avoid markdown issues
                    highlighted_escaped = highlighted_clean.replace("*", "\\*")
                    context_text = context_text.replace(highlighted_clean, f"**{highlighted_escaped}**")
            
            # Limit total length while keeping the highlighted portion
            max_length = 300
            if len(context_text) > max_length:
                if "**" in context_text:
                    # Find the highlighted portion
                    bold_start = context_text.find("**")
                    # Center the output around the highlighted text
                    start = max(0, bold_start - max_length // 2)
                    end = min(len(context_text), bold_start + max_length // 2)
                    context_text = context_text[start:end]
                    if start > 0:
                        context_text = "..." + context_text
                    if end < len(context_text):
                        context_text = context_text + "..."
                else:
                    # No highlighted portion, just truncate
                    context_text = context_text[:max_length] + "..."
            
            return context_text if context_text else highlighted_text
            
        except Exception as e:
            return highlighted_text if highlighted_text else ""
    
    def estimate_line_number(self, page, rect):
        """Estimate line number on the page based on position"""
        try:
            page_height = page.rect.height
            y_pos = rect.y0
            estimated_line_height = 20
            top_margin = 72
            adjusted_y = max(0, y_pos - top_margin)
            line_num = int(adjusted_y / estimated_line_height) + 1
            return max(1, line_num)
        except:
            return 1
    
    def close(self):
        """Close the PDF document"""
        if self.doc:
            self.doc.close()


class MarkdownGenerator:
    """Generates markdown output files from extracted comments"""
    
    def __init__(self, comments, output_dir, extractor=None):
        self.comments = comments
        self.output_dir = Path(output_dir).resolve()  # Resolve to absolute path
        self.extractor = extractor
    
    @staticmethod
    def _validate_output_dir(output_dir):
        """Validate output directory for security"""
        try:
            resolved_dir = Path(output_dir).resolve()
            
            # If it exists, ensure it's a directory
            if resolved_dir.exists() and not resolved_dir.is_dir():
                return None, "Output path exists but is not a directory"
            
            # Check if we have permission to create/write
            if resolved_dir.exists():
                # Test write permission
                test_file = resolved_dir / ".write_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                except OSError:
                    return None, "No write permission in output directory"
            
            return resolved_dir, None
        except (ValueError, OSError) as e:
            return None, f"Invalid output directory: {str(e)}"
    
    def generate_all(self):
        """Generate all three output files"""
        print("\nGenerating output files...")
        
        self.generate_all_comments()
        self.generate_student_corrections()
        self.generate_examiner_questions()
        
        print("Output files generated successfully")
    
    def generate_all_comments(self):
        """Generate comments.md with all comments grouped by chapter or page"""
        output_path = self.output_dir / "comments.md"
        print(f"Writing {output_path.name}")
        try:
            with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write("# All Comments\n\n")
                if not self.comments:
                    f.write("No comments found.\n")
                    return
                
                # Check if we should use chapter or page grouping
                use_chapters = self.extractor and self.extractor.has_useful_chapters()
                
                if use_chapters:
                    # Group by chapter
                    comments_by_group = {}
                    for comment in self.comments:
                        chapter = self.extractor.get_chapter_for_page(comment.page_num)
                        if chapter not in comments_by_group:
                            comments_by_group[chapter] = []
                        comments_by_group[chapter].append(comment)
                else:
                    # Group by page
                    comments_by_group = {}
                    for comment in self.comments:
                        page_key = f"Page {comment.page_num}"
                        if page_key not in comments_by_group:
                            comments_by_group[page_key] = []
                        comments_by_group[page_key].append(comment)
                
                # Write comments grouped by chapter or page
                for group_name in sorted(comments_by_group.keys()):
                    f.write(f"## {group_name}\n\n")
                    # Sort by page, then line within each group
                    group_comments = sorted(comments_by_group[group_name], key=lambda c: (c.page_num, c.line_num))
                    for comment in group_comments:
                        f.write(comment.to_markdown())
                        f.write("\n")
                
                f.write(f"\n---\n\n**Total comments: {len(self.comments)}**\n")
        except IOError as e:
            print(f"Error writing comments.md: {e}", file=sys.stderr)
            raise
    
    def generate_student_corrections(self):
        """Generate student_corrections.md with Note, Correction, Error, and Typo comments"""
        output_path = self.output_dir / "student_corrections.md"
        print(f"Writing {output_path.name}")
        student_comment_types = [CommentType.NOTE, CommentType.CORRECTION, CommentType.ERROR, CommentType.TYPO]
        student_comments = [c for c in self.comments if c.comment_type in student_comment_types]
        try:
            with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write("# Student Corrections\n\n")
                f.write("This document contains notes, corrections, errors, and typos identified in the thesis.\n\n")
                if not student_comments:
                    f.write("No student corrections found.\n")
                    return
                
                # Check if we should use chapter or page grouping
                use_chapters = self.extractor and self.extractor.has_useful_chapters()
                
                for comment_type in [CommentType.ERROR, CommentType.CORRECTION, CommentType.TYPO, CommentType.NOTE]:
                    type_comments = [c for c in student_comments if c.comment_type == comment_type]
                    if type_comments:
                        f.write(f"## {comment_type}s\n\n")
                        
                        if use_chapters:
                            # Group by chapter
                            comments_by_group = {}
                            for comment in type_comments:
                                chapter = self.extractor.get_chapter_for_page(comment.page_num)
                                if chapter not in comments_by_group:
                                    comments_by_group[chapter] = []
                                comments_by_group[chapter].append(comment)
                            
                            for group_name in sorted(comments_by_group.keys()):
                                f.write(f"### {group_name}\n\n")
                                group_comments = sorted(comments_by_group[group_name], key=lambda c: (c.page_num, c.line_num))
                                for comment in group_comments:
                                    f.write(comment.to_markdown())
                                    f.write("\n")
                        else:
                            # No chapter subheadings, just list all comments for this type
                            sorted_comments = sorted(type_comments, key=lambda c: (c.page_num, c.line_num))
                            for comment in sorted_comments:
                                f.write(comment.to_markdown())
                                f.write("\n")
                
                f.write(f"\n---\n\n**Total corrections: {len(student_comments)}**\n")
        except IOError as e:
            print(f"Error writing student_corrections.md: {e}", file=sys.stderr)
            raise
    
    def generate_examiner_questions(self):
        """Generate examiner_questions.md with questions for the viva"""
        output_path = self.output_dir / "examiner_questions.md"
        print(f"Writing {output_path.name}")
        questions = [c for c in self.comments if c.comment_type == CommentType.QUESTION]
        try:
            with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write("# Examiner Questions\n\n")
                f.write("Questions to ask during the viva examination.\n\n")
                if not questions:
                    f.write("No questions found.\n")
                    return
                
                # Check if we should use chapter or page grouping
                use_chapters = self.extractor and self.extractor.has_useful_chapters()
            
                use_chapters = self.extractor and self.extractor.has_useful_chapters()
                
                if use_chapters:
                    # Group by chapter
                    questions_by_group = {}
                    for question in questions:
                        chapter = self.extractor.get_chapter_for_page(question.page_num)
                        if chapter not in questions_by_group:
                            questions_by_group[chapter] = []
                        questions_by_group[chapter].append(question)
                    
                    for group_name in sorted(questions_by_group.keys()):
                        f.write(f"## {group_name}\n\n")
                        group_questions = sorted(questions_by_group[group_name], key=lambda c: (c.page_num, c.line_num))
                        for question in group_questions:
                            f.write(question.to_markdown())
                            f.write("\n")
                else:
                    # Group by page
                    questions_by_page = {}
                    for question in questions:
                        page_key = f"Page {question.page_num}"
                        if page_key not in questions_by_page:
                            questions_by_page[page_key] = []
                        questions_by_page[page_key].append(question)
                    
                    for page_name in sorted(questions_by_page.keys()):
                        f.write(f"## {page_name}\n\n")
                        page_questions = sorted(questions_by_page[page_name], key=lambda c: (c.page_num, c.line_num))
                        for question in page_questions:
                            f.write(question.to_markdown())
                            f.write("\n")
                
                f.write(f"\n---\n\n**Total questions: {len(questions)}**\n")
        except IOError as e:
            print(f"Error writing examiner_questions.md: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Extract comments from a marked-up PDF and generate markdown files'
    )
    parser.add_argument('--pdf', required=True, help='Path to the PDF file')
    parser.add_argument('--output_dir', required=True, help='Directory for output files')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    # Validate PDF path
    validated_pdf, error = PDFCommentExtractor._validate_path(args.pdf)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    
    # Validate output directory
    validated_output, error = MarkdownGenerator._validate_output_dir(args.output_dir)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    
    # Create output directory if it doesn't exist
    if not validated_output.exists():
        try:
            print(f"Creating output directory: {validated_output.name}")
            validated_output.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error: Cannot create output directory: {e}", file=sys.stderr)
            return 1
    
    # Extract comments
    extractor = PDFCommentExtractor(str(validated_pdf), debug=args.debug)
    
    if not extractor.open_pdf():
        return 1
    
    if not extractor.extract_comments():
        extractor.close()
        return 1
    
    # Generate output files (keep extractor open for chapter mapping)
    try:
        generator = MarkdownGenerator(extractor.comments, validated_output, extractor)
        generator.generate_all()
    except Exception as e:
        print(f"Error generating output files: {e}", file=sys.stderr)
        extractor.close()
        return 1
    
    extractor.close()
    
    print("\nProcessing complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

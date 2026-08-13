"""Content export service for tutorials."""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.tutorial import Tutorial
from ..models.chapter import Chapter


class ExportService:
    """Service for exporting tutorial content in various formats."""

    def __init__(self, db: Session):
        self.db = db

    def export_to_markdown(self, tutorial_id: str) -> Dict[str, Any]:
        """Export tutorial content to Markdown format."""
        tutorial = self.db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
        if not tutorial:
            raise ValueError(f"Tutorial {tutorial_id} not found")

        chapters = self.db.query(Chapter).filter_by(
            tutorial_id=tutorial_id
        ).order_by(Chapter.chapter_number).all()

        # Build markdown content
        md_content = f"# {tutorial.title}\n\n"
        if tutorial.description:
            md_content += f"{tutorial.description}\n\n"
        md_content += f"**Author:** {tutorial.owner_id}\n"
        md_content += f"**Status:** {tutorial.status}\n"
        md_content += f"**Created:** {tutorial.created_at.strftime('%Y-%m-%d') if tutorial.created_at else 'N/A'}\n\n"
        md_content += "---\n\n"

        for chapter in chapters:
            md_content += self._chapter_to_markdown(chapter)
            md_content += "\n---\n\n"

        return {
            "tutorial_id": tutorial_id,
            "title": tutorial.title,
            "format": "markdown",
            "content": md_content,
            "chapter_count": len(chapters),
            "generated_at": datetime.utcnow().isoformat()
        }

    def _chapter_to_markdown(self, chapter: Chapter) -> str:
        """Convert a chapter to markdown format."""
        md = f"## Chapter {chapter.chapter_number}: {chapter.title}\n\n"

        if not chapter.content:
            return md

        content = chapter.content

        # Add learning objectives
        if isinstance(content, dict):
            objectives = content.get("learning_objectives", [])
            if objectives:
                md += "### Learning Objectives\n\n"
                for obj in objectives:
                    md += f"- {obj}\n"
                md += "\n"

            # Add sections
            sections = content.get("sections", [])
            for section in sections:
                md += self._section_to_markdown(section)

            # Add practice exercises
            exercises = content.get("practice_exercises", [])
            if exercises:
                md += "### Practice Exercises\n\n"
                for i, exercise in enumerate(exercises, 1):
                    md += f"{i}. **{exercise.get('difficulty', 'medium')}**: {exercise.get('question', '')}\n"
                    if exercise.get('hint'):
                        md += f"   Hint: {exercise['hint']}\n"
                md += "\n"

        return md

    def _section_to_markdown(self, section: Dict) -> str:
        """Convert a section to markdown."""
        md = f"### {section.get('title', 'Section')}\n\n"

        content = section.get("content", {})

        # Overview
        if content.get("overview"):
            md += f"{content['overview']}\n\n"

        # Theoretical explanation
        if content.get("theoretical_explanation"):
            md += "**Theory:**\n\n"
            md += f"{content['theoretical_explanation']}\n\n"

        # Formulas
        formulas = content.get("formulas", [])
        if formulas:
            md += "**Formulas:**\n\n"
            for formula in formulas:
                md += f"$$ {formula.get('latex', '')} $$\n"
                if formula.get('derivation'):
                    md += f"*Derivation:* {formula['derivation']}\n\n"
            md += "\n"

        # Code samples
        code_samples = content.get("code_samples", [])
        if code_samples:
            md += "**Code Examples:**\n\n"
            for sample in code_samples:
                lang = sample.get("language", "python")
                md += f"```{lang}\n"
                md += f"{sample.get('code', '')}\n"
                md += "```\n\n"
                if sample.get('explanation'):
                    md += f"*{sample['explanation']}*\n\n"

        return md + "\n"

    def export_to_json(self, tutorial_id: str) -> Dict[str, Any]:
        """Export tutorial content to JSON format."""
        tutorial = self.db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
        if not tutorial:
            raise ValueError(f"Tutorial {tutorial_id} not found")

        chapters = self.db.query(Chapter).filter_by(
            tutorial_id=tutorial_id
        ).order_by(Chapter.chapter_number).all()

        return {
            "tutorial_id": tutorial_id,
            "title": tutorial.title,
            "format": "json",
            "tutorial": tutorial.to_dict(include_outline=True),
            "chapters": [ch.to_dict() for ch in chapters],
            "generated_at": datetime.utcnow().isoformat()
        }

    _PDF_CSS = """
    @page { size: A4; margin: 2cm; }
    body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1a1a2e; line-height: 1.6; }
    h1 { font-size: 22pt; color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 0.3em; }
    h2 { font-size: 16pt; color: #0f3460; margin-top: 1.5em; }
    h3 { font-size: 13pt; color: #1a1a2e; }
    pre { background: #f4f4f8; padding: 1em; border-radius: 6px; font-size: 9pt; overflow-x: auto; }
    code { background: #f0f0f5; padding: 0.1em 0.3em; border-radius: 3px; font-size: 9pt; }
    blockquote { border-left: 4px solid #0f3460; margin: 0; padding-left: 1em; color: #555; }
    table { border-collapse: collapse; width: 100%; margin: 1em 0; }
    th, td { border: 1px solid #ddd; padding: 0.5em; text-align: left; }
    th { background: #f0f0f5; }
    ul, ol { padding-left: 1.5em; }
    li { margin: 0.3em 0; }
    hr { border: none; border-top: 1px solid #ccc; margin: 2em 0; }
    """

    def export_to_pdf(self, tutorial_id: str) -> Dict[str, Any]:
        """Export tutorial content to PDF using WeasyPrint."""
        try:
            from weasyprint import HTML, CSS
        except ImportError:
            raise RuntimeError("weasyprint is not installed. Install with: pip install weasyprint")

        md_result = self.export_to_markdown(tutorial_id)
        html_content = self._markdown_to_html(md_result["content"], md_result["title"])

        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[CSS(string=self._PDF_CSS)]
        )
        return {
            "tutorial_id": tutorial_id,
            "title": md_result["title"],
            "format": "pdf",
            "size_bytes": len(pdf_bytes),
            "chapter_count": md_result["chapter_count"],
            "pdf_bytes": pdf_bytes,
        }

    def _markdown_to_html(self, markdown: str, title: str) -> str:
        """Convert markdown to HTML for PDF rendering."""
        html = markdown

        # Escape HTML
        html = html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Headings
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Code blocks
        html = re.sub(r'```(\w+)?\n(.+?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

        # Horizontal rule
        html = re.sub(r'^---$', '<hr/>', html, flags=re.MULTILINE)

        # Unordered lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html)

        # Ordered lists
        html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # Paragraphs
        html = re.sub(r'\n\n', '</p><p>', html)
        html = '<p>' + html + '</p>'
        html = re.sub(r'<p>(<h[123]>|<hr/?>|<ul>|</ul>|<pre>|</pre>)', r'\1', html)
        html = re.sub(r'(</h[123]>|</hr(?:/?)?>|</ul>|</pre>)</p>', r'\1', html)

        # Clean up empty paragraphs
        html = re.sub(r'<p>\s*</p>', '', html)
        html = re.sub(r'<p>\n', '<p>', html)
        html = re.sub(r'\n</p>', '</p>', html)

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body>{html}</body></html>"""


def create_export_service(db: Session) -> ExportService:
    """Create an export service instance."""
    return ExportService(db)

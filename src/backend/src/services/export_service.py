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


def create_export_service(db: Session) -> ExportService:
    """Create an export service instance."""
    return ExportService(db)

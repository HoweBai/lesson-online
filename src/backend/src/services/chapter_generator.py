"""Service for generating individual tutorial chapters."""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from ..models.tutorial import Tutorial
from ..models.chapter import Chapter
from ..models.claude_config import ClaudeConfig
from ..services.llm_adapter import ClaudeAdapter, OpenAIAAdapter
from ..services.claude_config_service import ClaudeConfigService
from ..services.prerequisite_checker import PrerequisiteChecker
from ..services.content_security import ContentSecurityService
from .crypto_service import SecureCryptoService

logger = logging.getLogger(__name__)


class ChapterGenerator:
    """Generates a single detailed chapter of a tutorial with prerequisite awareness."""

    def __init__(self, db_session: Session, crypto: SecureCryptoService,
                 claude_config_service: ClaudeConfigService):
        self.db = db_session
        self.crypto = crypto
        self.claude_service = claude_config_service
        self.checker = PrerequisiteChecker()
        self.security_service = ContentSecurityService()

    def build_chapter_prompt(self, chapter_number: int, chapter_title: str,
                            mastery_map: Dict[str, str],
                            prerequisite_review: Optional[str] = None) -> str:
        """Build a prompt for generating a single detailed chapter.

        The prompt includes requests for formulas/code examples in appropriate sections.
        """
        if prerequisite_review:
            intro = f"""【前置知识回顾】\n{prerequisite_review}\n\n"""
        else:
            intro = ""

        system_prompt = """You are creating a comprehensive computer science tutorial chapter. Your content must include:

1. Clear learning objectives at the beginning
2. Detailed theoretical explanations with mathematical derivations using proper LaTeX notation
3. Code examples in relevant programming languages with syntax highlighting instructions
4. Practice exercises at the end covering different difficulty levels (easy, medium, hard)
5. Real-world applications and analogies where helpful

Format the output as valid JSON with this structure:
{{
  "chapter_title": "...",
  "learning_objectives": ["objective 1", "objective 2"],
  "sections": [
    {{
      "section_id": "sec-1",
      "title": "Section Title",
      "type": "theory|formula|code",
      "content": {
        "overview": "...",
        "theoretical_explanation": "...",
        "formulas": [{"latex": "...", "derivation": "...", "explanation": "..."}],
        "code_samples": [{"language": "python", "code": "...", "explanation": "..."}]
      }}
    }],
    "practice_exercises": [{{
      "question": "...",
      "difficulty": "easy|medium|hard",
      "hint": "... (optional)",
      "solution_reference": "Related section or concept"
    }}],
    "key_concepts_learned": ["concept1", "concept2"]
}}

IMPORTANT: Make sure to include formula derivations step-by-step. For code samples, explain the complexity analysis."""

        full_prompt = system_prompt + "\n\n" + \
            f"Generate chapter {chapter_number}: '{chapter_title}' based on the user's knowledge level.\n\n" + \
            intro + "Here is the requested chapter content:"

        return full_prompt

    def generate(self, config_id: UUID, user_id: UUID, tutorial_id: UUID,
                 chapter_number: int, outline_data: Dict[str, Any],
                 mastery_map: Dict[str, str]) -> Dict[str, Any]:
        """Generate a single chapter of the tutorial.

        Returns dictionary with chapter content and metadata.
        """
        # Get config
        config = self.claude_service.get_config_for_api_call(user_id, config_id)
        if not config:
            raise ValueError("Invalid configuration")

        # Choose adapter
        model_name_lower = config["model_name"].lower()
        if "openai" in model_name_lower or "gpt-" in model_name_lower:
            llm_adapter = OpenAIAAdapter(config)
        else:
            llm_adapter = ClaudeAdapter(config)

        # Check prerequisites for this chapter
        # In production, you'd map chapter numbers to topics from the outline
        chapter_topic = self._get_topic_from_outline(outline_data, chapter_number)
        needs_review, missing_topics = self.checker.check_prerequisites(
            chapter_topic, mastery_map
        )

        prerequisite_review = None
        if needs_review:
            prerequisite_review = self.checker.generate_prerequisites_for_review(
                missing_topics, mastery_map
            )
            # Log this decision for audit purposes
            logger.info(f"Prerequisite review needed for chapter {chapter_number}: {missing_topics}")

        # Build prompt
        title = outline_data.get("chapters", [{}]).get(chapter_number, {}).get(
            "title", f"Chapter {chapter_number}"
        )
        prompt = self.build_chapter_prompt(
            chapter_number, title, mastery_map, prerequisite_review
        )

        # Generate content
        chapter_text = llm_adapter.generate_content(prompt)

        # Parse response
        try:
            clean_text = chapter_text.replace("```json", "").replace("```", "")
            chapter_content = json.loads(clean_text.strip())
        except Exception as e:
            chapter_content = {"error": f"Parsing failed: {str(e)}", "raw": chapter_text[:500]}

        # 扫描生成的内容
        content_to_scan = json.dumps(chapter_content) if isinstance(chapter_content, dict) else chapter_text
        scan_result = self.security_service.scan_content(content_to_scan, str(user_id))

        # 将扫描结果存入章节
        chapter_content['_security_scan'] = scan_result

        llm_adapter.close()

        # Prepare chapter object for database
        chapter_record = {
            "id": str(uuid.uuid4()),
            "tutorial_id": str(tutorial_id),
            "chapter_number": chapter_number,
            "title": title,
            "content": chapter_content,
            "status": "ready",
            "prerequisite_check_passed": not needs_review,
            "generated_at": datetime.utcnow()
        }

        return {
            "status": "success",
            "chapter_number": chapter_number,
            "chapter_id": chapter_record["id"],
            "chapter_content": chapter_content,
            "prerequisite_review_needed": needs_review,
            "prerequisite_topics": missing_topics if needs_review else []
        }

    def _get_topic_from_outline(self, outline: Dict[str, Any], chapter_num: int) -> str:
        """Extract the topic associated with a given chapter number from outline data."""
        # This would be more sophisticated in implementation - matching chapter numbers to topics
        chapter_info = outline.get("chapters", [{}])[chapter_num]
        topic_mapping = {
            1: "data_structures",
            2: "sorting_algorithms",
            3: "graph_algorithms",
            4: "dynamic_programming",
            5: "machine_learning",
        }
        return topic_mapping.get(chapter_num, "algorithm_analysis")

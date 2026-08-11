"""Service for generating course outlines."""

from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from ..models.tutorial import Tutorial
from ..models.chapter import Chapter
from ..services.prerequisite_checker import PrerequisiteChecker
from ..services.knowledge_inferencer import DynamicKnowledgeInferencer
from ..services.llm_adapter import ClaudeAdapter, OpenAIAAdapter
from ..services.claude_config_service import ClaudeConfigService
from .crypto_service import SecureCryptoService
import json


class OutlineGenerator:
    """Generates comprehensive course outlines based on user profile and knowledge level."""

    def __init__(self, db_session: Session, crypto: SecureCryptoService,
                 claude_config_service: ClaudeConfigService):
        self.db = db_session
        self.crypto = crypto
        self.claude_service = claude_config_service
        self.checker = PrerequisiteChecker()
        self.inferencer = DynamicKnowledgeInferencer()

    def build_outline_prompt(self, profile: Dict[str, Any], mastery_map: Dict[str, str],
                             topics: List[str]) -> str:
        """Build a comprehensive prompt for generating a course outline."""
        system_prompt = """You are an expert computer science educator designing a personalized learning curriculum. Create a detailed course outline with comprehensive chapter breakdowns. Each chapter should include: - Clear learning objectives - Detailed theoretical explanations - Mathematical formulas with step-by-step derivations where appropriate - Code examples in relevant programming languages - Practice exercises with varying difficulty levels - Connections to prerequisite topics when necessary Design the content to be accessible yet rigorous, matching the learner's current skill level while appropriately challenging them to advance. Use real-world examples and analogies to aid understanding. Structure the material in a logical progression from foundational concepts to more advanced applications."""

        context_parts = []
        if profile.get("programming_level"):
            context_parts.append(f"User programming level: {profile['programming_level']}/5")
        if profile.get("learning_goal"):
            context_parts.append(f"Learning goal: {profile['learning_goal']}")
        if profile.get("available_hours_per_day"):
            context_parts.append(f"Avg study time: {profile['available_hours_per_day']} hours/day")

        context_str = "; ".join(context_parts) or "General learner"

        topic_list = ", ".join(topics) if topics else "core computer science topics"

        knowledge_lines = "".join([f"  - {topic}: {level}\n" for topic, level in mastery_map.items()])

        prompt = f"""You are helping design a personalized learning path for: {context_str}.

Current knowledge assessment (based on profile analysis):
{knowledge_lines.strip()}

Please create a detailed outline for a course covering these topics: {topic_list}.

The outline should contain chapters numbered sequentially, each with clear titles and descriptions. Each chapter must contain thorough technical content including formulas, code samples, and exercises.

Format your response as valid JSON with the following structure:
{{
  "course_title": "Descriptive title of the course",
  "estimated_duration_days": 30,
  "total_chapters": 8,
  "chapters": [
    {{
      "chapter_number": 1,
      "title": "Chapter 1 Title",
      "description": "Brief overview of what this chapter covers",
      "objectives": ["List of learning objectives"],
      "estimated_reading_hours": 5
    }},
    ... more chapters ...
  ]
}}

DO NOT add any conversational text before or after the JSON output."""

        return system_prompt + "\n\n" + prompt

    def generate(self, config_id: UUID, user_id: UUID, topics: List[str],
                 outline_id: Optional[str] = None, mastery_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate a complete course outline.

        Returns:
            Dictionary containing task status, outline data, and metadata
        """
        # Get configuration
        config = self.claude_service.get_config_for_api_call(user_id, config_id)
        if not config:
            raise ValueError("Invalid configuration")

        # Determine which adapter to use
        model_name_lower = config["model_name"].lower()
        if "openai" in model_name_lower or "gpt-" in model_name_lower:
            llm_adapter = OpenAIAAdapter(config)
        else:
            llm_adapter = ClaudeAdapter(config)

        # Get user profile data (in implementation, fetch from DB)
        profile = {}

        # Infer knowledge map if not provided
        if not mastery_map:
            mastery_map = self.inferencer.infer_knowledge_graph(profile)

        # Build prompt
        prompt = self.build_outline_prompt(profile, mastery_map, topics)

        # Generate outline
        outline_text = llm_adapter.generate_content(prompt)

        # Clean and parse response
        try:
            # Remove any markdown code blocks
            clean_text = outline_text.replace("```json", "").replace("```", "")
            outline_data = json.loads(clean_text.strip())
        except (json.JSONDecodeError, Exception) as e:
            outline_data = {"error": f"Failed to parse outline: {str(e)}", "raw": outline_text[:500]}

        # Cleanup
        llm_adapter.close()

        return {
            "status": "success",
            "outline": outline_data,
            "model_used": config["model_name"],
            "prompt_tokens_estimate": len(prompt.split()),
            "knowledge_map": mastery_map
        }

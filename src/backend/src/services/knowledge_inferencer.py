from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class DynamicKnowledgeInferencer:
    """Dynamically infers a user's knowledge levels across CS topics based on their profile.

    This uses both heuristic rules and (optionally) LLM-based inference depending on
    whether an adapter is available.
    """

    # Default knowledge mapping for users without explicit info
    DEFAULT_MAPPING = {
        "algorithm_fundamentals": "beginner",
        "data_structures": "beginner",
        "discrete_math": "beginner",
        "linear_algebra": "beginner",
        "calculus": "beginner",
        "probability": "beginner",
        "graph_theory": "beginner",
        "recursion": "beginner",
        "dynamic_programming": "beginner",
        "machine_learning_prerequisites": "beginner"
    }

    def __init__(self, llm_adapter=None):
        """
        Args:
            llm_adapter: Optional LLMAdapter for more nuanced inference. If None,
                         only heuristic-based inference is used.
        """
        self.llm_adapter = llm_adapter

    def infer_knowledge_graph(self, profile: Dict[str, Any]) -> Dict[str, str]:
        """
        Infer knowledge levels from profile information using heuristics + optional LLM.

        Args:
            profile: Dictionary containing user profile data with keys:
                - programming_level (int, 1-5): Self-assessed skill level
                - math_background (str): Text description of math background
                - learning_goal (str): Learning objective
                - preferred_style (str): Preferred learning style
                - available_hours_per_day (float): Daily study time

        Returns:
            Mapping from topic name to skill level (beginner/intermediate/advanced)
        """
        # Start with default map
        inferred = self.DEFAULT_MAPPING.copy()

        # Apply heuristic adjustments based on profile data
        self._apply_heuristic_adjustments(inferred, profile)

        # If LLM adapter is available, refine the inference
        if self.llm_adapter:
            refined = self._refine_with_llm(inferred, profile)
            if refined:
                inferred = refined

        logger.info(f"Knowledge inference completed: {inferred}")
        return inferred

    def _apply_heuristic_adjustments(self, inferred: Dict[str, str], profile: Dict[str, Any]) -> None:
        """Adjust knowledge levels based on profile heuristics."""
        prog_level = profile.get("programming_level", 0)

        # Adjust based on programming level
        if prog_level >= 4:  # Experienced programmer
            inferred.update({
                "algorithm_fundamentals": "intermediate",
                "data_structures": "intermediate",
                "recursion": "intermediate",
                "dynamic_programming": "beginner"  # Still needs practice
            })
        elif prog_level == 3:  # Moderate experience
            inferred["algorithm_fundamentals"] = "beginner"
            inferred["data_structures"] = "beginner"

        # Check math background for hints
        math_bg = str(profile.get("math_background", "")).lower()
        if "linear algebra" in math_bg or "matrix" in math_bg or "vector" in math_bg:
            inferred["linear_algebra"] = "intermediate"
        if ("calculus" in math_bg or "integration" in math_bg or
            "derivative" in math_bg or "limit" in math_bg):
            inferred["calculus"] = "intermediate"
        if ("probability" in math_bg or "statistics" in math_bg or
            "distribution" in math_bg):
            inferred["probability"] = "intermediate"
        if "discrete math" in math_bg or "logic" in math_bg or "set theory" in math_bg:
            inferred["discrete_math"] = "intermediate"

        # Adjust based on learning goal
        goal = str(profile.get("learning_goal", "")).lower()
        if "research" in goal or "phd" in goal or "thesis" in goal:
            # Research-oriented learners typically have stronger foundations
            for key in inferred:
                if inferred[key] == "beginner":
                    inferred[key] = "intermediate"
        if "job" in goal or "interview" in goal:
            # Job seekers need practical algorithms focus
            inferred["algorithm_fundamentals"] = "intermediate"
            inferred["data_structures"] = "intermediate"

    def _refine_with_llm(self, initial_map: Dict[str, str], profile: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Refine inference using LLM adapter for more nuanced analysis."""
        if not self.llm_adapter:
            return None

        try:
            # Build prompt for the LLM
            prompt = f"""You are a senior computer science educator. Based on the following user profile, provide a detailed assessment of their knowledge levels in computer science fundamentals. Output ONLY valid JSON with no extra text.

User Profile:
- Programming Level: {profile.get('programming_level', 'Unknown')}/5
- Math Background: {profile.get('math_background', 'None')}
- Learning Goal: {profile.get('learning_goal', 'None')}
- Available Hours Per Day: {profile.get('available_hours_per_day', '?')} hours
- Preferred Style: {profile.get('preferred_style', 'text')}

Assess these topics and assign a level (beginner/intermediate/advanced):
{{
  "algorithm_fundamentals": "...",
  "data_structures": "...",
  "discrete_math": "...",
  "linear_algebra": "...",
  "calculus": "...",
  "probability": "...",
  "graph_theory": "...",
  "recursion": "...",
  "dynamic_programming": "...",
  "machine_learning_prerequisites": "..."
}}"""

            response = self.llm_adapter.generate_content(prompt)
            # Try to parse JSON from response
            import re
            # Find JSON block in response
            json_match = re.search(r'\{[^}]*\}', response, re.DOTALL)
            if json_match:
                refined = json.loads(json_match.group())
                # Validate all required keys exist
                required_keys = set(self.DEFAULT_MAPPING.keys())
                if set(refined.keys()) == required_keys:
                    return refined
        except Exception as e:
            logger.warning(f"LLM refinement failed: {e}, falling back to heuristics")

        return initial_map

    def validate_mastery_map(self, mastery_map: Dict[str, str]) -> bool:
        """Validate that a mastery map contains all expected keys with valid values."""
        expected_keys = set(self.DEFAULT_MAPPING.keys())
        valid_levels = {"beginner", "intermediate", "advanced"}

        if set(mastery_map.keys()) != expected_keys:
            return False
        if any(level not in valid_levels for level in mastery_map.values()):
            return False
        return True

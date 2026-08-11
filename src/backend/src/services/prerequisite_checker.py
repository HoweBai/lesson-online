from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Knowledge dependency graph for computer science topics
KNOWLEDGE_GRAPH = {
    "algorithm_analysis": ["basic_math", "discrete_math"],
    "sorting_algorithms": ["basic_data_structures", "algorithm_analysis"],
    "graph_algorithms": ["basic_data_structures", "discrete_math", "recursion"],
    "dynamic_programming": ["recursion", "mathematical_induction"],
    "machine_learning": ["linear_algebra", "probability", "calculus"],
    "neural_networks": ["machine_learning", "linear_algebra", "calculus"],
    "computer_graphics": ["linear_algebra", "geometry", "algorithms"],
    "compilers": ["formal_languages", "automata_theory", "algorithms"],
    "search_algorithms": ["data_structures", "algorithm_analysis"],
    "database_systems": ["data_structures", "discrete_math"],
    "operating_systems": ["computer_organization", "algorithms"],
}


class PrerequisiteChecker:
    """Checks if a user has required knowledge before advancing to new topics.

    This class integrates with the knowledge inference system to determine
    appropriate chapter generation order and prerequisites reminders.
    """

    def __init__(self, knowledge_inferencer=None):
        """
        Args:
            knowledge_inferencer: Optional DynamicKnowledgeInferencer instance
                                to fetch current user mastery levels
        """
        self.ki = knowledge_inferencer

    def check_prerequisites(self, chapter_topic: str, user_mastery: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Check if the user has mastered prerequisites for this topic.

        Args:
            chapter_topic: The topic/chapter being considered (e.g., "sorting_algorithms")
            user_mastery: Dictionary mapping topic names to mastery levels

        Returns:
            Tuple of (needs_review_list, list_of_missing_topics)

        Example:
            needs_review, missing = checker.check_prerequisites(
                "dynamic_programming",
                {"recursion": "intermediate", "mathematical_induction": "beginner"}
            )
            # returns (True, ["mathematical_induction"]) because induction is required but beginner
        """
        required_topics = set(KNOWLEDGE_GRAPH.get(chapter_topic, []))

        # Check each required topic - consider anything other than "advanced" as needing review
        missing_topics = [t for t in required_topics
                        if t not in user_mastery or user_mastery[t] in ["beginner", "intermediate"]]

        needs_review = len(missing_topics) > 0

        if needs_review and missing_topics:
            logger.info(f"Prerequisites checked for {chapter_topic}. Missing topics: {missing_topics}")

        return needs_review, missing_topics

    def generate_prerequisites_for_review(self, topics: List[str], mastery_map: Dict[str, str]) -> str:
        """Generate brief review content for missing prerequisites."""
        if not topics:
            return ""

        reviews = []
        for topic in topics:
            level = mastery_map.get(topic, "beginner")
            review_text = self._get_prerequisite_summary(topic, level)
            reviews.append(review_text)

        return "\n".join(reviews)

    def _get_prerequisite_summary(self, topic: str, level: str) -> str:
        """Get a short summary/review point for a prerequisite topic."""
        summaries = {
            "basic_math": "Review basic arithmetic operations, functions, and algebra.",
            "discrete_math": "Review sets, logic, proofs, and combinatorics.",
            "recursion": "Review function calls, base cases, and stack behavior.",
            "linear_algebra": "Review vectors, matrices, and linear transformations.",
            "calculus": "Review derivatives, integrals, and limits.",
            "probability": "Review basic probability rules and distributions.",
            "data_structures": "Review arrays, linked lists, trees, and hash tables.",
        }
        return summaries.get(topic, f"Review {topic} basics at {level} level.")

    def get_dependency_tree(self, chapter_topic: str, depth: int = 2) -> Dict[str, List[str]]:
        """Get the dependency tree for a topic up to specified depth.

        Useful for understanding cascade requirements when a user lacks multiple
        foundational topics.
        """
        def build_tree(current_topic: str, current_depth: int, visited: set = None) -> Dict[str, List[str]]:
            if visited is None:
                visited = set()
            if current_depth == 0 or current_topic in visited:
                return {}

            visited.add(current_topic)
            result = {current_topic: []}
            for dep in KNOWLEDGE_GRAPH.get(current_topic, []):
                if dep not in visited:
                    subtree = build_tree(dep, current_depth - 1, visited.copy())
                    result[current_topic].append(dep)
                    for sub_key, sub_value in subtree.items():
                        result[sub_key] = sub_value
            return result

        return build_tree(chapter_topic, depth)

    def suggest_review_order(self, missing_topics: List[str]) -> List[str]:
        """Suggest an optimal order for reviewing missing prerequisites."""
        # Simple topological sort based on dependency depth
        ranked = []
        for topic in missing_topics:
            depth = self._count_dependencies(topic)
            ranked.append((depth, topic))
        ranked.sort()
        return [t for _, t in ranked]

    def _count_dependencies(self, topic: str, max_depth: int = 5) -> int:
        """Count how many transitive dependencies a topic has (used for ranking)."""
        count = 0
        visited = set()
        queue = [(topic, 0)]
        while queue and count < max_depth:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if depth > 0:
                count += depth
            for dep in KNOWLEDGE_GRAPH.get(current, []):
                if dep not in visited:
                    queue.append((dep, depth + 1))
        return count

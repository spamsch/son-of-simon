"""Task: Skill Enrichment

Provides a tool for the agent to enrich bare skills with AI-generated
tasks, examples, and behavior notes.
"""

from macbot.tasks.base import Task
from macbot.tasks.registry import TaskRegistry


class EnrichSkillTask(Task):
    """Enrich a bare skill with AI-generated guidance."""

    @property
    def name(self) -> str:
        return "enrich_skill"

    @property
    def description(self) -> str:
        return (
            "Enrich a bare skill (e.g. from ClawHub) with task mappings, "
            "examples, and behavior notes using AI. Run this after installing "
            "a skill to make it fully usable."
        )

    async def execute(self, skill_id: str, force: bool = False) -> str:
        """Enrich a skill by ID.

        Args:
            skill_id: The ID of the skill to enrich.
            force: If true, re-enrich even if already enriched.

        Returns:
            Summary of what was enriched.
        """
        from macbot.skills import SkillsRegistry, enrich_skill, is_enriched

        registry = SkillsRegistry()
        skill = registry.get(skill_id)

        if not skill:
            available = [s.id for s in registry.list_skills()]
            return f"Skill '{skill_id}' not found. Available: {', '.join(available)}"

        if is_enriched(skill) and not force:
            return f"Skill '{skill_id}' is already enriched. Use force=true to re-enrich."

        if not skill.source_path:
            return f"Cannot enrich built-in skill '{skill_id}' — it has no file on disk."

        enriched = await enrich_skill(skill, force=force)
        return (
            f"Enriched '{enriched.id}' successfully. "
            f"Tasks: {', '.join(enriched.tasks) if enriched.tasks else '(none)'}. "
            f"Examples: {len(enriched.examples)}. "
            f"Body: {len(enriched.body)} chars."
        )


def register_skill_enrich_tasks(registry: TaskRegistry) -> None:
    """Register skill enrichment tasks."""
    registry.register(EnrichSkillTask())

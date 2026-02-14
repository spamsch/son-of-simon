"""Tasks: Mindwtr GTD Integration

Provides tasks for the agent to interact with a Mindwtr instance by reading
and writing its sync data.json file directly. No server required.

The desktop app's file watcher detects changes to the sync folder and
auto-refreshes the UI (~750ms delay).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from macbot.config import settings
from macbot.tasks.base import Task

# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

_VALID_STATUSES = {
    "inbox", "todo", "next", "in-progress", "waiting",
    "someday", "reference", "done", "archived",
}

_VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


def _data_path() -> Path:
    return Path(settings.mindwtr_data_path).expanduser()


def _load() -> dict[str, Any]:
    """Load AppData from the sync JSON file."""
    path = _data_path()
    if not path.exists():
        return {"tasks": [], "projects": [], "sections": [], "areas": [], "settings": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Ensure all top-level keys exist
        data.setdefault("tasks", [])
        data.setdefault("projects", [])
        data.setdefault("sections", [])
        data.setdefault("areas", [])
        data.setdefault("settings", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"tasks": [], "projects": [], "sections": [], "areas": [], "settings": {}}


def _save(data: dict[str, Any]) -> None:
    """Write AppData back to the sync JSON file."""
    path = _data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _generate_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Quick-add parser
# ---------------------------------------------------------------------------

_DAY_NAMES = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


def _parse_natural_date(text: str) -> str | None:
    """Parse a natural language date string into ISO date (YYYY-MM-DD)."""
    text = text.strip().lower()
    today = datetime.now().date()

    if not text or text == "today":
        return today.isoformat()

    if text == "tomorrow":
        return (today + timedelta(days=1)).isoformat()

    if text == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    # "next week/month/year"
    if text == "next week":
        return (today + timedelta(weeks=1)).isoformat()
    if text == "next month":
        month = today.month + 1
        year = today.year + (1 if month > 12 else 0)
        month = month if month <= 12 else month - 12
        day = min(today.day, 28)
        return datetime(year, month, day).date().isoformat()
    if text == "next year":
        return datetime(today.year + 1, today.month, min(today.day, 28)).date().isoformat()

    # "in N days/weeks/months"
    m = re.match(r"in\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)", text)
    if m:
        n = int(m.group(1))
        unit = m.group(2).rstrip("s")
        if unit == "day":
            return (today + timedelta(days=n)).isoformat()
        if unit == "week":
            return (today + timedelta(weeks=n)).isoformat()
        if unit == "month":
            month = today.month + n
            year = today.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            day = min(today.day, 28)
            return datetime(year, month, day).date().isoformat()
        if unit == "year":
            return datetime(today.year + n, today.month, min(today.day, 28)).date().isoformat()

    # Day name: "monday", "tue", etc.
    if text in _DAY_NAMES:
        target = _DAY_NAMES[text]
        current = today.weekday()
        delta = (target - current) % 7
        if delta == 0:
            delta = 7  # Next occurrence
        return (today + timedelta(days=delta)).isoformat()

    # ISO date
    iso_match = re.match(r"\d{4}-\d{2}-\d{2}", text)
    if iso_match:
        return iso_match.group(0)

    return None


def _parse_quick_add(
    text: str,
    projects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Parse quick-add syntax into title + properties.

    Supports: @context, #tag, /due:date, /priority:level, /status:status,
    /note:text, +ProjectName
    """
    props: dict[str, Any] = {}
    working = text

    # Extract contexts (@word)
    contexts = re.findall(r"@([\w-]+)", working)
    if contexts:
        props["contexts"] = contexts
        working = re.sub(r"@[\w-]+", "", working)

    # Extract tags (#word)
    tags = re.findall(r"#([\w-]+)", working)
    if tags:
        props["tags"] = tags
        working = re.sub(r"#[\w-]+", "", working)

    # Extract /due:value
    due_match = re.search(r"/due:([^\s/]+(?:\s+(?:days?|weeks?|months?|years?))?)", working)
    if due_match:
        due_str = due_match.group(1)
        parsed = _parse_natural_date(due_str)
        if parsed:
            props["dueDate"] = parsed
        working = working[:due_match.start()] + working[due_match.end():]

    # Extract /priority:value
    pri_match = re.search(r"/priority:(low|medium|high|urgent)", working, re.IGNORECASE)
    if pri_match:
        props["priority"] = pri_match.group(1).lower()
        working = working[:pri_match.start()] + working[pri_match.end():]

    # Extract /status:value or bare /status
    status_match = re.search(
        r"/(inbox|todo|next|in-progress|waiting|someday|reference|done|archived)\b",
        working,
        re.IGNORECASE,
    )
    if status_match:
        props["status"] = status_match.group(1).lower()
        working = working[:status_match.start()] + working[status_match.end():]

    # Extract /note:value
    note_match = re.search(r"/note:([^/]+?)(?=\s/|$)", working)
    if note_match:
        props["description"] = note_match.group(1).strip()
        working = working[:note_match.start()] + working[note_match.end():]

    # Extract +ProjectName
    proj_match = re.search(r"\+(\S+)", working)
    if proj_match:
        proj_name = proj_match.group(1)
        working = working[:proj_match.start()] + working[proj_match.end():]
        # Try to match existing project
        if projects:
            for p in projects:
                if p.get("title", "").lower() == proj_name.lower():
                    props["projectId"] = p["id"]
                    break

    # Clean up title
    title = re.sub(r"\s{2,}", " ", working).strip()

    return {"title": title, "props": props}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _matches_query(task: dict[str, Any], query: str) -> bool:
    """Check if a task matches a search query."""
    q = query.lower()
    title = (task.get("title") or "").lower()
    desc = (task.get("description") or "").lower()
    tags = [t.lower() for t in task.get("tags", [])]
    contexts = [c.lower() for c in task.get("contexts", [])]

    # Check @context filter
    ctx_match = re.search(r"@([\w-]+)", q)
    if ctx_match:
        target_ctx = ctx_match.group(1).lower()
        if target_ctx not in contexts:
            return False
        q = re.sub(r"@[\w-]+", "", q).strip()

    # Check #tag filter
    tag_match = re.search(r"#([\w-]+)", q)
    if tag_match:
        target_tag = tag_match.group(1).lower()
        if target_tag not in tags:
            return False
        q = re.sub(r"#[\w-]+", "", q).strip()

    # Remaining query is a text search
    if q:
        return q in title or q in desc or any(q in t for t in tags)

    return True


def _matches_project_query(project: dict[str, Any], query: str) -> bool:
    """Check if a project matches a search query."""
    q = query.lower()
    title = (project.get("title") or "").lower()
    notes = (project.get("supportNotes") or "").lower()
    return q in title or q in notes


# ---------------------------------------------------------------------------
# Recurrence
# ---------------------------------------------------------------------------

def _create_next_recurring_task(
    task: dict[str, Any],
    completed_at: str,
) -> dict[str, Any] | None:
    """Create the next instance of a recurring task after completion."""
    recurrence = task.get("recurrence")
    if not recurrence:
        return None

    # Extract rule
    if isinstance(recurrence, str):
        rule = recurrence
        strategy = "strict"
    elif isinstance(recurrence, dict):
        rule = recurrence.get("rule", "")
        strategy = recurrence.get("strategy", "strict")
    else:
        return None

    if rule not in ("daily", "weekly", "monthly", "yearly"):
        return None

    # Determine base date
    due_date = task.get("dueDate")
    if strategy == "strict" and due_date:
        base_str = due_date
    else:
        base_str = completed_at

    try:
        base = datetime.fromisoformat(base_str).date()
    except (ValueError, TypeError):
        base = datetime.now().date()

    # Calculate next date
    if rule == "daily":
        next_date = base + timedelta(days=1)
    elif rule == "weekly":
        next_date = base + timedelta(weeks=1)
    elif rule == "monthly":
        month = base.month + 1
        year = base.year + (1 if month > 12 else 0)
        month = month if month <= 12 else month - 12
        day = min(base.day, 28)
        next_date = datetime(year, month, day).date()
    elif rule == "yearly":
        next_date = datetime(base.year + 1, base.month, min(base.day, 28)).date()
    else:
        return None

    now = _now_iso()
    new_task: dict[str, Any] = {
        "id": _generate_id(),
        "title": task.get("title", ""),
        "status": "next",
        "tags": list(task.get("tags", [])),
        "contexts": list(task.get("contexts", [])),
        "dueDate": next_date.isoformat(),
        "recurrence": task.get("recurrence"),
        "createdAt": now,
        "updatedAt": now,
    }

    # Carry over optional fields
    for field in ("description", "priority", "projectId", "timeEstimate", "location"):
        if task.get(field):
            new_task[field] = task[field]

    # Reset checklist
    checklist = task.get("checklist")
    if checklist:
        new_task["checklist"] = [
            {"id": _generate_id(), "title": item.get("title", ""), "isCompleted": False}
            for item in checklist
        ]

    return new_task


# ---------------------------------------------------------------------------
# Task classes
# ---------------------------------------------------------------------------

class MindwtrListTasksTask(Task):
    """List tasks from Mindwtr with optional filters."""

    @property
    def name(self) -> str:
        return "mindwtr_list_tasks"

    @property
    def description(self) -> str:
        return (
            "List tasks from Mindwtr. Filter by status (inbox, todo, next, in-progress, "
            "waiting, someday, done, archived) or search by query string. "
            "By default excludes completed and deleted tasks."
        )

    async def execute(
        self,
        status: str = "",
        query: str = "",
        include_completed: bool = False,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """List tasks with optional filters.

        Args:
            status: Filter by status (inbox, todo, next, in-progress, waiting, someday, done, archived)
            query: Search query to filter tasks
            include_completed: Include done and archived tasks
            include_deleted: Include soft-deleted tasks

        Returns:
            Dictionary with tasks list
        """
        data = _load()
        tasks = data["tasks"]

        if not include_deleted:
            tasks = [t for t in tasks if not t.get("deletedAt")]
        if not include_completed:
            tasks = [t for t in tasks if t.get("status") not in ("done", "archived")]
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        if query:
            tasks = [t for t in tasks if _matches_query(t, query)]

        return {"success": True, "count": len(tasks), "tasks": tasks}


class MindwtrAddTaskTask(Task):
    """Create a new task in Mindwtr."""

    @property
    def name(self) -> str:
        return "mindwtr_add_task"

    @property
    def description(self) -> str:
        return (
            "Create a new task in Mindwtr. Use the 'input' parameter for quick-add syntax: "
            "\"Buy milk @errands #shopping /due:tomorrow /priority:high +ProjectName\". "
            "Contexts use @, tags use #, due dates use /due:, priority uses /priority:, "
            "and project assignment uses +. Alternatively pass title and individual properties."
        )

    async def execute(
        self,
        input: str = "",
        title: str = "",
        status: str = "",
        priority: str = "",
        due_date: str = "",
        project_id: str = "",
        section_id: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Create a task.

        Args:
            input: Quick-add string with natural language (e.g., "Buy milk @errands #shopping /due:tomorrow")
            title: Task title (used if input is empty)
            status: Initial status (inbox, todo, next, in-progress, waiting, someday)
            priority: Priority level (low, medium, high, urgent)
            due_date: Due date in ISO format (YYYY-MM-DD) or natural language (tomorrow, next monday)
            project_id: Project ID to assign to
            section_id: Section ID within the project to assign to (requires project_id)
            description: Task description/notes

        Returns:
            Dictionary with created task
        """
        if not input and not title:
            return {"success": False, "error": "Either 'input' or 'title' is required"}

        data = _load()
        now = _now_iso()

        # Parse quick-add or use explicit fields
        if input:
            parsed = _parse_quick_add(input, data.get("projects"))
            task_title = parsed["title"]
            props = parsed["props"]
        else:
            task_title = title
            props = {}

        # Override with explicit parameters
        if status and status in _VALID_STATUSES:
            props["status"] = status
        if priority and priority in _VALID_PRIORITIES:
            props["priority"] = priority
        if due_date:
            parsed_date = _parse_natural_date(due_date)
            if parsed_date:
                props["dueDate"] = parsed_date
        if project_id:
            props["projectId"] = project_id
        if section_id:
            # Ensure section belongs to the target project
            target_project = project_id or props.get("projectId", "")
            if not target_project:
                return {"success": False, "error": "section_id requires a project_id"}
            section = next(
                (s for s in data.get("sections", [])
                 if s.get("id") == section_id and not s.get("deletedAt")),
                None,
            )
            if not section:
                return {"success": False, "error": f"Section {section_id} not found"}
            if section.get("projectId") != target_project:
                return {"success": False, "error": "Section does not belong to the specified project"}
            props["sectionId"] = section_id
        if description:
            props["description"] = description

        task: dict[str, Any] = {
            "id": _generate_id(),
            "title": task_title,
            "status": props.pop("status", "inbox"),
            "tags": props.pop("tags", []),
            "contexts": props.pop("contexts", []),
            "createdAt": now,
            "updatedAt": now,
            **props,
        }

        data["tasks"].append(task)
        _save(data)

        return {"success": True, "task": task}


class MindwtrGetTaskTask(Task):
    """Get a specific task by ID."""

    @property
    def name(self) -> str:
        return "mindwtr_get_task"

    @property
    def description(self) -> str:
        return "Get full details of a Mindwtr task by its ID."

    async def execute(self, task_id: str) -> dict[str, Any]:
        """Get task details.

        Args:
            task_id: The task ID

        Returns:
            Dictionary with task details
        """
        data = _load()
        for t in data["tasks"]:
            if t.get("id") == task_id:
                return {"success": True, "task": t}
        return {"success": False, "error": f"Task {task_id} not found"}


class MindwtrUpdateTaskTask(Task):
    """Update an existing task's properties."""

    @property
    def name(self) -> str:
        return "mindwtr_update_task"

    @property
    def description(self) -> str:
        return (
            "Update a Mindwtr task's properties. Can change title, status, priority, "
            "due date, project, tags, contexts, and description. "
            "Valid statuses: inbox, todo, next, in-progress, waiting, someday, done, archived."
        )

    async def execute(
        self,
        task_id: str,
        title: str = "",
        status: str = "",
        priority: str = "",
        due_date: str = "",
        project_id: str = "",
        section_id: str = "",
        description: str = "",
        tags: list[str] | None = None,
        contexts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update a task.

        Args:
            task_id: The task ID to update
            title: New title
            status: New status (inbox, todo, next, in-progress, waiting, someday, done, archived)
            priority: New priority (low, medium, high, urgent)
            due_date: New due date in ISO format (YYYY-MM-DD) or natural language
            project_id: New project ID or empty to clear
            section_id: Section ID within the project (use "__clear__" to remove from section)
            description: New description/notes
            tags: New tags list (replaces existing)
            contexts: New contexts list (replaces existing)

        Returns:
            Dictionary with updated task
        """
        data = _load()
        now = _now_iso()

        for i, t in enumerate(data["tasks"]):
            if t.get("id") == task_id:
                if title:
                    t["title"] = title
                if status and status in _VALID_STATUSES:
                    old_status = t.get("status")
                    t["status"] = status
                    # Handle completion state transitions
                    if status in ("done", "archived") and old_status not in ("done", "archived"):
                        t["completedAt"] = now
                    elif status not in ("done", "archived") and old_status in ("done", "archived"):
                        t.pop("completedAt", None)
                if priority and priority in _VALID_PRIORITIES:
                    t["priority"] = priority
                if due_date:
                    parsed_date = _parse_natural_date(due_date)
                    if parsed_date:
                        t["dueDate"] = parsed_date
                if project_id:
                    old_project = t.get("projectId")
                    t["projectId"] = project_id
                    # Clear section when moving to a different project (unless section_id also provided)
                    if old_project != project_id and not section_id:
                        t.pop("sectionId", None)
                if section_id:
                    if section_id == "__clear__":
                        t.pop("sectionId", None)
                    else:
                        target_project = project_id or t.get("projectId", "")
                        if not target_project:
                            return {"success": False, "error": "section_id requires the task to have a project"}
                        section = next(
                            (s for s in data.get("sections", [])
                             if s.get("id") == section_id and not s.get("deletedAt")),
                            None,
                        )
                        if not section:
                            return {"success": False, "error": f"Section {section_id} not found"}
                        if section.get("projectId") != target_project:
                            return {"success": False, "error": "Section does not belong to the task's project"}
                        t["sectionId"] = section_id
                if description:
                    t["description"] = description
                if tags is not None:
                    t["tags"] = tags
                if contexts is not None:
                    t["contexts"] = contexts

                t["updatedAt"] = now
                data["tasks"][i] = t
                _save(data)
                return {"success": True, "task": t}

        return {"success": False, "error": f"Task {task_id} not found"}


class MindwtrCompleteTaskTask(Task):
    """Mark a task as done."""

    @property
    def name(self) -> str:
        return "mindwtr_complete_task"

    @property
    def description(self) -> str:
        return (
            "Mark a Mindwtr task as done. If the task has a recurrence rule, "
            "a new recurring instance is automatically created."
        )

    async def execute(self, task_id: str) -> dict[str, Any]:
        """Complete a task.

        Args:
            task_id: The task ID to complete

        Returns:
            Dictionary with completed task
        """
        data = _load()
        now = _now_iso()

        for i, t in enumerate(data["tasks"]):
            if t.get("id") == task_id:
                t["status"] = "done"
                t["completedAt"] = now
                t["updatedAt"] = now
                t["isFocusedToday"] = False
                data["tasks"][i] = t

                # Handle recurrence
                next_task = _create_next_recurring_task(t, now)
                if next_task:
                    data["tasks"].append(next_task)

                _save(data)

                result: dict[str, Any] = {"success": True, "task": t}
                if next_task:
                    result["next_recurring_task"] = next_task
                return result

        return {"success": False, "error": f"Task {task_id} not found"}


class MindwtrArchiveTaskTask(Task):
    """Archive a completed task."""

    @property
    def name(self) -> str:
        return "mindwtr_archive_task"

    @property
    def description(self) -> str:
        return "Archive a Mindwtr task. Typically used on tasks that are already done."

    async def execute(self, task_id: str) -> dict[str, Any]:
        """Archive a task.

        Args:
            task_id: The task ID to archive

        Returns:
            Dictionary with archived task
        """
        data = _load()
        now = _now_iso()

        for i, t in enumerate(data["tasks"]):
            if t.get("id") == task_id:
                t["status"] = "archived"
                if not t.get("completedAt"):
                    t["completedAt"] = now
                t["updatedAt"] = now
                t["isFocusedToday"] = False
                data["tasks"][i] = t
                _save(data)
                return {"success": True, "task": t}

        return {"success": False, "error": f"Task {task_id} not found"}


class MindwtrDeleteTaskTask(Task):
    """Soft-delete a task."""

    @property
    def name(self) -> str:
        return "mindwtr_delete_task"

    @property
    def description(self) -> str:
        return (
            "Soft-delete a Mindwtr task. The task is marked with a deletedAt timestamp "
            "but not permanently removed. Can be recovered."
        )

    async def execute(self, task_id: str) -> dict[str, Any]:
        """Soft-delete a task.

        Args:
            task_id: The task ID to delete

        Returns:
            Dictionary with success status
        """
        data = _load()
        now = _now_iso()

        for i, t in enumerate(data["tasks"]):
            if t.get("id") == task_id:
                t["deletedAt"] = now
                t["updatedAt"] = now
                data["tasks"][i] = t
                _save(data)
                return {"success": True, "message": f"Task {task_id} deleted"}

        return {"success": False, "error": f"Task {task_id} not found"}


class MindwtrListProjectsTask(Task):
    """List projects from Mindwtr."""

    @property
    def name(self) -> str:
        return "mindwtr_list_projects"

    @property
    def description(self) -> str:
        return (
            "List all active projects in Mindwtr. "
            "Projects organize tasks and can have statuses: active, someday, waiting, archived."
        )

    async def execute(self) -> dict[str, Any]:
        """List projects.

        Returns:
            Dictionary with projects list
        """
        data = _load()
        projects = [p for p in data.get("projects", []) if not p.get("deletedAt")]
        return {"success": True, "count": len(projects), "projects": projects}


class MindwtrCreateProjectTask(Task):
    """Create a new project in Mindwtr."""

    @property
    def name(self) -> str:
        return "mindwtr_create_project"

    @property
    def description(self) -> str:
        return (
            "Create a new project in Mindwtr. Projects group related tasks. "
            "Status can be: active, someday, waiting, archived."
        )

    async def execute(
        self,
        title: str,
        status: str = "active",
        area_id: str = "",
        is_sequential: bool = False,
    ) -> dict[str, Any]:
        """Create a project.

        Args:
            title: Project title
            status: Project status (active, someday, waiting, archived)
            area_id: Area ID to assign to
            is_sequential: Whether tasks must be done in order

        Returns:
            Dictionary with created project
        """
        if not title.strip():
            return {"success": False, "error": "Project title is required"}

        data = _load()
        now = _now_iso()

        project: dict[str, Any] = {
            "id": _generate_id(),
            "title": title.strip(),
            "status": status if status in ("active", "someday", "waiting", "archived") else "active",
            "isSequential": is_sequential,
            "createdAt": now,
            "updatedAt": now,
        }
        if area_id:
            project["areaId"] = area_id

        data["projects"].append(project)
        _save(data)

        return {"success": True, "project": project}


class MindwtrUpdateProjectTask(Task):
    """Update an existing project's properties."""

    @property
    def name(self) -> str:
        return "mindwtr_update_project"

    @property
    def description(self) -> str:
        return (
            "Update a Mindwtr project's properties. Can change title, status, "
            "area, and sequential mode. "
            "Valid statuses: active, someday, waiting, archived."
        )

    async def execute(
        self,
        project_id: str,
        title: str = "",
        status: str = "",
        area_id: str = "",
        is_sequential: bool | None = None,
    ) -> dict[str, Any]:
        """Update a project.

        Args:
            project_id: The project ID to update
            title: New title
            status: New status (active, someday, waiting, archived)
            area_id: New area ID
            is_sequential: Whether tasks must be done in order

        Returns:
            Dictionary with updated project
        """
        data = _load()
        now = _now_iso()

        for i, p in enumerate(data["projects"]):
            if p.get("id") == project_id:
                if title:
                    p["title"] = title.strip()
                if status and status in ("active", "someday", "waiting", "archived"):
                    p["status"] = status
                if area_id:
                    p["areaId"] = area_id
                if is_sequential is not None:
                    p["isSequential"] = is_sequential

                p["updatedAt"] = now
                data["projects"][i] = p
                _save(data)
                return {"success": True, "project": p}

        return {"success": False, "error": f"Project {project_id} not found"}


class MindwtrListSectionsTask(Task):
    """List sections for a project."""

    @property
    def name(self) -> str:
        return "mindwtr_list_sections"

    @property
    def description(self) -> str:
        return (
            "List sections within a Mindwtr project. Sections group tasks "
            "into logical phases or categories within a project."
        )

    async def execute(self, project_id: str) -> dict[str, Any]:
        """List sections for a project.

        Args:
            project_id: The project ID to list sections for

        Returns:
            Dictionary with sections list
        """
        data = _load()
        sections = [
            s for s in data.get("sections", [])
            if s.get("projectId") == project_id and not s.get("deletedAt")
        ]
        sections.sort(key=lambda s: s.get("order", 0))
        return {"success": True, "count": len(sections), "sections": sections}


class MindwtrCreateSectionTask(Task):
    """Create a new section in a project."""

    @property
    def name(self) -> str:
        return "mindwtr_create_section"

    @property
    def description(self) -> str:
        return (
            "Create a new section within a Mindwtr project. Sections group tasks "
            "into logical phases or categories (e.g., 'Planning', 'In Progress', 'Review')."
        )

    async def execute(
        self,
        project_id: str,
        title: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a section.

        Args:
            project_id: The project ID to create the section in
            title: Section title
            description: Optional section description

        Returns:
            Dictionary with created section
        """
        if not title.strip():
            return {"success": False, "error": "Section title is required"}

        data = _load()

        # Verify project exists
        project = next(
            (p for p in data.get("projects", [])
             if p.get("id") == project_id and not p.get("deletedAt")),
            None,
        )
        if not project:
            return {"success": False, "error": f"Project {project_id} not found"}

        # Determine next order value
        existing = [
            s for s in data.get("sections", [])
            if s.get("projectId") == project_id and not s.get("deletedAt")
        ]
        max_order = max((s.get("order", 0) for s in existing), default=-1)

        now = _now_iso()
        section: dict[str, Any] = {
            "id": _generate_id(),
            "projectId": project_id,
            "title": title.strip(),
            "order": max_order + 1,
            "createdAt": now,
            "updatedAt": now,
        }
        if description:
            section["description"] = description

        data.setdefault("sections", []).append(section)
        _save(data)

        return {"success": True, "section": section}


class MindwtrUpdateSectionTask(Task):
    """Update an existing section."""

    @property
    def name(self) -> str:
        return "mindwtr_update_section"

    @property
    def description(self) -> str:
        return "Update a Mindwtr section's title, description, or order."

    async def execute(
        self,
        section_id: str,
        title: str = "",
        description: str = "",
        order: int | None = None,
    ) -> dict[str, Any]:
        """Update a section.

        Args:
            section_id: The section ID to update
            title: New title
            description: New description
            order: New sort order within the project

        Returns:
            Dictionary with updated section
        """
        data = _load()
        now = _now_iso()

        for i, s in enumerate(data.get("sections", [])):
            if s.get("id") == section_id and not s.get("deletedAt"):
                if title:
                    s["title"] = title.strip()
                if description:
                    s["description"] = description
                if order is not None:
                    s["order"] = order

                s["updatedAt"] = now
                data["sections"][i] = s
                _save(data)
                return {"success": True, "section": s}

        return {"success": False, "error": f"Section {section_id} not found"}


class MindwtrDeleteSectionTask(Task):
    """Soft-delete a section and clear sectionId on its tasks."""

    @property
    def name(self) -> str:
        return "mindwtr_delete_section"

    @property
    def description(self) -> str:
        return (
            "Delete a Mindwtr section. Tasks in the section remain in the project "
            "but are moved out of the section."
        )

    async def execute(self, section_id: str) -> dict[str, Any]:
        """Soft-delete a section.

        Args:
            section_id: The section ID to delete

        Returns:
            Dictionary with success status
        """
        data = _load()
        now = _now_iso()

        found = False
        for i, s in enumerate(data.get("sections", [])):
            if s.get("id") == section_id and not s.get("deletedAt"):
                s["deletedAt"] = now
                s["updatedAt"] = now
                data["sections"][i] = s
                found = True
                break

        if not found:
            return {"success": False, "error": f"Section {section_id} not found"}

        # Clear sectionId on tasks that belonged to this section
        for j, t in enumerate(data["tasks"]):
            if t.get("sectionId") == section_id:
                t.pop("sectionId", None)
                t["updatedAt"] = now
                data["tasks"][j] = t

        _save(data)
        return {"success": True, "message": f"Section {section_id} deleted"}


class MindwtrListTagsTask(Task):
    """List all tags and contexts used across tasks."""

    @property
    def name(self) -> str:
        return "mindwtr_list_tags"

    @property
    def description(self) -> str:
        return (
            "List all unique tags and contexts used across Mindwtr tasks. "
            "Shows each tag/context with the number of active tasks using it."
        )

    async def execute(self) -> dict[str, Any]:
        """List all tags and contexts.

        Returns:
            Dictionary with tags and contexts, each with usage counts
        """
        data = _load()
        active_tasks = [
            t for t in data["tasks"]
            if not t.get("deletedAt") and t.get("status") not in ("done", "archived")
        ]

        tag_counts: dict[str, int] = {}
        context_counts: dict[str, int] = {}

        for t in active_tasks:
            for tag in t.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            for ctx in t.get("contexts", []):
                context_counts[ctx] = context_counts.get(ctx, 0) + 1

        tags = [{"name": k, "count": v} for k, v in sorted(tag_counts.items())]
        contexts = [{"name": k, "count": v} for k, v in sorted(context_counts.items())]

        return {
            "success": True,
            "tags": tags,
            "contexts": contexts,
        }


class MindwtrSearchTask(Task):
    """Search across tasks and projects."""

    @property
    def name(self) -> str:
        return "mindwtr_search"

    @property
    def description(self) -> str:
        return (
            "Search across Mindwtr tasks and projects. Matches against titles, "
            "tags, contexts, and descriptions. Use @context or #tag syntax in the query."
        )

    async def execute(self, query: str) -> dict[str, Any]:
        """Search tasks and projects.

        Args:
            query: Search query (supports @context and #tag syntax)

        Returns:
            Dictionary with matching tasks and projects
        """
        if not query.strip():
            return {"success": False, "error": "Query is required"}

        data = _load()
        tasks = [
            t for t in data["tasks"]
            if not t.get("deletedAt") and _matches_query(t, query)
        ]
        projects = [
            p for p in data.get("projects", [])
            if not p.get("deletedAt") and _matches_project_query(p, query)
        ]

        return {
            "success": True,
            "tasks": tasks,
            "projects": projects,
        }


class MindwtrUpdateChecklistTask(Task):
    """Manage checklist items on a task."""

    @property
    def name(self) -> str:
        return "mindwtr_update_checklist"

    @property
    def description(self) -> str:
        return (
            "Manage checklist (subtask) items on a Mindwtr task. "
            "Actions: 'add' to add items, 'remove' to delete an item by ID, "
            "'toggle' to toggle completion of an item by ID, "
            "'set' to replace the entire checklist. "
            "Use 'items' for add/set (list of title strings), 'item_id' for remove/toggle."
        )

    async def execute(
        self,
        task_id: str,
        action: str,
        items: list[str] | None = None,
        item_id: str = "",
        item_title: str = "",
    ) -> dict[str, Any]:
        """Manage checklist items.

        Args:
            task_id: The task ID to manage checklist for
            action: Action to perform: add, remove, toggle, set
            items: List of title strings (for 'add' and 'set' actions)
            item_id: Checklist item ID (for 'remove' and 'toggle' actions)
            item_title: New title for an item (for 'toggle' action, optional rename)

        Returns:
            Dictionary with updated task checklist
        """
        valid_actions = {"add", "remove", "toggle", "set"}
        if action not in valid_actions:
            return {"success": False, "error": f"Invalid action '{action}'. Use: {', '.join(sorted(valid_actions))}"}

        data = _load()
        now = _now_iso()

        for i, t in enumerate(data["tasks"]):
            if t.get("id") == task_id:
                checklist: list[dict[str, Any]] = list(t.get("checklist") or [])

                if action == "add":
                    if not items:
                        return {"success": False, "error": "'items' is required for 'add' action"}
                    for title in items:
                        checklist.append({
                            "id": _generate_id(),
                            "title": title.strip(),
                            "isCompleted": False,
                        })

                elif action == "remove":
                    if not item_id:
                        return {"success": False, "error": "'item_id' is required for 'remove' action"}
                    original_len = len(checklist)
                    checklist = [c for c in checklist if c.get("id") != item_id]
                    if len(checklist) == original_len:
                        return {"success": False, "error": f"Checklist item {item_id} not found"}

                elif action == "toggle":
                    if not item_id:
                        return {"success": False, "error": "'item_id' is required for 'toggle' action"}
                    found = False
                    for c in checklist:
                        if c.get("id") == item_id:
                            c["isCompleted"] = not c.get("isCompleted", False)
                            if item_title:
                                c["title"] = item_title.strip()
                            found = True
                            break
                    if not found:
                        return {"success": False, "error": f"Checklist item {item_id} not found"}

                elif action == "set":
                    if items is None:
                        return {"success": False, "error": "'items' is required for 'set' action"}
                    checklist = [
                        {"id": _generate_id(), "title": title.strip(), "isCompleted": False}
                        for title in items
                    ]

                t["checklist"] = checklist
                t["updatedAt"] = now
                data["tasks"][i] = t
                _save(data)
                return {"success": True, "checklist": checklist}

        return {"success": False, "error": f"Task {task_id} not found"}


def register_mindwtr_tasks(registry: Any) -> None:
    """Register Mindwtr tasks with a registry.

    Args:
        registry: TaskRegistry to register tasks with.
    """
    registry.register(MindwtrListTasksTask())
    registry.register(MindwtrAddTaskTask())
    registry.register(MindwtrGetTaskTask())
    registry.register(MindwtrUpdateTaskTask())
    registry.register(MindwtrCompleteTaskTask())
    registry.register(MindwtrArchiveTaskTask())
    registry.register(MindwtrDeleteTaskTask())
    registry.register(MindwtrListProjectsTask())
    registry.register(MindwtrCreateProjectTask())
    registry.register(MindwtrUpdateProjectTask())
    registry.register(MindwtrListSectionsTask())
    registry.register(MindwtrCreateSectionTask())
    registry.register(MindwtrUpdateSectionTask())
    registry.register(MindwtrDeleteSectionTask())
    registry.register(MindwtrUpdateChecklistTask())
    registry.register(MindwtrListTagsTask())
    registry.register(MindwtrSearchTask())

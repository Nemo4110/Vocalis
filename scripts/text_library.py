"""
Built-in text library loader and query engine.

Provides curated practice texts organized by category and difficulty level.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict


@dataclass
class TextEntry:
    """A single practice text entry."""
    text_id: str
    title: str
    category: str
    difficulty: str  # beginner, intermediate, advanced
    author: str
    source: str
    word_count: int
    content: str
    tags: List[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.title} — {self.author}"

    @property
    def content_clean(self) -> str:
        """Return content with newlines collapsed to spaces for speech."""
        return " ".join(self.content.split())


class TextLibrary:
    """Manages the built-in collection of practice texts."""

    DEFAULT_PATH = Path(__file__).parent.parent / "assets" / "texts" / "library.yaml"

    def __init__(self, library_path: Optional[Path] = None):
        self.library_path = library_path or self.DEFAULT_PATH
        self._entries: List[TextEntry] = []
        self._by_id: Dict[str, TextEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load texts from YAML library file."""
        if not self.library_path.exists():
            return

        try:
            import yaml
            with open(self.library_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except ImportError:
            print("Warning: PyYAML not installed. Text library unavailable.")
            return
        except Exception as e:
            print(f"Warning: Could not load text library: {e}")
            return

        if not data:
            return

        for category, items in data.items():
            if not isinstance(items, list):
                continue
            for item in items:
                entry = TextEntry(
                    text_id=item.get("text_id", ""),
                    title=item.get("title", "Untitled"),
                    category=item.get("category", category),
                    difficulty=item.get("difficulty", "intermediate"),
                    author=item.get("author", "Unknown"),
                    source=item.get("source", ""),
                    word_count=item.get("word_count", 0),
                    content=item.get("content", "").strip(),
                    tags=item.get("tags", []),
                )
                self._entries.append(entry)
                self._by_id[entry.text_id] = entry

    def get_by_id(self, text_id: str) -> Optional[TextEntry]:
        """Get a text entry by its ID."""
        return self._by_id.get(text_id)

    def list_all(self) -> List[TextEntry]:
        """Return all entries."""
        return self._entries[:]

    def filter(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[TextEntry]:
        """Filter entries by category and/or difficulty."""
        result = self._entries[:]
        if category:
            result = [e for e in result if e.category.lower() == category.lower()]
        if difficulty:
            result = [e for e in result if e.difficulty.lower() == difficulty.lower()]
        return result

    def get_categories(self) -> List[str]:
        """Return list of unique categories."""
        return sorted(set(e.category for e in self._entries))

    def get_difficulties(self) -> List[str]:
        """Return list of unique difficulty levels."""
        return sorted(set(e.difficulty for e in self._entries))

    def random(self, category: Optional[str] = None, difficulty: Optional[str] = None) -> Optional[TextEntry]:
        """Get a random entry matching filters."""
        import random
        candidates = self.filter(category=category, difficulty=difficulty)
        if not candidates:
            return None
        return random.choice(candidates)

    def format_catalog(self) -> str:
        """Format the entire library as a markdown catalog."""
        lines = []
        lines.append("# Vocalis Practice Text Library")
        lines.append("")
        lines.append(f"**Total texts:** {len(self._entries)}")
        lines.append("")

        for category in self.get_categories():
            entries = self.filter(category=category)
            lines.append(f"## {category.title()}")
            lines.append("")
            lines.append("| ID | Title | Author | Difficulty | Words |")
            lines.append("|----|-------|--------|------------|-------|")
            for e in entries:
                diff_emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(e.difficulty, "⚪")
                lines.append(f"| `{e.text_id}` | {e.title} | {e.author} | {diff_emoji} {e.difficulty} | {e.word_count} |")
            lines.append("")

        return "\n".join(lines)

    def format_entry(self, text_id: str) -> Optional[str]:
        """Format a single entry as markdown."""
        entry = self.get_by_id(text_id)
        if not entry:
            return None

        lines = []
        lines.append(f"# {entry.title}")
        lines.append("")
        lines.append(f"**Author:** {entry.author}")
        lines.append(f"**Source:** {entry.source}")
        lines.append(f"**Category:** {entry.category}")
        lines.append(f"**Difficulty:** {entry.difficulty}")
        lines.append(f"**Words:** {entry.word_count}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(entry.content)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*Text ID: `{entry.text_id}`*")

        return "\n".join(lines)

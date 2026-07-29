"""Generate editable release-note suggestions from README changes."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
from pathlib import Path
import re


BUG_KEYWORDS = (
    "bug",
    "fix",
    "fixed",
    "fixes",
    "resolve",
    "resolved",
    "correct",
    "crash",
)
REMOVAL_KEYWORDS = (
    "remove",
    "removed",
    "delete",
    "deleted",
    "deprecated",
    "no longer",
)
MAX_SUGGESTIONS_PER_SECTION = 6


@dataclass(frozen=True)
class ReadmeComparison:
    new_functions: tuple[str, ...]
    bug_fixes: tuple[str, ...]
    removed_functions: tuple[str, ...]
    added_lines: int
    removed_lines: int
    old_found: bool
    new_found: bool

    def suggested_title(self, version):
        categories = []
        if self.new_functions:
            categories.append("New Functions")
        if self.bug_fixes:
            categories.append("Bug Fixes")
        if self.removed_functions:
            categories.append("Removed Functions")
        summary = " & ".join(categories) if categories else "Repository Update"
        return f"{version} — {summary}"


@dataclass(frozen=True)
class ReleasePlan:
    """Editable release details prepared before an upload."""

    tag: str
    title: str
    message: str


def _clean_readme_line(line):
    line = line.strip()
    if not line or line.startswith(("#", "```", "![", "[![")):
        return ""
    if set(line) <= {"-", "_", "*", " ", "="}:
        return ""
    line = re.sub(r"^[-*+]\s+", "", line)
    line = re.sub(r"^\d+[.)]\s+", "", line)
    return line[:180].strip()


def _deduplicate(values):
    unique = []
    seen = set()
    for value in values:
        normalized = value.casefold()
        if value and normalized not in seen:
            seen.add(normalized)
            unique.append(value)
    return tuple(unique[:MAX_SUGGESTIONS_PER_SECTION])


def _heading_category(line):
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    heading = stripped.lstrip("# ").casefold()
    if any(keyword in heading for keyword in REMOVAL_KEYWORDS):
        return "removed"
    if any(keyword in heading for keyword in BUG_KEYWORDS):
        return "bug"
    if any(
        keyword in heading
        for keyword in ("new function", "feature", "enhancement", "added")
    ):
        return "new"
    return ""


def _section_contexts(lines):
    current = None
    contexts = []
    for line in lines:
        heading_category = _heading_category(line)
        if heading_category is not None:
            current = heading_category or None
        contexts.append(current)
    return contexts


def _comparison_words(value):
    words = []
    ignored = {"a", "an", "and", "during", "for", "is", "no", "the", "to", "when", "with"}
    for word in re.findall(r"[a-z0-9]+", value.casefold()):
        if word.endswith("ies") and len(word) > 4:
            word = f"{word[:-3]}y"
        elif word.endswith("s") and len(word) > 4:
            word = word[:-1]
        if word not in ignored:
            words.append(word)
    return set(words)


def _is_reworded_line(old_value, new_value):
    if difflib.SequenceMatcher(
        None,
        old_value.casefold(),
        new_value.casefold(),
    ).ratio() >= 0.58:
        return True
    old_words = _comparison_words(old_value)
    new_words = _comparison_words(new_value)
    shared = old_words & new_words
    return len(shared) >= 2 and len(shared) / max(1, min(len(old_words), len(new_words))) >= 0.5


def compare_readmes(old_readme, new_readme, *, old_found=True, new_found=True):
    """Classify meaningful README line changes into release-note categories."""
    if not new_found:
        return ReadmeComparison((), (), (), 0, 0, old_found, new_found)

    old_lines = str(old_readme or "").splitlines()
    new_lines = str(new_readme or "").splitlines()
    additions = []
    removals = []
    old_contexts = _section_contexts(old_lines)
    contexts = _section_contexts(new_lines)
    matcher = difflib.SequenceMatcher(
        None,
        list(zip(old_lines, old_contexts)),
        list(zip(new_lines, contexts)),
    )
    for change, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if change in ("replace", "delete"):
            removals.extend(
                cleaned
                for cleaned in (_clean_readme_line(line) for line in old_lines[old_start:old_end])
                if cleaned
            )
        if change in ("replace", "insert"):
            additions.extend(
                (cleaned, contexts[index])
                for index in range(new_start, new_end)
                if (cleaned := _clean_readme_line(new_lines[index]))
            )

    new_functions = []
    bug_fixes = []
    # A rewritten line appears once as removed and once as added. Do not call the
    # old wording a removed function when the new wording already explains a fix
    # or explicit removal.
    unmatched_removals = [
        removal
        for removal in removals
        if not any(
            _is_reworded_line(removal, addition)
            for addition, _ in additions
        )
    ]
    removed_functions = list(unmatched_removals)
    for addition, section_category in additions:
        normalized = addition.casefold()
        if section_category == "bug":
            bug_fixes.append(addition)
        elif section_category == "removed":
            removed_functions.append(addition)
        elif any(keyword in normalized for keyword in REMOVAL_KEYWORDS):
            removed_functions.append(addition)
        elif any(
            keyword in normalized for keyword in BUG_KEYWORDS
        ):
            bug_fixes.append(addition)
        else:
            new_functions.append(addition)

    return ReadmeComparison(
        new_functions=_deduplicate(new_functions),
        bug_fixes=_deduplicate(bug_fixes),
        removed_functions=_deduplicate(removed_functions),
        added_lines=len(additions),
        removed_lines=len(removals),
        old_found=old_found,
        new_found=new_found,
    )


def read_local_readme(folder):
    """Read README.md case-insensitively from the selected upload folder."""
    folder = Path(folder)
    try:
        readme_path = next(
            path for path in folder.iterdir()
            if path.is_file() and path.name.casefold() == "readme.md"
        )
    except (OSError, StopIteration):
        return "", False
    try:
        return readme_path.read_text(encoding="utf-8", errors="ignore"), True
    except OSError:
        return "", False


def suggestion_text(values, fallback):
    return "; ".join(values) if values else fallback

"""Professional keyboard-driven menus with Q and R shortcuts."""

from enum import Enum

import inquirer
from blessed import Terminal
from inquirer import errors, themes
from inquirer.render.console import ConsoleRender
from inquirer.render.console._list import List as InquirerListRenderer


class MenuAction(str, Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    DELETE = "delete"
    SWITCH_ACCOUNT = "switch_account"
    RESET_AUTH = "reset_auth"
    CHECK_UPDATES = "check_updates"
    EXIT = "exit"
    REFRESH = "refresh"


class RepositoryAction(str, Enum):
    SEARCH = "__search_repositories__"
    CLEAR_SEARCH = "__clear_repository_search__"
    CREATE = "__create_repository__"
    BACK = "__back_from_repositories__"


class ShortcutListRenderer(InquirerListRenderer):
    """Add single-key shortcuts without changing arrow/Enter behavior."""

    def process_input(self, pressed):
        shortcut = pressed.lower() if isinstance(pressed, str) else pressed
        shortcuts = getattr(self.question, "shortcuts", {})
        if shortcut in shortcuts:
            raise errors.EndOfInput(shortcuts[shortcut])
        return super().process_input(pressed)


class ShortcutConsoleRender(ConsoleRender):
    def render_factory(self, question_type):
        if question_type == "list":
            return ShortcutListRenderer
        return super().render_factory(question_type)


def _cyber_theme():
    terminal = Terminal()
    theme = themes.Default()
    theme.Question.mark_color = terminal.cyan
    theme.Question.brackets_color = terminal.cyan
    theme.List.selection_color = terminal.bold_cyan
    theme.List.selection_cursor = "▶"
    theme.List.unselected_color = terminal.normal
    return theme


def select_main_action():
    """Select a main action using arrows/Enter, Q to quit, or R to refresh."""
    question = inquirer.List(
        "action",
        message="Choose an action  [Q quit • R refresh]",
        choices=[
            ("Upload Folder to GitHub", MenuAction.UPLOAD),
            ("Download Repository from GitHub", MenuAction.DOWNLOAD),
            ("Delete a Repository", MenuAction.DELETE),
            ("Switch GitHub Account", MenuAction.SWITCH_ACCOUNT),
            ("Check for Updates", MenuAction.CHECK_UPDATES),
            ("Reset Authentication", MenuAction.RESET_AUTH),
            ("Exit", MenuAction.EXIT),
        ],
        carousel=True,
    )
    question.shortcuts = {
        "q": MenuAction.EXIT,
        "r": MenuAction.REFRESH,
    }
    answers = inquirer.prompt(
        [question],
        render=ShortcutConsoleRender(theme=_cyber_theme()),
        raise_keyboard_interrupt=True,
    )
    return answers["action"] if answers else MenuAction.EXIT


def _prompt_repository_query(current_query=""):
    question = inquirer.Text(
        "query",
        message="Repository search (name contains)",
        default=current_query or None,
    )
    answers = inquirer.prompt(
        [question],
        render=ShortcutConsoleRender(theme=_cyber_theme()),
        raise_keyboard_interrupt=True,
    )
    return answers["query"].strip() if answers else ""


def select_repository(repositories, *, message="Select repository", allow_create=False):
    """Search and select a repository with keyboard shortcuts.

    `/` or `S` starts a case-insensitive search, `R` clears the current filter,
    `Q` returns to the previous screen, and arrows/Enter select normally.
    """
    all_repositories = sorted(set(repositories), key=str.casefold)
    query = ""

    while True:
        if query:
            visible_repositories = [
                name for name in all_repositories if query.casefold() in name.casefold()
            ]
        else:
            visible_repositories = all_repositories

        choices = [("Search repositories  [/ or S]", RepositoryAction.SEARCH)]
        if query:
            choices.append((f"Clear search: {query}  [R]", RepositoryAction.CLEAR_SEARCH))
        if allow_create:
            choices.append(("Create New Repository", RepositoryAction.CREATE))
        if visible_repositories:
            choices.extend((name, name) for name in visible_repositories)
        else:
            choices.append((f"No matches for '{query}' — search again", RepositoryAction.SEARCH))
        choices.append(("Back", RepositoryAction.BACK))

        filter_label = f" • filter: {query}" if query else ""
        question = inquirer.List(
            "repository",
            message=(
                f"{message} ({len(visible_repositories)}/{len(all_repositories)})"
                f"{filter_label}  [Q back]"
            ),
            choices=choices,
            carousel=True,
        )
        question.shortcuts = {
            "q": RepositoryAction.BACK,
            "s": RepositoryAction.SEARCH,
            "/": RepositoryAction.SEARCH,
            "r": RepositoryAction.CLEAR_SEARCH,
        }
        answers = inquirer.prompt(
            [question],
            render=ShortcutConsoleRender(theme=_cyber_theme()),
            raise_keyboard_interrupt=True,
        )
        selection = answers["repository"] if answers else RepositoryAction.BACK

        if selection == RepositoryAction.SEARCH:
            query = _prompt_repository_query(query)
            continue
        if selection == RepositoryAction.CLEAR_SEARCH:
            query = ""
            continue
        if selection == RepositoryAction.BACK:
            return None
        return selection

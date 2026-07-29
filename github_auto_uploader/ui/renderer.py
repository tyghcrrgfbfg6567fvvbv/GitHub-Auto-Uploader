"""Responsive cyberpunk terminal rendering for GitHub Auto Uploader."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import signal

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme


CYAN = "#00FFFF"
DARK_BACKGROUND = "#05070A"
MIN_LAYOUT_WIDTH = 40
MIN_BORDER_WIDTH = 20
DEFAULT_MAX_CONTENT_WIDTH = 96
DEFAULT_MARGIN = 2

APP_THEME = Theme({
    "brand": f"bold {CYAN}",
    "accent": CYAN,
    "muted": "#8A9AA9",
    "success": "bold #39FF88",
    "warning": "bold #FFD166",
    "danger": "bold #FF5577",
    "cyber.text": f"#E6F7FF on {DARK_BACKGROUND}",
})

console = Console(theme=APP_THEME)


@dataclass(frozen=True)
class BoxRow:
    """A label/value row whose wrapping is handled by ``render_box``."""

    label: str
    value: str
    label_style: str = "muted"
    value_style: str = "cyber.text"


@dataclass(frozen=True)
class BoxLayout:
    """Resolved dimensions for one render pass."""

    terminal_width: int
    terminal_height: int
    box_width: int
    content_width: int
    horizontal_padding: int
    show_border: bool
    resize_generation: int


_resize_generation = 0


def _handle_terminal_resize(_signum, _frame):
    """Mark SIGWINCH so the next render uses a fresh terminal measurement."""
    global _resize_generation
    _resize_generation += 1


if hasattr(signal, "SIGWINCH"):
    try:
        signal.signal(signal.SIGWINCH, _handle_terminal_resize)
    except ValueError:
        # Signal registration is only legal in Python's main thread.
        pass


def get_terminal_dimensions():
    """Query terminal dimensions now; the result is deliberately never cached."""
    size = shutil.get_terminal_size(fallback=(80, 24))
    return max(size.columns, 1), max(size.lines, 1)


def calculate_box_layout(width=None):
    """Calculate a non-overflowing layout from the current terminal size."""
    terminal_width, terminal_height = get_terminal_dimensions()
    requested_width = DEFAULT_MAX_CONTENT_WIDTH if width is None else max(int(width), 1)

    margin = DEFAULT_MARGIN if terminal_width >= MIN_LAYOUT_WIDTH else 0
    available_width = max(terminal_width - margin, 1)
    box_width = min(available_width, requested_width)

    show_border = box_width >= MIN_BORDER_WIDTH
    horizontal_padding = 1 if terminal_width >= MIN_LAYOUT_WIDTH else 0
    decoration_width = (2 if show_border else 0) + (horizontal_padding * 2)
    content_width = max(box_width - decoration_width, 1)

    return BoxLayout(
        terminal_width=terminal_width,
        terminal_height=terminal_height,
        box_width=box_width,
        content_width=content_width,
        horizontal_padding=horizontal_padding,
        show_border=show_border,
        resize_generation=_resize_generation,
    )


def _wrap_text(text, content_width):
    """Wrap styled Rich text for this render pass while preserving its styling."""
    source = text.copy() if isinstance(text, Text) else Text(str(text), style="cyber.text")
    requested_alignment = source.justify
    source.justify = None
    wrapped = []
    logical_lines = source.split("\n", allow_blank=True)

    for logical_line in logical_lines:
        if not logical_line.plain:
            wrapped.append(Text(""))
            continue
        current_lines = logical_line.wrap(
            console,
            content_width,
            overflow="fold",
            no_wrap=False,
        )
        if requested_alignment in ("center", "right"):
            for current_line in current_lines:
                current_line.align(requested_alignment, content_width)
        wrapped.extend(current_lines)

    return wrapped or [Text("")]


def _render_row(row, content_width):
    """Render a row with hanging indentation, stacking it on tiny screens."""
    label = row.label.upper()
    if content_width < 28:
        label_text = Text(label, style=row.label_style)
        value_text = Text(row.value, style=row.value_style)
        return [label_text, *_wrap_text(value_text, content_width)]

    label_width = min(max(len(label), 8), 16)
    value_width = max(content_width - label_width - 1, 1)
    wrapped_values = _wrap_text(Text(row.value, style=row.value_style), value_width)
    rendered = []
    for index, value_line in enumerate(wrapped_values):
        line = Text()
        line.append(label.ljust(label_width) if index == 0 else " " * label_width,
                    style=row.label_style)
        line.append(" ")
        line.append_text(value_line)
        rendered.append(line)
    return rendered


def _prepare_lines(lines, content_width):
    if isinstance(lines, (str, Text, BoxRow)):
        lines = [lines]

    rendered_lines = []
    for line in lines:
        if isinstance(line, BoxRow):
            rendered_lines.extend(_render_row(line, content_width))
        else:
            rendered_lines.extend(_wrap_text(line, content_width))
    return rendered_lines or [Text("")]


def render_box(title, lines, width=None, *, border_style=CYAN, title_style="brand"):
    """Render a responsive sharp-cornered box without exceeding the terminal.

    ``shutil.get_terminal_size()`` is called for every invocation. The optional
    ``width`` is only an upper bound; the terminal width minus its live margin
    always wins. Below 40 columns padding is removed, and below 20 columns the
    border is removed before any content is truncated.
    """
    layout = calculate_box_layout(width)
    rendered_lines = _prepare_lines(lines, layout.content_width)

    if not layout.show_border:
        if title:
            title_text = Text(str(title), style=title_style)
            for line in _wrap_text(title_text, layout.content_width):
                console.print(line, width=layout.box_width, overflow="fold")
        for line in rendered_lines:
            console.print(line, width=layout.box_width, overflow="fold")
        return layout

    safe_title = escape(str(title)) if title else None
    panel = Panel(
        Group(*rendered_lines),
        title=f"[{title_style}]{safe_title}[/{title_style}]" if safe_title else None,
        title_align="left",
        width=layout.box_width,
        box=box.SQUARE,
        border_style=border_style,
        style=f"on {DARK_BACKGROUND}",
        padding=(0, layout.horizontal_padding),
        expand=False,
    )
    console.print(Align.center(panel), width=layout.terminal_width)
    return layout

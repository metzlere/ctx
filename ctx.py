#!/usr/bin/env python3
"""
ctx.py - Lightweight Context Engineering Tool

A single-file tool for building structured LLM prompts with codebase context.
Designed for chat-based LLM workflows where you need to quickly assemble
project context for code generation tasks.

Usage:
    python ctx.py              # Run interactive mode

Output:
    Creates 'llm_context.txt' in current directory, ready to copy-paste.
"""

import curses
import fnmatch
import json
import sys
import textwrap
from collections import namedtuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Container,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

# =============================================================================
# ANSI Styling (Zero-dependency terminal colors)
# =============================================================================


class Style:
    """ANSI escape codes for terminal styling. Yellow accents with white text."""

    # Reset
    RESET = "\033[0m"

    # Text styles
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Colors (foreground)
    YELLOW = "\033[33m"  # Warm yellow for highlights
    WHITE = "\033[97m"  # Bright white for main content
    GREEN = "\033[32m"  # Green for success
    RED = "\033[91m"  # Red for errors
    CYAN = "\033[36m"  # Cyan for info

    # Box drawing characters (rounded)
    BOX_TL = "╭"  # Top-left
    BOX_TR = "╮"  # Top-right
    BOX_BL = "╰"  # Bottom-left
    BOX_BR = "╯"  # Bottom-right
    BOX_H = "─"  # Horizontal
    BOX_V = "│"  # Vertical

    # Status symbols
    CHECK = "✓"
    BULLET = "•"
    ARROW = "→"
    INFO = "ℹ"

    @classmethod
    def yellow(cls, text: str) -> str:
        """Apply yellow highlight to text."""
        return f"{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def bold(cls, text: str) -> str:
        """Apply bold styling to text."""
        return f"{cls.BOLD}{text}{cls.RESET}"

    @classmethod
    def success(cls, text: str) -> str:
        """Apply green success styling to text."""
        return f"{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def error(cls, text: str) -> str:
        """Apply red error styling to text."""
        return f"{cls.RED}{text}{cls.RESET}"

    @classmethod
    def info(cls, text: str) -> str:
        """Apply cyan info styling to text."""
        return f"{cls.CYAN}{text}{cls.RESET}"

    @classmethod
    def white(cls, text: str) -> str:
        """Apply white styling to text."""
        return f"{cls.WHITE}{text}{cls.RESET}"

    @classmethod
    def dim(cls, text: str) -> str:
        """Apply dim styling (for hints, secondary info)."""
        return f"{cls.DIM}{text}{cls.RESET}"


def styled_header(title: str, width: int = 60) -> str:
    """
    Create a boxed header with rounded corners.

    Args:
        title: Header text
        width: Total width of the box

    Returns:
        Formatted header string
    """
    inner_width = width - 2
    top = f"{Style.YELLOW}{Style.BOX_TL}{Style.BOX_H * inner_width}{Style.BOX_TR}{Style.RESET}"
    mid = f"{Style.YELLOW}{Style.BOX_V}{Style.RESET} {Style.BOLD}{Style.WHITE}{title}{Style.RESET}{' ' * (inner_width - len(title) - 1)}{Style.YELLOW}{Style.BOX_V}{Style.RESET}"
    bot = f"{Style.YELLOW}{Style.BOX_BL}{Style.BOX_H * inner_width}{Style.BOX_BR}{Style.RESET}"

    return f"{top}\n{mid}\n{bot}"


def styled_box(title: str, width: int = 50) -> str:
    """
    Create a smaller boxed section header.

    Args:
        title: Section title
        width: Total width of the box

    Returns:
        Formatted box string
    """
    inner_width = width - 2
    top = f"{Style.YELLOW}{Style.BOX_TL}{Style.BOX_H * inner_width}{Style.BOX_TR}{Style.RESET}"
    mid = f"{Style.YELLOW}{Style.BOX_V}{Style.RESET} {Style.WHITE}{title}{Style.RESET}{' ' * (inner_width - len(title) - 1)}{Style.YELLOW}{Style.BOX_V}{Style.RESET}"
    bot = f"{Style.YELLOW}{Style.BOX_BL}{Style.BOX_H * inner_width}{Style.BOX_BR}{Style.RESET}"

    return f"{top}\n{mid}\n{bot}"


def styled_step(step: int, total: int, title: str, width: int = 50) -> str:
    """
    Create a step indicator as a boxed header.

    Args:
        step: Current step number
        total: Total number of steps
        title: Step title
        width: Total width of the box

    Returns:
        Formatted step box string
    """
    step_text = f"Step {step}/{total}: {title}"
    return f"\n{styled_box(step_text, width)}\n"


def styled_prompt(label: str, default: str = "", hint: str = "") -> str:
    """
    Create a styled input prompt.

    Args:
        label: Prompt label
        default: Default value to show
        hint: Optional hint text

    Returns:
        Formatted prompt string
    """
    parts = [f"  {Style.YELLOW}{Style.ARROW}{Style.RESET} {Style.WHITE}{label}{Style.RESET}"]
    if default:
        parts.append(f" {Style.DIM}[{default}]{Style.RESET}")
    if hint:
        parts.append(f" {Style.dim(hint)}")
    parts.append(f" ")
    return "".join(parts)


def styled_summary_box(items: list[tuple[str, str]], width: int = 50) -> str:
    """
    Create a summary box with key-value pairs.

    Args:
        items: List of (label, value) tuples
        width: Total width of the box

    Returns:
        Formatted summary box string
    """
    inner_width = width - 4  # Account for box borders and padding

    lines = []
    # Top border
    lines.append(f"{Style.YELLOW}{Style.BOX_TL}{Style.BOX_H * (width - 2)}{Style.BOX_TR}{Style.RESET}")

    for label, value in items:
        # Calculate padding to right-align values
        label_part = f"{Style.WHITE}{label}{Style.RESET}"
        value_part = f"{Style.YELLOW}{value}{Style.RESET}"
        # Raw lengths for spacing calculation
        spacing = inner_width - len(label) - len(value)
        line_content = f" {label_part}{' ' * spacing}{value_part} "
        lines.append(f"{Style.YELLOW}{Style.BOX_V}{Style.RESET}{line_content}{Style.YELLOW}{Style.BOX_V}{Style.RESET}")

    # Bottom border
    lines.append(f"{Style.YELLOW}{Style.BOX_BL}{Style.BOX_H * (width - 2)}{Style.BOX_BR}{Style.RESET}")

    return "\n".join(lines)


# =============================================================================
# Configuration
# =============================================================================

OUTPUT_FILE = "llm_context.txt"
CONSTITUTION_PATHS = ["CONSTITUTION.md", ".ctx/constitution.md", "constitution.md"]
PRESETS_PATH = ".ctx/presets.json"
MAX_TREE_DEPTH = 6

# Patterns to always ignore (in addition to .gitignore)
DEFAULT_IGNORE_PATTERNS = {
    # Python
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".Python",
    "venv",
    ".venv",
    "env",
    ".env",
    "*.egg-info",
    ".eggs",
    "*.egg",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    ".tox",
    ".nox",
    # JavaScript/Node
    "node_modules",
    "bower_components",
    ".npm",
    ".yarn",
    # IDE/Editor
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    ".project",
    ".settings",
    # OS
    ".DS_Store",
    "Thumbs.db",
    # Version control
    ".git",
    ".svn",
    ".hg",
    # Build outputs
    "build",
    "dist",
    "*.so",
    "*.dll",
    # This tool's output
    OUTPUT_FILE,
    "llm_context.txt",
}


# =============================================================================
# Embedded Pick Library (MIT License)
# Source: https://github.com/wong2/pick
# Embedded to keep ctx.py as a single file with no external dependencies.
# =============================================================================


@dataclass
class PickOption:
    """Option for the picker with label, value, and optional description."""

    label: str
    value: Any = None
    description: Optional[str] = None
    enabled: bool = True


PICK_KEYS_ENTER = (curses.KEY_ENTER, ord("\n"), ord("\r"))
PICK_KEYS_UP = (curses.KEY_UP, ord("k"))
PICK_KEYS_DOWN = (curses.KEY_DOWN, ord("j"))
PICK_KEYS_SELECT = (curses.KEY_RIGHT, ord(" "))

PICK_SYMBOL_FILLED = "●"
PICK_SYMBOL_EMPTY = "○"

PICK_OPTION_T = TypeVar("PICK_OPTION_T", str, PickOption)
PICK_RETURN_T = Tuple[PICK_OPTION_T, int]

PickPosition = namedtuple("PickPosition", ["y", "x"])


@dataclass
class Picker(Generic[PICK_OPTION_T]):
    """Interactive terminal picker with arrow-key navigation and multi-select."""

    options: Sequence[PICK_OPTION_T]
    title: Optional[str] = None
    indicator: str = "→"
    default_index: int = 0
    multiselect: bool = False
    min_selection_count: int = 0
    default_selected: Optional[List[int]] = None
    selected_indexes: List[int] = field(init=False, default_factory=list)
    index: int = field(init=False, default=0)
    screen: Optional[Any] = None  # curses window
    position: PickPosition = PickPosition(0, 0)
    clear_screen: bool = True
    quit_keys: Optional[Union[Container[int], Iterable[int]]] = None

    def __post_init__(self) -> None:
        if len(self.options) == 0:
            raise ValueError("options should not be an empty list")

        if self.default_index >= len(self.options):
            raise ValueError("default_index should be less than the length of options")

        if self.multiselect and self.min_selection_count > len(self.options):
            raise ValueError(
                "min_selection_count is bigger than the available options"
            )

        if all(
            isinstance(option, PickOption) and not option.enabled
            for option in self.options
        ):
            raise ValueError("all given options are disabled")

        self.index = self.default_index
        option = self.options[self.index]
        if isinstance(option, PickOption) and not option.enabled:
            self.move_down()

        # Initialize pre-selected indices for multiselect
        if self.default_selected and self.multiselect:
            self.selected_indexes = [
                i for i in self.default_selected if 0 <= i < len(self.options)
            ]

    def move_up(self) -> None:
        while True:
            self.index -= 1
            if self.index < 0:
                self.index = len(self.options) - 1
            option = self.options[self.index]
            if not isinstance(option, PickOption) or option.enabled:
                break

    def move_down(self) -> None:
        while True:
            self.index += 1
            if self.index >= len(self.options):
                self.index = 0
            option = self.options[self.index]
            if not isinstance(option, PickOption) or option.enabled:
                break

    def mark_index(self) -> None:
        if self.multiselect:
            if self.index in self.selected_indexes:
                self.selected_indexes.remove(self.index)
            else:
                self.selected_indexes.append(self.index)

    def get_selected(self) -> Union[List[PICK_RETURN_T], PICK_RETURN_T]:
        if self.multiselect:
            return_tuples = []
            for selected in self.selected_indexes:
                return_tuples.append((self.options[selected], selected))
            return return_tuples
        else:
            return self.options[self.index], self.index

    def get_title_lines(self, *, max_width: int = 80) -> List[str]:
        if self.title:
            return textwrap.fill(
                self.title, max_width - 2, drop_whitespace=False
            ).split("\n") + [""]
        return []

    def get_option_lines(self) -> List[str]:
        lines: List[str] = []
        for index, option in enumerate(self.options):
            if index == self.index:
                prefix = self.indicator
            else:
                prefix = len(self.indicator) * " "

            if self.multiselect:
                symbol = (
                    PICK_SYMBOL_FILLED
                    if index in self.selected_indexes
                    else PICK_SYMBOL_EMPTY
                )
                prefix = f"{prefix} {symbol}"

            option_as_str = option.label if isinstance(option, PickOption) else option
            lines.append(f"{prefix} {option_as_str}")

        return lines

    def get_lines(self, *, max_width: int = 80) -> Tuple[List[str], int]:
        title_lines = self.get_title_lines(max_width=max_width)
        option_lines = self.get_option_lines()
        lines = title_lines + option_lines
        current_line = self.index + len(title_lines) + 1
        return lines, current_line

    def draw(self, screen: Any) -> None:  # curses window
        if self.clear_screen:
            screen.clear()

        y, x = self.position
        max_y, max_x = screen.getmaxyx()
        max_rows = max_y - y

        # Get color attributes
        try:
            color_yellow = curses.color_pair(1) | curses.A_BOLD
            color_white = curses.color_pair(2)
            color_green = curses.color_pair(3)
        except Exception:
            color_yellow = curses.A_BOLD
            color_white = curses.A_NORMAL
            color_green = curses.A_NORMAL

        # Draw title lines
        title_lines = self.get_title_lines(max_width=max_x)
        for line in title_lines:
            try:
                screen.addnstr(y, x, line, max_x - 2, color_white)
            except curses.error:
                pass
            y += 1

        # Calculate scroll position
        visible_rows = max_rows - len(title_lines)
        scroll_top = 0
        if self.index >= visible_rows:
            scroll_top = self.index - visible_rows + 1

        # Draw options with colors
        for i in range(scroll_top, min(scroll_top + visible_rows, len(self.options))):
            option = self.options[i]
            is_current = i == self.index
            is_selected = i in self.selected_indexes

            # Build the line parts
            if is_current:
                indicator = self.indicator
            else:
                indicator = " " * len(self.indicator)

            if self.multiselect:
                symbol = PICK_SYMBOL_FILLED if is_selected else PICK_SYMBOL_EMPTY
                prefix = f"{indicator} {symbol} "
            else:
                prefix = f"{indicator} "

            option_str = option.label if isinstance(option, PickOption) else option
            line = f"{prefix}{option_str}"

            # Choose color based on state
            if is_current:
                attr = color_yellow
            elif is_selected:
                attr = color_green
            else:
                attr = color_white

            try:
                screen.addnstr(y, x, line, max_x - 2, attr)
            except curses.error:
                pass
            y += 1

        # Draw description if present
        option = self.options[self.index]
        if isinstance(option, PickOption) and option.description is not None:
            description_lines = textwrap.fill(
                option.description, max_x // 2 - 2
            ).split("\n")
            for i, line in enumerate(description_lines):
                try:
                    screen.addnstr(i + len(title_lines), max_x // 2, line, max_x - 2, color_white)
                except curses.error:
                    pass

        screen.refresh()

    def run_loop(
        self, screen: Any, position: PickPosition  # curses window
    ) -> Union[List[PICK_RETURN_T], PICK_RETURN_T]:
        while True:
            self.draw(screen)
            c = screen.getch()
            if self.quit_keys is not None and c in self.quit_keys:
                if self.multiselect:
                    return []
                else:
                    return None, -1
            elif c in PICK_KEYS_UP:
                self.move_up()
            elif c in PICK_KEYS_DOWN:
                self.move_down()
            elif c in PICK_KEYS_ENTER:
                if (
                    self.multiselect
                    and len(self.selected_indexes) < self.min_selection_count
                ):
                    continue
                return self.get_selected()
            elif c in PICK_KEYS_SELECT and self.multiselect:
                self.mark_index()

    def config_curses(self) -> None:
        try:
            curses.use_default_colors()
            curses.curs_set(0)
            # Initialize color pairs
            if curses.has_colors():
                curses.start_color()
                curses.init_pair(1, curses.COLOR_YELLOW, -1)  # Yellow for highlights
                curses.init_pair(2, curses.COLOR_WHITE, -1)   # White for text
                curses.init_pair(3, curses.COLOR_GREEN, -1)   # Green for selected
        except Exception:
            curses.initscr()

    def _start(self, screen: Any):  # curses window
        self.config_curses()
        return self.run_loop(screen, self.position)

    def start(self):
        if self.screen:
            last_cur = curses.curs_set(0)
            ret = self.run_loop(self.screen, self.position)
            if last_cur:
                curses.curs_set(last_cur)
            return ret
        return curses.wrapper(self._start)


def pick(
    options: Sequence[PICK_OPTION_T],
    title: Optional[str] = None,
    indicator: str = ">",
    default_index: int = 0,
    multiselect: bool = False,
    min_selection_count: int = 0,
    default_selected: Optional[List[int]] = None,
    screen: Optional[Any] = None,  # curses window
    position: PickPosition = PickPosition(0, 0),
    clear_screen: bool = True,
    quit_keys: Optional[Union[Container[int], Iterable[int]]] = None,
):
    """
    Simple terminal picker with arrow-key navigation.

    Args:
        options: List of options to pick from (strings or PickOption objects).
        title: Optional title displayed above options.
        indicator: Character(s) to indicate current selection.
        default_index: Index of initially selected option.
        multiselect: Allow selecting multiple options.
        min_selection_count: Minimum selections required (multiselect only).
        default_selected: Indices to pre-select (multiselect only).
        screen: Existing curses screen (optional).
        position: Starting position (y, x).
        clear_screen: Clear screen before drawing.
        quit_keys: Key codes that quit the picker.

    Returns:
        Single selection: (option, index) tuple.
        Multiselect: List of (option, index) tuples.
    """
    picker: Picker = Picker(
        options=options,
        title=title,
        indicator=indicator,
        default_index=default_index,
        multiselect=multiselect,
        min_selection_count=min_selection_count,
        default_selected=default_selected,
        screen=screen,
        position=position,
        clear_screen=clear_screen,
        quit_keys=quit_keys,
    )
    return picker.start()


# =============================================================================
# Ignore Pattern Handling
# =============================================================================


def load_gitignore(root: Path) -> set[str]:
    """
    Load patterns from .gitignore file if it exists.

    Args:
        root (Path): Project root directory.

    Returns:
        set[str]: Set of gitignore patterns.
    """
    gitignore_path = root / ".gitignore"
    patterns = set()

    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.add(line)

    return patterns


def should_ignore(path: Path, root: Path, ignore_patterns: set[str]) -> bool:
    """
    Check if a path should be ignored based on patterns.

    Args:
        path (Path): Path to check.
        root (Path): Project root for relative path calculation.
        ignore_patterns (set[str]): Set of ignore patterns.

    Returns:
        bool: True if path should be ignored.
    """
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        return False

    name = path.name
    rel_str = str(rel_path)

    for pattern in ignore_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(rel_str, pattern):
            return True
        if pattern.endswith("/") and fnmatch.fnmatch(name, pattern[:-1]):
            return True
        for parent in rel_path.parents:
            if fnmatch.fnmatch(parent.name, pattern.rstrip("/")):
                return True

    return False


# =============================================================================
# Directory Tree Generation
# =============================================================================


def generate_tree(
    root: Path, ignore_patterns: set[str], max_depth: int = MAX_TREE_DEPTH
) -> str:
    """
    Generate a directory tree string representation.

    Args:
        root (Path): Root directory to start from.
        ignore_patterns (set[str]): Patterns to ignore.
        max_depth (int): Maximum depth to traverse.

    Returns:
        str: Formatted tree string.
    """
    lines = [f"{root.name}/"]

    def walk(directory: Path, prefix: str, depth: int):
        if depth > max_depth:
            return

        try:
            entries = sorted(
                directory.iterdir(), key=lambda e: (e.is_file(), e.name.lower())
            )
        except PermissionError:
            return

        entries = [e for e in entries if not should_ignore(e, root, ignore_patterns)]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "

            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                extension = "    " if is_last else "│   "
                walk(entry, prefix + extension, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry.name}")

    walk(root, "", 1)
    return "\n".join(lines)


# =============================================================================
# File Discovery and Selection
# =============================================================================


def discover_files(root: Path, ignore_patterns: set[str]) -> list[Path]:
    """
    Discover all non-ignored files in the project.

    Args:
        root (Path): Project root directory.
        ignore_patterns (set[str]): Patterns to ignore.

    Returns:
        list[Path]: Sorted list of file paths.
    """
    files = []

    for path in root.rglob("*"):
        if path.is_file() and not should_ignore(path, root, ignore_patterns):
            files.append(path)

    return sorted(files, key=lambda p: str(p.relative_to(root)).lower())


def format_size(size_bytes: int) -> str:
    """
    Format file size in human-readable form.

    Args:
        size_bytes (int): Size in bytes.

    Returns:
        str: Formatted size string.
    """
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB"]:
        if size < 1024:
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def interactive_file_selection(
    files: list[Path],
    root: Path,
    preselected_indices: Optional[list[int]] = None,
) -> list[Path]:
    """
    Interactive file selection using arrow keys and space to select.

    Parameters
    ----------
    files : list[Path]
        Available files.
    root : Path
        Project root.
    preselected_indices : list[int], optional
        Indices of files to pre-select (from a preset).

    Returns
    -------
    list[Path]
        List of selected files.
    """
    # Build option labels with file sizes
    options = []
    for file_path in files:
        rel_path = file_path.relative_to(root)
        try:
            size = file_path.stat().st_size
            size_str = format_size(size)
        except OSError:
            size_str = "?"
        options.append(f"{rel_path}  ({size_str})")

    preselect_info = ""
    if preselected_indices:
        preselect_info = f"  ({len(preselected_indices)} pre-selected)"

    title = f"Select files to include:{preselect_info}"

    selected = pick(
        options,
        title=title,
        multiselect=True,
        min_selection_count=0,
        default_selected=preselected_indices,
    )

    # Extract selected file paths (multiselect=True returns list of tuples)
    selected_files = []
    if isinstance(selected, list):
        for _, index in selected:
            selected_files.append(files[index])

    return sorted(selected_files, key=lambda p: str(p.relative_to(root)).lower())


# =============================================================================
# File Content Reading
# =============================================================================


def read_file_content(path: Path) -> tuple[str, bool]:
    """
    Read file content, handling encoding issues.

    Args:
        path (Path): Path to file.

    Returns:
        tuple[str, bool]: Tuple of (content, is_binary).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), False
    except UnicodeDecodeError:
        return f"[Binary file - {format_size(path.stat().st_size)}]", True
    except Exception as e:
        return f"[Error reading file: {e}]", True


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (approximately 4 chars per token for code).

    Args:
        text (str): Text to estimate.

    Returns:
        int: Estimated token count.
    """
    return len(text) // 4


# =============================================================================
# Preset Management
# =============================================================================


def load_presets(root: Path) -> dict[str, list[str]]:
    """
    Load file selection presets from .ctx/presets.json.

    Parameters
    ----------
    root : Path
        Project root directory.

    Returns
    -------
    dict[str, list[str]]
        Dictionary mapping preset names to lists of relative file paths.
    """
    presets_path = root / PRESETS_PATH
    if not presets_path.exists():
        return {}

    try:
        with open(presets_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_preset(root: Path, name: str, files: list[Path]) -> bool:
    """
    Save a file selection as a named preset.

    Parameters
    ----------
    root : Path
        Project root directory.
    name : str
        Name for the preset.
    files : list[Path]
        List of file paths to save.

    Returns
    -------
    bool
        True if save succeeded.
    """
    presets_path = root / PRESETS_PATH

    # Ensure .ctx directory exists
    presets_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing presets
    presets = load_presets(root)

    # Add/update preset with relative paths
    presets[name] = [str(f.relative_to(root)) for f in files]

    try:
        with open(presets_path, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2)
        return True
    except OSError:
        return False


def apply_preset(
    preset_files: list[str], available_files: list[Path], root: Path
) -> tuple[list[int], list[str]]:
    """
    Match preset files against available files and return indices to pre-select.

    Parameters
    ----------
    preset_files : list[str]
        Relative file paths from the preset.
    available_files : list[Path]
        Currently available files in the project.
    root : Path
        Project root directory.

    Returns
    -------
    tuple[list[int], list[str]]
        Tuple of (indices to pre-select, missing files not found).
    """
    # Build lookup of relative path -> index
    path_to_index = {
        str(f.relative_to(root)): i for i, f in enumerate(available_files)
    }

    indices = []
    missing = []

    for rel_path in preset_files:
        if rel_path in path_to_index:
            indices.append(path_to_index[rel_path])
        else:
            missing.append(rel_path)

    return indices, missing


def prompt_preset_selection(
    root: Path, presets: dict[str, list[str]]
) -> tuple[Optional[str], Optional[list[str]]]:
    """
    Show menu to select a preset or choose custom selection.

    Parameters
    ----------
    root : Path
        Project root directory.
    presets : dict[str, list[str]]
        Available presets.

    Returns
    -------
    tuple[Optional[str], Optional[list[str]]]
        Tuple of (preset_name, preset_files) or (None, None) for custom selection.
    """
    options = [PickOption(label="Custom selection", value=None)]

    for name, files in presets.items():
        options.append(
            PickOption(
                label=f"{name} ({len(files)} files)",
                value=name,
                description=", ".join(files[:5]) + ("..." if len(files) > 5 else ""),
            )
        )

    title = "Load a preset or make a custom selection:"
    selected, _ = pick(options, title=title)

    if selected.value is None:
        return None, None

    return selected.value, presets[selected.value]


def prompt_save_preset(root: Path, files: list[Path]) -> None:
    """
    Prompt user to optionally save current selection as a preset.

    Parameters
    ----------
    root : Path
        Project root directory.
    files : list[Path]
        Currently selected files.
    """
    if not files:
        return

    print()
    response = input(styled_prompt("Save as preset?", "n")).strip().lower()

    if response not in ("y", "yes"):
        return

    name = input(styled_prompt("Preset name")).strip()
    if not name:
        print(f"  {Style.dim('No name entered, skipping.')}")
        return

    if save_preset(root, name, files):
        print(f"  {Style.success(Style.CHECK)} Saved preset: {Style.yellow(name)}")
    else:
        print(f"  {Style.error('Failed to save preset.')}")


# =============================================================================
# Constitution Handling
# =============================================================================


def find_constitution(root: Path) -> Optional[Path]:
    """
    Find constitution file in standard locations.

    Args:
        root (Path): Project root.

    Returns:
        Optional[Path]: Path to constitution file if found.
    """
    for rel_path in CONSTITUTION_PATHS:
        full_path = root / rel_path
        if full_path.exists():
            return full_path
    return None


def load_constitution(root: Path) -> Optional[str]:
    """
    Load constitution file if it exists.

    Args:
        root (Path): Project root.

    Returns:
        Optional[str]: Constitution content or None.
    """
    print(styled_step(3, 5, "Constitution"))
    const_path = find_constitution(root)

    if const_path:
        print(f"  {Style.success(Style.CHECK)} Found: {Style.yellow(str(const_path.relative_to(root)))}")
        include = input(styled_prompt("Include constitution?", "y")).strip().lower()
        if include not in ("n", "no"):
            content, _ = read_file_content(const_path)
            return content
    else:
        print(f"  {Style.dim(f'No constitution found ({', '.join(CONSTITUTION_PATHS)})')}")

    return None


# =============================================================================
# Mode Selection
# =============================================================================


def prompt_for_mode() -> str:
    """
    Prompt user to select quick or full mode.

    Returns:
        str: 'quick' or 'full'
    """
    print(styled_step(1, 5, "Select Mode"))
    print(f"  {Style.yellow('[q]')} {Style.white('Quick')} {Style.YELLOW}─{Style.RESET} Simple prompt, just task + context")
    print(f"  {Style.yellow('[f]')} {Style.white('Full')}  {Style.YELLOW}─{Style.RESET} 3-phase workflow (clarify → spec → implement)")
    print(f"  {Style.yellow('[l]')} {Style.white('Lite')}  {Style.YELLOW}─{Style.RESET} Flat, explicit instructions for weaker models")
    print()

    while True:
        choice = input(styled_prompt("Mode", "q")).strip().lower()
        if choice in ("", "q", "quick"):
            return "quick"
        if choice in ("f", "full"):
            return "full"
        if choice in ("l", "lite"):
            return "lite"
        print(Style.error("Invalid choice. Enter 'q', 'f', or 'l'."))


# =============================================================================
# Task Specification
# =============================================================================


def prompt_for_task() -> str:
    """
    Get task specification from user.

    Returns:
        str: Task specification text.
    """
    print(styled_step(2, 5, "Describe Your Task"))
    print(f"  {Style.white('What do you want to build or change?')}")
    print(f"  {Style.dim('Enter multiple lines. Type')} {Style.yellow('END')} {Style.dim('when done.')}")
    print()

    lines = []
    while True:
        try:
            line = input(f"  {Style.YELLOW}{Style.BOX_V}{Style.RESET} ")
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except (EOFError, KeyboardInterrupt):
            break

    return "\n".join(lines).strip()


# =============================================================================
# Output Generation
# =============================================================================


def get_quick_instructions() -> str:
    """
    Return simple instructions for quick mode.

    Returns:
        str: Quick mode instructions.
    """
    return '''Implement the task described below using the provided codebase context.

Guidelines:
- Follow the project's existing code style and patterns
- Follow the project constitution if provided
- Include appropriate error handling and type hints
- Keep changes focused and minimal

Output format:
- Show complete file contents for any modified or new files
- Clearly label each file as (modified) or (new)
- List any deleted files with reason
- Note any manual steps needed after implementation'''


def get_workflow_instructions() -> str:
    """
    Return the 3-phase workflow instructions for the LLM.

    Returns:
        str: Workflow instructions.
    """
    return '''Follow this 3-phase workflow exactly. Wait for user approval between phases.

## PHASE 1: CLARIFICATION

Review the task and codebase context. Ask clarifying questions about:
- Ambiguous requirements
- Edge cases or error handling expectations
- Integration points with existing code
- Any assumptions you need to verify

If everything is clear, summarize your understanding and confirm you're ready 
for Phase 2. **Wait for user confirmation before proceeding.**

## PHASE 2: SPECIFICATION & IMPLEMENTATION PLAN

Produce these two artifacts:

### Specification (spec.md)

```markdown
# [Feature/Change Name]

## Overview
[1-2 sentence summary]

## Requirements
- [Requirement 1]
- [Requirement 2]

## Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Out of Scope
- [What this does NOT include]
```

### Implementation Plan

```markdown
## Implementation Plan

### Files to Modify
- `path/to/file.py` - [what changes]

### New Files  
- `path/to/new_file.py` - [purpose]

### Dependencies (if any)
- [New packages needed]

### Approach
[Brief description of implementation approach]
```

Present both and **wait for user approval** ("approved", "proceed", "go ahead", etc.)
Iterate if the user requests changes.

## PHASE 3: IMPLEMENTATION

Once approved, implement the solution with organized output:

### Modified Files
For each existing file, show the complete updated file:

**`path/to/file.py`** (modified)
```python
[complete file contents]
```

### New Files
**`path/to/new_file.py`** (new)
```python  
[complete file contents]
```

### Deleted Files (if any)
- `path/to/deleted.py` - [reason]

### Summary
- Modified: [count] | Created: [count] | Deleted: [count]

### Next Steps (if any)
- [Manual steps, migrations, config changes needed]

---
**Guidelines**: Follow project constitution if provided. Match existing code
style and patterns. Include error handling and type hints. Keep changes focused.'''


def get_lite_instructions() -> str:
    """
    Return flat, explicit instructions for lite mode.

    Designed for weaker models (e.g. Gemini 2.5) that struggle with nested
    markdown, multi-phase workflows, and "wait for approval" protocols.
    Rules are short imperatives; output format is shown concretely.

    Returns
    -------
    str
        Lite mode instructions.
    """
    return '''1. Do exactly what <task> says. Nothing more.
2. Do not ask questions. If something is unclear, state your assumption in one line and continue.
3. Do not plan, outline, or explain before coding. Write the code.
4. For every file you change or create, output the COMPLETE new file contents. No partial snippets, no diffs, no "..." placeholders.
5. Use the exact file paths shown in <codebase> and <directory_tree>.
6. Match the existing code style in <codebase>.
7. Do not add features, tests, docs, or refactors the task does not ask for.
8. Follow <constitution> if one is provided.

Output format (follow exactly):

FILE: path/to/file.ext (modified)
```
<complete file contents here>
```

FILE: path/to/new_file.ext (new)
```
<complete file contents here>
```

DELETED: path/to/old_file.ext — reason
(only include this line if deleting files)

SUMMARY: one short sentence describing what changed.'''


def _generate_lite_output(
    task: str,
    tree: str,
    selected_files: list[Path],
    root: Path,
    constitution: Optional[str],
) -> str:
    """
    Build the lite-mode prompt.

    Section order is chosen for weaker models: role first so the model knows
    its job, task second (highest salience), rules third, context last, and
    the task restated at the very end to counter recency bias in long prompts.

    Parameters
    ----------
    task : str
        Task specification.
    tree : str
        Directory tree string.
    selected_files : list[Path]
        Files to include.
    root : Path
        Project root.
    constitution : Optional[str]
        Constitution content if any.

    Returns
    -------
    str
        Formatted lite-mode output.
    """
    sections = [
        "<role>\nYou are a code implementation assistant. You will be given a "
        "task, rules, and codebase context. Produce code that completes the "
        "task.\n</role>",
        f"<task>\n{task}\n</task>",
        f"<rules>\n{get_lite_instructions()}\n</rules>",
    ]

    if constitution:
        sections.append(f"<constitution>\n{constitution}\n</constitution>")

    sections.append(f"<directory_tree>\n{tree}\n</directory_tree>")

    if selected_files:
        file_sections = []
        for path in selected_files:
            rel_path = path.relative_to(root)
            content, _ = read_file_content(path)
            file_sections.append(f'<file path="{rel_path}">\n{content}\n</file>')
        sections.append("<codebase>\n" + "\n\n".join(file_sections) + "\n</codebase>")

    sections.append(
        "<now>\n"
        f"The task, restated:\n{task}\n\n"
        'Begin your output now. The first line must start with "FILE:".\n'
        "</now>"
    )

    return "\n\n".join(sections)


def generate_output(
    task: str,
    tree: str,
    selected_files: list[Path],
    root: Path,
    constitution: Optional[str],
    mode: str = "full",
) -> str:
    """
    Generate the final context output.

    Args:
        task (str): Task specification.
        tree (str): Directory tree string.
        selected_files (list[Path]): Files to include.
        root (Path): Project root.
        constitution (Optional[str]): Constitution content if any.
        mode (str): 'quick' or 'full' workflow mode.

    Returns:
        str: Formatted output string.
    """
    if mode == "lite":
        return _generate_lite_output(task, tree, selected_files, root, constitution)

    sections = []

    # Header
    sections.append(
        f"""<context>
Generated by ctx.py on {datetime.now().strftime('%Y-%m-%d %H:%M')}
Project: {root.name}
Mode: {mode}
</context>"""
    )

    # Workflow instructions based on mode
    if mode == "quick":
        sections.append(
            f"""<instructions>
{get_quick_instructions()}
</instructions>"""
        )
    else:
        sections.append(
            f"""<workflow>
{get_workflow_instructions()}
</workflow>"""
        )

    # Task
    sections.append(
        f"""<task>
{task}
</task>"""
    )

    # Constitution
    if constitution:
        sections.append(
            f"""<constitution>
{constitution}
</constitution>"""
        )

    # Directory tree
    sections.append(
        f"""<directory_tree>
{tree}
</directory_tree>"""
    )

    # Selected files
    if selected_files:
        file_sections = []
        for path in selected_files:
            rel_path = path.relative_to(root)
            content, _ = read_file_content(path)

            file_sections.append(
                f"""<file path="{rel_path}">
{content}
</file>"""
            )

        sections.append(
            "<codebase>\n" + "\n\n".join(file_sections) + "\n</codebase>"
        )

    output = "\n\n".join(sections)
    return output


def write_output(content: str, output_path: Path) -> None:
    """
    Write output to file.

    Args:
        content (str): Content to write.
        output_path (Path): Destination path.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def copy_to_clipboard(content: str) -> bool:
    """
    Copy content to system clipboard.

    Uses platform-specific commands (zero dependencies):
    - macOS: pbcopy
    - Linux: xclip or xsel
    - Windows: clip

    Args:
        content: Text to copy to clipboard.

    Returns:
        True if successful, False otherwise.
    """
    import subprocess
    import shutil

    # Determine clipboard command based on platform
    if sys.platform == "darwin":
        cmd = ["pbcopy"]
    elif sys.platform == "win32":
        cmd = ["clip"]
    else:
        # Linux - try xclip first, then xsel
        if shutil.which("xclip"):
            cmd = ["xclip", "-selection", "clipboard"]
        elif shutil.which("xsel"):
            cmd = ["xsel", "--clipboard", "--input"]
        else:
            return False

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        process.communicate(input=content.encode("utf-8"))
        return process.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


# =============================================================================
# Main Interactive Flow
# =============================================================================


def main():
    """Main entry point for interactive mode."""
    print()
    print(styled_header("ctx.py - Context Engineering Tool"))
    print(f"\n  {Style.white('Project:')} {Style.yellow(str(Path.cwd().resolve()))}")

    # Determine project root
    root = Path.cwd().resolve()

    # Load ignore patterns
    ignore_patterns = DEFAULT_IGNORE_PATTERNS | load_gitignore(root)

    # Step 1: Mode selection (handled in function)
    mode = prompt_for_mode()

    # Step 2: Task specification (handled in function)
    task = prompt_for_task()
    if not task:
        print(Style.error("\nNo task specified. Exiting."))
        sys.exit(1)

    # Step 3: Constitution (handled in function)
    constitution = load_constitution(root)

    # Step 4: File selection
    print(styled_step(4, 5, "Select Files"))
    tree = generate_tree(root, ignore_patterns)

    files = discover_files(root, ignore_patterns)
    if not files:
        print(f"  {Style.dim('No files found in project.')}")
        selected_files = []
    else:
        # Check for existing presets
        presets = load_presets(root)
        preselected_indices = None
        preset_name = None

        if presets:
            print(f"  Found {Style.yellow(str(len(presets)))} preset(s)")
            preset_name, preset_files = prompt_preset_selection(root, presets)

            if preset_name and preset_files:
                preselected_indices, missing = apply_preset(preset_files, files, root)
                if missing:
                    print(f"  {Style.dim(f'{len(missing)} file(s) from preset no longer exist')}")

        print(f"  Found {Style.yellow(str(len(files)))} files")
        print(f"  {Style.dim('↑↓ navigate  SPACE select  ENTER confirm')}")
        print()
        selected_files = interactive_file_selection(files, root, preselected_indices)

        # Offer to save as preset (if not already using a preset with same files)
        if selected_files:
            prompt_save_preset(root, selected_files)

    # Step 5: Generate output
    print(styled_step(5, 5, "Generate Context"))

    output = generate_output(task, tree, selected_files, root, constitution, mode)
    output_path = root / OUTPUT_FILE

    write_output(output, output_path)

    # Summary
    token_estimate = estimate_tokens(output)

    print(f"\n  {Style.success(Style.CHECK)} {Style.white('Context written to:')} {Style.yellow(OUTPUT_FILE)}")
    print()
    print(styled_summary_box([
        ("Mode", mode),
        ("Task", f"{len(task)} chars"),
        ("Constitution", "included" if constitution else "none"),
        ("Files", str(len(selected_files))),
        ("Est. tokens", f"~{token_estimate:,}"),
    ]))

    # Clipboard option
    print()
    try:
        response = input(styled_prompt("Copy to clipboard?", "y")).strip().lower()
        if response in ("", "y", "yes"):
            if copy_to_clipboard(output):
                print(f"\n  {Style.success(Style.CHECK)} {Style.white('Copied to clipboard!')}")
            else:
                print(f"\n  {Style.dim('Clipboard not available. Copy from')} {Style.yellow(OUTPUT_FILE)}")
        else:
            print(f"\n  Paste contents of {Style.yellow(OUTPUT_FILE)} into your LLM chat.")
    except (KeyboardInterrupt, EOFError):
        print(f"\n\n  Paste contents of {Style.yellow(OUTPUT_FILE)} into your LLM chat.")


if __name__ == "__main__":
    main()

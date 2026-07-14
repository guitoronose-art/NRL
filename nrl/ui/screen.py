"""Curses drawing helpers shared by the dashboard and mini-games."""

from __future__ import annotations

import curses

# Color pair ids
CP_DEFAULT = 0
CP_TITLE = 1
CP_GOOD = 2
CP_BAD = 3
CP_WARN = 4
CP_ACCENT = 5
CP_DIM = 6


def init_colors() -> None:
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(CP_GOOD, curses.COLOR_GREEN, -1)
    curses.init_pair(CP_BAD, curses.COLOR_RED, -1)
    curses.init_pair(CP_WARN, curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_ACCENT, curses.COLOR_MAGENTA, -1)
    curses.init_pair(CP_DIM, curses.COLOR_BLUE, -1)


def attr(pair: int, bold: bool = False) -> int:
    a = curses.color_pair(pair) if curses.has_colors() else 0
    if bold:
        a |= curses.A_BOLD
    return a


def safe_addstr(win, y: int, x: int, text: str, attrs: int = 0) -> None:
    """addstr that never crashes on the bottom-right cell or out-of-bounds."""
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    if x < 0:
        text = text[-x:]
        x = 0
    text = text[: max_x - x]
    if not text:
        return
    try:
        win.addstr(y, x, text, attrs)
    except curses.error:
        pass  # writing the very last cell raises even on success


def draw_box(win, y: int, x: int, h: int, w: int, title: str = "") -> None:
    safe_addstr(win, y, x, "┌" + "─" * (w - 2) + "┐")
    for row in range(y + 1, y + h - 1):
        safe_addstr(win, row, x, "│")
        safe_addstr(win, row, x + w - 1, "│")
    safe_addstr(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘")
    if title:
        safe_addstr(win, y, x + 2, f" {title} ", attr(CP_TITLE, bold=True))


def stat_color(value: float) -> int:
    if value >= 70:
        return attr(CP_GOOD)
    if value >= 40:
        return attr(CP_WARN)
    return attr(CP_BAD)


def draw_meter(win, y: int, x: int, width: int, value: float, label: str = "") -> None:
    """Horizontal 0-100 meter:  label [██████----] 60"""
    if label:
        safe_addstr(win, y, x, f"{label:<10}")
        x += 10
    filled = round(width * value / 100)
    safe_addstr(win, y, x, "[")
    safe_addstr(win, y, x + 1, "█" * filled, stat_color(value))
    safe_addstr(win, y, x + 1 + filled, "░" * (width - filled), attr(CP_DIM))
    safe_addstr(win, y, x + 1 + width, f"] {value:>3.0f}")


def center_text(win, y: int, text: str, attrs: int = 0) -> None:
    _, max_x = win.getmaxyx()
    safe_addstr(win, y, max(0, (max_x - len(text)) // 2), text, attrs)


def flash_message(win, text: str, attrs: int = 0, wait_ms: int = 1200) -> None:
    """Show a centered message and pause briefly."""
    max_y, _ = win.getmaxyx()
    center_text(win, max_y // 2, f"  {text}  ", attrs | curses.A_REVERSE)
    win.refresh()
    curses.napms(wait_ms)

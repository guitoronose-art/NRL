"""Off-field loop: training, shop, and relationship management screens."""

from __future__ import annotations

import curses

from nrl import config
from nrl.minigames.training import play_training
from nrl.models import GameState
from nrl.ui import screen as ui

TRAINING_ENERGY_COST = 15

REL_ACTIONS = [
    # (label, rel_key, gain, energy_cost, cash_cost)
    ("Extra video session with the coach", "coach", 8, 10, 0),
    ("Team barbecue at your place", "teammates", 8, 5, 100),
    ("Fan signing session", "fans", 8, 10, 0),
]


def _pick_from(stdscr, title: str, options: list[str], footer: str = "") -> int | None:
    """Generic vertical picker. Returns index or None on 'q'."""
    selected = 0
    stdscr.nodelay(False)
    curses.curs_set(0)
    while True:
        stdscr.erase()
        ui.center_text(stdscr, 1, title, ui.attr(ui.CP_TITLE, bold=True))
        for i, opt in enumerate(options):
            marker = "▶ " if i == selected else "  "
            attrs = ui.attr(ui.CP_ACCENT, bold=True) | curses.A_REVERSE if i == selected else 0
            ui.safe_addstr(stdscr, 3 + i, 4, f"{marker}{opt}", attrs)
        max_y, _ = stdscr.getmaxyx()
        ui.safe_addstr(stdscr, max_y - 1, 2, footer or "↑/↓ select · Enter confirm · q back",
                       ui.attr(ui.CP_DIM))
        stdscr.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            selected = (selected - 1) % len(options)
        elif key in (curses.KEY_DOWN, ord("j")):
            selected = (selected + 1) % len(options)
        elif key in (curses.KEY_ENTER, 10, 13):
            return selected
        elif key == ord("q"):
            return None


def training_screen(stdscr, state: GameState) -> None:
    p = state.player
    while True:
        options = [
            f"{k.capitalize():<10} {getattr(p, k):>3}   (costs {TRAINING_ENERGY_COST}% energy)"
            for k in p.STAT_KEYS
        ] + ["Back"]
        choice = _pick_from(stdscr, f"🏋 TRAINING GROUND — Energy: {p.energy}%", options)
        if choice is None or choice == len(options) - 1:
            return
        if p.energy < TRAINING_ENERGY_COST:
            ui.flash_message(stdscr, "Too exhausted to train! Buy an energy drink.", ui.attr(ui.CP_BAD, bold=True))
            continue
        stat = p.STAT_KEYS[choice]
        p.adjust("energy", -TRAINING_ENERGY_COST)
        gain = play_training(stdscr, stat)
        p.adjust(stat, gain)


def shop_screen(stdscr, state: GameState) -> None:
    p = state.player
    while True:
        options = [
            f"{name:<16} ${cost:<5} {desc}"
            for name, cost, desc, _, _ in config.SHOP_ITEMS
        ] + ["Back"]
        choice = _pick_from(stdscr, f"🛒 SHOP — Cash: ${p.cash}", options)
        if choice is None or choice == len(options) - 1:
            return
        name, cost, _, key, value = config.SHOP_ITEMS[choice]
        if p.cash < cost:
            ui.flash_message(stdscr, "Not enough cash!", ui.attr(ui.CP_BAD, bold=True))
            continue
        if key == "energy" and p.energy >= 100:
            ui.flash_message(stdscr, "You're already fully charged!", ui.attr(ui.CP_WARN))
            continue
        p.cash -= cost
        p.adjust(key, value)
        ui.flash_message(stdscr, f"Bought {name}!", ui.attr(ui.CP_GOOD, bold=True))


def relationships_screen(stdscr, state: GameState) -> None:
    p = state.player
    while True:
        status = " · ".join(f"{k.capitalize()} {getattr(p, k)}%" for k in p.REL_KEYS)
        options = [
            f"{label:<38} (+{gain} · -{energy}% energy" + (f" · ${cash})" if cash else ")")
            for label, _, gain, energy, cash in REL_ACTIONS
        ] + ["Back"]
        choice = _pick_from(stdscr, f"🤝 RELATIONSHIPS — {status}", options)
        if choice is None or choice == len(options) - 1:
            return
        label, key, gain, energy_cost, cash_cost = REL_ACTIONS[choice]
        if p.energy < energy_cost:
            ui.flash_message(stdscr, "Too tired for that right now.", ui.attr(ui.CP_BAD, bold=True))
            continue
        if p.cash < cash_cost:
            ui.flash_message(stdscr, "Not enough cash!", ui.attr(ui.CP_BAD, bold=True))
            continue
        p.adjust("energy", -energy_cost)
        p.cash -= cash_cost
        p.adjust(key, gain)
        ui.flash_message(stdscr, f"{key.capitalize()} +{gain}!", ui.attr(ui.CP_GOOD, bold=True))

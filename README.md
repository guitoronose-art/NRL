# NRL Career Simulator 🏉

A terminal-based NRL career game in the spirit of *New Star Soccer*, built with
Python and `curses` (stdlib only — no dependencies).

Live your career from rookie to legend: play real-time mini-games during
matches, train between rounds, manage your energy, cash, and your
relationships with the coach, teammates, and fans across a full 27-round
NRL season with a live 17-team ladder.

## Run

```bash
python3 main.py                    # full career game
python3 -m nrl.minigames.kick      # standalone kick mini-game prototype
python3 -m unittest discover tests # headless logic tests
```

Requires Python 3.10+ and a terminal at least ~80x30.

## Controls

- **Menus:** `↑`/`↓` (or `k`/`j`) to select, `Enter` to confirm, `q` to quit
- **Kick mini-game:** `Space` to lock the power bar, then `Space` again to
  lock the wind/angle bar
- **Breakaway run:** `↑`/`↓` to dodge defenders

## Architecture

```
main.py                  entry point - career loop state machine
nrl/
  config.py              teams, constants, tuning values
  models.py              Player / TeamRecord / Contract / ladder logic (pure)
  ui/screen.py           curses drawing helpers
  ui/dashboard.py        main menu, stats panel, ladder view
  minigames/base.py      shared real-time loop + Oscillator (pure logic)
  minigames/kick.py      power & angle bar kick
tests/test_logic.py      headless unit tests (no curses required)
```

**Design rule:** every mini-game separates pure simulation logic (judging,
trajectories, oscillators) from curses rendering, so game balance is
unit-testable without a terminal.

## Roadmap

- [x] Step 1: project scaffold, dashboard UI (stats, contract, ladder)
- [x] Step 2: real-time kick mini-game (power + angle bars)
- [ ] Step 3: match engine — live scoreboard, commentary ticker, player moments
- [ ] Step 4: playmaker pass (vector shooting) + breakaway run mini-games
- [ ] Step 5: full 27-round season, fixtures, ladder simulation
- [ ] Step 6: management loop — training mini-game, shop, relationships

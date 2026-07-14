# NRL Career Simulator 🏉

A terminal-based NRL career game in the spirit of *New Star Soccer*, built with
Python and `curses` (stdlib only — no dependencies).

Live your career from rookie to legend: play real-time mini-games during
matches, train between rounds, manage your energy, cash, and your
relationships with the coach, teammates, and fans across a full 27-round
NRL season with a live 17-team ladder.

## Run

```bash
python3 main.py                      # full career game
python3 -m nrl.minigames.kick        # standalone mini-game prototypes
python3 -m nrl.minigames.pass_game
python3 -m nrl.minigames.breakaway
python3 -m nrl.minigames.training
python3 -m unittest discover tests   # headless logic tests
```

Requires Python 3.10+ and a terminal at least ~80x30.

## Controls

- **Menus:** `↑`/`↓` (or `k`/`j`) to select, `Enter` to confirm, `q` to quit/back
- **Kick mini-game:** `Space` to lock the power bar, then `Space` again to
  lock the wind/angle bar
- **Playmaker pass:** `Space` to release the pass when the pivoting arrow
  lines up with your winger `O` — avoid the defender `X`
- **Breakaway run:** `↑`/`↓` (or `k`/`j`) to dodge defenders
- **Training:** `Space` when the marker is inside the green zone

## Gameplay loop

Each round: play the match (a live-ticking scoreboard with commentary that
pauses into 3–5 interactive Player Moments), then spend the week training,
shopping, or managing relationships.

- **Energy** drains from matches and training; low energy weakens your
  effective stats in mini-games. Recover with shop items or the bye week.
- **Coach** below 25 gets you benched. **Teammates** below 35 means fewer
  passing moments. **Fans** swing with your big-moment performances.
- Intercepted passes get run back for opposition tries — releasing the ball
  into `X` hurts.
- Contract renewal at season's end depends on your overall ability plus
  coach and fan standing.

## Architecture

```
main.py                    entry point - career loop state machine
nrl/
  config.py                teams, constants, tuning values
  models.py                Player / TeamRecord / Contract / ladder logic (pure)
  season.py                round-robin fixtures + AI results (pure)
  match_engine.py          match timeline planning (pure) + live curses runner
  management.py            training / shop / relationships screens
  ui/screen.py             curses drawing helpers
  ui/dashboard.py          main menu, stats panel, ladder view
  minigames/base.py        shared real-time loop + Oscillator (pure logic)
  minigames/kick.py        power & angle bar kick
  minigames/pass_game.py   vector-shooting playmaker pass
  minigames/breakaway.py   scrolling obstacle-dodge run
  minigames/training.py    timing-tap training session
tests/                     headless unit tests (no curses required)
```

**Design rule:** every mini-game separates pure simulation logic (judging,
trajectories, oscillators) from curses rendering, so game balance is
unit-testable without a terminal.

## Roadmap

- [x] Step 1: project scaffold, dashboard UI (stats, contract, ladder)
- [x] Step 2: real-time kick mini-game (power + angle bars)
- [x] Step 3: match engine — live scoreboard, commentary ticker, player moments
- [x] Step 4: playmaker pass (vector shooting) + breakaway run mini-games
- [x] Step 5: full 27-round season, fixtures, ladder simulation
- [x] Step 6: management loop — training mini-game, shop, relationships,
      benching, energy/fatigue, contract renewal

Ideas for later: multi-club transfers, finals series, save/load, injuries,
sponsor deals, State of Origin call-ups.

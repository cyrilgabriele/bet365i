**PROMPT**

You are my ML + quantitative betting engineer. Help me implement and document a fully reproducible research-grade football (soccer) betting project.

## Objective

Build a first-version end-to-end system that:

1. trains a model to predict **1X2** match outcome probabilities (Home/Draw/Away),
2. compares these probabilities to **Bet365 closing odds**,
3. places bets only when there is positive expected value (with a safety threshold), and
4. sizes stakes using **fractional Kelly** with strict risk caps.

This is a **research/backtest** setup first (offline, reproducible). No live betting and no live data feeds.

---

## Data Sources

### Match results + historical odds for training/testing

* Primary dataset source: **football-data.co.uk** CSVs (downloaded data for reproducibility).
* Use Bet365 odds columns if available (e.g., `B365H`, `B365D`, `B365A`).

### Odds API (for historical Bet365 odds if needed)

* Use OddsPapi historical odds endpoint: `GET /v4/historical-odds` from [https://oddspapi.io/en/docs/](https://oddspapi.io/en/docs/)
* Extract odds for **Bet365** only.
* Define odds used in backtest as **closing odds**: *the last Bet365 quote before kickoff time* for each outcome H/D/A. If multiple timestamps exist, choose the latest `createdAt <= kickoff_time`.

Important: Odds are **decimal odds** (e.g., 1.75). Convert to implied probabilities only when needed for margin removal/market comparison, but compute EV/Kelly directly from odds.

---

## Prediction Target

* Predict the full 3-way probability vector per match:
  [
  (p_H, p_D, p_A), \quad p_H+p_D+p_A=1
  ]
* Train using multiclass classification (softmax) with multiclass cross-entropy (log loss).
* Calibrate predicted probabilities (required) using a suitable method (temperature scaling or isotonic/Platt one-vs-rest). Evaluate calibration.

---

## Backtest Setup (Reproducible Research)

* Use a **time-based split** (windowed / walk-forward):

  * Select a fixed historical time window for train and a following window for test.
  * No random shuffling.
  * Prevent leakage: only use features available pre-match.

* Metrics to report:

  * Multiclass log loss
  * Brier score
  * Calibration plots (reliability)
  * Betting ROI / profit
  * Max drawdown (bankroll curve)
  * Number of bets placed
  * Optional: CLV if closing line comparisons become possible later (for v1 it’s okay to omit).

---

## Odds Handling

### Decimal odds meaning

* Decimal odds (O) imply raw probability (q = 1/O) (not margin-free).
* For market implied probabilities in 1X2:
  [
  q_k = 1/O_k,; S=\sum_k q_k,; \tilde{q}_k = q_k/S
  ]
  Use (\tilde{q}_k) only if comparing model probabilities to market probabilities. For EV and Kelly, use (O_k) directly.

---

## Bet Selection Policy (1X2)

For each match, compute for each outcome (k \in {H,D,A}):
[
EV_k = p_k \cdot O_k - 1
]
Then:

1. pick (k^* = \arg\max EV_k)
2. place at most **one bet per match**, on outcome (k^*)
3. bet only if:

   * (EV_{k^*} > 0.02) (2% edge threshold)
   * otherwise **skip match**

This defines “which games to bet”: only those where the best-outcome EV clears the threshold.

---

## Staking (Fractional Kelly + Risk Caps)

For the selected bet outcome (k^*) with probability (p) and decimal odds (O):

Full Kelly fraction:
[
f^* = \frac{pO - 1}{O - 1}
]
Use **fractional Kelly** with coefficient (\alpha = 0.25):
[
f = 0.25 \cdot f^*
]
If (f \le 0): no bet.

Hard risk constraints (apply after computing (f)):

* Max stake per bet: **1% of bankroll**
* Max total exposure per day/matchday: **5% of bankroll**
* Track bankroll as it evolves during the backtest.
* Use singles only (no parlays).

---

## Project Structure

Use a reproducible folder layout:

* `data/raw/` : immutable downloaded CSVs and raw API responses (never edit).
* `data/clean/` : cleaned/standardized datasets (column names, types, dates, team names), no merging.
* `data/complete/` (or `data/merged/`): final merged modeling table with:

  * match identifiers
  * kickoff time
  * features
  * label (H/D/A)
  * Bet365 **closing** odds for H/D/A
  * any derived fields needed for training/backtesting

Keep all transformations deterministic and scripted.

---

## Feature Engineering

* Maintain rolling **pre-match team ratings** (ELO-style or scaled variants) that are
  updated only after each finished match. For a given fixture, derive features from
  the ratings as they stood **immediately before kickoff** to avoid leakage.
* Allow the rating pipeline to ingest historical scorelines (full-time goal delta,
  home/away splits, recent form windows) so the model can learn relative strength
  without ever seeing future outcomes at inference time.
* Expose league-aware attributes (e.g., league identifier, competition strength
  multipliers) so multi-league datasets remain distinguishable and calibration can
  adapt per competition.

---

## Python Project Configuration

Use a `pyproject.toml` for project specs and tooling configuration (dependencies, linting, formatting, tests). Include typical libs: pandas/numpy/scikit-learn/requests and whichever modeling library is chosen.

---

## Deliverables

1. A clear written specification of the pipeline (data → cleaning → feature generation → model → calibration → betting decisions → staking → evaluation).
2. Code structure suggestion (modules) and key functions.
3. A minimal working prototype plan: first run on one league/season set from football-data with Bet365 odds columns.
4. Warnings about common pitfalls: leakage, mixing bookmaker odds, odds timestamp ambiguity, non-calibrated probabilities, and overbetting.

Proceed by proposing the detailed implementation plan and exact data columns needed, then the modeling and backtest steps.

**END PROMPT**

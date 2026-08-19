# BVSim Web User Guide

BVSim simulates beach volleyball points from team skill probabilities. Use the web interface to compare teams, test hypothetical improvements, inspect rally sequences, and understand how points are won and lost.

BVSim results are estimates from simulated points. They describe what the configured probability model produces; they are not guarantees about a real match.

## Start the Web Interface

Install the application dependencies, then start the server:

```bash
pip install -e .
pip install Flask
python -m bvsim_web
```

Open [http://localhost:8000](http://localhost:8000).

You can also use the launch scripts:

```bash
# Linux or macOS
./run_web.sh

# Windows Command Prompt
run_web.bat
```

## A Good First Run

1. In **Simulate**, select a team for Team A and Team B.
2. Click **Quick** to simulate 10,000 points.
3. Read the win percentages in the Output pane.
4. Review the tables below the chart to see how the points ended.
5. Use **Skills** to test which individual probability improvements have the greatest estimated effect.

## Understanding Teams

A team is a set of probabilities stored in YAML. Probabilities are decimals from `0` to `1`:

- `0.05` means 5%.
- `0.50` means 50%.
- `1.00` means 100%.

Each group of possible outcomes must add up to `1.00`. Many probabilities are conditional. For example, attack probabilities after an excellent set can differ from attack probabilities after a poor set.

### Teams Pane

Use the **Teams** pane to:

- Create a team from the Basic or Advanced template.
- Upload an existing `.yaml` or `.yml` team file.
- Edit, save, download, or delete a listed team.

The editor validates probability ranges and totals when you save. A team file may omit an entire top-level probability section; BVSim fills that section from the Basic template. If you include a section, its included probability distributions must be complete and total `1.00`.

## Simulation Size: Run, Quick, and Accurate

| Action | Simulated points | When to use it |
|---|---:|---|
| **Quick** | 10,000 | Fast exploration and checking whether an idea is promising |
| **Run / Analyze** | 200,000 by default | Normal analysis |
| **Accurate** | 400,000 | A more stable estimate when differences are small |

In the Simulate pane, entering **Points** and clicking **Run** uses that custom number. Quick and Accurate use their preset sizes.

More simulated points reduce random sampling noise. They do not make an unrealistic team model more realistic.

## Simulate Pane

Select Team A and Team B, then run a point simulation. Serving alternates between the teams so that each receives approximately the same number of serves.

### Main Results

| Result | Meaning |
|---|---|
| **Wins** | Number of simulated points won by the team |
| **Win %** | Team wins divided by all simulated points |
| **Total points** | Number of independent points simulated |
| **Average duration** | Average number of volleyball actions or states in a point, not elapsed time |

Example: if Team A wins 54,200 of 100,000 points, its point win rate is `54.20%`. This means the model gave Team A a 54.20% chance of winning an individual point under the simulated conditions.

The two team win rates should add up to 100%.

### Point Type Distribution

This table explains how all simulated points ended.

| Column | Meaning |
|---|---|
| **Point Type** | Final event that decided the point |
| **Count** | Number of points ending that way |
| **% of Points** | Count divided by all simulated points |

Common point types are:

| Point type | Meaning |
|---|---|
| `ace` | The serve directly won the point |
| `serve_error` | The server made an error |
| `receive_error` | Reception failed |
| `set_error` | Setting failed |
| `kill` | An attack directly won the point |
| `attack_error` | The attacker made an error |
| `stuff` | A block directly won the point |
| `dig_error` | Defense failed to control an attack |
| `rally` | Generic rally result when no more specific ending is available |

### Point Type Wins by Team

This table looks only at the points won by each team.

For example, if Team A has 20,000 wins and 8,000 are labeled `kill`, the Team A `%Wins` value for `kill` is 40%. It means 40% of Team A's winning points ended in a kill. It does **not** mean Team A kills 40% of every attack or every simulated point.

### Serving Performance

| Result | Meaning |
|---|---|
| **Serve Win %** | Percentage of points the team won when it started as the serving team |
| **Serves Count** | Number of simulated points for which the team served |
| **Serves Share** | Team's share of all simulated serves |

Serve Win % includes every way the serving team can eventually win the point; it is not the ace percentage.

### Duration by Point Type

Duration is measured in simulated actions or states.

- **Avg Dur** is the average number of actions for points of that type.
- **Min** and **Max** are the shortest and longest observed points of that type.
- **% of Points** is the share of all simulated points ending with that type.

## Skills Pane

Use **Skills** to answer: "If this team improved one probability at a time, which improvement would matter most against this opponent?"

1. Select the team to improve.
2. Select its opponent.
3. Enter an **Improve** value, such as `5%` or `0.05`.
4. Click Analyze, Quick, or Accurate.

The improvement is additive. If a probability is `0.10` and Improve is `5%`, BVSim tests `0.15`, not `0.105`. Other outcomes in the same distribution are adjusted so that the distribution remains valid.

Each row tests one parameter independently. BVSim does not apply all listed improvements to the team at the same time.

### Skills Results

| Result | Meaning |
|---|---|
| **Baseline win rate** | Point win percentage before changing the tested probability |
| **Point Impact mean** | Estimated change in point win rate, in percentage points |
| **Match Impact mean** | Estimated change in best-of-three match win probability, in percentage points |
| **Lower / Upper** | Approximate confidence interval around the estimated impact |
| **Significant** | Whether the displayed interval stays entirely above or below zero |

Percentage-point changes are not relative percentages. Moving from 50% to 53% is a **+3 percentage-point** impact, or a 6% relative increase.

Example:

```text
Match Impact mean: +4.20%
95% CI: [+2.10%, +6.30%]
Significant: Yes
```

This means the tested skill change is estimated to increase match win probability by 4.20 percentage points. The interval does not include zero, so the simulation provides evidence that the effect is positive under this model.

If an interval includes zero, such as `[-0.80%, +1.40%]`, the simulation did not clearly distinguish the change from sampling variation. It does not prove that the skill has no effect.

### Skills Chart Colors

- Dark blue: significant positive estimate.
- Dark red: significant negative estimate.
- Light blue: positive estimate whose interval includes zero.
- Light red: negative estimate whose interval includes zero.
- The horizontal line shows the interval.
- The vertical zero line separates estimated improvements from estimated regressions.

The match impact is a derived estimate that translates point-win changes into match-win changes using simulated best-of-three matches. Treat it as a planning aid rather than an exact forecast.

## Scenarios Pane

Use **Scenarios** to compare complete team variants instead of changing one probability at a time.

1. Select a baseline team.
2. Select one or more scenario YAML files. Hold Ctrl on Windows/Linux or Command on macOS to select multiple files.
3. Run the analysis.

The selected baseline team plays against itself to establish the baseline. Each scenario file then replaces one side with the variant, allowing you to compare the variant with the unchanged baseline.

By default, each scenario is evaluated across five runs. The displayed values mean:

- **Baseline mean**: average baseline point win rate across runs.
- **Baseline lower/upper**: interval around that baseline estimate.
- **Point impact**: scenario point win rate minus baseline point win rate.
- **Match impact**: estimated match-win change derived from the point impact.
- **Runs**: number of repeated analyses contributing to the result.

A positive result favors the scenario variant. A negative result means it performed worse than the baseline.

Use Scenarios when several coordinated changes belong together, such as a serve-focused or attack-focused team profile. Use Skills when you want to isolate one probability.

## Round Robin Pane

Select two or more teams to simulate every unique pairing.

### Win Rate Matrix

Read the matrix as **row team versus column team**. A value of `62.5%` in row Alpha and column Beta means Alpha won 62.5% of its simulated points against Beta. The reverse cell should be approximately `37.5%`.

The diagonal contains `-` because a team is not compared with itself.

### Rankings

**Average Win %** is a team's arithmetic mean point win rate against every other selected team. Rankings are sorted from highest to lowest average.

Example: if Alpha records 60% against Beta and 54% against Gamma, Alpha's average is 57%.

This ranking weights every opponent equally. It is not a league table, match record, confidence score, or strength-of-schedule adjustment.

## Rallies Pane

Generate example points to inspect how the state machine moves from serve to the point result.

- Blue cards represent Team A actions.
- Red cards represent Team B actions.
- Arrows show action order.
- The quality label describes the sampled outcome, such as excellent, good, poor, error, ace, kill, or defended.
- The final result identifies the event that decided the point.
- The winner is the team awarded that point.

Rallies are examples, not summaries. A few generated rallies should not be used to estimate team strength; use Simulate for aggregate results.

## Output and JSON Output

The **Output** pane presents the current result as a chart and readable tables. Running another operation replaces the previous visualization.

The **JSON Output** pane contains the same result in machine-readable form:

- Use **Copy** to copy it.
- Use it for detailed inspection or downstream analysis.
- Values under `parameters` record the simulation settings.
- `used_defaults: true` means BVSim substituted a Basic template for a missing selection.
- A `note` explains which default was used.

Most users can rely on the chart and tables; the JSON is primarily useful for auditing and integration.

Use **Hide Controls** to give the result panes more space. Use **Info** for the in-application quick guide.

## Default Selections

- Simulate, Skills, and Rallies use a Basic template when a team selection is blank.
- Round Robin requires at least two selected teams in the web interface.
- Scenarios use the selected team as both the baseline team and baseline opponent.

## How to Interpret Results Responsibly

- Compare differences that are larger than the displayed uncertainty.
- Repeat important analyses with Accurate mode.
- Check whether the team probability inputs are realistic and based on enough observations.
- Do not interpret a point win rate as a match win rate.
- Do not interpret correlation in the model as proof that training a skill will cause the predicted improvement.
- Remember that BVSim models the configured volleyball states; injuries, tactics, fatigue, weather, partnerships, and opponent adaptation are not represented unless encoded in the probabilities.

## Current Limitations

- Analyses run synchronously, so large requests keep the page waiting until they finish.
- The web interface is intended for local or trusted use and has no authentication.
- Generated values contain Monte Carlo sampling variation.
- Confidence intervals and match impacts are approximations from the simulator, not guarantees.

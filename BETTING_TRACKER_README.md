# Betting Tracker System

A comprehensive betting tracking system that allows you to manage parlays, prop bets, and moneyline bets while monitoring win/loss records and profit/loss metrics.

## Features

### Bet Input Format

The system supports a structured text format for entering bets. You can enter multiple bets at once, including parlays and singles.

#### Format Specification

Each bet leg consists of the following fields separated by commas:

```
Type: [moneyline|prop], Selection: [bet description], Game: [Team1 vs Team2], Date: [YYYY-MM-DD], Odds: [odds], Stake: [amount], Reason: [reasoning]
```

#### Example

```
Parlay #1 (3 legs)
Type: moneyline, Selection: Celtics ML, Game: Celtics vs Heat, Date: 2026-02-07, Odds: -150, Stake: 300, Reason: Strong matchup edge.
Type: moneyline, Selection: Bucks ML, Game: Bucks vs Pacers, Date: 2026-02-07, Odds: -140, Stake: 300, Reason: Better efficiency profile.
Type: prop, Selection: Anthony Edwards over 27.5 pts, Game: Timberwolves vs Pelicans, Date: 2026-02-07, Odds: -110, Stake: 300, Reason: High‑usage scoring role.

Parlay #2 (2 legs)
Type: moneyline, Selection: Kings ML, Game: Kings vs Clippers, Date: 2026-02-07, Odds: -130, Stake: 250, Reason: Home‑court edge.
Type: prop, Selection: De'Aaron Fox over 25.5 pts, Game: Kings vs Clippers, Date: 2026-02-07, Odds: -110, Stake: 250, Reason: Favorable defensive matchup.

Singles
Type: moneyline, Selection: Leeds ML, Game: Leeds vs Nottingham Forest, Date: 2026-02-06, Odds: -120, Stake: 100, Reason: Home form advantage.
Type: prop, Selection: Derrick White over 5.5 assists, Game: Celtics vs Heat, Date: 2026-02-07, Odds: -110, Stake: 100, Reason: Increased playmaking role.
```

## Field Descriptions

- **Type**: Either `moneyline` (team to win) or `prop` (player prop bet)
- **Selection**: The specific bet (e.g., "Celtics ML" for Celtics moneyline, "Anthony Edwards over 27.5 pts" for a player prop)
- **Game**: The matchup in format "Team1 vs Team2"
- **Date**: Game date in YYYY-MM-DD format
- **Odds**: American odds (e.g., -110, -150, +200)
- **Stake**: How much you're wagering (in dollars)
- **Reason**: Your reasoning for the bet (optional but recommended)

## How It Works

### Parsing

When you submit bets through the UI:

1. The system parses your text input
2. Automatically detects the sport (NBA, NCAAB, NFL, MLB, NHL, UFC, Soccer, etc.)
3. Matches games to existing games in the database
4. Attempts to find player names for prop bets
5. Groups bets into parlays based on their section headers

### Bet Storage

Each bet leg is stored with:
- Individual odds and stake
- Player name (for prop bets)
- Game reference
- Parlay grouping (for tracking parlays together)
- Status (pending, won, lost, void)
- Reasoning

### Parlay Tracking

Bets are automatically grouped by their parlay header:
- **Parlay #1**: All legs from "Parlay #1" are grouped together
- **Parlay #2**: All legs from "Parlay #2" are grouped together
- **Singles**: Single bets are grouped separately

### Statistics

The dashboard displays:
- **Total Bets**: Number of bets placed
- **Won**: Number of winning bets
- **Lost**: Number of losing bets
- **Pending**: Number of bets awaiting results
- **Win Rate**: Percentage of bets that won
- **Total Staked**: Total amount wagered
- **Total Profit/Loss**: Overall profit or loss

### Grading

Click "Grade Pending" to:
1. Check game results
2. Automatically update bet statuses (won/lost)
3. Calculate profit/loss based on odds

## Supported Sports

The system can automatically detect:
- **NBA**: Basketball
- **NCAAB**: College Basketball
- **NFL**: American Football
- **MLB**: Baseball
- **NHL**: Hockey
- **UFC**: Mixed Martial Arts
- **Soccer/Football**: International

## Bet Types

### Moneyline Bets
```
Type: moneyline, Selection: [Team] ML, Game: [Team1] vs [Team2], ...
```
- Example: "Celtics ML" means Celtics to win the game

### Prop Bets
```
Type: prop, Selection: [Player] over/under [Line] [Stat], Game: [Team1] vs [Team2], ...
```
- **Points**: "Anthony Edwards over 27.5 pts"
- **Rebounds**: "Player over 8.5 rebounds"
- **Assists**: "Player over 5.5 assists"
- **Yards**: "Player over 250 passing yards"

## API Endpoints

### Place Bets from Text
```
POST /bets/place-multiple
Content-Type: application/x-www-form-urlencoded
raw_text=[your bet text]
```

### Get All Bets with Details
```
GET /bets/all
```

### Grade Pending Bets
```
POST /bets/grade
```

## Profit/Loss Calculation

Profit is calculated based on American odds:

- **Positive Odds** (e.g., +200): `stake × (odds / 100)`
- **Negative Odds** (e.g., -110): `stake / (abs(odds) / 100)`
- **Loss**: `-stake`

## Tips for Better Tracking

1. **Always include reasoning**: This helps you review your betting strategy
2. **Be consistent with team names**: Use official team names or abbreviations
3. **Update dates correctly**: Ensure dates match actual game dates
4. **Use specific prop descriptions**: Include the line number (e.g., "over 27.5 pts")
5. **Grade regularly**: Click "Grade Pending" after games finish to update results

## Notes

- The system will attempt to match games automatically, but accuracy depends on having complete game data
- Player prop matching works best with full player names
- Void bets (games not found, players not found) are marked as "void" and don't count toward statistics
- All times are stored in UTC

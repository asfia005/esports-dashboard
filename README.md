# Esports Tournament & Player Stat Line Dashboard

A desktop dashboard for recording esports tournaments, match fixtures, and player statistics in a local SQLite database. The application is built with Python and Tkinter.

## Features

- Add tournament, match fixture, and player-stat records; reuse existing tournaments.
- Initialize sample records automatically when the database is empty.
- Browse the database in four tabbed views, including a combined SQL join.
- Delete records using dynamic dropdowns, with related records removed through cascading deletes.
- Validate inputs and persist data locally in SQLite.

## Database Schema

| Table | Purpose |
| --- | --- |
| `tournaments` | Tournament records (primary key). |
| `match_fixtures` | Match records linked to tournaments by a foreign key. |
| `player_stats` | Player stat-line records linked to match fixtures by a foreign key. |

Foreign-key relationships use `ON DELETE CASCADE` so deleting a parent record removes its related records. There is no separate player identity table.

## Requirements and Run

- Python 3.10 or newer with Tkinter available in the local Python installation.
- SQLite, included with standard Python installations.

On Windows, install Python from [python.org](https://www.python.org/downloads/) and ensure the Tcl/Tk support is included. In Command Prompt or PowerShell, navigate to this project folder and run:

```powershell
py esports_dashboard_qa.py
```

The app creates and uses its SQLite database locally, initializing sample data when all application tables are empty. Hosted Google Colab cannot display the native Tkinter GUI; run the app in a local desktop Python environment. The application is not deployed online.
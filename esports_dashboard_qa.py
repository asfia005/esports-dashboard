"""Esports Tournament & Player Stat Line Dashboard.

Standard-library only: tkinter, ttk, sqlite3 and Python standard modules.
Run: python esports_dashboard_qa.py
Hosted Google Colab can initialize/test SQLite, but cannot display a native Tk window.
"""

from __future__ import annotations

import math
import os
import re
import sqlite3
import sys
import tkinter as tk
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Iterator

APP_TITLE = "ESPORTS | Tournament & Player Stat Line Dashboard"
DB_NAME = "esports_tournament.db"
WINDOW_SIZE = "1280x820"
MIN_SIZE = (1050, 680)

BG = "#101722"
PANEL = "#192536"
CARD = "#223248"
ACCENT = "#00D4AA"
ACCENT_HOVER = "#35EBC7"
TEXT = "#F0F4FA"
MUTED = "#A5B3C5"
DANGER = "#E65B70"


def database_path() -> Path:
    """Keep the database beside this script (or in cwd in notebook use)."""
    try:
        base = Path(__file__).resolve().parent
    except NameError:
        base = Path.cwd()
    return base / DB_NAME


class Database:
    """SQLite persistence layer. Every connection enables and verifies FKs."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path), timeout=10)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            enabled = conn.execute("PRAGMA foreign_keys").fetchone()
            if enabled != (1,):
                raise sqlite3.DatabaseError("Could not enable SQLite foreign keys.")
            # The connection context commits on success and rolls back on error.
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create the schema and seed only when all three tables are empty."""
        with self.connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tournaments (
                    tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    admin_email TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS match_fixtures (
                    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    match_title TEXT NOT NULL,
                    match_date TEXT NOT NULL,
                    FOREIGN KEY (tournament_id)
                        REFERENCES tournaments(tournament_id)
                        ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    stat_type TEXT NOT NULL,
                    stat_value REAL NOT NULL CHECK (stat_value >= 0),
                    FOREIGN KEY (match_id)
                        REFERENCES match_fixtures(match_id)
                        ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_tournament
                ON match_fixtures(tournament_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stats_match
                ON player_stats(match_id)
            """)

            counts = (
                conn.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM match_fixtures").fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM player_stats").fetchone()[0],
            )
            if counts == (0, 0, 0):
                self._seed(conn)

    @staticmethod
    def _seed(conn: sqlite3.Connection) -> None:
        """Caller owns the transaction."""
        tournament_rows = [
            ("Valorant Championship 2026", "admin@valorantleague.com"),
            ("BGMI Masters 2026", "admin@bgmimasters.com"),
            ("CS2 Invitational 2026", "admin@cs2league.com"),
        ]
        ids: dict[str, int] = {}
        for name, email in tournament_rows:
            cur = conn.execute(
                "INSERT INTO tournaments (tournament_name, admin_email) VALUES (?, ?)",
                (name, email),
            )
            ids[name] = int(cur.lastrowid)

        match_rows = [
            (ids["Valorant Championship 2026"], "Quarter Final - Falcon vs Viper", "2026-11-10"),
            (ids["Valorant Championship 2026"], "Grand Final - Falcon vs Phoenix", "2026-11-12"),
            (ids["BGMI Masters 2026"], "Semi Final - Alpha vs Omega", "2026-11-14"),
            (ids["BGMI Masters 2026"], "Grand Final - Alpha vs Delta", "2026-11-16"),
            (ids["CS2 Invitational 2026"], "Quarter Final - Red vs Blue", "2026-11-18"),
            (ids["CS2 Invitational 2026"], "Grand Final - Red vs Black", "2026-11-20"),
        ]
        match_ids: list[int] = []
        for tournament_id, title, match_date in match_rows:
            cur = conn.execute(
                """INSERT INTO match_fixtures
                   (tournament_id, match_title, match_date) VALUES (?, ?, ?)""",
                (tournament_id, title, match_date),
            )
            match_ids.append(int(cur.lastrowid))

        stat_rows = [
            (match_ids[0], "Kills", 24), (match_ids[0], "Assists", 8),
            (match_ids[1], "Kills", 31), (match_ids[1], "Accuracy %", 76.5),
            (match_ids[2], "Kills", 18), (match_ids[2], "Assists", 12),
            (match_ids[3], "Kills", 27), (match_ids[3], "Accuracy %", 82.4),
            (match_ids[4], "Kills", 21), (match_ids[4], "Assists", 9),
            (match_ids[5], "Kills", 29), (match_ids[5], "Accuracy %", 79.8),
        ]
        conn.executemany(
            "INSERT INTO player_stats (match_id, stat_type, stat_value) VALUES (?, ?, ?)",
            stat_rows,
        )

    def counts(self) -> tuple[int, int, int]:
        with self.connection() as conn:
            return (
                conn.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM match_fixtures").fetchone()[0],
                conn.execute("SELECT COUNT(*) FROM player_stats").fetchone()[0],
            )

    def tournaments(self) -> list[tuple]:
        with self.connection() as conn:
            return conn.execute(
                "SELECT tournament_id, tournament_name, admin_email "
                "FROM tournaments ORDER BY tournament_id"
            ).fetchall()

    def matches(self) -> list[tuple]:
        with self.connection() as conn:
            return conn.execute(
                "SELECT match_id, tournament_id, match_title, match_date "
                "FROM match_fixtures ORDER BY match_id"
            ).fetchall()

    def stats(self) -> list[tuple]:
        with self.connection() as conn:
            return conn.execute(
                "SELECT stat_id, match_id, stat_type, stat_value "
                "FROM player_stats ORDER BY stat_id"
            ).fetchall()

    def joined(self) -> list[tuple]:
        with self.connection() as conn:
            return conn.execute("""
                SELECT m.match_id, t.tournament_name, m.match_title,
                       m.match_date, p.stat_type, p.stat_value
                FROM tournaments AS t
                INNER JOIN match_fixtures AS m
                    ON t.tournament_id = m.tournament_id
                INNER JOIN player_stats AS p
                    ON m.match_id = p.match_id
                ORDER BY m.match_id, p.stat_id
            """).fetchall()

    def matches_for_dropdown(self) -> list[tuple]:
        with self.connection() as conn:
            return conn.execute("""
                SELECT m.match_id, m.match_title, t.tournament_name
                FROM match_fixtures AS m
                INNER JOIN tournaments AS t
                    ON m.tournament_id = t.tournament_id
                ORDER BY m.match_id
            """).fetchall()

    def stats_for_dropdown(self) -> list[tuple]:
        with self.connection() as conn:
            return conn.execute("""
                SELECT p.stat_id, p.match_id, p.stat_type, p.stat_value,
                       m.match_title
                FROM player_stats AS p
                INNER JOIN match_fixtures AS m ON p.match_id = m.match_id
                ORDER BY p.stat_id
            """).fetchall()

    def add_match_and_stat(
        self, tournament_name: str, admin_email: str, match_title: str,
        match_date: str, stat_type: str, stat_value: float,
    ) -> tuple[int, int]:
        """Atomically reuse/create tournament, then insert one match and one stat."""
        name = tournament_name.strip()
        email = admin_email.strip()
        title = match_title.strip()
        stat = stat_type.strip()
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT tournament_id, admin_email FROM tournaments "
                "WHERE tournament_name = ?",
                (name,),
            ).fetchone()
            if existing:
                tournament_id, stored_email = existing
                if stored_email.casefold() != email.casefold():
                    raise ValueError(
                        "This tournament already exists with a different admin email. "
                        "Use the registered email; the existing record was not changed."
                    )
            else:
                cur = conn.execute(
                    "INSERT INTO tournaments (tournament_name, admin_email) VALUES (?, ?)",
                    (name, email),
                )
                tournament_id = int(cur.lastrowid)

            cur = conn.execute(
                "INSERT INTO match_fixtures "
                "(tournament_id, match_title, match_date) VALUES (?, ?, ?)",
                (tournament_id, title, match_date),
            )
            match_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO player_stats (match_id, stat_type, stat_value) VALUES (?, ?, ?)",
                (match_id, stat, stat_value),
            )
            return int(tournament_id), match_id

    def delete_tournament(self, tournament_id: int) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM tournaments WHERE tournament_id = ?", (tournament_id,)
            )
            return cur.rowcount

    def delete_match(self, match_id: int) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM match_fixtures WHERE match_id = ?", (match_id,)
            )
            return cur.rowcount

    def delete_stat(self, stat_id: int) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM player_stats WHERE stat_id = ?", (stat_id,)
            )
            return cur.rowcount


# ---------------------------- Validation ----------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(value: str) -> bool:
    return bool(EMAIL_RE.fullmatch(value.strip()))


def validate_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def validate_form(
    tournament_name: str, admin_email: str, match_title: str,
    match_date: str, stat_type: str, stat_value: str,
) -> tuple[bool, float | None, str]:
    fields = {
        "Tournament name": tournament_name,
        "Admin email": admin_email,
        "Match title": match_title,
        "Match date": match_date,
        "Stat type": stat_type,
        "Stat value": stat_value,
    }
    for label, value in fields.items():
        if not value.strip():
            return False, None, f"{label} cannot be blank."

    if not validate_email(admin_email):
        return False, None, "Enter a valid administrator email address."
    if not validate_date(match_date):
        return False, None, "Enter a real date in YYYY-MM-DD format."

    try:
        number = float(stat_value.strip())
    except (TypeError, ValueError):
        return False, None, "Stat value must be numeric."
    if not math.isfinite(number):
        return False, None, "Stat value must be a finite number."
    if number < 0:
        return False, None, "Negative stat values are not allowed."
    return True, number, "Valid."


def display_value(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def hosted_colab() -> bool:
    return (
        "google.colab" in sys.modules
        or "COLAB_RELEASE_TAG" in os.environ
        or "COLAB_BACKEND_VERSION" in os.environ
    )


def graphical_display_available() -> bool:
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


# ------------------------------ GUI ---------------------------------

class EsportsDashboard:
    def __init__(self, root: tk.Tk, db: Database):
        self.root = root
        self.db = db
        self.closed = False
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(*MIN_SIZE)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.tournament_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.stat_type_var = tk.StringVar()
        self.stat_value_var = tk.StringVar()
        self.del_tournament_var = tk.StringVar()
        self.del_match_var = tk.StringVar()
        self.del_stat_var = tk.StringVar()
        self.tournament_ids: dict[str, int] = {}
        self.match_ids: dict[str, int] = {}
        self.stat_ids: dict[str, int] = {}

        self._configure_styles()
        self._build_layout()
        self.refresh_all()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Header.TLabel", background=BG, foreground=ACCENT,
                        font=("Segoe UI", 22, "bold"))
        style.configure("Section.TLabel", background=PANEL, foreground=ACCENT,
                        font=("Segoe UI", 11, "bold"))
        style.configure("TEntry", fieldbackground=CARD, foreground=TEXT,
                        insertcolor=TEXT, padding=7)
        style.configure("TCombobox", fieldbackground=CARD, background=CARD,
                        foreground=TEXT, padding=6, arrowcolor=ACCENT)
        style.map("TCombobox", fieldbackground=[("readonly", CARD)],
                  foreground=[("readonly", TEXT)])
        style.configure("Accent.TButton", background=ACCENT, foreground="#08131B",
                        padding=(12, 8), font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER)])
        style.configure("Danger.TButton", background=DANGER, foreground="white",
                        padding=(9, 6), font=("Segoe UI", 9, "bold"))
        style.map("Danger.TButton", background=[("active", "#FF8091")])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=CARD, foreground=TEXT,
                        padding=(14, 9), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#087D6C")],
                  foreground=[("selected", "white")])
        style.configure("Treeview", background=CARD, fieldbackground=CARD,
                        foreground=TEXT, rowheight=28, borderwidth=0,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#263A51",
                        foreground=ACCENT, padding=7,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#087D6C")],
                  foreground=[("selected", "white")])

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="ESPORTS DATABASE", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="TOURNAMENT MANAGEMENT  /  MATCH TRACKING  /  PLAYER STATISTICS",
            foreground=MUTED,
        ).pack(anchor="w", pady=(3, 0))

        self.summary_labels: dict[str, tk.Label] = {}
        summary = ttk.Frame(main)
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for col, label in enumerate(("Tournaments", "Match Fixtures", "Player Stat Lines")):
            summary.columnconfigure(col, weight=1)
            card = tk.Frame(summary, bg=PANEL, padx=14, pady=9,
                            highlightbackground="#34465C", highlightthickness=1)
            card.grid(row=0, column=col, sticky="ew", padx=4)
            tk.Label(card, text=label.upper(), bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            value = tk.Label(card, text="0", bg=PANEL, fg=ACCENT,
                             font=("Segoe UI", 21, "bold"))
            value.pack(anchor="w")
            self.summary_labels[label] = value

        management = ttk.Frame(main)
        management.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        management.columnconfigure(0, weight=2)
        management.columnconfigure(1, weight=1)
        self._build_insert_panel(management)
        self._build_delete_panel(management)
        self._build_tabs(main)
        ttk.Label(main, text="ESPORTS DATABASE MANAGEMENT SYSTEM  |  SQLITE  |  TKINTER",
                  foreground=MUTED).grid(row=4, column=0, sticky="w", pady=(9, 0))

    def _build_insert_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=13)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        panel.columnconfigure(1, weight=1)
        panel.columnconfigure(3, weight=1)
        ttk.Label(panel, text="ADD NEW RECORD", style="Section.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        fields = [
            ("Tournament Name", self.tournament_var),
            ("Admin Email", self.email_var),
            ("Match Title", self.title_var),
            ("Match Date (YYYY-MM-DD)", self.date_var),
            ("Stat Type", self.stat_type_var),
            ("Stat Value", self.stat_value_var),
        ]
        for i, (label, variable) in enumerate(fields):
            row, col = 1 + i // 2, (i % 2) * 2
            ttk.Label(panel, text=label, style="Panel.TLabel").grid(
                row=row, column=col, sticky="w", padx=(0, 5), pady=4)
            ttk.Entry(panel, textvariable=variable).grid(
                row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=4)
        ttk.Button(panel, text="ADD RECORD", style="Accent.TButton",
                   command=self.add_record).grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=(8, 0))

    def _build_delete_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=13)
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ttk.Label(panel, text="DELETE RECORDS", style="Section.TLabel").pack(
            anchor="w", pady=(0, 7))
        selectors = [
            ("Tournament", "tournament", self.del_tournament_var),
            ("Match Fixture", "match", self.del_match_var),
            ("Player Stat Line", "stat", self.del_stat_var),
        ]
        self.combos: dict[str, ttk.Combobox] = {}
        for label, kind, variable in selectors:
            ttk.Label(panel, text=label, style="Panel.TLabel").pack(anchor="w")
            combo = ttk.Combobox(panel, textvariable=variable, state="readonly")
            combo.pack(fill="x", pady=(2, 4))
            self.combos[kind] = combo
            ttk.Button(panel, text=f"DELETE {label.upper()}", style="Danger.TButton",
                       command=lambda selected_kind=kind: self.delete_selected(selected_kind)).pack(
                fill="x", pady=(0, 5))

    def _build_tabs(self, parent: ttk.Frame) -> None:
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=3, column=0, sticky="nsew")
        tabs = [
            ("COMBINED JOIN", ("match_id", "tournament_name", "match_title", "match_date", "stat_type", "stat_value"),
             ("Match ID", "Tournament Name", "Match Title", "Match Date", "Stat Type", "Stat Value"),
             (85, 190, 260, 110, 120, 90)),
            ("TOURNAMENTS", ("tournament_id", "tournament_name", "admin_email"),
             ("Tournament ID", "Tournament Name", "Admin Email"), (120, 280, 300)),
            ("MATCH FIXTURES", ("match_id", "tournament_id", "match_title", "match_date"),
             ("Match ID", "Tournament ID", "Match Title", "Match Date"), (100, 120, 350, 130)),
            ("PLAYER STATS", ("stat_id", "match_id", "stat_type", "stat_value"),
             ("Stat ID", "Match ID", "Stat Type", "Stat Value"), (100, 100, 230, 130)),
        ]
        self.trees: dict[str, ttk.Treeview] = {}
        for title, columns, headings, widths in tabs:
            frame = ttk.Frame(self.notebook, padding=8)
            self.notebook.add(frame, text=f"  {title}  ")
            tree = self._make_tree(frame, columns, headings, widths)
            self.trees[title] = tree

    @staticmethod
    def _make_tree(parent: ttk.Frame, columns: tuple, headings: tuple,
                   widths: tuple) -> ttk.Treeview:
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        for col, heading, width in zip(columns, headings, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=70, anchor="center", stretch=True)
        ybar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        xbar = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        tree.tag_configure("even", background="#223248")
        tree.tag_configure("odd", background="#293B52")
        return tree

    def add_record(self) -> None:
        values = (
            self.tournament_var.get(), self.email_var.get(), self.title_var.get(),
            self.date_var.get(), self.stat_type_var.get(), self.stat_value_var.get(),
        )
        valid, number, error = validate_form(*values)
        if not valid:
            messagebox.showwarning("Input Validation", error, parent=self.root)
            return
        try:
            tournament_id, match_id = self.db.add_match_and_stat(
                values[0].strip(), values[1].strip(), values[2].strip(),
                values[3].strip(), values[4].strip(), float(number),
            )
            self._clear_form()
            self.refresh_all()
            messagebox.showinfo(
                "Record Added",
                f"Record added successfully.\n\nTournament ID: {tournament_id}\nMatch ID: {match_id}",
                parent=self.root,
            )
        except ValueError as exc:
            messagebox.showwarning("Tournament Details", str(exc), parent=self.root)
        except sqlite3.Error as exc:
            messagebox.showerror("Database Error", f"Could not add record:\n{exc}", parent=self.root)

    def _clear_form(self) -> None:
        for variable in (self.tournament_var, self.email_var, self.title_var,
                         self.date_var, self.stat_type_var, self.stat_value_var):
            variable.set("")

    def delete_selected(self, kind: str) -> None:
        config = {
            "tournament": (self.del_tournament_var, self.tournament_ids,
                           "tournament", "Delete this tournament and all its matches and stats?"),
            "match": (self.del_match_var, self.match_ids,
                      "match fixture", "Delete this match and all its player stat lines?"),
            "stat": (self.del_stat_var, self.stat_ids,
                     "player stat line", "Delete only this player stat line?"),
        }
        variable, mapping, label, prompt = config[kind]
        selected = variable.get()
        if not selected or selected not in mapping:
            messagebox.showwarning("No Selection", f"Select a {label} first.", parent=self.root)
            # A stale selection should never be retained.
            self.refresh_all()
            return
        record_id = mapping[selected]
        if not messagebox.askyesno("Confirm Deletion", prompt, parent=self.root):
            return
        try:
            if kind == "tournament":
                deleted = self.db.delete_tournament(record_id)
            elif kind == "match":
                deleted = self.db.delete_match(record_id)
            else:
                deleted = self.db.delete_stat(record_id)
            # Refresh even when rowcount is zero (e.g. stale ID from another process).
            self.refresh_all()
            if deleted:
                messagebox.showinfo("Deleted", f"{label.title()} ID {record_id} deleted.", parent=self.root)
            else:
                messagebox.showwarning("Not Found", "That record no longer exists.", parent=self.root)
        except sqlite3.Error as exc:
            self.refresh_all()
            messagebox.showerror("Database Error", f"Could not delete record:\n{exc}", parent=self.root)

    @staticmethod
    def _fill_tree(tree: ttk.Treeview, rows: list[tuple]) -> None:
        tree.delete(*tree.get_children())
        for index, row in enumerate(rows):
            tree.insert("", "end", values=tuple(display_value(v) for v in row),
                        tags=("even" if index % 2 == 0 else "odd",))

    def refresh_views(self) -> None:
        self._fill_tree(self.trees["COMBINED JOIN"], self.db.joined())
        tournaments = self.db.tournaments()
        matches = self.db.matches()
        stats = self.db.stats()
        self._fill_tree(self.trees["TOURNAMENTS"], tournaments)
        self._fill_tree(self.trees["MATCH FIXTURES"], matches)
        self._fill_tree(self.trees["PLAYER STATS"], stats)
        self.summary_labels["Tournaments"].config(text=str(len(tournaments)))
        self.summary_labels["Match Fixtures"].config(text=str(len(matches)))
        self.summary_labels["Player Stat Lines"].config(text=str(len(stats)))

    def refresh_dropdowns(self) -> None:
        self.tournament_ids.clear()
        self.match_ids.clear()
        self.stat_ids.clear()

        tournament_options = []
        for tournament_id, name, _email in self.db.tournaments():
            label = f"ID: {tournament_id} | {name}"
            tournament_options.append(label)
            self.tournament_ids[label] = tournament_id
        self.combos["tournament"]["values"] = tournament_options
        self.del_tournament_var.set("")

        match_options = []
        for match_id, title, tournament_name in self.db.matches_for_dropdown():
            label = f"ID: {match_id} | {title} ({tournament_name})"
            match_options.append(label)
            self.match_ids[label] = match_id
        self.combos["match"]["values"] = match_options
        self.del_match_var.set("")

        stat_options = []
        for stat_id, match_id, stat_type, stat_value, match_title in self.db.stats_for_dropdown():
            label = (f"ID: {stat_id} | Match {match_id} | {stat_type}: "
                     f"{display_value(stat_value)} ({match_title})")
            stat_options.append(label)
            self.stat_ids[label] = stat_id
        self.combos["stat"]["values"] = stat_options
        self.del_stat_var.set("")

    def refresh_all(self) -> None:
        self.refresh_views()
        self.refresh_dropdowns()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.root.destroy()


def main() -> None:
    db = Database(database_path())
    root = None
    try:
        db.initialize()
        print(f"Database: {db.path}")
        print(f"Initial records (tournaments, matches, stats): {db.counts()}")

        if hosted_colab():
            print("Hosted Google Colab detected: SQLite is available, but standard hosted "
                  "Colab does not support native Tkinter desktop windows. Run the GUI locally.")
            return
        if not graphical_display_available():
            print("No graphical display detected. Database initialized; Tkinter GUI not started.")
            return
        try:
            root = tk.Tk()
            EsportsDashboard(root, db)
            root.mainloop()
        except tk.TclError as exc:
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass
            print(f"Tkinter could not start: {exc}")
    except (sqlite3.Error, OSError) as exc:
        print(f"Application/database error: {exc}")
    except Exception as exc:
        print(f"Unexpected application error: {exc}")
    finally:
        # Database connections are operation-scoped and already closed.
        # Destroy a partially created root if startup failed unexpectedly.
        if root is not None:
            try:
                if root.winfo_exists():
                    root.destroy()
            except tk.TclError:
                pass


if __name__ == "__main__":
    main()

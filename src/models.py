"""Data models and database manager for the sticky notes application."""

import json
import os
import sqlite3
from datetime import datetime
from typing import Optional

from src.utils import get_data_dir, get_db_path


# Color palette for note cards
NOTE_COLORS = {
    "default": ("rgba(49, 50, 68, 0.8)", "rgba(69, 71, 90, 0.5)"),
    "red": ("rgba(80, 35, 35, 0.8)", "rgba(120, 45, 45, 0.5)"),
    "orange": ("rgba(80, 55, 30, 0.8)", "rgba(120, 75, 35, 0.5)"),
    "yellow": ("rgba(75, 70, 25, 0.8)", "rgba(110, 100, 35, 0.5)"),
    "green": ("rgba(35, 70, 40, 0.8)", "rgba(45, 100, 55, 0.5)"),
    "blue": ("rgba(30, 45, 75, 0.8)", "rgba(40, 60, 110, 0.5)"),
    "purple": ("rgba(55, 35, 70, 0.8)", "rgba(85, 45, 105, 0.5)"),
}

COLOR_NAMES = {
    "default": "默认",
    "red": "红",
    "orange": "橙",
    "yellow": "黄",
    "green": "绿",
    "blue": "蓝",
    "purple": "紫",
}


class Note:
    """Represents a sticky note."""

    def __init__(
        self,
        id: Optional[int] = None,
        title: str = "新建便签",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        is_pinned: bool = False,
        opacity: float = 0.92,
        sort_order: int = 0,
        color: str = "default",
    ):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.id = id
        self.title = title
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.is_pinned = is_pinned
        self.opacity = opacity
        self.sort_order = sort_order
        self.color = color

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_pinned": self.is_pinned,
            "opacity": self.opacity,
            "sort_order": self.sort_order,
            "color": self.color,
        }

    @staticmethod
    def from_row(row: tuple) -> "Note":
        return Note(
            id=row[0],
            title=row[1],
            created_at=row[2],
            updated_at=row[3],
            is_pinned=bool(row[4]),
            opacity=row[5],
            sort_order=row[6],
            color=row[7] if len(row) > 7 else "default",
        )


class Todo:
    """Represents a todo item with due date and reminder support."""

    def __init__(
        self,
        id: Optional[int] = None,
        content: str = "",
        is_done: bool = False,
        done_at: Optional[str] = None,
        created_at: Optional[str] = None,
        note_id: Optional[int] = None,
        due_date: Optional[str] = None,
        reminder_time: Optional[str] = None,
        is_reminded: bool = False,
    ):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.id = id
        self.content = content
        self.is_done = is_done
        self.done_at = done_at
        self.created_at = created_at or now
        self.note_id = note_id
        self.due_date = due_date          # e.g. "2026-06-15"
        self.reminder_time = reminder_time  # e.g. "2026-06-15 09:00:00"
        self.is_reminded = is_reminded

    def is_overdue(self) -> bool:
        """Return True if due_date is in the past and not done."""
        if not self.due_date or self.is_done:
            return False
        try:
            due = datetime.strptime(self.due_date, "%Y-%m-%d")
            return due.date() < datetime.now().date()
        except ValueError:
            return False

    def mark_done(self):
        self.is_done = True
        self.done_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def mark_undone(self):
        self.is_done = False
        self.done_at = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "is_done": self.is_done,
            "done_at": self.done_at,
            "created_at": self.created_at,
            "note_id": self.note_id,
            "due_date": self.due_date,
            "reminder_time": self.reminder_time,
            "is_reminded": self.is_reminded,
        }

    @staticmethod
    def from_row(row: tuple) -> "Todo":
        return Todo(
            id=row[0],
            content=row[1],
            is_done=bool(row[2]),
            done_at=row[3],
            created_at=row[4],
            note_id=row[5],
            due_date=row[6] if len(row) > 6 else None,
            reminder_time=row[7] if len(row) > 7 else None,
            is_reminded=bool(row[8]) if len(row) > 8 else False,
        )


class DatabaseManager:
    """Manages SQLite database operations and JSON file storage."""

    def __init__(self):
        self.db_path = get_db_path()
        self.data_dir = get_data_dir()
        self.notes_dir = os.path.join(self.data_dir, "notes")
        self.images_dir = os.path.join(self.data_dir, "images")
        self._init_db()

    def _init_db(self):
        """Initialize the database and create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS notes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT DEFAULT '新建便签',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    is_pinned   INTEGER DEFAULT 0,
                    opacity     REAL DEFAULT 0.92,
                    sort_order  INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS todos (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    content     TEXT NOT NULL,
                    is_done     INTEGER DEFAULT 0,
                    done_at     TEXT,
                    created_at  TEXT NOT NULL,
                    note_id     INTEGER,
                    due_date        TEXT,
                    reminder_time   TEXT,
                    is_reminded     INTEGER DEFAULT 0,
                    FOREIGN KEY (note_id) REFERENCES notes(id)
                );
            """)
            # Migration: add color column if not exists
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN color TEXT DEFAULT 'default'")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists
            # Migration: add todo new columns if not exist
            for col, col_type in [
                ("due_date", "TEXT"),
                ("reminder_time", "TEXT"),
                ("is_reminded", "INTEGER DEFAULT 0"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE todos ADD COLUMN {col} {col_type}")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Column already exists
            conn.commit()

    # ─── Note Operations ───────────────────────────────────────────

    def create_note(self, title: str = "新建便签") -> Note:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO notes (title, created_at, updated_at) VALUES (?, ?, ?)",
                (title, now, now),
            )
            note_id = cursor.lastrowid
            conn.commit()
        # Create empty JSON file for note content
        self._save_note_content(note_id, {"content": "", "html": "", "images": []})
        return self.get_note(note_id)

    def get_note(self, note_id: int) -> Optional[Note]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
        return Note.from_row(row) if row else None

    def get_all_notes(self) -> list[Note]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM notes ORDER BY is_pinned DESC, sort_order ASC, updated_at DESC"
            )
            rows = cursor.fetchall()
        return [Note.from_row(row) for row in rows]

    def update_note(self, note: Note):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE notes SET title=?, updated_at=?, is_pinned=?, opacity=?, sort_order=?, color=?
                   WHERE id=?""",
                (note.title, now, int(note.is_pinned), note.opacity, note.sort_order, note.color, note.id),
            )
            conn.commit()

    def delete_note(self, note_id: int):
        # Delete JSON content file
        json_path = os.path.join(self.notes_dir, f"{note_id}.json")
        if os.path.exists(json_path):
            os.remove(json_path)
        # Delete from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()

    def get_note_content(self, note_id: int) -> dict:
        json_path = os.path.join(self.notes_dir, f"{note_id}.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"content": "", "html": "", "images": []}

    def save_note_content(self, note_id: int, content: str):
        """Save plain text content for a note."""
        data = self.get_note_content(note_id)
        data["content"] = content
        self._save_note_content(note_id, data)
        # Update timestamp
        note = self.get_note(note_id)
        if note:
            self.update_note(note)

    def save_note_html(self, note_id: int, html: str, images: list = None):
        """Save rich text HTML content for a note."""
        data = self.get_note_content(note_id)
        data["html"] = html
        if images is not None:
            data["images"] = images
        self._save_note_content(note_id, data)
        note = self.get_note(note_id)
        if note:
            self.update_note(note)

    def _save_note_content(self, note_id: int, data: dict):
        json_path = os.path.join(self.notes_dir, f"{note_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ─── Todo Operations ───────────────────────────────────────────

    def create_todo(self, content: str, note_id: Optional[int] = None,
                    due_date: Optional[str] = None,
                    reminder_time: Optional[str] = None) -> Todo:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO todos (content, created_at, note_id, due_date, reminder_time)
                   VALUES (?, ?, ?, ?, ?)""",
                (content, now, note_id, due_date, reminder_time),
            )
            todo_id = cursor.lastrowid
            conn.commit()
        return self.get_todo(todo_id)

    def get_todo(self, todo_id: int) -> Optional[Todo]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
            row = cursor.fetchone()
        return Todo.from_row(row) if row else None

    def get_active_todos(self) -> list[Todo]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM todos WHERE is_done = 0 ORDER BY due_date ASC NULLS LAST, created_at DESC"
            )
            rows = cursor.fetchall()
        return [Todo.from_row(row) for row in rows]

    def get_completed_todos(self) -> list[Todo]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM todos WHERE is_done = 1 ORDER BY done_at DESC"
            )
            rows = cursor.fetchall()
        return [Todo.from_row(row) for row in rows]

    def get_todos_to_remind(self) -> list[Todo]:
        """Return todos whose reminder_time has passed and not yet reminded."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT * FROM todos
                   WHERE is_done = 0 AND is_reminded = 0
                     AND reminder_time IS NOT NULL
                     AND reminder_time <= ?""",
                (now_str,),
            )
            rows = cursor.fetchall()
        return [Todo.from_row(row) for row in rows]

    def mark_reminded(self, todo_id: int):
        """Mark a todo as already reminded."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE todos SET is_reminded = 1 WHERE id = ?", (todo_id,)
            )
            conn.commit()

    def update_todo(self, todo: Todo):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE todos SET content=?, is_done=?, done_at=?, note_id=?,
                      due_date=?, reminder_time=?, is_reminded=?
                   WHERE id=?""",
                (todo.content, int(todo.is_done), todo.done_at, todo.note_id,
                 todo.due_date, todo.reminder_time, int(todo.is_reminded), todo.id),
            )
            conn.commit()

    def toggle_todo(self, todo_id: int, is_done: bool):
        """Toggle a todo's completion status."""
        todo = self.get_todo(todo_id)
        if todo:
            if is_done:
                todo.mark_done()
            else:
                todo.mark_undone()
            self.update_todo(todo)

    def delete_todo(self, todo_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()

    def clear_completed_todos(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM todos WHERE is_done = 1")
            conn.commit()
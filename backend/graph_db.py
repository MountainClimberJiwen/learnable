#!/usr/bin/env python3
"""
Learnable Graph DB — Lightweight SQLite-based graph storage.

Designed for future Mac desktop app compatibility.
Single-file database, zero external dependencies (except sqlite3 stdlib).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class GraphDB:
    """Embedded graph database using SQLite."""

    def __init__(self, db_path: str = "learnable.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    parent_id TEXT,
                    level INTEGER DEFAULT 0,
                    x REAL DEFAULT 0,
                    y REAL DEFAULT 0,
                    zoom_threshold REAL DEFAULT 0.0,
                    detail_json TEXT,
                    color_index INTEGER DEFAULT 0,
                    expanded INTEGER DEFAULT 0,
                    created_at INTEGER,
                    updated_at INTEGER,
                    FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);
                CREATE INDEX IF NOT EXISTS idx_nodes_level ON nodes(level);

                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    created_at INTEGER,
                    UNIQUE(from_id, to_id),
                    FOREIGN KEY (from_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (to_id) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
                CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id);

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    root_topic TEXT NOT NULL,
                    camera_x REAL DEFAULT 0,
                    camera_y REAL DEFAULT 0,
                    camera_zoom REAL DEFAULT 0.3,
                    created_at INTEGER,
                    updated_at INTEGER
                );

                CREATE TABLE IF NOT EXISTS node_positions (
                    session_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    x REAL DEFAULT 0,
                    y REAL DEFAULT 0,
                    PRIMARY KEY (session_id, node_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def insert_node(
        self,
        node_id: str,
        label: str,
        parent_id: str | None = None,
        level: int = 0,
        x: float = 0,
        y: float = 0,
        zoom_threshold: float = 0.0,
        detail: dict | None = None,
        color_index: int = 0,
        expanded: bool = False,
    ) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO nodes
                (id, label, parent_id, level, x, y, zoom_threshold, detail_json,
                 color_index, expanded, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id, label, parent_id, level, x, y, zoom_threshold,
                    json.dumps(detail, ensure_ascii=False) if detail else None,
                    color_index, 1 if expanded else 0, now, now,
                ),
            )
            conn.commit()

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
            if not row:
                return None
            return self._row_to_node(row)

    def get_nodes_by_parent(self, parent_id: str | None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if parent_id is None:
                rows = conn.execute("SELECT * FROM nodes WHERE parent_id IS NULL").fetchall()
            else:
                rows = conn.execute("SELECT * FROM nodes WHERE parent_id = ?", (parent_id,)).fetchall()
            return [self._row_to_node(r) for r in rows]

    def get_all_nodes(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM nodes").fetchall()
            return [self._row_to_node(r) for r in rows]

    def update_node_position(self, node_id: str, x: float, y: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE nodes SET x = ?, y = ?, updated_at = ? WHERE id = ?",
                (x, y, int(time.time()), node_id),
            )
            conn.commit()

    def update_node_detail(self, node_id: str, detail: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE nodes SET detail_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(detail, ensure_ascii=False), int(time.time()), node_id),
            )
            conn.commit()

    def delete_node(self, node_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            conn.commit()

    def delete_node_tree(self, node_id: str) -> None:
        """Delete node and all descendants (cascade)."""
        with self._connect() as conn:
            to_delete = [node_id]
            cursor = 0
            while cursor < len(to_delete):
                current = to_delete[cursor]
                children = conn.execute(
                    "SELECT id FROM nodes WHERE parent_id = ?", (current,)
                ).fetchall()
                to_delete.extend([c["id"] for c in children])
                cursor += 1
            conn.executemany("DELETE FROM nodes WHERE id = ?", [(i,) for i in to_delete])
            conn.commit()

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    def insert_edge(self, from_id: str, to_id: str) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO edges (from_id, to_id, created_at) VALUES (?, ?, ?)",
                (from_id, to_id, now),
            )
            conn.commit()

    def get_edges_from(self, from_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM edges WHERE from_id = ?", (from_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_edges(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM edges").fetchall()
            return [dict(r) for r in rows]

    def delete_edge(self, from_id: str, to_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM edges WHERE from_id = ? AND to_id = ?", (from_id, to_id))
            conn.commit()

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    def create_session(self, session_id: str, root_topic: str) -> None:
        now = int(time.time())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (id, root_topic, camera_x, camera_y, camera_zoom, created_at, updated_at)
                VALUES (?, ?, 0, 0, 0.3, ?, ?)
                """,
                (session_id, root_topic, now, now),
            )
            conn.commit()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
            return [dict(r) for r in rows]

    def update_session_camera(
        self, session_id: str, x: float, y: float, zoom: float
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET camera_x = ?, camera_y = ?, camera_zoom = ?, updated_at = ? WHERE id = ?",
                (x, y, zoom, int(time.time()), session_id),
            )
            conn.commit()

    def delete_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_graph(self) -> dict[str, Any]:
        """Export entire graph as JSON (for backup or migration)."""
        return {
            "nodes": self.get_all_nodes(),
            "edges": self.get_all_edges(),
            "sessions": self.list_sessions(),
        }

    def import_graph(self, data: dict[str, Any]) -> None:
        """Import graph from JSON."""
        with self._connect() as conn:
            for n in data.get("nodes", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO nodes
                    (id, label, parent_id, level, x, y, zoom_threshold, detail_json,
                     color_index, expanded, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        n["id"], n["label"], n.get("parent_id"), n.get("level", 0),
                        n.get("x", 0), n.get("y", 0), n.get("zoom_threshold", 0),
                        json.dumps(n.get("detail"), ensure_ascii=False) if n.get("detail") else None,
                        n.get("color_index", 0), 1 if n.get("expanded") else 0,
                        n.get("created_at", int(time.time())), n.get("updated_at", int(time.time())),
                    ),
                )
            for e in data.get("edges", []):
                conn.execute(
                    "INSERT OR IGNORE INTO edges (from_id, to_id, created_at) VALUES (?, ?, ?)",
                    (e["from_id"], e["to_id"], e.get("created_at", int(time.time()))),
                )
            for s in data.get("sessions", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sessions
                    (id, root_topic, camera_x, camera_y, camera_zoom, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s["id"], s["root_topic"], s.get("camera_x", 0), s.get("camera_y", 0),
                        s.get("camera_zoom", 0.3), s.get("created_at", int(time.time())),
                        s.get("updated_at", int(time.time())),
                    ),
                )
            conn.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_node(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["detail"] = json.loads(d.pop("detail_json")) if d.get("detail_json") else None
        d["expanded"] = bool(d.pop("expanded", 0))
        return d


# ------------------------------------------------------------------
# Singleton instance
# ------------------------------------------------------------------

_db: GraphDB | None = None


def get_db(db_path: str = "learnable.db") -> GraphDB:
    global _db
    if _db is None:
        _db = GraphDB(db_path)
    return _db

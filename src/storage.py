import sqlite3
from typing import Any


class KGStore:
    """Read/write access to the mempalace SQLite knowledge graph."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._mem_conn: sqlite3.Connection | None = None
        if path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row

    def _get_conn(self) -> tuple[sqlite3.Connection, bool]:
        """Return (connection, should_close_after_use)."""
        if self._mem_conn is not None:
            return self._mem_conn, False
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn, True

    def get_graph(self, show_invalidated: bool = False) -> dict:
        conn, close = self._get_conn()
        try:
            triples = conn.execute(
                "SELECT id, subject, predicate, object, confidence "
                "FROM triples WHERE valid_to IS NULL"
            ).fetchall()

            active_ids: set[str] = set()
            for t in triples:
                active_ids.add(t["subject"])
                active_ids.add(t["object"])

            all_entities = conn.execute(
                "SELECT id, name, type, properties, created_at FROM entities"
            ).fetchall()
            entities = (
                all_entities
                if show_invalidated
                else [e for e in all_entities if e["id"] in active_ids]
            )

            indegree: dict[str, int] = {}
            for t in triples:
                indegree[t["object"]] = indegree.get(t["object"], 0) + 1

            seen: set[str] = set()
            nodes = []
            for e in entities:
                if e["id"] in seen:
                    continue
                seen.add(e["id"])
                nodes.append({
                    "id":         e["id"],
                    "name":       e["name"],
                    "type":       e["type"] or "unknown",
                    "created_at": e["created_at"],
                    "is_root":    indegree.get(e["id"], 0) == 0,
                })

            edges = [
                {
                    "id":         t["id"],
                    "subject":    t["subject"],
                    "predicate":  t["predicate"],
                    "object":     t["object"],
                    "confidence": t["confidence"],
                }
                for t in triples
            ]
            return {"nodes": nodes, "edges": edges}
        finally:
            if close:
                conn.close()

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        conn, close = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            if close:
                conn.close()

    def get_entity_relations(self, entity_id: str) -> dict:
        conn, close = self._get_conn()
        try:
            outgoing = conn.execute(
                """
                SELECT t.predicate, t.object, t.confidence, t.valid_from, t.valid_to,
                       t.source_closet, t.source_file,
                       e.name AS object_name, e.type AS object_type
                FROM triples t LEFT JOIN entities e ON t.object = e.id
                WHERE t.subject = ? AND t.valid_to IS NULL
                ORDER BY t.predicate
                """,
                (entity_id,),
            ).fetchall()
            incoming = conn.execute(
                """
                SELECT t.subject, t.predicate, t.confidence, t.valid_from, t.valid_to,
                       t.source_closet, t.source_file,
                       e.name AS subject_name, e.type AS subject_type
                FROM triples t LEFT JOIN entities e ON t.subject = e.id
                WHERE t.object = ? AND t.valid_to IS NULL
                ORDER BY t.predicate
                """,
                (entity_id,),
            ).fetchall()
            closets: set[str] = set()
            for t in list(outgoing) + list(incoming):
                if t["source_closet"]:
                    closets.add(t["source_closet"])
            return {
                "outgoing": [dict(t) for t in outgoing],
                "incoming": [dict(t) for t in incoming],
                "closets":  sorted(closets),
            }
        finally:
            if close:
                conn.close()

    def get_triple(
        self, triple_id: str
    ) -> tuple[dict | None, dict | None, dict | None]:
        conn, close = self._get_conn()
        try:
            triple = conn.execute(
                "SELECT * FROM triples WHERE id = ?", (triple_id,)
            ).fetchone()
            if not triple:
                return None, None, None
            subject = conn.execute(
                "SELECT id, name, type FROM entities WHERE id = ?",
                (triple["subject"],),
            ).fetchone()
            obj = conn.execute(
                "SELECT id, name, type FROM entities WHERE id = ?",
                (triple["object"],),
            ).fetchone()
            return (
                dict(triple),
                dict(subject) if subject else None,
                dict(obj) if obj else None,
            )
        finally:
            if close:
                conn.close()

    def update_triple_wing(self, source: str, target: str) -> None:
        conn, close = self._get_conn()
        try:
            conn.execute(
                "UPDATE triples SET source_closet = ? || SUBSTR(source_closet, ?) "
                "WHERE source_closet LIKE ?",
                (target + "/", len(source) + 2, source + "/%"),
            )
            conn.commit()
        finally:
            if close:
                conn.close()

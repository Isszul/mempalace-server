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


# ── PalaceStore ────────────────────────────────────────────────────────────

from functools import cached_property
from pathlib import Path as _Path


class PalaceStore:
    """ChromaDB-backed palace: drawer storage and retrieval."""

    COLLECTION = "mempalace_drawers"

    def __init__(self, path: str | None = None) -> None:
        import chromadb
        if path is None:
            self._client = chromadb.EphemeralClient()
        else:
            self._client = chromadb.PersistentClient(path=path)

    @cached_property
    def _col(self):
        return self._client.get_or_create_collection(self.COLLECTION)

    # ── reads ──────────────────────────────────────────────────────────────

    def search(self, q: str, limit: int = 30) -> list[dict]:
        try:
            results = self._col.query(
                query_texts=[q],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []
        ids   = results["ids"][0]
        docs  = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]
        return [
            {
                "id":         doc_id,
                "content":    doc[:300],
                "wing":       meta.get("wing", "unknown"),
                "room":       meta.get("room", "unknown"),
                "source":     _Path(meta.get("source_file", "") or "").name,
                "similarity": round(max(0.0, 1.0 - dist / 2), 3),
            }
            for doc_id, doc, meta, dist in zip(ids, docs, metas, dists)
        ]

    def get_tree(self) -> dict:
        all_data = self._col.get(include=["metadatas"])
        wings_map: dict = {}
        for m in all_data["metadatas"]:
            w  = m.get("wing", "?")
            r  = m.get("room", "?")
            sf = m.get("source_file", "")
            wings_map.setdefault(w, {}).setdefault(r, {"count": 0, "files": set()})
            wings_map[w][r]["count"] += 1
            fname = sf.rsplit("/", 1)[-1]
            if fname:
                wings_map[w][r]["files"].add(fname)
        wings = [
            {
                "name": w_name,
                "rooms": [
                    {
                        "name":         r_name,
                        "drawer_count": data["count"],
                        "sources":      sorted(data["files"])[:8],
                    }
                    for r_name, data in sorted(rooms.items())
                ],
            }
            for w_name, rooms in sorted(wings_map.items())
        ]
        return {"wings": wings, "total_drawers": len(all_data["metadatas"])}

    def get_drawers(
        self,
        wing: str | None,
        room: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        where: dict = {}
        if wing and room:
            where = {"$and": [{"wing": wing}, {"room": room}]}
        elif wing:
            where = {"wing": wing}
        elif room:
            where = {"room": room}
        kwargs: dict = {
            "include": ["documents", "metadatas"],
            "limit":   limit,
            "offset":  offset,
        }
        if where:
            kwargs["where"] = where
        results = self._col.get(**kwargs)
        ids = results.get("ids", [])
        return [
            {
                "id":      ids[i] if i < len(ids) else None,
                "content": doc,
                "wing":    meta.get("wing"),
                "room":    meta.get("room"),
                "source":  meta.get("source_file"),
            }
            for i, (doc, meta) in enumerate(
                zip(results["documents"], results["metadatas"])
            )
        ]

    def get_drawer_by_id(self, drawer_id: str) -> dict | None:
        results = self._col.get(ids=[drawer_id], include=["documents", "metadatas"])
        if not results["ids"]:
            return None
        return {
            "id":      drawer_id,
            "content": results["documents"][0],
            "wing":    results["metadatas"][0].get("wing"),
            "room":    results["metadatas"][0].get("room"),
            "source":  results["metadatas"][0].get("source_file"),
        }

    def get_source_drawer(self, source_closet: str) -> str | None:
        """Fetch the drawer best matching source_closet (for triple detail)."""
        try:
            where: dict = {}
            if "/" in source_closet:
                where = {"wing": source_closet.split("/")[0]}
            results = self._col.query(
                query_texts=[source_closet],
                n_results=1,
                where=where or None,
                include=["documents"],
            )
            if results["documents"] and results["documents"][0]:
                return results["documents"][0][0]
            return None
        except Exception:
            return None

    # ── mutations ──────────────────────────────────────────────────────────

    def merge_wings(self, source: str, target: str) -> int:
        src = self._col.get(where={"wing": source}, include=["metadatas", "documents"])
        moved = 0
        for i, doc_id in enumerate(src["ids"]):
            meta = {**src["metadatas"][i], "wing": target}
            self._col.update(ids=[doc_id], metadatas=[meta])
            moved += 1
        return moved

    def dedupe_wing(self, wing: str) -> dict:
        src = self._col.get(where={"wing": wing}, include=["documents"])
        seen: dict[str, str] = {}
        dup_ids: list[str] = []
        for doc_id, doc in zip(src["ids"], src["documents"]):
            if doc in seen:
                dup_ids.append(doc_id)
            else:
                seen[doc] = doc_id
        if dup_ids:
            self._col.delete(ids=dup_ids)
        return {"removed": len(dup_ids), "kept": len(seen)}

    def delete_wing(self, wing: str) -> int:
        src = self._col.get(where={"wing": wing}, include=[])
        if src["ids"]:
            self._col.delete(ids=src["ids"])
        return len(src["ids"])

    def delete_room(self, wing: str, room: str) -> int:
        src = self._col.get(
            where={"$and": [{"wing": wing}, {"room": room}]}, include=[]
        )
        if src["ids"]:
            self._col.delete(ids=src["ids"])
        return len(src["ids"])

    def delete_drawer(self, drawer_id: str) -> None:
        self._col.delete(ids=[drawer_id])

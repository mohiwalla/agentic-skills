#!/usr/bin/env python3
"""Azure Boards REST API helper — one safe CLI for agents.

Uses the Azure DevOps REST API directly (no az-cli dependency at runtime).
Mirrors the clockify_api.py pattern: argparse subcommands, JSON output,
env-var config, zero third-party deps.
"""

import argparse
import base64
import json
import os
import ssl
import time
from urllib import error, parse, request

API_VERSION = "7.1"

# ── relation type aliases (agent-friendly → API ref name) ──────────────
RELATION_ALIASES: dict[str, str] = {
    "parent": "System.LinkTypes.Hierarchy-Reverse",
    "child": "System.LinkTypes.Hierarchy-Forward",
    "related": "System.LinkTypes.Related",
    "predecessor": "System.LinkTypes.Dependency-Reverse",
    "successor": "System.LinkTypes.Dependency-Forward",
}


def _compact(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _parse_bool(value: str | None):
    if value is None:
        return None
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y"}:
        return True
    if v in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected boolean (true/false)")


def _parse_fields(raw: list[str] | None) -> dict[str, str]:
    """Turn ["Key=Val", "Key2=Val2"] into a dict."""
    if not raw:
        return {}
    out: dict[str, str] = {}
    for pair in raw:
        if "=" not in pair:
            raise argparse.ArgumentTypeError(f"Field must be Key=Value, got: {pair}")
        k, v = pair.split("=", 1)
        out[k.strip()] = v.strip()
    return out


# ═══════════════════════════════════════════════════════════════════════
#  Client
# ═══════════════════════════════════════════════════════════════════════

class AzureBoardsClient:
    def __init__(self, org: str, project: str, pat: str):
        self.org = org
        self.project = project
        self._auth = "Basic " + base64.b64encode((":" + pat).encode()).decode()

    # ── low-level ──────────────────────────────────────────────────────

    def _url(self, path: str, query: dict | None = None) -> str:
        url = f"https://dev.azure.com/{self.org}/{parse.quote(self.project, safe='')}/{path}"
        q = {"api-version": API_VERSION}
        if query:
            q.update({k: v for k, v in query.items() if v is not None})
        return url + "?" + parse.urlencode(q, doseq=True)

    def _request(
        self,
        method: str,
        path: str,
        payload=None,
        query: dict | None = None,
        content_type: str = "application/json",
    ):
        data = None
        headers = {"Authorization": self._auth, "Content-Type": content_type}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        url = self._url(path, query)
        ctx = ssl.create_default_context()

        last_exc: Exception | None = None
        for attempt in range(3):
            req = request.Request(url, data=data, headers=headers, method=method)
            try:
                with request.urlopen(req, context=ctx) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body) if body else {"status": resp.status}
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8")
                try:
                    parsed = json.loads(detail)
                except Exception:
                    parsed = {"message": detail}
                raise RuntimeError(f"Azure DevOps API {exc.code}: {json.dumps(parsed)}") from exc
            except (ConnectionError, OSError) as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Azure DevOps API connection failed after 3 attempts: {last_exc}") from last_exc

    def _patch_work_item(self, item_id: int, ops: list[dict]):
        return self._request(
            "PATCH",
            f"_apis/wit/workitems/{item_id}",
            payload=ops,
            content_type="application/json-patch+json",
        )

    # ── iterations ─────────────────────────────────────────────────────

    def list_iterations(self, team: str | None = None, timeframe: str | None = None):
        path = "_apis/work/teamsettings/iterations"
        if team:
            path = f"{parse.quote(team, safe='')}/_apis/work/teamsettings/iterations"
        query = _compact({"$timeframe": timeframe}) if timeframe else None
        return self._request("GET", path, query=query)

    def get_current_iteration(self, team: str | None = None) -> dict | None:
        data = self.list_iterations(team=team, timeframe="current")
        items = data.get("value", [])
        return items[0] if items else None

    def get_latest_iteration(self, team: str | None = None) -> dict | None:
        """Return the current iteration, or the most recent past one."""
        current = self.get_current_iteration(team=team)
        if current:
            return current
        data = self.list_iterations(team=team)
        items = data.get("value", [])
        return items[-1] if items else None

    # ── work items: read ───────────────────────────────────────────────

    def get_work_item(self, item_id: int, expand: str | None = None):
        query = _compact({"$expand": expand or "relations"})
        return self._request("GET", f"_apis/wit/workitems/{item_id}", query=query)

    def query_wiql(self, wiql: str, top: int | None = None):
        payload: dict = {"query": wiql}
        query = _compact({"$top": str(top)}) if top else None
        result = self._request("POST", "_apis/wit/wiql", payload=payload, query=query)
        return result

    def get_work_items_batch(self, ids: list[int], fields: list[str] | None = None):
        if not ids:
            return {"count": 0, "value": []}
        query: dict = {"ids": ",".join(str(i) for i in ids)}
        if fields:
            query["fields"] = ",".join(fields)
        query["$expand"] = "relations"
        return self._request("GET", "_apis/wit/workitems", query=query)

    # ── work items: create ─────────────────────────────────────────────

    def create_work_item(
        self,
        work_item_type: str,
        title: str,
        description: str | None = None,
        iteration: str | None = None,
        area: str | None = None,
        assigned_to: str | None = None,
        state: str | None = None,
        reason: str | None = None,
        tags: str | None = None,
        fields: dict[str, str] | None = None,
        parent_id: int | None = None,
    ):
        ops: list[dict] = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
        ]
        if description:
            ops.append({"op": "add", "path": "/fields/System.Description", "value": description})
        if iteration:
            ops.append({"op": "add", "path": "/fields/System.IterationPath", "value": iteration})
        if area:
            ops.append({"op": "add", "path": "/fields/System.AreaPath", "value": area})
        if assigned_to:
            ops.append({"op": "add", "path": "/fields/System.AssignedTo", "value": assigned_to})
        if state:
            ops.append({"op": "add", "path": "/fields/System.State", "value": state})
        if reason:
            ops.append({"op": "add", "path": "/fields/System.Reason", "value": reason})
        if tags:
            ops.append({"op": "add", "path": "/fields/System.Tags", "value": tags})
        for k, v in (fields or {}).items():
            ops.append({"op": "add", "path": f"/fields/{k}", "value": v})

        if parent_id:
            parent_url = f"https://dev.azure.com/{self.org}/_apis/wit/workItems/{parent_id}"
            ops.append({
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": parent_url,
                },
            })

        safe_type = parse.quote(work_item_type, safe="")
        return self._request(
            "POST",
            f"_apis/wit/workitems/${safe_type}",
            payload=ops,
            content_type="application/json-patch+json",
        )

    # ── work items: update ─────────────────────────────────────────────

    def update_work_item(
        self,
        item_id: int,
        title: str | None = None,
        description: str | None = None,
        iteration: str | None = None,
        area: str | None = None,
        assigned_to: str | None = None,
        state: str | None = None,
        reason: str | None = None,
        tags: str | None = None,
        fields: dict[str, str] | None = None,
    ):
        ops: list[dict] = []
        if title:
            ops.append({"op": "replace", "path": "/fields/System.Title", "value": title})
        if description:
            ops.append({"op": "replace", "path": "/fields/System.Description", "value": description})
        if iteration:
            ops.append({"op": "replace", "path": "/fields/System.IterationPath", "value": iteration})
        if area:
            ops.append({"op": "replace", "path": "/fields/System.AreaPath", "value": area})
        if assigned_to:
            ops.append({"op": "replace", "path": "/fields/System.AssignedTo", "value": assigned_to})
        if state:
            ops.append({"op": "replace", "path": "/fields/System.State", "value": state})
        if reason:
            ops.append({"op": "replace", "path": "/fields/System.Reason", "value": reason})
        if tags is not None:
            ops.append({"op": "replace", "path": "/fields/System.Tags", "value": tags})
        for k, v in (fields or {}).items():
            ops.append({"op": "replace", "path": f"/fields/{k}", "value": v})
        if not ops:
            raise RuntimeError("No fields to update — provide at least one option.")
        return self._patch_work_item(item_id, ops)

    # ── work items: delete ─────────────────────────────────────────────

    def delete_work_item(self, item_id: int, destroy: bool = False):
        query = _compact({"destroy": "true" if destroy else None})
        return self._request("DELETE", f"_apis/wit/workitems/{item_id}", query=query)

    # ── relations ──────────────────────────────────────────────────────

    def add_relation(self, item_id: int, relation_type: str, target_id: int):
        rel = RELATION_ALIASES.get(relation_type, relation_type)
        target_url = f"https://dev.azure.com/{self.org}/_apis/wit/workItems/{target_id}"
        ops = [{"op": "add", "path": "/relations/-", "value": {"rel": rel, "url": target_url}}]
        return self._patch_work_item(item_id, ops)

    def remove_relation(self, item_id: int, relation_index: int):
        ops = [{"op": "remove", "path": f"/relations/{relation_index}"}]
        return self._patch_work_item(item_id, ops)

    # ── comments ───────────────────────────────────────────────────────

    def add_comment(self, item_id: int, text: str):
        return self._request(
            "POST",
            f"_apis/wit/workitems/{item_id}/comments",
            payload={"text": text},
            query={"api-version": "7.1-preview.4"},
        )

    def list_comments(self, item_id: int, top: int | None = None):
        query: dict = {"api-version": "7.1-preview.4"}
        if top:
            query["$top"] = str(top)
        return self._request("GET", f"_apis/wit/workitems/{item_id}/comments", query=query)


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def build_parser():
    p = argparse.ArgumentParser(description="Azure Boards REST API helper")
    p.add_argument("--org", default=os.getenv("AZURE_DEVOPS_ORG"))
    p.add_argument("--project", default=os.getenv("AZURE_DEVOPS_PROJECT"))
    p.add_argument("--pat", default=os.getenv("AZURE_DEVOPS_PAT"))

    sub = p.add_subparsers(dest="command", required=True)

    # ── create ─────────────────────────────────────────────────────────
    c = sub.add_parser("create", help="Create a work item")
    c.add_argument("--type", required=True, help="Task, Bug, User Story, Issue, Epic, Feature")
    c.add_argument("--title", required=True)
    c.add_argument("--description", help="HTML description")
    c.add_argument("--iteration", help="Full path e.g. Project\\Sprint 1  (omit to auto-detect current)")
    c.add_argument("--area", help="Full area path e.g. Project\\TeamName")
    c.add_argument("--assigned-to")
    c.add_argument("--state")
    c.add_argument("--reason")
    c.add_argument("--tags", help="Semicolon-separated tags")
    c.add_argument("--field", action="append", default=[], help="Key=Value; repeatable")
    c.add_argument("--parent-id", type=int, help="Parent work item ID (auto-links)")

    # ── update ─────────────────────────────────────────────────────────
    u = sub.add_parser("update", help="Update a work item")
    u.add_argument("--id", required=True, type=int)
    u.add_argument("--title")
    u.add_argument("--description", help="HTML description")
    u.add_argument("--iteration")
    u.add_argument("--area")
    u.add_argument("--assigned-to")
    u.add_argument("--state")
    u.add_argument("--reason")
    u.add_argument("--tags", help="Semicolon-separated tags (replaces existing)")
    u.add_argument("--field", action="append", default=[], help="Key=Value; repeatable")

    # ── get ─────────────────────────────────────────────────────────────
    g = sub.add_parser("get", help="Show a single work item")
    g.add_argument("--id", required=True, type=int)
    g.add_argument("--expand", default="relations", help="none, relations, fields, links, all")

    # ── delete ──────────────────────────────────────────────────────────
    d = sub.add_parser("delete", help="Delete (recycle) a work item")
    d.add_argument("--id", required=True, type=int)
    d.add_argument("--destroy", type=_parse_bool, default=False, help="Permanently destroy")

    # ── query ───────────────────────────────────────────────────────────
    q = sub.add_parser("query", help="Run a WIQL query and return hydrated results")
    q.add_argument("--wiql", required=True, help="WIQL query string")
    q.add_argument("--top", type=int, help="Max rows from WIQL")
    q.add_argument("--fields", help="Comma-separated field names to return")

    # ── relation-add ────────────────────────────────────────────────────
    ra = sub.add_parser("relation-add", help="Add a link between work items")
    ra.add_argument("--id", required=True, type=int, help="Source work item")
    ra.add_argument("--relation-type", required=True, help="parent, child, related, predecessor, successor")
    ra.add_argument("--target-id", required=True, type=int)

    # ── relation-remove ─────────────────────────────────────────────────
    rr = sub.add_parser("relation-remove", help="Remove a relation by index")
    rr.add_argument("--id", required=True, type=int, help="Work item ID")
    rr.add_argument("--relation-index", required=True, type=int, help="Zero-based index in relations array")

    # ── comment-add ─────────────────────────────────────────────────────
    ca = sub.add_parser("comment-add", help="Add a comment (discussion) to a work item")
    ca.add_argument("--id", required=True, type=int)
    ca.add_argument("--text", required=True, help="HTML comment body")

    # ── comment-list ────────────────────────────────────────────────────
    cl = sub.add_parser("comment-list", help="List comments on a work item")
    cl.add_argument("--id", required=True, type=int)
    cl.add_argument("--top", type=int)

    # ── iterations ──────────────────────────────────────────────────────
    il = sub.add_parser("iterations", help="List iterations (sprints)")
    il.add_argument("--team", help="Team name (omit for default team)")
    il.add_argument("--timeframe", help="current, past, or future")

    # ── current-iteration ───────────────────────────────────────────────
    sub.add_parser("current-iteration", help="Show the current (or latest) iteration")

    return p


def _summarize_item(raw: dict) -> dict:
    """Extract the most useful fields into a flat dict for agent consumption."""
    fields = raw.get("fields", {})
    assigned = fields.get("System.AssignedTo")
    return _compact({
        "id": raw.get("id"),
        "rev": raw.get("rev"),
        "type": fields.get("System.WorkItemType"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "reason": fields.get("System.Reason"),
        "assigned_to": assigned.get("displayName") if isinstance(assigned, dict) else assigned,
        "iteration": fields.get("System.IterationPath"),
        "area": fields.get("System.AreaPath"),
        "tags": fields.get("System.Tags"),
        "priority": fields.get("Microsoft.VSTS.Common.Priority"),
        "description_snippet": (fields.get("System.Description") or "")[:200] or None,
        "parent": fields.get("System.Parent"),
        "url": raw.get("_links", {}).get("html", {}).get("href") or raw.get("url"),
        "relations": [
            _compact({
                "index": idx,
                "type": r.get("attributes", {}).get("name"),
                "rel": r.get("rel"),
                "target_url": r.get("url"),
            })
            for idx, r in enumerate(raw.get("relations") or [])
        ] or None,
    })


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    missing = []
    if not args.org:
        missing.append("AZURE_DEVOPS_ORG/--org")
    if not args.project:
        missing.append("AZURE_DEVOPS_PROJECT/--project")
    if not args.pat:
        missing.append("AZURE_DEVOPS_PAT/--pat")
    if missing:
        print(json.dumps({"error": "Missing required config", "missing": missing}, indent=2))
        return 2

    client = AzureBoardsClient(args.org, args.project, args.pat)

    cmd = args.command

    if cmd == "create":
        iteration = args.iteration
        if not iteration:
            it = client.get_latest_iteration()
            if it:
                iteration = it["path"]
        extra_fields = _parse_fields(args.field)
        out = client.create_work_item(
            work_item_type=args.type,
            title=args.title,
            description=args.description,
            iteration=iteration,
            area=args.area,
            assigned_to=args.assigned_to,
            state=args.state,
            reason=args.reason,
            tags=args.tags,
            fields=extra_fields,
            parent_id=args.parent_id,
        )
        out = _summarize_item(out)

    elif cmd == "update":
        extra_fields = _parse_fields(args.field)
        out = client.update_work_item(
            item_id=args.id,
            title=args.title,
            description=args.description,
            iteration=args.iteration,
            area=args.area,
            assigned_to=args.assigned_to,
            state=args.state,
            reason=args.reason,
            tags=args.tags,
            fields=extra_fields,
        )
        out = _summarize_item(out)

    elif cmd == "get":
        out = client.get_work_item(args.id, expand=args.expand)
        out = _summarize_item(out)

    elif cmd == "delete":
        out = client.delete_work_item(args.id, destroy=bool(args.destroy))

    elif cmd == "query":
        wiql_result = client.query_wiql(args.wiql, top=args.top)
        ids = [wi["id"] for wi in wiql_result.get("workItems", [])]
        if not ids:
            out = {"count": 0, "items": []}
        else:
            field_list = [f.strip() for f in args.fields.split(",")] if args.fields else None
            batch = client.get_work_items_batch(ids, fields=field_list)
            out = {
                "count": len(ids),
                "items": [_summarize_item(item) for item in batch.get("value", [])],
            }

    elif cmd == "relation-add":
        out = client.add_relation(args.id, args.relation_type, args.target_id)
        out = _summarize_item(out)

    elif cmd == "relation-remove":
        out = client.remove_relation(args.id, args.relation_index)
        out = _summarize_item(out)

    elif cmd == "comment-add":
        out = client.add_comment(args.id, args.text)

    elif cmd == "comment-list":
        out = client.list_comments(args.id, top=args.top)

    elif cmd == "iterations":
        out = client.list_iterations(team=args.team, timeframe=args.timeframe)

    elif cmd == "current-iteration":
        it = client.get_latest_iteration()
        out = it if it else {"error": "No iterations found"}

    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}, indent=2))
        return 1

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        raise SystemExit(1)

#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from urllib import parse, request, error


BASE_URL = "https://api.clockify.me/api/v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_none(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def parse_bool(value: str):
    if value is None:
        return None
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y"}:
        return True
    if v in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected boolean (true/false)")


class ClockifyClient:
    def __init__(self, api_key: str, workspace_id: str, user_id: str):
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.user_id = user_id

    def _url(self, path: str, query: dict | None = None) -> str:
        url = f"{BASE_URL}{path}"
        if query:
            filtered = {k: v for k, v in query.items() if v is not None}
            if filtered:
                url += "?" + parse.urlencode(filtered, doseq=True)
        return url

    def _request(self, method: str, path: str, payload: dict | None = None, query: dict | None = None):
        data = None
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = request.Request(
            self._url(path, query=query),
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                if not body:
                    return {"status": resp.status}
                return json.loads(body)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            try:
                parsed = json.loads(detail)
            except Exception:
                parsed = {"message": detail}
            raise RuntimeError(f"Clockify API {exc.code}: {json.dumps(parsed)}") from exc

    def start_timer(self, description: str, project_id: str | None = None, billable: bool | None = None):
        payload = clean_none(
            {
                "start": utc_now_iso(),
                "description": description,
                "projectId": project_id,
                "billable": billable,
            }
        )
        return self._request("POST", f"/workspaces/{self.workspace_id}/time-entries", payload=payload)

    def stop_timer(self):
        payload = {"end": utc_now_iso()}
        return self._request(
            "PATCH",
            f"/workspaces/{self.workspace_id}/user/{self.user_id}/time-entries",
            payload=payload,
        )

    def list_entries(
        self,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        in_progress: bool | None = None,
    ):
        query = clean_none(
            {
                "start": start,
                "end": end,
                "description": description,
                "page": page,
                "page-size": page_size,
                "in-progress": str(in_progress).lower() if in_progress is not None else None,
            }
        )
        return self._request(
            "GET",
            f"/workspaces/{self.workspace_id}/user/{self.user_id}/time-entries",
            query=query,
        )

    def get_entry(self, entry_id: str):
        return self._request("GET", f"/workspaces/{self.workspace_id}/time-entries/{entry_id}")

    def update_entry(
        self,
        entry_id: str,
        start: str,
        description: str | None = None,
        end: str | None = None,
        project_id: str | None = None,
        billable: bool | None = None,
    ):
        payload = clean_none(
            {
                "start": start,
                "description": description,
                "end": end,
                "projectId": project_id,
                "billable": billable,
            }
        )
        return self._request("PUT", f"/workspaces/{self.workspace_id}/time-entries/{entry_id}", payload=payload)

    def delete_entry(self, entry_id: str):
        return self._request("DELETE", f"/workspaces/{self.workspace_id}/time-entries/{entry_id}")

    def in_progress(self):
        return self._request("GET", f"/workspaces/{self.workspace_id}/time-entries/status/in-progress")


def build_parser():
    parser = argparse.ArgumentParser(description="Clockify API helper")
    parser.add_argument("--api-key", default=os.getenv("CLOCKIFY_API_KEY"))
    parser.add_argument("--workspace-id", default=os.getenv("CLOCKIFY_WORKSPACE_ID"))
    parser.add_argument("--user-id", default=os.getenv("CLOCKIFY_USER_ID"))
    parser.add_argument("--project-id-default", default=os.getenv("CLOCKIFY_PROJECT_ID"))

    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start a running timer")
    start.add_argument("--description", required=True)
    start.add_argument("--project-id")
    start.add_argument("--billable", type=parse_bool)

    sub.add_parser("stop", help="Stop the running timer")

    list_cmd = sub.add_parser("list", help="List time entries for user")
    list_cmd.add_argument("--start")
    list_cmd.add_argument("--end")
    list_cmd.add_argument("--description")
    list_cmd.add_argument("--page", type=int)
    list_cmd.add_argument("--page-size", type=int)
    list_cmd.add_argument("--in-progress", type=parse_bool)

    get_cmd = sub.add_parser("get", help="Get a single time entry")
    get_cmd.add_argument("--id", required=True)

    upd = sub.add_parser("update", help="Update a time entry")
    upd.add_argument("--id", required=True)
    upd.add_argument("--start", required=True, help="UTC timestamp, e.g. 2026-01-02T03:04:05Z")
    upd.add_argument("--description")
    upd.add_argument("--end")
    upd.add_argument("--project-id")
    upd.add_argument("--billable", type=parse_bool)

    delete_cmd = sub.add_parser("delete", help="Delete a time entry")
    delete_cmd.add_argument("--id", required=True)

    sub.add_parser("in-progress", help="List in-progress timers on workspace")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    missing = []
    if not args.api_key:
        missing.append("CLOCKIFY_API_KEY/--api-key")
    if not args.workspace_id:
        missing.append("CLOCKIFY_WORKSPACE_ID/--workspace-id")
    if not args.user_id:
        missing.append("CLOCKIFY_USER_ID/--user-id")
    if missing:
        print(json.dumps({"error": "Missing required config", "missing": missing}, indent=2))
        return 2

    client = ClockifyClient(args.api_key, args.workspace_id, args.user_id)

    if args.command == "start":
        project_id = args.project_id or args.project_id_default
        out = client.start_timer(description=args.description, project_id=project_id, billable=args.billable)
    elif args.command == "stop":
        out = client.stop_timer()
    elif args.command == "list":
        out = client.list_entries(
            start=args.start,
            end=args.end,
            description=args.description,
            page=args.page,
            page_size=args.page_size,
            in_progress=args.in_progress,
        )
    elif args.command == "get":
        out = client.get_entry(args.id)
    elif args.command == "update":
        out = client.update_entry(
            entry_id=args.id,
            start=args.start,
            description=args.description,
            end=args.end,
            project_id=args.project_id,
            billable=args.billable,
        )
    elif args.command == "delete":
        out = client.delete_entry(args.id)
    else:
        out = client.in_progress()

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        raise SystemExit(1)

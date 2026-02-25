"""Command-line interface for Grafana PDF Reporter.

Allows report generation, listing, and download from the terminal
without using the web frontend.

Usage:
    python -m backend.cli generate --dashboard <uid> [--panels 1,2,3]
    python -m backend.cli list [--status completed]
    python -m backend.cli download <report_id> [-o output.pdf]
    python -m backend.cli dashboards
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30


def _get_client(args: argparse.Namespace) -> httpx.Client:
    """Create an authenticated HTTP client."""
    client = httpx.Client(
        base_url=args.base_url,
        timeout=DEFAULT_TIMEOUT,
    )
    if args.token:
        client.headers["Authorization"] = f"Bearer {args.token}"
    return client


def _login(client: httpx.Client, username: str, password: str) -> str:
    """Authenticate and return a JWT access token.

    Args:
        client: HTTP client.
        username: User login name.
        password: User password.

    Returns:
        JWT access token string.

    Raises:
        SystemExit: On authentication failure.
    """
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    if response.status_code != 200:
        print(f"Login failed: {response.text}", file=sys.stderr)
        sys.exit(1)
    token: str = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------


def cmd_dashboards(args: argparse.Namespace) -> None:
    """List available Grafana dashboards."""
    client = _get_client(args)
    if args.username:
        _login(client, args.username, args.password)

    response = client.get("/api/v1/grafana/dashboards")
    if response.status_code != 200:
        print(f"Error: {response.text}", file=sys.stderr)
        sys.exit(1)

    dashboards: list[dict[str, Any]] = response.json()
    if args.json_output:
        print(json.dumps(dashboards, indent=2))
        return

    print(f"{'UID':<20} {'Title':<40} {'Tags'}")
    print("-" * 80)
    for d in dashboards:
        tags = ", ".join(d.get("tags", []))
        print(f"{d['uid']:<20} {d['title']:<40} {tags}")


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate a PDF report."""
    client = _get_client(args)
    if args.username:
        _login(client, args.username, args.password)

    panels = [int(p) for p in args.panels.split(",")] if args.panels else []

    payload: dict[str, Any] = {
        "dashboard_uid": args.dashboard,
        "panel_ids": panels,
        "time_range_from": args.time_from,
        "time_range_to": args.time_to,
    }
    if args.title:
        payload["title"] = args.title
    if args.orientation:
        payload["orientation"] = args.orientation
    if args.language:
        payload["language"] = args.language

    response = client.post("/api/v1/reports/generate", json=payload)
    if response.status_code not in (200, 202):
        print(f"Error: {response.text}", file=sys.stderr)
        sys.exit(1)

    report = response.json()
    report_id = report["id"]
    print(f"Report queued: {report_id}")

    if args.wait:
        print("Waiting for completion...", end="", flush=True)
        for _ in range(120):
            time.sleep(2)
            r = client.get(f"/api/v1/reports/{report_id}")
            if r.status_code == 200:
                status = r.json()["status"]
                if status == "completed":
                    print(f"\nReport completed: {report_id}")
                    if args.output:
                        _download_to_file(client, report_id, args.output)
                    return
                if status == "failed":
                    print(f"\nReport failed: {r.json().get('error_message', 'unknown')}", file=sys.stderr)
                    sys.exit(1)
            print(".", end="", flush=True)
        print("\nTimeout waiting for report.")
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List reports."""
    client = _get_client(args)
    if args.username:
        _login(client, args.username, args.password)

    params: dict[str, Any] = {"page": args.page, "per_page": args.per_page}
    if args.status:
        params["status"] = args.status

    response = client.get("/api/v1/reports", params=params)
    if response.status_code != 200:
        print(f"Error: {response.text}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    if args.json_output:
        print(json.dumps(data, indent=2))
        return

    items = data.get("items", [])
    print(f"{'ID':<38} {'Status':<12} {'Title':<30} {'Created'}")
    print("-" * 100)
    for r in items:
        print(
            f"{r['id']:<38} {r['status']:<12} "
            f"{r.get('title', '')[:30]:<30} {r.get('created_at', '')[:19]}"
        )
    print(f"\nPage {data['page']}/{data['pages']} — Total: {data['total']}")


def cmd_download(args: argparse.Namespace) -> None:
    """Download a report PDF."""
    client = _get_client(args)
    if args.username:
        _login(client, args.username, args.password)

    output = args.output or f"report_{args.report_id}.pdf"
    _download_to_file(client, args.report_id, output)


def _download_to_file(client: httpx.Client, report_id: str, output: str) -> None:
    """Download report PDF to a local file."""
    response = client.get(f"/api/v1/reports/{report_id}/download")
    if response.status_code != 200:
        print(f"Download error: {response.text}", file=sys.stderr)
        sys.exit(1)

    with open(output, "wb") as f:
        f.write(response.content)
    print(f"Downloaded: {output} ({len(response.content):,} bytes)")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show report statistics."""
    client = _get_client(args)
    if args.username:
        _login(client, args.username, args.password)

    response = client.get("/api/v1/reports/stats")
    if response.status_code != 200:
        print(f"Error: {response.text}", file=sys.stderr)
        sys.exit(1)

    stats = response.json()
    if args.json_output:
        print(json.dumps(stats, indent=2))
        return

    print("=== Report Statistics ===")
    print(f"Total reports: {stats['total']}")
    print(f"Total size:    {_format_bytes(stats['total_size_bytes'])}")
    print(f"Avg size:      {_format_bytes(stats['avg_size_bytes'])}")
    print("\nBy status:")
    for status, count in stats.get("by_status", {}).items():
        print(f"  {status:<12} {count}")
    print("\nTop dashboards:")
    for d in stats.get("top_dashboards", []):
        print(f"  {d['title']:<40} {d['count']} reports")


def _format_bytes(n: int) -> str:
    """Format bytes to human-readable string."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


# ------------------------------------------------------------------
# Parser
# ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="grafana-reporter",
        description="Grafana PDF Reporter CLI",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--token", help="JWT access token")
    parser.add_argument("--username", "-u", help="Username for login")
    parser.add_argument("--password", "-p", help="Password for login", default="")
    parser.add_argument("--json", dest="json_output", action="store_true", help="JSON output")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # dashboards
    sub.add_parser("dashboards", help="List Grafana dashboards")

    # generate
    gen = sub.add_parser("generate", help="Generate a PDF report")
    gen.add_argument("--dashboard", "-d", required=True, help="Dashboard UID")
    gen.add_argument("--panels", help="Comma-separated panel IDs")
    gen.add_argument("--title", help="Report title")
    gen.add_argument("--time-from", default="now-24h", help="Time range start")
    gen.add_argument("--time-to", default="now", help="Time range end")
    gen.add_argument("--orientation", choices=["portrait", "landscape"])
    gen.add_argument("--language", choices=["ca", "es", "en", "pl"])
    gen.add_argument("--wait", "-w", action="store_true", help="Wait for completion")
    gen.add_argument("--output", "-o", help="Output file path (with --wait)")

    # list
    ls = sub.add_parser("list", help="List reports")
    ls.add_argument("--status", help="Filter by status")
    ls.add_argument("--page", type=int, default=1)
    ls.add_argument("--per-page", type=int, default=20)

    # download
    dl = sub.add_parser("download", help="Download a report PDF")
    dl.add_argument("report_id", help="Report UUID")
    dl.add_argument("--output", "-o", help="Output file path")

    # stats
    sub.add_parser("stats", help="Show report statistics")

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "dashboards": cmd_dashboards,
        "generate": cmd_generate,
        "list": cmd_list,
        "download": cmd_download,
        "stats": cmd_stats,
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

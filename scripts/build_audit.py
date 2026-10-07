"""Build deterministic maintenance evidence from committed snapshots (no network)."""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OPEN_LICENSES = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "GPL-2.0", "GPL-3.0", "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later", "LGPL-2.1", "LGPL-3.0", "LGPL-2.1-or-later", "LGPL-3.0-or-later", "MPL-2.0", "Python-2.0", "Unlicense", "CC0-1.0"}


def audit(catalogue: dict, snapshot: dict, connectors: dict) -> dict:
    date = dt.date.fromisoformat(snapshot["reviewed_on"])
    repositories = {r["repository"].lower(): r for r in snapshot["repositories"]}
    links = {r["url"]: r for r in snapshot["links"]}
    seen = set()
    results = []
    for tool in catalogue["tools"]:
        if tool["id"] in seen:
            raise ValueError("duplicate tool id: " + tool["id"])
        seen.add(tool["id"])
        if not tool["interfaces"] or not tool["limitations"]:
            raise ValueError("missing interface/limitations: " + tool["id"])
        for source in (tool["license_evidence"], tool["interface_evidence"]):
            if source not in tool["links"]:
                raise ValueError("evidence must be included in links: " + tool["id"])
        for url in tool["links"]:
            if urlparse(url).scheme not in ("http", "https") or url not in links:
                raise ValueError("unprobed or invalid URL: " + url)
        repo = repositories.get((tool.get("github") or "").lower(), {})
        if tool.get("github") and not repo:
            raise ValueError("missing repository evidence: " + tool["id"])
        status = "unknown"
        reason = "No dated code-activity evidence in snapshot; website availability is not maintenance evidence."
        if repo.get("archived"):
            status, reason = "archived", "GitHub reports archived; historical entry retained."
        elif repo.get("committed_at"):
            age = (date - dt.date.fromisoformat(repo["committed_at"][:10])).days
            if age < 0:
                status, reason = "unknown", "Commit timestamp is later than review date; check clock/source."
            elif age <= 365:
                status, reason = "recent_activity", f"Default-branch commit observed {age} days before review; no support guarantee."
            else:
                status, reason = "historical_review", f"Last observed default-branch commit {age} days old; age alone does not prove abandonment."
        license_id = tool["license"]
        license_source = tool["license_evidence"]
        licence_class = tool["licence_class"]
        if license_id == "NOASSERTION" and repo.get("license") in OPEN_LICENSES:
            license_id, licence_class, license_source = repo["license"], "open_source", repo["source"]
        if licence_class == "open_source" and license_id == "NOASSERTION":
            raise ValueError("unverified open-source classification: " + tool["id"])
        observations = [links[u] for u in tool["links"]]
        results.append({**tool, "license": license_id, "licence_class": licence_class,
            "license_evidence": license_source, "maintenance": {"status": status, "reason": reason, "evidence": repo},
            "link_status": "broken" if any(o["status"] == "broken" for o in observations) else "inconclusive" if any(o["status"] == "inconclusive" for o in observations) else "reachable",
            "link_evidence": observations})
    for connector in connectors["connectors"]:
        if connector["tool"] not in seen:
            raise ValueError("connector references unknown tool")
        if connector["status"] != "evaluated" or not connector["security_notes"]:
            raise ValueError("unvalidated connector support claim")
    grouped = {}
    for tool in results:
        key = (tool.get("github") or tool["url"]).rstrip("/").lower()
        grouped.setdefault(key, []).append(tool["id"])
    return {"schema_version": "0.1.0", "reviewed_on": snapshot["reviewed_on"],
        "policy": "Historical entries retained; 365-day code activity heuristic is not a maintenance guarantee. HTTP 404/410 need review; other errors are inconclusive.",
        "duplicate_source_groups": [ids for ids in grouped.values() if len(ids) > 1],
        "related_not_duplicates": [["geckocircuits", "pygeckocircuits2"], ["gmsh", "getdp", "onelab"], ["kicad", "kiclearance"]],
        "tools": sorted(results, key=lambda t: t["id"]),
        "connectors": [{**c, "maintenance_evidence": repositories.get(c["github"].lower(), {})} for c in connectors["connectors"]]}


def render(data: dict) -> str:
    lines = ["# Tool maintenance audit", "", "Reviewed on " + data["reviewed_on"] + ". Generated from committed evidence; no live requests during build.", "", data["policy"], "", "| Tool | Licence / access | Maintenance | Links | Automation |", "| --- | --- | --- | --- | --- |"]
    for tool in data["tools"]:
        lines.append(f"| [{tool['name']}]({tool['url']}) | {tool['license']} / {tool['licence_class']} | {tool['maintenance']['status']} | {tool['link_status']} | {', '.join(tool['interfaces'])} |")
    lines += ["", "Full per-URL results, immutable observed commits, limitations and provenance are in [audit.json](audit.json).", "", "## Links needing review", ""]
    problems = {r["url"]: r for t in data["tools"] for r in t["link_evidence"] if r["status"] != "reachable"}
    for url, record in sorted(problems.items()):
        detail = record.get("http_status", record.get("error", "unknown"))
        lines.append(f"- [{url}]({url}): {record['status']} ({detail}).")
    lines += ["", "## Connector evaluation", ""]
    for c in data["connectors"]:
        evidence = c["maintenance_evidence"]
        lines += [f"### [{c['id']}]({c['repository']})", "", f"{c['license']}; {c['status']}; {c['execution_validation']}. Last observed commit: {evidence.get('committed_at', 'unknown')} (`{evidence.get('commit', 'unknown')}`).", "", c["supported_versions"] + ".", "", "Upstream platform claims: " + ", ".join(c["platforms"]) + "; AIPE has not independently tested this matrix.", "", "API: " + ", ".join(c["api_surface"]) + ".", "", " ".join(c["security_notes"]), "", "Default alternative: " + c["direct_alternative"] + ".", ""]
    lines += ["## Relationships", "", "No entries were removed. Wrappers, symbol libraries, datasets and hardware are distinct from their host tools. Source-code availability does not imply that required commercial runtimes are free.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = audit(*(json.loads((ROOT / ("catalogue/" + name)).read_text()) for name in ["tools.json", "source-snapshot.json", "connectors.json"]))
    outputs = {"audit.json": json.dumps(data, indent=2, ensure_ascii=False) + "\n", "audit.md": render(data)}
    (ROOT / "generated").mkdir(exist_ok=True)
    for name, content in outputs.items():
        path = ROOT / "generated" / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit("Stale generated file: " + name)
        else:
            path.write_text(content, encoding="utf-8")
    print(f"Validated {len(data['tools'])} catalogue entries and {len(data['connectors'])} connector evaluations")


if __name__ == "__main__":
    main()

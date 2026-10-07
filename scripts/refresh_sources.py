"""Opt-in, read-only source/link audit; never removes catalogue entries."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def github(repo: str) -> dict:
    result = subprocess.run(["gh", "api", "repos/" + repo], capture_output=True, text=True)
    if result.returncode:
        return {"repository": repo, "status": "unavailable", "error": result.stderr.strip()[:300]}
    data = json.loads(result.stdout)
    commit = subprocess.run(["gh", "api", "repos/" + repo + "/commits?per_page=1"], capture_output=True, text=True)
    latest = json.loads(commit.stdout)[0] if commit.returncode == 0 else {}
    return {"repository": repo, "status": "observed", "canonical_url": data["html_url"],
            "archived": data["archived"], "pushed_at": data["pushed_at"],
            "default_branch": data["default_branch"], "license": (data.get("license") or {}).get("spdx_id", "NOASSERTION"),
            "commit": latest.get("sha"), "committed_at": latest.get("commit", {}).get("committer", {}).get("date"),
            "source": "https://api.github.com/repos/" + repo}


def probe(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "AIPE-catalogue-link-audit/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return {"url": url, "status": "reachable", "http_status": response.status, "final_url": response.url}
    except urllib.error.HTTPError as error:
        status = "broken" if error.code in (404, 410) else "inconclusive"
        return {"url": url, "status": status, "http_status": error.code}
    except (OSError, ValueError) as error:
        return {"url": url, "status": "inconclusive", "error": str(error)[:180]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", action="store_true", help="Explicitly permit public HTTP requests and gh API reads")
    parser.add_argument("--as-of", required=True, type=dt.date.fromisoformat)
    args = parser.parse_args()
    if not args.network:
        parser.error("Refreshing requires --network; offline validation uses the committed snapshot")
    catalogue = json.loads((ROOT / "catalogue/tools.json").read_text())
    connectors = json.loads((ROOT / "catalogue/connectors.json").read_text())
    records = catalogue["tools"] + connectors["connectors"]
    repos = sorted({r["github"] for r in records if r.get("github")})
    urls = sorted({u for r in records for u in r["links"]})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        metadata = list(pool.map(github, repos))
        links = list(pool.map(probe, urls))
    snapshot = {"schema_version": "0.1.0", "reviewed_on": args.as_of.isoformat(),
                "method": "GitHub repository/default-branch commit API; bounded HTTP GET (404/410 broken; other failures inconclusive)",
                "repositories": metadata, "links": links}
    (ROOT / "catalogue/source-snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"Observed {len(metadata)} repositories and {len(links)} links; inspect changes before committing")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Record a provider-wide terminal block after a large failed search probe."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "nber_si" / "data"
OUTPUT = DATA / "web_search_provider_status.json"


def main() -> None:
    broad = json.loads((DATA / "provisional_web_audit_attempts.json").read_text())
    sources = json.loads((DATA / "cv_audit_sources.json").read_text())
    broad_pending = [row for row in broad.values() if row.get("state") == "pending"]
    author_pending = [row for row in sources if row.get("web_search_state") == "pending"]
    attempted_queries = sum(row.get("queries", 0) for row in broad_pending) + 2 * len(author_pending)
    successful_queries = sum(row.get("successful_queries", 0) for row in broad_pending)
    # Author discovery stores completion only when both queries returned a
    # usable response; pending rows therefore contribute no successful pair.
    failed_probe_rows = len(broad_pending) + len(author_pending)
    state = "exhausted_unavailable" if failed_probe_rows >= 100 and successful_queries == 0 else "pending"
    record = {
        "provider": "DuckDuckGo Lite",
        "state": state,
        "checked_at": date.today().isoformat(),
        "failed_probe_rows": failed_probe_rows,
        "attempted_queries_lower_bound": attempted_queries,
        "successful_queries_in_failed_probe": successful_queries,
        "reason": (
            "Provider-wide timeouts persisted across a large title and author discovery probe; "
            "the provider is terminally unavailable for this July 2026 audit snapshot."
            if state == "exhausted_unavailable" else
            "The failed-probe threshold has not been reached."
        ),
    }
    OUTPUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()

import gzip
import hashlib
import json
import logging
import os
from collections.abc import Callable
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

LOGGER = logging.getLogger(__name__)
PACIFIC = ZoneInfo("America/Los_Angeles")
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def quota_period_start(period: str, now: datetime) -> datetime:
    local_now = now.astimezone(PACIFIC)
    if period == "day":
        start = datetime.combine(local_now.date(), time.min, tzinfo=PACIFIC)
    elif period == "month":
        start = datetime(
            local_now.year, local_now.month, 1, tzinfo=PACIFIC
        )
    else:
        raise ValueError(f"Unsupported quota period: {period}")
    return start.astimezone(timezone.utc)


def evaluate_limits(
    limits: list[dict[str, Any]],
    threshold_percent: int,
    usage_reader: Callable[[dict[str, Any], datetime, datetime], float | None],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    if not 1 <= threshold_percent <= 100:
        raise ValueError("QUOTA_SHUTDOWN_PERCENT must be between 1 and 100.")
    current_time = now or datetime.now(timezone.utc)
    exceeded = []
    for limit in limits:
        quota_limit = float(limit["limit"])
        if quota_limit <= 0:
            raise ValueError(f"Quota limit must be positive: {limit['name']}")
        usage = usage_reader(limit, quota_period_start(limit["period"], current_time), current_time)
        if usage is None:
            LOGGER.warning("No metric data available for quota %s", limit["name"])
            continue
        percent_used = usage / quota_limit * 100
        LOGGER.info(
            "Quota %s: %.2f / %.2f %s (%.1f%%)",
            limit["name"],
            usage,
            quota_limit,
            limit.get("unit", "units"),
            percent_used,
        )
        if percent_used >= threshold_percent:
            exceeded.append({
                "name": limit["name"],
                "usage": usage,
                "limit": quota_limit,
                "unit": limit.get("unit", "units"),
                "percent_used": round(percent_used, 2),
            })
    return exceeded


def read_metric(
    client: Any,
    project_id: str,
    limit: dict[str, Any],
    start: datetime,
    end: datetime,
) -> float | None:
    from google.cloud import monitoring_v3

    filters = [
        f'metric.type = "{limit["metric_type"]}"',
        f'resource.type = "{limit["resource_type"]}"',
    ]
    if limit.get("filter"):
        filters.append(limit["filter"])
    interval = monitoring_v3.TimeInterval(
        {"start_time": start, "end_time": end}
    )
    series = client.list_time_series(
        request={
            "name": f"projects/{project_id}",
            "filter": " AND ".join(filters),
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        }
    )
    total = 0.0
    found = False
    for item in series:
        for point in item.points:
            fields = point.value._pb.ListFields()
            if not fields:
                continue
            field, amount = fields[0]
            if field.name not in {"int64_value", "double_value"}:
                raise ValueError(
                    f"Unsupported metric value type for {limit['name']}: {field.name}"
                )
            total += amount
            found = True
    return total if found else None


def api_session() -> Any:
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=SCOPES)
    return AuthorizedSession(credentials)


def hosting_api(session: Any, method: str, url: str, **kwargs: Any) -> Any:
    response = session.request(method, url, timeout=30, **kwargs)
    response.raise_for_status()
    return response


def deploy_blank_hosting_page(session: Any, site_id: str) -> None:
    base_url = "https://firebasehosting.googleapis.com/v1beta1"
    site_path = f"sites/{quote(site_id, safe='')}"
    version = hosting_api(
        session,
        "POST",
        f"{base_url}/{site_path}/versions",
        json={
            "config": {
                "headers": [
                    {"glob": "**", "headers": {"Cache-Control": "no-store"}}
                ]
            }
        },
    ).json()
    version_name = version["name"]
    version_id = version_name.rsplit("/", 1)[1]

    blank_html = b"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head><body></body></html>"
    compressed_html = gzip.compress(blank_html, mtime=0)
    file_hash = hashlib.sha256(compressed_html).hexdigest()
    version_url = f"{base_url}/{site_path}/versions/{quote(version_id, safe='')}"
    upload = hosting_api(
        session,
        "POST",
        f"{version_url}:populateFiles",
        json={"files": {"/index.html": file_hash}},
    ).json()
    if file_hash in upload.get("uploadRequiredHashes", []):
        hosting_api(
            session,
            "POST",
            f'{upload["uploadUrl"]}/{file_hash}',
            data=compressed_html,
            headers={"Content-Type": "application/octet-stream"},
        )
    hosting_api(
        session,
        "PATCH",
        f"{version_url}?update_mask=status",
        json={"status": "FINALIZED"},
    )
    hosting_api(
        session,
        "POST",
        f"{base_url}/{site_path}/releases",
        params={"versionName": version_name},
        json={"message": "Automatic quota shutdown"},
    )


def shutdown_application(
    session: Any,
    project_id: str,
    site_id: str,
    service_name: str,
    region: str,
) -> bool:
    service_url = (
        "https://run.googleapis.com/v2/projects/"
        f"{quote(project_id, safe='')}/locations/{quote(region, safe='')}"
        f"/services/{quote(service_name, safe='')}"
    )
    service = hosting_api(session, "GET", service_url).json()
    site_url = (
        "https://firebasehosting.googleapis.com/v1beta1/sites/"
        f"{quote(site_id, safe='')}"
    )
    latest_release = hosting_api(
        session, "GET", f"{site_url}/releases", params={"pageSize": 1}
    ).json().get("releases", [])
    blank_release_active = bool(
        latest_release
        and latest_release[0].get("message") == "Automatic quota shutdown"
    )
    if (
        service.get("ingress") == "INGRESS_TRAFFIC_INTERNAL_ONLY"
        and blank_release_active
    ):
        LOGGER.info("Quota shutdown is already active.")
        return False

    if not blank_release_active:
        deploy_blank_hosting_page(session, site_id)
    hosting_api(
        session,
        "PATCH",
        f"{service_url}?updateMask=ingress",
        json={"ingress": "INGRESS_TRAFFIC_INTERNAL_ONLY"},
    )
    LOGGER.warning(
        "Quota threshold reached; Hosting now serves a blank page and "
        "Cloud Run ingress is restricted to internal traffic."
    )
    return True


def check_quotas(request: Any) -> tuple[str, int, dict[str, str]]:
    if request.method != "POST":
        return json.dumps({"error": "POST required"}), 405, {"Content-Type": "application/json"}

    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    site_id = os.environ["HOSTING_SITE_ID"]
    service_name = os.environ["CLOUD_RUN_SERVICE"]
    region = os.environ["CLOUD_RUN_REGION"]
    threshold = int(os.environ.get("QUOTA_SHUTDOWN_PERCENT", "80"))
    limits_path = Path(__file__).with_name("limits.json")
    limits = json.loads(limits_path.read_text(encoding="utf-8"))
    from google.cloud import monitoring_v3

    client = monitoring_v3.MetricServiceClient()
    now = datetime.now(timezone.utc)

    def usage_reader(limit: dict[str, Any], start: datetime, end: datetime) -> float | None:
        return read_metric(client, project_id, limit, start, end)

    exceeded = evaluate_limits(limits, threshold, usage_reader, now)
    if not exceeded:
        return json.dumps({"status": "active", "threshold_percent": threshold}), 200, {
            "Content-Type": "application/json"
        }

    session = api_session()
    shutdown_application(session, project_id, site_id, service_name, region)
    return json.dumps({
        "status": "shutdown",
        "threshold_percent": threshold,
        "exceeded": exceeded,
    }), 200, {"Content-Type": "application/json"}

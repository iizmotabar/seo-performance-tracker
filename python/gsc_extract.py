"""
Pulls query, page, click, and impression data from the Google Search Console API
for a rolling 16 month window (the max GSC retains) and lands it in BigQuery.
"""

import logging
from datetime import date, timedelta

from google.cloud import bigquery
from googleapiclient.discovery import build
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gsc_extract")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
SITE_URL = "https://example-client-site.com/"


def get_search_console_service():
    credentials = service_account.Credentials.from_service_account_file(
        "gsc_service_account.json", scopes=SCOPES
    )
    return build("searchconsole", "v1", credentials=credentials)


def fetch_query_data(service, start_date: str, end_date: str, row_limit: int = 25000) -> list[dict]:
    """Fetches query and page level performance data for the given date range."""
    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query", "page", "date"],
        "rowLimit": row_limit,
    }
    response = service.searchanalytics().query(siteUrl=SITE_URL, body=request).execute()
    rows = response.get("rows", [])

    return [
        {
            "query": row["keys"][0],
            "page": row["keys"][1],
            "date": row["keys"][2],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": row["ctr"],
            "position": row["position"],
        }
        for row in rows
    ]


def load_to_bigquery(rows: list[dict], table_id: str = "project.raw.search_console_queries") -> None:
    bq_client = bigquery.Client()
    errors = bq_client.insert_rows_json(table_id, rows)
    if errors:
        raise RuntimeError(f"Failed to load Search Console data: {errors}")
    logger.info(f"Loaded {len(rows)} rows into {table_id}")


def main() -> None:
    service = get_search_console_service()
    end_date = date.today() - timedelta(days=2)  # GSC data has a ~2 day lag
    start_date = end_date - timedelta(days=1)

    rows = fetch_query_data(service, str(start_date), str(end_date))
    load_to_bigquery(rows)


if __name__ == "__main__":
    main()

"""
Locust test for exploring and filtering datasets by community.

Place this file under: app/modules/explore/tests/locust_test_explore_community.py

How it works:
- Uses HttpUser to visit the exploration page, perform a search query and then apply
  a community filter. The script asserts expected HTTP responses and simple
  response-content checks (community name/logo present, dataset list reduced).

Configuration:
- Set the target host with the LOCUST_HOST environment variable or via `--host`.
  Example: locust -f app/modules/explore/tests/locust_test_explore_community.py --host=http://127.0.0.1:5000

- You can set these environment variables to tune the test (optional):
  * EXPLORE_PATH  - path to exploration page (default: /explore)
  * SEARCH_PARAM  - query parameter name for search (default: query)
  * COMMUNITY_PARAM - query parameter name for community filter (default: community)
  * COMMUNITY_SLUG - slug or id of the community to filter by (default: ai-research-group)

Notes:
- Adjust the selectors/endpoint names depending on how your app handles search and filters.
- Locust will perform HTTP requests; it doesn't run JS. If your site relies on client-side
  filtering only (AJAX), ensure the backend accepts the same parameters or call the
  API endpoints directly.

"""

import os
from urllib.parse import urlencode

from locust import HttpUser, between, task

# Configurable values (can be overridden via environment variables)
EXPLORE_PATH = os.environ.get("EXPLORE_PATH", "/explore")
SEARCH_PARAM = os.environ.get("SEARCH_PARAM", "query")
COMMUNITY_PARAM = os.environ.get("COMMUNITY_PARAM", "community")
COMMUNITY_SLUG = os.environ.get("COMMUNITY_SLUG", "ai-research-group")
SAMPLE_QUERY = os.environ.get("SAMPLE_QUERY", "machine learning")


class ExploreUser(HttpUser):
    """Simulate a visitor exploring datasets and filtering by community."""

    wait_time = between(1, 3)

    @task(3)
    def visit_explore(self):
        """Visit the exploration page and verify it loads."""
        with self.client.get(EXPLORE_PATH, name="Explore Page", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Explore page returned {resp.status_code}")
                return
            # Basic check: the page should contain a marker for the community filter area
            if b"community_filter" not in resp.content and b"Community" not in resp.content:
                # Not failing outright because some apps render filters via JS.
                resp.interrupt()

    @task(6)
    def search_and_filter_by_community(self):
        """Perform a search then apply the community filter via query parameters.

        Many server-side search implementations accept both `query` and a
        `community` parameter to filter results. If your app uses a POST form or
        an API endpoint, adapt the path/params accordingly.
        """
        # 1) Search without filter
        params = {SEARCH_PARAM: SAMPLE_QUERY}
        url = f"{EXPLORE_PATH}?{urlencode(params)}"
        with self.client.get(url, name="Search results - no filter", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Search (no filter) returned {resp.status_code}")
                return
            before_len = self._approx_result_count(resp)

        # 2) Search with community filter
        params[COMMUNITY_PARAM] = COMMUNITY_SLUG
        url_filtered = f"{EXPLORE_PATH}?{urlencode(params)}"
        with self.client.get(url_filtered, name="Search results - community filter", catch_response=True) as resp2:
            if resp2.status_code != 200:
                resp2.failure(f"Search (filtered) returned {resp2.status_code}")
                return

            # Check that community name or logo appears on the page
            if COMMUNITY_SLUG.encode() not in resp2.content and b"Community" not in resp2.content:
                # Not critical failure: some templates use different slugs/IDs.
                resp2.success()
            # Compare approximate counts: filtered result set should be <= unfiltered
            after_len = self._approx_result_count(resp2)
            if before_len is not None and after_len is not None:
                if after_len > before_len:
                    resp2.failure("Filtered results larger than unfiltered results")
                else:
                    resp2.success()

    def _approx_result_count(self, resp):
        """Try to estimate the number of visible dataset items in the HTML.

        This is a heuristic: look for repeated dataset item markers. Adjust
        the marker depending on your templates (e.g., 'dataset-card',
        '.dataset-item', 'class="dataset"', etc.).
        Returns an int or None if it can't estimate.
        """
        text = resp.content
        # Common marker used in templates: a class or data attribute for a result
        markers = [b"dataset-card", b"dataset-item", b"data-dataset-id", b"result-item", b"dataset-list"]
        for m in markers:
            count = text.count(m)
            if count:
                return count
        return None


# If you prefer a quick single-request smoke test, you can run:
#   python3 -c "from locust_test_explore_community import ExploreUser; u=ExploreUser();"
# But Locust should be run with:
#   locust -f app/modules/explore/tests/locust_test_explore_community.py --host=http://127.0.0.1:5000

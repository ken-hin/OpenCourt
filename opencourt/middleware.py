# middleware.py — Request/response middleware for the opencourt app.
#
# Middleware runs on every HTTP request. Each class is registered in the
# project-level MIDDLEWARE list (see config/settings.py).

import logging

from opencourt.views import trigger_async_warm

logger = logging.getLogger(__name__)


class CacheWarmerMiddleware:
    """
    Pre-warms expensive per-page caches in the background.

    Today this only warms the season-wide model accuracy used by the
    /upcoming/?mode=results banner — that computation takes ~1-2s on a cold
    cache and was the cause of the gunicorn worker timeout we hit on
    Railway. By firing the warm from a daemon thread on the FIRST request
    handled by each worker (regardless of which URL the user hit), the
    cache is already populated by the time someone clicks through to the
    results page.

    Behavior:
      - Runs on every request, but `trigger_async_warm()` short-circuits when
        the cache is already populated or a warm is already in flight, so
        the per-request overhead is a single in-memory cache.get + a set
        membership check.
      - Spawns a daemon thread so it never blocks the response. If the
        process is killed mid-warm, the thread dies with it (daemon=True).
      - Wrapped in a broad try/except: a warmer crash must never break the
        actual request the user is making.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            trigger_async_warm()
        except Exception:
            # Defensive: the warmer is a nice-to-have, never a blocker.
            logger.exception("CacheWarmerMiddleware: trigger_async_warm failed")
        return self.get_response(request)

"""
VoxMark Firewall — request filtering, rate limiting, security headers.
Author: Divyanshu Sinha

Provides:
  - Per-IP in-memory rate limiter with sliding window
  - Request body size cap
  - Suspicious path/header detection
  - XSS / injection content scanner
  - Opinionated HTTP security headers (CSP, HSTS, etc.)
  - Flask integration via init_firewall()
  - require_safe_content() decorator for API endpoints
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Dict, List, Optional

from flask import Flask, Request, Response, abort, jsonify, request

logger = logging.getLogger('voxmark.firewall')

# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

RATE_LIMIT_WINDOW: int = 60          # seconds in the sliding window
RATE_LIMIT_MAX:    int = 120         # max requests per window per IP
BODY_SIZE_LIMIT:   int = 512 * 1024  # 512 KB hard cap on request body

# Patterns blocked in incoming source content (XSS / injection)
_BLOCKED_PATTERNS: List[re.Pattern] = [
    re.compile(r'<script[\s\S]*?>[\s\S]*?</script>', re.I),
    re.compile(r'javascript\s*:',                    re.I),
    re.compile(r'on\w+\s*=',                         re.I),   # onerror=, onload=, …
    re.compile(r'vbscript\s*:',                      re.I),
    re.compile(r'data\s*:\s*text/html',              re.I),
    re.compile(r'<iframe[\s\S]*?>',                  re.I),
    re.compile(r'<object[\s\S]*?>',                  re.I),
    re.compile(r'expression\s*\(',                   re.I),   # CSS expression()
    re.compile(r'url\s*\(\s*["\']?\s*javascript',    re.I),
]

# Suspicious null byte / path traversal patterns in URL paths
_BAD_PATH_PATTERNS: List[re.Pattern] = [
    re.compile(r'\x00'),            # null byte
    re.compile(r'\.\.'),            # path traversal
    re.compile(r'[\r\n]'),          # header injection in path
]

# ══════════════════════════════════════════════════════════════════════════════
# Security Headers
# ══════════════════════════════════════════════════════════════════════════════

SECURITY_HEADERS: Dict[str, str] = {
    'X-Content-Type-Options':  'nosniff',
    'X-Frame-Options':         'DENY',
    'X-XSS-Protection':        '1; mode=block',
    'Referrer-Policy':         'strict-origin-when-cross-origin',
    'Permissions-Policy':      'geolocation=(), microphone=(), camera=()',
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "frame-src 'none';"
    ),
    # HSTS: 1 year, include subdomains — only add if serving over HTTPS
    # 'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
}

# ══════════════════════════════════════════════════════════════════════════════
# In-memory rate limiter (thread-safe)
# ══════════════════════════════════════════════════════════════════════════════

class _RateLimiter:
    """
    Sliding-window per-IP rate limiter backed by a dict of timestamp lists.
    Thread-safe via a per-instance lock.
    """

    def __init__(
        self,
        window_seconds: int = RATE_LIMIT_WINDOW,
        max_requests:   int = RATE_LIMIT_MAX,
    ) -> None:
        self._window  = window_seconds
        self._max     = max_requests
        self._counts: Dict[str, List[float]] = defaultdict(list)
        self._lock    = threading.Lock()

    def is_allowed(self, ip: str) -> bool:
        """Return True if the request is within rate limits; False if throttled."""
        now          = time.monotonic()
        window_start = now - self._window
        with self._lock:
            hits = self._counts[ip]
            # Evict timestamps outside the current window
            self._counts[ip] = [t for t in hits if t > window_start]
            if len(self._counts[ip]) >= self._max:
                return False
            self._counts[ip].append(now)
            return True

    def cleanup(self) -> None:
        """Purge all expired tracking data (call periodically from a background thread)."""
        now     = time.monotonic()
        cutoff  = now - self._window
        with self._lock:
            stale = [ip for ip, ts in self._counts.items() if not any(t > cutoff for t in ts)]
            for ip in stale:
                del self._counts[ip]

    @property
    def tracked_ips(self) -> int:
        with self._lock:
            return len(self._counts)


_limiter = _RateLimiter()


# ══════════════════════════════════════════════════════════════════════════════
# Content Scanner
# ══════════════════════════════════════════════════════════════════════════════

def scan_content(text: str) -> bool:
    """
    Return True if the content is considered safe, False if a blocked pattern
    is detected.

    Scans for XSS, script injection, event-handler attributes, and similar.
    """
    if not isinstance(text, str):
        return True
    for pat in _BLOCKED_PATTERNS:
        if pat.search(text):
            logger.debug('Content blocked by pattern: %s', pat.pattern[:60])
            return False
    return True


def _path_is_safe(path: str) -> bool:
    for pat in _BAD_PATH_PATTERNS:
        if pat.search(path):
            return False
    return True


def _get_client_ip(req: Request) -> str:
    """
    Extract the real client IP, respecting X-Forwarded-For when present.
    In production, only trust this header if behind a known reverse proxy.
    """
    forwarded_for = req.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the leftmost (originating) address
        return forwarded_for.split(',')[0].strip()
    return req.remote_addr or '0.0.0.0'


# ══════════════════════════════════════════════════════════════════════════════
# Flask Integration
# ══════════════════════════════════════════════════════════════════════════════

def init_firewall(app: Flask, *, trust_proxy: bool = False) -> None:
    """
    Register firewall before/after-request hooks on a Flask application.

    Parameters
    ----------
    app          : Flask application instance
    trust_proxy  : set True if the app runs behind a reverse proxy that sets
                   X-Forwarded-For (enables proxy-aware IP extraction)
    """

    @app.before_request
    def _firewall_check() -> Optional[Response]:
        ip = _get_client_ip(request) if trust_proxy else (request.remote_addr or '0.0.0.0')

        # ── Rate limit ────────────────────────────────────────────────────────
        if not _limiter.is_allowed(ip):
            logger.warning('Rate limit exceeded: %s', ip)
            return jsonify(error='Rate limit exceeded. Please slow down.'), 429  # type: ignore[return-value]

        # ── Body size cap ─────────────────────────────────────────────────────
        content_length = request.content_length
        if content_length is not None and content_length > BODY_SIZE_LIMIT:
            logger.warning('Body too large from %s: %d bytes', ip, content_length)
            abort(413)

        # ── Path safety ───────────────────────────────────────────────────────
        if not _path_is_safe(request.path):
            logger.warning('Suspicious path from %s: %r', ip, request.path)
            abort(400)

        # ── Host header check (simple open-redirect guard) ────────────────────
        host = request.host or ''
        if '\n' in host or '\r' in host:
            logger.warning('Malformed Host header from %s', ip)
            abort(400)

        return None

    @app.after_request
    def _add_security_headers(response: Response) -> Response:
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response

    logger.info(
        'VoxMark Firewall initialised (rate_limit=%d/%ds, body_cap=%dKB, trust_proxy=%s)',
        RATE_LIMIT_MAX, RATE_LIMIT_WINDOW, BODY_SIZE_LIMIT // 1024, trust_proxy,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Endpoint Decorators
# ══════════════════════════════════════════════════════════════════════════════

def require_safe_content(field: str = 'source') -> Callable:
    """
    Decorator factory: scan a JSON body field for malicious patterns.

    Usage::

        @app.post('/api/compile')
        @require_safe_content('source')
        def compile_endpoint():
            ...

    Parameters
    ----------
    field : the JSON key whose value will be scanned (default: 'source')
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            data   = request.get_json(silent=True) or {}
            source = data.get(field, '')
            if source and not scan_content(source):
                ip = _get_client_ip(request)
                logger.warning('Blocked malicious content in field %r from %s', field, ip)
                return jsonify(error='Content blocked by firewall.'), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_json(f: Callable) -> Callable:
    """Decorator: reject requests whose Content-Type is not application/json."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return jsonify(error='Content-Type must be application/json'), 415
        return f(*args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# Background cleanup (optional — wire up in app factory if desired)
# ══════════════════════════════════════════════════════════════════════════════

def start_cleanup_thread(interval_seconds: int = 300) -> threading.Thread:
    """
    Start a daemon thread that calls _limiter.cleanup() every `interval_seconds`.
    Call this once from your app factory after init_firewall().

    Example::

        init_firewall(app)
        start_cleanup_thread()
    """
    def _loop() -> None:
        while True:
            time.sleep(interval_seconds)
            _limiter.cleanup()
            logger.debug('Firewall rate-limiter cleanup ran (tracked IPs: %d)', _limiter.tracked_ips)

    t = threading.Thread(target=_loop, daemon=True, name='voxmark-firewall-cleanup')
    t.start()
    logger.info('Firewall cleanup thread started (interval=%ds)', interval_seconds)
    return t
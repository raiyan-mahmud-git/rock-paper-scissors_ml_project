"""Vercel Serverless Function entrypoint for FastAPI."""

from urllib.parse import parse_qs
from rps.web.server import app as fastapi_app


class VercelASGI:
    """Wraps FastAPI to restore the exact requested path when invoked via Vercel rewrites."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            headers = dict(scope.get("headers", []))
            forwarded = headers.get(b"x-forwarded-uri") or headers.get(b"x-matched-path")
            target = None
            if forwarded:
                target = forwarded.decode("latin1").split("?")[0]

            if not target or target in ("/api/index", "/api"):
                qs = scope.get("query_string", b"").decode("latin1")
                if qs:
                    params = parse_qs(qs)
                    for key in ("match", "path"):
                        if key in params and params[key]:
                            val = params[key][0].lstrip("/")
                            target = f"/api/{val}" if not val.startswith("api/") else f"/{val}"
                            break

            if target:
                scope["path"] = target
                scope["raw_path"] = target.encode("latin1")

        await self.asgi_app(scope, receive, send)


app = VercelASGI(fastapi_app)

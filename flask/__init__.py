"""Minimal Flask stub for unit testing without external dependencies."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

__all__ = ["Flask", "render_template", "request", "url_for"]


class _RequestProxy:
    def __init__(self) -> None:
        self.method: Optional[str] = None
        self.form: Dict[str, str] = {}


request = _RequestProxy()


class Response:
    """Simple response wrapper mimicking Flask's testing API."""

    def __init__(self, body: str | bytes, status_code: int = 200) -> None:
        self.status_code = status_code
        if isinstance(body, bytes):
            self._data = body
        else:
            self._data = body.encode("utf-8")

    def get_data(self, as_text: bool = False) -> str | bytes:
        return self._data.decode("utf-8") if as_text else bytes(self._data)


class _TestClient:
    def __init__(self, app: "Flask") -> None:
        self._app = app

    def get(self, path: str):
        return self._app._dispatch_request("GET", path, None)

    def post(self, path: str, data: Optional[Dict[str, str]] = None):
        return self._app._dispatch_request("POST", path, data or {})

    def __enter__(self):  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
        return False


class AttrDict(dict):
    """Dictionary with attribute access for template rendering."""

    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:  # pragma: no cover - defensive
            raise AttributeError(item) from exc

    def __setattr__(self, key: str, value: Any) -> None:  # pragma: no cover - unused
        self[key] = value


def _convert(value: Any) -> Any:
    if isinstance(value, dict):
        return AttrDict({key: _convert(val) for key, val in value.items()})
    if isinstance(value, list):
        return [_convert(item) for item in value]
    return value


def _prepare_namespace(context: Dict[str, Any]) -> Dict[str, Any]:
    namespace: Dict[str, Any] = {key: _convert(value) for key, value in context.items()}
    return namespace


_TOKEN_RE = re.compile(r"(\{%.*?%\}|\{\{.*?\}\})", re.DOTALL)


def _render_template_text(text: str, context: Dict[str, Any]) -> str:
    namespace = _prepare_namespace(context)
    namespace["url_for"] = url_for

    code_lines = [
        "def __render():",
        "    result = []",
        "    append = result.append",
    ]
    indent = "    "

    for token in _TOKEN_RE.split(text):
        if not token:
            continue
        if token.startswith("{{") and token.endswith("}}"): 
            expr = token[2:-2].strip()
            code_lines.append(f"{indent}append(str({expr}))")
        elif token.startswith("{%") and token.endswith("%}"):
            statement = token[2:-2].strip()
            if statement.startswith("if "):
                code_lines.append(f"{indent}if {statement[3:]}:")
                indent += "    "
            elif statement.startswith("elif "):
                indent = indent[:-4]
                code_lines.append(f"{indent}elif {statement[5:]}:")
                indent += "    "
            elif statement == "else":
                indent = indent[:-4]
                code_lines.append(f"{indent}else:")
                indent += "    "
            elif statement == "endif":
                indent = indent[:-4]
            elif statement.startswith("for "):
                code_lines.append(f"{indent}for {statement[4:]}:")
                indent += "    "
            elif statement == "endfor":
                indent = indent[:-4]
            else:  # pragma: no cover - unsupported syntax guard
                raise ValueError(f"Unsupported template statement: {statement}")
        else:
            code_lines.append(f"{indent}append({token!r})")

    code_lines.append("    return ''.join(result)")
    exec_namespace = dict(namespace)
    exec("\n".join(code_lines), exec_namespace)
    return exec_namespace["__render"]()


_current_app: "Flask" | None = None


def render_template(template_name: str, **context: Any) -> str:
    if _current_app is None:  # pragma: no cover - defensive
        raise RuntimeError("No active Flask application")
    template_path = _current_app.template_folder / template_name
    text = template_path.read_text(encoding="utf-8")
    return _render_template_text(text, context)


def url_for(endpoint: str) -> str:
    if _current_app is None:  # pragma: no cover - defensive
        raise RuntimeError("No active Flask application")
    return _current_app._endpoints.get(endpoint, f"/{endpoint}")


def _push_request(method: str, form: Optional[Dict[str, str]]) -> None:
    request.method = method
    request.form = form or {}


def _pop_request() -> None:
    request.method = None
    request.form = {}


class Flask:
    """Lightweight Flask-compatible application used for unit tests."""

    def __init__(self, import_name: str) -> None:
        global _current_app
        self.import_name = import_name
        module = sys.modules.get(import_name)
        if module and getattr(module, "__file__", None):
            self.root_path = Path(module.__file__).resolve().parent
        else:  # pragma: no cover - fallback for uncommon cases
            self.root_path = Path.cwd()
        self.template_folder = self.root_path / "templates"
        self.config: Dict[str, Any] = {}
        self._routes: Dict[Tuple[str, str], Callable[[], Any]] = {}
        self._endpoints: Dict[str, str] = {}
        _current_app = self

    def route(self, rule: str, methods: Optional[Iterable[str]] = None):
        def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
            self.add_url_rule(rule, endpoint=func.__name__, view_func=func, methods=methods)
            return func

        return decorator

    def get(self, rule: str):
        return self.route(rule, methods=["GET"])

    def post(self, rule: str):
        return self.route(rule, methods=["POST"])

    def add_url_rule(
        self,
        rule: str,
        endpoint: Optional[str] = None,
        view_func: Optional[Callable[[], Any]] = None,
        methods: Optional[Iterable[str]] = None,
    ) -> None:
        endpoint = endpoint or (view_func.__name__ if view_func else rule)
        methods = list(methods) if methods else ["GET"]
        if view_func is None:  # pragma: no cover - unused in tests
            raise ValueError("view_func is required for this stub")
        for method in methods:
            self._routes[(method.upper(), rule)] = view_func
        self._endpoints[endpoint] = rule

    def test_client(self) -> _TestClient:
        return _TestClient(self)

    def _dispatch_request(self, method: str, path: str, data: Optional[Dict[str, str]]):
        view_func = self._routes.get((method.upper(), path))
        if view_func is None:
            return Response("Not Found", 404)
        _push_request(method, data)
        try:
            result = view_func()
        finally:
            _pop_request()
        if isinstance(result, Response):  # pragma: no cover - future-proofing
            return result
        return Response(result or "", 200)

    def run(self, debug: bool = False):  # pragma: no cover - debug helper
        print(f"Running Flask stub (debug={debug})")

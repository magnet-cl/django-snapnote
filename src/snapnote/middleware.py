from . import conf
from .templatetags.snapnote_tags import render_button


class AutoInjectMiddleware:
    """Inserts the button before </body> in HTML responses. Opt in with SNAPNOTE_AUTO_INJECT.

    Not compatible with streaming responses or a strict CSP.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            not conf.get("AUTO_INJECT")
            or getattr(response, "streaming", False)
            or "text/html" not in response.get("Content-Type", "")
            or response.get("Content-Encoding")
        ):
            return response
        content = response.content.decode(response.charset or "utf-8")
        if "snapnote-root" in content or "</body>" not in content:
            return response
        snippet = render_button(request)
        if snippet.strip():
            head, _, tail = content.rpartition("</body>")
            response.content = f"{head}{snippet}</body>{tail}".encode(response.charset or "utf-8")
            if response.has_header("Content-Length"):
                response["Content-Length"] = len(response.content)
        return response

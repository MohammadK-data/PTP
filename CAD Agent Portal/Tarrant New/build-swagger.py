#!/usr/bin/env python3
"""Build a self-contained, responsive Swagger UI page from Tarrant-New-Docs.yaml.

Usage: python3 build-swagger.py [--cloud] [input.yaml] [output.html]
The spec is embedded in the page, so it opens straight from disk (no server needed).

Every build redacts tokens, password hashes and pre-signed AWS URL credentials.

--cloud builds the shareable claude.ai Artifact version: Swagger's CSS is inlined (the
Artifact CSP only allows CDN scripts), and "Try it out" is turned off because the
Artifact sandbox blocks calls to the API.

--hosted builds a page for a normal static host (Netlify, GitHub Pages, S3...)
with "Try it out" on; the API allows cross-origin calls, so requests work from there.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
cloud = "--cloud" in sys.argv
hosted = "--hosted" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
src = Path(args[0]) if len(args) > 0 else HERE / "Tarrant-New-Docs.yaml"
out = Path(args[1]) if len(args) > 1 else HERE / ("Tarrant-New-Docs.cloud.html" if cloud else "hosted/index.html" if hosted else "Tarrant-New-Docs.html")
SWAGGER_CSS = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css"

spec = yaml.safe_load(src.read_text(encoding="utf-8"))

# OpenAPI 3 says a header parameter named "Authorization" must be ignored, so Swagger UI
# never sends it. Move those params into apiKey security schemes instead.
schemes = spec.setdefault("components", {}).setdefault("securitySchemes", {})
schemes["agentToken"] = {
    "type": "apiKey", "in": "header", "name": "authorization",
    "description": "Raw JWT from Agent Token (no 'Bearer' prefix). Filled in automatically after Agent Token succeeds.",
}
schemes["officeToken"] = {
    "type": "apiKey", "in": "header", "name": "authorization",
    "description": "Office Token expects the literal value null (pre-filled).",
}
for ops in spec.get("paths", {}).values():
    for op in ops.values():
        if not isinstance(op, dict):
            continue
        params = op.get("parameters", [])
        auth = [p for p in params if p.get("in") == "header" and p.get("name", "").lower() == "authorization"]
        if not auth:
            continue
        op["parameters"] = [p for p in params if p not in auth]
        scheme = "officeToken" if str(auth[0].get("example")) == "null" else "agentToken"
        op.setdefault("security", [{scheme: []}])

JWT = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")
# Pre-signed S3 URLs carry temporary AWS credentials in their query string
AWS_SIGNED = re.compile(r"(?i)\b(AWSAccessKeyId|Signature|x-amz-security-token|X-Amz-Credential|X-Amz-Signature)=[^&\"'\s]+")
SECRET_KEYS = {"userpassword", "password", "token"}


def redact(node):
    if isinstance(node, dict):
        return {k: "<redacted>" if k.lower() in SECRET_KEYS and isinstance(v, str) else redact(v)
                for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v) for v in node]
    if isinstance(node, str):
        return AWS_SIGNED.sub(r"\1=<redacted>", JWT.sub("<redacted JWT>", node))
    return node


spec = redact(spec)

spec_json = json.dumps(spec, default=str, separators=(",", ":")).replace("</", "<\\/")
title = spec.get("info", {}).get("title", "API Docs")

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
<style>
  *, *::before, *::after { box-sizing: border-box; }
  html, body { margin: 0; background: #fafafa; overflow-x: hidden; }
  #loading { font: 16px/1.5 system-ui, sans-serif; color: #555; padding: 48px 16px; text-align: center; }

  .swagger-ui .wrapper { max-width: 1200px; padding: 0 16px; }
  .swagger-ui .info { margin: 32px 0 24px; }

  /* Long example payloads: cap height and scroll inside the block */
  .swagger-ui .highlight-code, .swagger-ui .microlight, .swagger-ui pre {
    max-height: 480px; overflow: auto; word-break: normal; white-space: pre;
  }
  .swagger-ui .opblock-body pre.microlight { max-height: 480px; }

  /* Tables scroll horizontally instead of overflowing the page */
  .swagger-ui .table-container, .swagger-ui .responses-inner, .swagger-ui .parameters-container {
    overflow-x: auto;
  }
  .swagger-ui .opblock .opblock-summary-path { word-break: break-all; }

  @media (max-width: 768px) {
    .swagger-ui .wrapper { padding: 0 12px; }
    .swagger-ui .info .title { font-size: 24px; }
    .swagger-ui .scheme-container { padding: 12px 0; }
    .swagger-ui .scheme-container .schemes { flex-direction: column; align-items: stretch; gap: 8px; }

    /* Operation header: method badge on top row, path + summary below */
    .swagger-ui .opblock .opblock-summary { flex-wrap: wrap; padding: 8px; }
    .swagger-ui .opblock .opblock-summary-control { flex-wrap: wrap; gap: 4px; }
    .swagger-ui .opblock .opblock-summary-method { min-width: 64px; font-size: 12px; padding: 6px 0; }
    .swagger-ui .opblock .opblock-summary-path,
    .swagger-ui .opblock .opblock-summary-path__deprecated { font-size: 13px; padding: 0 8px; max-width: 100%; flex: 1 1 calc(100% - 80px); }
    .swagger-ui .opblock .opblock-summary-description { flex: 1 1 100%; font-size: 12px; padding: 4px 0 0; text-align: left; }
    .swagger-ui .opblock-tag { font-size: 18px; padding: 8px 4px; }
    .swagger-ui .opblock-tag small { display: block; padding: 4px 0 0; }

    .swagger-ui .opblock-section-header { flex-wrap: wrap; gap: 8px; padding: 8px 12px; }
    .swagger-ui .opblock-description-wrapper,
    .swagger-ui .opblock-external-docs-wrapper,
    .swagger-ui .opblock-title_normal { padding: 12px; }

    /* Parameter & response tables stack into cards */
    .swagger-ui table thead { display: none; }
    .swagger-ui table.parameters tr,
    .swagger-ui table.responses-table tr { display: block; padding: 8px 0; border-bottom: 1px solid #e5e5e5; }
    .swagger-ui table.parameters td,
    .swagger-ui table.responses-table td { display: block; width: 100% !important; max-width: 100% !important; padding: 4px 12px !important; }
    .swagger-ui .parameters-col_name { width: auto; }
    .swagger-ui .parameter__name { word-break: break-all; }
    .swagger-ui input[type=text], .swagger-ui textarea, .swagger-ui select { width: 100%; max-width: 100%; min-width: 0; }

    .swagger-ui .btn { padding: 6px 14px; }
    .swagger-ui .execute-wrapper { padding: 12px; }
    .swagger-ui .btn-group { padding: 12px; }
    .swagger-ui .responses-wrapper .curl-command, .swagger-ui .request-url { overflow-x: auto; }
    .swagger-ui .model-box { max-width: 100%; overflow-x: auto; }
    .swagger-ui .dialog-ux .modal-ux { width: calc(100% - 24px); max-width: none; }
    .swagger-ui .highlight-code, .swagger-ui .microlight, .swagger-ui pre { max-height: 320px; font-size: 11px; }
  }
</style>
</head>
<body>
<div id="loading">Loading API documentation…</div>
<div id="swagger-ui"></div>
<script id="spec" type="application/json">__SPEC__</script>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-standalone-preset.js"></script>
<script>
  window.addEventListener("load", function () {
    var spec = JSON.parse(document.getElementById("spec").textContent);
    window.ui = SwaggerUIBundle({
      spec: spec,
      dom_id: "#swagger-ui",
      deepLinking: true,
      docExpansion: "list",
      defaultModelsExpandDepth: -1,
      filter: true,
      tryItOutEnabled: false,
      displayRequestDuration: true,
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
      plugins: [SwaggerUIBundle.plugins.DownloadUrl],
      layout: "BaseLayout",
      persistAuthorization: true,
      // After Agent Token succeeds, authorize every other endpoint with the returned JWT
      responseInterceptor: function (res) {
        var token = res.ok && /\\/trueprodigy\\/auth\\/token$/.test(res.url) && res.body && res.body.user && res.body.user.token;
        if (token) window.ui.preauthorizeApiKey("agentToken", token);
        return res;
      },
      onComplete: function () {
        window.ui.preauthorizeApiKey("officeToken", "null");
        document.getElementById("loading").remove();
      }
    });
  });
</script>
</body>
</html>
"""

html = TEMPLATE.replace("__TITLE__", title).replace("__SPEC__", spec_json)
out.parent.mkdir(parents=True, exist_ok=True)
if cloud:
    css = urllib.request.urlopen(SWAGGER_CSS).read().decode("utf-8").replace("</", "<\\/")
    html = html.replace(f'<link rel="stylesheet" href="{SWAGGER_CSS}">', f"<style>{css}</style>")
    # The Artifact host supplies the document skeleton
    html = re.sub(r"<!doctype html>\s*<html[^>]*>\s*<head>\s*<meta charset=\"utf-8\">\s*<meta name=\"viewport\"[^>]*>\s*", "", html)
    html = html.replace("</head>\n<body>\n", "").replace("</body>\n</html>\n", "")
    html = html.replace("deepLinking: true,", "deepLinking: false,\n      supportedSubmitMethods: [],")
out.write_text(html, encoding="utf-8")
print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")

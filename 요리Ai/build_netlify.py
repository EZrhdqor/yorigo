"""Prepare the static frontend for Netlify from the shared Flask template."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
STATIC = ROOT / "static"
TEMPLATE = ROOT / "templates" / "index.html"

ASSET_PATHS = {
    "{{ url_for('static', filename='styles.css') }}": "/static/styles.css",
    "{{ url_for('static', filename='app.js') }}": "/static/app.js",
    "{{ url_for('static', filename='favicon.svg') }}": "/static/favicon.svg",
}


def main() -> None:
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"Web template was not found: {TEMPLATE}")
    if not STATIC.is_dir():
        raise FileNotFoundError(f"Static asset folder was not found: {STATIC}")

    SITE.mkdir(exist_ok=True)
    html = TEMPLATE.read_text(encoding="utf-8")
    for template_expression, public_path in ASSET_PATHS.items():
        html = html.replace(template_expression, public_path)
    if "{{ url_for(" in html:
        raise ValueError("The web template contains an unsupported Flask template expression.")

    (SITE / "index.html").write_text(html, encoding="utf-8")
    destination = SITE / "static"
    shutil.copytree(STATIC, destination, dirs_exist_ok=True)
    print(f"Netlify site prepared at {SITE}")


if __name__ == "__main__":
    main()

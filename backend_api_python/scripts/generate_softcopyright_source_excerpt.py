import os
from pathlib import Path


SOFTWARE_NAME = "ZhiYiQuant Desktop"
SOFTWARE_VERSION = "V2.2.0"
LINES_PER_PAGE = 50
FRONT_PAGES = 30
BACK_PAGES = 30

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "software-copyright" / "source_excerpt_v2.2.0.txt"

SOURCE_FILES = [
    "src-tauri/src/main.rs",
    "src-tauri/src/lib.rs",
    "backend_api_python/run.py",
    "backend_api_python/sidecar_main.py",
    "backend_api_python/app/__init__.py",
    "backend_api_python/app/routes/__init__.py",
    "backend_api_python/app/routes/indicator.py",
    "backend_api_python/app/routes/strategy.py",
    "backend_api_python/app/routes/fast_analysis.py",
    "backend_api_python/app/routes/portfolio.py",
    "backend_api_python/app/services/trading_executor.py",
    "backend_api_python/app/services/fast_analysis.py",
    "backend_api_python/app/services/market_data_collector.py",
    "backend_api_python/app/utils/db.py",
    "backend_api_python/app/utils/db_sqlite.py",
    "quantdinger_vue/src/main.js",
    "quantdinger_vue/src/utils/request.js",
    "quantdinger_vue/src/config/router.config.js",
    "quantdinger_vue/src/views/indicator-analysis/index.vue",
    "quantdinger_vue/src/views/ai-analysis/index.vue",
    "quantdinger_vue/src/views/trading-assistant/index.vue",
]


def load_source_lines():
    combined = []
    for rel_path in SOURCE_FILES:
        file_path = ROOT / rel_path
        if not file_path.exists():
            continue
        combined.append(f"// FILE: {rel_path}")
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, start=1):
                combined.append(f"{rel_path}:{idx:04d}: {line.rstrip()}")
        combined.append("")
    return combined


def paginate(lines):
    pages = []
    for i in range(0, len(lines), LINES_PER_PAGE):
        pages.append(lines[i:i + LINES_PER_PAGE])
    return pages


def render_pages(pages):
    out = []
    for page_no, page_lines in pages:
        out.append(f"{SOFTWARE_NAME} {SOFTWARE_VERSION} - Source Excerpt - Page {page_no}")
        out.append("=" * 88)
        out.extend(page_lines)
        out.append("")
    return "\n".join(out)


def main():
    lines = load_source_lines()
    pages = paginate(lines)
    required_pages = FRONT_PAGES + BACK_PAGES
    if len(pages) < required_pages:
        raise SystemExit(
            f"Not enough pages for excerpt generation: only {len(pages)} pages, need {required_pages}."
        )

    selected = []
    for idx in range(FRONT_PAGES):
        selected.append((idx + 1, pages[idx]))

    start_back = len(pages) - BACK_PAGES
    for idx in range(start_back, len(pages)):
        selected.append((idx + 1, pages[idx]))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_pages(selected), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()

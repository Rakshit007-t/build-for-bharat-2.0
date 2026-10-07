from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.src.reporting import build_approach_docx
from model.src.config import FIGURES_DIR


def main() -> None:
    source = ROOT / "docs" / "APPROACH_NOTE.md"
    if not source.is_file():
        raise SystemExit("Run model/src/run_pipeline.py first to generate the result-based Approach Note Markdown.")
    build_approach_docx(source.read_text(encoding="utf-8"), ROOT / "docs" / "APPROACH_NOTE.docx", FIGURES_DIR)
    print("Created docs/APPROACH_NOTE.docx from the current generated Approach Note and local figures.")


if __name__ == "__main__":
    main()

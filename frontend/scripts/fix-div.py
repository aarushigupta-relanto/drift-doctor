import os
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
tag = "di" + "v"
wrong = "motion." + tag

for path in root.rglob("*.tsx"):
    text = path.read_text(encoding="utf-8")
    if "from \"framer-motion\"" in text or "from 'framer-motion'" in text:
        continue
    if wrong not in text and f"</{wrong}>" not in text:
        continue
    text = text.replace(wrong, tag)
    text = text.replace(f"</{wrong}>", f"</{tag}>")
    path.write_text(text, encoding="utf-8")
    print("fixed", path.relative_to(root))

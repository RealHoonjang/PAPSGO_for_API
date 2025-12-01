# -*- coding: utf-8 -*-
from pathlib import Path

path = Path('streamlit_app.py')
text = path.read_text(encoding='utf-8')
marker = "# ?곗씠?곌? ?낅뜲?댄듃?섏뿀?쇰㈃ ?먮룞 ?덈줈怨좎묠"
before, found, _ = text.partition(marker)
if not found:
    raise SystemExit("marker not found")
indent = before.splitlines()[-1]
indent = indent[:len(indent) - len(indent.lstrip())]
new_tail = Path('new_tail.txt').read_text(encoding='utf-8')
prefix = indent + marker
path.write_text(before + marker + new_tail, encoding='utf-8')

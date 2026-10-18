"""Add prevent_destroy to each generated resource; never overwrite curated HCL."""
import argparse
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('path', type=Path)
args = p.parse_args()
text = args.path.read_text()
if re.search(r'^\s*lifecycle\s*\{', text, re.M):
    raise SystemExit('Lifecycle already present. Review each resource manually.')
pattern = r'^(resource\s+"[^"]+"\s+"[^"]+"\s*\{)'
text, count = re.subn(pattern,
    r'\1\n  lifecycle {\n    prevent_destroy = true\n  }', text, flags=re.M)
if not count:
    raise SystemExit('No resource blocks found.')
args.path.write_text(text)
print('Protected resource blocks:', count)

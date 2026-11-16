#!/usr/bin/env python3
"""Compare the original RD Studio before starting the independent integration."""
from pathlib import Path
import hashlib,sys
root=Path(__file__).resolve().parents[1]
base=Path(sys.argv[1]).expanduser() if len(sys.argv)>1 else Path.home()/'rd-studio'
errors=[]
for line in (root/'integration/RD442-SHA256SUMS.txt').read_text().splitlines():
    sha,name=line.split('  ',1); p=base/name
    if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:errors.append(name)
if errors:sys.exit('Base RD Studio divergiu (nenhum arquivo alterado): '+', '.join(errors))
print('RD Studio 4.4.2: 23 arquivos-base conferidos.')

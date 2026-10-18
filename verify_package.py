"""Verify the included datasets and Python syntax, without network access."""
import ast
from pathlib import Path
from rerun import validate_inputs, load_manifest
ROOT=Path(__file__).resolve().parent

def main():
    manifest=load_manifest()
    count=validate_inputs(manifest)
    assert len(manifest['automated']) == 49
    assert len(manifest['expert']) == 8
    for folder in ('btp','experiments','src','stats','tests'):
        for path in (ROOT/folder).rglob('*.py'):
            ast.parse(path.read_text(),filename=str(path.relative_to(ROOT)))
    for path in ROOT.glob('*.py'):
        ast.parse(path.read_text(),filename=path.name)
    print(f"Verified 49 benchmark tasks and eight expert-study tasks ({count} unique CSVs), and Python syntax.")

if __name__=='__main__':
    main()

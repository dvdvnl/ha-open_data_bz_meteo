from pathlib import Path
import sys

# Ensure the repo root is on sys.path so custom_components can be imported.
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

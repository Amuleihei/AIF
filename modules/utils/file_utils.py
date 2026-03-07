from pathlib import Path

def ensure(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
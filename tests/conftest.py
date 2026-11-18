import sys
from pathlib import Path

# Permite pruebas offline sin resolver dependencias extra de OAuth/keyring.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

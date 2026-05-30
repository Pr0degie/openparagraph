import sys
from pathlib import Path

# Allow `from src.xxx` and `from spikes.xxx` imports in tests
sys.path.insert(0, str(Path(__file__).parent))

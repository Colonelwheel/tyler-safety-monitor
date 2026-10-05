"""Tyler Safety Monitor: Milestone 0 observation only."""

import os
from pathlib import Path

# MediaPipe imports matplotlib. Keep its generated font cache within app data,
# rather than letting it write into an existing user-wide matplotlib directory.
if os.environ.get("LOCALAPPDATA"):
    os.environ["MPLCONFIGDIR"] = str(
        Path(os.environ["LOCALAPPDATA"]) / "TylerSafetyMonitor" / "cache" / "matplotlib"
    )

__version__ = "0.0.1"

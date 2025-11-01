"""
Compatibility shim: interactive plotting has moved to plot/plot.py.
This file forwards execution to the new location to avoid breakage.
"""
from pathlib import Path
import runpy

NEW_SCRIPT = Path(__file__).resolve().parent.parent / "plot" / "plot.py"
runpy.run_path(str(NEW_SCRIPT), run_name="__main__")

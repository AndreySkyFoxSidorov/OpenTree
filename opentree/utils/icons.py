"""
Icon utility for OpenTree.
Keys are icon names (without extension).
"""

import tkinter as tk
from pathlib import Path
from typing import Dict, Optional, Tuple
import os

# Check for tksvg
try:
    import tksvg
    HAS_TKSVG = True
except ImportError:
    HAS_TKSVG = False

from opentree.core.theme import ThemeManager

class IconManager:
    _instance = None
    _cache: Dict[str, tk.PhotoImage] = {}
    
    def __init__(self):
        # Determine icon path robustly
        base_dir = Path(__file__).parent.parent
        self._icon_path = base_dir / "icons"
        
        # Fallback to local icons if opentree/icons doesn't exist (e.g. running from root)
        if not self._icon_path.exists():
            if Path("opentree/icons").exists():
                self._icon_path = Path("opentree/icons")
            elif Path("icons").exists():
                self._icon_path = Path("icons")
    
    @classmethod
    def get_instance(cls) -> "IconManager":
        if cls._instance is None:
            cls._instance = IconManager()
        return cls._instance
    
    def get_icon(self, name: str, size: int = 16) -> Optional[tk.PhotoImage]:
        """
        Get cached PhotoImage for icon name.
        """
        key = f"{name}_{size}"
        if key in self._cache:
            return self._cache[key]
        
        icon = self._load_icon(name, size)
        if icon:
            self._cache[key] = icon
            
        return icon
    
    def _load_icon(self, name: str, size: int) -> Optional[tk.PhotoImage]:
        """
        Load icon from assets.
        Priority: SVG > PNG.
        """
        # Try SVG
        svg_path = self._icon_path / f"{name}.svg"
        if svg_path.exists():
            if HAS_TKSVG:
                 try:
                      # Try standard PhotoImage with svg format (supported by tksvg)
                      return tk.PhotoImage(file=str(svg_path), format="svg", width=size, height=size)
                 except Exception:
                      try:
                          # Fallback to tksvg.SvgImage if available
                          return tksvg.SvgImage(master=None, file=str(svg_path), scale=size/24.0)
                      except Exception as e:
                          print(f"Failed to load SVG {name}: {e}")
        
        # Fallback to PNG
        png_path = self._icon_path / f"{name}.png"
        if png_path.exists():
            try:
                img = tk.PhotoImage(file=str(png_path))
                # Resize if necessary (simple subsample/zoom for power of 2)
                # For more complex resizing, PIL would be needed.
                return img
            except Exception:
                pass
        
        return None

# Global accessor
icons = IconManager.get_instance()

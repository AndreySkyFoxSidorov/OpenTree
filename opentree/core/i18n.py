"""
Internationalization (i18n) support for OpenTree.

Loads translations from CSV file and provides tr() function for UI strings.
"""

import csv
from pathlib import Path
from typing import Dict, Optional


class I18n:
    """
    Internationalization manager.
    
    Loads translations from localization.csv and provides access to localized strings.
    Singleton pattern - use I18n.instance() to get the global instance.
    """
    
    _instance: Optional["I18n"] = None
    
    def __init__(self) -> None:
        self._translations: Dict[str, Dict[str, str]] = {}
        self._current_lang: str = "EN"
        self._fallback_lang: str = "EN"
        self._load_translations()
    
    @classmethod
    def instance(cls) -> "I18n":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def set_language(cls, lang: str) -> None:
        """Set the current language."""
        inst = cls.instance()
        if lang in inst._get_available_languages():
            inst._current_lang = lang
    
    @classmethod
    def get_language(cls) -> str:
        """Get the current language code."""
        return cls.instance()._current_lang
    
    def _get_csv_path(self) -> Path:
        """Get path to localization.csv."""
        return Path(__file__).parent.parent / "localization.csv"
    
    def _load_translations(self) -> None:
        """Load translations from CSV file."""
        csv_path = self._get_csv_path()
        if not csv_path.exists():
            return
        
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                
                # First row is header with language codes
                header = next(reader)
                # Header format: "", "EN", "UK", "RU", ...
                languages = [lang.strip() for lang in header[1:] if lang.strip()]
                
                # Read translations
                for row in reader:
                    if not row or not row[0].strip():
                        continue
                    
                    key = row[0].strip()
                    self._translations[key] = {}
                    
                    for i, lang in enumerate(languages):
                        if i + 1 < len(row):
                            self._translations[key][lang] = row[i + 1]
                        else:
                            self._translations[key][lang] = key
                            
        except Exception as e:
            print(f"Failed to load translations: {e}")
    
    def _get_available_languages(self) -> set:
        """Get set of available language codes."""
        if not self._translations:
            return {"EN"}
        first_key = next(iter(self._translations))
        return set(self._translations[first_key].keys())
    
    def translate(self, key: str, default: Optional[str] = None) -> str:
        """
        Get translated string for key.
        
        Falls back to English if translation not found,
        then to default (if provided) or key itself.
        """
        if key not in self._translations:
            return default if default is not None else key
        
        trans = self._translations[key]
        
        # Try current language
        if self._current_lang in trans and trans[self._current_lang]:
            return trans[self._current_lang]
        
        # Fallback to English
        if self._fallback_lang in trans and trans[self._fallback_lang]:
            return trans[self._fallback_lang]
        
        # Return default or key as last resort
        return default if default is not None else key


def tr(key: str, default: Optional[str] = None) -> str:
    """
    Translate a string key to the current language.
    
    Usage:
        from opentree.core.i18n import tr
        label = tr("la_commit")  # Returns "Commit" or translated version
        label = tr("la_unknown", "Default")  # Returns "Default"
    """
    return I18n.instance().translate(key, default)


def set_language(lang: str) -> None:
    """Set the interface language."""
    I18n.set_language(lang)


def get_language() -> str:
    """Get the current language code."""
    return I18n.get_language()

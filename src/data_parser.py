"""
data_parser.py

Parses War Thunder VROMFS game data files:
  - char.vromfs.bin → UnitTags: vehicle classification (fighter, bomber, tank, etc.)
  - lang.vromfs.bin → LangTableReader: vehicle name translation (internal ID → display name)
  - lang.vromfs.bin → WeaponTableReader: weapon/ammo name translation (internal ID → display name)
"""

# Standard Library Imports
import csv
import logging
import re
import sys
from io import StringIO
from pathlib import Path

# Both the VROMFS parser and the .vromfs.bin data files live under
# src/assets/. The parser is a utility-only package, the data files are
# game assets — keep them colocated and add the assets root to sys.path
# so `from DAGOR_FILES.*` imports resolve.
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
if str(_ASSETS_DIR) not in sys.path:
    sys.path.insert(0, str(_ASSETS_DIR))

# Third-Party Library Imports
from DAGOR_FILES.WtFileUtils.vromfs.VROMFs import VROMFs


# ---------------------------------------------------------------------------
# Unit tags — lazy-loaded from char.vromfs.bin
# ---------------------------------------------------------------------------

_TAG_TO_TYPE = {
    "type_spaa":             "SPAA",
    "type_light_tank":       "Light Tank",
    "type_heavy_tank":       "Tank",
    "type_medium_tank":      "Tank",
    "type_tank_destroyer":   "Tank",
    "type_missile_tank":     "Tank",
    "type_fighter":          "Fighter",
    "type_strike_aircraft":  "Fighter",
    "type_bomber":           "Bomber",
    "type_helicopter":       "Helicopter",
}

_TAG_TO_ABBREV = {
    "type_spaa":             "AA",
    "type_light_tank":       "L",
    "type_heavy_tank":       "T",
    "type_medium_tank":      "T",
    "type_tank_destroyer":   "T",
    "type_missile_tank":     "T",
    "tank":                  "T",
    "type_fighter":          "F",
    "type_strike_aircraft":  "F",
    "type_bomber":           "B",
    "helicopter":            "H",
    "type_helicopter":       "H",
}


class UnitTags:
    """Lazy-loaded lookup for vehicle classification from char.vromfs.bin."""

    _instance: "UnitTags | None" = None

    def __init__(self):
        self._data: dict | None = None
        self._lowercase_map: dict[str, str] | None = None

    @classmethod
    def get(cls) -> "UnitTags":
        """Return the singleton UnitTags instance, creating it on first call.

        Returns:
            The shared UnitTags instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self):
        """Parse char.vromfs.bin and populate ``_data`` and ``_lowercase_map`` if not already loaded."""
        if self._data is not None:
            return
        path = _ASSETS_DIR / "char.vromfs.bin"
        v = VROMFs(str(path)).get_directory()
        data = v["config"]["unittags.blk"].get_data()["root"]  # type: ignore[index,union-attr]
        self._data = data
        self._lowercase_map = {k.lower(): k for k in data}

    def _resolve_key(self, internal_name: str) -> str | None:
        """Return the actual key in the data dict, or None if not found."""
        self._ensure_loaded()
        assert self._data is not None and self._lowercase_map is not None
        if internal_name in self._data:
            return internal_name
        return self._lowercase_map.get(internal_name.lower())

    def _get_tags(self, internal_name: str) -> list[str] | None:
        """Return the tag list for a vehicle, or None if not found."""
        key = self._resolve_key(internal_name)
        if key is None:
            return None
        entry = self._data[key]  # type: ignore[index]
        tags = list(entry["tags"].keys())
        if entry.get("type"):
            tags.append(entry["type"])
        if entry.get("type") == "helicopter" and "type_helicopter" not in tags:
            tags.append("type_helicopter")
        return tags

    @property
    def all_names(self) -> list[str]:
        """All vehicle internal names known to unittags.blk."""
        self._ensure_loaded()
        return list(self._data.keys())  # type: ignore[union-attr]

    @property
    def raw(self) -> dict:
        """Direct access to the parsed unittags dict."""
        self._ensure_loaded()
        return self._data  # type: ignore[return-value]

    @staticmethod
    def _best_match(tags: list[str], mapping: dict[str, str]) -> str | None:
        """Return the most specific matching value from *mapping* for *tags*.

        Specific ``type_*`` tags (e.g. ``type_spaa``, ``type_light_tank``) are
        checked first so they take priority over generic tags like ``tank`` or
        ``helicopter``.
        """
        fallback = None
        for tag in tags:
            if tag not in mapping:
                continue
            if tag.startswith("type_"):
                return mapping[tag]
            if fallback is None:
                fallback = mapping[tag]
        return fallback

    def get_unit_type(self, internal_name: str) -> str | None:
        """Return full vehicle type like 'Tank', 'Fighter', 'SPAA', etc."""
        tags = self._get_tags(internal_name)
        if tags is None:
            print(f"ERROR: Vehicle {internal_name} not found in unit tags")
            return None
        result = self._best_match(tags, _TAG_TO_TYPE)
        if result is None:
            print(f"ERROR DETERMINING VEHICLE TYPE FOR UNIT: {internal_name} WITH TAGS: {tags}")
        return result

    def get_unit_type_abbrev(self, internal_name: str | None) -> str:
        """Return abbreviated vehicle type like 'T', 'F', 'AA', etc."""
        if not internal_name or internal_name == "DISCONNECTED":
            return "?"
        tags = self._get_tags(internal_name)
        if tags is None:
            print(f"ERROR: Vehicle {internal_name} not found in unit tags")
            return "?"
        result = self._best_match(tags, _TAG_TO_ABBREV)
        if result is None:
            print(f"ERROR DETERMINING VEHICLE TYPE FOR UNIT: {internal_name} WITH TAGS: {tags}")
            return "?"
        return result


# Module-level convenience functions (so callers don't need to touch UnitTags directly)

def get_unit_type(internal_name: str) -> str | None:
    """Return full vehicle type (e.g. ``'Tank'``, ``'Fighter'``) for an internal name.

    Args:
        internal_name: War Thunder internal vehicle identifier.

    Returns:
        Human-readable type string, or None if unrecognised.
    """
    return UnitTags.get().get_unit_type(internal_name)

def get_unit_type_abbrev(internal_name: str | None) -> str:
    """Return abbreviated vehicle type (e.g. ``'T'``, ``'F'``, ``'AA'``).

    Args:
        internal_name: War Thunder internal vehicle identifier, or None.

    Returns:
        Single-letter abbreviation, or ``'?'`` if unknown/None.
    """
    return UnitTags.get().get_unit_type_abbrev(internal_name)

def count_unit_types(internal_name_list: list[str]) -> dict[str, int]:
    """Count vehicle types in a list, returning e.g. {'T': 2, 'F': 1}."""
    counts: dict[str, int] = {}
    for name in internal_name_list:
        if name != "MEOW":
            t = get_unit_type_abbrev(name)
            counts[t] = counts.get(t, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Lang CSV readers — translations from lang.vromfs.bin
# ---------------------------------------------------------------------------

class _LangCSVBase:
    """Shared loader for semicolon-delimited lang CSVs inside lang.vromfs.bin."""

    header_info: list[str]
    global_data: dict[str, list[str]]
    lowercase_key_map: dict[str, str]

    _lang_dir = None  # lazily shared across subclasses

    @classmethod
    def _get_lang_dir(cls):
        """Return the parsed lang.vromfs.bin directory, loading it once on first call."""
        if _LangCSVBase._lang_dir is None:
            p = _ASSETS_DIR / "lang.vromfs.bin"
            _LangCSVBase._lang_dir = VROMFs(str(p)).get_directory()
        return _LangCSVBase._lang_dir

    @classmethod
    def _load_csv(cls, csv_path: str):
        """Load a CSV from the lang vromfs. Returns (header, data_dict, lowercase_map)."""
        lang_dir = cls._get_lang_dir()
        parts = csv_path.split("/")
        node = lang_dir[parts[0]][parts[1]]  # type: ignore[index]
        reader = csv.reader(StringIO(node.get_data().decode("utf-8")), delimiter=";")
        header = next(reader)[1:]
        data = {}
        lc_map = {}
        for line in reader:
            key = line[0]
            data[key] = line[1:]
            lc_map[key.lower()] = key
        return header, data, lc_map

    def __init__(self, language: str = "<Chinese>"):
        """Initialise the reader with the given language column.

        Args:
            language: Language column name (e.g. ``"English"``).
                AXBot defaults to Simplified Chinese (``"<Chinese>"``).
        """
        self.index = 0
        self.update_language(language)

    def update_language(self, lang: str) -> bool:
        """Switch translation output to *lang*.

        Accepts either the literal column header (e.g. ``"<English>"``)
        or the bare language name (e.g. ``"English"``) — the columns in
        the WT lang CSVs are stored with literal angle brackets, so we
        try both forms before giving up. If neither matches we keep the
        previous index and log a warning so silent fallthrough to column 0
        (the historical bug) doesn't recur.

        Args:
            lang: Language column name with or without angle brackets.

        Returns:
            True if the language was found and set, False otherwise.
        """
        if lang in self.header_info:
            self.index = self.header_info.index(lang)
            return True
        bracketed = f"<{lang}>"
        if bracketed in self.header_info:
            self.index = self.header_info.index(bracketed)
            return True
        logging.warning(
            "%s: unknown language column '%s' (also tried '%s'); "
            "keeping current column index %d (%s). Available columns: %s",
            type(self).__name__, lang, bracketed, self.index,
            self.header_info[self.index] if 0 <= self.index < len(self.header_info) else '?',
            self.header_info,
        )
        return False

    # Keep old misspelled name working
    update_langauge = update_language

    def _lookup(self, key: str) -> str | None:
        """Case-insensitive lookup, returns translated string or None."""
        try:
            if key in self.global_data:
                val = self.global_data[key][self.index]
            elif key.lower() in self.lowercase_key_map:
                actual = self.lowercase_key_map[key.lower()]
                val = self.global_data[actual][self.index]
            else:
                return None
            return val.replace("\\t", "\t")
        except (KeyError, IndexError):
            return None


class LangTableReader(_LangCSVBase):
    """Translate internal vehicle/unit names to human-readable names."""
    header_info, global_data, lowercase_key_map = _LangCSVBase._load_csv("lang/units.csv")

    def get_translate(self, value: str) -> str | None:
        """Translate a vehicle internal name to its display name.

        Args:
            value: Internal vehicle identifier (e.g. ``"ussr_t_34_1941_l_11"``).

        Returns:
            Translated display name, or None if not found.
        """
        return self._lookup(value + "_shop")


class WeaponTableReader(_LangCSVBase):
    """Translate internal weapon/ammo names to human-readable names."""
    header_info, global_data, lowercase_key_map = _LangCSVBase._load_csv("lang/units_weaponry.csv")

    def get_translate(self, value: str) -> str | None:
        """Translate a weapon/ammo internal name to its display name.

        Args:
            value: Internal weapon identifier (e.g. ``"120mm_dm53"``).
                   Also accepts bare names without the ``weapons/`` prefix.

        Returns:
            Translated display name, or None if not found.
        """
        result = self._lookup(value)
        if result is None and not value.startswith("weapons/"):
            result = self._lookup("weapons/" + value)
        return result


# ---------------------------------------------------------------------------
# Name cleanup utilities
# ---------------------------------------------------------------------------

VEHICLE_NAME_FILTERS = [
    ("Weizman\u2019s ", ""),
    ("Weizman's ", ""),
    ("Plagis\u2019 ", ""),
    ("Plagis' ", ""),
    (" (TEL)", ""),
]
# Decoration glyphs (country tree-leak ▄ ▀, event/premium markers
# ◊ ◌ ◔, block elements ▂▃▅▆▇█,
# control pictures ␗ etc.) used to live in this list and were stripped
# *unconditionally* by the loop in apply_vehicle_name_filters() —
# running before the strip_decorations flag was checked, making
# strip_decorations=False silently a no-op. That's why
# vehicle_translations.json had glyphs stripped despite
# init_vehicle_translation_cache() passing False. _DECORATION_RE already
# covers the same set, so the strip_decorations branch now handles them
# correctly: kept when False (web i18n), stripped when True (Discord PNG).

# Strip every WT decoration glyph in one sweep instead of chasing individual
# codepoints as Gaijin adds new tree-leak indicators.
#
# Covered ranges:
#   U+2400-U+27FF — Control Pictures, Box Drawing, Block Elements (▀ ▄ etc.),
#                   Geometric Shapes (◊ ◌ ◢ ◣ ◤ ◥), Dingbats, Misc Symbols.
#   U+E000-U+F8FF — Private Use Area, where older WT variants stored sprite
#                   refs that survived a few client patches.
#
# Mirrors normalizeVehicleName() in server.js — keep both sides in sync.
_DECORATION_RE = re.compile(r"[␀-⟿-]")
_PRIVATE_USE_RE = _DECORATION_RE  # backward-compat alias for any external imports


def apply_vehicle_name_filters(name: str, strip_decorations: bool = True) -> str:
    """Apply standard vehicle-name cleanup.

    Args:
        name: Raw vehicle display string from lang/units.csv.
        strip_decorations: When True (the historical default), drop every
            glyph in ``_DECORATION_RE`` — country tree-leak indicators (▄ ▀),
            event/premium markers (◊), tree shape markers (◢ ◣ ◤ ◥), control
            pictures, and the Private Use Area. The Discord scoreboard PNG
            renderer uses this because its font can't draw those reliably.
            When False, keep every visible glyph and only strip the Private
            Use Area (true tofu cruft that no font renders). Used by the
            website i18n cache so country indicators survive to the UI.
    """
    if not name:
        return name
    for target, repl in VEHICLE_NAME_FILTERS:
        name = name.replace(target, repl)
    if strip_decorations:
        name = _DECORATION_RE.sub("", name)
    else:
        # Just the PUA — keep all visible decorations.
        name = re.sub(r"[-]", "", name)
    return name.strip()


def normalize_name(name: str):
    """Normalize a vehicle display name to ASCII-safe form.

    Replaces Cyrillic ``T`` with Latin ``T``, converts ``No.`` symbols,
    strips remaining non-ASCII characters, and collapses whitespace.

    Args:
        name: Raw display name string.

    Returns:
        Cleaned ASCII string, or None if *name* is falsy.
    """
    if not name:
        return None
    name = name.replace("Т", "T")       # Cyrillic Т → Latin T
    name = name.replace("№", "No.")     # Number Symbol to No.
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9 .\-\(\)]", "", name)
    return re.sub(r"\s+", " ", name).strip()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    translate = LangTableReader("English")

    vehicles_list = ["ussr_t_34_1941_l_11", "spitfire_lf_mk9e_weisman", "spitfire_ix_usa", "DISCONNECTED"]
    print("Vehicles:", vehicles_list)
    print("Abbreviated types:", count_unit_types(vehicles_list))
    print("\nHuman-readable vehicle translations:")
    for vehicle in vehicles_list:
        if vehicle and vehicle != "DISCONNECTED":
            readable = translate.get_translate(vehicle)
            print(f"  {vehicle} -> {readable}")
        else:
            print(f"  {vehicle} -> (skipped)")

    print("\n--- Weapon translations ---")
    weapons = WeaponTableReader("English")
    weapon_list = ["120mm_dm13", "120mm_dm33", "120mm_dm53", "105mm_dm33", "weapons/cannonMGC30L"]
    for w in weapon_list:
        print(f"  {w} -> {weapons.get_translate(w)}")

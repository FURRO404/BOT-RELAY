"""
scoreboard.py

Generates scoreboard images for autologging match results.
Renders a styled PNG with blurred map backgrounds, player stats, vehicle icons,
team compositions, win/loss records, and squadron point diffs using PIL.
"""

# Standard Library Imports
import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

# Third-Party Library Imports
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL.Image import Resampling

try:
    from .data_parser import LangTableReader, apply_vehicle_name_filters, count_unit_types
except Exception:
    try:
        from data_parser import LangTableReader, apply_vehicle_name_filters, count_unit_types
    except Exception:
        # Fall back to a minimal no-op implementation if the parser bundle is
        # not present in a stripped deployment.
        LangTableReader = None  # type: ignore[assignment]

        def count_unit_types(internal_name_list):
            player_count = len([v for v in internal_name_list if v != "MEOW"])
            return {"?": player_count} if player_count > 0 else {}

        def apply_vehicle_name_filters(name):
            return name


BASE_DIR = Path(__file__).resolve().parent


def _resolve_asset_root() -> Path:
    """Locate the scoreboard asset bundle.

    Preference order:
    1. Explicit AXBOT_SCOREBOARD_ASSETS_DIR
    2. Bundled AXBot/src/assets
    3. The sibling SREBOT asset bundle in the workspace, if present
    """

    candidates: list[Path] = []
    env_root = os.getenv("AXBOT_SCOREBOARD_ASSETS_DIR", "").strip()
    if env_root:
        candidates.append(Path(env_root).expanduser())

    candidates.append(BASE_DIR / "assets")

    workspace_root = BASE_DIR.parent.parent
    candidates.append(workspace_root / "SREBOT_MEOW" / "BOT")

    def _is_ready(root: Path) -> bool:
        return (
            root.exists()
            and (root / "MAPS").exists()
            and (root / "ICONS").exists()
            and (root / "FONTS" / "arial_unicode_ms.otf").exists()
        )

    for candidate in candidates:
        if _is_ready(candidate):
            return candidate

    if env_root:
        return Path(env_root).expanduser()
    return BASE_DIR / "assets"


ASSET_ROOT = _resolve_asset_root()
MAPS_DIR = ASSET_ROOT / "MAPS"
ICON_BASE_DIR = ASSET_ROOT / "ICONS"
TEXT_FONT_PATH = ASSET_ROOT / "FONTS" / "arial_unicode_ms.otf"


def _normalize_squad_key(value: str | None) -> str:
    """Casefold and trim identifiers so scoreboard + prefs align."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().casefold()

FONTS = {}
_LANG_TRANSLATOR = None


def _translate_vehicle_name(vehicle_internal: str | None, fallback: str = "DISCONNECTED") -> str:
    """Resolve an internal vehicle name into a display label."""

    if not vehicle_internal:
        return fallback

    name = ""
    if LangTableReader is not None:
        global _LANG_TRANSLATOR
        if _LANG_TRANSLATOR is None:
            try:
                _LANG_TRANSLATOR = LangTableReader()
            except Exception:
                _LANG_TRANSLATOR = False
        if _LANG_TRANSLATOR:
            try:
                translated = _LANG_TRANSLATOR.get_translate(vehicle_internal)
            except Exception:
                translated = None
            if translated:
                name = translated

    if not name:
        name = vehicle_internal
    return apply_vehicle_name_filters(name)

def load_fonts(base_width):
    """
    Load and cache all fonts for scoreboard rendering.
    Re-uses cache if already loaded.
    """
    global FONTS

    if FONTS:
        return FONTS
    
    # main text fonts (measurable)
    FONTS = {
        "title":   ImageFont.truetype(TEXT_FONT_PATH, int(base_width * 0.04)),
        "team":    ImageFont.truetype(TEXT_FONT_PATH, int(base_width * 0.03)),
        "body":    ImageFont.truetype(TEXT_FONT_PATH, int(base_width * 0.0175)),
        "stat":    ImageFont.truetype(TEXT_FONT_PATH, int(base_width * 0.022)),
        "comp":    ImageFont.truetype(TEXT_FONT_PATH, int(base_width * 0.018)),
        "winloss": ImageFont.truetype(TEXT_FONT_PATH, int(base_width * 0.023)),
        "info":    ImageFont.truetype(TEXT_FONT_PATH, int(base_width * 0.016)),
        "small":   ImageFont.truetype(TEXT_FONT_PATH, int(base_width * 0.014)),
    }

    return FONTS


# ──────────────────────────────────────────────────────────────────────────────────────────────
# Icon Caching Functions
# ──────────────────────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=200)
def _load_icon_cached(icon_path_str: str, size_tuple: tuple, resample_mode: int):
    """
    Internal cached function. Loads icon from disk and resizes.
    Uses only hashable types for lru_cache compatibility.
    LRU cache with maxsize=200 automatically evicts least-used icons.
    """
    icon_path = Path(icon_path_str)

    # Load and convert to RGBA
    img = Image.open(icon_path).convert("RGBA")

    # Resize if size specified
    if size_tuple:
        img = img.resize(size_tuple, resample_mode)

    return img


def load_cached_icon(icon_path, size=None, resample_filter=Image.Resampling.LANCZOS):
    """
    Load and cache icon images for scoreboard rendering.
    LRU cache with maxsize=200 automatically evicts least-used icons.

    Args:
        icon_path: Path object or string to icon file
        size: Optional (width, height) tuple for resizing
        resample_filter: Resampling filter for resize (default: LANCZOS)

    Returns:
        PIL Image object in RGBA mode
    """
    # Convert to hashable types for lru_cache
    path_str = str(icon_path)
    size_tuple = tuple(size) if size else None
    resample_int = int(resample_filter)

    return _load_icon_cached(path_str, size_tuple, resample_int)


@lru_cache(maxsize=20)
def _load_map_background_cached(map_path_str: str, blur_radius: int):
    """
    Internal cached function. Loads map background and applies blur.
    LRU cache with maxsize=20 stores up to 20 blurred map backgrounds.
    """
    map_path = Path(map_path_str)

    # Load, convert, and blur
    background = Image.open(map_path).convert("RGBA")
    background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    return background


def load_cached_map_background(map_path, blur_radius=2):
    """
    Load and cache map background images with blur applied.
    LRU cache with maxsize=20 prevents excessive memory usage.

    Args:
        map_path: Path to map background image
        blur_radius: Gaussian blur radius to apply

    Returns:
        PIL Image object in RGBA mode with blur applied
    """
    return _load_map_background_cached(str(map_path), blur_radius)


def get_pts_color(value: int) -> tuple[int,int,int,int]:
    """
    Color gradient based on points:
    1500 = green, 1600 = yellow, 1750 = orange,
    1850 = red-orange, 1900+ = red.
    Below 1500 = green.
    """

    if value is None:
        return (180, 180, 180, 255)  # grey

    # Green for anything below 1500
    if value < 1500:
        value = 1500

    # Phase 1: 1500-1600 green → yellow
    if value < 1600:
        progress = (value - 1500) / 100.0
        r = int(255 * progress)  # 0 → 255
        g = 255
        b = 0

    # Phase 2: 1600-1750 yellow → orange
    elif value < 1750:
        progress = (value - 1600) / 150.0
        r = 255
        g = int(255 - (115 * progress))  # 255 → 140
        b = 0

    # Phase 3: 1750-1850 orange → red-orange
    elif value < 1850:
        progress = (value - 1750) / 100.0
        r = 255
        g = int(140 - (80 * progress))  # 140 → 60
        b = 0

    # Phase 4: 1850+ red-orange → red
    else:
        if value > 1900:
            value = 1900
        progress = (value - 1850) / 50.0
        r = 255
        g = int(60 - (60 * progress))  # 60 → 0
        b = 0

    return (r, g, b, 255)


def get_gradient_color(win_rate):
    """
    Calculate color gradient from red to yellow to lime green based on win percentage.
    0% = Red (255, 0, 0), 50% = Yellow (255, 255, 0), 100% = Lime Green (0, 255, 0)
    Transitions smoothly in 1% intervals
    """
    win_rate = max(0, min(100, win_rate))

    if win_rate <= 50:
        red = 255
        green = int(255 * (win_rate / 50))
        blue = 0
    else:
        red = int(255 * (1 - (win_rate - 50) / 50))
        green = 255
        blue = 0

    return (red, green, blue, 255)


def make_vignette(width, height, base_alpha=140, max_alpha=175, power=4):
    """Build a radial alpha mask for a vignette overlay.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        base_alpha: Minimum alpha at the center (0-255).
        max_alpha: Maximum alpha at the edges (0-255).
        power: Exponent controlling vignette falloff curve.

    Returns:
        A PIL Image in "L" mode containing the alpha mask.
    """
    base_alpha = max(0, min(255, base_alpha))
    max_alpha  = max(0, min(255, max_alpha))
    if max_alpha < base_alpha:
        max_alpha = base_alpha

    y, x = np.ogrid[:height, :width]
    cx, cy = width / 2.0, height / 2.0
    dx = (x - cx) / cx
    dy = (y - cy) / cy
    d = np.sqrt(dx*dx + dy*dy)
    d = np.clip(d, 0, 1)

    alpha = base_alpha + (max_alpha - base_alpha) * (d ** power)
    alpha = np.clip(alpha, 0, 255).astype(np.uint8)

    return Image.fromarray(alpha, mode="L")


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 1) Synchronous helper that does all the heavy PIL/math work and saves to disk.
#    (Run this on a worker thread via asyncio.to_thread.)
# ──────────────────────────────────────────────────────────────────────────────────────────────
def _create_scoreboard_sync(match_details,
                            winning_team,
                            team1_details,
                            team2_details,
                            map_file,
                            output_path,
                            bar_color="",
                            diffs=None, WL=None, is_draw=False):

    """CPU-bound routine that renders the full scoreboard image and saves it.

    Loads the map background, builds a vignette gradient, draws all text/icons
    for both teams, resizes/compresses, and writes the final PNG.

    Args:
        match_details: Dict with match metadata (utc_timestamp, session_id).
        winning_team: Squadron short name of the winner.
        team1_details: Dict with "squadron" and "players" list for team 1.
        team2_details: Dict with "squadron" and "players" list for team 2.
        map_file: Map display name (e.g. "Abandoned Factory").
        output_path: Filesystem path to write the output PNG.
        bar_color: Color hint for the header bar ("win", "loss", or "").
        diffs: Squadron point diffs dict, keyed by squadron name.
        WL: Win/loss record dict, keyed by squadron name.
        is_draw: Whether the match ended in a draw.
    """

    # ── A) Figure out paths & background
    map_file_clean = re.sub(r"^\s*\[[^]]+\]\s*", "", map_file)
    map_name = map_file_clean
    map_file_clean = map_file_clean.replace(" ", "_")

    target = f"{map_file_clean}.jpg"

    # look for any file in MAPS whose name matches target, ignoring case
    try:
        candidates = {f.name for f in MAPS_DIR.iterdir() if f.is_file()}
    except FileNotFoundError:
        map_image_path = str(MAPS_DIR / target)
    else:
        match = next((fn for fn in candidates if fn.lower() == target.lower()), None)
        if match:
            map_image_path = str(MAPS_DIR / match)
        else:
            map_image_path = str(MAPS_DIR / target)

    # Load base background (with caching)
    blur_power = 2
    try:
        background = load_cached_map_background(map_image_path, blur_radius=blur_power)
    except Exception as e:
        logging.error(f"[Scoreboard] Failed to open map image {map_image_path}: {e}")
        raise

    bg_width, bg_height = background.size
    margin = 0

    # ── B) Build vignette overlay (NumPy vectorized)
    alpha_band = make_vignette(bg_width, bg_height, base_alpha=140, max_alpha=175, power=4)

    # Build a black overlay with that alpha gradient
    overlay   = Image.new("RGBA", (bg_width, bg_height), (0, 0, 0, 0))
    black_rgb = Image.new("RGBA", (bg_width, bg_height), (0, 0, 0, 255))
    overlay   = Image.composite(black_rgb, overlay, alpha_band)

    draw = ImageDraw.Draw(overlay)

    BODY_FONT_SIZE     = int(bg_width * 0.0175)
    STAT_FONT_SIZE     = int(bg_width * 0.022)

    # ── C) Load fonts
    fonts = load_fonts(bg_width)
    font_title   = fonts["title"]
    font_team    = fonts["team"]
    font_body    = fonts["body"]
    stat_font    = fonts["stat"]
    comp_font    = fonts["comp"]
    winloss_font = fonts["winloss"]
    info_font    = fonts["info"]
    small_font   = fonts["small"]


    resample_filter = Image.Resampling.LANCZOS

    normalized_diffs = {}
    if isinstance(diffs, dict) and diffs:
        for key, value in diffs.items():
            norm_key = _normalize_squad_key(key)
            if norm_key and norm_key not in normalized_diffs:
                normalized_diffs[norm_key] = (key, value)


    # ── D) Draw match_details (timestamp + session ID) in top-right
    padding = 15
    ts_epoch = int(match_details["utc_timestamp"])
    dt_utc = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)
    ts_text  = dt_utc.strftime("%H:%M:%S - %Y-%m-%d UTC")
    sid_text = f"{match_details['session_id']}"

    ts_bbox = draw.textbbox((0,0), ts_text, font=info_font)
    x_ts = bg_width - margin - (ts_bbox[2] - ts_bbox[0]) - padding - 10
    y_ts = margin + padding + 10
    draw.text((x_ts, y_ts), ts_text, font=info_font, fill=(200,200,200,255))

    sid_bbox = draw.textbbox((0,0), sid_text, font=info_font)
    x_id = bg_width - margin - (sid_bbox[2] - sid_bbox[0]) - padding - 10
    y_id = y_ts + (ts_bbox[3] - ts_bbox[1]) + 20
    draw.text((x_id, y_id), sid_text, font=info_font, fill=(200,200,200,255))

    received_raw = match_details.get("received_unix")
    if received_raw is not None:
        try:
            delay = int(received_raw) - ts_epoch
        except (TypeError, ValueError):
            delay = None
        if delay is not None and delay >= 60:
            d_hr, rem = divmod(delay, 3600)
            d_min, d_sec = divmod(rem, 60)
            delay_text = f"TTL: {d_hr:02d}:{d_min:02d}:{d_sec:02d}"
            delay_color = (255, 60, 60, 255) if delay > 300 else (200, 200, 200, 255)
            delay_bbox = draw.textbbox((0, 0), delay_text, font=info_font)
            x_delay = bg_width - margin - (delay_bbox[2] - delay_bbox[0]) - padding - 10
            y_delay = y_id + (sid_bbox[3] - sid_bbox[1]) + 20
            draw.text((x_delay, y_delay), delay_text, font=info_font, fill=delay_color)

    # ── E) Draw top titles (map name + winner)
    title_text = map_name
    win_text   = "DRAW" if is_draw else f"Winner - {winning_team}"
    y = 50

    # Centered map-name
    title_bbox = draw.textbbox((0,0), title_text, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    x_center = (bg_width - title_width) // 2
    draw.text((x_center, y), title_text, font=font_title, fill=(255,255,255,255))
    title_height = title_bbox[3] - title_bbox[1]
    y += title_height + 40

    win_loss_data = WL or {}

    # Squadrons for each team
    team1_squadron = team1_details.get("squadron", "Unknown")
    team2_squadron = team2_details.get("squadron", "Unknown")

    # Pull stats directly from the WL dict instead of hitting storage
    stats1 = win_loss_data.get(team1_squadron, {"wins": 0, "losses": 0})
    stats2 = win_loss_data.get(team2_squadron, {"wins": 0, "losses": 0})

    # Unpack for drawing
    team1_wins, team1_losses = stats1["wins"], stats1["losses"]
    team2_wins, team2_losses = stats2["wins"], stats2["losses"]
    
    # Store winloss data as raw values: (win_str, loss_str, percent_str, fill_color)
    team1_total = team1_wins + team1_losses
    if team1_total > 0:
        team1_win_rate = (team1_wins / team1_total) * 100
        team1_winloss_data = (str(team1_wins), str(team1_losses), f"{team1_win_rate:.0f}%", get_gradient_color(team1_win_rate))
    else:
        team1_winloss_data = None

    team2_total = team2_wins + team2_losses
    if team2_total > 0:
        team2_win_rate = (team2_wins / team2_total) * 100
        team2_winloss_data = (str(team2_wins), str(team2_losses), f"{team2_win_rate:.0f}%", get_gradient_color(team2_win_rate))
    else:
        team2_winloss_data = None

    # Centered winner text (not drawn — winner/draw is conveyed by team name colors)
    win_bbox = draw.textbbox((0,0), win_text, font=font_title)
    win_height = win_bbox[3] - win_bbox[1]
    y_start = y + win_height + 60  # Back to normal spacing since winloss moved to icon level

    # ── F) Compute layout for two team columns
    x_start      = margin + 45
    gap_between  = 0
    col_width    = (bg_width - (x_start * 2) - gap_between) // 2

    def draw_team(idx, team_data, start_x, start_y, section_width, buffer):
        """Draw one team's block onto the scoreboard canvas.

        Renders squadron header, player rows (nick, vehicle icon, stats),
        team composition, and W/L record. Layout is mirrored for team 2.

        Args:
            idx: Team index (1 or 2). Team 2 is drawn right-aligned.
            team_data: Dict with "squadron", "players", and optional metadata.
            start_x: Left x-coordinate of the team column.
            start_y: Top y-coordinate to begin drawing.
            section_width: Available pixel width for this team's column.
            buffer: Shared list collecting the running y-position for layout.
        """
        flipped = (idx == 2)

        Username_fill        = (250, 227, 200, 255)
        Living_vehicle_fill  = (255, 255, 255, 255)
        Dead_vehicle_fill    = (200, 200, 200, 255)
        Positive_Points_fill = (60, 255, 60, 255)
        Negative_Points_fill = (255, 60, 60, 255)
        Unknown_Points_fill  = (200, 200, 200, 255)


        # --- 1) Squadron header & points ---
        squadron_short = team_data.get("squadron", "Unknown")
        squadron_long  = team_data.get("squadron_long", "Unknown")
        matched_diff_source = None
        squad_diffs = None
        if normalized_diffs:
            for candidate in (squadron_long, squadron_short):
                norm_candidate = _normalize_squad_key(candidate)
                match = normalized_diffs.get(norm_candidate)
                if match:
                    matched_diff_source, squad_diffs = match
                    break

        diff_keys = list(diffs.keys()) if isinstance(diffs, dict) else None


        points_diff     = {}
        current_points  = {}
        sq_string       = ""
        sq_points_fill  = (200, 200, 200, 255)  # neutral grey

        if squad_diffs:
            points_diff    = squad_diffs.get("points_diff", {})
            current_points = squad_diffs.get("current_points", {})
            diff_total     = squad_diffs.get("diff_total", 0)

            sq_points = int(diff_total)
            if sq_points > 0:
                sq_string, sq_points_fill = f"+{sq_points}", Positive_Points_fill
            elif sq_points < 0:
                sq_string, sq_points_fill = str(sq_points), Negative_Points_fill
            else:
                sq_string, sq_points_fill = "0", Unknown_Points_fill

        
        squad_bbox = draw.textbbox((0,0), squadron_short, font=font_team)
        squad_width  = squad_bbox[2] - squad_bbox[0]
        squad_height = squad_bbox[3] - squad_bbox[1]
        header_y = start_y - 10
        text    = squadron_short

        # Yellow color for draws (255, 255, 0, 255)
        Draw_fill = (255, 255, 0, 255)

        if is_draw:
            fill = Draw_fill
        else:
            fill = Positive_Points_fill if squadron_short == winning_team else Negative_Points_fill

        gap = 30
        if not flipped:
            name_x = start_x
            pts_x  = start_x

            if diffs:
                pts_x  = name_x + squad_width + gap
        else:
            name_x = start_x + section_width - squad_width
            pts_x  = start_x

            if diffs:
                sq_bbox = draw.textbbox((0,0), sq_string, font=font_team)
                sq_width = sq_bbox[2] - sq_bbox[0]
                pts_x = name_x - gap - sq_width

        draw.text((name_x, header_y), text, font=font_team, fill=fill)

        if diffs:
            draw.text((pts_x,  header_y), sq_string, font=font_team, fill=sq_points_fill)

        # --- 2) Comp notation below header ---
        # count_unit_types() indexes by INTERNAL name (matches `unittags.blk`),
        # not the display name. Post-refactor payloads carry that under
        # `vehicle_internal`; old payloads put it under `vehicle`.
        notation_list = count_unit_types([
            p.get("vehicle_internal") or p.get("vehicle") or ""
            for p in team_data.get("players", [])
        ])
        comp_order = [
            ("F", "Fighters"), 
            ("B", "Bombers"),
            ("H", "Helicopters"), 
            ("L", "Light"), 
            ("T", "Tanks"),
            ("AA", "AA"), 
            ("?", "?")
        ]

        comp_y = header_y + squad_height + 40

        if not flipped:
            # Build left→right
            comp_x = start_x + 5
            first = True
            for code, _ in comp_order:
                cnt = notation_list.get(code, 0)
                if cnt > 0:
                    txt = f"{cnt}{code}"
                    if not first:
                        sep = "/ "
                        sep_w = draw.textbbox((0, 0), sep, font=comp_font)[2]
                        draw.text((comp_x, comp_y), sep, font=comp_font, fill=(255, 255, 255, 255))
                        comp_x += sep_w + 5
                    draw.text((comp_x, comp_y), txt, font=comp_font, fill=(255, 255, 255, 255))
                    txt_w = draw.textbbox((0, 0), txt, font=comp_font)[2]
                    comp_x += txt_w + 15
                    first = False
        else:
            # Build a single string, then right‐align
            codes_drawn = []
            for code, _ in comp_order:
                cnt = notation_list.get(code, 0)
                if cnt > 0:
                    codes_drawn.append(f"{cnt}{code}")
            if codes_drawn:
                full_comp_str = " / ".join(codes_drawn)
                full_w = draw.textbbox((0, 0), full_comp_str, font=comp_font)[2]
                comp_x = start_x + section_width - 5 - full_w
                draw.text((comp_x, comp_y), full_comp_str, font=comp_font, fill=(255, 255, 255, 255))
            # else: nothing to draw

        # --- 3) Column headers with icons ---
        if not flipped:
            columns = ["", "Air", "Ground", "Assists", "Deaths", "Caps"]
        else:
            columns = ["", "Caps", "Deaths", "Assists", "Ground", "Air"]

        num_stat_cols  = len(columns) - 1
        stat_area_width= int(section_width * 0.32)
        stat_start     = start_x + section_width - stat_area_width + buffer

        col_positions = [start_x] + [
            stat_start + int(i * stat_area_width / num_stat_cols)
            for i in range(num_stat_cols)
        ]
        if flipped:
            col_positions = [
                start_x + (section_width - (x - start_x)) for x in col_positions
            ]


        ICON_SIZE = int(STAT_FONT_SIZE * 1.1)
        base_icon_map = {
            "Air":     ICON_BASE_DIR / "fighter_icon.png",
            "Ground":  ICON_BASE_DIR / "tank_icon.png",
            "Assists": ICON_BASE_DIR / "assists_icon.png",
            "Deaths":  ICON_BASE_DIR / "deaths_icon.png",
            "Caps":    ICON_BASE_DIR / "cap_icon.png"
        }

        if not flipped:
            cols_to_draw = columns
            pos_to_draw  = col_positions
        else:
            cols_to_draw = list(reversed(columns))
            pos_to_draw  = list(reversed(col_positions))

        for i, name in enumerate(cols_to_draw):
            icon_file = base_icon_map.get(name)
            if not icon_file:
                continue
            header_x   = pos_to_draw[i]
            try:
                icon_img = load_cached_icon(icon_file, (ICON_SIZE, ICON_SIZE), resample_filter)
                header_icon_y = header_y + 90
                overlay.paste(icon_img, (header_x - 15, header_icon_y), icon_img)
            except Exception:
                pass

        row_height = ICON_SIZE + 30
        y_offset  = header_y + row_height + 60

        # --- 4) Player rows
        players_sorted = sorted(
            team_data.get("players", []),
            key=lambda p: int(p.get("score", 0)), reverse=True
        )
        
        for player in players_sorted:
            uid = str(player.get("uid"))
            pts_str  = ""
            pts_fill = (200, 200, 200, 255)  # neutral
            pts      = None
            c_pts    = None

            if squad_diffs:  # only if this team was actually tracked
                pts   = points_diff.get(uid)
                c_pts = current_points.get(uid)

                if pts is None:
                    pts_str  = "???"   # tracked, but this player missing in snapshot
                    pts_fill = Unknown_Points_fill
                elif pts > 0:
                    pts_str  = f"+{pts}"
                    pts_fill = Positive_Points_fill
                elif pts < 0:
                    pts_str  = str(pts)
                    pts_fill = Negative_Points_fill
                else:
                    pts_str  = "0"
                    pts_fill = Unknown_Points_fill
            else:
                # not tracked at all by this guild → leave blank
                pts_str = ""




            # --- Prepare icon image ---
            # Icons live under VEHICLES/<internal_name>.png. Post-refactor
            # payloads carry the internal name in `vehicle_internal`; legacy
            # ones put it in `vehicle`. Display strings (current `vehicle`)
            # do not match the icon filename pattern, so prefer internal.
            vehicle_id = (player.get("vehicle_internal") or player.get("vehicle") or "").lower()
            if vehicle_id == "disconnected" or not vehicle_id:
                ICON_PATH = ICON_BASE_DIR / "disconnected.png"
            else:
                ICON_PATH = ICON_BASE_DIR / "VEHICLES" / f"{vehicle_id}.png"

            icon_display_size = int(BODY_FONT_SIZE * 3.0)
            size_tuple = (icon_display_size, icon_display_size)
            try:
                vicon = load_cached_icon(ICON_PATH, size_tuple, resample_filter)
            except Exception:
                # If vehicle icon fails to load (invalid vehicle), use not_found icon as fallback
                try:
                    vicon = load_cached_icon(
                        ICON_BASE_DIR / "not_found.png",
                        size_tuple,
                        resample_filter
                    )
                except Exception:
                    vicon = None

            # --- Name & (c_pts) formatting (no inline font mixing) ---

            # Prefer fake_nick if present, otherwise fall back to nick
            name_raw = (player.get("fake_nick") or player.get("nick") or "").strip()

            # Strip platform suffixes
            name_raw = name_raw.replace("@live", "").replace("@psn", "")

            # SREBOT shape: `vehicle` is the display name, `vehicle_internal`
            # is the internal id. Pre-refactor payloads used `vehicle` for the
            # internal id and `vehicle_new` for the display name, so we accept
            # both shapes during transition.
            vehicle_display = _translate_vehicle_name(
                player.get("vehicle")
                or player.get("vehicle_internal")
                or player.get("vehicle_new"),
                fallback="DISCONNECTED",
            )


            show_pts = bool(diffs)  # only show when diffs data is present

            # compute name/vehicle metrics using only the base name (no c_pts)
            name_bbox    = draw.textbbox((0,0), name_raw, font=font_body)
            name_w       = name_bbox[2] - name_bbox[0]
            name_h       = name_bbox[3] - name_bbox[1]

            vehicle_bbox = draw.textbbox((0,0), vehicle_display, font=font_body)
            vehicle_w    = vehicle_bbox[2] - vehicle_bbox[0]
            vehicle_h    = vehicle_bbox[3] - vehicle_bbox[1]

            identity_w = max(name_w, vehicle_w)
            identity_h = name_h + 5 + vehicle_h

            row_height = max(identity_h, int(BODY_FONT_SIZE * 2.70))
            text_y     = y_offset + (row_height - identity_h) // 2
            icon_y     = y_offset + (row_height - int(BODY_FONT_SIZE * 2.35)) // 2
            player_name_y_offset = 12
            vehicle_name_y_offset = 4

            # === Draw icon + name + vehicle ===
            if not flipped:
                icon_x = start_x
                if vicon:
                    overlay.paste(vicon, (icon_x, icon_y + 3), vicon)

                text_x = icon_x + icon_display_size + 15

                # draw name
                draw.text((text_x, text_y-player_name_y_offset), name_raw, font=font_body, fill=Username_fill)

                if show_pts and c_pts is not None:
                    pts_text = f"({c_pts})"
                    pts_bbox = draw.textbbox((0,0), pts_text, font=small_font)
                    pts_w    = pts_bbox[2] - pts_bbox[0]
                    pts_h    = pts_bbox[3] - pts_bbox[1]
                    pts_x    = text_x + name_w + 8
                    pts_y    = (text_y + (name_h - pts_h) // 2) - player_name_y_offset
                    draw.text((pts_x, pts_y), pts_text, font=small_font, fill=get_pts_color(c_pts))

                # vehicle (left side)
                vehicle_y = (text_y + name_h + 10) - vehicle_name_y_offset
                player_dead = (int(player.get("deaths", 0)) > 0)
                draw.text(
                    (text_x, vehicle_y),
                    vehicle_display,
                    font=font_body,
                    fill=Dead_vehicle_fill if player_dead or vehicle_display == "DISCONNECTED"
                        else Living_vehicle_fill
                )

            else:
                # flipped: icon on the right, name right-aligned against it
                icon_x = start_x + section_width - icon_display_size - 5
                if vicon:
                    overlay.paste(vicon, (icon_x, icon_y + 3), vicon)

                text_x = icon_x - name_w - 15

                # draw name
                draw.text((text_x, text_y-player_name_y_offset), name_raw, font=font_body, fill=Username_fill)

                # draw (c_pts) in smaller font to the LEFT of the name
                if show_pts and c_pts is not None:
                    pts_text = f"({c_pts})"
                    pts_bbox = draw.textbbox((0,0), pts_text, font=small_font)
                    pts_w    = pts_bbox[2] - pts_bbox[0]
                    pts_h    = pts_bbox[3] - pts_bbox[1]
                    pts_x = text_x - 8 - pts_w
                    pts_y = (text_y + (name_h - pts_h) // 2) - player_name_y_offset
                    draw.text((pts_x, pts_y), pts_text, font=small_font, fill=get_pts_color(c_pts))

                # vehicle (right side)
                vehicle_y = (text_y + name_h + 10) - vehicle_name_y_offset
                vehicle_x = icon_x - vehicle_w - 15
                player_dead = (int(player.get("deaths", 0)) > 0)
                draw.text(
                    (vehicle_x, vehicle_y),
                    vehicle_display,
                    font=font_body,
                    fill=Dead_vehicle_fill if player_dead or vehicle_display == "DISCONNECTED"
                        else Living_vehicle_fill
                )


            if diffs:
                # 1) measure your text
                stat_bbox = draw.textbbox((0, 0), pts_str, font=stat_font)
                stat_w    = stat_bbox[2] - stat_bbox[0]
                stat_h    = stat_bbox[3] - stat_bbox[1]

                pts_string_offset = 0 # positive is down

                # 2) vertical centering
                pts_y = (y_offset + (row_height - stat_h) // 2) + pts_string_offset

                # 3) compute your right‐edge anchor
                if not flipped:
                    anchor_x = col_positions[1] - 35
                    pts_x_draw = anchor_x

                    # 4b) draw
                    draw.text((pts_x_draw, pts_y), pts_str, font=stat_font, fill=pts_fill, anchor="ra")

                else:
                    # flipped side stays as before
                    pts_x_draw = col_positions[1] + 65

                    # 4b) draw
                    draw.text((pts_x_draw, pts_y), pts_str, font=stat_font, fill=pts_fill)

            # Draw the five stat columns
            stats = [
                player.get("air_kills", 0),
                player.get("ground_kills", 0),
                player.get("assists", 0),
                player.get("deaths", 0),
                player.get("captures", 0)
            ]

            base_labels = ["Air", "Ground", "Assists", "Deaths", "Caps"]
            if not flipped:
                labels    = base_labels
                positions = col_positions[1:]
            else:
                labels    = base_labels
                positions = list(reversed(col_positions[1:]))

            for val, x_pos, label in zip(stats, positions, labels):
                try:
                    num = int(val)
                except Exception:
                    num = 0

                if label in ("Air","Ground") and num > 0:
                    fill_color = (60, 255, 60, 255)
                elif label == "Deaths" and num > 0:
                    fill_color = (255, 20, 20, 255)
                elif label == "Caps" and num > 0:
                    fill_color = (255, 255, 0, 255)
                elif label == "Assists" and num > 0:
                    fill_color = (230, 150, 90, 255)
                else:
                    fill_color = (255, 255, 255, 255)

                num_str = str(num)
                num_bbox= draw.textbbox((0,0), num_str, font=stat_font)
                num_h   = num_bbox[3] - num_bbox[1]
                stat_y  = y_offset + (row_height - num_h) // 2

                draw.text((x_pos, stat_y), num_str, font=stat_font, fill=fill_color)

            y_offset += row_height + 15

    # ── G) Draw separator line and both teams side-by-side
    dx = 0
    dy_top    = -50
    dy_bottom = 50

    if bar_color == "win":
        bar_color_fill = (60, 255, 60, 255)
    elif bar_color == "loss":
        bar_color_fill = (255, 60, 60, 255)
    elif bar_color == "draw":
        bar_color_fill = (255, 255, 0, 255)
    else:
        bar_color_fill = (255, 255, 255, 255)

    sep_x  = x_start + col_width + gap_between // 2 + dx
    sep_y1 = y_start + dy_top
    sep_y2 = bg_height - margin - dy_bottom

    draw.line([(sep_x, sep_y1), (sep_x, sep_y2)],
              fill=bar_color_fill,
              width=5)

    draw_team(
        idx=1,
        team_data=team1_details,
        start_x=x_start + 10,
        start_y=y_start - 130,
        section_width=col_width,
        buffer=-10
    )
    draw_team(
        idx=2,
        team_data=team2_details,
        start_x=x_start + col_width + gap_between,
        start_y=y_start - 130,
        section_width=col_width,
        buffer=33
    )

    # Draw winloss data in center area between title and icons
    icon_level_y = y_start - 130 - 5  # Slightly down from previous position
    center_x = bg_width // 2
    
    def _draw_winloss(draw, x_start, y, win_num, loss_num, percent_part, pct_fill):
        """Draw colored W-L-% text starting at x_start. Returns nothing."""
        cx = x_start

        # Win number + W (green)
        draw.text((cx, y), win_num, font=winloss_font, fill=(0, 255, 0, 255))
        cx += draw.textbbox((0,0), win_num, font=winloss_font)[2]
        draw.text((cx, y), "W", font=winloss_font, fill=(0, 255, 0, 255))
        cx += draw.textbbox((0,0), "W", font=winloss_font)[2]

        # Dash (grey)
        draw.text((cx, y), " - ", font=winloss_font, fill=(200, 200, 200, 255))
        cx += draw.textbbox((0,0), " - ", font=winloss_font)[2]

        # Loss number + L (red)
        draw.text((cx, y), loss_num, font=winloss_font, fill=(255, 60, 60, 255))
        cx += draw.textbbox((0,0), loss_num, font=winloss_font)[2]
        draw.text((cx, y), "L", font=winloss_font, fill=(255, 60, 60, 255))
        cx += draw.textbbox((0,0), "L", font=winloss_font)[2]

        # Dash (grey)
        draw.text((cx, y), " - ", font=winloss_font, fill=(200, 200, 200, 255))
        cx += draw.textbbox((0,0), " - ", font=winloss_font)[2]

        # Percentage (color depends on win rate)
        draw.text((cx, y), percent_part, font=winloss_font, fill=pct_fill)

    if team1_winloss_data:
        win_num, loss_num, percent_part, wl_fill = team1_winloss_data
        total_text = f"{win_num}W - {loss_num}L - {percent_part}"
        total_bbox = draw.textbbox((0,0), total_text, font=winloss_font)
        total_width = total_bbox[2] - total_bbox[0]
        _draw_winloss(draw, center_x - total_width - 30, icon_level_y, win_num, loss_num, percent_part, wl_fill)

    if team2_winloss_data:
        win_num, loss_num, percent_part, wl_fill = team2_winloss_data
        _draw_winloss(draw, center_x + 30, icon_level_y, win_num, loss_num, percent_part, wl_fill)

    # ── H) Composite overlay onto background, downsample, and save
    final_img = Image.alpha_composite(background, overlay)

    # Lower is more compression, think of it like what percentage of the W / H to keep
    compression_level: float = 0.42
    w, h = final_img.size
    new_size = (int(w * compression_level), int(h * compression_level))

    resized = final_img.resize(new_size, resample=Resampling.LANCZOS)

    # Convert to RGB to remove unused alpha channel (~25% size reduction)
    resized = resized.convert("RGB")

    try:
        resized.save(output_path, format="PNG", compress_level=1, optimize=False)

    except Exception as e:
        logging.error(f"[Scoreboard] ✗ Failed to save to {output_path}: {e}")
        raise


# ──────────────────────────────────────────────────────────────────────────────────────────────
# 2) Async wrapper that simply offloads the above helper to a thread
# ──────────────────────────────────────────────────────────────────────────────────────────────
async def create_scoreboard(match_details,
                            winning_team,
                            team1_details,
                            team2_details,
                            map_file,
                            output_path,
                            bar_color="",
                            diffs=None,
                            WL=None,
                            is_draw=False):
    """Async entry point that offloads scoreboard rendering to a worker thread.

    Args:
        match_details: Dict with match metadata (utc_timestamp, session_id).
        winning_team: Squadron short name of the winner.
        team1_details: Dict with "squadron" and "players" list for team 1.
        team2_details: Dict with "squadron" and "players" list for team 2.
        map_file: Map display name (e.g. "Abandoned Factory").
        output_path: Filesystem path to write the output PNG.
        bar_color: Color hint for the header bar ("win", "loss", or "").
        diffs: Squadron point diffs dict, keyed by squadron name.
        WL: Win/loss record dict, keyed by squadron name.
        is_draw: Whether the match ended in a draw.

    Raises:
        Exception: Re-raised from _create_scoreboard_sync on render failure.
    """
    # Ensure the parent folder is present
    base_dir = os.path.dirname(output_path)
    os.makedirs(base_dir, exist_ok=True)

    try:
        await asyncio.to_thread(_create_scoreboard_sync,
            match_details,
            winning_team,
            team1_details,
            team2_details,
            map_file,
            output_path,
            bar_color,
            diffs,
            WL,
            is_draw
        )

    except Exception as e:
        logging.error(f"[Scoreboard] create_scoreboard_sync failed: {e}")
        raise


async def render_scoreboard_from_context(context, output_path):
    """Render a scoreboard directly from a SREBOT-style context payload."""

    replay = context.get("replay") if isinstance(context, dict) else {}
    teams = []
    if isinstance(context, dict) and isinstance(context.get("teams"), list):
        teams = list(context["teams"][:2])
    elif isinstance(replay, dict) and isinstance(replay.get("teams"), list):
        teams = list(replay["teams"][:2])

    if len(teams) < 2:
        raise ValueError("scoreboard context is missing two teams")

    match_details = {}
    if isinstance(context, dict):
        match_details = dict(context.get("match_details") or {})
    if not match_details:
        match_details = {
            "utc_timestamp": int((replay or {}).get("end_ts") or 0),
            "session_id": str((context or {}).get("session_id") or (replay or {}).get("session_id") or ""),
        }

    map_name = None
    mode = None
    if isinstance(context, dict):
        map_name = context.get("map_name")
        mode = context.get("mode") or context.get("game_type")
    if not map_name and isinstance(replay, dict):
        map_name = replay.get("map")
    if not mode and isinstance(replay, dict):
        mode = replay.get("mode")

    winner = None
    is_draw = False
    if isinstance(context, dict):
        winner = context.get("winner")
        is_draw = bool(context.get("is_draw", False))
    if not winner and isinstance(replay, dict):
        winner = replay.get("winning_team_squadron")
    if not is_draw and isinstance(replay, dict):
        is_draw = bool(replay.get("draw") or replay.get("is_draw"))

    bar_color = ""
    if isinstance(context, dict):
        bar_color = context.get("bar_color") or ""
    if not bar_color:
        if is_draw:
            bar_color = "draw"
        elif winner and teams and len(teams) >= 2:
            first_squad = str(teams[0].get("squadron") or "").strip()
            bar_color = "win" if first_squad == str(winner).strip() else "loss"

    wl = {}
    points_diffs = {}
    if isinstance(context, dict):
        wl = context.get("wl") or {}
        points_diffs = context.get("points_diffs") or {}

    await create_scoreboard(
        match_details=match_details,
        winning_team=winner or "",
        team1_details=teams[0],
        team2_details=teams[1],
        map_file=map_name or "Unknown Map",
        output_path=output_path,
        bar_color=bar_color,
        diffs=points_diffs,
        WL=wl,
        is_draw=is_draw,
    )

__all__ = [
    "create_scoreboard",
    "render_scoreboard_from_context",
    "load_cached_icon",
    "load_cached_map_background",
    "load_fonts",
]

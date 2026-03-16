# v20260309-1
"""
app/services/place_geocoder.py
──────────────────────────────
Assigns Census-defined place names to listings via point-in-polygon lookup
against the free Census TIGER/Line Places shapefile for South Carolina.

PLACE NAMES returned look like:
  "Charleston city"       "James Island CDP"      "Goose Creek city"
  "Summerville town"      "Ladson CDP"             "Johns Island CDP"
  "North Charleston city" "Mount Pleasant town"    "Hanahan city"

ONE-TIME SETUP:
  1. Download: https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_45_place.zip
  2. Unzip to:  <project_root>/data/tl_2024_45_place/
  3. Install:   pip install geopandas shapely

USAGE:
  from app.services.place_geocoder import get_place_name, get_area_places
  place = get_place_name(32.776, -79.931)   # "Charleston city"
  places = get_area_places()                # sorted list for UI autocomplete
"""
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# ── Candidate shapefile locations ─────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent.parent   # project root (three levels up from services/)
_SHAPEFILE_CANDIDATES = [
    _ROOT / "data" / "tl_2024_45_place" / "tl_2024_45_place.shp",
    _ROOT / "data" / "tl_2023_45_place" / "tl_2023_45_place.shp",
]

_gdf = None
_load_attempted = False


def _load_shapefile():
    """Load and cache the GeoDataFrame.  Returns it or None."""
    global _gdf, _load_attempted
    if _load_attempted:
        return _gdf
    _load_attempted = True

    shp_path = next((p for p in _SHAPEFILE_CANDIDATES if p.exists()), None)
    if shp_path is None:
        log.warning(
            "Census Places shapefile not found — place filtering disabled.\n"
            "Download: https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_45_place.zip\n"
            "Unzip to: <project>/data/tl_2024_45_place/"
        )
        return None
    try:
        import geopandas as gpd
        gdf = gpd.read_file(shp_path).to_crs("EPSG:4326")
        _gdf = gdf
        log.info(f"Census Places shapefile loaded: {len(gdf)} SC places ({shp_path.name})")
        return _gdf
    except Exception as e:
        log.error(f"Failed to load Census Places shapefile: {e}")
        return None


def get_place_name(lat: float, lon: float) -> str | None:
    """
    Return the NAMELSAD for the given lat/lon, or None if outside all Census places.

    Examples:
      32.776, -79.931  ->  "Charleston city"
      32.745, -79.988  ->  "James Island CDP"
      32.988, -80.041  ->  "Goose Creek city"
      32.960, -80.099  ->  "Ladson CDP"
    """
    if lat is None or lon is None:
        return None
    gdf = _load_shapefile()
    if gdf is None:
        return None
    try:
        from shapely.geometry import Point
        point = Point(lon, lat)     # shapely: (x=lon, y=lat)
        matches = gdf[gdf.geometry.contains(point)]
        if matches.empty:
            return None
        row = matches.iloc[0]
        return row.get("NAMELSAD") or row.get("NAME") or None
    except Exception as e:
        log.warning(f"Place lookup failed ({lat}, {lon}): {e}")
        return None


# Charleston tri-county bounding box
_CHARLESTON_BOUNDS = (-80.6, 32.5, -79.6, 33.3)


def get_area_places(bounds: tuple = _CHARLESTON_BOUNDS) -> list[str]:
    """
    Return sorted NAMELSAD list for places that intersect the bounding box.
    Used to populate the Avoid Areas multi-select in Preferences.
    """
    gdf = _load_shapefile()
    if gdf is None:
        return []
    try:
        from shapely.geometry import box
        area_gdf = gdf[gdf.geometry.intersects(box(*bounds))]
        return sorted(area_gdf["NAMELSAD"].dropna().tolist())
    except Exception as e:
        log.warning(f"get_area_places failed: {e}")
        return []


def is_available() -> bool:
    """True if the shapefile is present and loadable."""
    return _load_shapefile() is not None


def backfill_place_names(app, batch_size: int = 200) -> int:
    """
    One-time backfill: set place_name on all listings that have lat/lon but no place_name.

    Run from Flask shell:
        from app.services.place_geocoder import backfill_place_names
        from app import create_app
        app = create_app()
        with app.app_context():
            n = backfill_place_names(app)
            print(f"Updated {n} listings")
    """
    from app.models import db, Listing

    gdf = _load_shapefile()
    if gdf is None:
        log.error("Backfill aborted — shapefile not available")
        return 0

    listings = (
        Listing.query
        .filter(
            Listing.latitude.isnot(None),
            Listing.longitude.isnot(None),
            Listing.place_name.is_(None),
        )
        .all()
    )
    log.info(f"Backfill: {len(listings)} listings need place_name")

    updated = 0
    for i, listing in enumerate(listings):
        place = get_place_name(listing.latitude, listing.longitude)
        if place:
            listing.place_name = place
            updated += 1
        if (i + 1) % batch_size == 0:
            try:
                db.session.commit()
                log.info(f"  …{i + 1}/{len(listings)}")
            except Exception as e:
                db.session.rollback()
                log.error(f"Batch commit error: {e}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f"Final commit error: {e}")

    log.info(f"Backfill complete — {updated} listings updated")
    return updated

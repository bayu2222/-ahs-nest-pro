"""SVG import layer (Phase B).

Isolated from the nesting engine: it turns an SVG file into polygon objects in
the AHS convention (cm, origin bottom-left, +Y up), then hands them to the
existing engine exactly like the random generator does. The nesting engine
never needs to know an object originated from SVG.

Pipeline:
    SVG text -> svgelements (parse, apply transforms + viewBox/units at `dpi`)
             -> flatten every supported element to closed rings (px)
             -> convert px -> cm (2.54 / dpi)
             -> classify rings (outer / hole) -> one valid Shapely Polygon
             -> flip Y once (y_ahs = docHeight - y_svg), orient
             -> {id, type:'polygon', points(cm), holes, bbox, width, height}
"""

from .importer import (  # noqa: F401
    COORDINATE_SYSTEM,
    CURVE_MAX_CHORD_CM,
    DEFAULT_DPI,
    SUPPORTED_ELEMENTS,
    SUPPORTED_TRANSFORMS,
    import_svg,
)

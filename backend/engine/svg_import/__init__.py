"""SVG import layer (Phase A).

Isolated from the nesting engine: it turns an SVG file into normalized polygon
objects expressed in CENTIMETERS, then hands them to the existing engine exactly
like the random generator does. The nesting engine never needs to know an object
originated from SVG.

Pipeline:
    SVG text -> svgelements (parse, apply transforms + viewBox/units)
             -> flatten every supported element to a polygon ring (px)
             -> convert px -> cm (deterministic 96 ppi basis)
             -> sanitize with Shapely -> {id, type:'polygon', points(cm), bbox}
"""

from .importer import SUPPORTED_ELEMENTS, SUPPORTED_TRANSFORMS, import_svg  # noqa: F401

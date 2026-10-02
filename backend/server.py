from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
import uuid

from engine.api_models import (
    BenchmarkRequest,
    GenerateRequest,
    ImportSvgRequest,
    NestRequest,
    ShapeInput,
)
from engine.benchmark import run_benchmark
from engine.nesting.base import NestSettings, ShapeObject
from engine.nesting.registry import ALGORITHMS, get_algorithm
from engine.nesting.verify import verify_spacing
from engine.svg_import import (
    COORDINATE_SYSTEM,
    CURVE_MAX_CHORD_CM,
    DEFAULT_DPI,
    SUPPORTED_ELEMENTS,
    SUPPORTED_TRANSFORMS,
    import_svg,
)
from engine.test_data import SHAPE_TYPES, generate_objects
from shapely.geometry import Polygon

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="AHS Nesting Engine V0.1")
api_router = APIRouter(prefix="/api")


# ----------------------------- serialization --------------------------------
def shape_to_dict(obj: ShapeObject) -> dict:
    return {
        "id": obj.id,
        "type": obj.type,
        "points": obj.points,
        "width": obj.width,
        "height": obj.height,
        "originalRotation": obj.original_rotation,
    }


def placed_to_dict(obj: ShapeObject) -> dict:
    return {
        "id": obj.id,
        "type": obj.type,
        "x": obj.x,
        "y": obj.y,
        "rotation": obj.rotation,
        "width": obj.width,
        "height": obj.height,
        "points": obj.points,
        "rotatedPoints": obj.rotated_points,
        "bbox": obj.bbox,
        "placed": obj.placed,
    }


def settings_from_input(s) -> NestSettings:
    return NestSettings(
        media_width=s.media_width,
        media_height=s.media_height,
        height_mode=s.height_mode,
        spacing=s.spacing,
        rotation_step=s.rotation_step,
        allow_rotation=s.allow_rotation,
        max_angle=s.max_angle,
    )


def input_to_shape(item: ShapeInput, index: int) -> ShapeObject:
    oid = item.id or f"obj-{index + 1:03d}"
    pts = [tuple(p) for p in item.points] if item.points else None
    return ShapeObject.from_spec(
        id=oid,
        type=item.type,
        width=item.width,
        height=item.height,
        points=pts,
        original_rotation=item.original_rotation,
    )


# --------------------------------- routes -----------------------------------
@api_router.get("/")
async def root():
    return {"engine": "AHS Nesting Engine", "version": "0.1"}


@api_router.get("/algorithms")
async def list_algorithms():
    return {"algorithms": list(ALGORITHMS.keys()), "shapeTypes": SHAPE_TYPES}


@api_router.post("/generate")
async def generate(req: GenerateRequest):
    objects = generate_objects(req.count, seed=req.seed, types=req.types)
    return {"objects": [shape_to_dict(o) for o in objects]}


@api_router.post("/nest")
async def nest(req: NestRequest):
    settings = settings_from_input(req.settings)
    objects = [input_to_shape(item, i) for i, item in enumerate(req.objects)]
    algo = get_algorithm(req.settings.algorithm)
    outcome = algo.nest(objects, settings, debug=req.debug)

    response = {
        "objects": [placed_to_dict(o) for o in outcome.objects],
        "stats": {
            "mediaWidth": outcome.media_width,
            "mediaHeight": outcome.media_height,
            "usedWidth": outcome.used_width,
            "usedHeight": outcome.used_height,
            "utilization": outcome.utilization,
            "processingTime": outcome.processing_time,
            "objectCount": outcome.object_count,
            "placedCount": outcome.placed_count,
            "failedPlacements": outcome.failed_placements,
            "candidatesTested": outcome.candidates_tested,
            "algorithm": algo.name,
        },
    }

    placed_polys = [
        Polygon(o.rotated_points)
        for o in outcome.objects
        if o.placed and o.rotated_points
    ]
    response["verification"] = verify_spacing(placed_polys, settings.spacing)

    if outcome.debug is not None:
        response["debug"] = {
            "candidates": outcome.debug.candidates,
            "rejected": outcome.debug.rejected,
            "collisions": outcome.debug.collisions,
            "boundingBoxes": outcome.debug.bounding_boxes,
        }
    return response


@api_router.post("/benchmark")
async def benchmark(req: BenchmarkRequest):
    settings = settings_from_input(req.settings)
    results = run_benchmark(
        req.counts, settings, seed=req.seed, algorithm=req.settings.algorithm
    )
    return {"results": results}


@api_router.get("/import-svg/capabilities")
async def import_svg_capabilities():
    return {
        "elements": SUPPORTED_ELEMENTS,
        "transforms": SUPPORTED_TRANSFORMS,
        "defaultDpi": DEFAULT_DPI,
        "curveMaxChordCm": CURVE_MAX_CHORD_CM,
        "coordinateSystem": COORDINATE_SYSTEM,
    }


@api_router.post("/import-svg")
async def import_svg_endpoint(req: ImportSvgRequest):
    """Convert SVG text into nesting-ready polygon objects (cm, bottom-left, +Y up).

    400 when the SVG cannot be parsed or contains no usable geometry.
    200 with `objects` (+ per-element `failures`) otherwise. Each object's
    `points` can be posted to /api/nest as {type:'polygon', points}.
    """
    try:
        result = import_svg(req.svg, dpi=req.dpi)
    except Exception as exc:  # defensive: parser must never 500
        raise HTTPException(status_code=400, detail={
            "error": f"SVG import failed: {exc}", "failures": [], "filename": req.filename,
        })
    if not result["objects"]:
        raise HTTPException(status_code=400, detail={
            "error": result["error"] or "No supported/valid geometry found in the SVG.",
            "failures": result["failures"],
            "filename": req.filename,
        })
    result["filename"] = req.filename
    return result


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

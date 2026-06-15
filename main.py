"""
main.py -- FastAPI application for the Y-Strainer Pressure Drop Calculator.

Web routes
----------
GET  /           -> calculator UI (requires login)
GET  /login      -> login page
POST /login      -> authenticate
GET  /signup     -> registration page
POST /signup     -> create account
GET  /logout     -> clear session

API endpoints
-------------
POST /calculate
POST /calculate/from-selection
GET  /lookup/meshes
GET  /lookup/perforations
GET  /lookup/strainer-models

Run with:
    uvicorn main:app --reload
"""

import os
import secrets
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from schemas import (
    CalculationRequest,
    LookupRequest,
    CalculationResponse,
    MeshOption,
    PerfOption,
    StrainerSizeOption,
    PipeNPSOption,
    PipeScheduleOption,
    PRClassOption,
)
from calculator import calculate
from config import MESH_DATA, PERF_SHEET_DATA, STRAINER_DATA, PIPE_NPS_DATA, PR_CLASS_DATA, PIPE_SCHEDULE_DATA
from database import init_db, create_user, get_user_by_username, verify_password

# -- Session secret ------------------------------------------------------------
# Production (Railway): set SESSION_SECRET_KEY env var in Railway dashboard.
# Local dev: falls back to a file-persisted secret so sessions survive restarts.
_SECRET_FILE = Path(__file__).parent / ".session_secret"


def _get_session_secret() -> str:
    # 1. Prefer explicit env var (required on Railway -- filesystem is ephemeral)
    env_key = os.environ.get("SESSION_SECRET_KEY", "").strip()
    if env_key:
        return env_key
    # 2. Local dev: persist to file so sessions survive --reload restarts
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()
    key = secrets.token_hex(32)
    try:
        _SECRET_FILE.write_text(key)
    except OSError:
        pass  # read-only filesystem (Railway without env var set)
    return key


# -- Lifespan -------------------------------------------------------------------
@asynccontextmanager
async def _lifespan(application: FastAPI):
    init_db()
    # Auto-create admin user from env vars if provided
    _username = os.environ.get("ADMIN_USERNAME", "").strip()
    _email    = os.environ.get("ADMIN_EMAIL", "").strip()
    _password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if _username and _email and _password:
        ok, _ = create_user(_username, _email, _password)
        if ok:
            print(f"[startup] Admin user '{_username}' created from environment variables.")
    yield


# -- App setup ------------------------------------------------------------------
app = FastAPI(
    title="Y-Strainer Pressure Drop Calculator",
    description=(
        "Calculates pressure drop across Y-strainers for two conditions: "
        "100 % clean screen and 50 % clogged screen. "
        "Implements the Forbes Marshall formula chain validated against 14 software screenshots."
    ),
    version="1.0.0",
    lifespan=_lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=_get_session_secret())

_BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(_BASE / "templates"))


# -- Auth helpers ---------------------------------------------------------------
def _current_user(request: Request) -> str | None:
    return request.session.get("username")


# -- Web routes -----------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    if not _current_user(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        request, "calculator.html", {"username": _current_user(request)}
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    if _current_user(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login", response_class=HTMLResponse, include_in_schema=False)
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    # Static credential check -- set STATIC_USERNAME / STATIC_PASSWORD in Railway
    # env vars for instant access without needing the database.
    _static_user = os.environ.get("STATIC_USERNAME", "").strip()
    _static_pass = os.environ.get("STATIC_PASSWORD", "").strip()
    if _static_user and _static_pass:
        if username.strip() == _static_user and password == _static_pass:
            request.session["username"] = _static_user
            return RedirectResponse("/", status_code=302)

    # Database credential check (used when add_user.py accounts exist)
    user = get_user_by_username(username)
    if user and verify_password(password, user["password_hash"]):
        request.session["username"] = user["username"]
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid username or password."},
    )


@app.get("/signup", include_in_schema=False)
@app.post("/signup", include_in_schema=False)
def signup_disabled(request: Request):
    """Registration is closed -- accounts are created by the administrator only."""
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Page not found")


@app.get("/logout", include_in_schema=False)
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# -- T&C acceptance (stored locally) --------------------------------------------

_TNC_DIR = Path(__file__).parent / "tnc_acceptances"
_TNC_DIR.mkdir(exist_ok=True)


@app.post("/api/accept-tnc", include_in_schema=False)
def accept_tnc(request: Request, html_body: str = Form(...)):
    """Store the signed T&C acceptance HTML locally on the server."""
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    ts = datetime.now()
    ts_label = ts.strftime("%d %B %Y, %H:%M:%S")
    ts_file = ts.strftime("%Y%m%d_%H%M%S")
    filename = f"{user}_{ts_file}.html"
    filepath = _TNC_DIR / filename

    filepath.write_text(html_body, encoding="utf-8")
    print(f"[tnc] User '{user}' accepted T&C at {ts_label} -> {filepath}")

    return {"status": "ok", "message": f"T&C acceptance saved as {filename}"}


# -- Primary calculation endpoint -----------------------------------------------

@app.post(
    "/calculate",
    response_model=CalculationResponse,
    summary="Calculate pressure drop -- direct inputs",
    tags=["calculation"],
)
def calculate_direct(req: CalculationRequest) -> CalculationResponse:
    """All geometry and fluid properties are provided directly by the caller."""
    result = calculate(
        rho=req.rho,
        mu_cP=req.mu_cP,
        W=req.W,
        flow_unit=req.flow_unit,
        D_pipe_cm=req.D_pipe_cm,
        D_screen_cm=req.D_screen_cm,
        L_cm=req.L_cm,
        D_open_cm=req.D_open_cm,
        Q_pct=req.Q_pct,
        P_pct=req.P_pct,
        strainer_type=req.strainer_type,
        D_screen2_cm=req.D_screen2_cm,
    )
    return CalculationResponse(tag_no=req.tag_no, fluid_name=req.fluid_name, **result)


# -- Lookup-based calculation endpoint -----------------------------------------

@app.post(
    "/calculate/from-selection",
    response_model=CalculationResponse,
    summary="Calculate pressure drop -- model / mesh / perf selection",
    tags=["calculation"],
)
def calculate_from_selection(req: LookupRequest) -> CalculationResponse:
    """Resolve geometry from the reference tables, then run the calculation.

    - model + nps  ->  D_pipe_cm, D_screen_cm, L_cm   (Strainer data sheet)
    - mesh + swg   ->  D_open_cm, Q_pct               (Mesh Data sheet)
    - perforation  ->  P_pct                           (Perf Sheet sheet)

    No-Mesh case: set mesh=0 and provide D_open_cm_override.
    """
    # -- Strainer geometry ------------------------------------------------------
    strainer_key = (req.model.strip().upper(), req.nps.strip())
    if strainer_key not in STRAINER_DATA:
        raise HTTPException(
            status_code=404,
            detail=f"Strainer model '{req.model}' NPS '{req.nps}' not found in catalogue."
                   " Use GET /lookup/strainer-models to see available options.",
        )
    pipe_OD_mm, screen_D_mm, screen_L_mm = STRAINER_DATA[strainer_key]
    D_pipe_cm = pipe_OD_mm / 10.0
    D_screen_cm = screen_D_mm / 10.0
    L_cm = screen_L_mm / 10.0

    # -- Mesh / opening data ----------------------------------------------------
    if req.mesh == 0:
        # No-Mesh case: full open area, caller must supply effective opening width
        Q_pct = 100.0
        if req.D_open_cm_override is None:
            raise HTTPException(
                status_code=422,
                detail="D_open_cm_override is required when mesh=0 (No Mesh).",
            )
        D_open_cm = req.D_open_cm_override
    else:
        mesh_key = (req.mesh, req.swg)
        if mesh_key not in MESH_DATA:
            raise HTTPException(
                status_code=404,
                detail=f"Mesh {req.mesh} x SWG {req.swg} not found."
                       " Use GET /lookup/meshes to see available options.",
            )
        opening_mm, Q_pct = MESH_DATA[mesh_key]
        D_open_cm = opening_mm / 10.0

    # -- Perforation data -------------------------------------------------------
    perf_key = req.perforation.strip().upper()
    if perf_key not in PERF_SHEET_DATA:
        raise HTTPException(
            status_code=404,
            detail=f"Perforation '{req.perforation}' not found."
                   " Use GET /lookup/perforations to see available options.",
        )
    P_pct = PERF_SHEET_DATA[perf_key]

    # -- Run calculation --------------------------------------------------------
    result = calculate(
        rho=req.rho,
        mu_cP=req.mu_cP,
        W=req.W,
        flow_unit=req.flow_unit,
        D_pipe_cm=D_pipe_cm,
        D_screen_cm=D_screen_cm,
        L_cm=L_cm,
        D_open_cm=D_open_cm,
        Q_pct=Q_pct,
        P_pct=P_pct,
    )
    return CalculationResponse(tag_no=req.tag_no, fluid_name=req.fluid_name, **result)


# -- Lookup list endpoints ------------------------------------------------------

@app.get(
    "/lookup/meshes",
    response_model=list[MeshOption],
    summary="List available mesh options",
    tags=["lookup"],
)
def list_meshes() -> list[MeshOption]:
    """Returns all (mesh, SWG) combinations with opening size and open-area %."""
    return [
        MeshOption(mesh=m, swg=s, opening_mm=v[0], open_area_pct=v[1])
        for (m, s), v in sorted(MESH_DATA.items())
    ]


@app.get(
    "/lookup/perforations",
    response_model=list[PerfOption],
    summary="List available perforation options",
    tags=["lookup"],
)
def list_perforations() -> list[PerfOption]:
    """Returns all perforation descriptions with their open-area %."""
    return [
        PerfOption(description=desc, open_area_pct=pct)
        for desc, pct in PERF_SHEET_DATA.items()
    ]


@app.get(
    "/lookup/strainer-models",
    response_model=list[StrainerSizeOption],
    summary="List available strainer models and sizes",
    tags=["lookup"],
)
def list_strainer_models() -> list[StrainerSizeOption]:
    """Returns all (model, NPS) combinations with screen and pipe dimensions."""
    return [
        StrainerSizeOption(
            model=k[0], nps=k[1],
            pipe_OD_mm=v[0], screen_D_mm=v[1], screen_L_mm=v[2],
        )
        for k, v in sorted(STRAINER_DATA.items())
    ]


@app.get(
    "/lookup/pipe-nps",
    response_model=list[PipeNPSOption],
    summary="List available pipe NPS sizes",
    tags=["lookup"],
)
def list_pipe_nps() -> list[PipeNPSOption]:
    """Returns all unique NPS inch values with their DN (nominal bore) in mm."""
    return [
        PipeNPSOption(nps_inch=nps, dn_mm=dn)
        for nps, dn in PIPE_NPS_DATA.items()
    ]


@app.get(
    "/lookup/pr-class",
    response_model=list[PRClassOption],
    summary="List available pressure rating classes",
    tags=["lookup"],
)
def list_pr_class() -> list[PRClassOption]:
    """Returns all pressure rating classes (e.g. 150, 300, 600, 900, 1500, 2500)."""
    return [PRClassOption(rating=r) for r in PR_CLASS_DATA]


@app.get(
    "/lookup/pipe-schedules",
    response_model=list[PipeScheduleOption],
    summary="List pipe schedules (SchNoCS1 + SchNoCS2) for all NPS sizes",
    tags=["lookup"],
)
def list_pipe_schedules() -> list[PipeScheduleOption]:
    """Returns all (NPS, schedule, pipe ID) entries for the Basket strainer Schedule dropdown."""
    return [
        PipeScheduleOption(nps=nps, schedule=sch, id_mm=id_mm)
        for nps, entries in PIPE_SCHEDULE_DATA.items()
        for sch, id_mm in entries
    ]

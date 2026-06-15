"""
schemas.py — Pydantic request/response models for the Y-Strainer API.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Request models ─────────────────────────────────────────────────────────────

class CalculationRequest(BaseModel):
    """Direct calculation — all geometry values supplied explicitly."""

    # Fluid properties
    rho: float = Field(..., gt=0, description="Fluid density (kg/m³)")
    mu_cP: float = Field(..., gt=0, description="Dynamic viscosity (cP)")
    W: float = Field(..., gt=0, description="Flow rate value (unit given by flow_unit)")
    flow_unit: Literal["kg/hr", "m3/hr"] = Field("kg/hr", description="Unit of W")

    # Geometry — all in centimetres
    D_pipe_cm: float = Field(..., gt=0, description="Pipe internal diameter (cm)")
    D_screen_cm: float = Field(..., gt=0, description="Screen outer diameter (cm)")
    L_cm: float = Field(..., gt=0, description="Screen length (cm)")
    D_open_cm: float = Field(..., gt=0, description="Mesh / perf opening width (cm)")
    Q_pct: float = Field(..., gt=0, le=100, description="Mesh open area Q (%)")
    P_pct: float = Field(..., gt=0, le=100, description="Perforated-sheet open area P (%)")

    # Strainer type — controls screen area formula
    # Basket:          A_screen = π·d·L + π·(d/2)²
    # T-Type (Monkey): A_screen = π·d·(L−1.3d) + 0.644·π·d·(0.8d) + π·(d/2)²
    # T-Type (Boat):   A_screen = 2·(L−d/2)·(d/√2) + π·(d/2)²
    # Conical:         A_screen = π·r2² + π·(r1+r2)·L + π·r1²
    # Y:               A_screen = π·d·L (cylinder only)
    strainer_type: Literal["Y", "Basket", "T-Type", "T-Type (Monkey)", "T-Type (Boat)", "Conical"] = Field(
        "Y", description="Strainer type: Y, Basket, T-Type (Monkey), T-Type (Boat), or Conical"
    )

    # Conical-type second diameter — the smaller end diameter (cm)
    # Required when strainer_type='Conical'; defaults to 0 (full cone, no small end cap)
    D_screen2_cm: float = Field(
        0.0, ge=0,
        description="Smaller-end screen diameter (cm) — used only for Conical type; 0 = full cone"
    )

    # Optional metadata
    tag_no: Optional[str] = None
    fluid_name: Optional[str] = None
    project: Optional[str] = None

    model_config = {"json_schema_extra": {"example": {
        "rho": 951.0, "mu_cP": 0.248, "W": 165, "flow_unit": "kg/hr",
        "D_pipe_cm": 2.5, "D_screen_cm": 2.6, "L_cm": 8.0,
        "D_open_cm": 0.05, "Q_pct": 62.7, "P_pct": 51,
        "tag_no": "ND031-PZSY-0303", "fluid_name": "Naphtha"
    }}}


class LookupRequest(BaseModel):
    """Selection-based calculation — geometry resolved from model / mesh / perf selection."""

    # Fluid properties
    rho: float = Field(..., gt=0, description="Fluid density (kg/m³)")
    mu_cP: float = Field(..., gt=0, description="Dynamic viscosity (cP)")
    W: float = Field(..., gt=0, description="Flow rate value")
    flow_unit: Literal["kg/hr", "m3/hr"] = Field("kg/hr")

    # Strainer selection
    model: str = Field(..., description="Strainer model code (e.g. FMSTR54-T)")
    nps: str = Field(..., description="NPS / pipe size string (e.g. '2', '1 1/2')")

    # Mesh selection — use mesh=0 to indicate 'No Mesh' (Q=100%)
    mesh: int = Field(..., ge=0, description="Mesh number; 0 = No Mesh (Q=100%)")
    swg: int = Field(..., ge=0, description="SWG wire gauge; ignored when mesh=0")

    # Perforation selection
    perforation: str = Field(..., description="Perforation description key (e.g. 'Perf. : 12mm x Pitch: 14mm')")

    # Override for effective opening width when mesh=0 (No Mesh case)
    D_open_cm_override: Optional[float] = Field(
        None, gt=0,
        description="Effective opening diameter (cm) — required when mesh=0 (No Mesh)"
    )

    # Optional metadata
    tag_no: Optional[str] = None
    fluid_name: Optional[str] = None
    project: Optional[str] = None


# ── Response models ────────────────────────────────────────────────────────────

class ConditionResult(BaseModel):
    """Pressure-drop result for a single screen-cleanliness condition."""
    surface_area_cm2: float
    net_surface_area_cm2: float
    screening_area_ratio: float
    V_cm_s: float
    Re: float
    C: float
    K: float
    delta_P_cm_wc: float
    delta_P_in_wc: float
    delta_P_kg_cm2: float


class CalculationResponse(BaseModel):
    """Full pressure-drop response for both 100% clean and 50% clogged conditions."""
    tag_no: Optional[str] = None
    fluid_name: Optional[str] = None

    # Shared derived values
    alpha: float
    A_pipe_cm2: float
    A_screen_gross_cm2: float
    Q_vol_cm3_s: float

    # Per-condition results
    clean_100pct: ConditionResult
    clogged_50pct: ConditionResult


# ── Lookup list models ─────────────────────────────────────────────────────────

class MeshOption(BaseModel):
    mesh: int
    swg: int
    opening_mm: float
    open_area_pct: float


class PerfOption(BaseModel):
    description: str
    open_area_pct: float


class StrainerSizeOption(BaseModel):
    model: str
    nps: str
    pipe_OD_mm: float
    screen_D_mm: float
    screen_L_mm: float


class PipeNPSOption(BaseModel):
    nps_inch: str
    dn_mm: float


class PipeScheduleOption(BaseModel):
    nps: str
    schedule: str
    id_mm: float


class PRClassOption(BaseModel):
    rating: int

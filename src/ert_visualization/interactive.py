from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ert_visualization.processing import interpolate_ert_grid

def _prepare_fence_surface(
    ert_df: pd.DataFrame,
    elevation_df: pd.DataFrame,
    vmin: float,
    vmax: float,
    nx: int,
    nz: int,
    interpolation_space: Literal["linear", "log10"],
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """
    Prepare a topography corrected ERT grid for a 3-D fence surface.

    Returns
    -------
    tuple
        Horizontal coordinates (X), vertical coordinates (Z)
        masked elevation coordinates, and log10 resistivity colours.

    """
    XI, ZI, RHOI = interpolate_ert_grid(
    ert_df,
    vertical_column="model_elevation_m",
    nx=nx,
    nz=nz,
    interpolation_space=interpolation_space,
)

    elevation_sorted = elevation_df.sort_values("x_m")

    surface_at_grid_x = np.interp(
        XI[0, :],
        elevation_sorted["x_m"],
        elevation_sorted["elevation_m"],
    )

    surface_grid = np.broadcast_to(
        surface_at_grid_x,
        ZI.shape,
    )

    mask = (
        ~np.isfinite(RHOI)
        | (ZI > surface_grid)
    )

    masked_resistivity = np.where(
        mask,
        np.nan,
        RHOI,
    )

    masked_elevation = np.where(
        mask,
        np.nan,
        ZI,
    )

    clipped_resistivity = np.clip(
        RHOI,
        vmin,
        vmax,
    )

    log_resistivity = np.log10(clipped_resistivity)

    log_resistivity_masked = np.where(
        mask,
        np.nan,
        log_resistivity,
    )

    return (
        XI,
        ZI,
        masked_elevation,
        log_resistivity_masked,
        masked_resistivity,
    )

def make_ert_fence_diagram(
    day1_model: pd.DataFrame,
    day1_elevation: pd.DataFrame,
    day2_model: pd.DataFrame,
    day2_elevation: pd.DataFrame,
    day1_intersection_m: float | None = None,
    day2_intersection_m: float | None = None,
    array_name: str = "Wenner",
    vmin: float = 0.1,
    vmax: float = 10000.0,
    nx: int = 350,
    nz: int = 150,
    interpolation_space: Literal["linear", "log10"] = "log10",
) -> go.Figure:
    """
    Create an interactive pseudo-3D fence diagram from two
    approximately orthogonal 2-D ERT inversion models.

    If intersection coordinates are not provided, the profiles are 
    centered on their midponts.

    Parameters
    ----------
    day1_model: 
        Topography corrected Day 1 ERT model

    day1_elevation:
        Day 1 measured electrode elevations

    day2_model:
        Topography corrected Day 2 ERT model

    day2_elevation:
        Day 2 measured electrode elevations

    day1_intersection_m:
        Along profile Day 1 coordinate of the line intersection

    day2_intersection_m:
        Along profile Day 2 coordinate of the line intersection

    vmin:
        Minimum resistivity value in Ohm m
    
    vmax:
        Maximum resistivity value in Ohm m
    
    nx:
        Number of horizontal grid points for interpolation
    
    nz:
        Number of vertical grid points for interpolation
    
    interpolation_space:
        Space used to interpolate resistivity values

    Returns
    -------
    plotly.graph_objects.Figure
        Interactive pseudo-3D fence diagram 
    """

    if vmin <= 0:
        raise ValueError(
            "vmin must be greater than zero."
        )

    if vmax <= vmin:
        raise ValueError(
            "vmax must be greater than vmin"
        )

    one_intersection_missing =(
        (day1_intersection_m is None)
        != (day2_intersection_m is None)
    )
    if one_intersection_missing:
        raise ValueError(
            "Provide both intersection coordinates or neither."
        )

    schematic = (
        day1_intersection_m is None
        and day2_intersection_m is None
    )

    if schematic:
        day1_intersection_m = (
            day1_elevation["x_m"].min()
            + day1_elevation["x_m"].max()
        ) / 2

        day2_intersection_m = (
            day2_elevation["x_m"].min()
            + day2_elevation["x_m"].max()
        ) / 2

    day1_grid = _prepare_fence_surface(
        day1_model,
        day1_elevation,
        vmin,
        vmax,
        nx,
        nz,
        interpolation_space,
    )

    day2_grid = _prepare_fence_surface(
        day2_model,
        day2_elevation,
        vmin,
        vmax,
        nx,
        nz,
        interpolation_space,
    )

    XI1, _, Z1, C1, RHO1 = day1_grid
    XI2, _, Z2, C2, RHO2 = day2_grid

    # -----------------------------------------------------
    # Convert profile coordinates into perpendicular 
    # Relative coordinates that intersect at the origin
    # -----------------------------------------------------

    X1 = XI1 - day1_intersection_m
    Y1 = np.zeros_like(X1)

    X2 = np.zeros_like(XI2)
    Y2 = XI2 - day2_intersection_m

    log_min = np.log10(vmin)
    log_max = np.log10(vmax)

    decade_ticks = np.arange(
        np.ceil(log_min),
        np.floor(log_max) + 1,
    )

    decade_ticks = np.arange(
        np.ceil(log_min),
        np.floor(log_max) + 1,
    )

    decade_lables = [
        f"{10 ** value:,.0f}" for value in decade_ticks
    ]

    fig = go.Figure()

    #-----------------------------------------------------
    # Day 1 curtain
    #-----------------------------------------------------

    fig.add_trace(
        go.Surface(
            x = X1,
            y = Y1,
            z = Z1,
            surfacecolor = C1,
            colorscale = "Viridis",
            cmin = log_min,
            cmax = log_max,
            showscale = True,
            colorbar = {
                "title": "Resistivity<br>(Ω·m)",
                "tickvals": decade_ticks,
                "ticktext": decade_lables, 
            },
            customdata = RHO1,
            name = f"{array_name} Day 1",
            hovertemplate = (
                f"{array_name} Day 1<br>"
                "Relative distance: %{x:.1f} m<br>"
                "Elevation: %{z:.1f} m<br>"
                "Resistivity: %{customdata:,.1f} Ω·m"
                "<extra></extra>"
            ),
        )
    )

    #-----------------------------------------------------
    # Day 2 curtain
    #-----------------------------------------------------

    fig.add_trace(
        go.Surface(
            x = X2,
            y = Y2,
            z = Z2,
            surfacecolor = C2,
            colorscale = "Viridis",
            cmin = log_min,
            cmax = log_max,
            showscale = False,
            customdata = RHO2,
            name = f"{array_name} Day 2",
            hovertemplate = (
                f"{array_name} Day 2<br>"
                "Relative distance: %{y:.1f} m<br>"
                "Elevation: %{z:.1f} m<br>"
                "Resistivity: %{customdata:,.1f} Ω·m"
                "<extra></extra>"
            ),
        )
    )

    #-----------------------------------------------------
    # Measured ground-surface lines
    #-----------------------------------------------------

    day1_surface_x =(
        day1_elevation["x_m"].to_numpy()
        - day1_intersection_m
    )

    fig.add_trace(
        go.Scatter3d(
            x = day1_surface_x,
            y = np.zeros_like (day1_surface_x),
            z = day1_elevation["elevation_m"],
            mode = "lines",
            line = {
                "color": "black",
                "width": 5,
            },
            name = "Day 1 ground surface",
        )
    )

    day2_surface_y =(
        day2_elevation["x_m"].to_numpy()
        - day2_intersection_m
    )

    fig.add_trace(
        go.Scatter3d(
            x = np.zeros_like(day2_surface_y),
            y = day2_surface_y,
            z = day2_elevation["elevation_m"],
            mode = "lines",
            line = {
                "color": "black",
                "width": 5,
            },
            name = "Day 2 ground surface",
        )
    )

    if schematic:
        title = (
            "Schematic Pseudo-3D ERT Fence Diagram "
            f"({array_name} Array)"
        )

    else:
        title = (
            "Pseudo-3D ERT Fence Diagram "
            f"({array_name} Array)"
        )

    fig.update_layout(
        title = title,
        scene = {
            "xaxis_title": "Day 1 relative distance (m)",
            "yaxis_title": "Day 2 relative distance (m)",
            "zaxis_title" : "Elevation (m)",
            "aspectmode" : "data",
            "camera" : {
                "eye" : {
                    "x" : 1.5,
                    "y" : 1.5,
                    "z" : 0.8,
                }
            },
        },
        height = 750,
        margin = {
            "l" : 0,
            "r" : 0,
            "b" : 0,
            "t" : 50,
        },
    )

    return fig
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.interpolate 
from scipy.interpolate import griddata
from typing import Literal

def validate_topography_coverage(
        ert_df: pd.DataFrame,
        elevation_df: pd.DataFrame,
) -> None:
    """
    Check whether the topography data covers the ERT survey area.

    Parameters
    ----------
    ert_df: pd.DataFrame
        DataFrame containing ERT survey data with columns 'x_m'

    elevation_df: pd.DataFrame
        DataFrame containing topography data with columns 'x_m'

    Raises
    ------
    ValueError
        If the topography data does not cover the ERT survey area.

    """

    ert_x_min = ert_df["x_m"].min()
    ert_x_max = ert_df["x_m"].max()

    elevation_x_min = elevation_df["x_m"].min()
    elevation_x_max = elevation_df["x_m"].max()

    if (
        ert_x_min < elevation_x_min
        or ert_x_max > elevation_x_max
    ):
        raise ValueError(
            "Topography data does not cover the ERT survey area. "
            f"ERT model spans {ert_x_min:.1f} - {ert_x_max:.1f} m, "
            f"but elevation data spans {elevation_x_min:.1f} - {elevation_x_max:.1f} m."
        )

def add_topography_to_model(
        ert_df: pd.DataFrame,
        elevation_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert ERT model depth coordinates to absolute elevation.

    Ground-surface elevation is linearly interpolated between measured electrode elevations.
    Model elevation is then calcualated from the interpolated surface elevation. 

    Parameters
    ----------
    ert_df: pd.DataFrame
        ERT model data containing:
        - x_m
        - depth_positive_m

    elevation_df: pd.DataFrame
        Electrode elevation data containing:
        - x_m
        - elevation_m

    Returns
    -------
    pd.DataFrame
        Copy of the ERT model with two addttional columns:
        - surface_elevation_m
        - model_elevation_m

    Raises
    ------
    ValueError
        If the topography data does not cover the ERT survey area.

    """
    validate_topography_coverage(
        ert_df,
        elevation_df,
    )

    elevation_sorted = elevation_df.sort_values("x_m")

    surface_elevation = np.interp(
        ert_df["x_m"],
        elevation_sorted["x_m"],
        elevation_sorted["elevation_m"],
    )

    result = ert_df.copy()

    result["surface_elevation_m"] = surface_elevation

    result["model_elevation_m"] = (
        result["surface_elevation_m"] - result["depth_positive_m"]
    )

    return result

def interpolate_ert_grid(
        ert_df:pd.DataFrame,
        vertical_column: str = "depth_positive_m",
        nx: int = 400,
        nz: int = 200,
        interpolation_space: Literal["linear", "log10"] = "log10",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:

    """
    Interpolate irregular ERT model-block centers onto a regular grid

    Parameters
    ----------
    ert_df: pandas.DataFrame
        ERT model data.

    vertical_column : str, default="depth_positive_m"
        Column to use for the vertical coordinate.

        Examples:

        - "depth_positive_m" for depth sections
        - "model_elevation_m" for topographic sections

    nx: int, default=400
        Number of grid points in the horizontal direction

    nz: int, default=200
        Number of grid points in the vertical diraction

    log_resistivity: bool, default=False
        If Trye, interpolate log10 resistivity rather than raw resistivity values

    Returns
    -------
    tuple of numpy.ndarray
    XI
        Horizontal grid coordinates
    ZI 
        Vertical grid coordinates
    RHOI
        Interpolated resistivity values, or log10 resistivity 
        when "log_resistivity=True"

    """

    required_columns = {
        "x_m",
        vertical_column,
        "resistivity_ohm_m",
    }

    missing_columns = required_columns - set(ert_df.columns)

    if missing_columns:
        raise ValueError(
            "ERT data are missing required columns:"
            + ", ".join(sorted(missing_columns))
        )

    valid = (
        np.isfinite(ert_df["x_m"])
        & np.isfinite(ert_df[vertical_column])
        & np.isfinite(ert_df["resistivity_ohm_m"])
        & (ert_df["resistivity_ohm_m"] > 0)
    )

    data = ert_df.loc[valid].copy()

    x = data["x_m"].to_numpy()
    z = data[vertical_column].to_numpy()
    resistivity = data["resistivity_ohm_m"].to_numpy()

    if interpolation_space == "linear":
        values = resistivity

    elif interpolation_space == "log10":
        values = np.log10(resistivity)
    
    else:
        raise ValueError(
            "interpolation_space must be either "
            "'linear' or 'log10' ."
        )

    xi = np.linspace(
        x.min(),
        x.max(),
        nx,
    )

    zi = np.linspace(
        z.min(),
        z.max(),
        nz,
    )

    XI, ZI = np.meshgrid(
        xi,
        zi,
    )

    RHOI = griddata(
        points=(x, z),
        values=values,
        xi=(XI, ZI),
        method="linear",
    )

    if interpolation_space == "log10":
        RHOI = 10 ** RHOI

    return XI, ZI, RHOI

def crop_model_to_topography(
    ert_df: pd.DataFrame,
    elevation_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Crop an ERT inversion model to the horizontal extent covered
    by measured electrode elevations.

    Model blocks outside the measured survey-line footprint are
    excluded rather than extrapolating the topography.
    """

    minimum_x = elevation_df["x_m"].min()
    maximum_x = elevation_df["x_m"].max()

    cropped = ert_df.loc[
        ert_df["x_m"].between(
            minimum_x,
            maximum_x,
        )
    ].copy()

    if cropped.empty:
        raise ValueError(
            "No ERT model blocks fall within the "
            "measured topography extent."
        )

    return cropped
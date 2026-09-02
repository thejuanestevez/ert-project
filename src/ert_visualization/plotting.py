from collections.abc import Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure
from typing import Literal

from ert_visualization.processing import interpolate_ert_grid

def plot_ert_section(
        ert_df: pd.DataFrame,
        title: str,
        ax: Axes | None = None,
        vmin: float = 1.0,
        vmax: float = 10000.0,
        cmap: str = "viridis",
        nx: int = 400,
        nz: int = 200,
        interpolation_space: Literal["linear", "log10"] = "log10",
) -> tuple[Figure, Axes, object]:
    """
    Plot a 2-D ERT inversion secion in depth cooridnates.

    Resistivity is displayed using a logarthimic colour normalization 
    because ERT resistivity values commonly span several orders of magnitude

    Parameters
    ----------
    ert_df: ERT inversion model containing horizontal position, depth, and resistivity 

    title: Title shown above the section

    ax: existing axes on which to draw the section. If not supplied, a new figure & axes created

    vmin: lower limit of the log resistivity scale

    vmax: Upper limit of the log resistivity scale

    cmap: Matplotlib colourmap

    nz: Number of interpolation points in the vertical direction 

    Returns
    -------
    tuple: figures, axes, and plotted mesh

    """

    if vmin <= 0:
        raise ValueError(
            "vmin must be greater than zero for log scalling"
        )

    if vmax <= vmin:
        raise ValueError(
            "vmax must be greater than vmin"
        )

    if ax is None:
        fig, ax = plt.subplots(
            figsize= (10, 4.5),
        )

    else:
        fig = ax.figure

    XI, ZI, RHOI = interpolate_ert_grid (
        ert_df,
        vertical_column="depth_positive_m",
        nx=nx,
        nz=nz,
        interpolation_space=interpolation_space,
    )

    resistivity_grid = np.ma.masked_invalid(RHOI)

    norm = LogNorm(
        vmin=vmin,
        vmax=vmax,
    )

    mesh = ax.pcolormesh(
        XI,
        ZI,
        resistivity_grid,
        shading="auto",
        cmap=cmap,
        norm=norm,
    )

    ax.set_title(title)
    ax.set_xlabel("Distance along profile (m)")
    ax.set_ylabel("Depth below surface (m)")

    ax.set_xlim(
        ert_df["x_m"].min(),
        ert_df["x_m"].max(),
    )

    ax.set_ylim(
        ert_df["depth_positive_m"].max(),
        0,
    )

    ax.grid(
        alpha=0.2,
        linewidth=0.5,
    )

    return fig, ax, mesh

def plot_ert_comparison(
        ert_data: Mapping[str, pd.DataFrame],
        vmin: float = 1.0,
        vmax: float = 10000.0,
        cmap: str = "viridis",
        interpolation_space: str = "linear",
) -> Figure:
    """
    Plot the four ERT inversion datasets using a shared log color scale

    Parameters
    ----------
    ert_data: Dictionary like object containing four ERT datasets

    vmin: minimum resistivity show on colour scale

    vmax: max resisitivity shown on colour scale 

    cmap: Matplotlib color map 

    Returns
    -------
    Four panel comparision figure 
    """

    survey_order = [
        "Wenner Day 1",
        "Dipole-Dipole Day 1",
        "Wenner Day 2",
        "Dipole-Dipole Day 2",
    ]

    missing_surveys = [
        survey
        for survey in survey_order
        if survey not in ert_data
    ]

    if missing_surveys:
        raise ValueError(
            "Missing ERT datasets:"
            + ",".join(missing_surveys)
        )

    fig, axes = plt.subplots(
        nrows=2,
        ncols=2,
        figsize=(14,8),
        constrained_layout=True,
    )

    mesh = None

    for ax, survey_name in zip(
        axes.flat,
        survey_order,
        strict= True
    ):
        _, _, mesh = plot_ert_section(
            ert_df = ert_data[survey_name],
            title = survey_name,
            ax = ax,
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            interpolation_space=interpolation_space,
        )

    colorbar = fig.colorbar(
        mesh,
        ax=axes,
        orientation = "vertical",
        shrink = 0.85,
        pad = 0.03, 
        extend = "both",
    )

    colorbar.set_label(
        "Resistivity (Ω·m)"
    )

    fig.suptitle(
        "ERT Inversion Results: Wenner and Dipole-Diple Arrays",
        fontsize = 14,
    )

    return fig

def plot_ert_topography_section(
        ert_df: pd.DataFrame,
        elevation_df: pd.DataFrame,
        title: str,
        ax: Axes | None = None,
        vmin: float = 1.0,
        vmax: float = 10000.0,
        cmap: str = "viridis",
        nx: int = 400,
        nz: int = 200,
        interpolation_space: Literal["linear", "log10"] = "log10",
        show_legend: bool = True,
) -> tuple[Figure, Axes, object]:
    """
    Plot a 2-D ERT inversion model using absolute elevation.

    The ERT model must already contain topographic coordinates created by 'add_topography_to_model()'

    Resistivity is shown with logarithmic colour normalization. 

    Parameters
    ----------
    ert_df: Topography corrected ERT model contatining:
        - x_m
        - model_elevation_m
        - resistivity_ohm_m

    elevation_df: Measured electrode elevations containing:
        - x_m
        - elevation_m

    Returns
    --------
    tuple: Figure, aces, and plotted mesh 

    """
    if vmin <= 0:
        raise ValueError(
            "vmin must be greater than zero for logarithmic scaling."
        )

    if vmax <= vmin:
        raise ValueError(
            "vmax must be greater than vmin."
        )

    required_ert_columns = {
        "x_m",
        "model_elevation_m",
        "resistivity_ohm_m",
    }

    missing_ert_columns = (
        required_ert_columns - set(ert_df.columns)
    )

    if missing_ert_columns:
        raise ValueError(
            "ERT data are missing required columns: "
            + ", ".join(sorted(missing_ert_columns))
        )

    required_elevation_columns = {
        "x_m",
        "elevation_m",
    }

    missing_elevation_columns = (
        required_elevation_columns - set(elevation_df.columns)
    )

    if missing_elevation_columns:
        raise ValueError(
            "Elevation data are missing required columns: "
            + ", ".join(sorted(missing_elevation_columns))
        )

    if ax is None:
        fig, ax = plt.subplots(
            figsize=(10, 4.5),
        )

    else:
        fig = ax.figure

    # -----------------------------------------------------
    # Interpolate the inversion model in elevation coordinates
    # -----------------------------------------------------

    XI, ZI, RHOI = interpolate_ert_grid(
        ert_df,
        vertical_column="model_elevation_m",
        nx=nx,
        nz=nz,
        interpolation_space=interpolation_space,
    )

    # -----------------------------------------------------
    # Interpolate the measured ground surface onto the same
    # horizontal grid used for the ERT visualization
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Mask invalid interpolation and anything above ground
    # -----------------------------------------------------

    invalid_values = ~np.isfinite(RHOI)

    above_ground = ZI > surface_grid

    mask = (
        invalid_values
        | above_ground
    )

    resistivity_grid = np.ma.masked_where(
        mask,
        RHOI,
    )

    # -----------------------------------------------------
    # Plot resistivity section
    # -----------------------------------------------------

    norm = LogNorm(
        vmin=vmin,
        vmax=vmax,
    )

    mesh = ax.pcolormesh(
        XI,
        ZI,
        resistivity_grid,
        shading="auto",
        cmap=cmap,
        norm=norm,
    )

    # -----------------------------------------------------
    # Plot measured ground surface
    # -----------------------------------------------------

    ax.plot(
        elevation_sorted["x_m"],
        elevation_sorted["elevation_m"],
        color="black",
        linewidth=1.5,
        label="Ground surface",
    )

    # -----------------------------------------------------
    # Axes and formatting
    # -----------------------------------------------------

    ax.set_title(title)
    ax.set_xlabel("Distance along profile (m)")
    ax.set_ylabel("Elevation (m)")

    ax.set_xlim(
        ert_df["x_m"].min(),
        ert_df["x_m"].max(),
    )

    minimum_elevation = ert_df[
        "model_elevation_m"
    ].min()

    maximum_elevation = elevation_sorted[
        "elevation_m"
    ].max()

    elevation_range = (
        maximum_elevation
        - minimum_elevation
    )

    margin = max(
        1.0,
        0.03 * elevation_range,
    )

    ax.set_ylim(
        minimum_elevation - margin,
        maximum_elevation + margin,
    )

    ax.grid(
        alpha=0.2,
        linewidth=0.5,
    )

    if show_legend:
        ax.legend(
            loc="best",
        )

    return fig, ax, mesh


def plot_ert_topography_comparison(
    topographic_models: Mapping[str, pd.DataFrame],
    elevation_profiles: Mapping[str, pd.DataFrame],
    vmin: float = 1.0,
    vmax: float = 10000.0,
    cmap: str = "viridis",
    interpolation_space: Literal["linear", "log10"] = "log10",
) -> Figure:
    """
    Plot topography-corrected ERT inversion models using a shared
    logarithmic resistivity colour scale.

    The comparison includes only models for which measured elevation
    data cover the complete horizontal extent of the inversion.

    Parameters
    ----------
    topographic_models : mapping
        Dictionary containing topography-corrected ERT models.

    elevation_profiles : mapping
        Dictionary mapping each survey name to its corresponding
        electrode elevation data.
    
    Returns
    -------
    matplotlib.figure.Figure
        Three-panel topographic comparison figure.
    """

    survey_order = [
        "Wenner Day 1",
        "Wenner Day 2",
        "Dipole-Dipole Day 2",
    ]

    missing_models = [
        survey
        for survey in survey_order
        if survey not in topographic_models
    ]

    if missing_models:
        raise ValueError(
            "Missing topographic ERT models: "
            + ", ".join(missing_models)
        )

    missing_elevations = [
        survey
        for survey in survey_order
        if survey not in elevation_profiles
    ]

    if missing_elevations:
        raise ValueError(
            "Missing elevation profiles: "
            + ", ".join(missing_elevations)
        )

    fig, axes = plt.subplots(
        nrows=3,
        ncols=1,
        figsize=(12, 11),
        constrained_layout=True,
    )

    mesh = None

    for index, (ax, survey_name) in enumerate(
        zip(
            axes,
            survey_order,
            strict=True,
        )
    ):
        _, _, mesh = plot_ert_topography_section(
            ert_df=topographic_models[survey_name],
            elevation_df=elevation_profiles[survey_name],
            title=survey_name,
            ax=ax,
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            interpolation_space=interpolation_space,
            show_legend=(index == 0),
        )

    colorbar = fig.colorbar(
        mesh,
        ax=axes,
        orientation="vertical",
        shrink=0.8,
        pad=0.03,
        extend="both",
    )

    colorbar.set_label(
        "Resistivity (Ω·m)"
    )

    fig.suptitle(
        "ERT Inversion Models with Measured Topography",
        fontsize=14,
    )

    return fig
from collections.abc import Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure

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
        log_resistivity=False,
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
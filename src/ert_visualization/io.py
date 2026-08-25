from ast import If
from pathlib import Path
import numpy as np
import pandas as pd

def read_ert_xyz(filepath: str | Path) -> pd.DataFrame:
    """
    Reads the inverted model-block section of a RE2DINV-style XYZ file.
    The model-block section contains:
        X, Depth, Resistivity, Conductivity

    Parameters
    ----------
    filepath: str or pathlib.Path
        Path to the RE2DINV-style XYZ file.

    Returns
    -------
    pandas.DataFrame
        Model block data with columns:

        - x_m
        - depth_m
        - resistivity_ohm_m
        - conductivity_s_m
        - depth_positive_m

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.

    ValueError
        If the file format is invalid or does not contain the expected data.


    """

    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(
            f"The specified file does not exist: {filepath}"
        )

    with filepath.open("r", encoding="latin1") as f:
        lines = f.readlines()

    # -----------------------------------------------------
    # Find the number of inverted model blocks
    # -----------------------------------------------------

    block_line = next(
        (
            line
            for line in lines
            if "Number of blocks" in line
        ),
        None,
    )
    
    if block_line is None:
        raise ValueError(
            f"Could not find the number of blocks in {filepath}"
        ) 

    try:
        n_blocks = int(block_line.split()[-1])

    except ValueError as exc:
        raise ValueError(
            f"Could not parse the number of blocks in {filepath}"
        ) from exc


    # -----------------------------------------------------
    # Locate the model-block table
    # -----------------------------------------------------

    required_headers = {
        "X",
        "Depth",
        "Resistivity",
        "Conductivity",
    }

    header_index = next(
        (
            i for i, line in enumerate(lines)
            if required_headers.issubset(
                set(line.replace("/", " ").split())
            )
        ),
        None,
    )
    

    if header_index is None:
        raise ValueError(
            f"Could not find the model-block table header in {filepath}"
        )

    start_idx = header_index + 1
  
    # -----------------------------------------------------
    # Parse model blocks
    # -----------------------------------------------------

    rows = []

    model_lines = lines[start_idx:start_idx + n_blocks]

    for offset, line in enumerate(model_lines):
        line_number = start_idx + offset + 1
        parts = line.split()

        if len(parts) < 4:
            raise ValueError(
                f"Invalid model-block row at line "
                f"{line_number} in {filepath}"
            )

        try:
            x = float(parts[0])
            depth = float(parts[1])
            resistivity = float(parts[2])
            conductivity = float(parts[3])

        except ValueError as exc:
            raise ValueError(
                f"Could not parse numeric values at line "
                f"{line_number} in {filepath}"
            ) from exc

        rows.append(
            [
                x,
                depth,
                resistivity,
                conductivity,
            ]
        )

    if len(rows) != n_blocks:
        raise ValueError(
            f"Expected {n_blocks} model blocks in {filepath}, "
            f"but parsed {len(rows)}."
        )

    # -----------------------------------------------------
    # Create DataFrame
    # -----------------------------------------------------

    df = pd.DataFrame(
        rows,
        columns=[
            "x_m",
            "depth_m",
            "resistivity_ohm_m",
            "conductivity_s_m",
        ],
    )

    # RES2dINV stores depths below the surface as negative values, but we want to store them as positive values
    df["depth_positive_m"] = np.abs(df["depth_m"])

    # Resitivity must be positive for logarithimic plotting
    df = df[df["resistivity_ohm_m"] > 0].copy()

    return df


def read_electrode_elevations(filepath: str | Path,) -> pd.DataFrame:
    """
    Reads electrode locations and elevations from CSV.
    
    Required columns:
        "Electrode_number",
        "x_m", 
        "elevation_m",
        "line",

    """

    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"The specified file does not exist: {filepath}")

    df = pd.read_csv(filepath)

    required_columns = {
        "Electrode_number",
        "x_m",
        "elevation_m",
        "line",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"The following required columns are missing from the CSV file: {missing_columns}"
        )

    return df.sort_values(
        ["line", "x_m"]
    ).reset_index(drop=True)
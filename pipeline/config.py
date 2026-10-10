"""
Central settings for the BrainTwin pipeline.

Every step imports its paths from here, so the raw-data location, subject,
and fMRI run only need to change in one place.
"""

import argparse
import importlib.util
import sys
from pathlib import Path

# Python inside the braintwin conda env (used in the error message below)
BRAINTWIN_PYTHON = "/Users/neelrajan/anaconda3/envs/braintwin/bin/python"
REQUIRED_PACKAGES = ["nibabel", "numpy", "pandas", "networkx", "scipy", "matplotlib"]


def check_python_environment():
    """
    Stop with a clear message if this Python is missing the pipeline's packages
    (usually because the braintwin conda env isn't active).
    Input: none. Output: none; exits the program if packages are missing.
    """
    missing = [name for name in REQUIRED_PACKAGES if importlib.util.find_spec(name) is None]
    if missing:
        script = sys.argv[0] or "pipeline/<step>.py"
        print(f"This Python ({sys.executable}) is missing: {', '.join(missing)}\n"
              f"Run this step with the braintwin env instead:\n\n"
              f"    {BRAINTWIN_PYTHON} {script}\n\n"
              f"or, in your own terminal, first run:  conda activate braintwin",
              file=sys.stderr)
        sys.exit(1)


check_python_environment()

import pandas as pd  # noqa: E402  (must come after the environment check)

# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------

# Repo root = the folder that contains pipeline/, data/, web/
REPO_DIR = Path(__file__).resolve().parent.parent

# Raw HCP download (outside the repo; never commit it)
RAW_DATA_DIR = Path("/Users/neelrajan/Downloads")

DATA_DIR = REPO_DIR / "data"
ATLAS_DIR = DATA_DIR / "atlas"
DERIVED_DIR = DATA_DIR / "derived"
WEB_DATA_DIR = REPO_DIR / "web" / "public" / "data"
SUBJECTS_CSV = DATA_DIR / "subjects.csv"

# ---------------------------------------------------------------------------
# What we are processing right now
# ---------------------------------------------------------------------------

SUBJECT_ID = "subject_001"
# Default run. Any step can be pointed at another run with --run, e.g.
#   python pipeline/step2_parcellate.py --run rfMRI_REST2_LR
RUN_NAME = "rfMRI_REST1_LR"  # other options: rfMRI_REST1_RL, rfMRI_REST2_LR, rfMRI_REST2_RL
# The two scans compared in step 7 (same person, resting state, two different days)
RUNS_TO_COMPARE = ["rfMRI_REST1_LR", "rfMRI_REST2_LR"]

# HCP-Young Adult resting-state repetition time (seconds between fMRI frames)
TR_SECONDS = 0.72

# Graph measures use only the strongest connections: this fraction of all
# possible region pairs (0.10 = 10% -> 1,990 of 19,900 pairs for 200 regions)
GRAPH_DENSITY = 0.10

# Website export: include every connection with r above this (the site's
# slider filters further). 0.10 keeps ~7,750 of 19,900 pairs and still gives
# every region at least one connection.
EXPORT_EDGE_MIN_R = 0.10
# How many strongest partners (from the full matrix) to list per region
EXPORT_TOP_CONNECTIONS = 10

# ---------------------------------------------------------------------------
# Atlas
# ---------------------------------------------------------------------------

ATLAS_NAME = "Schaefer2018_200Parcels_7Networks_order"
ATLAS_DLABEL = ATLAS_DIR / f"{ATLAS_NAME}.dlabel.nii"
ATLAS_INFO_TXT = ATLAS_DIR / f"{ATLAS_NAME}_info.txt"
ATLAS_URL_BASE = (
    "https://raw.githubusercontent.com/ThomasYeoLab/CBIG/master/stable_projects/"
    "brain_parcellation/Schaefer2018_LocalGlobal/Parcellations/HCP/fslr32k/cifti/"
)

# Number of vertices per hemisphere on the fs_LR 32k surface
VERTICES_PER_HEMISPHERE = 32492

# The 7 Yeo networks in the atlas's own order, with their standard colors
# and readable names. Used for sorting, plots, and the website legend.
NETWORK_ORDER = ["Vis", "SomMot", "DorsAttn", "SalVentAttn", "Limbic", "Cont", "Default"]
NETWORK_COLORS = {
    "Vis": "#781286",
    "SomMot": "#4682b4",
    "DorsAttn": "#00760e",
    "SalVentAttn": "#c43afa",
    "Limbic": "#dcf8a4",
    "Cont": "#e69422",
    "Default": "#cd3e4e",
}
NETWORK_FULL_NAMES = {
    "Vis": "Visual",
    "SomMot": "Somatomotor",
    "DorsAttn": "Dorsal attention",
    "SalVentAttn": "Salience / ventral attention",
    "Limbic": "Limbic",
    "Cont": "Frontoparietal control",
    "Default": "Default mode",
}


def get_hcp_id(subject_id=SUBJECT_ID):
    """
    Look up the HCP subject number for one of our subject ids.
    Input: subject_id like "subject_001".
    Output: HCP id as a string, e.g. "125525".
    """
    subjects = pd.read_csv(SUBJECTS_CSV, dtype=str)
    match = subjects.loc[subjects["subject_id"] == subject_id, "hcp_id"]
    if match.empty:
        raise ValueError(f"{subject_id} is not listed in {SUBJECTS_CSV}")
    return match.iloc[0]


def get_raw_paths(subject_id=SUBJECT_ID, run_name=RUN_NAME, surface="midthickness"):
    """
    Build the paths to all raw HCP files we use for one subject and run.
    Inputs: subject_id, run_name (e.g. "rfMRI_REST1_LR"),
            surface ("midthickness", "pial", or "inflated").
    Output: dict of name -> Path.
    """
    hcp_id = get_hcp_id(subject_id)
    subject_dir = RAW_DATA_DIR / hcp_id / "MNINonLinear"
    surface_dir = subject_dir / "fsaverage_LR32k"
    run_dir = subject_dir / "Results" / run_name

    return {
        "mesh_L": surface_dir / f"{hcp_id}.L.{surface}_MSMAll.32k_fs_LR.surf.gii",
        "mesh_R": surface_dir / f"{hcp_id}.R.{surface}_MSMAll.32k_fs_LR.surf.gii",
        "fmri": run_dir / f"{run_name}_Atlas_MSMAll_hp2000_clean_rclean_tclean.dtseries.nii",
        "motion": run_dir / "Movement_RelativeRMS_mean.txt",
    }


def get_run_name():
    """
    Read which fMRI run to process from the command line (--run), or use RUN_NAME.
    Input: none (reads sys.argv). Output: run name string, e.g. "rfMRI_REST2_LR".
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--run", default=RUN_NAME)
    arguments, _unused = parser.parse_known_args()
    if not arguments.run.startswith("rfMRI_"):
        raise ValueError(f"--run should look like rfMRI_REST2_LR, got {arguments.run!r}")
    return arguments.run


def get_subject_dir(subject_id=SUBJECT_ID):
    """
    Folder for outputs that don't depend on the fMRI run (node positions,
    run comparisons). Input: subject_id. Output: Path (created if missing).
    """
    folder = DERIVED_DIR / subject_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_derived_dir(subject_id=SUBJECT_ID, run_name=RUN_NAME):
    """
    Folder where pipeline steps save their outputs for one subject and run:
    data/derived/<subject>/<run_name>/. Inputs: subject_id, run_name.
    Output: Path (created if missing).
    """
    folder = get_subject_dir(subject_id) / run_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder

# BrainTwin — Project Brief for Claude Code

## What this project is

BrainTwin turns brain-imaging data into an interactive 3D brain plus a 3D brain network
that researchers can explore in a web browser.

Long-term, it will hold many subjects, compare them, and use graph AI on brain networks.
**Right now the goal is small: get ONE subject working extremely well.**

Milestone 1:
Subject 001 → connectivity data → correct 3D graph → interactive website →
anatomical brain overlay → clickable regions with graph statistics.

## About me (how to work with me)

- I'm a data science student. Explain code in plain language.
- Use simple, readable variable names (`brain_points`, `region_labels`, not `bp`, `rl`).
- Put a short comment at the top of every function saying what it does, its inputs and outputs.
- Build the pipeline as **separate steps that each save their output to disk**. Each step should
  run on its own by reading the previous step's files. When we add a new extraction later,
  I want to run just that step, not re-run the whole pipeline.
- Work in phases. Stop at the end of each phase, show me what was produced, and tell me how to
  check it before moving on.

## Tech stack

- **Pipeline:** Python (nibabel, numpy, pandas, networkx, scipy). I use conda; create an env
  called `braintwin`.
- **Website:** React + Vite, with React Three Fiber (`@react-three/fiber`) and `@react-three/drei`
  for 3D.
- **No backend server for now.** The Python pipeline writes static files (JSON + binary arrays);
  the React app loads them. A FastAPI backend comes later when there are many subjects.

## The data (already downloaded)

Source: Human Connectome Project, HCP-Young Adult 2025 release. Healthy adult.
HCP subject ID **125525** = our **subject_001**. Keep this mapping in `data/subjects.csv`.

Raw data folder (outside the repo, never commit it — HCP data use terms restrict redistribution):

```
/Users/neelrajan/Downloads/125525
```

Store this path in a config file (`pipeline/config.py`), not hard-coded across scripts.

Files we use (paths relative to the raw folder):

| What | Path |
|---|---|
| Left surface mesh | `MNINonLinear/fsaverage_LR32k/125525.L.midthickness_MSMAll.32k_fs_LR.surf.gii` |
| Right surface mesh | `MNINonLinear/fsaverage_LR32k/125525.R.midthickness_MSMAll.32k_fs_LR.surf.gii` |
| Pial + inflated meshes (later, view toggle) | same folder, `pial_MSMAll` / `inflated_MSMAll` |
| Resting-state fMRI | `MNINonLinear/Results/rfMRI_REST1_LR/rfMRI_REST1_LR_Atlas_MSMAll_hp2000_clean_rclean_tclean.dtseries.nii` |
| Head motion (QC) | `MNINonLinear/Results/rfMRI_REST1_LR/Movement_RelativeRMS_mean.txt` |

Other runs exist (`REST1_RL`, `REST2_LR`, `REST2_RL`). Use only `REST1_LR` for now, but write
code so the run name is a parameter.

**Everything must stay in MNINonLinear space** so the network sits correctly on the mesh.

### Atlas (brain regions)

Use the **Schaefer 2018, 200 parcels, 7 networks** atlas, fs_LR 32k CIFTI version:
`Schaefer2018_200Parcels_7Networks_order.dlabel.nii`
from the CBIG GitHub repo (ThomasYeoLab/CBIG, under
`stable_projects/brain_parcellation/Schaefer2018_LocalGlobal/Parcellations/HCP/fslr32k/cifti/`).
Verify the exact URL before downloading. Save to `data/atlas/`.

Each parcel name encodes its hemisphere and network (e.g. `7Networks_LH_Vis_1`).
Parse these into `hemisphere`, `network`, and `region_name` columns.

## Important technical details

- The `.dtseries.nii` is a CIFTI file with ~91k "grayordinates": left cortex, right cortex
  (medial wall removed), and subcortical voxels. Use `nibabel`'s CIFTI axes
  (`BrainModelAxis`) to get which surface vertex each column belongs to.
- The atlas may store all 32,492 vertices per hemisphere (including medial wall) or only the
  cortex vertices. **Inspect both files' axes first** and map fMRI columns to atlas labels by
  vertex index, not by column position. Print the counts so I can see the match is correct.
- Surface meshes have 32,492 vertices per hemisphere. Mesh vertex index = CIFTI vertex index.

## Repo structure

```
braintwin/
├── CLAUDE.md
├── pipeline/
│   ├── config.py              # paths, subject list, run name
│   ├── step1_load_check.py    # load files, print shapes, sanity checks
│   ├── step2_parcellate.py    # average fMRI signal inside each region
│   ├── step3_connectivity.py  # correlation matrix between regions
│   ├── step4_node_positions.py# 3D position of each region on the mesh
│   ├── step5_graph_stats.py   # graph measurements per region
│   └── step6_export_web.py    # write files the website loads
├── data/
│   ├── subjects.csv           # subject_001,125525
│   ├── atlas/
│   └── derived/subject_001/   # outputs of each step (.npy / .csv)
└── web/
    ├── public/data/subject_001/   # exported files for the website
    └── src/
```

Add a `.gitignore` that excludes raw data and large derived files.

## Phases

### Phase 1 — Setup and loading check
- Create the conda env, repo folders, config, `subjects.csv`.
- Download the atlas.
- `step1_load_check.py`: load both meshes, the fMRI, and the atlas. Print vertex/triangle
  counts, fMRI shape (timepoints × grayordinates), number of timepoints, atlas region count,
  and how many cortex vertices match between fMRI and atlas.
- **Checkpoint:** show me the printout.

### Phase 2 — Connectivity
- `step2_parcellate.py`: for each of the 200 regions, average the fMRI signal across its
  vertices → `region_timeseries.npy` (timepoints × 200) and `regions.csv`
  (id, name, hemisphere, network, vertex count).
- `step3_connectivity.py`: Pearson correlation between every pair of regions →
  `connectivity.npy` (200 × 200). Also save the Fisher z-transformed version.
- Checks: matrix is symmetric, diagonal is 1, values within [-1, 1]. Save a heatmap PNG
  sorted by network (same-network blocks should look brighter).
- **Checkpoint:** show me the heatmap.

### Phase 3 — Graph
- `step4_node_positions.py`: for each region, average the midthickness coordinates of its
  vertices, then snap to the nearest vertex of that region so the node sits on the surface.
  Save `node_positions.csv` (x, y, z per region).
- `step5_graph_stats.py`: build the graph with networkx.
  - Keep the full weighted matrix for export.
  - For graph measures, keep the strongest 10% of positive connections (make density a
    parameter).
  - Per region: degree, strength (sum of weights), betweenness centrality, clustering
    coefficient, eigenvector centrality, network membership.
  - Whole-brain: density, average clustering, modularity using the Schaefer networks as
    communities.
  - Left vs right: average strength per network in each hemisphere.
  - Save `region_stats.csv` and `graph_summary.json`.
- Also save the subject's mean head motion in `graph_summary.json` as QC.
- **Checkpoint:** show me the top 10 regions by strength and by betweenness.

### Phase 4 — Export for the website
- `step6_export_web.py` writes to `web/public/data/subject_001/`:
  - `mesh_L_points.bin`, `mesh_L_triangles.bin`, same for R (Float32 / Uint32 raw arrays)
  - `mesh_L_region.bin`, `mesh_R_region.bin`: region id per vertex (0 = medial wall)
  - `graph.json`: nodes (id, name, hemisphere, network, x, y, z, all stats) and edges
    (source, target, weight) for connections above a low threshold
  - `subject.json`: subject id, HCP id, run, counts, QC info, file list
- Keep total size small enough to load quickly (print file sizes).

### Phase 5 — Website
- Vite + React app in `web/`.
- 3D view: both hemispheres as a semi-transparent brain mesh, orbit/zoom controls.
- Network layer toggle: nodes as spheres colored by network, edges as lines whose
  thickness/opacity follows connection strength.
- Slider for edge strength threshold.
- Click a node, or click the brain surface (look up the region of the clicked vertex), to open
  a side panel with: region name, network, hemisphere, its strongest connections, and its
  graph stats.
- Network legend with a toggle to show/hide each network.
- **Checkpoint:** run it locally and walk me through it.

### Later (don't build yet)
- Pial / inflated mesh toggle
- Subcortical regions (hippocampus, amygdala, thalamus) from the CIFTI volume part
- Averaging multiple runs (REST1/REST2, LR/RL)
- Diffusion-based structural network as a second layer
- Multiple subjects: download → extract → delete loop, database, FastAPI backend
- Population comparison, GNN brain embeddings, longitudinal analysis

# BrainTwin

Turns brain-imaging data from the Human Connectome Project (HCP) into an
interactive 3D brain and brain network you can explore in a web browser.

- `pipeline/` — Python steps that each read the previous step's files and save their own
- `web/` — React + React Three Fiber site that loads the exported files (no backend)
- `data/` — subject list, atlas, and derived outputs (raw and derived data are not committed)

## Setup

```bash
conda env create -f environment.yml
conda activate braintwin
```

## HCP data access

Raw data is downloaded from HCP's Amazon S3 bucket (`hcp-openaccess`), which needs
your own HCP access keys. HCP data use terms don't allow redistributing the data,
so it is never committed to this repo.

1. **Get keys.** Log in to ConnectomeDB (https://db.humanconnectome.org), accept the
   HCP Open Access Data Use Terms, and use its Amazon S3 access option to generate an
   access key and secret key.
2. **Save them** in a file called `.hcp_credentials` in the project root (next to this
   README), exactly like this, with no quotes or spaces:

   ```
   HCP_ACCESS_KEY=your-access-key
   HCP_SECRET_KEY=your-secret-key
   ```

   The file is listed in `.gitignore`, so it is never committed. Make it readable only
   by you:

   ```bash
   chmod 600 .hcp_credentials
   ```

   The pipeline reads the keys from this file and never prints them.
3. **Download a subject** (HCP subject id, e.g. 125525):

   ```bash
   python pipeline/step0_fetch_subject.py 125525
   ```

   Files go to `RAW_DATA_DIR` in `pipeline/config.py` (`--dest` picks another folder),
   in the same layout HCP uses. Only the files the pipeline needs are fetched (about
   880 MB per subject): left/right midthickness surfaces, the cleaned resting-state fMRI
   for REST1_LR and REST2_LR, and their head-motion summaries. Files already downloaded
   are skipped, and every file is opened after download to check it's readable.

### Which fMRI version

The pipeline uses `<run>_Atlas_MSMAll_hp2000_clean.dtseries.nii` (the HCP_1200 release's
sICA+FIX-cleaned data), set by `FMRI_FILE_ENDING` in `pipeline/config.py`. The 2025
release's extra-cleaned `..._hp2000_clean_rclean_tclean` files are not on the S3 bucket,
so they can't be fetched automatically; using the S3 version for every subject keeps the
preprocessing identical across subjects.

## Pipeline

Run each step from the project root with the `braintwin` environment active.
Steps that depend on the scan take `--run` (default `rfMRI_REST1_LR`).

| Step | What it does |
|---|---|
| `step0_fetch_subject.py <hcp_id>` | Download one subject's raw files from HCP S3 |
| `step1_load_check.py` | Load everything and print sanity checks |
| `step2_parcellate.py` | Average the fMRI signal inside each of 200 regions |
| `step3_connectivity.py` | Correlation between every pair of regions |
| `step4_node_positions.py` | 3D position of each region on the brain surface |
| `step5_graph_stats.py` | Graph measures per region and for the whole brain |
| `step7_compare_runs.py` | Compare REST1 with REST2 (reproducibility) |
| `step6_export_web.py` | Write the files the website loads (run after step 7 so the site includes the comparison) |

## Website

```bash
cd web
npm install
npm run dev
```

Then open http://localhost:5173.

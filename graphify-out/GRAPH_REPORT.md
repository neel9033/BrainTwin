# Graph Report - braintwin  (2026-10-13)

## Corpus Check
- Corpus is ~18,778 words - fits in a single context window. You may not need a graph.

## Summary
- 304 nodes · 651 edges · 9 communities (8 shown, 1 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.82)
- Token cost: 58,992 input · 0 output

## Community Hubs (Navigation)
- Connectivity, Graph Stats & Export
- Brain Data Loading & Checks
- Config & HCP S3 Fetch
- 3D Brain Scene Rendering
- Panels & Plain-Language Text
- App Shell & Data Loader
- Web Build Dependencies
- Project Docs & Data Access
- Run Label Helper

## God Nodes (most connected - your core abstractions)
1. `App()` - 18 edges
2. `main()` - 14 edges
3. `load_atlas()` - 13 edges
4. `get_derived_dir()` - 13 edges
5. `main()` - 13 edges
6. `load_mesh()` - 12 edges
7. `NetworkLayer()` - 12 edges
8. `main()` - 11 edges
9. `main()` - 11 edges
10. `main()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Static React Three Fiber Website (no backend)` --references--> `Website HTML Entry Page`  [INFERRED]
  README.md → web/index.html
- `Step 0: Fetch Subject from HCP S3` --conceptually_related_to--> `boto3 Dependency`  [INFERRED]
  README.md → environment.yml
- `Step-by-Step Python Pipeline` --conceptually_related_to--> `networkx Dependency`  [INFERRED]
  README.md → environment.yml
- `Step-by-Step Python Pipeline` --conceptually_related_to--> `nibabel Dependency`  [INFERRED]
  README.md → environment.yml
- `verify_file()` --calls--> `load_mesh()`  [EXTRACTED]
  pipeline/step0_fetch_subject.py → pipeline/brain_io.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **HCP Data Access Flow** — readme_connectomedb, readme_hcp_data_use_terms, readme_hcp_credentials_file, readme_hcp_openaccess_s3_bucket, readme_subject_fetch_step [EXTRACTED 0.95]

## Communities (9 total, 1 thin omitted)

### Community 0 - "Connectivity, Graph Stats & Export"
Cohesion: 0.05
Nodes (29): get_derived_dir(), get_hcp_id(), get_subject_dir(), check_matrix(), compute_connectivity(), main(), network_sort_order(), plot_heatmap() (+21 more)

### Community 1 - "Brain Data Loading & Checks"
Cohesion: 0.07
Nodes (25): get_cortex_columns(), load_atlas(), load_fmri(), load_mesh(), parse_region_name(), get_raw_paths(), check_atlas(), check_files_only() (+17 more)

### Community 2 - "Config & HCP S3 Fetch"
Cohesion: 0.09
Nodes (10): check_python_environment(), get_raw_paths_for_hcp_id(), get_run_name(), fetch_subject(), files_to_fetch(), format_size(), load_credentials(), main() (+2 more)

### Community 3 - "3D Brain Scene Rendering"
Cohesion: 0.12
Nodes (26): react, @react-three/fiber, three, BrainScene(), FirstFrameSignal(), KeyLight(), SCENE_BACKGROUND, BrainSurface() (+18 more)

### Community 4 - "Panels & Plain-Language Text"
Cohesion: 0.13
Nodes (21): react-dom, CollapsibleSection(), ControlPanel(), InfoTip(), buildPairs(), COLORS, PADDING, ReproducibilityScatter() (+13 more)

### Community 5 - "App Shell & Data Loader"
Cohesion: 0.13
Nodes (12): App(), buildLookups(), computeRanks(), DEFAULT_SETTINGS, hasSeenIntro(), rememberIntroSeen(), IntroPanel(), LoadingScreen() (+4 more)

### Community 6 - "Web Build Dependencies"
Cohesion: 0.10
Nodes (20): @react-three/drei, vite, @vitejs/plugin-react, dependencies, react, react-dom, @react-three/drei, @react-three/fiber (+12 more)

### Community 7 - "Project Docs & Data Access"
Cohesion: 0.13
Nodes (15): boto3 Dependency, braintwin Conda Environment, networkx Dependency, nibabel Dependency, BrainTwin Project, ConnectomeDB, HCP Credentials File (.hcp_credentials), HCP S3 Bucket (hcp-openaccess) (+7 more)

## Knowledge Gaps
- **3 isolated node(s):** `RAW_DATA_DIR Config Setting`, `--run Scan Parameter (default rfMRI_REST1_LR)`, `#root Mount Div`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 125 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `3D Brain Scene Rendering` to `Panels & Plain-Language Text`, `App Shell & Data Loader`, `Web Build Dependencies`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **What connects `RAW_DATA_DIR Config Setting`, `--run Scan Parameter (default rfMRI_REST1_LR)`, `#root Mount Div` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Connectivity, Graph Stats & Export` be split into smaller, more focused modules?**
  _Cohesion score 0.05136986301369863 - nodes in this community are weakly interconnected._
- **Why does `Website HTML Entry Page` connect `Project Docs & Data Access` to `App Shell & Data Loader`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Should `Brain Data Loading & Checks` be split into smaller, more focused modules?**
  _Cohesion score 0.06980433632998413 - nodes in this community are weakly interconnected._
- **Should `Config & HCP S3 Fetch` be split into smaller, more focused modules?**
  _Cohesion score 0.0907563025210084 - nodes in this community are weakly interconnected._
- **Should `3D Brain Scene Rendering` be split into smaller, more focused modules?**
  _Cohesion score 0.11932773109243698 - nodes in this community are weakly interconnected._
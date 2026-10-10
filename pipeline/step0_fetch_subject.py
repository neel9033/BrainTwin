"""
Step 0 - Download one subject's raw files from the Human Connectome Project's
Amazon S3 bucket.

Downloads only what the pipeline uses, for each run in config.RUNS_TO_COMPARE:
  - left and right midthickness surfaces (fs_LR 32k, MSMAll)
  - the cleaned resting-state fMRI (<run>_<config.FMRI_FILE_ENDING>)
  - the mean head-motion file (Movement_RelativeRMS_mean.txt)
Files already present with the right size are skipped. Each file is downloaded
to "<name>.part" and only renamed once complete, so an interrupted download is
never mistaken for a finished one. Every file is opened after download to make
sure it's readable.

Needs:  .hcp_credentials in the repo root (see README) and the boto3 package.
Writes: <dest>/<hcp_id>/MNINonLinear/... (same layout as HCP, so the pipeline's
        config.get_raw_paths finds the files when dest = config.RAW_DATA_DIR)

Run:    python pipeline/step0_fetch_subject.py 125525
        python pipeline/step0_fetch_subject.py 125525 --dest /path/to/test_folder
"""

import config  # first: stops early with a clear message if the wrong Python is used

import argparse
import sys
import time
from pathlib import Path

import boto3
import nibabel as nib
import numpy as np
from botocore.exceptions import ClientError

from brain_io import load_mesh


def load_credentials(credentials_path):
    """
    Read the HCP access and secret keys from the credentials file.
    The keys are never printed or logged.
    Input: path to .hcp_credentials. Output: (access_key, secret_key).
    """
    if not credentials_path.exists():
        sys.exit(f"No credentials file at {credentials_path}. See 'HCP data access' in README.md.")
    values = {}
    for line in credentials_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip('"').strip("'")
    missing = [name for name in ("HCP_ACCESS_KEY", "HCP_SECRET_KEY") if not values.get(name)]
    if missing:
        sys.exit(f"{credentials_path.name} is missing: {', '.join(missing)} (see README.md).")
    return values["HCP_ACCESS_KEY"], values["HCP_SECRET_KEY"]


def files_to_fetch(hcp_id, runs, dest):
    """
    List every file the pipeline needs for one subject.
    Inputs: hcp_id, list of run names, destination folder.
    Output: list of (kind, local Path, S3 key), surfaces first, no duplicates.
    """
    wanted = []
    for run_name in runs:
        paths = config.get_raw_paths_for_hcp_id(hcp_id, run_name, "midthickness", dest)
        for kind in ("mesh_L", "mesh_R", "fmri", "motion"):
            local_path = paths[kind]
            relative = local_path.relative_to(dest).as_posix()  # <hcp_id>/MNINonLinear/...
            entry = (kind, local_path, f"{config.HCP_S3_PREFIX}/{relative}")
            if entry not in wanted:
                wanted.append(entry)
    return wanted


def format_size(n_bytes):
    """Input: bytes. Output: readable size like '418.4 MB'."""
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024 or unit == "GB":
            return f"{n_bytes:.1f} {unit}" if unit != "B" else f"{n_bytes} B"
        n_bytes /= 1024


class ProgressPrinter:
    """Prints download progress for one file on a single updating line."""

    def __init__(self, name, total_bytes):
        """Inputs: file name to show, its total size in bytes."""
        self.name, self.total, self.done, self.last_print = name, total_bytes, 0, 0.0

    def __call__(self, chunk_bytes):
        """Called by boto3 with each chunk size received."""
        self.done += chunk_bytes
        now = time.monotonic()
        if now - self.last_print > 0.5 or self.done >= self.total:
            self.last_print = now
            percent = 100 * self.done / self.total if self.total else 100
            print(f"\r    {percent:5.1f}%  {format_size(self.done)} / {format_size(self.total)}", end="", flush=True)


def verify_file(kind, path):
    """
    Open a downloaded file to make sure it's complete and readable.
    Inputs: kind ("mesh_L", "mesh_R", "fmri", "motion"), file path.
    Output: short description of what was found (raises if the file is bad).
    """
    if kind in ("mesh_L", "mesh_R"):
        points, triangles = load_mesh(path)
        if len(points) != config.VERTICES_PER_HEMISPHERE:
            raise ValueError(f"expected {config.VERTICES_PER_HEMISPHERE} vertices, found {len(points)}")
        return f"{len(points):,} vertices, {len(triangles):,} triangles"
    if kind == "fmri":
        image = nib.load(str(path))
        first_frame = np.asarray(image.dataobj[0:1, :])  # read a little data, not all 400 MB
        if not np.isfinite(first_frame).all():
            raise ValueError("first frame contains NaN or infinite values")
        return f"{image.shape[0]:,} timepoints x {image.shape[1]:,} grayordinates"
    if kind == "motion":
        value = float(np.loadtxt(path))
        return f"mean relative motion {value:.4f} mm"
    raise ValueError(f"unknown file kind {kind}")


def fetch_subject(hcp_id, dest, runs, client):
    """
    Download (or skip) and verify every needed file for one subject.
    Inputs: hcp_id, destination folder, run names, boto3 S3 client.
    Output: dict with downloaded/skipped counts and bytes (exits on any failure).
    """
    summary = {"downloaded_files": 0, "downloaded_bytes": 0, "skipped_files": 0, "skipped_bytes": 0}
    wanted = files_to_fetch(hcp_id, runs, dest)
    print(f"Subject {hcp_id}: {len(wanted)} files -> {dest / hcp_id}\n")

    for kind, local_path, key in wanted:
        print(f"  {local_path.relative_to(dest)}")
        try:
            remote_size = client.head_object(Bucket=config.HCP_S3_BUCKET, Key=key)["ContentLength"]
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code", "?")
            sys.exit(f"    Could not find s3://{config.HCP_S3_BUCKET}/{key} (error {code}). "
                     "Check the subject id and that your HCP credentials are valid.")

        if local_path.exists() and local_path.stat().st_size == remote_size:
            print(f"    already downloaded ({format_size(remote_size)}) - skipped")
            summary["skipped_files"] += 1
            summary["skipped_bytes"] += remote_size
        else:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            partial_path = local_path.with_name(local_path.name + ".part")
            client.download_file(config.HCP_S3_BUCKET, key, str(partial_path),
                                 Callback=ProgressPrinter(local_path.name, remote_size))
            print()
            if partial_path.stat().st_size != remote_size:
                sys.exit(f"    Size mismatch after download ({partial_path.stat().st_size} vs {remote_size}).")
            partial_path.rename(local_path)
            summary["downloaded_files"] += 1
            summary["downloaded_bytes"] += remote_size

        try:
            print(f"    opens OK: {verify_file(kind, local_path)}")
        except Exception as error:  # any read failure means the file can't be used
            sys.exit(f"    Could not open {local_path.name}: {error}. Delete it and run step 0 again.")
    return summary


def main():
    """
    Parse the subject id and destination, download the subject's files,
    and print what was downloaded.
    """
    parser = argparse.ArgumentParser(description="Download one HCP subject's files from S3.")
    parser.add_argument("hcp_id", help="HCP subject id, e.g. 125525")
    parser.add_argument("--dest", type=Path, default=config.RAW_DATA_DIR,
                        help=f"folder that will hold <hcp_id>/ (default {config.RAW_DATA_DIR})")
    parser.add_argument("--runs", nargs="+", default=config.RUNS_TO_COMPARE, help="runs to fetch")
    arguments = parser.parse_args()
    if not arguments.hcp_id.isdigit():
        sys.exit(f"HCP subject ids are numbers like 125525, got {arguments.hcp_id!r}")

    access_key, secret_key = load_credentials(config.HCP_CREDENTIALS_FILE)
    client = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                          region_name=config.HCP_S3_REGION)

    started = time.monotonic()
    summary = fetch_subject(arguments.hcp_id, arguments.dest.expanduser().resolve(), arguments.runs, client)
    minutes = (time.monotonic() - started) / 60

    print(f"\nSubject {arguments.hcp_id} done in {minutes:.1f} min:")
    print(f"  downloaded {summary['downloaded_files']} files, {format_size(summary['downloaded_bytes'])}")
    print(f"  skipped    {summary['skipped_files']} files already present, {format_size(summary['skipped_bytes'])}")
    print(f"  total on disk for this subject: {format_size(summary['downloaded_bytes'] + summary['skipped_bytes'])}")
    print("  every file opened successfully")


if __name__ == "__main__":
    main()

# SAP Web Dispatcher Audit Tool

## Overview
This Python script is an auditing and reporting tool designed specifically for SAP Web Dispatcher instances running on Linux. It scans the local filesystem for SAP Web Dispatcher installations, checks for binary consistency, executes the binary to retrieve version information, and generates a clear, color-coded HTML report.

## Purpose
In enterprise SAP environments, ensuring that Web Dispatcher binaries are consistent across directories and up-to-date is critical for security and stability. This script automates that verification process by:
1. Discovering all local Web Dispatcher instances (`W<XX>`).
2. Identifying discrepancies between the instance-specific binary and the global executable.
3. Extracting exactly which Kernel Release and Patch Number is actively installed.
4. Flagging outdated binaries (compiled more than 1 year ago).

## Prerequisites
* **OS:** Linux/Unix (Relies on Unix-specific paths and the `os.stat`/`grp` modules).
* **Python:** Python 3.6 or newer.
* **Permissions:** * Read access to `/usr/sap/` directories.
    * The executing user should ideally be a member of the `sapsys` group. The script will issue a warning to `stderr` if run by a non-`sapsys` user (unless run as `root`), as this may prevent it from traversing certain directories or executing the binaries.

## How it Works

### 1. Discovery
The script scans the `/usr/sap/` directory for standard SAP instance patterns matching `[A-Z][A-Z0-9][A-Z0-9]/W[0-9][0-9]`. For each match, it extracts the 3-character SID (System ID).

### 2. Binary Consistency Check (The "State" Column)
For each discovered instance, the script looks for the `sapwebdisp` binary in two locations:
* **Instance path:** `/usr/sap/<SID>/W<XX>/exe/sapwebdisp`
* **Global path:** `/usr/sap/<SID>/SYS/exe/run/sapwebdisp`

It compares the two files. They are marked as **`OK` (Green)** only if:
* Both files exist.
* They have the exact same file size.
* They have the exact same modification timestamp (`mtime`).

If only one exists, or if the size/timestamps differ, the instance is marked as **`Inconsistent` (Red)**.

### 3. Execution & Version Extraction
The script executes the binary using the `-version` flag to retrieve the patch details.
* To ensure the binary can find its required shared libraries (`.so` files), the script dynamically sets the `LD_LIBRARY_PATH` environment variable to the directory containing the binary.
* It parses the standard output to extract:
    * `kernel release`
    * `patch number`
    * `compile time`

### 4. Age Verification
The `compile time` is parsed. If the compilation date is strictly older than one year from the current system date, the date is highlighted in **Red** in the final report to indicate that an update should be considered. Otherwise, it is colored **Green**.

## Usage

Simply run the script. It requires no arguments. Standard output (`stdout`) contains the raw HTML, while warnings or errors are sent to standard error (`stderr`).

```bash
# Run the script and save the output to an HTML file
./sap_webdisp_audit.py > webdisp_report.html

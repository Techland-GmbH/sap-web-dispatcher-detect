#!/usr/bin/env python3
import glob
import grp
import html
import os
import re
import subprocess
import sys
from datetime import datetime


def check_sapsys_group():
    """Check if the user is a member of 'sapsys'."""
    try:
        # Get the group ID for 'sapsys'
        sapsys_gid = grp.getgrnam('sapsys').gr_gid

        # Get user's current groups (supplementary + primary)
        user_groups = os.getgroups()
        user_groups.append(os.getgid())

        if sapsys_gid not in user_groups and os.geteuid() != 0:
            print("Warning: The current user is not a member of the "
                  "'sapsys' group. This might limit the capability to "
                  "find and collect all information.", file=sys.stderr)
    except KeyError:
        print("Warning: The group 'sapsys' does not exist on this system.", file=sys.stderr)
    except OSError as e:
        print(f"Warning: Could not verify group membership ({e}).", file=sys.stderr)


def compare_binaries(loc1, loc2):
    """Compare existence, size, and modification date of two files."""

    # If only one file exists, it's inconsistent
    if os.path.exists(loc1) != os.path.exists(loc2):
        return "Inconsistent", "red"

    # If both exist, check size and modification date
    try:
        stat1 = os.stat(loc1)
        stat2 = os.stat(loc2)

        if stat1.st_size == stat2.st_size and stat1.st_mtime == stat2.st_mtime:
            return "OK", "green"
        else:
            return "Inconsistent", "red"
    except OSError as e:
        # Catch specific OS errors (e.g., PermissionError) and log them safely
        print(f"Warning: Could not stat files for comparison ({e})", file=sys.stderr)
        return "Inconsistent", "red"


def get_date_color(date_str):
    """Check date age and return appropriate color."""
    # Normalize multiple spaces (e.g., "Jan  5 2025" -> "Jan 5 2025")
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    try:
        parsed_date = datetime.strptime(date_str, "%b %d %Y %H:%M:%S")
        now = datetime.now()

        # Calculate exactly one year ago, handling leap years safely
        try:
            one_year_ago = now.replace(year=now.year - 1)
        except ValueError:
            # Handles if current date is Feb 29 and last year wasn't a leap year
            one_year_ago = now.replace(year=now.year - 1, day=28)

        if parsed_date < one_year_ago:
            return 'red'
        else:
            return 'green'
    except ValueError:
        # If the date format is unexpected, default to not coloring it
        return 'inherit'


def collect_data():
    """Discover, verify, execute sapwebdisp and collect data."""
    entries = []

    # Find all SAP Web Dispatcher instance directories
    sap_dirs = sorted(glob.glob('/usr/sap/[A-Z][A-Z0-9][A-Z0-9]'))

    for path in sap_dirs:
        # Extract SID from path (e.g., '/usr/sap/A52/' -> 'A52')
        sid = path.split('/')[3]

        wdisp_instance = glob.glob(f'{path}/W[0-9][0-9]/exe/sapwebdisp')
        wdisp_global = f'{path}/SYS/exe/run/sapwebdisp'

        if len(wdisp_instance) > 1:
            print(f"Warning: Multiple sapwebdisp binaries found in {path}. Using the first one found.", file=sys.stderr)
        wdisp_instance = wdisp_instance[0] if wdisp_instance else ""

        state_text, state_color = compare_binaries(wdisp_instance, wdisp_global)

        entry = {'sid': sid, 'release': 'N/A', 'patch': 'N/A', 'date': 'N/A', 'state': state_text,
                 'state_color': state_color, 'date_color': 'inherit'}

        bin_to_run = wdisp_instance if os.path.exists(wdisp_instance) else wdisp_global

        # 1. Build the command array directly (without the 'env' command)
        cmd = [bin_to_run, '-version']

        # 2. Copy the current environment and inject the correct LD_LIBRARY_PATH
        custom_env = os.environ.copy()
        custom_env['LD_LIBRARY_PATH'] = bin_to_run.rsplit('/', 1)[0]

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                                    env=custom_env, check=False)
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("kernel release"):
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        entry['release'] = parts[1].strip()

                elif line.startswith("compile time"):
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        d_str = parts[1].strip()
                        entry['date'] = d_str
                        entry['date_color'] = get_date_color(d_str)

                elif line.startswith("patch number"):
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        entry['patch'] = parts[1].strip()
        except (OSError, subprocess.SubprocessError) as e:
            print(f"Error executing {bin_to_run}: {e}", file=sys.stderr)

        entries.append(entry)

    return entries


def generate_html(data):
    """Generates the HTML table with the collected data."""
    html_content = ["<!DOCTYPE html>", '<html lang="en">', "<head>", '    <meta charset="UTF-8">',
                    '    <title>SAP Web Dispatcher Audit Report</title>', "    <style>",
                    "        body { font-family: sans-serif; margin: 20px; }", "        h2 { text-align: center; }",
                    "        table { border-collapse: collapse; margin: 0 auto; }",
                    "        th, td { border: 1px solid #ddd; padding: 10px; }",
                    "        th { background-color: #0070b8; color: white; }",
                    "        tr:nth-child(even) { background-color: #f9f9f9; }",
                    "        .red { color: #d32f2f; font-weight: bold; }",
                    "        .green { color: #2e7d32; font-weight: bold; }", "    </style>", "</head>", "<body>",
                    "    <h2>SAP Web Dispatcher Versions & Consistency</h2>", "    <table>", "        <thead>",
                    "            <tr>", "                <th>Number</th>", "                <th>SID</th>",
                    "                <th>Release</th>", "                <th>Patch Number</th>",
                    "                <th>Date</th>", "                <th>State</th>", "            </tr>",
                    "        </thead>", "        <tbody>"]

    for i, entry in enumerate(data, start=1):
        sid = html.escape(entry.get('sid', 'N/A'))
        rel = html.escape(entry.get('release', 'N/A'))
        pat = html.escape(entry.get('patch', 'N/A'))
        date = html.escape(entry.get('date', 'N/A'))

        st_text = entry['state']
        st_cls = "green" if entry['state_color'] == "green" else "red"

        d_color = entry['date_color']
        d_style = f' style="color: {d_color}; font-weight: bold;"' if d_color in ('red', 'green') else ''

        html_content.extend(["            <tr>", f"                <td>{i}</td>", f"                <td>{sid}</td>",
                             f"                <td>{rel}</td>", f"                <td>{pat}</td>",
                             f"                <td{d_style}>{date}</td>",
                             f'                <td class="{st_cls}">{st_text}</td>', "            </tr>"])

    html_content.extend(["        </tbody>", "    </table>", "</body>", "</html>"])

    return "\n".join(html_content)


def main():
    # 1. Run the prerequisite check
    check_sapsys_group()

    # 2. Collect data from filesystem and executions
    parsed_data = collect_data()

    # 3. Output standard HTML to stdout
    print(generate_html(parsed_data))


if __name__ == "__main__":
    main()

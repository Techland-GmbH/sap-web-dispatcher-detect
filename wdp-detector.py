#!/usr/bin/env python3
import os
import sys
import glob
import subprocess
import re
from datetime import datetime
import html
import grp

def check_sapsys_group():
    """Requirement 6: Check if the user is a member of 'sapsys'."""
    try:
        # Get the group ID for 'sapsys'
        sapsys_gid = grp.getgrnam('sapsys').gr_gid

        # Get user's current groups (supplementary + primary)
        user_groups = os.getgroups()
        user_groups.append(os.getgid())

        if sapsys_gid not in user_groups and os.geteuid() != 0:
            print("Warning: The current user is not a member of the 'sapsys' group. "
                  "This might limit the capability to find and collect all information.",
                  file=sys.stderr)
    except KeyError:
        print("Warning: The group 'sapsys' does not exist on this system.", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not verify group membership ({e}).", file=sys.stderr)

def compare_binaries(loc1, loc2):
    """Requirement 2: Compare existence, size, and modification date."""
    exists1 = os.path.exists(loc1)
    exists2 = os.path.exists(loc2)

    # If only one file exists, it's inconsistent
    if exists1 != exists2:
        return "Inconsistent", "red"

    # If both exist, check size and modification date
    if exists1 and exists2:
        try:
            stat1 = os.stat(loc1)
            stat2 = os.stat(loc2)

            if stat1.st_size == stat2.st_size and stat1.st_mtime == stat2.st_mtime:
                return "OK", "green"
            else:
                return "Inconsistent", "red"
        except Exception:
            return "Inconsistent", "red"

    # If neither exists, this shouldn't happen based on our glob logic, but handle it cleanly
    return "Inconsistent", "red"

def is_older_than_one_year(date_str):
    """Requirement 5: Check if the compile time is older than 1 year."""
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

        return parsed_date < one_year_ago
    except ValueError:
        # If the date format is unexpected, default to not coloring it
        return False

def collect_data():
    """Main function to discover, verify, and execute sapwebdisp."""
    entries = []

    # Find all Web Dispatcher instance directories
    # Matches: /usr/sap/[A-Z][A-Z0-9][A-Z0-9]/W[0-9][0-9]
    instance_dirs = glob.glob('/usr/sap/[A-Z][A-Z0-9][A-Z0-9]/W[0-9][0-9]')

    # Sort for deterministic output
    instance_dirs.sort()

    for w_dir in instance_dirs:
        # Extract SID from path (e.g., '/usr/sap/A52/W87' -> 'A52')
        path_parts = w_dir.split('/')
        sid = path_parts[3]

        loc1 = f'{w_dir}/exe/sapwebdisp'
        loc2 = f'/usr/sap/{sid}/SYS/exe/run/sapwebdisp'

        # Skip if BOTH are missing (not a real web dispatcher installation)
        if not os.path.exists(loc1) and not os.path.exists(loc2):
            continue

        entry = {
            'sid': sid,
            'release': 'N/A',
            'patch': 'N/A',
            'date': 'N/A',
            'state': 'Inconsistent',
            'state_color': 'red',
            'date_color': 'inherit' # Default text color
        }

        # Check binary consistency
        state_text, state_color = compare_binaries(loc1, loc2)
        entry['state'] = state_text
        entry['state_color'] = state_color

        # Requirement 3: Determine which binary to run
        bin_to_run = loc1 if os.path.exists(loc1) else loc2

        # Requirement 3 & 4: Execute the command and capture output
        cmd = ['env', f'LD_LIBRARY_PATH={w_dir}', bin_to_run, '-version']

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

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
                        if is_older_than_one_year(d_str):
                            entry['date_color'] = 'red'

                elif line.startswith("patch number"):
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        entry['patch'] = parts[1].strip()
        except Exception as e:
            print(f"Error executing {bin_to_run}: {e}", file=sys.stderr)

        entries.append(entry)

    return entries

def generate_html(data):
    """Generates the HTML table with the collected data."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SAP Web Dispatcher Audit Report</title>
    <style>
        body { font-family: sans-serif; margin: 20px; color: #333; }
        table { border-collapse: collapse; width: 100%; max-width: 900px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #0070b8; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #f1f1f1; }
        .red { color: #d32f2f; font-weight: bold; }
        .green { color: #2e7d32; font-weight: bold; }
    </style>
</head>
<body>
    <h2>SAP Web Dispatcher Versions & Consistency</h2>
    <table>
        <thead>
            <tr>
                <th>Number</th>
                <th>SID</th>
                <th>Release</th>
                <th>Patch Number</th>
                <th>Date</th>
                <th>State</th>
            </tr>
        </thead>
        <tbody>
"""

    # Requirement 1: Counter variable
    for i, entry in enumerate(data, start=1):
        sid = html.escape(entry.get('sid', 'N/A'))
        release = html.escape(entry.get('release', 'N/A'))
        patch = html.escape(entry.get('patch', 'N/A'))
        date = html.escape(entry.get('date', 'N/A'))

        state_text = entry['state']
        state_class = "green" if entry['state_color'] == "green" else "red"
        date_style = f"color: {entry['date_color']}; font-weight: bold;" if entry['date_color'] == 'red' else ""

        row = f"""            <tr>
                <td>{i}</td>
                <td>{sid}</td>
                <td>{release}</td>
                <td>{patch}</td>
                <td style="{date_style}">{date}</td>
                <td class="{state_class}">{state_text}</td>
            </tr>
"""
        html_content += row

    html_content += """        </tbody>
    </table>
</body>
</html>
"""
    return html_content

def main():
    # 1. Run the prerequisite check
    check_sapsys_group()

    # 2. Collect data from filesystem and executions
    parsed_data = collect_data()

    # 3. Output standard HTML to stdout
    print(generate_html(parsed_data))

if __name__ == "__main__":
    main()

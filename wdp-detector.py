#!/usr/bin/env python3
import sys
import re
import html

def parse_input(lines):
    """
    Parses the raw input lines into a list of dictionaries representing each entry.
    """
    entries = []
    current_entry = {}

    # Regex for the command line to extract SID.
    # Matches patterns like /usr/sap/SID/... or /sapmnt/SID/...
    # Captures the 3-character alphanumeric SID after /sap/
    sid_pattern = re.compile(r"/sap/([A-Z0-9]{3})/", re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for the start of a new block (the command line)
        if line.startswith("env 'LD_LIBRARY_PATH="):
            # If we have a previous entry in progress, save it
            if current_entry:
                entries.append(current_entry)
                current_entry = {}

            # Extract SID
            match = sid_pattern.search(line)
            if match:
                current_entry['sid'] = match.group(1)
            else:
                current_entry['sid'] = "Unknown"

        elif line.startswith("kernel release"):
            # format: kernel release       = 789
            parts = line.split('=', 1)
            if len(parts) > 1:
                current_entry['release'] = parts[1].strip()

        elif line.startswith("compile time"):
            # format: compile time         = Jan 28 2025 19:34:42
            parts = line.split('=', 1)
            if len(parts) > 1:
                # We take the date part. The user asked for "Date".
                # The raw string includes time, we can keep it all or truncate.
                # Keeping the full string as requested.
                current_entry['date'] = parts[1].strip()

        elif line.startswith("patch number"):
            # format: patch number         = 325
            parts = line.split('=', 1)
            if len(parts) > 1:
                current_entry['patch'] = parts[1].strip()

    # Append the last entry if it exists
    if current_entry:
        entries.append(current_entry)

    return entries

def generate_html(data):
    """
    Generates a complete HTML page with a table from the parsed data.
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SAP Web Dispatcher Versions</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; max-width: 800px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #0070b8; color: white; } /* SAP Blue */
        tr:nth-child(even) { background-color: #f2f2f2; }
        tr:hover { background-color: #ddd; }
    </style>
</head>
<body>
    <h2>SAP Component Versions</h2>
    <table>
        <thead>
            <tr>
                <th>SID</th>
                <th>Release</th>
                <th>Patch Number</th>
                <th>Date</th>
            </tr>
        </thead>
        <tbody>
"""

    for entry in data:
        # Use .get() with default to handle missing fields gracefully
        sid = html.escape(entry.get('sid', 'N/A'))
        release = html.escape(entry.get('release', 'N/A'))
        patch = html.escape(entry.get('patch', 'N/A'))
        date = html.escape(entry.get('date', 'N/A'))

        row = f"""            <tr>
                <td>{sid}</td>
                <td>{release}</td>
                <td>{patch}</td>
                <td>{date}</td>
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
    # Read all lines from stdin
    input_lines = sys.stdin.readlines()

    # Process data
    parsed_data = parse_input(input_lines)

    # Output HTML
    print(generate_html(parsed_data))

if __name__ == "__main__":
    main()

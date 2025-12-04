#!/usr/bin/env python3
"""
Fetch temperatures per region from a CWA open data JSON file and save to CSV and SQLite.
This version extracts all temperature types (e.g., min, max, average) for each location.

Usage examples (Windows cmd):
  python fetch_temperatures.py
"""
import argparse
import csv
import json
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional


def is_temp_name(name: str) -> bool:
    """Checks if an element name looks like a temperature."""
    return bool(re.search(r"temp|temperature|t\b|溫度", name, re.IGNORECASE))


def find_locations(data: Any) -> List[Dict[str, Optional[str]]]:
    """
    Recursively scan JSON to find objects that represent locations with temperatures.
    Returns list of dicts with keys: 'location', 'temp_type', and 'temperature'.
    """
    found: List[Dict[str, Optional[str]]] = []

    def scan(obj: Any, inherited_loc_name: Optional[str] = None):
        if isinstance(obj, dict):
            # Try to find a location name in the current object, otherwise use the one passed down.
            loc_name = inherited_loc_name
            for k in ("locationName", "locationname", "location", "siteName", "stationName", "name"):
                if k in obj and isinstance(obj[k], str):
                    loc_name = obj[k]
                    break

            # Check for weather elements in the current object
            if "weatherElement" in obj and isinstance(obj["weatherElement"], list):
                for elem in obj["weatherElement"]:
                    if not isinstance(elem, dict):
                        continue
                    
                    elem_name = elem.get("elementName") or elem.get("name") or ""
                    
                    if is_temp_name(elem_name):
                        temp_val = None
                        val_container = elem.get("elementValue") or elem.get("value")
                        if isinstance(val_container, dict):
                            temp_val = val_container.get("value") or val_container.get("measure")
                        elif val_container is not None:
                            temp_val = str(val_container)

                        if loc_name and temp_val is not None:
                            found.append({
                                "location": loc_name,
                                "temp_type": elem_name,
                                "temperature": temp_val
                            })

            # Continue recursion, passing down the most recently found location name
            for v in obj.values():
                scan(v, loc_name)

        elif isinstance(obj, list):
            # For lists, pass down the same inherited location name to each item
            for it in obj:
                scan(it, inherited_loc_name)

    scan(data)
    # No de-duplication needed as we now want all temperature types.
    return found


def write_csv(rows: List[Dict[str, Optional[str]]], out_path: str) -> None:
    if not rows:
        return
    with open(out_path, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["location", "temp_type", "temperature"])
        for r in rows:
            writer.writerow([r.get("location"), r.get("temp_type"), r.get("temperature")])


def write_sqlite(rows: List[Dict[str, Optional[str]]], db_path: str) -> None:
    if not rows:
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS temperatures (
            id INTEGER PRIMARY KEY,
            location TEXT NOT NULL,
            temp_type TEXT NOT NULL,
            temperature REAL NOT NULL
        )
    """)
    # Clear the table before inserting new data
    cur.execute("DELETE FROM temperatures")
    
    for r in rows:
        loc = r.get("location")
        temp_type = r.get("temp_type")
        temp = r.get("temperature")
        if loc and temp_type and temp is not None:
            try:
                temp_float = float(temp)
                cur.execute("INSERT INTO temperatures (location, temp_type, temperature) VALUES (?, ?, ?)", 
                            (loc, temp_type, temp_float))
            except (ValueError, TypeError):
                print(f"Warning: Could not convert temperature '{temp}' to float. Skipping.", file=sys.stderr)

    conn.commit()
    conn.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Parse temperatures from a CWA open data JSON file")
    parser.add_argument("--file", default="data.json", help="Input JSON file path")
    parser.add_argument("--out", default="temperatures.csv", help="Output CSV file path")
    parser.add_argument("--db", default="data.db", help="Output SQLite database file path")
    parser.add_argument("--sample", type=int, default=15, help="How many sample rows to print")
    args = parser.parse_args(argv)

    print(f"Reading: {args.file}")
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.file}")
        return 2
    except (json.JSONDecodeError, Exception) as e:
        print(f"Failed to read or parse file: {e}")
        return 3

    # The actual data is nested inside the 'cwaopendata' key.
    locations = find_locations(data.get('cwaopendata', data))
    if not locations:
        print("No locations/temperatures discovered.")
        return 4

    # Write to CSV
    if args.out:
        write_csv(locations, args.out)
        print(f"Wrote {len(locations)} rows to {args.out}")

    # Write to SQLite
    if args.db:
        write_sqlite(locations, args.db)
        print(f"Wrote {len(locations)} rows to SQLite database: {args.db}")

    print("\nSample of extracted data:")
    for r in locations[: args.sample]:
        print(f"{r.get('location')} ({r.get('temp_type')}): {r.get('temperature')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

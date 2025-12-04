# CWA Temperature Crawler

This small script fetches region temperature data from the CWA open data API and writes a CSV file.

Files:

- `fetch_temperatures.py`: main script
- `requirements.txt`: Python requirements

Quick start (Windows `cmd.exe`):

```cmd
python -m pip install -r requirements.txt
python fetch_temperatures.py
```

Options:

- `--url`: use a custom API URL (default is the URL you provided)
- `--out`: specify output CSV filename (default `temperatures.csv`)
- `--sample`: how many sample rows to print

If the script cannot find temperatures with the default heuristics it will print top-level JSON keys to help debugging; you can then adapt the parsing logic in `fetch_temperatures.py` if needed.

# QTIBIA Topology - Coverage Cleaning Plugin

A QGIS plugin for cleaning polygon coverages using PostGIS ST_CoverageClean function.

## Features

- Clean polygon coverages by removing small gaps and fixing overlaps
- Uses PostGIS 3.6+ ST_CoverageClean function with GEOS 3.14.1+
- Connects to PostGIS via pg_service for easy configuration
- Configurable gap tolerance parameter
- Updates features in-place in QGIS

## Requirements

- QGIS 3.0+
- PostgreSQL 18.1+
- PostGIS 3.6+
- GEOS 3.14.1+
- Python psycopg (psycopg3) library (auto-installed if missing)
- Configured pg_service for database connection

## Installation

1. Copy the `qtibiatopology` folder to your QGIS plugins directory:
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Windows: `C:\Users\<username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

2. Restart QGIS

3. Enable the plugin from Plugins → Manage and Install Plugins → Installed

## Usage

1. Load a polygon layer in QGIS
2. Select at least 2 features that form a coverage (adjacent polygons)
3. Click the "Clean Coverage" toolbar button or go to Vector → QTIBIA Topology → Clean Coverage
4. Enter the gap maximum width (tolerance) in map units (default: 0.01)
5. Enter your pg_service name (default: pg_qtibia)
6. Click OK

The plugin will:
- Automatically start editing on the layer (if not already editing)
- Send the selected geometries to PostGIS
- Run ST_CoverageClean with the specified tolerance
- Return the cleaned geometries to the edit buffer (not auto-committed)
- Only update features where geometries actually changed
- Show a count of modified features

**Important**: The changes are placed in the edit buffer. You need to manually save edits (Ctrl+S or click "Save Edits") to commit the changes, or rollback if you want to discard them.

## Performance

The plugin includes several performance optimizations:
- **Binary format (WKB)** instead of text (WKT) for 2-5x faster geometry transfer
- **Batch inserts** with `executemany()` for 5-10x faster data loading
- **Optimized memory usage** by eliminating duplicate geometry storage
- **Optional verbose logging** - disabled by default for better performance
- **Auto-installs psycopg** if not found, using pip

See [PERFORMANCE.md](PERFORMANCE.md) for detailed optimization guide and benchmarks.

## How Coverage Cleaning Works

Based on the JTS CoverageCleaner implementation (ported to GEOS 3.14 and PostGIS 3.6):

1. **Snapping & Noding**: Eliminates small discrepancies and narrow gaps through distance-based vertex alignment
2. **Polygonizing**: Reconstructs noded linework into clean topology
3. **Overlap Merging**: Merges overlaps to adjacent polygons
4. **Gap Detection & Merging**: Identifies gaps narrower than the tolerance (measured by Maximum Inscribed Circle diameter) and merges them with neighboring polygons

The `gapMaximumWidth` parameter specifies the maximum width of gaps to clean. Gaps narrower than this value will be merged with adjacent polygons.

## Configuration

### pg_service Setup

Create or edit your `~/.pg_service.conf` file (Linux/macOS) or `%APPDATA%\postgresql\.pg_service.conf` (Windows):

```ini
[pg_qtibia]
host=localhost
port=5432
dbname=your_database
user=your_username
password=your_password
```

Then you can simply use `pg_qtibia` as the service name in the plugin.

## References

- [Coverage Cleaning in JTS](https://lin-ear-th-inking.blogspot.com/2025/04/coverage-cleaning-in-jts.html)
- [PostGIS 3.6 and GEOS 3.14 Release](https://www.crunchydata.com/blog/2025-postgis-and-geos-release)
- [PostGIS Performance and Simplification](https://www.crunchydata.com/blog/postgis-performance-simplification)

## License

GNU General Public License v2.0

## Author

QTIBIA Engineering
tudor.barascu@qtibia.ro

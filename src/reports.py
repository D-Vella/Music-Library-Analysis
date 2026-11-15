"""Run report SQL from sql/reports/ and print tables.

Phase 7.
"""
import math

def human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = int(math.floor(math.log(size_bytes, 1024)))
    return f"{size_bytes / (1024 ** unit_index):.2f} {units[unit_index]}"

# Usage:
# human_readable_size(file_size)  → e.g., "15.30 MB"

"""Walk the NAS and build a file inventory (one record per file).

Phase 2: walk_library(root) -> Iterator[dict]
"""

import os
from pathlib import Path
from itertools import islice

def scan_library():
    """
    Walk the library directory and build a file inventory.

    Args:
        library_path (Path): The path to the library directory.

    Returns:
        Iterator[dict]: An iterator over the file inventory records.
    """
    library_path = Path(os.getenv('LIBRARY_PATH'))

    file_list = []
    file_data = {}

    for root, dirs, files in islice(os.walk(library_path), 0, None):
        if files:
            file_list.extend([os.path.join(root, f) for f in files])

    for file_path in file_list:
        relative_path = os.path.relpath(file_path, library_path)
        file_name = os.path.basename(file_path)
        file_type = os.path.splitext(file_name)[1].lower()  # Get file extension and convert to lowercase
        file_size = os.path.getsize(file_path) # Get file size in bytes
        file_modified_time = os.path.getmtime(file_path)
        file_data[relative_path] = {
            'name': file_name,
            'type': file_type,
            'size': file_size,
            'modified_time': file_modified_time
        }

    return file_data

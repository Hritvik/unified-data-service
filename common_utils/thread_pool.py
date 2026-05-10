import os
from concurrent.futures import ThreadPoolExecutor

# Calculate optimal number of workers
# Use 2x CPU cores for I/O bound tasks, but cap at 32
cpu_count = os.cpu_count()
if cpu_count is None:
    cpu_count = 4  # Default fallback
MAX_WORKERS = min(32, cpu_count * 2)

# Create a shared thread pool with proper configuration
thread_pool = ThreadPoolExecutor(
    max_workers=MAX_WORKERS, thread_name_prefix="modelswitch-worker"
)

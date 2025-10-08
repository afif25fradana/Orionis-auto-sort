"""
Improved File Sorter module with enhanced security and error handling
"""
import logging
import shutil
import threading
import time
import queue
from pathlib import Path

STABLE_FILE_WAIT_SECONDS = 1
STABLE_FILE_MAX_ATTEMPTS = 10
NUM_WORKERS = 4  # Number of concurrent worker threads


def safe_path_join(base_path: Path, *additional_parts) -> Path:
    """
    Safely join path parts, preventing path traversal.
    Ensures the final path stays within the base directory.
    """
    # Convert to Path objects and join them
    result = base_path.joinpath(*additional_parts)
    
    # Resolve the path and ensure it's within base_path
    resolved = result.resolve()
    base_resolved = base_path.resolve()
    
    try:
        # Check if the resolved path is within the base path
        resolved.relative_to(base_resolved)
        return resolved
    except ValueError:
        # Path traversal detected - return base path only
        logging.warning("⚠️ Path traversal attempt detected: %s", result)
        raise ValueError(f"Path traversal detected: {result}")


class SortWorker(threading.Thread):
    """A worker thread that processes files from a queue with security enhancements."""

    def __init__(self, work_queue: queue.Queue, status_queue: queue.Queue, download_path: Path, file_categories: dict, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.work_queue = work_queue
        self.status_queue = status_queue
        self.download_path = download_path.resolve()  # Ensure absolute path
        self.file_categories = file_categories
        self.stop_event = stop_event

    def run(self):
        """The main loop for the worker."""
        while not self.stop_event.is_set():
            try:
                file_path = self.work_queue.get(timeout=1)
                self._process_file(file_path)
                self.work_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.error("❌ Unexpected error in worker thread: %s", e, exc_info=True)

    def _process_file(self, file_path: Path):
        """The core logic to process a single file with security checks."""
        try:
            # Validate file path to ensure it's within downloads directory
            try:
                file_path = file_path.resolve()
                file_path.relative_to(self.download_path)
            except ValueError:
                logging.error("❌ Security: File path is outside of download directory: %s", file_path)
                return

            if not file_path.exists() or not file_path.is_file():
                logging.warning("⚠️ File no longer exists or is not a file: %s", file_path.name)
                return

            if not self._wait_for_file_completion(file_path):
                logging.warning("⚠️ File was not stable or disappeared: %s", file_path.name)
                return

            category = self._get_file_category(file_path.suffix)
            
            # Safely create destination folder path
            try:
                destination_folder = safe_path_join(self.download_path, category)
                destination_folder.mkdir(exist_ok=True)
            except ValueError as e:
                logging.error("❌ Security: Invalid destination path construction: %s", e)
                return

            # Generate unique destination path safely
            try:
                destination_path = self._get_unique_destination(destination_folder, file_path.name)
                # Further validate the destination path
                destination_path.relative_to(self.download_path)
            except ValueError as e:
                logging.error("❌ Security: Invalid destination path: %s", e)
                return

            logging.info("⏳ Moving %s to %s/", file_path.name, category)
            
            # Move the file
            shutil.move(str(file_path), str(destination_path))
            logging.info("✅ Successfully moved %s → %s/", file_path.name, category)
            self.status_queue.put({
                'title': 'File Sorted',
                'text': f'{file_path.name} was moved to {category}.'
            })

        except (PermissionError, OSError) as e:
            logging.error("❌ Permission/OS error moving %s: %s", file_path.name, e)
            self.status_queue.put({
                'title': 'Move Error',
                'text': f"Could not move {file_path.name}. Check permissions."
            })
        except Exception as e:
            logging.error("❌ Unexpected error moving %s: %s", file_path.name, e, exc_info=True)
            self.status_queue.put({
                'title': 'Move Error',
                'text': f"An unexpected error occurred with {file_path.name}."
            })

    def _wait_for_file_completion(self, file_path: Path) -> bool:
        """Wait until a file's size is stable with timeout protection."""
        if not file_path.exists():
            return False
        
        # For very small files, wait just a moment
        try:
            file_size = file_path.stat().st_size
        except (FileNotFoundError, OSError):
            return False

        if file_size < 1024:
            time.sleep(STABLE_FILE_WAIT_SECONDS)
            return file_path.exists()

        prev_size = -1
        for attempt in range(STABLE_FILE_MAX_ATTEMPTS):
            try:
                if not file_path.exists():
                    return False
                current_size = file_path.stat().st_size
                if current_size == prev_size and current_size > 0:
                    return True
                prev_size = current_size
                time.sleep(STABLE_FILE_WAIT_SECONDS)
            except (FileNotFoundError, OSError):
                return False
        return False  # File never stabilized

    def _get_file_category(self, file_extension: str) -> str:
        """Determine file category based on its extension."""
        file_extension = file_extension.lower()
        for category, extensions in self.file_categories.items():
            if file_extension in extensions:
                return category
        return 'Others'

    def _get_unique_destination(self, destination_folder: Path, filename: str) -> Path:
        """Generate a unique file path if the destination already exists."""
        # Validate filename to prevent path traversal
        if '..' in filename or filename.startswith('/') or '../' in filename:
            raise ValueError(f"Invalid filename detected: {filename}")
        
        destination_path = destination_folder / filename
        counter = 1
        while destination_path.exists():
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            # Sanitize stem to prevent path traversal in the middle
            if '..' in stem or '/' in stem or '\\' in stem:
                stem = ''.join(c for c in stem if c.isalnum() or c in (' ', '-', '_')).strip()
            destination_path = destination_folder / f"{stem}_{counter}{suffix}"
            counter += 1
        return destination_path


class FileSorter:
    """Manages the file sorting process by managing a pool of worker threads."""

    def __init__(self, work_queue: queue.Queue, status_queue: queue.Queue, download_path: Path, file_categories: dict, stop_event: threading.Event):
        self.work_queue = work_queue
        self.status_queue = status_queue
        self.download_path = download_path.resolve()  # Ensure absolute path
        self.file_categories = file_categories
        self.stop_event = stop_event
        self.workers = []

    def start(self):
        """Start the worker threads."""
        logging.info("🚀 Starting %d sorter workers...", NUM_WORKERS)
        for _ in range(NUM_WORKERS):
            worker = SortWorker(
                self.work_queue,
                self.status_queue,
                self.download_path,
                self.file_categories,
                self.stop_event
            )
            worker.start()
            self.workers.append(worker)
        
        # Also create category folders at startup
        self._create_category_folders()

    def stop(self):
        """Stop all worker threads."""
        logging.info("🛑 Stopping sorter workers...")
        # The stop_event will signal workers to exit their loops
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=2)

    def _create_category_folders(self):
        """Create folders for each file category safely."""
        for folder_name in self.file_categories.keys():
            try:
                folder_path = safe_path_join(self.download_path, folder_name)
                folder_path.mkdir(exist_ok=True)
            except ValueError as e:
                logging.error("❌ Security: Invalid category folder name: %s (%s)", folder_name, e)
                continue

    def sort_existing_files(self):
        """Add all existing files in the download path to the work queue."""
        logging.info("🔄 Queueing existing files for sorting...")
        count = 0
        for file_path in self.download_path.iterdir():
            if file_path.is_file():
                # Validate the file path before adding to queue
                try:
                    safe_path = file_path.resolve()
                    safe_path.relative_to(self.download_path)
                    self.work_queue.put(safe_path)
                    count += 1
                except ValueError:
                    logging.warning("⚠️ Skipping file outside download directory: %s", file_path)
                    continue
        logging.info("✅ Queued %d existing files.", count)
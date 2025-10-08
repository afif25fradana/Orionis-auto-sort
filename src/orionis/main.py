import logging
import queue
import signal
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemMovedEvent

from .config import load_configuration
from .sorter import FileSorter
from .tray import SystemTrayIcon

# Constants
LOG_FILE = "orionis_auto_sort.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3
APP_NAME = "Orionis Auto Sort"

class WatcherEventHandler(FileSystemEventHandler):
    """A watchdog event handler that puts new file paths into a queue."""
    def __init__(self, work_queue: queue.Queue, download_path: Path):
        self.work_queue = work_queue
        self.download_path = download_path

    def on_created(self, event):
        if not event.is_directory:
            logging.info("📥 New file detected: %s", event.src_path)
            self.work_queue.put(Path(event.src_path))

    def on_moved(self, event: FileSystemMovedEvent):
        if not event.is_directory and Path(event.dest_path).parent == self.download_path:
            logging.info("📥 File moved into downloads: %s", event.dest_path)
            self.work_queue.put(Path(event.dest_path))


def setup_logging():
    """Set up file-based logging."""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
    log_handler.setFormatter(log_formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_handler)
    # Also log to console for debugging
    root_logger.addHandler(logging.StreamHandler())


def main():
    """The main function to run the application."""
    setup_logging()
    
    # Use Path.home() to be user-agnostic
    downloads_path = Path.home() / "Downloads"
    if not downloads_path.exists():
        logging.critical("❌ Downloads folder not found at %s!", downloads_path)
        return

    # Improved resource path handling to prevent path traversal
    try:
        # Try to get base path from executable location first (for PyInstaller), otherwise from script location
        if getattr(sys, 'frozen', False):  # Running as compiled executable
            base_path = Path(sys.executable).parent
        else:  # Running as script
            base_path = Path(__file__).parent.parent.parent

        config_path = base_path / 'config.json'
        if not config_path.exists():
            config_path = Path(__file__).parent.parent.parent / 'config.json'
        
        icon_path = base_path / 'icon.png'
        if not icon_path.exists():
            icon_path = Path(__file__).parent.parent.parent / 'icon.png'

        # Fallback to script location if not found in base path
        if not config_path.exists():
            config_path = Path(__file__).parent.parent.parent / 'config.json'
        if not icon_path.exists():
            icon_path = Path(__file__).parent.parent.parent / 'icon.png'

    except Exception as e:
        logging.error("❌ Error determining resource paths: %s", e)
        # Fallback to relative paths in the current directory
        config_path = Path('config.json')
        icon_path = Path('icon.png')

    # Verify that paths are within safe directories to prevent path traversal
    try:
        config_path.resolve().relative_to(Path('.').resolve())
        icon_path.resolve().relative_to(Path('.').resolve())
    except ValueError:
        logging.critical("❌ Security: Config or icon path is outside allowed directory!")
        return

    # --- Setup Communication Channels ---
    stop_event = threading.Event()
    work_queue = queue.Queue()
    status_queue = queue.Queue()

    # --- Load Configuration ---
    file_categories = load_configuration(config_path)

    # --- Setup Core Components ---
    file_sorter = FileSorter(work_queue, status_queue, downloads_path, file_categories, stop_event)
    
    event_handler = WatcherEventHandler(work_queue, downloads_path)
    observer = Observer()
    observer.schedule(event_handler, str(downloads_path), recursive=False)

    tray_icon = SystemTrayIcon(APP_NAME, icon_path, status_queue, stop_event, downloads_path)

    # --- Signal Handling for Graceful Shutdown ---
    def signal_handler(sig, frame):
        logging.info("\n🛑 Signal received, initiating shutdown...")
        stop_event.set()
        tray_icon.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # --- Start Application ---
    try:
        logging.info("🚀 Application starting...")
        
        # Start all background components
        observer.start()
        file_sorter.start()
        
        # Perform initial sort of existing files
        file_sorter.sort_existing_files()

        logging.info("✅ Application is running. Monitoring folder: %s", downloads_path)
        
        # Run the UI in the main thread (this is a blocking call)
        tray_icon.run()

    except Exception as e:
        logging.critical("❌ A fatal error occurred in the main loop: %s", e, exc_info=True)
    finally:
        # --- Graceful Shutdown ---
        logging.info("🛑 Shutting down application...")
        if observer.is_alive():
            observer.stop()
            observer.join(timeout=2)
        
        file_sorter.stop()
        
        # The tray_icon.run() call blocks until it's stopped,
        # so we just need to ensure its threads are clean if any are left.
        if tray_icon.status_thread.is_alive():
            tray_icon.status_thread.join(timeout=2)

        logging.info("👋 Goodbye!")


if __name__ == "__main__":
    main()

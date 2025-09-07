import os
import shutil
from pathlib import Path
import time
import json
import traceback
import tempfile
import uuid
import errno
import threading
import signal
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import libraries for system tray
import pystray
from PIL import Image

class FileSorter(FileSystemEventHandler):
    def __init__(self, download_path):
        self.download_path = Path(download_path)
        self.config_path = Path(__file__).parent / 'config.json'
        self.load_config()
        
        # Create category folders if they don't exist
        self.create_folders()
        
        # Dictionary untuk melacak file yang sedang diproses
        self.processing_files = set()
        
        # Folder untuk file lock
        self.lock_folder = Path(tempfile.gettempdir()) / "orionis_auto_sort_locks"
        self.lock_folder.mkdir(exist_ok=True)

    def load_config(self):
        """Load configuration from config.json file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.file_categories = config.get('file_categories', {})
                print("✓ Configuration successfully loaded from config.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ Error loading config.json: {e}")
            print("➡️ Using default configuration.")
            # Fallback ke konfigurasi default jika file tidak ada atau error
            self.file_categories = {
                'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff'],
                'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
                'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'],
                'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
                'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
                'Programs': ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.appx'],
                'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go'],
                'Others': []
            }
    
    def create_folders(self):
        """Create folders for each file category"""
        for folder_name in self.file_categories.keys():
            folder_path = self.download_path / folder_name
            folder_path.mkdir(exist_ok=True)
            print(f"✓ Folder '{folder_name}' ready")
    
    def get_file_category(self, file_extension):
        """Determine file category based on extension"""
        file_extension = file_extension.lower()
        
        for category, extensions in self.file_categories.items():
            if file_extension in extensions:
                return category
        
        return 'Others'  # Jika tidak ditemukan kategori
    
    def acquire_lock(self, file_path):
        """Try to acquire a lock for a specific file"""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
            
        # Create a unique lock file name based on file path
        lock_name = f"{file_path.name}_{uuid.uuid4().hex}.lock"
        lock_path = self.lock_folder / lock_name
        
        try:
            # Check if file is already being processed
            file_id = str(file_path)
            if file_id in self.processing_files:
                print(f"⚠️ File is being processed by another process: {file_path.name}")
                return False
                
            # Mark file as being processed
            self.processing_files.add(file_id)
            
            # Create lock file
            with open(lock_path, 'w') as f:
                f.write(f"Locked by Orionis Auto Sort at {time.ctime()}")
                
            return True
        except Exception as e:
            print(f"⚠️ Failed to acquire lock for {file_path.name}: {e}")
            return False
    
    def release_lock(self, file_path):
        """Release lock for a specific file"""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
            
        try:
            # Remove file from the list of files being processed
            file_id = str(file_path)
            if file_id in self.processing_files:
                self.processing_files.remove(file_id)
                
            # Remove all lock files associated with this file
            for lock_file in self.lock_folder.glob(f"{file_path.name}_*.lock"):
                try:
                    lock_file.unlink()
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"⚠️ Error when releasing lock: {e}")
    
    def move_file(self, file_path):
        """Move file to the appropriate folder"""
        try:
            file_path = Path(file_path)
            
            # Skip if path doesn't exist
            if not file_path.exists():
                print(f"⚠️ File not found: {file_path}")
                return
            
            # Skip if it's a folder or hidden file
            if file_path.is_dir() or file_path.name.startswith('.'):
                return
            
            # Skip if file is already in a subfolder we created
            if file_path.parent != self.download_path:
                return
                
            # Try to acquire lock for this file
            if not self.acquire_lock(file_path):
                print(f"⚠️ Cannot acquire lock for {file_path.name}, skipping")
                return
                
            try:
                # Verify file still exists after acquiring lock
                if not file_path.exists():
                    print(f"⚠️ File missing after acquiring lock: {file_path}")
                    return
                
                # Determine file category
                file_extension = file_path.suffix
                category = self.get_file_category(file_extension)
                
                # Destination path
                destination_folder = self.download_path / category
                destination_path = destination_folder / file_path.name
                
                # If file with same name already exists, add a number
                counter = 1
                original_destination = destination_path
                while destination_path.exists():
                    stem = original_destination.stem
                    suffix = original_destination.suffix
                    destination_path = destination_folder / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                # Verify file still exists before moving
                if not file_path.exists():
                    print(f"⚠️ File missing before moving: {file_path}")
                    return
                    
                # Pindahkan file dengan metode yang lebih aman
                try:
                    # Coba salin file terlebih dahulu
                    shutil.copy2(str(file_path), str(destination_path))
                    
                    # Verifikasi file berhasil disalin
                    if destination_path.exists() and destination_path.stat().st_size > 0:
                        # Bandingkan ukuran file
                        src_size = file_path.stat().st_size
                        dest_size = destination_path.stat().st_size
                        
                        if src_size == dest_size:
                            # Hapus file asli hanya jika salinan berhasil dan ukuran sama
                            try:
                                file_path.unlink()
                                print(f"📁 {file_path.name} → {category}/")
                            except Exception as e:
                                print(f"⚠️ Gagal menghapus file asli: {e}, tetapi file sudah disalin")
                        else:
                            print(f"⚠️ Ukuran file tidak sama: {src_size} vs {dest_size}, file tidak dihapus")
                    else:
                        print(f"⚠️ Gagal menyalin {file_path.name}, file tidak dipindahkan")
                except Exception as e:
                    print(f"❌ Error saat menyalin {file_path.name}: {e}")
                    # Jika gagal menyalin, coba metode move langsung
                    if file_path.exists():
                        try:
                            shutil.move(str(file_path), str(destination_path))
                            print(f"📁 {file_path.name} → {category}/ (with direct move)")
                        except Exception as move_error:
                            print(f"❌ Failed to move with direct move: {move_error}")
            finally:
                # Make sure lock is released in any condition
                self.release_lock(file_path)
            
        except Exception as e:
            print(f"❌ Error moving {file_path}: {e}")
            # Log more detailed error for debugging
            print(traceback.format_exc())
            # Make sure lock is released if an error occurs
            self.release_lock(file_path)
    
    def sort_existing_files(self):
        """Sort existing files in the Downloads folder"""
        print("🔄 Starting to sort existing files...")
        
        files_moved = 0
        for file_path in self.download_path.iterdir():
            if file_path.is_file():
                self.move_file(file_path)
                files_moved += 1
        
        print(f"✅ Done! {files_moved} files have been moved.")
    
    def on_created(self, event):
        """Event handler when a new file is created/downloaded"""
        if not event.is_directory:
            try:
                src_path = Path(event.src_path)
                print(f"📥 New file detected: {src_path}")
                
                # Wait until file is completely downloaded (stable size)
                self.wait_for_file_completion(src_path)
                
                # Verify file still exists before moving
                if src_path.exists():
                    self.move_file(src_path)
                else:
                    print(f"⚠️ File missing before it could be moved: {src_path}")
            except Exception as e:
                print(f"❌ Error in created event: {e}")
    
    def on_moved(self, event):
        """Event handler when a file is moved to the Downloads folder"""
        try:
            dest_path = Path(event.dest_path)
            if not event.is_directory and dest_path.parent == self.download_path:
                print(f"📥 File moved to Downloads: {dest_path}")
                
                # Wait until file is completely moved (stable size)
                self.wait_for_file_completion(dest_path)
                
                # Verify file still exists before moving
                if dest_path.exists():
                    self.move_file(dest_path)
                else:
                    print(f"⚠️ File missing before it could be moved: {dest_path}")
        except Exception as e:
            print(f"❌ Error in moved event: {e}")
    
    def wait_for_file_completion(self, file_path):
        """Wait until file is completely downloaded/moved (stable size)"""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
            
        if not file_path.exists():
            print(f"⚠️ File not found while waiting: {file_path}")
            return False
            
        # If file is very small, wait just a moment
        if file_path.stat().st_size < 1024:  # Less than 1KB
            time.sleep(1)
            return file_path.exists()
            
        max_attempts = 10
        prev_size = -1
        attempt = 0
        
        while attempt < max_attempts:
            try:
                if not file_path.exists():
                    print(f"⚠️ File missing while waiting: {file_path}")
                    return False
                    
                current_size = file_path.stat().st_size
                
                # If size doesn't change, file might be complete
                if current_size == prev_size and current_size > 0:
                    return True
                    
                prev_size = current_size
                attempt += 1
                time.sleep(1)  # Wait 1 second
                
            except Exception as e:
                print(f"⚠️ Error while waiting for file: {e}")
                time.sleep(1)
                attempt += 1
        
        # Jika sampai di sini, anggap file sudah selesai
        return file_path.exists()

class SystemTrayIcon:
    """Class to manage system tray icon"""
    def __init__(self, icon_path, app_name):
        self.app_name = app_name
        self.icon = None
        self.stop_event = threading.Event()
        self.observer = None
        self.file_sorter = None
    
    def create_image(self):
        """Create image object from icon file"""
        try:
            # Create a default image with dark blue background (night sky)
            img = Image.new('RGBA', (64, 64), color=(10, 17, 40, 255))
            
            # Draw Orion constellation stars
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            
            # Betelgeuse (top left shoulder) - reddish
            draw.ellipse((12, 12, 18, 18), fill=(255, 107, 107, 255))
            
            # Bellatrix (top right shoulder) - white
            draw.ellipse((43, 16, 47, 20), fill=(255, 255, 255, 255))
            
            # Rigel (bottom right foot) - blue-white
            draw.ellipse((45, 45, 51, 51), fill=(122, 215, 240, 255))
            
            # Saiph (bottom left foot) - white
            draw.ellipse((16, 43, 20, 47), fill=(255, 255, 255, 255))
            
            # Belt stars - white
            draw.ellipse((22, 30, 26, 34), fill=(255, 255, 255, 255))  # Alnitak
            draw.ellipse((30, 30, 34, 34), fill=(255, 255, 255, 255))  # Alnilam
            draw.ellipse((38, 30, 42, 34), fill=(255, 255, 255, 255))  # Mintaka
            
            # Meissa (head) - white
            draw.ellipse((30, 8, 34, 12), fill=(255, 255, 255, 255))
            
            # Constellation lines - blue
            draw.line((15, 15, 45, 18, 48, 48, 18, 45, 15, 15), fill=(74, 134, 232, 150), width=1)
            draw.line((24, 32, 32, 32, 40, 32), fill=(74, 134, 232, 150), width=1)
            draw.line((32, 10, 32, 32), fill=(74, 134, 232, 150), width=1)
            
            return img
        except Exception as e:
            print(f"⚠️ Error creating icon: {e}")
            # Create simple default image if there's an error
            img = Image.new('RGB', (64, 64), color = (73, 134, 232))
            return img
    
    def create_menu(self):
        """Create context menu for system tray icon"""
        return pystray.Menu(
            pystray.MenuItem('Status', self.show_status, default=True),
            pystray.MenuItem('Open Downloads Folder', self.open_downloads),
            pystray.MenuItem('Exit', self.exit_app)
        )
    
    def setup(self, observer, file_sorter):
        """Set up system tray icon"""
        self.observer = observer
        self.file_sorter = file_sorter
        
        # Create system tray icon
        self.icon = pystray.Icon(self.app_name)
        self.icon.icon = self.create_image()
        self.icon.title = "Orionis Auto Sort"
        self.icon.menu = self.create_menu()
    
    def run(self):
        """Run system tray icon"""
        self.icon.run_detached()
    
    def stop(self):
        """Stop system tray icon"""
        if self.icon:
            self.icon.stop()
    
    def show_status(self, icon, item):
        """Display application status"""
        if self.observer and self.observer.is_alive():
            icon.notify("Orionis Auto Sort is running", "Status")
        else:
            icon.notify("Orionis Auto Sort is not running", "Status")
    
    def open_downloads(self, icon, item):
        """Open Downloads folder"""
        try:
            downloads_path = Path.home() / "Downloads"
            os.startfile(str(downloads_path))
        except Exception as e:
            icon.notify(f"Error opening folder: {e}", "Error")
    
    def exit_app(self, icon, item):
        """Exit application"""
        self.stop_event.set()
        icon.stop()

def cleanup_temp_files():
    """Clean up lock files that might be left from previous processes"""
    try:
        lock_folder = Path(tempfile.gettempdir()) / "orionis_auto_sort_locks"
        if lock_folder.exists():
            for lock_file in lock_folder.glob("*.lock"):
                try:
                    lock_file.unlink()
                    print(f"🧹 Cleaning up lock file: {lock_file.name}")
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️ Error cleaning up lock files: {e}")

def setup_signal_handlers(tray_icon):
    """Set up handlers for system signals"""
    def signal_handler(sig, frame):
        print("\n🛑 Stopping auto-sorter...")
        tray_icon.stop_event.set()
        tray_icon.stop()
    
    # Capture SIGINT (Ctrl+C) and SIGTERM signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    # Clean up any remaining lock files
    cleanup_temp_files()
    
    # Path to Windows Downloads folder
    downloads_path = Path.home() / "Downloads"
    
    if not downloads_path.exists():
        print("❌ Downloads folder not found!")
        return
    
    print(f"🎯 Monitoring folder: {downloads_path}")
    print("=" * 50)
    
    # Initialize file sorter
    try:
        file_sorter = FileSorter(downloads_path)
    except Exception as e:
        print(f"❌ Error initializing FileSorter: {e}")
        print(traceback.format_exc())
        return
    
    # Sort existing files
    try:
        file_sorter.sort_existing_files()
    except Exception as e:
        print(f"❌ Error sorting existing files: {e}")
        print(traceback.format_exc())
        # Continue despite errors
    
    print("\n" + "=" * 50)
    print("👀 Starting to monitor new files...")
    print("Application is running in the system tray. Right-click on the icon to see the menu.")
    print("=" * 50)
    
    # Setup file system watcher
    observer = None
    tray_icon = None
    
    try:
        # Initialize observer
        observer = Observer()
        observer.schedule(file_sorter, str(downloads_path), recursive=False)
        observer.start()
        
        # Initialize system tray icon
        icon_path = None
        tray_icon = SystemTrayIcon(icon_path, "orionis-auto-sort")
        tray_icon.setup(observer, file_sorter)
        
        # Setup signal handlers
        setup_signal_handlers(tray_icon)
        
        # Run system tray icon
        tray_icon.run()
        
        # Main loop
        while not tray_icon.stop_event.is_set():
            time.sleep(0.5)
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print(traceback.format_exc())
    finally:
        # Make sure observer is stopped properly
        if observer:
            try:
                observer.stop()
                observer.join(timeout=3)  # Wait maximum 3 seconds
            except Exception as e:
                print(f"⚠️ Error stopping observer: {e}")
        
        # Make sure system tray icon is stopped properly
        if tray_icon:
            try:
                tray_icon.stop()
            except Exception as e:
                print(f"⚠️ Error stopping system tray icon: {e}")
        
        # Clean up lock files before exiting
        cleanup_temp_files()
        
        print("✅ Auto-sorter stopped. Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print(traceback.format_exc())
        # Make sure lock files are cleaned up in case of fatal error
        cleanup_temp_files()

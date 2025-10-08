import queue
import threading
from pathlib import Path
import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

# Add the src directory to the Python path to allow imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from orionis.sorter import SortWorker, FileSorter, safe_path_join

# --- Test Data and Fixtures ---

@pytest.fixture
def file_categories():
    """Returns a sample file categories configuration."""
    return {
        'Images': ['.jpg', '.png'],
        'Documents': ['.pdf', '.docx'],
        'Archives': ['.zip'],
        'Others': []
    }

@pytest.fixture
def downloads_path(fs: FakeFilesystem, file_categories):
    """Sets up a fake filesystem with a downloads directory and category folders."""
    path = Path.home() / "Downloads"
    fs.create_dir(path)
    for category in file_categories.keys():
        fs.create_dir(path / category)
    return path

# --- Unit Tests for Helper Functions ---

def test_safe_path_join(downloads_path):
    """Test the safe_path_join function for both valid and invalid paths."""
    # Valid case
    valid_path = safe_path_join(downloads_path, "Images", "test.jpg")
    assert valid_path == downloads_path / "Images" / "test.jpg"

    # Path traversal attempt
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_path_join(downloads_path, "..", "some_other_folder")

def test_get_file_category(file_categories):
    """Test the _get_file_category method."""
    # A dummy worker instance to test the private method
    worker = SortWorker(queue.Queue(), queue.Queue(), Path("/fake"), file_categories, threading.Event())
    
    assert worker._get_file_category('.jpg') == 'Images'
    assert worker._get_file_category('.png') == 'Images'
    assert worker._get_file_category('.pdf') == 'Documents'
    assert worker._get_file_category('.zip') == 'Archives'
    assert worker._get_file_category('.txt') == 'Others'
    assert worker._get_file_category('.JPG') == 'Images' # Test case-insensitivity

def test_get_unique_destination(downloads_path, fs: FakeFilesystem):
    """Test the _get_unique_destination method for unique and duplicate filenames."""
    images_path = downloads_path / "Images"
    
    worker = SortWorker(queue.Queue(), queue.Queue(), downloads_path, {}, threading.Event())

    # Test with a new file
    unique_path = worker._get_unique_destination(images_path, "new_file.jpg")
    assert unique_path == images_path / "new_file.jpg"

    # Create a file and test for duplication
    fs.create_file(images_path / "existing_file.jpg")
    duplicate_path = worker._get_unique_destination(images_path, "existing_file.jpg")
    assert duplicate_path == images_path / "existing_file_1.jpg"

    # Test with multiple duplicates
    fs.create_file(images_path / "existing_file_1.jpg")
    duplicate_path_2 = worker._get_unique_destination(images_path, "existing_file.jpg")
    assert duplicate_path_2 == images_path / "existing_file_2.jpg"

    # Test for path traversal in filename
    with pytest.raises(ValueError, match="Invalid filename detected"):
        worker._get_unique_destination(images_path, "../traversal.txt")


# --- Integration-style Tests for Worker and Sorter ---

def test_sort_worker_process_file(downloads_path, file_categories, fs: FakeFilesystem):
    """Test the full processing of a single file by the SortWorker."""
    work_queue = queue.Queue()
    status_queue = queue.Queue()
    stop_event = threading.Event()

    # Create a test file in the fake downloads directory
    test_file_path = downloads_path / "my_image.jpg"
    fs.create_file(test_file_path, contents="fake image data")

    # Create and run the worker
    worker = SortWorker(work_queue, status_queue, downloads_path, file_categories, stop_event)
    
    # We call the internal method directly for a synchronous test
    worker._process_file(test_file_path)

    # Assertions
    destination_path = downloads_path / "Images" / "my_image.jpg"
    assert not test_file_path.exists()
    assert destination_path.exists()
    
    status_message = status_queue.get_nowait()
    assert status_message['title'] == 'File Sorted'
    assert "my_image.jpg" in status_message['text']
    assert "Images" in status_message['text']

def test_sort_worker_ignores_file_outside_downloads(downloads_path, file_categories, fs: FakeFilesystem, caplog):
    """Test that the worker ignores and logs a file outside the monitored directory."""
    work_queue = queue.Queue()
    
    # Create a file in a different directory
    other_path = Path.home() / "Documents"
    fs.create_dir(other_path)
    external_file = other_path / "secret.txt"
    fs.create_file(external_file)

    worker = SortWorker(work_queue, queue.Queue(), downloads_path, file_categories, threading.Event())
    worker._process_file(external_file)

    assert "File path is outside of download directory" in caplog.text
    assert external_file.exists() # File should not be moved

def test_file_sorter_sort_existing_files(downloads_path, file_categories, fs: FakeFilesystem):
    """Test that the FileSorter correctly queues all existing files."""
    work_queue = queue.Queue()
    
    # Create some files in the fake downloads directory
    fs.create_file(downloads_path / "image.png")
    fs.create_file(downloads_path / "document.pdf")
    fs.create_file(downloads_path / "archive.zip")
    fs.create_dir(downloads_path / "an_existing_folder") # Should be ignored

    sorter = FileSorter(work_queue, queue.Queue(), downloads_path, file_categories, threading.Event())
    sorter.sort_existing_files()

    assert work_queue.qsize() == 3
    
    # Check that the files are in the queue
    queued_files = {work_queue.get_nowait().name for _ in range(3)}
    assert queued_files == {"image.png", "document.pdf", "archive.zip"}
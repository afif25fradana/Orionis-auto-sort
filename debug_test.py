"""
Debug test script for Orionis Auto Sort
This script tests various scenarios to identify issues and validate functionality
"""
import json
import logging
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.orionis.config import load_configuration
from src.orionis.sorter import FileSorter, SortWorker
from src.orionis.tray import SystemTrayIcon


def setup_test_logging():
    """Setup logging for the test"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_config_loading():
    """Test configuration loading with various scenarios"""
    print("\n=== Testing Config Loading ===")
    
    # Test with non-existent config file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        wrong_config = Path(f.name)
    wrong_config.unlink()  # Remove the file
    
    config = load_configuration(wrong_config)
    print(f"Loaded default config: {bool(config)}")
    print(f"Default categories: {list(config.keys())}")
    
    # Test with valid config
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump({
            "file_categories": {
                "Test": [".test"]
            }
        }, f)
        valid_config = Path(f.name)
    
    config = load_configuration(valid_config)
    print(f"Loaded custom config: {bool(config)}")
    print(f"Custom categories: {list(config.keys())}")
    
    valid_config.unlink()  # Clean up


def test_path_traversal_vulnerability():
    """Test potential path traversal vulnerability"""
    print("\n=== Testing Path Traversal Vulnerability ===")
    
    # This demonstrates a potential issue with path construction
    # In the original code, config_path is constructed as:
    # base_path / '..' / '..' / 'config.json'
    # If an attacker controlled the base path structure, they could access arbitrary files
    
    base_path = Path("/some/valid/path")
    config_path = base_path / '..' / '..' / 'config.json'
    print(f"Base path: {base_path}")
    print(f"Config path: {config_path}")
    print(f"Resolved config path: {config_path.resolve()}")
    
    # The issue is that if an attacker can control directory structure,
    # they could potentially make this resolve to sensitive locations


def test_worker_race_condition_simulation():
    """Simulate potential race conditions"""
    print("\n=== Testing Worker Race Condition Simulation ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        downloads_path = test_dir / "Downloads"
        downloads_path.mkdir()
        
        # Create a category directory that multiple workers might try to create
        category_dir = downloads_path / "TestCategory"
        
        # Simulate multiple workers trying to create the same directory
        def worker_create_dir():
            try:
                category_dir.mkdir(exist_ok=True)
                print(f"Thread {threading.current_thread().name} created directory")
            except FileExistsError:
                print(f"Thread {threading.current_thread().name} encountered FileExistsError")
            except Exception as e:
                print(f"Thread {threading.current_thread().name} encountered error: {e}")
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker_create_dir, name=f"Worker-{i}")
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        print(f"Directory exists: {category_dir.exists()}")


def test_file_creation_during_sort():
    """Test file creation during sorting process"""
    print("\n=== Testing File Creation During Sort ===")
    
    import time
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        downloads_path = test_dir / "Downloads"
        downloads_path.mkdir()
        
        # Create a file that we'll modify during the wait period
        test_file = downloads_path / "test_file.txt"
        
        with open(test_file, 'w') as f:
            f.write("Initial content")
        
        print(f"Initial file size: {test_file.stat().st_size}")
        
        # Start a thread that will modify the file
        def modify_file():
            time.sleep(0.5)  # Wait a bit before modification
            with open(test_file, 'a') as f:
                f.write("Additional content")
            print(f"Modified file size: {test_file.stat().st_size}")
        
        modifier_thread = threading.Thread(target=modify_file)
        modifier_thread.start()
        
        # Simulate the file completion wait logic
        prev_size = -1
        max_attempts = 10
        wait_seconds = 1
        
        for attempt in range(max_attempts):
            if not test_file.exists():
                print(f"File no longer exists at attempt {attempt}")
                break
                
            current_size = test_file.stat().st_size
            print(f"Attempt {attempt}: Size = {current_size}, Prev = {prev_size}")
            
            if current_size == prev_size and current_size > 0:
                print(f"File appears stable at attempt {attempt}")
                break
                
            prev_size = current_size
            time.sleep(wait_seconds)
        else:
            print("File never stabilized after max attempts")
        
        modifier_thread.join()


def test_unique_filename_generation():
    """Test unique filename generation logic"""
    print("\n=== Testing Unique Filename Generation ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        dest_folder = test_dir / "TestCategory"
        dest_folder.mkdir()
        
        # Create some test files
        test_file1 = dest_folder / "test.txt"
        test_file2 = dest_folder / "test_1.txt"
        test_file3 = dest_folder / "test_2.txt"
        
        test_file1.touch()
        test_file2.touch()
        test_file3.touch()
        
        # Import the worker's method for generating unique paths
        from src.orionis.sorter import SortWorker
        import queue
        
        work_queue = queue.Queue()
        status_queue = queue.Queue()
        stop_event = threading.Event()
        
        worker = SortWorker(work_queue, status_queue, test_dir / "Downloads", {}, stop_event)
        
        # Test the unique destination generation
        unique_path = worker._get_unique_destination(dest_folder, "test.txt")
        print(f"Original: test.txt")
        print(f"Unique path: {unique_path}")
        
        # Test with no existing collision
        unique_path2 = worker._get_unique_destination(dest_folder, "new.txt")
        print(f"Original: new.txt")
        print(f"Unique path: {unique_path2}")


def test_path_manipulation():
    """Test potential path manipulation issues"""
    print("\n=== Testing Path Manipulation ===")
    
    # Create a malformed filename that could cause issues
    malicious_filename = "../test_folder/malicious.txt"
    print(f"Malicious filename: {malicious_filename}")
    
    # The original code doesn't validate this, which could be problematic
    # This is an example of why path validation is important


def run_comprehensive_tests():
    """Run all tests"""
    print("Starting comprehensive debug tests for Orionis Auto Sort")
    
    setup_test_logging()
    test_config_loading()
    test_path_traversal_vulnerability()
    test_worker_race_condition_simulation()
    test_file_creation_during_sort()
    test_unique_filename_generation()
    test_path_manipulation()
    
    print("\n=== Debug tests completed ===")


if __name__ == "__main__":
    run_comprehensive_tests()
#!/usr/bin/env python3
"""
Comprehensive unit tests for file_io_utils.py
Tests all file I/O operations with various edge cases
"""

import json
import pickle
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import unittest
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utilities.file_io_utils import FileIOUtils, save_json, load_json, save_timestamped_json, find_latest_json


class TestFileIOUtils(unittest.TestCase):
    """Test suite for FileIOUtils class"""
    
    def setUp(self):
        """Setup test environment before each test"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_data = {
            "name": "test",
            "value": 42,
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "timestamp": datetime.now()
        }
    
    def tearDown(self):
        """Clean up test environment after each test"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_save_json_basic(self):
        """Test basic JSON save functionality"""
        filepath = self.test_dir / "test.json"
        result = FileIOUtils.save_json(self.test_data, filepath)
        
        self.assertEqual(result, filepath)
        self.assertTrue(filepath.exists())
        
        # Verify content
        with open(filepath) as f:
            loaded = json.load(f)
        self.assertEqual(loaded["name"], "test")
        self.assertEqual(loaded["value"], 42)
    
    def test_save_json_with_nested_dirs(self):
        """Test JSON save with nested directory creation"""
        filepath = self.test_dir / "nested" / "deep" / "test.json"
        result = FileIOUtils.save_json(self.test_data, filepath)
        
        self.assertEqual(result, filepath)
        self.assertTrue(filepath.exists())
        self.assertTrue(filepath.parent.exists())
    
    def test_load_json_basic(self):
        """Test basic JSON load functionality"""
        filepath = self.test_dir / "test.json"
        FileIOUtils.save_json(self.test_data, filepath)
        
        loaded = FileIOUtils.load_json(filepath)
        self.assertEqual(loaded["name"], "test")
        self.assertEqual(loaded["value"], 42)
        self.assertEqual(loaded["nested"]["key"], "value")
    
    def test_load_json_file_not_found(self):
        """Test JSON load with non-existent file"""
        filepath = self.test_dir / "nonexistent.json"
        
        with self.assertRaises(FileNotFoundError):
            FileIOUtils.load_json(filepath)
    
    def test_load_json_invalid_format(self):
        """Test JSON load with invalid JSON format"""
        filepath = self.test_dir / "invalid.json"
        with open(filepath, 'w') as f:
            f.write("invalid json {")
        
        with self.assertRaises(json.JSONDecodeError):
            FileIOUtils.load_json(filepath)
    
    def test_save_pickle_basic(self):
        """Test basic pickle save functionality"""
        filepath = self.test_dir / "test.pkl"
        complex_data = {
            "object": datetime.now(),
            "bytes": b"binary data",
            "set": {1, 2, 3}
        }
        
        result = FileIOUtils.save_pickle(complex_data, filepath)
        self.assertEqual(result, filepath)
        self.assertTrue(filepath.exists())
    
    def test_load_pickle_basic(self):
        """Test basic pickle load functionality"""
        filepath = self.test_dir / "test.pkl"
        complex_data = {
            "object": datetime.now(),
            "bytes": b"binary data",
            "set": {1, 2, 3}
        }
        
        FileIOUtils.save_pickle(complex_data, filepath)
        loaded = FileIOUtils.load_pickle(filepath)
        
        self.assertEqual(loaded["bytes"], b"binary data")
        self.assertEqual(loaded["set"], {1, 2, 3})
        self.assertIsInstance(loaded["object"], datetime)
    
    def test_load_pickle_file_not_found(self):
        """Test pickle load with non-existent file"""
        filepath = self.test_dir / "nonexistent.pkl"
        
        with self.assertRaises(FileNotFoundError):
            FileIOUtils.load_pickle(filepath)
    
    def test_save_timestamped_json(self):
        """Test timestamped JSON save functionality"""
        base_dir = self.test_dir / "outputs"
        prefix = "test_data"
        
        filepath = FileIOUtils.save_timestamped(
            self.test_data, 
            base_dir, 
            prefix,
            suffix="json",
            date_format="%Y%m%d",
            time_format="%H%M%S"
        )
        
        self.assertTrue(filepath.exists())
        self.assertEqual(filepath.suffix, ".json")
        self.assertIn(prefix, filepath.name)
        
        # Check directory structure
        date_dir = filepath.parent
        self.assertEqual(date_dir.name, datetime.now().strftime("%Y%m%d"))
        
        # Verify content
        loaded = FileIOUtils.load_json(filepath)
        self.assertEqual(loaded["name"], "test")
    
    def test_save_timestamped_pickle(self):
        """Test timestamped pickle save functionality"""
        base_dir = self.test_dir / "outputs"
        prefix = "test_data"
        
        filepath = FileIOUtils.save_timestamped(
            self.test_data, 
            base_dir, 
            prefix,
            suffix="pkl",
            use_json=False
        )
        
        self.assertTrue(filepath.exists())
        self.assertEqual(filepath.suffix, ".pkl")
        self.assertIn(prefix, filepath.name)
    
    def test_find_latest_file(self):
        """Test finding the latest file by modification time"""
        # Create multiple files with different timestamps
        import time
        
        for i in range(3):
            filepath = self.test_dir / f"test_{i}.json"
            FileIOUtils.save_json({"index": i}, filepath)
            time.sleep(0.1)  # Ensure different timestamps
        
        latest = FileIOUtils.find_latest_file(self.test_dir, "*.json")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.name, "test_2.json")
        
        # Test with recursive search
        nested_dir = self.test_dir / "nested"
        nested_file = nested_dir / "test_3.json"
        FileIOUtils.save_json({"index": 3}, nested_file)
        
        latest_recursive = FileIOUtils.find_latest_file(self.test_dir, "*.json", recursive=True)
        self.assertEqual(latest_recursive.name, "test_3.json")
    
    def test_find_latest_file_no_matches(self):
        """Test find latest file with no matching files"""
        result = FileIOUtils.find_latest_file(self.test_dir, "*.xml")
        self.assertIsNone(result)
    
    def test_find_latest_file_nonexistent_dir(self):
        """Test find latest file with non-existent directory"""
        result = FileIOUtils.find_latest_file(self.test_dir / "nonexistent", "*.json")
        self.assertIsNone(result)
    
    def test_cleanup_old_files(self):
        """Test cleaning up old files keeping only recent ones"""
        # Create 10 test files
        import time
        
        for i in range(10):
            filepath = self.test_dir / f"test_{i:02d}.json"
            FileIOUtils.save_json({"index": i}, filepath)
            time.sleep(0.05)  # Ensure different timestamps
        
        # Keep only 5 most recent
        deleted = FileIOUtils.cleanup_old_files(self.test_dir, "*.json", keep_count=5)
        
        self.assertEqual(len(deleted), 5)
        remaining = list(self.test_dir.glob("*.json"))
        self.assertEqual(len(remaining), 5)
        
        # Check that we kept the most recent ones
        names = sorted([f.name for f in remaining])
        self.assertEqual(names, ["test_05.json", "test_06.json", "test_07.json", "test_08.json", "test_09.json"])
    
    def test_cleanup_old_files_dry_run(self):
        """Test cleanup in dry run mode"""
        # Create test files
        for i in range(5):
            filepath = self.test_dir / f"test_{i}.json"
            FileIOUtils.save_json({"index": i}, filepath)
        
        # Dry run should not delete anything
        deleted = FileIOUtils.cleanup_old_files(self.test_dir, "*.json", keep_count=2, dry_run=True)
        
        self.assertEqual(len(deleted), 0)  # Nothing actually deleted
        remaining = list(self.test_dir.glob("*.json"))
        self.assertEqual(len(remaining), 5)  # All files still exist
    
    def test_backward_compatibility_functions(self):
        """Test backward compatibility convenience functions"""
        filepath = self.test_dir / "compat.json"
        
        # Test save_json function
        save_json(self.test_data, filepath)
        self.assertTrue(filepath.exists())
        
        # Test load_json function
        loaded = load_json(filepath)
        self.assertEqual(loaded["name"], "test")
        
        # Test save_timestamped_json function
        ts_path = save_timestamped_json(self.test_data, self.test_dir, "compat")
        self.assertTrue(ts_path.exists())
        self.assertEqual(ts_path.suffix, ".json")
        
        # Test find_latest_json function
        latest = find_latest_json(self.test_dir)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.suffix, ".json")
    
    def test_pathlib_compatibility(self):
        """Test that both str and Path objects work as inputs"""
        # Test with Path object
        filepath_path = self.test_dir / "path_test.json"
        FileIOUtils.save_json(self.test_data, filepath_path)
        loaded_path = FileIOUtils.load_json(filepath_path)
        
        # Test with string
        filepath_str = str(self.test_dir / "str_test.json")
        FileIOUtils.save_json(self.test_data, filepath_str)
        loaded_str = FileIOUtils.load_json(filepath_str)
        
        self.assertEqual(loaded_path["name"], loaded_str["name"])
    
    def test_custom_json_kwargs(self):
        """Test passing custom kwargs to json.dump"""
        filepath = self.test_dir / "custom.json"
        
        # Save with custom indentation and sorting
        FileIOUtils.save_json(
            self.test_data, 
            filepath, 
            indent=4, 
            sort_keys=True
        )
        
        # Read raw file to check formatting
        with open(filepath) as f:
            content = f.read()
        
        # Check that keys are sorted (list should come before name)
        self.assertLess(content.index('"list"'), content.index('"name"'))
        # Check indentation (4 spaces)
        self.assertIn('    "list"', content)


if __name__ == "__main__":
    unittest.main()
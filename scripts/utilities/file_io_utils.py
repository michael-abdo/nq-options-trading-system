#!/usr/bin/env python3
"""
Common File I/O Utilities
Centralized functions for JSON, pickle, and timestamped file operations
"""

import json
import pickle
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class FileIOUtils:
    """Common file I/O operations with standardized error handling"""
    
    @staticmethod
    def save_json(data: Any, filepath: Union[str, Path], indent: int = 2, **kwargs) -> Path:
        """
        Save data to JSON file with error handling
        
        Args:
            data: Data to save
            filepath: Path to save to
            indent: JSON indentation level
            **kwargs: Additional arguments for json.dump
            
        Returns:
            Path object of saved file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=indent, default=str, **kwargs)
            logger.debug(f"Saved JSON to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save JSON to {filepath}: {e}")
            raise
    
    @staticmethod
    def load_json(filepath: Union[str, Path]) -> Any:
        """
        Load data from JSON file with error handling
        
        Args:
            filepath: Path to load from
            
        Returns:
            Loaded data
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"JSON file not found: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            logger.debug(f"Loaded JSON from {filepath}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load JSON from {filepath}: {e}")
            raise
    
    @staticmethod
    def save_pickle(data: Any, filepath: Union[str, Path]) -> Path:
        """
        Save data to pickle file with error handling
        
        Args:
            data: Data to save
            filepath: Path to save to
            
        Returns:
            Path object of saved file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"Saved pickle to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save pickle to {filepath}: {e}")
            raise
    
    @staticmethod
    def load_pickle(filepath: Union[str, Path]) -> Any:
        """
        Load data from pickle file with error handling
        
        Args:
            filepath: Path to load from
            
        Returns:
            Loaded data
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Pickle file not found: {filepath}")
        
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            logger.debug(f"Loaded pickle from {filepath}")
            return data
        except Exception as e:
            logger.error(f"Failed to load pickle from {filepath}: {e}")
            raise
    
    @staticmethod
    def save_timestamped(
        data: Any, 
        base_dir: Union[str, Path], 
        prefix: str, 
        suffix: str = "json",
        date_format: str = "%Y%m%d",
        time_format: str = "%H%M%S",
        use_json: bool = True
    ) -> Path:
        """
        Save data with timestamp in organized directory structure
        
        Args:
            data: Data to save
            base_dir: Base directory for output
            prefix: Filename prefix
            suffix: File extension
            date_format: Date format for directory
            time_format: Time format for filename
            use_json: Use JSON (True) or pickle (False)
            
        Returns:
            Path object of saved file
        """
        now = datetime.now()
        date_dir = now.strftime(date_format)
        timestamp = now.strftime(time_format)
        
        # Create directory structure
        output_dir = Path(base_dir) / date_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{prefix}_{timestamp}.{suffix}"
        filepath = output_dir / filename
        
        # Save based on format
        if use_json and suffix == "json":
            return FileIOUtils.save_json(data, filepath)
        elif suffix == "pkl":
            return FileIOUtils.save_pickle(data, filepath)
        else:
            # Generic save for other formats
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w' if use_json else 'wb') as f:
                if use_json:
                    json.dump(data, f, indent=2, default=str)
                else:
                    f.write(str(data))
            return filepath
    
    @staticmethod
    def find_latest_file(
        base_dir: Union[str, Path], 
        pattern: str = "*.json",
        recursive: bool = True
    ) -> Optional[Path]:
        """
        Find the most recently modified file matching pattern
        
        Args:
            base_dir: Directory to search
            pattern: Glob pattern to match
            recursive: Search recursively
            
        Returns:
            Path to latest file or None
        """
        base_dir = Path(base_dir)
        
        if not base_dir.exists():
            logger.warning(f"Directory not found: {base_dir}")
            return None
        
        # Find all matching files
        if recursive:
            files = list(base_dir.rglob(pattern))
        else:
            files = list(base_dir.glob(pattern))
        
        if not files:
            logger.warning(f"No files found matching {pattern} in {base_dir}")
            return None
        
        # Sort by modification time
        latest = max(files, key=lambda f: f.stat().st_mtime)
        logger.debug(f"Found latest file: {latest}")
        return latest
    
    @staticmethod
    def cleanup_old_files(
        directory: Union[str, Path],
        pattern: str = "*",
        keep_count: int = 5,
        dry_run: bool = False
    ) -> list[Path]:
        """
        Clean up old files, keeping only the most recent ones
        
        Args:
            directory: Directory to clean
            pattern: File pattern to match
            keep_count: Number of files to keep
            dry_run: If True, don't actually delete
            
        Returns:
            List of deleted file paths
        """
        directory = Path(directory)
        
        if not directory.exists():
            return []
        
        # Find all matching files
        files = sorted(
            directory.glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        # Identify files to delete
        to_delete = files[keep_count:] if len(files) > keep_count else []
        
        deleted = []
        for file in to_delete:
            if dry_run:
                logger.info(f"Would delete: {file}")
            else:
                try:
                    file.unlink()
                    logger.info(f"Deleted: {file}")
                    deleted.append(file)
                except Exception as e:
                    logger.error(f"Failed to delete {file}: {e}")
        
        return deleted


# Convenience functions for backward compatibility
def save_json(data: Any, filepath: Union[str, Path], **kwargs) -> Path:
    """Save data to JSON file"""
    return FileIOUtils.save_json(data, filepath, **kwargs)


def load_json(filepath: Union[str, Path]) -> Any:
    """Load data from JSON file"""
    return FileIOUtils.load_json(filepath)


def save_timestamped_json(
    data: Any,
    base_dir: Union[str, Path],
    prefix: str
) -> Path:
    """Save JSON data with timestamp"""
    return FileIOUtils.save_timestamped(data, base_dir, prefix, suffix="json")


def find_latest_json(base_dir: Union[str, Path]) -> Optional[Path]:
    """Find most recent JSON file in directory"""
    return FileIOUtils.find_latest_file(base_dir, "*.json")
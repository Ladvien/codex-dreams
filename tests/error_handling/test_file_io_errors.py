#!/usr/bin/env python3
"""
STORY-004: File I/O Error Handling Tests
Comprehensive tests for file I/O operations including permissions,
missing files, disk space issues, and network file system failures.
"""

import json
import os
import shutil
import stat

# Import from biological_memory error handling
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "biological_memory"))

try:
    from error_handling import (
        BiologicalMemoryErrorHandler,
        ErrorEvent,
        ErrorType,
        SecuritySanitizer,
    )
except ImportError:
    pytest.skip("Error handling module not available", allow_module_level=True)


class TestFileIOErrorHandling:
    """Test comprehensive file I/O error handling patterns."""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.error_handler = BiologicalMemoryErrorHandler(base_path=str(self.temp_dir))

    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_permission_error_handling(self):
        """Test handling of file permission errors"""

        # Create a file and remove read permissions
        test_file = self.temp_dir / "permission_test.txt"
        test_file.write_text("Test content")

        # Remove read permissions
        os.chmod(test_file, 0o000)

        try:
            # Attempt to read should handle permission error gracefully
            def read_protected_file():
                return test_file.read_text()

            # Should retry and eventually fail with permission error
            with pytest.raises(Exception):
                self.error_handler.exponential_backoff_retry(
                    read_protected_file,
                    max_retries=2,
                    base_delay=0.1,
                    exceptions=(PermissionError, OSError),
                )

        finally:
            # Restore permissions for cleanup
            os.chmod(test_file, 0o644)

    def test_missing_file_error_handling(self):
        """Test handling of missing file errors"""

        nonexistent_file = self.temp_dir / "does_not_exist.txt"

        def read_missing_file():
            if not nonexistent_file.exists():
                raise FileNotFoundError(f"File not found: {nonexistent_file}")
            return nonexistent_file.read_text()

        # Should handle FileNotFoundError gracefully
        with pytest.raises(FileNotFoundError):
            self.error_handler.exponential_backoff_retry(
                read_missing_file, max_retries=3, base_delay=0.1, exceptions=(FileNotFoundError,)
            )

        # Verify error was logged
        assert self.error_handler.recovery_stats["total_errors"] > 0

    def test_disk_space_exhaustion_error_handling(self):
        """Test handling of disk space exhaustion"""

        # Mock disk space check
        def mock_disk_space_check():
            # Simulate disk space exhaustion
            raise OSError("No space left on device")

        with pytest.raises(OSError, match="No space left on device"):
            self.error_handler.exponential_backoff_retry(
                mock_disk_space_check, max_retries=2, base_delay=0.1, exceptions=(OSError,)
            )

    def test_file_locking_conflict_handling(self):
        """Test handling of file locking conflicts"""

        test_file = self.temp_dir / "lock_test.txt"
        test_file.write_text("Initial content")

        # Simulate file being locked by another process
        lock_attempts = 0

        def try_write_locked_file():
            nonlocal lock_attempts
            lock_attempts += 1

            # Simulate lock conflict for first 2 attempts
            if lock_attempts <= 2:
                raise OSError("Resource temporarily unavailable")

            # Success on third attempt
            test_file.write_text("Updated content")
            return "Success"

        # Should eventually succeed after retries
        result = self.error_handler.exponential_backoff_retry(
            try_write_locked_file, max_retries=3, base_delay=0.1, exceptions=(OSError,)
        )

        assert result == "Success"
        assert lock_attempts == 3
        assert test_file.read_text() == "Updated content"

    def test_corrupted_file_recovery(self):
        """Test recovery from corrupted files"""

        # Create a file with corrupted JSON
        corrupted_file = self.temp_dir / "corrupted.json"
        corrupted_file.write_text('{"incomplete": json data without closing brace')

        def read_json_with_recovery():
            content = corrupted_file.read_text()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Recovery strategy: return safe default
                return {"error": "corrupted_data", "recovered": True}

        result = read_json_with_recovery()
        assert result["error"] == "corrupted_data"
        assert result["recovered"] is True

    def test_network_file_system_timeout_handling(self):
        """Test handling of network file system timeouts"""

        # Mock network file system operation that times out
        def network_file_operation():
            import time

            time.sleep(0.5)  # Simulate network delay
            return "Network operation completed"

        # Test with timeout
        start_time = __import__("time").time()

        result = self.error_handler.exponential_backoff_retry(
            network_file_operation, max_retries=1, base_delay=0.1, exceptions=(Exception,)
        )

        elapsed = __import__("time").time() - start_time
        assert result == "Network operation completed"
        assert elapsed >= 0.5  # Should have taken at least the operation time

    def test_directory_creation_error_handling(self):
        """Test error handling for directory creation"""

        # Test creating directory in protected location
        def create_protected_directory():
            protected_path = Path("/root/protected_directory")  # Requires admin
            try:
                protected_path.mkdir(parents=True, exist_ok=True)
                return True
            except PermissionError:
                # Fallback to temp directory
                fallback_path = self.temp_dir / "fallback_directory"
                fallback_path.mkdir(parents=True, exist_ok=True)
                return fallback_path.exists()

        result = create_protected_directory()
        assert result is True  # Should succeed with fallback
        assert (self.temp_dir / "fallback_directory").exists()

    def test_file_encoding_error_handling(self):
        """Test handling of file encoding errors"""

        # Create file with mixed encoding
        binary_file = self.temp_dir / "mixed_encoding.txt"

        # Write binary data that's not valid UTF-8
        with open(binary_file, "wb") as f:
            f.write(b"Valid text\xff\xfe\x00Invalid UTF-8\x80\x81")

        def read_with_encoding_recovery():
            try:
                # Try UTF-8 first
                with open(binary_file, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                try:
                    # Fallback to latin-1 which accepts all byte values
                    with open(binary_file, "r", encoding="latin-1") as f:
                        content = f.read()
                    return f"[ENCODING_RECOVERED] {content[:20]}..."
                except Exception:
                    # Final fallback: read as binary and represent as hex
                    with open(binary_file, "rb") as f:
                        binary_content = f.read()
                    return f"[BINARY_FALLBACK] {binary_content[:10].hex()}..."

        result = read_with_encoding_recovery()
        assert "[ENCODING_RECOVERED]" in result or "[BINARY_FALLBACK]" in result

    def test_atomic_file_operations_error_handling(self):
        """Test error handling for atomic file operations"""

        target_file = self.temp_dir / "atomic_target.txt"
        target_file.write_text("Original content")

        def atomic_file_update(content):
            # Use temporary file for atomic update
            temp_file = target_file.with_suffix(".tmp")

            try:
                # Write to temporary file
                temp_file.write_text(content)

                # Simulate failure during atomic move
                if "fail" in content:
                    raise OSError("Simulated atomic operation failure")

                # Atomic move (replace)
                temp_file.replace(target_file)
                return True

            except Exception as e:
                # Cleanup temporary file on failure
                if temp_file.exists():
                    temp_file.unlink()
                raise e

        # Test successful atomic update
        result = atomic_file_update("New content")
        assert result is True
        assert target_file.read_text() == "New content"

        # Test failed atomic update
        with pytest.raises(OSError, match="atomic operation failure"):
            atomic_file_update("fail content")

        # Original content should be preserved
        assert target_file.read_text() == "New content"  # Not corrupted

    def test_large_file_handling_with_memory_limits(self):
        """Test error handling for large files that exceed memory limits"""

        large_file = self.temp_dir / "large_file.txt"

        def create_large_file():
            # Simulate creating a large file
            with open(large_file, "w") as f:
                # Write in chunks to simulate large file
                for i in range(100):
                    f.write(f"Line {i}: " + "x" * 1000 + "\n")
            return large_file.stat().st_size

        def read_large_file_chunked():
            content_chunks = []
            chunk_size = 4096  # Read in 4KB chunks

            with open(large_file, "r") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    content_chunks.append(len(chunk))  # Just track chunk sizes

                    # Simulate memory pressure
                    if len(content_chunks) > 50:  # Limit chunks in memory
                        # Keep only recent chunks
                        content_chunks = content_chunks[-10:]

            return sum(content_chunks)

        # Create large file
        file_size = create_large_file()
        assert file_size > 100000  # Should be reasonably large

        # Read with chunked approach
        processed_size = read_large_file_chunked()
        assert processed_size > 0  # Should have processed some data

    def test_concurrent_file_access_handling(self):
        """Test handling of concurrent file access conflicts"""

        shared_file = self.temp_dir / "shared_file.txt"
        shared_file.write_text("0")  # Initial counter value

        def increment_counter():
            """Simulate concurrent counter increment with file locking"""
            import fcntl  # Unix file locking

            try:
                with open(shared_file, "r+") as f:
                    # Try to acquire exclusive lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                    # Read current value
                    f.seek(0)
                    current = int(f.read().strip())

                    # Increment
                    new_value = current + 1

                    # Write back
                    f.seek(0)
                    f.write(str(new_value))
                    f.truncate()

                    # Lock is automatically released when file is closed
                    return new_value

            except (OSError, BlockingIOError) as e:
                # Handle lock conflict
                raise OSError(f"File lock conflict: {e}")

        # Test multiple increments (simulating concurrent access)
        for i in range(5):
            try:
                result = increment_counter()
                assert result == i + 1
            except OSError:
                # On lock conflict, retry with exponential backoff
                result = self.error_handler.exponential_backoff_retry(
                    increment_counter, max_retries=3, base_delay=0.01, exceptions=(OSError,)
                )
                assert isinstance(result, int)

    def test_file_system_watcher_error_recovery(self):
        """Test error recovery for file system watchers"""

        watch_dir = self.temp_dir / "watch_directory"
        watch_dir.mkdir()

        events_log = []

        def file_system_watcher():
            """Simplified file system watcher with error recovery"""
            import time

            # Simulate watching for file changes
            test_file = watch_dir / "watched_file.txt"

            if not test_file.exists():
                test_file.write_text("Initial content")
                events_log.append("file_created")

            # Simulate watcher error (directory deleted)
            if not watch_dir.exists():
                raise FileNotFoundError("Watch directory no longer exists")

            # Simulate file modification
            if test_file.exists():
                content = test_file.read_text()
                test_file.write_text(content + " [modified]")
                events_log.append("file_modified")

            return len(events_log)

        # Test successful watching
        result = file_system_watcher()
        assert result >= 1
        assert "file_created" in events_log

        # Simulate directory deletion and recovery
        shutil.rmtree(watch_dir)

        def watcher_with_recovery():
            try:
                return file_system_watcher()
            except FileNotFoundError:
                # Recovery: recreate watch directory
                watch_dir.mkdir()
                events_log.append("directory_recovered")
                return file_system_watcher()

        result = watcher_with_recovery()
        assert result >= 1
        assert "directory_recovered" in events_log


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

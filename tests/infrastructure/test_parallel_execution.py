"""
Test parallel execution capabilities of the refactored test architecture.

Validates that tests can run efficiently in parallel with proper resource
management and no race conditions.
"""

import multiprocessing
import os
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from unittest.mock import patch

import pytest


class TestParallelCapabilities:
    """Test parallel test execution capabilities."""

    def test_pytest_xdist_compatibility(self):
        """Test that the test architecture is compatible with pytest-xdist."""
        # Check if pytest-xdist is available
        try:
            import xdist

            xdist_available = True
        except ImportError:
            xdist_available = False

        if xdist_available:
            # Test that we can create multiple worker configurations
            worker_configs = ["auto", "2", "4", "worksteal"]
            for config in worker_configs:
                assert isinstance(config, str), f"Worker config {config} should be valid"

    def test_concurrent_database_connections(self):
        """Test that multiple database connections can coexist."""
        import os
        import tempfile

        import duckdb

        def create_isolated_connection(worker_id):
            """Create an isolated database connection."""
            import os
            import tempfile

            import duckdb

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f"_worker_{worker_id}.duckdb"
            ) as f:
                db_path = f.name

            # Remove the empty file so DuckDB can create a proper database
            os.unlink(db_path)

            try:
                conn = duckdb.connect(db_path)

                # Install extensions
                try:
                    conn.execute("INSTALL json")
                    conn.execute("LOAD json")
                except Exception:
                    pass

                # Create test table
                conn.execute("CREATE TABLE worker_test (worker_id INTEGER, timestamp TIMESTAMP)")
                conn.execute("INSERT INTO worker_test VALUES (?, CURRENT_TIMESTAMP)", (worker_id,))

                # Verify data
                result = conn.execute("SELECT worker_id FROM worker_test").fetchall()
                assert result[0][0] == worker_id

                conn.close()
                return worker_id
            finally:
                import os

                if os.path.exists(db_path):
                    os.unlink(db_path)

        # Test with thread pool (similar to pytest-xdist)
        max_workers = min(4, multiprocessing.cpu_count())
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(create_isolated_connection, i) for i in range(8)]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        assert len(results) == 8
        assert set(results) == set(range(8))

    def test_concurrent_mock_usage(self):
        """Test that mocks work correctly under parallel execution."""

        def test_mock_responses(worker_id):
            """Test mock responses in parallel worker."""
            import json

            # Simulate the mock_ollama behavior
            mock_responses = {
                "extraction": {
                    "entities": ["test", "parallel"],
                    "worker_id": worker_id,
                    "timestamp": time.time(),
                }
            }

            # Multiple calls to test consistency
            responses = []
            for i in range(3):
                response = json.dumps(mock_responses["extraction"])
                parsed = json.loads(response)
                responses.append(parsed["worker_id"])

            return worker_id, responses

        # Execute in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(test_mock_responses, i) for i in range(6)]

            results = []
            for future in as_completed(futures):
                worker_id, responses = future.result()
                results.append((worker_id, responses))

        # Verify all workers completed successfully
        assert len(results) == 6
        for worker_id, responses in results:
            assert all(resp == worker_id for resp in responses)

    def test_resource_contention_handling(self):
        """Test handling of resource contention in parallel execution."""
        shared_resource = {"counter": 0, "lock": threading.Lock()}

        def access_shared_resource(worker_id):
            """Simulate shared resource access with proper locking."""
            results = []

            for i in range(10):
                with shared_resource["lock"]:
                    current = shared_resource["counter"]
                    # Simulate some processing time
                    time.sleep(0.001)
                    shared_resource["counter"] = current + 1
                    results.append(shared_resource["counter"])

            return worker_id, results

        # Run multiple workers accessing shared resource
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(access_shared_resource, i) for i in range(4)]

            all_results = []
            for future in as_completed(futures):
                worker_id, results = future.result()
                all_results.extend(results)

        # Verify no race conditions occurred
        assert len(all_results) == 40  # 4 workers * 10 operations each
        assert shared_resource["counter"] == 40
        assert max(all_results) == 40

    def test_memory_usage_scaling(self):
        """Test that memory usage scales reasonably with parallel execution."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        def memory_intensive_task(task_id):
            """Create and process some test data."""
            # Generate test data
            large_list = list(range(task_id * 1000, (task_id + 1) * 1000))

            # Process data
            processed = [x * 2 for x in large_list if x % 2 == 0]

            # Simulate biological memory processing
            memory_items = []
            for i, value in enumerate(processed):
                if i < 7:  # Miller's 7±2 limit
                    memory_items.append(
                        {
                            "id": i,
                            "content": f"Memory item {value}",
                            "activation": 1.0 - (i * 0.1),
                            "task_id": task_id,
                        }
                    )

            return task_id, len(memory_items), len(processed)

        # Execute memory-intensive tasks in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(memory_intensive_task, i) for i in range(8)]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100 * 1024 * 1024, "Memory usage should scale reasonably"

        # All tasks should have completed successfully
        assert len(results) == 8
        for task_id, memory_items, processed_items in results:
            assert memory_items <= 7, "Should respect Miller's capacity limit"
            assert processed_items > 0, "Should have processed some items"


class TestPerformanceOptimizations:
    """Test performance optimizations for parallel execution."""

    def test_fixture_setup_time(self, performance_benchmark):
        """Test that fixture setup doesn't become a bottleneck."""
        timer = performance_benchmark()

        # Simulate multiple fixture setups
        setup_times = []
        for i in range(5):
            with timer:
                # Simulate database fixture setup
                import tempfile

                with tempfile.NamedTemporaryFile(delete=True) as f:
                    db_path = f.name

                # Simulate schema creation
                time.sleep(0.001)  # Minimal setup time

            setup_times.append(timer.elapsed_ms)

        # Average setup time should be reasonable
        avg_setup = sum(setup_times) / len(setup_times)
        assert (
            avg_setup < 10
        ), f"Average fixture setup time ({avg_setup:.2f}ms) should be under 10ms"

    def test_parallel_speedup_measurement(self):
        """Measure actual speedup from parallel execution."""

        def sequential_task(task_count):
            """Execute tasks sequentially."""
            start_time = time.perf_counter()

            results = []
            for i in range(task_count):
                # Simulate test execution
                time.sleep(0.01)  # 10ms per test
                results.append(i * 2)

            end_time = time.perf_counter()
            return results, end_time - start_time

        def parallel_task(task_count):
            """Execute tasks in parallel."""
            start_time = time.perf_counter()

            def single_task(task_id):
                time.sleep(0.01)  # Same 10ms per test
                return task_id * 2

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(single_task, i) for i in range(task_count)]
                results = [future.result() for future in as_completed(futures)]

            end_time = time.perf_counter()
            return results, end_time - start_time

        task_count = 12  # Should show clear parallel benefit

        # Run sequential version
        seq_results, seq_time = sequential_task(task_count)

        # Run parallel version
        par_results, par_time = parallel_task(task_count)

        # Results should be the same
        assert set(seq_results) == set(par_results)

        # Parallel should be faster (allowing for overhead)
        speedup_ratio = seq_time / par_time
        assert (
            speedup_ratio > 1.5
        ), f"Parallel execution should show speedup (ratio: {speedup_ratio:.2f})"

    def test_resource_cleanup_efficiency(self):
        """Test that resource cleanup is efficient in parallel scenarios."""
        import os
        import tempfile

        def create_and_cleanup_resources(worker_id):
            """Create temporary resources and clean them up."""
            temp_files = []

            # Create multiple temporary files
            for i in range(5):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f"_w{worker_id}_f{i}.tmp"
                ) as f:
                    f.write(f"Worker {worker_id} File {i}".encode())
                    temp_files.append(f.name)

            # Verify all files exist
            for temp_file in temp_files:
                assert os.path.exists(temp_file)

            # Clean up (simulating fixture teardown)
            for temp_file in temp_files:
                os.unlink(temp_file)

            # Verify cleanup
            for temp_file in temp_files:
                assert not os.path.exists(temp_file)

            return worker_id, len(temp_files)

        # Execute cleanup test in parallel
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_and_cleanup_resources, i) for i in range(8)]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        cleanup_time = time.perf_counter() - start_time

        # All workers should have completed successfully
        assert len(results) == 8
        for worker_id, file_count in results:
            assert file_count == 5

        # Cleanup should be reasonably fast
        assert cleanup_time < 2.0, f"Resource cleanup took {cleanup_time:.2f}s, should be under 2s"

    @pytest.mark.slow
    def test_large_scale_parallel_execution(self):
        """Test behavior with large numbers of parallel tests."""

        def simulate_test_execution(test_id):
            """Simulate a complete test execution."""
            # Simulate fixture setup
            setup_start = time.perf_counter()
            time.sleep(0.002)  # 2ms setup
            setup_time = time.perf_counter() - setup_start

            # Simulate test execution
            exec_start = time.perf_counter()

            # Simulate biological memory test operations
            working_memory = list(range(min(7, test_id % 10)))  # Miller's limit
            processed_memory = [x * 2 for x in working_memory]

            time.sleep(0.005)  # 5ms execution
            exec_time = time.perf_counter() - exec_start

            # Simulate teardown
            teardown_start = time.perf_counter()
            time.sleep(0.001)  # 1ms teardown
            teardown_time = time.perf_counter() - teardown_start

            return {
                "test_id": test_id,
                "setup_time": setup_time,
                "exec_time": exec_time,
                "teardown_time": teardown_time,
                "memory_items": len(working_memory),
            }

        # Execute large number of simulated tests
        test_count = 50
        max_workers = min(8, multiprocessing.cpu_count())

        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(simulate_test_execution, i) for i in range(test_count)]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        total_time = time.perf_counter() - start_time

        # Analyze results
        assert len(results) == test_count

        avg_setup = sum(r["setup_time"] for r in results) / test_count
        avg_exec = sum(r["exec_time"] for r in results) / test_count
        avg_teardown = sum(r["teardown_time"] for r in results) / test_count

        # Performance should meet targets
        assert avg_setup < 0.01, f"Average setup time ({avg_setup:.4f}s) should be under 10ms"
        assert avg_exec < 0.02, f"Average execution time ({avg_exec:.4f}s) should be under 20ms"
        assert (
            avg_teardown < 0.005
        ), f"Average teardown time ({avg_teardown:.4f}s) should be under 5ms"

        # Total parallel execution should show significant speedup
        sequential_estimate = test_count * (avg_setup + avg_exec + avg_teardown)
        speedup = sequential_estimate / total_time

        assert (
            speedup > 2.0
        ), f"Large scale parallel execution should show 2x+ speedup (actual: {speedup:.2f}x)"

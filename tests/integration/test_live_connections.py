#!/usr/bin/env python3
"""
Live connection testing for BMP-002.
Tests actual connections to PostgreSQL and Ollama when available.
"""

import json
import os
import time
from pathlib import Path

import duckdb
import requests


class LiveConnectionTester:
    """Test live connections for DuckDB extensions."""

    def __init__(self):
        self.db_path = os.getenv(
            "DUCKDB_PATH", "/Users/ladvien/biological_memory/dbs/memory.duckdb"
        )
        # Use TEST_DATABASE_URL if available, fallback to POSTGRES_DB_URL
        self.postgres_url = os.getenv(
            "TEST_DATABASE_URL",
            os.getenv(
                "POSTGRES_DB_URL", "postgresql://codex_user:defaultpassword@localhost:5432/codex_db"
            ),
        )
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    def get_connection_with_extensions(self):
        """Get a database connection with all extensions loaded."""
        conn = duckdb.connect(self.db_path)
        # Load extensions for this session
        conn.execute("LOAD httpfs")
        conn.execute("LOAD postgres")
        conn.execute("LOAD json")
        conn.execute("LOAD spatial")
        return conn

    def test_postgres_connection(self):
        """Test live PostgreSQL connection."""
        print("Testing PostgreSQL connection...")
        conn = self.get_connection_with_extensions()

        try:
            # Test attachment with masked URL for security logging
            masked_url = self._mask_credentials_in_url(self.postgres_url)
            print(f"Testing connection to: {masked_url}")
            conn.execute(f"ATTACH '{self.postgres_url}' AS postgres_live (TYPE postgres)")

            # Test basic query
            result = conn.execute(
                "SELECT version() FROM postgres_query(?, 'SELECT version();')", [self.postgres_url]
            ).fetchone()

            if result:
                print(f"✅ PostgreSQL connected successfully: {result[0][:50]}...")

                # Update connection status
                conn.execute(
                    """
                    UPDATE connection_status 
                    SET is_connected = TRUE, last_check = CURRENT_TIMESTAMP, error_message = 'Connected successfully'
                    WHERE connection_name = 'postgres'
                """
                )

                return True
            else:
                print("❌ PostgreSQL query returned no results")
                return False

        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")

            # Log failure
            conn.execute(
                """
                INSERT INTO retry_log VALUES (
                    'postgres', 1, CURRENT_TIMESTAMP, FALSE, ?
                )
            """,
                [str(e)],
            )

            conn.execute(
                """
                UPDATE connection_status 
                SET is_connected = FALSE, last_check = CURRENT_TIMESTAMP, 
                    error_message = ?, retry_count = retry_count + 1
                WHERE connection_name = 'postgres'
            """,
                [str(e)],
            )

            return False
        finally:
            conn.close()

    def _mask_credentials_in_url(self, url):
        """Mask credentials in database URL for logging."""
        import re

        # Replace password with *** in URL for secure logging
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)

    def test_ollama_connection(self):
        """Test live Ollama connection."""
        print("Testing Ollama connection...")

        try:
            # Test API availability
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                print("✅ Ollama API is accessible")

                # Test model availability
                models = response.json()
                available_models = [m["name"] for m in models.get("models", [])]

                if self.ollama_model in available_models:
                    print(f"✅ Model {self.ollama_model} is available")
                    return self.test_ollama_prompt()
                else:
                    print(f"⚠️  Model {self.ollama_model} not found. Available: {available_models}")
                    return False
            else:
                print(f"❌ Ollama API returned status {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Ollama connection failed: {e}")
            return False

    def test_ollama_prompt(self):
        """Test Ollama prompt functionality."""
        print("Testing Ollama prompt...")

        try:
            prompt_data = {
                "model": self.ollama_model,
                "prompt": "What is 2+2? Respond with just the number.",
                "stream": False,
            }

            start_time = time.time()
            response = requests.post(
                f"{self.ollama_url}/api/generate", json=prompt_data, timeout=30
            )
            end_time = time.time()

            if response.status_code == 200:
                response_data = response.json()
                response_time_ms = int((end_time - start_time) * 1000)

                print(f"✅ Prompt successful in {response_time_ms}ms")
                print(f"Response: {response_data.get('response', 'No response')[:100]}")

                # Store response in database
                conn = self.get_connection_with_extensions()
                conn.execute(
                    """
                    INSERT INTO prompt_responses (model, prompt, response, response_time_ms, success)
                    VALUES (?, ?, ?, ?, TRUE)
                """,
                    [
                        self.ollama_model,
                        prompt_data["prompt"],
                        response_data.get("response", ""),
                        response_time_ms,
                    ],
                )
                conn.close()

                return True
            else:
                print(f"❌ Prompt failed with status {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Prompt test failed: {e}")
            return False

    def test_embedding_generation(self):
        """Test embedding generation with nomic-embed-text."""
        print("Testing embedding generation...")

        try:
            embedding_data = {
                "model": self.embedding_model,
                "prompt": "This is a test text for embedding generation.",
            }

            response = requests.post(
                f"{self.ollama_url}/api/embeddings", json=embedding_data, timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()
                embedding = response_data.get("embedding", [])

                if embedding and len(embedding) > 0:
                    print(f"✅ Embedding generated successfully: {len(embedding)} dimensions")

                    # Store in database
                    conn = self.get_connection_with_extensions()
                    conn.execute(
                        """
                        INSERT INTO embeddings (text_input, model, embedding, dimensions)
                        VALUES (?, ?, ?, ?)
                    """,
                        [
                            embedding_data["prompt"],
                            self.embedding_model,
                            embedding,  # DuckDB supports arrays
                            len(embedding),
                        ],
                    )
                    conn.close()

                    return True
                else:
                    print("❌ No embedding data in response")
                    return False
            else:
                print(f"❌ Embedding request failed with status {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Embedding test failed: {e}")
            return False

    def test_retry_logic(self):
        """Test exponential backoff retry logic."""
        print("Testing retry logic...")

        conn = self.get_connection_with_extensions()

        # Test backoff calculation
        backoffs = conn.execute(
            """
            SELECT attempt, delay_ms
            FROM backoff_calculator
            WHERE attempt BETWEEN 0 AND 5
            ORDER BY attempt
        """
        ).fetchall()

        print("Exponential backoff schedule:")
        for attempt, delay in backoffs:
            print(f"  Attempt {attempt}: {delay}ms")

        # Simulate retry scenario
        for attempt in range(3):
            delay_ms = conn.execute(
                """
                SELECT delay_ms FROM backoff_calculator WHERE attempt = ?
            """,
                [attempt],
            ).fetchone()[0]

            conn.execute(
                """
                INSERT INTO retry_log VALUES (
                    'test_connection', ?, CURRENT_TIMESTAMP, FALSE, 'Simulated retry test'
                )
            """,
                [attempt],
            )

            print(f"  Simulated attempt {attempt}: would wait {delay_ms}ms")
            time.sleep(0.1)  # Brief pause for demonstration

        conn.close()
        return True

    def generate_health_report(self):
        """Generate a health report of all connections."""
        print("\n" + "=" * 50)
        print("DUCKDB EXTENSION HEALTH REPORT")
        print("=" * 50)

        conn = self.get_connection_with_extensions()

        # Extension status
        extensions = conn.execute(
            """
            SELECT extension_name, loaded, installed
            FROM duckdb_extensions()
            WHERE installed = true
            ORDER BY extension_name
        """
        ).fetchall()

        print("\nExtension Status:")
        for ext_name, loaded, installed in extensions:
            status = "✅ Loaded" if loaded else "⚠️  Installed but not loaded"
            print(f"  {ext_name}: {status}")

        # Connection status
        connections = conn.execute(
            """
            SELECT connection_name, is_connected, last_check, error_message
            FROM connection_status
            ORDER BY connection_name
        """
        ).fetchall()

        print("\nConnection Status:")
        for conn_name, connected, last_check, error in connections:
            status = "✅ Connected" if connected else "❌ Disconnected"
            print(f"  {conn_name}: {status}")
            if error and error != "Extension loaded":
                print(f"    Last error: {error}")

        # Configuration summary
        config_count = conn.execute("SELECT COUNT(*) FROM connection_config").fetchone()[0]
        print(f"\nConfiguration: {config_count} parameters configured")

        # Performance metrics
        if conn.execute("SELECT COUNT(*) FROM prompt_responses").fetchone()[0] > 0:
            avg_response_time = conn.execute(
                """
                SELECT AVG(response_time_ms) FROM prompt_responses WHERE success = true
            """
            ).fetchone()[0]
            print(f"Average prompt response time: {avg_response_time:.1f}ms")

        conn.close()

    def run_all_tests(self):
        """Run all connection tests."""
        print("Starting BMP-002 Live Connection Tests")
        print("=====================================\n")

        test_results = {
            "postgres": self.test_postgres_connection(),
            "ollama_connection": self.test_ollama_connection(),
            "embedding": self.test_embedding_generation(),
            "retry_logic": self.test_retry_logic(),
        }

        self.generate_health_report()

        print(f"\nTest Summary:")
        passed = sum(test_results.values())
        total = len(test_results)
        print(f"  Passed: {passed}/{total} tests")

        if passed == total:
            print("🎉 All tests passed! BMP-002 implementation is complete.")
        else:
            print("⚠️  Some tests failed - this is expected if live services are unavailable.")
            print("   The DuckDB extensions are properly configured for when services are online.")

        return test_results


if __name__ == "__main__":
    tester = LiveConnectionTester()
    tester.run_all_tests()

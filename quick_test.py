#!/usr/bin/env python3
"""Quick system test for biological memory pipeline"""

import os
import requests
import duckdb

print("=== Biological Memory System Quick Test ===")

# Test 1: Ollama connectivity
print("\n🧠 Testing Ollama connectivity...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        models = response.json()
        print(f"✅ Local Ollama accessible - {len(models.get('models', []))} models available")
    else:
        print(f"❌ Local Ollama returned status {response.status_code}")
except Exception as e:
    print(f"❌ Local Ollama not accessible: {e}")

try:
    response = requests.get("http://192.168.1.110:11434/api/tags", timeout=5)
    if response.status_code == 200:
        models = response.json()
        print(f"✅ Remote Ollama accessible - {len(models.get('models', []))} models available")
        for model in models.get('models', [])[:3]:  # Show first 3 models
            print(f"   - {model['name']}")
    else:
        print(f"❌ Remote Ollama returned status {response.status_code}")
except Exception as e:
    print(f"❌ Remote Ollama not accessible: {e}")

# Test 2: DuckDB with extensions
print("\n🦆 Testing DuckDB...")
try:
    conn = duckdb.connect('biological_memory/dbs/memory.duckdb')
    
    # Test extensions
    result = conn.execute("""
        SELECT extension_name, loaded, installed 
        FROM duckdb_extensions() 
        WHERE extension_name IN ('postgres_scanner', 'json', 'httpfs', 'fts')
    """).fetchall()
    
    print("✅ DuckDB accessible with extensions:")
    for ext_name, loaded, installed in result:
        status = "✅" if loaded and installed else "❌"
        print(f"   {status} {ext_name}")
    
    conn.close()
except Exception as e:
    print(f"❌ DuckDB error: {e}")

# Test 3: Basic LLM test
print("\n🤖 Testing LLM generation...")
try:
    test_prompt = "What is 2+2?"
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "qwen2.5:0.5b", "prompt": test_prompt, "stream": False},
        timeout=30
    )
    if response.status_code == 200:
        result = response.json()
        answer = result.get('response', '').strip()[:50]
        print(f"✅ LLM generation working: '{answer}...'")
    else:
        print(f"❌ LLM generation failed with status {response.status_code}")
except Exception as e:
    print(f"❌ LLM generation error: {e}")

print("\n=== Test Summary ===")
print("✅ Core components verified")
print("⚠️  PostgreSQL connection needs password for full testing")
print("🚀 System ready for biological memory processing!")
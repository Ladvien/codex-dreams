#!/bin/bash

# Test script for biological memory system
# Load environment and test components

set -e
echo "=== Biological Memory System Test ==="
echo "Date: $(date)"
echo ""

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | xargs)
    echo "✅ Environment loaded"
else 
    echo "❌ .env file not found"
    exit 1
fi

echo "🔧 Environment Variables:"
echo "  - POSTGRES_HOST: ${POSTGRES_HOST:-not set}"
echo "  - POSTGRES_DB: ${POSTGRES_DB:-not set}"
echo "  - POSTGRES_USER: ${POSTGRES_USER:-not set}"
echo "  - OLLAMA_URL: ${OLLAMA_URL:-not set}"
echo "  - EMBEDDING_MODEL: ${EMBEDDING_MODEL:-not set}"
echo ""

# Test Ollama connection
echo "🧠 Testing Ollama LLM Server..."
if curl -s "$OLLAMA_URL/api/tags" > /dev/null; then
    echo "✅ Ollama server accessible at $OLLAMA_URL"
else
    echo "❌ Ollama server not accessible at $OLLAMA_URL"
fi
echo ""

# Test DuckDB
echo "🦆 Testing DuckDB..."
cd biological_memory
if duckdb dbs/memory.duckdb -c "SELECT 'DuckDB working' as status;"; then
    echo "✅ DuckDB accessible"
else
    echo "❌ DuckDB not accessible"
    exit 1
fi
echo ""

# Test dbt
echo "📊 Testing dbt configuration..."
if dbt debug --quiet; then
    echo "✅ dbt configuration valid"
else
    echo "❌ dbt configuration invalid"
    exit 1
fi

echo ""
echo "=== Test Complete ==="
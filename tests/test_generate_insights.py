"""
Tests for generate_insights.py module
"""
import pytest
from unittest.mock import patch, MagicMock, call
import json
import uuid
from datetime import datetime

# Import the functions to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.generate_insights import call_ollama, extract_tags, generate_insight, process_memories


class TestOllamaIntegration:
    """Test Ollama API integration"""
    
    @patch('src.generate_insights.requests.post')
    def test_call_ollama_success(self, mock_post):
        """Test successful Ollama API call"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Test insight'}
        mock_post.return_value = mock_response
        
        result = call_ollama('Test prompt')
        
        assert result == 'Test insight'
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'http://localhost:11434/api/generate' in call_args[0][0]
        assert call_args[1]['json']['prompt'] == 'Test prompt'
    
    @patch('src.generate_insights.requests.post')
    def test_call_ollama_error(self, mock_post):
        """Test Ollama API error handling"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        result = call_ollama('Test prompt')
        
        assert result == ""
    
    @patch('src.generate_insights.requests.post')
    def test_call_ollama_exception(self, mock_post):
        """Test Ollama API exception handling"""
        mock_post.side_effect = Exception("Connection error")
        
        result = call_ollama('Test prompt')
        
        assert result == ""


class TestTagExtraction:
    """Test tag extraction functionality"""
    
    @patch('src.generate_insights.call_ollama')
    def test_extract_tags_success(self, mock_ollama):
        """Test successful tag extraction"""
        mock_ollama.return_value = "memory, test, processing, data, analysis"
        
        tags = extract_tags("Test memory content")
        
        assert len(tags) == 5
        assert 'memory' in tags
        assert 'test' in tags
        assert all(isinstance(tag, str) for tag in tags)
    
    @patch('src.generate_insights.call_ollama')
    def test_extract_tags_empty_response(self, mock_ollama):
        """Test tag extraction with empty response"""
        mock_ollama.return_value = ""
        
        tags = extract_tags("Test memory content")
        
        assert tags == []
    
    @patch('src.generate_insights.call_ollama')
    def test_extract_tags_filters_invalid(self, mock_ollama):
        """Test tag extraction filters invalid tags"""
        mock_ollama.return_value = "good-tag, , very-long-tag-that-exceeds-limit, @invalid, valid"
        
        tags = extract_tags("Test memory content")
        
        assert 'good-tag' in tags
        assert 'valid' in tags
        assert len(tags) <= 5
        assert all(len(tag) < 20 for tag in tags)


class TestInsightGeneration:
    """Test insight generation functionality"""
    
    @patch('src.generate_insights.call_ollama')
    @patch('src.generate_insights.extract_tags')
    def test_generate_insight_basic(self, mock_tags, mock_ollama):
        """Test basic insight generation"""
        mock_ollama.return_value = "This is a test insight about the memory"
        mock_tags.return_value = ['test', 'memory']
        
        insight = generate_insight("Test memory content")
        
        assert insight['content'] == "This is a test insight about the memory"
        assert insight['type'] == 'pattern'
        assert insight['tags'] == ['test', 'memory']
        assert insight['confidence'] == 0.7
    
    @patch('src.generate_insights.call_ollama')
    @patch('src.generate_insights.extract_tags')
    def test_generate_insight_with_related(self, mock_tags, mock_ollama):
        """Test insight generation with related memories"""
        mock_ollama.return_value = "Connected memory pattern detected"
        mock_tags.return_value = ['connection', 'pattern']
        
        related = [str(uuid.uuid4()), str(uuid.uuid4())]
        insight = generate_insight("Test memory", related)
        
        assert insight['type'] == 'connection'
        assert 'Connected memory pattern' in insight['content']
    
    @patch('src.generate_insights.call_ollama')
    @patch('src.generate_insights.extract_tags')
    def test_generate_insight_fallback(self, mock_tags, mock_ollama):
        """Test insight generation fallback when LLM fails"""
        mock_ollama.return_value = ""  # Empty response
        mock_tags.return_value = []
        
        insight = generate_insight("Test memory content that is longer than usual")
        
        assert insight['content'].startswith("Memory recorded about:")
        assert insight['type'] == 'pattern'
        assert insight['tags'] == []


class TestDatabaseOperations:
    """Test database operation mocking"""
    
    @patch('src.generate_insights.psycopg2.connect')
    @patch('src.generate_insights.duckdb.connect')
    def test_database_connections(self, mock_duckdb, mock_pg):
        """Test that database connections are established"""
        # Setup mocks
        mock_duck_conn = MagicMock()
        mock_duck_conn.execute.return_value.fetchdf.return_value = MagicMock(iterrows=lambda: [])
        mock_duckdb.return_value = mock_duck_conn
        
        mock_pg_conn = MagicMock()
        mock_pg_cursor = MagicMock()
        mock_pg_cursor.fetchone.return_value = ('codex', 'public')
        mock_pg_conn.cursor.return_value = mock_pg_cursor
        mock_pg.return_value = mock_pg_conn
        
        # Run the function
        process_memories()
        
        # Verify connections were made
        mock_duckdb.assert_called_once()
        mock_pg.assert_called_once()
        mock_pg_conn.commit.assert_called_once()
        mock_pg_conn.close.assert_called_once()


class TestFullPipeline:
    """Test the full pipeline integration"""
    
    @patch('src.generate_insights.psycopg2.connect')
    @patch('src.generate_insights.duckdb.connect')
    @patch('src.generate_insights.call_ollama')
    @patch('src.generate_insights.extract_tags')
    def test_process_memories_integration(self, mock_tags, mock_ollama, mock_duckdb, mock_pg):
        """Test full memory processing pipeline"""
        # Setup memory data
        import pandas as pd
        test_memory_id = uuid.uuid4()
        test_df = pd.DataFrame({
            'memory_id': [test_memory_id],
            'content': ['Test memory content'],
            'suggested_tags': [['test', 'memory']],
            'related_memories': [None],
            'connection_count': [0]
        })
        
        # Setup DuckDB mock
        mock_duck_conn = MagicMock()
        mock_duck_conn.execute.return_value.fetchdf.return_value = test_df
        mock_duckdb.return_value = mock_duck_conn
        
        # Setup PostgreSQL mock
        mock_pg_conn = MagicMock()
        mock_pg_cursor = MagicMock()
        mock_pg_cursor.fetchone.return_value = ('codex', 'public')
        mock_pg_conn.cursor.return_value = mock_pg_cursor
        mock_pg.return_value = mock_pg_conn
        
        # Setup Ollama mocks
        mock_ollama.return_value = "Test insight"
        mock_tags.return_value = ['test', 'tag']
        
        # Run the pipeline
        process_memories()
        
        # Verify insight was inserted
        mock_pg_cursor.execute.assert_called()
        insert_call = [c for c in mock_pg_cursor.execute.call_args_list 
                      if 'INSERT INTO public.insights' in str(c)]
        assert len(insert_call) > 0
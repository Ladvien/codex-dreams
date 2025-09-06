"""
Test dbt model tags for biological orchestration compliance.

This module validates that all dbt models have proper tags for biological
rhythm orchestration and memory stage classification.
"""

import pytest
import yaml
from pathlib import Path


class TestModelTags:
    """Test suite for dbt model tag validation."""
    
    @classmethod
    def setup_class(cls):
        """Load dbt configuration for model tag testing."""
        project_path = Path("/Users/ladvien/codex-dreams/biological_memory/dbt_project.yml")
        
        if not project_path.exists():
            pytest.skip("dbt_project.yml not found")
        
        with open(project_path, 'r') as f:
            config = yaml.safe_load(f)
        
        cls.models = config.get('models', {}).get('biological_memory', {})
    
    def test_working_memory_tags(self):
        """Test working memory models have correct orchestration tags."""
        wm_config = self.models.get('working_memory', {})
        tags = wm_config.get('+tags', [])
        
        # Required biological orchestration tags
        assert 'biological' in tags, "Working memory should have 'biological' tag"
        assert 'working_memory' in tags, "Working memory should have 'working_memory' tag"
        assert 'continuous' in tags, "Working memory should have 'continuous' tag for orchestration"
        
        # Performance tags
        assert 'performance_critical' in tags or 'rapid' in tags, (
            "Working memory should have performance tags"
        )
        
        # Real-time processing tag
        assert 'real_time' in tags or 'rapid' in tags, (
            "Working memory should have real-time processing tags"
        )
    
    def test_short_term_memory_tags(self):
        """Test short-term memory models have correct orchestration tags."""
        stm_config = self.models.get('short_term_memory', {})
        tags = stm_config.get('+tags', [])
        
        # Required biological orchestration tags
        assert 'biological' in tags, "Short-term memory should have 'biological' tag"
        assert 'short_term_memory' in tags or 'short_term' in tags, (
            "Short-term memory should have memory stage tag"
        )
        assert 'short_term' in tags, "Short-term memory should have 'short_term' orchestration tag"
        
        # Processing frequency tag
        assert 'rapid' in tags, "Short-term memory should have 'rapid' processing tag"
    
    def test_consolidation_tags(self):
        """Test consolidation models have correct orchestration tags."""
        cons_config = self.models.get('consolidation', {})
        tags = cons_config.get('+tags', [])
        
        # Required biological orchestration tags
        assert 'biological' in tags, "Consolidation should have 'biological' tag"
        assert 'consolidation' in tags, "Consolidation should have 'consolidation' orchestration tag"
        
        # Timing tags for biological rhythms
        assert 'hourly' in tags or 'deep_sleep' in tags, (
            "Consolidation should have rhythm timing tags"
        )
    
    def test_long_term_memory_tags(self):
        """Test long-term memory models have correct orchestration tags."""
        ltm_config = self.models.get('long_term_memory', {})
        tags = ltm_config.get('+tags', [])
        
        # Required biological orchestration tags  
        assert 'biological' in tags, "Long-term memory should have 'biological' tag"
        assert 'long_term_memory' in tags or 'long_term' in tags, (
            "Long-term memory should have memory stage tag"
        )
        assert 'long_term' in tags, "Long-term memory should have 'long_term' orchestration tag"
        
        # Biological rhythm tags
        assert 'deep_sleep' in tags or 'weekly' in tags, (
            "Long-term memory should have consolidation rhythm tags"
        )
    
    def test_semantic_network_tags(self):
        """Test semantic network models have appropriate tags."""
        semantic_config = self.models.get('semantic', {})
        tags = semantic_config.get('+tags', [])
        
        # Required tags
        assert 'biological' in tags, "Semantic networks should have 'biological' tag"
        assert 'semantic' in tags, "Semantic networks should have 'semantic' tag"
        assert 'long_term' in tags, "Semantic networks should have 'long_term' tag"
    
    def test_tag_consistency_across_aliases(self):
        """Test that model aliases have consistent tags."""
        # Check short_term vs short_term_memory
        stm_config = self.models.get('short_term_memory', {})
        st_config = self.models.get('short_term', {})
        
        if st_config:  # If alias exists
            stm_tags = set(stm_config.get('+tags', []))
            st_tags = set(st_config.get('+tags', []))
            
            # Should have overlapping biological tags
            biological_overlap = stm_tags.intersection(st_tags)
            assert 'biological' in biological_overlap, (
                "Alias models should have consistent 'biological' tag"
            )
        
        # Check long_term vs long_term_memory  
        ltm_config = self.models.get('long_term_memory', {})
        lt_config = self.models.get('long_term', {})
        
        if lt_config:  # If alias exists
            ltm_tags = set(ltm_config.get('+tags', []))
            lt_tags = set(lt_config.get('+tags', []))
            
            biological_overlap = ltm_tags.intersection(lt_tags)
            assert 'biological' in biological_overlap, (
                "Alias models should have consistent 'biological' tag"
            )


class TestOrchestrationTags:
    """Test orchestration-specific tag requirements."""
    
    @classmethod
    def setup_class(cls):
        """Load configuration for orchestration tag testing."""
        project_path = Path("/Users/ladvien/codex-dreams/biological_memory/dbt_project.yml")
        with open(project_path, 'r') as f:
            config = yaml.safe_load(f)
        cls.models = config.get('models', {}).get('biological_memory', {})
    
    def test_continuous_processing_tags(self):
        """Test models tagged for continuous processing."""
        continuous_models = []
        
        for model_name, model_config in self.models.items():
            tags = model_config.get('+tags', [])
            if 'continuous' in tags:
                continuous_models.append(model_name)
        
        # Working memory should definitely be continuous
        assert 'working_memory' in continuous_models, (
            "Working memory must be tagged for continuous processing"
        )
        
        # Should have at least one continuous model
        assert len(continuous_models) >= 1, (
            "Should have at least one model tagged for continuous processing"
        )
    
    def test_short_term_processing_tags(self):
        """Test models tagged for short-term processing (every 5-20 minutes)."""
        short_term_models = []
        
        for model_name, model_config in self.models.items():
            tags = model_config.get('+tags', [])
            if 'short_term' in tags or 'rapid' in tags:
                short_term_models.append(model_name)
        
        # Should have short-term memory models
        assert any('short_term' in name for name in short_term_models), (
            "Should have short-term memory models tagged appropriately"
        )
        
        assert len(short_term_models) >= 1, (
            "Should have at least one model for short-term processing"
        )
    
    def test_consolidation_processing_tags(self):
        """Test models tagged for consolidation processing (hourly)."""
        consolidation_models = []
        
        for model_name, model_config in self.models.items():
            tags = model_config.get('+tags', [])
            if 'consolidation' in tags or 'hourly' in tags:
                consolidation_models.append(model_name)
        
        # Should have consolidation models
        assert 'consolidation' in consolidation_models or any('consolidation' in name for name in consolidation_models), (
            "Should have consolidation models tagged appropriately"
        )
        
        assert len(consolidation_models) >= 1, (
            "Should have at least one model for consolidation processing"
        )
    
    def test_long_term_processing_tags(self):
        """Test models tagged for long-term processing (daily/weekly)."""
        long_term_models = []
        
        for model_name, model_config in self.models.items():
            tags = model_config.get('+tags', [])
            if 'long_term' in tags or 'deep_sleep' in tags or 'weekly' in tags:
                long_term_models.append(model_name)
        
        # Should have long-term memory models
        assert any('long_term' in name for name in long_term_models), (
            "Should have long-term memory models tagged appropriately"
        )
        
        assert len(long_term_models) >= 1, (
            "Should have at least one model for long-term processing"
        )
    
    def test_all_required_orchestration_tags_present(self):
        """Test that all required orchestration tags are represented."""
        required_orchestration_tags = ['continuous', 'short_term', 'consolidation', 'long_term']
        
        all_tags = set()
        for model_config in self.models.values():
            tags = model_config.get('+tags', [])
            all_tags.update(tags)
        
        for required_tag in required_orchestration_tags:
            assert required_tag in all_tags, (
                f"Required orchestration tag '{required_tag}' not found in any model. "
                f"Available tags: {sorted(all_tags)}"
            )


class TestBiologicalMemoryStageTagging:
    """Test that memory stage models are properly tagged for biological accuracy."""
    
    @classmethod
    def setup_class(cls):
        """Load configuration for memory stage testing."""
        project_path = Path("/Users/ladvien/codex-dreams/biological_memory/dbt_project.yml")
        with open(project_path, 'r') as f:
            config = yaml.safe_load(f)
        cls.models = config.get('models', {}).get('biological_memory', {})
    
    def test_memory_hierarchy_tagging(self):
        """Test that memory stages are tagged to represent the biological hierarchy."""
        # Working Memory -> Short-Term -> Consolidation -> Long-Term
        hierarchy_stages = [
            ('working_memory', 'continuous'),
            ('short_term_memory', 'short_term'),
            ('consolidation', 'consolidation'), 
            ('long_term_memory', 'long_term')
        ]
        
        for model_name, expected_stage_tag in hierarchy_stages:
            if model_name in self.models:
                tags = self.models[model_name].get('+tags', [])
                assert expected_stage_tag in tags, (
                    f"Model '{model_name}' should have stage tag '{expected_stage_tag}' "
                    f"for biological memory hierarchy. Current tags: {tags}"
                )
    
    def test_performance_critical_tagging(self):
        """Test that performance-critical models are properly tagged."""
        performance_critical_models = ['working_memory']
        
        for model_name in performance_critical_models:
            if model_name in self.models:
                tags = self.models[model_name].get('+tags', [])
                has_performance_tag = any(
                    tag in tags for tag in ['performance_critical', 'real_time', 'rapid']
                )
                assert has_performance_tag, (
                    f"Performance-critical model '{model_name}' should have performance tags. "
                    f"Current tags: {tags}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
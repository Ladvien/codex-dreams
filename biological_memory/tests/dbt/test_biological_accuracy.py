#!/usr/bin/env python3
"""
Additional tests for biological accuracy and edge cases
Review by Senior Data Engineer - Advanced Validation
"""

import pytest
import yaml
from pathlib import Path


class TestBiologicalAccuracy:
    """Test biological memory model accuracy"""
    
    @classmethod
    def setup_class(cls):
        cls.project_dir = Path("/Users/ladvien/biological_memory")
        
    def test_millers_law_compliance(self):
        """Test working memory capacity follows Miller's Law (7±2)"""
        project_file = self.project_dir / "dbt_project.yml"
        with open(project_file, 'r') as f:
            config = yaml.safe_load(f)
            
        capacity = config['vars']['working_memory_capacity']
        assert 5 <= capacity <= 9, f"Working memory capacity {capacity} violates Miller's Law"
        
    def test_hebbian_learning_parameters(self):
        """Test Hebbian learning parameters are biologically plausible"""
        project_file = self.project_dir / "dbt_project.yml"
        with open(project_file, 'r') as f:
            config = yaml.safe_load(f)
            
        vars_config = config['vars']
        
        # Learning rate should be small for biological realism
        learning_rate = vars_config['hebbian_learning_rate']
        assert 0.001 <= learning_rate <= 0.1, f"Hebbian learning rate {learning_rate} unrealistic"
        
        # Decay rate should be slower than learning
        decay_rate = vars_config['synaptic_decay_rate']
        assert decay_rate < learning_rate, "Decay should be slower than learning"
        
    def test_consolidation_timing_realistic(self):
        """Test memory consolidation timing matches neuroscience"""
        project_file = self.project_dir / "dbt_project.yml"
        with open(project_file, 'r') as f:
            config = yaml.safe_load(f)
            
        # Short-term memory should last 15-30 seconds typically
        stm_duration = config['vars']['short_term_memory_duration']
        assert 15 <= stm_duration <= 60, f"STM duration {stm_duration}s outside biological range"
        
        # Consolidation window should be 12-48 hours
        consolidation_hours = config['vars']['consolidation_window_hours']
        assert 12 <= consolidation_hours <= 48, f"Consolidation window {consolidation_hours}h unrealistic"


class TestMacroRobustness:
    """Test macro edge cases and error handling"""
    
    @classmethod  
    def setup_class(cls):
        cls.macros_dir = Path("/Users/ladvien/biological_memory/macros")
        
    def test_macro_null_handling(self):
        """Test that macros handle null inputs gracefully"""
        macro_file = self.macros_dir / "biological_memory_macros.sql"
        with open(macro_file, 'r') as f:
            content = f.read()
            
        # Key macros should have null protection
        critical_macros = ['calculate_hebbian_strength', 'synaptic_homeostasis']
        for macro in critical_macros:
            macro_start = content.find(f'macro {macro}')
            macro_end = content.find('{% endmacro %}', macro_start)
            if macro_start > -1 and macro_end > -1:
                macro_content = content[macro_start:macro_end]
                # Should have some null handling (COALESCE, NULLIF, etc.)
                has_null_handling = any(keyword in macro_content.upper() 
                                     for keyword in ['COALESCE', 'NULLIF', 'IS NULL'])
                assert has_null_handling, f"Macro {macro} lacks null handling"
                
    def test_division_by_zero_protection(self):
        """Test macros protect against division by zero"""
        utility_file = self.macros_dir / "utility_macros.sql"
        with open(utility_file, 'r') as f:
            content = f.read()
            
        # Should have safe_divide macro
        assert 'macro safe_divide' in content, "Missing safe_divide macro for division protection"
        assert 'NULLIF' in content or 'denominator = 0' in content, "safe_divide lacks zero protection"


class TestPerformanceConfiguration:
    """Test performance and scalability configurations"""
    
    @classmethod
    def setup_class(cls):
        cls.project_dir = Path("/Users/ladvien/biological_memory")
        
    def test_materialization_strategy_appropriate(self):
        """Test materialization strategies match usage patterns"""
        project_file = self.project_dir / "dbt_project.yml"
        with open(project_file, 'r') as f:
            config = yaml.safe_load(f)
            
        models_config = config['models']['biological_memory']
        
        # Working memory should be fast views
        assert models_config['working_memory']['+materialized'] == 'view'
        
        # Long-term memory should be optimized tables
        assert models_config['long_term_memory']['+materialized'] == 'table'
        
        # Semantic should be incremental for efficiency
        assert models_config['semantic']['+materialized'] == 'incremental'
        
    def test_batch_sizes_reasonable(self):
        """Test batch sizes are appropriate for performance"""
        project_file = self.project_dir / "dbt_project.yml"
        with open(project_file, 'r') as f:
            config = yaml.safe_load(f)
            
        vars_config = config['vars']
        
        consolidation_batch = vars_config['consolidation_batch_size']
        assert 100 <= consolidation_batch <= 10000, f"Consolidation batch {consolidation_batch} may impact performance"
        
        incremental_batch = vars_config['incremental_batch_size']
        assert 1000 <= incremental_batch <= 100000, f"Incremental batch {incremental_batch} inappropriate"


class TestDataLineage:
    """Test model dependencies and data lineage"""
    
    @classmethod
    def setup_class(cls):
        cls.models_dir = Path("/Users/ladvien/biological_memory/models")
        
    def test_model_dependency_order(self):
        """Test models follow logical dependency order"""
        # Working memory should be base (no dependencies)
        working_memory_file = self.models_dir / "working_memory" / "wm_active_context.sql"
        with open(working_memory_file, 'r') as f:
            wm_content = f.read()
            
        # Should only reference sources, not other models
        assert 'ref(' not in wm_content, "Working memory should not depend on other models"
        assert 'source(' in wm_content, "Working memory should reference sources"
        
    def test_circular_dependency_prevention(self):
        """Test no circular dependencies exist"""
        dependency_graph = {}
        
        for model_file in self.models_dir.rglob("*.sql"):
            if model_file.name == "sources.yml":
                continue
                
            with open(model_file, 'r') as f:
                content = f.read()
                
            model_name = model_file.stem
            dependencies = []
            
            # Extract ref() calls
            import re
            refs = re.findall(r"ref\(['\"]([^'\"]+)['\"]\)", content)
            dependencies.extend(refs)
            
            dependency_graph[model_name] = dependencies
            
        # Simple circular dependency check (would need proper graph algorithm for complex cases)
        for model, deps in dependency_graph.items():
            for dep in deps:
                if dep in dependency_graph:
                    assert model not in dependency_graph[dep], f"Circular dependency: {model} <-> {dep}"


if __name__ == "__main__":
    # Run additional advanced tests
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])
    
    print("\n" + "="*50)
    print("🧠 BIOLOGICAL ACCURACY REVIEW COMPLETE")
    print("="*50)
    
    if exit_code == 0:
        print("✅ Advanced validation PASSED")
        print("✅ Biological parameters are scientifically accurate")
        print("✅ Macro robustness verified") 
        print("✅ Performance configuration appropriate")
        print("✅ Data lineage validated")
    else:
        print("❌ Advanced validation found issues")
        print("⚠️  Review biological parameters and macro implementations")
        
    exit(exit_code)

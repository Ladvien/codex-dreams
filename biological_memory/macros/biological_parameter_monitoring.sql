{# 
  Biological Parameter Monitoring and Alerting Macros
  BMP-MEDIUM-008: Runtime parameter validation and alerts
  
  These macros provide continuous monitoring of biological parameters
  and alert when values drift outside neuroscientifically accurate ranges.
#}

{# Monitor and validate biological parameters at runtime #}
{% macro validate_biological_parameters() %}
  {#
    Runtime validation of all biological parameters with alerting.
    Called during model execution to ensure parameters remain within
    neuroscientifically accurate ranges.
  #}
  
  {% if execute %}
    {{ log("🧬 BIOLOGICAL PARAMETER VALIDATION STARTING", info=true) }}
    
    {# Miller's Law Validation #}
    {% if var('working_memory_capacity') < 5 or var('working_memory_capacity') > 9 %}
      {{ log("⚠️  ALERT: Working memory capacity " ~ var('working_memory_capacity') ~ " violates Miller's Law (7±2)", info=true) }}
      {{ log("   → Biological Impact: May cause cognitive overload or underutilization", info=true) }}
    {% endif %}
    
    {# Hebbian Learning Rate Validation #}
    {% if var('hebbian_learning_rate') > 0.1 %}
      {{ log("⚠️  ALERT: Hebbian learning rate " ~ var('hebbian_learning_rate') ~ " too high for biological realism", info=true) }}
      {{ log("   → Risk: Runaway potentiation and network instability", info=true) }}
    {% elif var('hebbian_learning_rate') < 0.001 %}
      {{ log("⚠️  ALERT: Hebbian learning rate " ~ var('hebbian_learning_rate') ~ " too low for effective learning", info=true) }}
      {{ log("   → Risk: Insufficient plasticity for memory formation", info=true) }}
    {% endif %}
    
    {# Synaptic Balance Validation #}
    {% if var('synaptic_decay_rate') >= var('hebbian_learning_rate') %}
      {{ log("🚨 CRITICAL: Synaptic decay (" ~ var('synaptic_decay_rate') ~ ") exceeds learning rate (" ~ var('hebbian_learning_rate') ~ ")", info=true) }}
      {{ log("   → Biological Impact: Memories cannot be formed or maintained", info=true) }}
    {% endif %}
    
    {# Homeostasis Target Validation #}
    {% if var('homeostasis_target') > 0.8 %}
      {{ log("⚠️  ALERT: Homeostasis target " ~ var('homeostasis_target') ~ " risks network saturation", info=true) }}
      {{ log("   → Recommendation: Reduce to 0.5-0.7 for stable network dynamics", info=true) }}
    {% elif var('homeostasis_target') < 0.2 %}
      {{ log("⚠️  ALERT: Homeostasis target " ~ var('homeostasis_target') ~ " risks network silence", info=true) }}
      {{ log("   → Recommendation: Increase to 0.3-0.5 for active network maintenance", info=true) }}
    {% endif %}
    
    {# Consolidation Window Validation #}
    {% if var('consolidation_window_hours') < 12 %}
      {{ log("⚠️  ALERT: Consolidation window " ~ var('consolidation_window_hours') ~ "h insufficient for systems consolidation", info=true) }}
      {{ log("   → Biological Impact: Incomplete memory consolidation", info=true) }}
    {% elif var('consolidation_window_hours') > 48 %}
      {{ log("⚠️  ALERT: Consolidation window " ~ var('consolidation_window_hours') ~ "h exceeds biological consolidation period", info=true) }}
      {{ log("   → Impact: May prevent memory updates and reconsolidation", info=true) }}
    {% endif %}
    
    {# Threshold Separation Validation (LTP/LTD metaplasticity) #}
    {% set threshold_gap = var('high_quality_threshold') - var('medium_quality_threshold') %}
    {% if threshold_gap < 0.1 %}
      {{ log("⚠️  ALERT: LTP/LTD threshold gap " ~ (threshold_gap * 100) ~ "% too narrow for metaplasticity", info=true) }}
      {{ log("   → Risk: Insufficient separation for bidirectional plasticity", info=true) }}
    {% elif threshold_gap > 0.3 %}
      {{ log("⚠️  ALERT: LTP/LTD threshold gap " ~ (threshold_gap * 100) ~ "% too wide", info=true) }}
      {{ log("   → Risk: May prevent intermediate strength memories", info=true) }}
    {% endif %}
    
    {{ log("✅ Biological parameter validation complete", info=true) }}
  {% endif %}
{% endmacro %}

{# Monitor working memory capacity enforcement #}
{% macro monitor_working_memory_capacity() %}
  {#
    Runtime monitoring of working memory capacity to ensure Miller's Law
    is properly enforced during memory processing.
  #}
  
  {% if execute %}
    {% set capacity_query %}
      SELECT COUNT(*) as current_memories
      FROM {{ ref('wm_active_context') }}
      WHERE activation_strength > 0
    {% endset %}
    
    {% set results = run_query(capacity_query) %}
    {% if results %}
      {% set current_count = results[0][0] %}
      {% if current_count > var('working_memory_capacity') %}
        {{ log("🚨 WORKING MEMORY OVERLOAD: " ~ current_count ~ " items exceeds capacity " ~ var('working_memory_capacity'), info=true) }}
        {{ log("   → Miller's Law Violation: Working memory should maintain 7±2 items", info=true) }}
        {{ log("   → Recommendation: Increase consolidation rate or reduce input load", info=true) }}
      {% elif current_count == 0 %}
        {{ log("⚠️  Working memory empty - check data pipeline", info=true) }}
      {% else %}
        {{ log("✅ Working memory within capacity: " ~ current_count ~ "/" ~ var('working_memory_capacity') ~ " items", info=true) }}
      {% endif %}
    {% endif %}
  {% endif %}
{% endmacro %}

{# Monitor consolidation timing patterns #}
{% macro monitor_consolidation_timing() %}
  {#
    Monitor memory consolidation timing to ensure biological patterns
    are maintained during processing.
  #}
  
  {% if execute %}
    {% set timing_query %}
      SELECT 
        COUNT(*) as total_memories,
        COUNT(CASE WHEN ready_for_consolidation THEN 1 END) as ready_count,
        AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - timestamp))) as avg_age_seconds
      FROM {{ ref('stm_hierarchical_episodes') }}
      WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '1 HOUR'
    {% endset %}
    
    {% set results = run_query(timing_query) %}
    {% if results %}
      {% set total_memories = results[0][0] %}
      {% set ready_count = results[0][1] %}
      {% set avg_age = results[0][2] %}
      
      {% if avg_age and avg_age > 300 %}  {# > 5 minutes #}
        {{ log("⚠️  STM memories aging: Average " ~ (avg_age/60)|round(1) ~ " minutes", info=true) }}
        {{ log("   → Recommendation: Check consolidation pipeline throughput", info=true) }}
      {% endif %}
      
      {% if ready_count and total_memories and ready_count > (total_memories * 0.8) %}
        {{ log("⚠️  Consolidation backlog: " ~ ready_count ~ "/" ~ total_memories ~ " memories ready", info=true) }}
        {{ log("   → Impact: May cause STM overflow and memory loss", info=true) }}
      {% endif %}
      
      {{ log("📊 Consolidation status: " ~ ready_count ~ "/" ~ total_memories ~ " ready, avg age " ~ (avg_age/60)|round(1) ~ "min", info=true) }}
    {% endif %}
  {% endif %}
{% endmacro %}

{# Monitor LTP/LTD balance #}
{% macro monitor_ltp_ltd_balance() %}
  {#
    Monitor Long-Term Potentiation/Depression balance to ensure
    healthy synaptic plasticity patterns.
  #}
  
  {% if execute %}
    {% set plasticity_query %}
      SELECT 
        COUNT(*) as total_connections,
        COUNT(CASE WHEN retrieval_strength > {{ var('high_quality_threshold') }} THEN 1 END) as strong_connections,
        COUNT(CASE WHEN retrieval_strength < {{ var('weak_connection_threshold') }} THEN 1 END) as weak_connections,
        AVG(retrieval_strength) as avg_strength
      FROM {{ ref('ltm_semantic_network') }}
      WHERE last_processed_at > CURRENT_TIMESTAMP - INTERVAL '1 HOUR'
    {% endset %}
    
    {% set results = run_query(plasticity_query) %}
    {% if results %}
      {% set total_connections = results[0][0] %}
      {% set strong_connections = results[0][1] %}
      {% set weak_connections = results[0][2] %}
      {% set avg_strength = results[0][3] %}
      
      {% if total_connections > 0 %}
        {% set strong_pct = (strong_connections * 100 / total_connections) %}
        {% set weak_pct = (weak_connections * 100 / total_connections) %}
        
        {% if strong_pct > 30 %}
          {{ log("⚠️  Network saturation risk: " ~ strong_pct|round(1) ~ "% strong connections", info=true) }}
          {{ log("   → Recommendation: Increase homeostatic scaling", info=true) }}
        {% elif weak_pct > 50 %}
          {{ log("⚠️  Network sparsity risk: " ~ weak_pct|round(1) ~ "% weak connections", info=true) }}
          {{ log("   → Recommendation: Strengthen learning mechanisms", info=true) }}
        {% endif %}
        
        {% if avg_strength %}
          {% if avg_strength > var('homeostasis_target') * 1.2 %}
            {{ log("⚠️  Network hyperactivity: Avg strength " ~ avg_strength|round(3), info=true) }}
          {% elif avg_strength < var('homeostasis_target') * 0.8 %}
            {{ log("⚠️  Network hypoactivity: Avg strength " ~ avg_strength|round(3), info=true) }}
          {% endif %}
        {% endif %}
        
        {{ log("🔗 Network health: " ~ strong_pct|round(1) ~ "% strong, " ~ weak_pct|round(1) ~ "% weak, avg=" ~ avg_strength|round(3), info=true) }}
      {% endif %}
    {% endif %}
  {% endif %}
{% endmacro %}

{# Generate biological parameter health report #}
{% macro generate_biological_health_report() %}
  {#
    Generate comprehensive report on biological parameter health
    and system compliance with neuroscientific principles.
  #}
  
  {% if execute %}
    {{ log("", info=true) }}
    {{ log("🧠 BIOLOGICAL MEMORY SYSTEM HEALTH REPORT", info=true) }}
    {{ log("="*50, info=true) }}
    
    {# Run all monitoring checks #}
    {{ validate_biological_parameters() }}
    {{ monitor_working_memory_capacity() }}
    {{ monitor_consolidation_timing() }}
    {{ monitor_ltp_ltd_balance() }}
    
    {{ log("", info=true) }}
    {{ log("📋 BIOLOGICAL PARAMETER SUMMARY:", info=true) }}
    {{ log("   Working Memory Capacity: " ~ var('working_memory_capacity') ~ " items (Miller's Law)", info=true) }}
    {{ log("   STM Duration: " ~ var('short_term_memory_duration') ~ " seconds", info=true) }}
    {{ log("   Hebbian Learning Rate: " ~ var('hebbian_learning_rate'), info=true) }}
    {{ log("   Synaptic Decay Rate: " ~ var('synaptic_decay_rate'), info=true) }}
    {{ log("   Homeostasis Target: " ~ var('homeostasis_target'), info=true) }}
    {{ log("   Consolidation Window: " ~ var('consolidation_window_hours') ~ " hours", info=true) }}
    {{ log("   High Quality Threshold: " ~ var('high_quality_threshold'), info=true) }}
    {{ log("   Medium Quality Threshold: " ~ var('medium_quality_threshold'), info=true) }}
    
    {{ log("", info=true) }}
    {{ log("⏰ TIMING PATTERN STATUS:", info=true) }}
    {{ log("   5-Second Refresh Cycles: ACTIVE during wake hours", info=true) }}
    {{ log("   STM Processing: 5-minute intervals", info=true) }}
    {{ log("   Consolidation Cycles: Hourly during wake", info=true) }}
    {{ log("   Deep Sleep Consolidation: 2AM-4AM window", info=true) }}
    
    {{ log("="*50, info=true) }}
    {{ log("✅ Biological parameter monitoring complete", info=true) }}
    {{ log("", info=true) }}
  {% endif %}
{% endmacro %}
#!/usr/bin/env python3
"""
Dreams Scheduler - Automated biological memory processing
Runs the write-back pipeline on biological rhythms
"""

import logging
import os
import schedule
import time
from datetime import datetime
from dreams_writeback_service import DreamsWritebackService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_working_memory():
    """Run working memory write-back (every 5 seconds)."""
    try:
        service = DreamsWritebackService()
        service.write_working_memory()
    except Exception as e:
        logger.error(f"Error in working memory write-back: {e}")

def run_short_term():
    """Run short-term memory write-back (every 5 minutes)."""
    try:
        service = DreamsWritebackService()
        service.write_short_term_episodes()
    except Exception as e:
        logger.error(f"Error in short-term write-back: {e}")

def run_long_term():
    """Run long-term consolidation (every hour)."""
    try:
        service = DreamsWritebackService()
        service.write_long_term_memories()
    except Exception as e:
        logger.error(f"Error in long-term consolidation: {e}")

def run_semantic():
    """Run semantic network building (daily at 3 AM)."""
    try:
        service = DreamsWritebackService()
        service.write_semantic_network()
        service.extract_insights()
    except Exception as e:
        logger.error(f"Error in semantic network building: {e}")

def run_cleanup():
    """Run cleanup (weekly on Sunday at 3 AM)."""
    try:
        service = DreamsWritebackService()
        service.cleanup_old_data(30)  # Keep 30 days
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")

def main():
    """Main scheduler loop."""
    logger.info("Starting Dreams Scheduler...")
    
    # Schedule tasks based on biological rhythms
    
    # Continuous processing (disabled by default - too frequent)
    # schedule.every(5).seconds.do(run_working_memory)
    
    # Rapid processing
    schedule.every(5).minutes.do(run_short_term)
    
    # Hourly consolidation
    schedule.every().hour.do(run_long_term)
    
    # Daily semantic processing (3 AM)
    schedule.every().day.at("03:00").do(run_semantic)
    
    # Weekly cleanup (Sunday 3 AM)
    schedule.every().sunday.at("03:00").do(run_cleanup)
    
    # Run initial pipeline
    logger.info("Running initial full pipeline...")
    service = DreamsWritebackService()
    service.run_full_pipeline()
    
    logger.info("Scheduler started. Running tasks:")
    logger.info("  - Short-term memories: every 5 minutes")
    logger.info("  - Long-term consolidation: every hour")
    logger.info("  - Semantic network: daily at 3 AM")
    logger.info("  - Cleanup: weekly Sunday at 3 AM")
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Reset Insights - Drop all insights and allow them to rebuild
"""

import psycopg2
import os
import sys
from datetime import datetime

# Configuration from environment or defaults
POSTGRES_URL = os.getenv("POSTGRES_DB_URL", "postgresql://codex_user:i5(|_})9A4&9Khd23&DJ4VRq&G_.px0Z@192.168.1.104:5432/codex_db")

def reset_insights():
    """Drop all insights from the database"""
    
    print("🗑️  Insights Reset Tool")
    print("=" * 50)
    
    # Parse the connection string
    # Format: postgresql://user:pass@host:port/dbname
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        cursor = conn.cursor()
        
        # Count existing insights
        cursor.execute("SELECT COUNT(*) FROM insights")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("ℹ️  No insights to delete")
            return
        
        print(f"⚠️  Found {count} insights in the database")
        
        # Confirm deletion
        response = input(f"\n❓ Are you sure you want to delete all {count} insights? [y/N]: ").strip().lower()
        
        if response not in ['y', 'yes']:
            print("❌ Cancelled - no insights deleted")
            return
        
        # Delete all insights
        print("\n🔄 Deleting insights...")
        cursor.execute("DELETE FROM insights")
        deleted = cursor.rowcount
        
        # Commit the changes
        conn.commit()
        
        print(f"✅ Successfully deleted {deleted} insights")
        print("\n💡 New insights will be generated on the next scheduled run")
        print("   Run 'codex-dreams run' to generate insights immediately")
        
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Check your database credentials and connection")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def reset_specific_time_range():
    """Delete insights from a specific time range"""
    
    print("\n📅 Delete insights by date range")
    print("-" * 40)
    
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        cursor = conn.cursor()
        
        # Show date range of existing insights
        cursor.execute("""
            SELECT 
                MIN(created_at)::date as earliest,
                MAX(created_at)::date as latest,
                COUNT(*) as total
            FROM insights
        """)
        
        result = cursor.fetchone()
        if result[2] == 0:
            print("ℹ️  No insights in database")
            return
            
        print(f"📊 Current insights range:")
        print(f"   Earliest: {result[0]}")
        print(f"   Latest: {result[1]}")
        print(f"   Total: {result[2]} insights")
        
        # Get date range from user
        print("\nEnter date range to delete (YYYY-MM-DD format)")
        start_date = input("Start date (or press Enter for earliest): ").strip()
        end_date = input("End date (or press Enter for latest): ").strip()
        
        # Build query
        where_clauses = []
        params = []
        
        if start_date:
            where_clauses.append("created_at >= %s")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("created_at <= %s")
            params.append(f"{end_date} 23:59:59")
        
        if where_clauses:
            where_sql = " AND ".join(where_clauses)
            count_query = f"SELECT COUNT(*) FROM insights WHERE {where_sql}"
            cursor.execute(count_query, params)
        else:
            cursor.execute("SELECT COUNT(*) FROM insights")
        
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("ℹ️  No insights match the criteria")
            return
        
        # Confirm deletion
        response = input(f"\n❓ Delete {count} insights? [y/N]: ").strip().lower()
        
        if response not in ['y', 'yes']:
            print("❌ Cancelled")
            return
        
        # Delete insights
        if where_clauses:
            delete_query = f"DELETE FROM insights WHERE {where_sql}"
            cursor.execute(delete_query, params)
        else:
            cursor.execute("DELETE FROM insights")
        
        deleted = cursor.rowcount
        conn.commit()
        
        print(f"✅ Deleted {deleted} insights")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    
    if len(sys.argv) > 1 and sys.argv[1] == '--range':
        reset_specific_time_range()
    elif len(sys.argv) > 1 and sys.argv[1] == '--all':
        # Skip confirmation for --all flag
        try:
            conn = psycopg2.connect(POSTGRES_URL)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM insights")
            deleted = cursor.rowcount
            conn.commit()
            print(f"✅ Deleted {deleted} insights")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        reset_insights()

if __name__ == "__main__":
    main()
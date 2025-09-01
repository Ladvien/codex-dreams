-- Test Data Setup for Codex Dreams Test Suite
-- This script populates the test database with sample data

-- Clear existing test data
DELETE FROM public.memories WHERE content LIKE 'Test memory%';

-- Insert test memories with various timestamps and metadata
INSERT INTO public.memories (content, timestamp, metadata) VALUES
('Test memory 1: Morning routine completed', NOW() - INTERVAL '1 hour', '{"category": "routine", "importance": 0.3}'::jsonb),
('Test memory 2: Important meeting with team', NOW() - INTERVAL '2 hours', '{"category": "work", "importance": 0.8}'::jsonb),
('Test memory 3: Lunch with colleagues', NOW() - INTERVAL '3 hours', '{"category": "social", "importance": 0.5}'::jsonb),
('Test memory 4: Code review session', NOW() - INTERVAL '4 hours', '{"category": "work", "importance": 0.7}'::jsonb),
('Test memory 5: Evening walk in the park', NOW() - INTERVAL '5 hours', '{"category": "personal", "importance": 0.4}'::jsonb),
('Test memory 6: Read interesting article', NOW() - INTERVAL '6 hours', '{"category": "learning", "importance": 0.6}'::jsonb),
('Test memory 7: Fixed critical bug', NOW() - INTERVAL '7 hours', '{"category": "work", "importance": 0.9}'::jsonb),
('Test memory 8: Called family', NOW() - INTERVAL '8 hours', '{"category": "personal", "importance": 0.7}'::jsonb),
('Test memory 9: Completed project milestone', NOW() - INTERVAL '24 hours', '{"category": "work", "importance": 0.9}'::jsonb),
('Test memory 10: Weekend trip planning', NOW() - INTERVAL '48 hours', '{"category": "personal", "importance": 0.6}'::jsonb);

-- Add some older memories for consolidation testing
INSERT INTO public.memories (content, timestamp, metadata) VALUES
('Old memory 1: Project kickoff', NOW() - INTERVAL '7 days', '{"category": "work", "importance": 0.8}'::jsonb),
('Old memory 2: Birthday celebration', NOW() - INTERVAL '14 days', '{"category": "personal", "importance": 0.9}'::jsonb),
('Old memory 3: Learning new framework', NOW() - INTERVAL '30 days', '{"category": "learning", "importance": 0.7}'::jsonb);

-- Display count of inserted test memories
SELECT COUNT(*) as test_memory_count FROM public.memories WHERE content LIKE '%memory%';
-- Migration to add supabase_images column to slidesqlmodel table
-- Run this in Supabase SQL Editor

-- Add the supabase_images column to the existing slidesqlmodel table
ALTER TABLE slide_agent.slidesqlmodel 
ADD COLUMN supabase_images JSON;

-- Add a comment to describe the column
COMMENT ON COLUMN slide_agent.slidesqlmodel.supabase_images IS 'Array of Supabase storage URLs for slide images';

-- Optional: Update existing rows to have empty array if needed
-- UPDATE slide_agent.slidesqlmodel SET supabase_images = '[]'::json WHERE supabase_images IS NULL; 
-- backend/migrations/init_db.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE section_type AS ENUM (
    'inciting_incident',
    'plot_point_1',
    'midpoint',
    'plot_point_2',
    'climax',
    'resolution'
);

CREATE TYPE checklist_status AS ENUM (
    'pending',
    'complete'
);

CREATE TYPE framework AS ENUM (
    'three_act',
    'save_the_cat',
    'hero_journey'
);

-- Create tables
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    framework framework DEFAULT 'three_act',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type section_type NOT NULL,
    user_notes TEXT DEFAULT '',
    ai_suggestions JSONB DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE checklist_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    answer TEXT DEFAULT '',
    status checklist_status DEFAULT 'pending',
    "order" INTEGER DEFAULT 0
);

-- Create indexes
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_sections_project ON sections(project_id);
CREATE INDEX idx_checklist_section ON checklist_items(section_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sections_updated_at
    BEFORE UPDATE ON sections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

// frontend/src/types/index.ts

export enum SectionType {
  INCITING_INCIDENT = "inciting_incident",
  PLOT_POINT_1 = "plot_point_1",
  MIDPOINT = "midpoint",
  PLOT_POINT_2 = "plot_point_2",
  CLIMAX = "climax",
  RESOLUTION = "resolution"
}

export enum ChecklistStatus {
  PENDING = "pending",
  COMPLETE = "complete"
}

export enum Framework {
  THREE_ACT = "three_act",
  SAVE_THE_CAT = "save_the_cat",
  HERO_JOURNEY = "hero_journey"
}

export interface ChecklistItem {
  id: string;
  section_id: string;
  prompt: string;
  answer: string;
  status: ChecklistStatus;
  order: number;
}

export interface AIFeedback {
  issues: string[];
  suggestions: string[];
}

export interface Section {
  id: string;
  project_id: string;
  type: SectionType;
  user_notes: string;
  ai_suggestions: AIFeedback;
  updated_at: string | null;
  checklist_items: ChecklistItem[];
}

export interface Project {
  id: string;
  owner_id: string;
  title: string;
  framework: Framework;
  created_at: string;
  updated_at: string | null;
  sections: Section[];
}

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface ReviewRequest {
  section_id: string;
  text: string;
  framework: Framework;
}

export interface ReviewResponse {
  issues: string[];
  suggestions: string[];
}

// ============================================================
// Book types
// ============================================================

export type BookStatus = 'pending' | 'extracting' | 'analyzing' | 'embedding' | 'completed' | 'failed';

export interface Book {
  id: string;
  title: string;
  author: string | null;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  status: BookStatus;
  processing_step: string | null;
  total_chunks: number;
  total_concepts: number;
  processing_error: string | null;
  uploaded_at: string;
  processed_at: string | null;
}

export interface Concept {
  id: string;
  name: string;
  definition: string;
  chapter_source: string | null;
  page_range: string | null;
  examples: Array<{ film: string; description: string; page?: string | null }>;
  actionable_questions: string[];
  section_relevance: Record<string, number>;
  tags: string[];
}

// ============================================================
// Agent types
// ============================================================

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  personality: string | null;
  color: string;
  icon: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  book_count: number;
}

// ============================================================
// Chat types
// ============================================================

export interface ChatSession {
  id: string;
  agent_id: string;
  project_id: string;
  title: string | null;
  agent_name?: string;
  agent_color?: string;
  agent_icon?: string;
  created_at: string;
  updated_at: string | null;
}

export interface BookReference {
  concept_name?: string;
  book_title?: string;
  chapter?: string;
  page?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_type: 'chat' | 'review' | 'system';
  book_references: BookReference[];
  created_at: string;
}

// ============================================================
// Multi-agent review types
// ============================================================

export interface AgentReviewResult {
  agent_id: string;
  agent_name: string;
  agent_color: string;
  agent_icon: string;
  issues: string[];
  suggestions: string[];
  book_references: BookReference[];
  status: 'completed' | 'error';
  error?: string;
}

// Re-export template types
export * from './template';
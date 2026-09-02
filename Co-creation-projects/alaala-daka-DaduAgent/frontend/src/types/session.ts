export interface Session {
  session_id: string;
  title?: string;
  message_count: number;
  user_message_count?: number;
  created_at?: string;
  updated_at?: string;
  size_bytes?: number;
  size_human?: string;
}

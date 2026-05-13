export interface VoiceProfile {
  id: string;
  name: string;
  description: string | null;
  provider: 'tts' | 'openvoice';
  voice_key: string;
  has_reference_audio: boolean;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface VoiceSetting {
  voice_profile_id: string | null;
  auto_play: boolean;
  voice_profile: VoiceProfile | null;
}

import client, { unwrap } from './client';
import type { ApiResponse, VoiceProfile } from '@zhiqu/shared';

export function listVoiceProfiles(includeInactive = true) {
  return unwrap<VoiceProfile[]>(
    client.get('/admin/voice/profiles', { params: { include_inactive: includeInactive } }),
  );
}

export function createVoiceProfile(data: {
  name: string;
  description?: string;
  provider: 'tts' | 'openvoice';
  voice_key?: string;
  is_active: boolean;
  sort_order: number;
  file?: File;
}) {
  const form = new FormData();
  form.append('name', data.name);
  if (data.description) form.append('description', data.description);
  form.append('provider', data.provider);
  if (data.voice_key) form.append('voice_key', data.voice_key);
  form.append('is_active', String(data.is_active));
  form.append('sort_order', String(data.sort_order));
  if (data.file) form.append('file', data.file);
  return unwrap<VoiceProfile>(
    client.post('/admin/voice/profiles', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
    }),
  );
}

export async function transcribeAudio(file: Blob): Promise<{ text: string }> {
  const form = new FormData();
  form.append('file', file, 'recording.webm');
  const res = await client.post<ApiResponse<{ text: string }>>('/admin/voice/stt', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  });
  return res.data.data;
}

export async function synthesizeSpeech(text: string, voiceProfileId?: string | null): Promise<Blob> {
  const res = await client.post('/admin/voice/tts', {
    text,
    voice_profile_id: voiceProfileId || null,
  }, {
    responseType: 'blob',
    timeout: 120_000,
  });
  return res.data as Blob;
}

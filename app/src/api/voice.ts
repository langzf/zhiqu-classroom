import type { ApiResponse, VoiceProfile, VoiceSetting } from '@zhiqu/shared';
import { client, unwrap } from './client';

export function listVoiceProfiles() {
  return client.get<ApiResponse<VoiceProfile[]>>('/app/voice/profiles').then(unwrap);
}

export function getVoiceSetting() {
  return client.get<ApiResponse<VoiceSetting>>('/app/voice/settings').then(unwrap);
}

export function updateVoiceSetting(data: { voice_profile_id?: string | null; auto_play: boolean }) {
  return client.patch<ApiResponse<VoiceSetting>>('/app/voice/settings', data).then(unwrap);
}

export async function transcribeAudio(file: Blob): Promise<{ text: string }> {
  const form = new FormData();
  form.append('file', file, 'recording.webm');
  const res = await client.post<ApiResponse<{ text: string }>>('/app/voice/stt', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  });
  return res.data.data;
}

export async function synthesizeSpeech(text: string, voiceProfileId?: string | null): Promise<Blob> {
  const res = await client.post('/app/voice/tts', {
    text,
    voice_profile_id: voiceProfileId || null,
  }, {
    responseType: 'blob',
    timeout: 120_000,
  });
  return res.data as Blob;
}

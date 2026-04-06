import { client, unwrap } from './client';

// ── Types ──

export interface ModelProvider {
  id: string;
  name: string;
  provider_type: string;
  base_url: string | null;
  api_key_masked: string;
  extra_config: Record<string, unknown> | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ModelConfig {
  id: string;
  provider_id: string;
  model_name: string;
  display_name: string;
  capabilities: string[];
  default_params: Record<string, unknown>;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ModelConfigDetail extends ModelConfig {
  provider: ModelProvider | null;
}

export interface SceneModelBinding {
  id: string;
  scene_key: string;
  scene_label: string | null;
  model_config_id: string;
  param_overrides: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Providers ──

export function listProviders(params: { page?: number; size?: number } = {}) {
  return client.get('/admin/model-config/providers', { params }).then(unwrap) as Promise<{ items: ModelProvider[]; total: number }>;
}

export function getProvider(id: string) {
  return client.get(`/admin/model-config/providers/${id}`).then(unwrap) as Promise<ModelProvider>;
}

export function createProvider(data: {
  name: string;
  provider_type: string;
  base_url?: string;
  api_key: string;
  extra_config?: Record<string, unknown>;
  is_active?: boolean;
  sort_order?: number;
}) {
  return client.post('/admin/model-config/providers', data).then(unwrap) as Promise<ModelProvider>;
}

export function updateProvider(id: string, data: Partial<{
  name: string;
  provider_type: string;
  base_url: string;
  api_key: string;
  extra_config: Record<string, unknown>;
  is_active: boolean;
  sort_order: number;
}>) {
  return client.put(`/admin/model-config/providers/${id}`, data).then(unwrap) as Promise<ModelProvider>;
}

export function deleteProvider(id: string) {
  return client.delete(`/admin/model-config/providers/${id}`);
}

// ── Model Configs ──

export function listModelConfigs(params: { provider_id?: string; page?: number; size?: number } = {}) {
  return client.get('/admin/model-config/configs', { params }).then(unwrap) as Promise<{ items: ModelConfig[]; total: number }>;
}

export function getModelConfig(id: string) {
  return client.get(`/admin/model-config/configs/${id}`).then(unwrap) as Promise<ModelConfigDetail>;
}

export function createModelConfig(data: {
  provider_id: string;
  model_name: string;
  display_name: string;
  capabilities?: string[];
  default_params?: Record<string, unknown>;
  is_active?: boolean;
  sort_order?: number;
}) {
  return client.post('/admin/model-config/configs', data).then(unwrap) as Promise<ModelConfig>;
}

export function updateModelConfig(id: string, data: Partial<{
  provider_id: string;
  model_name: string;
  display_name: string;
  capabilities: string[];
  default_params: Record<string, unknown>;
  is_active: boolean;
  sort_order: number;
}>) {
  return client.put(`/admin/model-config/configs/${id}`, data).then(unwrap) as Promise<ModelConfig>;
}

export function deleteModelConfig(id: string) {
  return client.delete(`/admin/model-config/configs/${id}`);
}

// ── Scene Bindings ──

export function listSceneBindings(params: { page?: number; size?: number } = {}) {
  return client.get('/admin/model-config/bindings', { params }).then(unwrap) as Promise<{ items: SceneModelBinding[]; total: number }>;
}

export function createSceneBinding(data: {
  scene_key: string;
  scene_label?: string;
  model_config_id: string;
  param_overrides?: Record<string, unknown>;
  is_active?: boolean;
}) {
  return client.post('/admin/model-config/bindings', data).then(unwrap) as Promise<SceneModelBinding>;
}

export function updateSceneBinding(sceneKey: string, data: Partial<{
  scene_label: string;
  model_config_id: string;
  param_overrides: Record<string, unknown>;
  is_active: boolean;
}>) {
  return client.put(`/admin/model-config/bindings/${sceneKey}`, data).then(unwrap) as Promise<SceneModelBinding>;
}

export function deleteSceneBinding(sceneKey: string) {
  return client.delete(`/admin/model-config/bindings/${sceneKey}`);
}

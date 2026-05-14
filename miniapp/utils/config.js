const API_BASE_URL = 'https://zqback.yueying.cloud/api/v1';
const TRACE_PLATFORM_URL = 'https://trace.yueying.cloud';
const TRACE_PROJECT_KEY = 'zhiqu-classroom';
const TRACE_SERVICE_NAME = 'zhiqu-miniapp';
const TRACE_ENABLED = true;

const STORAGE_KEYS = {
  token: 'zhiqu_token',
  refreshToken: 'zhiqu_refresh_token',
  user: 'zhiqu_user'
};

module.exports = {
  API_BASE_URL,
  TRACE_PLATFORM_URL,
  TRACE_PROJECT_KEY,
  TRACE_SERVICE_NAME,
  TRACE_ENABLED,
  STORAGE_KEYS
};

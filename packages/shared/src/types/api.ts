/** 标准 API 响应 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  request_id?: string;
}

/** 分页数据 */
export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** 分页响应 */
export type PaginatedResponse<T> = ApiResponse<PaginatedData<T>>;

/** API 错误 */
export interface ApiError {
  code: number;
  message: string;
  details?: Record<string, string[]>;
  request_id?: string;
}

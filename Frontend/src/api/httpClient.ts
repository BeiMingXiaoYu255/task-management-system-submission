/**
 * 统一 HTTP 请求客户端。
 *
 * 设计说明：
 * 1. 桌面模式（Tauri）通过原生命令获取后端地址（http://127.0.0.1:端口）；
 *    浏览器/局域网模式使用同源地址（后端同时托管前端静态资源）；
 * 2. 自动注入 Bearer token，401 时清除本地凭证并广播 tms:unauthorized 事件；
 * 3. 错误统一抛出 ApiError，携带后端返回的错误码与中文提示。
 */

/** token 在 localStorage 中的键名。 */
const TOKEN_STORAGE_KEY = 'tms.token'

/** 缓存的 API 基地址（首次解析后复用）。 */
let cachedApiBaseUrl: string | null = null

/** 后端统一错误结构。 */
interface ErrorResponseBody {
  code?: string
  message?: string
  details?: unknown
}

/** 业务错误类型：页面捕获后展示 message。 */
export class ApiError extends Error {
  /** 机器可读错误码。 */
  readonly code: string
  /** HTTP 状态码。 */
  readonly status: number
  /** 附加明细。 */
  readonly details: unknown

  constructor(code: string, message: string, status: number, details: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

/** 请求参数定义。 */
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  query?: Record<string, unknown>
  headers?: Record<string, string>
}

/** 读取本地保存的 token。 */
export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

/** 保存或清除 token。 */
export function setStoredToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
  } catch {
    // 隐私模式等场景下 localStorage 不可用时静默忽略
  }
}

/** 解析 API 基地址（桌面模式向后端询问，浏览器模式同源）。 */
export async function resolveApiBaseUrl(): Promise<string> {
  if (cachedApiBaseUrl !== null) {
    return cachedApiBaseUrl
  }
  if (window.__TAURI_INTERNALS__) {
    try {
      const { invoke } = await import('@tauri-apps/api/core')
      const baseUrl = await invoke<string>('getApiBaseUrl')
      cachedApiBaseUrl = baseUrl.replace(/\/$/, '')
      return cachedApiBaseUrl
    } catch {
      cachedApiBaseUrl = 'http://127.0.0.1:8765'
      return cachedApiBaseUrl
    }
  }
  cachedApiBaseUrl = ''
  return cachedApiBaseUrl
}

/** 把查询对象拼成 URL 查询串，忽略空值。 */
function buildQueryString(query?: Record<string, unknown>): string {
  if (!query) {
    return ''
  }
  const searchParameters = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }
    searchParameters.append(key, String(value))
  })
  const queryString = searchParameters.toString()
  return queryString ? '?' + queryString : ''
}

/** 解析响应体：优先 JSON，空响应返回 null。 */
async function parseResponseBody(response: Response): Promise<unknown> {
  const responseText = await response.text()
  if (!responseText) {
    return null
  }
  try {
    return JSON.parse(responseText) as unknown
  } catch {
    return responseText
  }
}

/** 发起请求并返回类型化数据。 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = await resolveApiBaseUrl()
  const token = getStoredToken()
  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {}),
  }
  if (token) {
    requestHeaders.Authorization = 'Bearer ' + token
  }
  const fullUrl = baseUrl + '/api/v1' + path + buildQueryString(options.query)
  const response = await fetch(fullUrl, {
    method: options.method ?? 'GET',
    headers: requestHeaders,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  const responseBody = await parseResponseBody(response)
  if (!response.ok) {
    const errorBody = (responseBody ?? {}) as ErrorResponseBody
    const error = new ApiError(
      errorBody.code ?? 'REQUEST_FAILED',
      errorBody.message ?? 'Request failed. Please try again later.',
      response.status,
      errorBody.details ?? null,
    )
    if (response.status === 401) {
      setStoredToken(null)
      window.dispatchEvent(new CustomEvent('tms:unauthorized'))
    }
    throw error
  }
  return responseBody as T
}

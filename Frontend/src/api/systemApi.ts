/** 系统信息接口调用。 */

import { request } from './httpClient'

/** 系统基础信息。 */
export interface SystemInfo {
  appName: string
  version: string
  databaseType: string
  redisMode: string
}

/** 局域网访问信息。 */
export interface NetworkInfo {
  lanUrls: string[]
  port: number
  version: string
  hostname: string
}

/** 获取系统信息。 */
export function getSystemInfo(): Promise<SystemInfo> {
  return request<SystemInfo>('/system/info')
}

/** 获取局域网访问地址。 */
export function getNetworkInfo(): Promise<NetworkInfo> {
  return request<NetworkInfo>('/system/network')
}

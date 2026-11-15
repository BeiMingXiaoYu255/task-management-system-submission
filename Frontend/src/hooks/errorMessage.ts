/**
 * 错误文案提取工具。
 *
 * 页面捕获异常后统一调用本函数得到面向用户的中文提示：
 * 优先使用后端返回的 ApiError.message，其次使用标准 Error.message，
 * 最后回退到调用方提供的默认文案，避免把原始异常堆栈暴露给用户。
 */

import { ApiError } from '../api/httpClient'

/** 默认的通用失败提示文案。 */
const DEFAULT_ERROR_MESSAGE = 'Something went wrong. Please try again.'

/**
 * 从任意异常对象中提取可展示的中文错误提示。
 *
 * @param error 捕获到的异常
 * @param fallbackMessage 兜底提示文案
 * @returns 可直接展示给用户的提示文本
 */
export function getErrorMessage(error: unknown, fallbackMessage: string = DEFAULT_ERROR_MESSAGE): string {
  if (error instanceof ApiError) {
    return error.message || fallbackMessage
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  if (typeof error === 'string' && error.length > 0) {
    return error
  }
  return fallbackMessage
}

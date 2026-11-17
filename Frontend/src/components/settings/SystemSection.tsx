/**
 * 系统信息区块：展示版本、数据库、缓存等运行信息，
 * 以及局域网访问地址（支持一键复制）与便签小窗入口。
 */

import { useCallback, useEffect, useState } from 'react'

import { getNetworkInfo, getSystemInfo, type NetworkInfo, type SystemInfo } from '../../api/systemApi'
import { useToast } from '../../context/ToastContext'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'
import styles from './SystemSection.module.css'

/** 单条系统信息展示项。 */
interface SystemInfoRow {
  label: string
  value: string
}

/** 系统信息区块。 */
export default function SystemSection() {
  const { showToast } = useToast()
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [networkInfo, setNetworkInfo] = useState<NetworkInfo | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  /** 并行加载系统信息与局域网访问信息，互不阻塞。 */
  const loadSystemData = useCallback(async (): Promise<void> => {
    setLoading(true)
    try {
      const [loadedSystemInfo, loadedNetworkInfo] = await Promise.all([
        getSystemInfo().catch(() => null),
        getNetworkInfo().catch(() => null),
      ])
      setSystemInfo(loadedSystemInfo)
      setNetworkInfo(loadedNetworkInfo)
      if (loadedSystemInfo === null && loadedNetworkInfo === null) {
        showToast('Failed to load system information', 'error')
      }
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => {
    void loadSystemData()
  }, [loadSystemData])

  /** 复制文本到剪贴板并提示结果。 */
  const copyText = async (text: string): Promise<void> => {
    if (!navigator.clipboard) {
      showToast('Clipboard access is not available in this environment. Please copy the text manually.', 'info')
      return
    }
    try {
      await navigator.clipboard.writeText(text)
      showToast('Copied: ' + text, 'success')
    } catch {
      showToast('Copy failed. Please copy the text manually.', 'error')
    }
  }

  /** 打开便签待办小窗：桌面模式调用原生命令，浏览器模式打开新窗口。 */
  const openStickyWindow = async (): Promise<void> => {
    if (window.__TAURI_INTERNALS__) {
      try {
        const { invoke } = await import('@tauri-apps/api/core')
        await invoke('openStickyWindow')
        return
      } catch {
        // 原生命令不可用时降级为浏览器窗口
      }
    }
    window.open('/sticky', 'sticky', 'width=380,height=620')
  }

  /** 组装系统信息展示行。 */
  const systemInfoRows: SystemInfoRow[] =
    systemInfo === null
      ? []
      : [
          { label: 'App Name', value: systemInfo.appName },
          { label: 'Version', value: systemInfo.version },
          { label: 'Database Type', value: systemInfo.databaseType },
          { label: 'Cache Mode', value: systemInfo.redisMode },
        ]

  return (
    <div className={styles.systemLayout}>
      {loading ? (
        <div className={styles.loadingArea}>
          <Spinner />
          <span>Loading system information ...</span>
        </div>
      ) : (
        <>
          <section className={styles.infoBlock}>
            <h3 className={styles.blockTitle}>Runtime Information</h3>
            {systemInfoRows.length === 0 ? (
              <p className={styles.emptyText}>System information is currently unavailable.</p>
            ) : (
              <dl className={styles.infoGrid}>
                {systemInfoRows.map((infoRow) => (
                  <div key={infoRow.label} className={styles.infoItem}>
                    <dt className={styles.infoLabel}>{infoRow.label}</dt>
                    <dd className={styles.infoValue}>{infoRow.value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>

          <section className={styles.infoBlock}>
            <h3 className={styles.blockTitle}>LAN Access Addresses</h3>
            <p className={styles.blockDescription}>
              Phones or other computers on the same LAN can access this system at the addresses below.
            </p>
            {networkInfo === null || networkInfo.lanUrls.length === 0 ? (
              <p className={styles.emptyText}>No LAN addresses available.</p>
            ) : (
              <ul className={styles.addressList}>
                {networkInfo.lanUrls.map((lanUrl) => (
                  <li key={lanUrl} className={styles.addressRow}>
                    <span className={styles.addressText}>{lanUrl}</span>
                    <Button variant="secondary" size="small" onClick={() => void copyText(lanUrl)}>
                      Copy
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={styles.infoBlock}>
            <h3 className={styles.blockTitle}>Sticky Notes Window</h3>
            <p className={styles.blockDescription}>
              Open a minimal sticky to-do window for quick notes and task check-offs (recommended window size 380×620).
            </p>
            <div className={styles.actionRow}>
              <Button variant="secondary" onClick={() => void openStickyWindow()}>
                Open Sticky Window
              </Button>
              <Button variant="ghost" onClick={() => void loadSystemData()}>
                Refresh System Information
              </Button>
            </div>
          </section>
        </>
      )}
    </div>
  )
}

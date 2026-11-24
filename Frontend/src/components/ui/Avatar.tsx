/**
 * 头像：优先显示图片，加载失败或无图片时回退到姓名首字。
 */

import { useEffect, useState } from 'react'

import { getInitials } from '../../utils/displayUtils'
import styles from './Avatar.module.css'

/** 头像尺寸。 */
export type AvatarSize = 'small' | 'medium' | 'large'

/** 头像属性。 */
export interface AvatarProps {
  /** 姓名（用于回退显示首字与无障碍标签）。 */
  name: string
  /** 头像图片地址。 */
  src?: string | null
  /** 尺寸，默认 medium。 */
  size?: AvatarSize
  /** 额外样式类名。 */
  className?: string
}

/** 头像组件。 */
export function Avatar({ name, src, size = 'medium', className }: AvatarProps) {
  const [imageFailed, setImageFailed] = useState(false)

  /** 图片地址变化时重置失败状态，允许重新加载。 */
  useEffect(() => {
    setImageFailed(false)
  }, [src])

  const classNames = [styles.avatar, styles[size]]
  if (className) {
    classNames.push(className)
  }
  const showImage = Boolean(src) && !imageFailed
  return (
    <span className={classNames.join(' ')} title={name} aria-label={name}>
      {showImage ? (
        <img
          className={styles.image}
          src={src ?? ''}
          alt={name}
          onError={() => setImageFailed(true)}
        />
      ) : (
        <span className={styles.initials}>{getInitials(name)}</span>
      )}
    </span>
  )
}

export default Avatar

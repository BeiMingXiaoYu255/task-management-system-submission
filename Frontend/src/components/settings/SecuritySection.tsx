/**
 * 账号安全区块：修改密码与注销账号。
 *
 * 安全约定：
 * 1. 修改密码成功后旧 token 立即失效，因此统一退出登录并跳转登录页；
 * 2. 注销账号必须输入当前密码二次确认，确认弹窗中再次明示不可恢复。
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { changePassword } from '../../api/authApi'
import { deleteAccount } from '../../api/settingApi'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import Button from '../ui/Button'
import ConfirmDialog from '../ui/ConfirmDialog'
import Input from '../ui/Input'
import styles from './SecuritySection.module.css'

/** 修改密码表单错误集合。 */
interface PasswordFormErrors {
  oldPassword?: string
  newPassword?: string
  confirmPassword?: string
}

/** 新密码最小长度。 */
const MIN_PASSWORD_LENGTH = 6

/** 账号安全区块。 */
export default function SecuritySection() {
  const { logout } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const [oldPassword, setOldPassword] = useState<string>('')
  const [newPassword, setNewPassword] = useState<string>('')
  const [confirmPassword, setConfirmPassword] = useState<string>('')
  const [passwordErrors, setPasswordErrors] = useState<PasswordFormErrors>({})
  const [changingPassword, setChangingPassword] = useState<boolean>(false)

  const [deletePassword, setDeletePassword] = useState<string>('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState<boolean>(false)
  const [deleting, setDeleting] = useState<boolean>(false)

  /** 修改密码：前端校验后提交，成功后强制重新登录。 */
  const handleChangePassword = async (): Promise<void> => {
    const nextErrors: PasswordFormErrors = {}
    if (oldPassword.length === 0) {
      nextErrors.oldPassword = 'Enter your current password'
    }
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      nextErrors.newPassword = 'New password must be at least ' + MIN_PASSWORD_LENGTH + ' characters'
    }
    if (newPassword === oldPassword) {
      nextErrors.newPassword = 'New password must differ from the current password'
    }
    if (confirmPassword !== newPassword) {
      nextErrors.confirmPassword = 'Passwords do not match'
    }
    setPasswordErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }
    setChangingPassword(true)
    try {
      const responseMessage = await changePassword({ oldPassword, newPassword })
      showToast(responseMessage.message, 'success')
      await logout()
      navigate('/login', { replace: true })
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to change password', 'error')
    } finally {
      setChangingPassword(false)
    }
  }

  /** 打开注销确认弹窗；密码为空时先提示。 */
  const handleRequestDeleteAccount = (): void => {
    if (deletePassword.length === 0) {
      showToast('Enter your current password to delete your account', 'error')
      return
    }
    setDeleteDialogOpen(true)
  }

  /** 确认注销账号：成功后退出登录并跳转登录页。 */
  const handleConfirmDeleteAccount = async (): Promise<void> => {
    setDeleting(true)
    try {
      const responseMessage = await deleteAccount({ password: deletePassword })
      showToast(responseMessage.message, 'success')
      await logout()
      navigate('/login', { replace: true })
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to delete account', 'error')
      setDeleteDialogOpen(false)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className={styles.securityLayout}>
      <section className={styles.sectionBlock}>
        <h3 className={styles.sectionTitle}>Change Password</h3>
        <p className={styles.sectionDescription}>You will need to sign in again with your new password after changing it.</p>
        <div className={styles.formGrid}>
          <Input
            label="Current Password"
            type="password"
            value={oldPassword}
            onChange={(event) => setOldPassword(event.target.value)}
            placeholder="Enter your current password"
            error={passwordErrors.oldPassword}
          />
          <Input
            label="New Password"
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            placeholder="At least 6 characters"
            error={passwordErrors.newPassword}
          />
          <Input
            label="Confirm New Password"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            placeholder="Re-enter your new password"
            error={passwordErrors.confirmPassword}
          />
        </div>
        <div className={styles.actionRow}>
          <Button variant="primary" loading={changingPassword} onClick={() => void handleChangePassword()}>
            Change Password
          </Button>
        </div>
      </section>

      <section className={styles.dangerBlock}>
        <h3 className={styles.dangerTitle}>Delete Account</h3>
        <p className={styles.dangerDescription}>
          Deleting your account and personal data cannot be undone. Enter your current password to confirm.
        </p>
        <div className={styles.deleteRow}>
          <Input
            label="Current Password"
            type="password"
            value={deletePassword}
            onChange={(event) => setDeletePassword(event.target.value)}
            placeholder="Enter your current password"
          />
          <Button variant="danger" onClick={handleRequestDeleteAccount}>
            Delete Account
          </Button>
        </div>
      </section>

      <ConfirmDialog
        open={deleteDialogOpen}
        title="Confirm Account Deletion"
        description="Deleting your account and personal data cannot be undone. Continue?"
        confirmText="Delete Account"
        danger
        loading={deleting}
        onConfirm={() => void handleConfirmDeleteAccount()}
        onCancel={() => setDeleteDialogOpen(false)}
      />
    </div>
  )
}

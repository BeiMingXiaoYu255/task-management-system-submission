/**
 * 个人资料表单：编辑昵称、邮箱、手机号与简介。
 *
 * 前端先行校验（昵称必填、邮箱/手机号格式、简介长度），
 * 校验通过后调用 userApi.updateMyProfile，成功后通过 onSaved 回传最新资料。
 */

import { useEffect, useState } from 'react'

import { updateMyProfile } from '../../api/userApi'
import { useToast } from '../../context/ToastContext'
import type { UpdateProfilePayload, UserDetail } from '../../types/user'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Textarea from '../ui/Textarea'
import styles from './ProfileForm.module.css'

/** 表单字段错误集合。 */
interface ProfileFormErrors {
  nickname?: string
  email?: string
  phone?: string
  bio?: string
}

/** 邮箱格式校验正则。 */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** 手机号格式校验正则（中国大陆 11 位）。 */
const PHONE_PATTERN = /^1[3-9]\d{9}$/

/** 个人资料表单属性。 */
interface ProfileFormProps {
  profile: UserDetail
  onSaved: (updatedProfile: UserDetail) => void
}

/** 个人资料表单。 */
export default function ProfileForm({ profile, onSaved }: ProfileFormProps) {
  const { showToast } = useToast()
  const [nickname, setNickname] = useState<string>('')
  const [email, setEmail] = useState<string>('')
  const [phone, setPhone] = useState<string>('')
  const [bio, setBio] = useState<string>('')
  const [errors, setErrors] = useState<ProfileFormErrors>({})
  const [saving, setSaving] = useState<boolean>(false)

  /** 资料变化时重置表单内容。 */
  useEffect(() => {
    setNickname(profile.nickname)
    setEmail(profile.email ?? '')
    setPhone(profile.phone ?? '')
    setBio(profile.bio ?? '')
    setErrors({})
  }, [profile])

  /** 前端校验；返回字段错误集合，空对象表示校验通过。 */
  const validateForm = (): ProfileFormErrors => {
    const nextErrors: ProfileFormErrors = {}
    const trimmedNickname = nickname.trim()
    if (trimmedNickname.length === 0) {
      nextErrors.nickname = 'Nickname is required'
    } else if (trimmedNickname.length > 20) {
      nextErrors.nickname = 'Nickname must be 20 characters or fewer'
    }
    const trimmedEmail = email.trim()
    if (trimmedEmail.length > 0 && !EMAIL_PATTERN.test(trimmedEmail)) {
      nextErrors.email = 'Enter a valid email address'
    }
    const trimmedPhone = phone.trim()
    if (trimmedPhone.length > 0 && !PHONE_PATTERN.test(trimmedPhone)) {
      nextErrors.phone = 'Enter a valid 11-digit phone number'
    }
    if (bio.trim().length > 200) {
      nextErrors.bio = 'Bio must be 200 characters or fewer'
    }
    return nextErrors
  }

  /** 提交保存。 */
  const handleSubmit = async (): Promise<void> => {
    const nextErrors = validateForm()
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }
    setSaving(true)
    try {
      const payload: UpdateProfilePayload = {
        nickname: nickname.trim(),
        email: email.trim() === '' ? null : email.trim(),
        phone: phone.trim() === '' ? null : phone.trim(),
        bio: bio.trim() === '' ? null : bio.trim(),
      }
      const updatedProfile = await updateMyProfile(payload)
      onSaved(updatedProfile)
      showToast('Profile saved', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to save. Please try again later.', 'error')
    } finally {
      setSaving(false)
    }
  }

  /** 重置为最近一次保存的资料。 */
  const handleReset = (): void => {
    setNickname(profile.nickname)
    setEmail(profile.email ?? '')
    setPhone(profile.phone ?? '')
    setBio(profile.bio ?? '')
    setErrors({})
  }

  return (
    <div className={styles.formGrid}>
      <Input
        label="Username"
        value={profile.username}
        onChange={() => undefined}
        hint="Username cannot be changed after creation"
        disabled
      />
      <Input
        label="Nickname"
        value={nickname}
        onChange={(event) => setNickname(event.target.value)}
        placeholder="Enter your nickname"
        error={errors.nickname}
      />
      <Input
        label="Email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        placeholder="Enter your email"
        type="email"
        error={errors.email}
      />
      <Input
        label="Phone"
        value={phone}
        onChange={(event) => setPhone(event.target.value)}
        placeholder="Enter your phone number"
        error={errors.phone}
      />
      <div className={styles.fullWidth}>
        <Textarea
          label="Bio"
          value={bio}
          onChange={(event) => setBio(event.target.value)}
          rows={4}
          placeholder="Introduce yourself, including your areas of expertise and work habits"
          maxLength={200}
          error={errors.bio}
        />
      </div>
      <div className={styles.formActions}>
        <Button variant="primary" loading={saving} onClick={() => void handleSubmit()}>
          Save Changes
        </Button>
        <Button variant="secondary" onClick={handleReset}>
          Reset
        </Button>
      </div>
    </div>
  )
}

/**
 * 个人资料页面：查看并编辑账号基本信息、技能标签与团队身份。
 *
 * 数据来源：userApi.getMyProfile（本人资料）；团队身份来自 AuthContext；
 * 保存成功后同步刷新 AuthContext，保证顶栏昵称等信息即时更新。
 */

import { useCallback, useEffect, useState } from 'react'

import { getMyProfile } from '../../api/userApi'
import MembershipSection from '../../components/profile/MembershipSection'
import ProfileForm from '../../components/profile/ProfileForm'
import SkillEditor from '../../components/profile/SkillEditor'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { useAuth } from '../../context/AuthContext'
import type { UserDetail } from '../../types/user'
import styles from './ProfilePage.module.css'

/** 个人资料页面。 */
export default function ProfilePage() {
  const { user, refreshMe } = useAuth()
  const [profile, setProfile] = useState<UserDetail | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  /** 拉取本人资料。 */
  const loadProfile = useCallback(async (): Promise<void> => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const userDetail = await getMyProfile()
      setProfile(userDetail)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load profile')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadProfile()
  }, [loadProfile])

  /** 资料保存成功：更新局部资料并刷新全局登录用户信息。 */
  const handleProfileSaved = useCallback(
    (updatedProfile: UserDetail): void => {
      setProfile(updatedProfile)
      refreshMe().catch(() => undefined)
    },
    [refreshMe],
  )

  /** 渲染主体内容。 */
  const renderContent = () => {
    if (loading) {
      return (
        <div className={styles.stateArea}>
          <Spinner />
          <span>Loading profile ...</span>
        </div>
      )
    }
    if (errorMessage !== null || profile === null) {
      return (
        <EmptyState
          title="Failed to load profile"
          description={errorMessage ?? 'Profile not found. Please try again later.'}
          action={
            <Button variant="secondary" onClick={() => void loadProfile()}>
              Reload
            </Button>
          }
        />
      )
    }
    return (
      <div className={styles.contentStack}>
        <Card title="Basic Information">
          <ProfileForm profile={profile} onSaved={handleProfileSaved} />
        </Card>
        <Card title="Skill Tags">
          <SkillEditor skills={profile.skills} onSaved={handleProfileSaved} />
        </Card>
        <Card title="Teams and Roles">
          <MembershipSection
            teams={user?.teams ?? []}
            globalRole={user?.user.globalRole ?? 'user'}
          />
        </Card>
      </div>
    )
  }

  return (
    <div className={styles.pageRoot}>
      <PageHeader title="Profile" description="Keep your basic information and skill tags up to date for smoother collaboration and task assignment." />
      {renderContent()}
    </div>
  )
}

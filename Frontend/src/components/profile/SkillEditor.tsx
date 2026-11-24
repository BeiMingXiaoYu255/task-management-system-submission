/**
 * 技能标签编辑器：支持从标签字典选择已有技能、新建技能标签，
 * 并为每个技能设置 1-5 级熟练度，最后整体覆盖式保存到后端。
 *
 * 交互说明：
 * 1. 页面加载时拉取全部技能标签字典，供选择复用；
 * 2. 编辑区维护草稿列表，全部调整完成后再点击“保存技能”统一提交；
 * 3. 新建标签成功后自动加入草稿，避免用户二次操作。
 */

import { useCallback, useEffect, useMemo, useState } from 'react'

import { createSkillTag, listSkillTags, saveMySkills } from '../../api/userApi'
import { useToast } from '../../context/ToastContext'
import type { SkillItem, SkillTagItem, UserDetail } from '../../types/user'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Tag from '../ui/Tag'
import styles from './SkillEditor.module.css'

/** 编辑中的技能草稿项。 */
interface SkillDraftItem {
  /** 技能标签 ID。 */
  skillTagId: number
  /** 技能名称。 */
  name: string
  /** 技能分类。 */
  category: string | null
  /** 熟练度 1-5。 */
  proficiency: number
}

/** 熟练度下拉选项。 */
const PROFICIENCY_OPTIONS = [1, 2, 3, 4, 5].map((level) => ({ value: level, label: 'Level ' + level }))

/** 技能标签编辑器属性。 */
interface SkillEditorProps {
  skills: SkillItem[]
  onSaved: (updatedProfile: UserDetail) => void
}

/** 技能标签编辑器。 */
export default function SkillEditor({ skills, onSaved }: SkillEditorProps) {
  const { showToast } = useToast()
  const [allTags, setAllTags] = useState<SkillTagItem[]>([])
  const [draftSkills, setDraftSkills] = useState<SkillDraftItem[]>([])
  const [selectedTagId, setSelectedTagId] = useState<number>(0)
  const [newTagName, setNewTagName] = useState<string>('')
  const [newTagCategory, setNewTagCategory] = useState<string>('')
  const [saving, setSaving] = useState<boolean>(false)
  const [creating, setCreating] = useState<boolean>(false)

  /** 已选技能标签同步到草稿列表。 */
  useEffect(() => {
    setDraftSkills(
      skills.map((skill) => ({
        skillTagId: skill.id,
        name: skill.name,
        category: skill.category,
        proficiency: skill.proficiency,
      })),
    )
  }, [skills])

  /** 拉取技能标签字典。 */
  const loadSkillTags = useCallback(async (): Promise<void> => {
    try {
      const skillTags = await listSkillTags()
      setAllTags(skillTags)
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to load skill tags', 'error')
    }
  }, [showToast])

  useEffect(() => {
    void loadSkillTags()
  }, [loadSkillTags])

  /** 可添加的标签选项：过滤掉草稿中已存在的标签。 */
  const availableTagOptions = useMemo(() => {
    const draftTagIds = new Set(draftSkills.map((draftItem) => draftItem.skillTagId))
    return allTags
      .filter((tag) => !draftTagIds.has(tag.id))
      .map((tag) => ({
        value: tag.id,
        label: tag.category === null ? tag.name : tag.name + ' · ' + tag.category,
      }))
  }, [allTags, draftSkills])

  /** 把标签加入草稿列表；已存在时提示并忽略。 */
  const appendSkillDraft = (tag: SkillTagItem): void => {
    if (draftSkills.some((draftItem) => draftItem.skillTagId === tag.id)) {
      showToast('This skill tag is already in the list', 'info')
      return
    }
    setDraftSkills((previous) => [
      ...previous,
      { skillTagId: tag.id, name: tag.name, category: tag.category, proficiency: 3 },
    ])
  }

  /** 添加已有标签到草稿。 */
  const handleAddExistingTag = (): void => {
    if (selectedTagId === 0) {
      showToast('Select a skill tag to add first', 'info')
      return
    }
    const targetTag = allTags.find((tag) => tag.id === selectedTagId)
    if (targetTag) {
      appendSkillDraft(targetTag)
      setSelectedTagId(0)
    }
  }

  /** 新建技能标签并加入草稿。 */
  const handleCreateTag = async (): Promise<void> => {
    const trimmedName = newTagName.trim()
    if (trimmedName.length === 0) {
      showToast('Enter a name for the new skill tag', 'error')
      return
    }
    setCreating(true)
    try {
      const createdTag = await createSkillTag({
        name: trimmedName,
        category: newTagCategory.trim() === '' ? null : newTagCategory.trim(),
      })
      setAllTags((previous) => {
        if (previous.some((tag) => tag.id === createdTag.id)) {
          return previous
        }
        return [...previous, createdTag]
      })
      appendSkillDraft(createdTag)
      setNewTagName('')
      setNewTagCategory('')
      showToast('Skill tag created', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to create skill tag', 'error')
    } finally {
      setCreating(false)
    }
  }

  /** 移除草稿中的技能标签。 */
  const handleRemoveTag = (skillTagId: number): void => {
    setDraftSkills((previous) => previous.filter((item) => item.skillTagId !== skillTagId))
  }

  /** 修改某个技能的熟练度。 */
  const handleProficiencyChange = (skillTagId: number, value: string | number): void => {
    const proficiency = Number(value)
    setDraftSkills((previous) =>
      previous.map((item) => (item.skillTagId === skillTagId ? { ...item, proficiency } : item)),
    )
  }

  /** 整体保存技能列表。 */
  const handleSaveSkills = async (): Promise<void> => {
    setSaving(true)
    try {
      const updatedProfile = await saveMySkills({
        skills: draftSkills.map((item) => ({
          skillTagId: item.skillTagId,
          proficiency: item.proficiency,
        })),
      })
      onSaved(updatedProfile)
      showToast('Skill tags saved', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Failed to save skill tags', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={styles.editorLayout}>
      {draftSkills.length === 0 ? (
        <EmptyState title="No skill tags yet" description="Select an existing tag below or create a new one to showcase your expertise." />
      ) : (
        <ul className={styles.skillList}>
          {draftSkills.map((draftItem) => (
            <li key={draftItem.skillTagId} className={styles.skillRow}>
              <div className={styles.skillNameArea}>
                <Tag label={draftItem.name} />
                {draftItem.category !== null && (
                  <span className={styles.skillCategory}>{draftItem.category}</span>
                )}
              </div>
              <div className={styles.skillProficiency}>
                <Select
                  value={draftItem.proficiency}
                  onChange={(value) => handleProficiencyChange(draftItem.skillTagId, value)}
                  options={PROFICIENCY_OPTIONS}
                />
                <Button variant="ghost" size="small" onClick={() => handleRemoveTag(draftItem.skillTagId)}>
                  Remove
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className={styles.addArea}>
        <div className={styles.addRow}>
          <Select
            label="Existing Skill Tags"
            value={selectedTagId === 0 ? '' : selectedTagId}
            onChange={(value) => setSelectedTagId(Number(value))}
            options={availableTagOptions}
            placeholder="Select a skill tag"
          />
          <Button variant="secondary" onClick={handleAddExistingTag}>
            Add
          </Button>
        </div>
        <div className={styles.addRow}>
          <Input
            label="New Tag Name"
            value={newTagName}
            onChange={(event) => setNewTagName(event.target.value)}
            placeholder="e.g. Backend Development"
          />
          <Input
            label="Tag Category (Optional)"
            value={newTagCategory}
            onChange={(event) => setNewTagCategory(event.target.value)}
            placeholder="e.g. Technology"
          />
          <Button variant="secondary" loading={creating} onClick={() => void handleCreateTag()}>
            Create and Add
          </Button>
        </div>
      </div>

      <div className={styles.editorActions}>
        <Button variant="primary" loading={saving} onClick={() => void handleSaveSkills()}>
          Save Skills
        </Button>
        <span className={styles.hintText}>Proficiency is rated 1-5. Saving replaces the existing skill list.</span>
      </div>
    </div>
  )
}

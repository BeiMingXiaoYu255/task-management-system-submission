/**
 * Modal 组件测试：打开渲染、Esc 关闭、关闭后不渲染。
 */

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import Modal from '../components/ui/Modal'

describe('Modal', () => {
  it('renders the title, content, and footer when open', () => {
    render(
      <Modal open title="Confirm action" onClose={() => {}} footer={<button type="button">Confirm</button>}>
        <p>Body content</p>
      </Modal>,
    )
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Confirm action')).toBeInTheDocument()
    expect(screen.getByText('Body content')).toBeInTheDocument()
    expect(screen.getByText('Confirm')).toBeInTheDocument()
  })

  it('calls onClose when Escape is pressed', () => {
    const handleClose = vi.fn()
    render(
      <Modal open title="Confirm action" onClose={handleClose}>
        <p>Body content</p>
      </Modal>,
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it('renders nothing when closed', () => {
    render(
      <Modal open={false} title="Confirm action" onClose={() => {}}>
        <p>Body content</p>
      </Modal>,
    )
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})

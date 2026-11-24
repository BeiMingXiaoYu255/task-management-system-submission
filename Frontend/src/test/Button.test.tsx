/**
 * Button 组件测试：渲染、点击、禁用态与加载态。
 */

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import Button from '../components/ui/Button'

describe('Button', () => {
  it('renders its text and responds to clicks', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Save</Button>)
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('does not fire clicks while disabled', () => {
    const handleClick = vi.fn()
    render(
      <Button disabled onClick={handleClick}>
        Save
      </Button>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(handleClick).not.toHaveBeenCalled()
  })

  it('is disabled and marked with aria-busy while loading', () => {
    render(<Button loading>Submit</Button>)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('aria-busy', 'true')
  })
})

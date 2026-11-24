/**
 * 表单类组件测试：Input / Textarea / Checkbox / Select 的基础行为。
 */

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import Checkbox from '../components/ui/Checkbox'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Textarea from '../components/ui/Textarea'

describe('Input', () => {
  it('renders the label and forwards native change events', () => {
    const handleChange = vi.fn()
    render(<Input label="Username" value="" onChange={handleChange} />)
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'alice' } })
    expect(handleChange).toHaveBeenCalledTimes(1)
  })

  it('shows the error message', () => {
    render(<Input label="Username" value="" onChange={() => {}} error="Please enter your username" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Please enter your username')
  })
})

describe('Textarea', () => {
  it('renders the label and forwards native change events', () => {
    const handleChange = vi.fn()
    render(<Textarea label="Task description" value="" onChange={handleChange} />)
    fireEvent.change(screen.getByLabelText('Task description'), { target: { value: 'A short description' } })
    expect(handleChange).toHaveBeenCalledTimes(1)
  })
})

describe('Checkbox', () => {
  it('fires the native change event when the label is clicked', () => {
    const handleChange = vi.fn()
    render(<Checkbox checked={false} onChange={handleChange} label="Remember me" />)
    fireEvent.click(screen.getByLabelText('Remember me'))
    expect(handleChange).toHaveBeenCalledTimes(1)
  })
})

describe('Select', () => {
  it('returns the original typed option value when the selection changes', () => {
    const handleChange = vi.fn()
    render(
      <Select
        label="Level"
        value={2}
        onChange={handleChange}
        options={[
          { value: 1, label: 'Beginner' },
          { value: 2, label: 'Intermediate' },
        ]}
      />,
    )
    fireEvent.change(screen.getByLabelText('Level'), { target: { value: '1' } })
    expect(handleChange).toHaveBeenCalledWith(1)
  })
})

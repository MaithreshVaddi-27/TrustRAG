import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RegisterPage from './RegisterPage'
import LoginPage from './LoginPage'

const { authService } = vi.hoisted(() => ({
  authService: { login: vi.fn(), register: vi.fn() },
}))

vi.mock('@/services/auth', () => ({ authService }))

const navigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

function setValue(selector, value) {
  const element = document.querySelector(selector)
  const prototype = Object.getPrototypeOf(element)
  Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, value)
  element.dispatchEvent(new Event('input', { bubbles: true }))
}

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authService.register.mockResolvedValue({ id: 'u1' })
    authService.login.mockResolvedValue({ access_token: 't' })
  })

  it('lists the password requirements and reports them as they are met', () => {
    render(
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const items = screen.getAllByRole('listitem')
    const unmet = items.filter((li) => !li.className.includes('--met'))
    expect(unmet).toHaveLength(5)

    setValue('#reg-password', 'CorrectHorse1!')
    expect(
      screen.getAllByRole('listitem').filter((li) => li.className.includes('--met')),
    ).toHaveLength(5)
  })

  it('names what the password still needs, and focuses the field', async () => {
    render(
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
        </Routes>
      </MemoryRouter>,
    )

    setValue('#reg-email', 'someone@example.com')
    setValue('#reg-password', 'short')
    setValue('#reg-confirm', 'short')

    fireEvent.submit(document.querySelector('#register-form'))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeTruthy()
    })
    expect(screen.getByRole('alert').textContent).toMatch(/still needs/i)
    expect(authService.register).not.toHaveBeenCalled()
  })

  it('refuses a password and its confirmation that differ', async () => {
    render(
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
        </Routes>
      </MemoryRouter>,
    )

    setValue('#reg-email', 'someone@example.com')
    setValue('#reg-password', 'CorrectHorse1!')
    setValue('#reg-confirm', 'CorrectHorse2!')

    fireEvent.submit(document.querySelector('#register-form'))

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toMatch(/do not match/i)
    })
    expect(authService.register).not.toHaveBeenCalled()
  })

  it('registers once the rules are met and the passwords agree', async () => {
    render(
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
        </Routes>
      </MemoryRouter>,
    )

    setValue('#reg-name', 'Test User')
    setValue('#reg-email', 'someone@example.com')
    setValue('#reg-password', 'CorrectHorse1!')
    setValue('#reg-confirm', 'CorrectHorse1!')

    fireEvent.submit(document.querySelector('#register-form'))

    await waitFor(() => {
      expect(authService.register).toHaveBeenCalled()
    })
    expect(authService.register.mock.calls[0][0]).toBe('someone@example.com')
  })
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('acknowledges an account that was just created', () => {
    // Regression: the register page sent the reader here with ?registered=1
    // and nothing read the flag.
    render(
      <MemoryRouter initialEntries={['/login?registered=1']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(
      screen.getByText('Your account was created. Sign in to continue.'),
    ).toBeTruthy()
  })

  it('says nothing about registration on a plain sign-in', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(
      screen.queryByText('Your account was created. Sign in to continue.'),
    ).toBeNull()
  })
})

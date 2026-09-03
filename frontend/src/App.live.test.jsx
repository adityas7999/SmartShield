import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.jsx'


const liveDescribe = process.env.SMARTSHIELD_LIVE_API === '1' ? describe : describe.skip
const nativeFetch = globalThis.fetch


afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})


liveDescribe('SmartShield live vertical slice', () => {
  it('renders vulnerable and safe outcomes returned by FastAPI and C++', async () => {
    vi.stubGlobal('fetch', (input, init) => {
      const target = new URL(String(input), 'http://127.0.0.1:8000')
      return nativeFetch(target, init)
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByLabelText('Solidity source code').value).toContain('tx.origin')
    })
    fireEvent.click(screen.getByRole('button', { name: /analyse contract/i }))
    expect(await screen.findByText('TXO-001')).toBeInTheDocument()
    expect(screen.getByText(/Confidence:/i).parentElement).toHaveTextContent('high')

    fireEvent.click(screen.getByRole('button', { name: /safe sample/i }))
    await waitFor(() => {
      expect(screen.getByLabelText('Solidity source code').value).toContain('msg.sender')
    })
    await screen.findByText('Ready')
    fireEvent.click(screen.getByRole('button', { name: /analyse contract/i }))
    expect(await screen.findByText(/No direct tx.origin authorization guard found/i)).toBeInTheDocument()
  })
})

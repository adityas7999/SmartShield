import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.jsx'

const vulnerableSource = 'contract Wallet { function withdraw() external { require(tx.origin == owner); recipient.transfer(1); } }'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('SmartShield workbench', () => {
  it('renders a finding returned by the API', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ fileName: 'TxOriginWallet.sol', source: vulnerableSource, expected: 'potential finding' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        status: 'completed',
        findings: [{
          detectorId: 'TXO-001', vulnerabilityType: 'tx.origin authorization misuse', severity: 'high', confidence: 'high',
          location: { file: 'TxOriginWallet.sol', line: 1, column: 58 }, function: 'withdraw',
          explanation: 'tx.origin is used in an authorization guard.', evidence: ['Authorization condition contains tx.origin'],
          limitations: [], irFacts: { statementType: 'require', conditionExpression: 'tx.origin == owner' },
        }],
        analysisLimitations: [], analysisStages: [], analysisSummary: { functionsInspected: 1 },
      }), { status: 200 })))

    render(<App />)
    await screen.findByDisplayValue(vulnerableSource)
    fireEvent.click(screen.getByRole('button', { name: /analyse contract/i }))
    expect(await screen.findByText('TXO-001')).toBeInTheDocument()
    expect(screen.getByText(/Transaction origin used for authorization/i)).toBeInTheDocument()
  })

  it('shows the safe state returned by the API', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ fileName: 'TxOriginWallet.sol', source: vulnerableSource, expected: 'potential finding' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        status: 'completed', findings: [], analysisLimitations: [], analysisStages: [], analysisSummary: { functionsInspected: 1 },
      }), { status: 200 })))

    render(<App />)
    await screen.findByDisplayValue(vulnerableSource)
    fireEvent.click(screen.getByRole('button', { name: /analyse contract/i }))
    expect(await screen.findByText(/No direct tx.origin authorization guard found/i)).toBeInTheDocument()
  })

  it('shows compiler errors returned by the API', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ fileName: 'Broken.sol', source: 'contract Broken {', expected: 'error' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: { code: 'parse_failed', message: 'Solidity compilation failed.', diagnostics: ['ParserError'] } }), { status: 422 })))

    render(<App />)
    await screen.findByDisplayValue('contract Broken {')
    fireEvent.click(screen.getByRole('button', { name: /analyse contract/i }))
    expect(await screen.findByText(/Analysis could not be completed/i)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Compiler diagnostics/i))
    expect(screen.getByText('ParserError')).toBeInTheDocument()
  })
})

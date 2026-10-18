const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function parseResponse(response) {
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = body?.detail
    const error = new Error(detail?.message ?? `Request failed with status ${response.status}`)
    error.code = detail?.code ?? 'request_failed'
    error.diagnostics = detail?.diagnostics ?? []
    error.report = detail?.report ?? null
    throw error
  }
  return body
}

export async function loadFixture(name) {
  const response = await fetch(`${API_BASE}/api/fixtures/${name}`)
  return parseResponse(response)
}

export async function getMlStatus() {
  try {
    const response = await fetch(`${API_BASE}/api/ml/status`)
    if (!response.ok) return null
    return await response.json()
  } catch {
    return null
  }
}

export async function analyzeContract(source, fileName) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, fileName }),
  })
  return parseResponse(response)
}

export async function remediateFinding(source, fileName, findingId = null, ruleId = null) {
  const response = await fetch(`${API_BASE}/api/remediate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, fileName, findingId, ruleId }),
  })
  return parseResponse(response)
}

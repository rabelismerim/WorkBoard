export async function api(path, method = 'GET', body, revision) {
  const csrf = document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] ?? ''
  const multipart = body instanceof FormData
  const headers = { 'X-CSRFToken': decodeURIComponent(csrf) }
  if (!multipart) headers['Content-Type'] = 'application/json'
  if (revision !== undefined && revision !== null) headers['If-Match'] = String(revision)
  const response = await fetch(`/api/${path}`, { method, credentials: 'same-origin', headers, body: body === undefined ? undefined : multipart ? body : JSON.stringify(body) })
  if (response.status === 204) return undefined
  const data = await response.json().catch(() => ({ detail: 'O servidor não respondeu. Verifique a conexão.' }))
  if (!response.ok) {
    const error = new Error(data.detail ?? Object.values(data).flat().join(' '))
    error.status = response.status
    throw error
  }
  return data
}

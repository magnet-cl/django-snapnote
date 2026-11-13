import { afterEach, describe, expect, it, vi } from 'vitest';
import { resolveCsrfToken, sendReport } from './api';

const payload = { title: 't', description: '', screenshot: null, annotations: null };

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT';
});

describe('CSRF token', () => {
  it('prefers the token from the props over the cookie', () => {
    document.cookie = 'csrftoken=fromcookie';
    expect(resolveCsrfToken('fromprops')).toBe('fromprops');
  });

  it('falls back to the cookie when the props have no token', () => {
    document.cookie = 'csrftoken=fromcookie';
    expect(resolveCsrfToken(undefined)).toBe('fromcookie');
    expect(resolveCsrfToken('')).toBe('fromcookie');
  });

  it('is empty when there is neither', () => {
    expect(resolveCsrfToken()).toBe('');
  });

  it('sends the props token in X-CSRFToken without reading the cookie', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);
    await sendReport('/snapnote/report/', payload, 'fromprops');
    expect(fetchMock.mock.calls[0][1].headers['X-CSRFToken']).toBe('fromprops');
  });

  it('sends the cookie token when the props have none', async () => {
    document.cookie = 'csrftoken=fromcookie';
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);
    await sendReport('/snapnote/report/', payload);
    expect(fetchMock.mock.calls[0][1].headers['X-CSRFToken']).toBe('fromcookie');
  });
});

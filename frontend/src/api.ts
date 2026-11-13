function getCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1]) : '';
}

export type Payload = {
  title: string;
  description: string;
  screenshot: Blob | null;
  annotations: Blob | null;
};

/** Token from the page props; the cookie is only a fallback (it may be HttpOnly). */
export function resolveCsrfToken(propToken?: string): string {
  return propToken || getCookie('csrftoken');
}

export async function sendReport(url: string, payload: Payload, csrfToken?: string) {
  const data = new FormData();
  data.append('title', payload.title);
  data.append('description', payload.description);
  data.append('page_url', window.location.href);
  if (payload.screenshot) {
    data.append('screenshot', payload.screenshot, 'screenshot.png');
  }
  if (payload.annotations) {
    data.append('annotations', payload.annotations, 'annotations.png');
  }
  const response = await fetch(url, {
    method: 'POST',
    body: data,
    credentials: 'same-origin',
    headers: { 'X-CSRFToken': resolveCsrfToken(csrfToken) },
  });
  if (!response.ok) {
    throw new Error(`Snapnote request failed: ${response.status}`);
  }
}

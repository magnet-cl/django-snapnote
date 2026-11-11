import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import styles from './styles.css?inline';
import { Props } from './types';

function mount() {
  const root = document.getElementById('snapnote-root');
  const json = document.getElementById('snapnote-props');
  if (!root || !json?.textContent || root.shadowRoot) return;

  const props = JSON.parse(json.textContent) as Props;
  // Shadow DOM: the host page's CSS can't break the widget and vice versa.
  const shadow = root.attachShadow({ mode: 'open' });
  const style = document.createElement('style');
  style.textContent = styles;
  const container = document.createElement('div');
  container.className = 'snapnote';
  shadow.append(style, container);
  createRoot(container).render(
    <React.StrictMode>
      <App {...props} />
    </React.StrictMode>,
  );
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount);
} else {
  mount();
}

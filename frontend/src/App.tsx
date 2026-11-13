import React, { useEffect, useState } from 'react';
import { AnnotationEditor } from './AnnotationEditor';
import { sendReport } from './api';
import { captureScreen } from './capture';
import { FlagIcon } from './icons';
import { Props, Shape } from './types';

type Phase = 'idle' | 'capturing' | 'editing' | 'form';

/**
 * Floating button that captures the tab (or lets the user attach an image when
 * capturing is not possible), lets them annotate it and sends a ticket. The
 * form stays mounted while editing so typed values survive.
 */
export function App({ report_url: reportUrl, csrf_token: csrfToken, labels, max_upload_mb: maxMb }: Props) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [screenshot, setScreenshot] = useState<Blob | null>(null);
  const [captureFailed, setCaptureFailed] = useState(false);
  const [shapes, setShapes] = useState<Shape[]>([]);
  const [layer, setLayer] = useState<Blob | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [urls, setUrls] = useState({ screenshot: '', layer: '' });

  // Object URLs for the preview; revoked on change/unmount (StrictMode safe).
  useEffect(() => {
    const next = {
      screenshot: screenshot ? URL.createObjectURL(screenshot) : '',
      layer: layer ? URL.createObjectURL(layer) : '',
    };
    setUrls(next);
    return () => {
      if (next.screenshot) URL.revokeObjectURL(next.screenshot);
      if (next.layer) URL.revokeObjectURL(next.layer);
    };
  }, [screenshot, layer]);

  // Success notice disappears by itself.
  useEffect(() => {
    if (!message?.ok) return undefined;
    const timer = setTimeout(() => setMessage(null), 5000);
    return () => clearTimeout(timer);
  }, [message]);

  const reset = () => {
    setPhase('idle');
    setScreenshot(null);
    setCaptureFailed(false);
    setShapes([]);
    setLayer(null);
    setTitle('');
    setDescription('');
    setMessage(null);
  };

  const start = async () => {
    setMessage(null);
    setPhase('capturing');
    const blob = await captureScreen();
    setScreenshot(blob);
    setCaptureFailed(!blob);
    setShapes([]);
    setLayer(null);
    setPhase(blob ? 'editing' : 'form');
    if (!blob) setMessage({ ok: false, text: labels.noCapture });
  };

  const onFile = (file: File | undefined) => {
    if (!file) return;
    if (file.size > maxMb * 1024 * 1024) {
      setMessage({ ok: false, text: labels.error });
      return;
    }
    setMessage(null);
    setScreenshot(file);
    setShapes([]);
    setLayer(null);
    setPhase('editing');
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim()) {
      setMessage({ ok: false, text: labels.titleRequired });
      return;
    }
    setSending(true);
    try {
      await sendReport(
        reportUrl,
        { title: title.trim(), description, screenshot, annotations: layer },
        csrfToken,
      );
      reset();
      setMessage({ ok: true, text: labels.success });
    } catch {
      setMessage({ ok: false, text: labels.error });
    } finally {
      setSending(false);
    }
  };

  const reporting = phase === 'editing' || phase === 'form';

  return (
    <>
      {!reporting && phase !== 'capturing' && (
        <button
          type="button"
          className="snapnote-fab"
          title={labels.report}
          aria-label={labels.report}
          onClick={start}
        >
          <FlagIcon />
        </button>
      )}

      {message?.ok && phase === 'idle' && (
        <div className="snapnote-toast" role="status">
          {message.text}
        </div>
      )}

      {reporting && (
        <div
          className="snapnote-backdrop"
          hidden={phase === 'editing'}
          role="dialog"
          aria-modal="true"
          aria-label={labels.report}
        >
          <form className="snapnote-modal" onSubmit={submit}>
            <div className="snapnote-modal-header">
              <h2>{labels.report}</h2>
              <button
                type="button"
                className="snapnote-close"
                aria-label={labels.cancel}
                onClick={reset}
              >
                ×
              </button>
            </div>
            <div className="snapnote-modal-body">
              {message && !message.ok && (
                <div className="snapnote-alert" role="alert">
                  {message.text}
                </div>
              )}
              <label className="snapnote-field">
                <span>{labels.title}</span>
                <input
                  required
                  maxLength={200}
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </label>
              <label className="snapnote-field">
                <span>{labels.description}</span>
                <textarea
                  rows={4}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </label>
              {captureFailed && !screenshot && (
                <label className="snapnote-field">
                  <span>{labels.attach}</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => onFile(event.target.files?.[0])}
                  />
                </label>
              )}
              {screenshot && (
                <div>
                  <div className="snapnote-label">{labels.preview}</div>
                  <div className="snapnote-preview">
                    {urls.screenshot && <img src={urls.screenshot} alt="" />}
                    {urls.layer && (
                      <img className="snapnote-preview-annotations" src={urls.layer} alt="" />
                    )}
                  </div>
                  <div className="snapnote-gap">
                    <button type="button" className="snapnote-btn" onClick={() => setPhase('editing')}>
                      {labels.editAnnotations}
                    </button>
                  </div>
                </div>
              )}
            </div>
            <div className="snapnote-modal-footer">
              <button type="button" className="snapnote-btn" onClick={reset}>
                {labels.cancel}
              </button>
              <button type="submit" className="snapnote-btn snapnote-btn-primary" disabled={sending}>
                {sending ? labels.sending : labels.send}
              </button>
            </div>
          </form>
        </div>
      )}

      {phase === 'editing' && screenshot && (
        <AnnotationEditor
          screenshot={screenshot}
          initialShapes={shapes}
          labels={labels}
          onDone={(newShapes, newLayer) => {
            setShapes(newShapes);
            setLayer(newLayer);
            setPhase('form');
          }}
          onCancel={() => setPhase('form')}
        />
      )}
    </>
  );
}

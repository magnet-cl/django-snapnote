import React, { useEffect, useRef, useState } from 'react';
import { PenIcon, RectIcon, TextIcon, TrashIcon, UndoIcon } from './icons';
import {
  containedRect,
  drawShapes,
  renderAnnotationLayer,
  strokeWidthFor,
  textFontSize,
  toImagePoint,
} from './drawing';
import { Shape, Labels, Tool } from './types';

type Props = {
  screenshot: Blob;
  initialShapes: Shape[];
  labels: Labels;
  onDone: (shapes: Shape[], layer: Blob | null) => void;
  onCancel: () => void;
};

type TextDraft = { x: number; y: number; width: number; value: string };

const TOOLS: {
  tool: Tool;
  key: string;
  Icon: React.ComponentType;
  label: keyof Labels;
}[] = [
  { tool: 'pen', key: 'F', Icon: PenIcon, label: 'pen' },
  { tool: 'rect', key: 'G', Icon: RectIcon, label: 'rectangle' },
  { tool: 'text', key: 'R', Icon: TextIcon, label: 'text' },
];

const KEY_TO_TOOL: Record<string, Tool> = { f: 'pen', g: 'rect', r: 'text' };

export function AnnotationEditor({
  screenshot,
  initialShapes,
  labels,
  onDone,
  onCancel,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const draftRef = useRef<TextDraft | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const drawingRef = useRef<Shape | null>(null);

  const [imageUrl, setImageUrl] = useState('');
  const [tool, setTool] = useState<Tool>('pen');
  const [shapes, setShapes] = useState<Shape[]>(initialShapes);
  const [draft, setDraftState] = useState<TextDraft | null>(null);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });

  // Object URLs are created in an effect and revoked on unmount (StrictMode safe).
  useEffect(() => {
    const url = URL.createObjectURL(screenshot);
    setImageUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [screenshot]);

  const setDraft = (value: TextDraft | null) => {
    draftRef.current = value;
    setDraftState(value);
  };

  const redraw = (extra?: Shape | null) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    drawShapes(ctx, extra ? [...shapes, extra] : shapes);
  };

  useEffect(() => {
    redraw(drawingRef.current);
  });

  const draftToShape = (current: TextDraft): Shape | null => {
    const value = current.value.trim();
    if (!value) return null;
    return {
      tool: 'text',
      points: [{ x: current.x, y: current.y }],
      width: current.width,
      text: value,
    };
  };

  const commitDraft = (): Shape | null => {
    const { current } = draftRef;
    if (!current) return null;
    // Clear the ref first so a later blur doesn't commit it twice.
    setDraft(null);
    const shape = draftToShape(current);
    if (shape) setShapes((prev) => [...prev, shape]);
    return shape;
  };

  const finish = async () => {
    const committed = commitDraft();
    const final = committed ? [...shapes, committed] : shapes;
    const layer = await renderAnnotationLayer(
      final,
      naturalSize.width,
      naturalSize.height,
    );
    onDone(final, layer);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (event.composedPath()[0] === inputRef.current) return;
      if (event.key === 'Escape') {
        onCancel();
        return;
      }
      const next = KEY_TO_TOOL[event.key.toLowerCase()];
      if (next) setTool(next);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onCancel]);

  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // Avoid native drag-and-drop of selected page text (cancels the pointer)
    // and keep focus on the text input.
    event.preventDefault();
    const point = toImagePoint(canvas, event.clientX, event.clientY);
    const width = strokeWidthFor(canvas);

    if (tool === 'text') {
      if (draftRef.current) {
        commitDraft();
        return;
      }
      setDraft({ x: point.x, y: point.y, width, value: '' });
      return;
    }
    canvas.setPointerCapture(event.pointerId);
    drawingRef.current = { tool, points: [point], width };
    redraw(drawingRef.current);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const { current } = drawingRef;
    if (!canvas || !current) return;
    const point = toImagePoint(canvas, event.clientX, event.clientY);
    current.points =
      current.tool === 'pen'
        ? [...current.points, point]
        : [current.points[0], point];
    redraw(current);
  };

  const onPointerUp = () => {
    const { current } = drawingRef;
    drawingRef.current = null;
    if (current) setShapes((prev) => [...prev, current]);
  };

  // Position of the text input over the canvas, in CSS pixels.
  const inputStyle = (() => {
    const canvas = canvasRef.current;
    if (!draft || !canvas) return undefined;
    const rect = canvas.getBoundingClientRect();
    const box = containedRect(rect, canvas.width, canvas.height);
    const scale = box.width / canvas.width;
    return {
      left: box.left + draft.x * scale,
      top: box.top + draft.y * scale,
      fontSize: textFontSize(draft.width) * scale,
    };
  })();

  return (
    <div className="snapnote-editor" role="dialog" aria-modal="true">
      <div className="snapnote-editor-toolbar">
        {TOOLS.map(({ tool: t, key, Icon, label }) => (
          <button
            key={t}
            type="button"
            className={`snapnote-btn snapnote-editor-tool ${tool === t ? 'snapnote-btn-primary' : ''}`}
            aria-pressed={tool === t}
            aria-keyshortcuts={key}
            title={`${labels[label]} (${key})`}
            aria-label={labels[label]}
            onClick={() => {
              commitDraft();
              setTool(t);
            }}
          >
            <Icon />
            <kbd className="snapnote-editor-kbd">{key}</kbd>
          </button>
        ))}
        <button
          type="button"
          className="snapnote-btn"
          title={labels.undo}
          aria-label={labels.undo}
          disabled={shapes.length === 0}
          onClick={() => setShapes((prev) => prev.slice(0, -1))}
        >
          <UndoIcon />
        </button>
        <button
          type="button"
          className="snapnote-btn"
          title={labels.clear}
          aria-label={labels.clear}
          disabled={shapes.length === 0}
          onClick={() => setShapes([])}
        >
          <TrashIcon />
        </button>
        <span className="snapnote-spacer" />
        <button
          type="button"
          className="snapnote-btn"
          onClick={onCancel}
        >
          {labels.cancel} (Esc)
        </button>
        <button
          type="button"
          className="snapnote-btn snapnote-btn-primary"
          onClick={finish}
        >
          {labels.done}
        </button>
      </div>
      <div className="snapnote-editor-stage">
        {imageUrl && (
          <img
            ref={imageRef}
            className="snapnote-editor-image"
            src={imageUrl}
            alt=""
            draggable={false}
            onLoad={(event) => {
              const img = event.currentTarget;
              setNaturalSize({
                width: img.naturalWidth,
                height: img.naturalHeight,
              });
            }}
          />
        )}
        {naturalSize.width > 0 && (
          <canvas
            ref={canvasRef}
            className="snapnote-editor-canvas"
            width={naturalSize.width}
            height={naturalSize.height}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
          />
        )}
        {draft && (
          <input
            ref={inputRef}
            className="snapnote-editor-text-input"
            // Position and size depend on the click, so they can't be in the stylesheet.
            style={inputStyle}
            value={draft.value}
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus
            onChange={(event) => {
              const { value } = event.target;
              if (draftRef.current) setDraft({ ...draftRef.current, value });
            }}
            onBlur={commitDraft}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                commitDraft();
              } else if (event.key === 'Escape') {
                event.stopPropagation();
                setDraft(null);
              }
            }}
          />
        )}
      </div>
    </div>
  );
}

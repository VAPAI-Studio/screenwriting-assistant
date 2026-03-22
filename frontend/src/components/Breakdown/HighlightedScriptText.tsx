import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { buildHighlightSegments } from '../../lib/textHighlight';
import { ROUTES, BREAKDOWN_CATEGORIES } from '../../lib/constants';
import type { BreakdownElement } from '../../types';

interface HighlightedScriptTextProps {
  text: string;
  elements: BreakdownElement[];
  projectId: string;
}

export function HighlightedScriptText({ text, elements, projectId }: HighlightedScriptTextProps) {
  const navigate = useNavigate();

  const segments = useMemo(
    () => buildHighlightSegments(text, elements),
    [text, elements],
  );

  return (
    <>
      {segments.map((seg, i) =>
        seg.type === 'text' ? (
          <span key={i}>{seg.content}</span>
        ) : (
          <span
            key={i}
            className={`element-highlight element-highlight--${seg.match!.category}`}
            title={`${seg.match!.elementName} - ${BREAKDOWN_CATEGORIES.find((c) => c.value === seg.match!.category)?.label ?? seg.match!.category}`}
            onClick={(e) => {
              e.stopPropagation();
              window.getSelection()?.removeAllRanges();
              navigate(ROUTES.ELEMENT_DETAIL(projectId, seg.match!.elementId));
            }}
          >
            {seg.content}
          </span>
        ),
      )}
    </>
  );
}

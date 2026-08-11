/** Component for rendering LaTeX mathematical formulas. Uses KaTeX for fast, client-side rendering. */

import React, { useEffect, useRef } from 'react';
import * as katex from 'katex';
import 'katex/dist/katex.min.css';

interface MathFormulaProps {
  latex: string;
  display?: boolean; // Whether to display as block (true) or inline (false)
  errorContainer?: React.ReactNode; // Fallback if rendering fails
}

const MathFormula = ({ latex, display = false, errorContainer }: MathFormulaProps) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef || !latex) return;

    try {
      katex.render(latex, containerRef.current!, {
        throwOnError: true,
        displayMode: display,
        strict: false,
        macros: {
          '\\RR': '\\mathbb{R}',
          '\\ZZ': '\\mathbb{Z}',
          '\\NN': '\\mathbb{N}',
        },
      });
    } catch (err) {
      console.error('Failed to render LaTeX:', err);
      if (errorContainer && containerRef.current) {
        containerRef.current.appendChild(errorContainer as unknown as Node);
      }
    }
  }, [latex, display, errorContainer]);

  if (!latex) return null;

  return (
    <div
      ref={containerRef}
      className={`inline-block ${display ? 'my-4 text-center' : 'inline-block align-middle'}`}
    >
      {/* Render target - content will be injected by KaTeX */}
    </div>
  );
};

export default MathFormula;

/** Syntax-highlighted code block component for displaying code samples with line numbers and language tagging. */

import React from 'react';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';

interface CodeBlockProps {
  language: string;
  code: string;
  highlightLines?: number[]; // Array of 1-based line numbers to highlight
}

const CodeBlock = ({ language, code, highlightLines }: CodeBlockProps) => {
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (ref.current) {
      // Highlight specific lines if provided
      highlightLines?.forEach(lineNum => {
        const lines = ref.current!.querySelectorAll('code > span.line');
        if (lines[lineNum - 1]) {
          lines[lineNum - 1].classList.add('highlighted');
        }
      });
    }
  }, [code, language, highlightLines]);

  const highlightedCode = Prism.highlight(code, Prism.languages[language] || Prism.languages.plaintext, language);

  return (
    <div className="code-block bg-gray-900 text-green-400 rounded-lg overflow-hidden shadow-md">
      <div className="bg-gray-800 px-4 py-2 flex justify-between items-center text-sm font-mono">
        <span>{language.toUpperCase()}</span>
        {highlightLines && (
          <span className="text-yellow-400">
            Lines highlighted: {highlightLines.join(', ')}
          </span>
        )}
      </div>
      <div ref={ref} className="p-4 overflow-x-auto">
        <pre className="m-0">
          <code
            className={`language-${language}`}
            dangerouslySetInnerHTML={{ __html: highlightedCode }}
          />
        </pre>
      </div>
    </div>
  );
};

export default CodeBlock;

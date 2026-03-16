import { useMemo } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { autocompletion } from '@codemirror/autocomplete';
import { ViewPlugin, Decoration, EditorView } from '@codemirror/view';
import type { DecorationSet } from '@codemirror/view';
import type { ViewUpdate } from '@codemirror/view';
import { RangeSetBuilder } from '@codemirror/state';

interface PromptEditorProps {
  value: string;
  onChange: (value: string) => void;
  columns: string[];
  direction?: 'ltr' | 'rtl';
  placeholder?: string;
}

const lightTheme = EditorView.theme({
  '.cm-variable-valid': {
    backgroundColor: 'rgba(59,130,246,0.2)',
    border: '1px solid rgba(59,130,246,0.4)',
    borderRadius: '4px',
    padding: '0 2px',
    color: 'rgb(59,130,246)',
    fontWeight: '500',
  },
  '.cm-variable-invalid': {
    backgroundColor: 'rgba(239,68,68,0.2)',
    border: '1px solid rgba(239,68,68,0.4)',
    borderRadius: '4px',
    padding: '0 2px',
    color: 'rgb(239,68,68)',
  },
  '&': {
    fontSize: '14px',
  },
  '.cm-content': {
    minHeight: '200px',
  },
});

const darkTheme = EditorView.theme(
  {
    '.cm-variable-valid': {
      backgroundColor: 'rgba(96,165,250,0.2)',
      border: '1px solid rgba(96,165,250,0.4)',
      color: 'rgb(147,197,253)',
    },
    '.cm-variable-invalid': {
      backgroundColor: 'rgba(248,113,113,0.2)',
      border: '1px solid rgba(248,113,113,0.4)',
      color: 'rgb(252,165,165)',
    },
  },
  { dark: true }
);

function columnCompletion(columns: string[]) {
  return autocompletion({
    override: [
      (context) => {
        const word = context.matchBefore(/\{[\w]*/);
        if (!word) return null;
        return {
          from: word.from + 1,
          options: columns.map((col) => ({
            label: col,
            type: 'variable',
            apply: col + '}',
          })),
        };
      },
    ],
  });
}

function variableHighlighter(columns: string[]) {
  return ViewPlugin.fromClass(
    class {
      decorations: DecorationSet;

      constructor(view: EditorView) {
        this.decorations = this.buildDecorations(view);
      }

      update(update: ViewUpdate) {
        if (update.docChanged || update.viewportChanged) {
          this.decorations = this.buildDecorations(update.view);
        }
      }

      buildDecorations(view: EditorView) {
        const builder = new RangeSetBuilder<Decoration>();
        const regex = /\{(\w+)\}/g;
        for (const { from, to } of view.visibleRanges) {
          const text = view.state.doc.sliceString(from, to);
          let match;
          while ((match = regex.exec(text)) !== null) {
            const start = from + match.index;
            const end = start + match[0].length;
            const varName = match[1];
            const isValid = columns.includes(varName);
            builder.add(
              start,
              end,
              Decoration.mark({
                class: isValid ? 'cm-variable-valid' : 'cm-variable-invalid',
              })
            );
          }
        }
        return builder.finish();
      }
    },
    { decorations: (v) => v.decorations }
  );
}

export default function PromptEditor({
  value,
  onChange,
  columns,
  direction = 'ltr',
  placeholder = 'Enter your prompt template...',
}: PromptEditorProps) {
  const extensions = useMemo(() => {
    const exts = [
      lightTheme,
      darkTheme,
      columnCompletion(columns),
      variableHighlighter(columns),
      EditorView.lineWrapping,
    ];
    if (direction === 'rtl') {
      exts.push(
        EditorView.theme({
          '.cm-content': { direction: 'rtl', textAlign: 'right' },
          '.cm-line': { direction: 'rtl' },
        })
      );
    }
    return exts;
  }, [columns, direction]);

  return (
    <div className="rounded-md border border-input overflow-hidden">
      <CodeMirror
        value={value}
        onChange={onChange}
        extensions={extensions}
        placeholder={placeholder}
        basicSetup={{
          lineNumbers: false,
          foldGutter: false,
          highlightActiveLine: false,
        }}
        minHeight="200px"
      />
    </div>
  );
}

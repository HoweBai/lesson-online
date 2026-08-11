/** Step component: Outline review and editing */

import React from 'react';

interface OutlineEditorStepProps {
  formData: any;
  updateFormData: (key: string, value: any) => void;
}

export const OutlineEditorStep = ({ formData, updateFormData }: OutlineEditorStepProps) => {
  return (
    <div className="space-y-4">
      <p className="text-gray-600 mb-4">Review the generated outline. You can modify it in the sidebar or confirm as-is:</p>

      <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
        <h4 className="font-semibold mb-2">Generated Course Outline:</h4>
        <div className="text-sm text-gray-700 space-y-2">
          {/* Display the outline content - would normally come from AI response */}
          <p>{formData.outline_content || 'The AI will generate your course outline here after clicking "Next". Once generated, you can edit it using the Claude Chat Sidebar.'}</p>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Select chapters to include initially</label>
        <div className="flex flex-wrap gap-2 mt-2">
          {[1, 2, 3, 4, 5].map(num => (
            <button
              key={num}
              type="button"
              onClick={() => {
                const selected = formData.selected_sections || [];
                const newSelected = selected.includes(num)
                  ? selected.filter((n: number) => n !== num)
                  : [...selected, num];
                updateFormData('selected_sections', newSelected);
              }}
              className={`px-3 py-1 rounded-full text-sm ${
                formData.selected_sections?.includes(num)
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Chapter {num}
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-1">You can continue generating chapters later one by one</p>
      </div>

      <div className="mt-4 p-3 bg-blue-50 rounded-md border border-blue-200">
        <p className="text-sm text-blue-800">
          💡 Tip: Use the Claude Chat Sidebar on the right side of the screen to ask questions or request modifications to the outline!
        </p>
      </div>
    </div>
  );
};

export default OutlineEditorStep;

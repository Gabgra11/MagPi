import { useState } from 'react';
import clsx from 'clsx';

export const ExpandableCard = ({ title, children }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div
      className={clsx(
        'card-gradient rounded-xl shadow-lg border border-white/10',
        'transition-all duration-300 cursor-pointer',
        isExpanded ? 'col-span-2 row-span-2' : ''
      )}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <div className="p-6 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <button
          className="text-gray-500 hover:text-gray-700 text-2xl"
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {isExpanded && (
        <div className="px-6 pb-6 border-t border-white/10 pt-4">
          {children}
        </div>
      )}

      {!isExpanded && (
        <div className="px-6 pb-6">
          {children}
        </div>
      )}
    </div>
  );
};

import clsx from 'clsx';

export const Card = ({ children, className = '', ...props }) => (
  <div
    className={clsx(
      'card-gradient rounded-xl p-6 shadow-lg border border-white/10',
      'transition-all duration-300 hover:shadow-xl',
      className
    )}
    {...props}
  >
    {children}
  </div>
);

export const Badge = ({ children, variant = 'default', className = '' }) => {
  const baseClasses = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold';
  const variants = {
    default: 'bg-blue-100 text-blue-800',
    gold: 'bg-teal-600 text-white',
    silver: 'bg-gray-200 text-gray-800',
    bronze: 'bg-orange-100 text-orange-800',
    success: 'bg-green-100 text-green-800',
  };

  return (
    <span className={clsx(baseClasses, variants[variant], className)}>
      {children}
    </span>
  );
};

export const Stat = ({ label, value, trend = null }) => (
  <div className="p-4">
    <div className="flex items-center justify-between mb-2">
      <span className="text-gray-600 text-sm font-medium">{label}</span>
    </div>
    <div className="flex items-baseline gap-2">
      <span className="text-3xl font-bold text-gray-900">{value}</span>
      {trend && <span className={trend > 0 ? 'text-green-600' : 'text-red-600'}>{trend}%</span>}
    </div>
  </div>
);

export const LoadingSpinner = () => (
  <div className="flex justify-center items-center h-40">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500"></div>
  </div>
);

export const ErrorAlert = ({ message }) => (
  <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
    <p className="font-semibold">Error</p>
    <p className="text-sm">{message}</p>
  </div>
);

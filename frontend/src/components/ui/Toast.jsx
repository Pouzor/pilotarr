import React, { useEffect } from "react";
import { cn } from "../../utils/cn";
import Icon from "../AppIcon";

const VARIANTS = {
  success: {
    container: "bg-success/10 border-success/30 text-success",
    icon: "CheckCircle",
  },
  error: {
    container: "bg-error/10 border-error/30 text-error",
    icon: "XCircle",
  },
  info: {
    container: "bg-primary/10 border-primary/30 text-primary",
    icon: "Info",
  },
};

const Toast = ({ message, variant = "success", duration = 4000, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const { container, icon } = VARIANTS[variant] ?? VARIANTS.info;

  return (
    <div
      className={cn(
        "fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg border shadow-elevation-3 max-w-sm",
        "animate-in slide-in-from-bottom-4 fade-in duration-200",
        container,
      )}
    >
      <Icon name={icon} size={18} className="flex-shrink-0" />
      <p className="text-sm font-medium">{message}</p>
      <button onClick={onClose} className="ml-auto flex-shrink-0 opacity-70 hover:opacity-100">
        <Icon name="X" size={14} />
      </button>
    </div>
  );
};

export default Toast;

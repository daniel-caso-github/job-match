interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
}

export default function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  disabled = false,
}: SegmentedControlProps<T>) {
  return (
    <div
      className={`flex gap-1 p-1 bg-panel border border-line-2 rounded-[11px] ${
        disabled ? "opacity-60" : ""
      }`}
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          disabled={disabled}
          onClick={() => onChange(opt.value)}
          className={`h-8 px-3.5 flex-1 rounded-lg text-sm transition-colors ${
            value === opt.value
              ? "bg-accent text-accent-ink font-semibold"
              : "text-sub font-medium"
          } ${disabled ? "cursor-not-allowed" : ""}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

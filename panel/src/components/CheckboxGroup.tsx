export type CheckboxOption = { id: string; label: string };

/** Multi-select list of checkboxes. Used where a record links to several others. */
export function CheckboxGroup({
  id,
  label,
  options,
  value,
  onChange,
  isLoading = false,
  isError = false,
  emptyHint,
  errorHint = "Could not load options.",
}: {
  id: string;
  label?: string;
  options: CheckboxOption[];
  value: string[];
  onChange: (ids: string[]) => void;
  isLoading?: boolean;
  isError?: boolean;
  emptyHint: string;
  errorHint?: string;
}) {
  function toggle(optionId: string) {
    onChange(
      value.includes(optionId) ? value.filter((item) => item !== optionId) : [...value, optionId],
    );
  }

  return (
    <fieldset>
      {label ? (
        <legend className="mb-1 block text-sm font-medium text-slate-700">{label}</legend>
      ) : null}
      {isLoading ? <p className="text-xs text-slate-500">Loading…</p> : null}
      {isError ? <p className="text-xs text-red-700">{errorHint}</p> : null}
      {!isLoading && !isError && options.length === 0 ? (
        <p className="text-xs text-slate-500">{emptyHint}</p>
      ) : null}
      {options.length > 0 ? (
        <div
          id={id}
          className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-slate-300 p-2"
        >
          {options.map((option) => (
            <label key={option.id} className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-teal-700"
                checked={value.includes(option.id)}
                onChange={() => toggle(option.id)}
              />
              <span className="truncate">{option.label}</span>
            </label>
          ))}
        </div>
      ) : null}
      {value.length > 0 ? (
        <p className="mt-1 text-xs text-slate-500">{value.length} selected</p>
      ) : null}
    </fieldset>
  );
}

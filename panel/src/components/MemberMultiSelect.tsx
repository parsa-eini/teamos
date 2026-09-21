import { useOrganizationMembers } from "@/hooks/useOrganizationMembers";
import { displayName } from "@/lib/format";

export function MemberMultiSelect({
  id,
  label,
  value,
  onChange,
  emptyHint = "No people available. Add members on the organization members page.",
  excludeIds = [],
}: {
  id: string;
  label?: string;
  value: string[];
  onChange: (userIds: string[]) => void;
  emptyHint?: string;
  excludeIds?: string[];
}) {
  const query = useOrganizationMembers();
  const options = (query.data?.data ?? []).filter((member) => !excludeIds.includes(member.user_id));

  function toggle(userId: string) {
    onChange(
      value.includes(userId) ? value.filter((id) => id !== userId) : [...value, userId],
    );
  }

  return (
    <fieldset>
      {label ? (
        <legend className="mb-1 block text-sm font-medium text-slate-700">{label}</legend>
      ) : null}
      {query.isLoading ? <p className="text-xs text-slate-500">Loading people…</p> : null}
      {query.isError ? (
        <p className="text-xs text-red-700">Could not load organization members.</p>
      ) : null}
      {!query.isLoading && !query.isError && options.length === 0 ? (
        <p className="text-xs text-slate-500">{emptyHint}</p>
      ) : null}
      {options.length > 0 ? (
        <div
          id={id}
          className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-slate-300 p-2"
        >
          {options.map((member) => (
            <label
              key={member.user_id}
              className="flex items-center gap-2 text-sm text-slate-700"
            >
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-teal-700"
                checked={value.includes(member.user_id)}
                onChange={() => toggle(member.user_id)}
              />
              <span className="truncate">
                {displayName(member.first_name, member.last_name)} ({member.email})
              </span>
            </label>
          ))}
        </div>
      ) : null}
      {value.length > 0 ? (
        <p className="mt-1 text-xs text-slate-500">
          {value.length} selected
        </p>
      ) : null}
    </fieldset>
  );
}

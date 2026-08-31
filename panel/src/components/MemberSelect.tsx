import { Label, Select } from "@/components/ui";
import { useOrganizationMembers } from "@/hooks/useOrganizationMembers";
import { displayName } from "@/lib/format";

export function MemberSelect({
  id,
  label,
  value,
  onChange,
  allowEmpty = false,
  emptyLabel = "None",
  excludeIds = [],
}: {
  id: string;
  label?: string;
  value: string;
  onChange: (userId: string) => void;
  allowEmpty?: boolean;
  emptyLabel?: string;
  excludeIds?: string[];
}) {
  const query = useOrganizationMembers();
  const options = (query.data?.data ?? []).filter((member) => !excludeIds.includes(member.user_id));

  return (
    <div>
      {label ? <Label htmlFor={id}>{label}</Label> : null}
      <Select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={query.isLoading}
      >
        <option value="">{query.isLoading ? "Loading people…" : emptyLabel}</option>
        {options.map((member) => (
          <option key={member.user_id} value={member.user_id}>
            {displayName(member.first_name, member.last_name)} ({member.email})
          </option>
        ))}
      </Select>
      {query.isError ? (
        <p className="mt-1 text-xs text-red-700">Could not load organization members.</p>
      ) : null}
      {!query.isLoading && !query.isError && options.length === 0 && !allowEmpty ? (
        <p className="mt-1 text-xs text-slate-500">
          No people available. Add members on the organization members page.
        </p>
      ) : null}
    </div>
  );
}

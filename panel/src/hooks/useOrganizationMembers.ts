import { useQuery } from "@tanstack/react-query";

import { listOrganizationMembers } from "@/services/organizations";
import type { OrganizationMember } from "@/types/api";
import { displayName } from "@/lib/format";

export const organizationMembersQueryKey = ["organizations", "members"] as const;

export function useOrganizationMembers() {
  return useQuery({
    queryKey: organizationMembersQueryKey,
    queryFn: () => listOrganizationMembers({ page: 1, page_size: 100 }),
  });
}

export function memberById(
  members: OrganizationMember[] | undefined,
  userId: string,
): OrganizationMember | undefined {
  return members?.find((member) => member.user_id === userId);
}

export function personName(
  members: OrganizationMember[] | undefined,
  userId: string,
  fallback = "Unknown",
): string {
  const member = memberById(members, userId);
  return member ? displayName(member.first_name, member.last_name) : fallback;
}

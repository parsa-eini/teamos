import { apiRequest, toQuery } from "@/lib/api";
import type {
  CollectionResponse,
  DataResponse,
  ListParams,
  Organization,
  OrganizationMember,
  OrganizationRole,
} from "@/types/api";

export async function getCurrentOrganization(): Promise<Organization> {
  const response = await apiRequest<DataResponse<Organization>>("/organizations/current");
  return response.data;
}

export async function updateCurrentOrganization(payload: {
  name?: string;
  slug?: string;
}): Promise<Organization> {
  const response = await apiRequest<DataResponse<Organization>>("/organizations/current", {
    method: "PATCH",
    body: payload,
  });
  return response.data;
}

export async function listOrganizationMembers(
  params: ListParams = {},
): Promise<CollectionResponse<OrganizationMember>> {
  return apiRequest(`/organizations/current/members${toQuery(params)}`);
}

export async function createOrganizationMember(payload: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role?: OrganizationRole;
}): Promise<OrganizationMember> {
  const response = await apiRequest<DataResponse<OrganizationMember>>(
    "/organizations/current/members",
    { method: "POST", body: payload },
  );
  return response.data;
}

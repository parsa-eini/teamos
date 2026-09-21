import { apiRequest, toQuery } from "@/lib/api";
import type {
  CollectionResponse,
  DataResponse,
  Feedback,
  FeedbackSentiment,
  ListParams,
} from "@/types/api";

export type FeedbackListParams = ListParams & {
  subject_id?: string;
  sentiment?: FeedbackSentiment | "";
};

export async function listFeedback(
  params: FeedbackListParams = {},
): Promise<CollectionResponse<Feedback>> {
  return apiRequest(`/feedback${toQuery(params)}`);
}

export async function createFeedback(payload: {
  subject_id: string;
  sentiment: FeedbackSentiment;
  body: string;
}): Promise<Feedback> {
  const response = await apiRequest<DataResponse<Feedback>>("/feedback", {
    method: "POST",
    body: payload,
  });
  return response.data;
}

export async function deleteFeedback(feedbackId: string): Promise<void> {
  await apiRequest(`/feedback/${feedbackId}`, { method: "DELETE" });
}

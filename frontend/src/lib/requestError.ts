export interface RequestErrorPresentation {
  message: string;
  detail: string;
}

/**
 * Maps transport and API failures to a safe, recoverable user-facing action.
 * Raw details remain available to callers for diagnostics but are never the
 * primary message shown in the workspace.
 */
export function describeRequestError(
  error: unknown,
  fallback: string,
  language: "en" | "vi" = "en",
): RequestErrorPresentation {
  const detail = error instanceof Error ? error.message : String(error);
  const candidateStatus =
    error && typeof error === "object" && "status" in error
      ? (error as { status?: unknown }).status
      : null;
  const status = typeof candidateStatus === "number" ? candidateStatus : null;
  const candidateCode =
    error && typeof error === "object" && "code" in error
      ? (error as { code?: unknown }).code
      : null;
  const code = typeof candidateCode === "string" ? candidateCode : null;

  const vi = language === "vi";
  if (status === 429) {
    return code === "client_rate_limited"
      ? { message: vi ? "Có quá nhiều yêu cầu từ thiết bị này. Hãy chờ rồi thử lại." : "Too many requests from this client. Please wait and try again.", detail }
      : { message: vi ? "Provider tạm thời hết quota. Hãy chờ và thử lại sau." : "The provider is temporarily out of quota. Please wait and try again later.", detail };
  }
  if (status === 408 || status === 504) {
    return { message: vi ? "Yêu cầu đã hết thời gian chờ. Hãy thu hẹp câu hỏi hoặc thử lại." : "The request timed out. Try a narrower question or try again.", detail };
  }
  if (status !== null && status >= 500) {
    return { message: vi ? "Dịch vụ nghiên cứu tạm thời không khả dụng. Hãy thử lại." : "The research service is temporarily unavailable. Please try again.", detail };
  }
  if (error instanceof TypeError) {
    return { message: vi ? "Không thể kết nối backend. Hãy kiểm tra kết nối và thử lại." : "The backend could not be reached. Check the connection and try again.", detail };
  }
  return { message: fallback, detail };
}

import { ConversationRecord } from "./conversationStore";

function escapeMarkdown(value: string): string {
  return value.replace(/\r\n/g, "\n").trim();
}
export function conversationToMarkdown(conversation: ConversationRecord): string {
  const lines = [
    `# ${escapeMarkdown(conversation.title)}`,
    "",
    `Exported: ${new Date(conversation.updatedAt).toISOString()}`,
    "Stored locally on this device.",
    "",
  ];

  const messages = conversation.messages;
  let question = "";
  for (const message of messages) {
    if (message.sender === "user") {
      question = message.text;
      continue;
    }
    if (!message.text) continue;

    lines.push("## Question", "", escapeMarkdown(question || "Question unavailable"), "");
    lines.push("## Answer", "", escapeMarkdown(message.text), "");
    if (message.status === "stopped" || message.status === "error") {
      lines.push(
        `> Status: ${message.status === "stopped" ? "partial answer; generation stopped" : "answer ended with an error"}.`,
        "",
      );
    }
    if (message.requestSnapshot) {
      const snapshot = message.requestSnapshot;
      lines.push(
        "### Request scope",
        "",
        `- Company: ${snapshot.ticker || "All companies"}`,
        `- Section: ${snapshot.section || "All sections"}`,
        `- Context breadth: ${snapshot.topK}`,
        "",
      );
    }
    if (message.sources?.length) {
      lines.push("### Retrieved filing evidence", "");
      message.sources.forEach((source, index) => {
        lines.push(
          `#### [Source ${index + 1}] ${escapeMarkdown(source.citation)}`,
          "",
          `Rank score: ${source.score}`,
          "",
          escapeMarkdown(source.text || source.text_preview),
          "",
        );
      });
    }
  }

  return `${lines.join("\n").trim()}\n`;
}

export function downloadConversationMarkdown(conversation: ConversationRecord): void {
  const blob = new Blob([conversationToMarkdown(conversation)], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${conversation.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "conversation"}.md`;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

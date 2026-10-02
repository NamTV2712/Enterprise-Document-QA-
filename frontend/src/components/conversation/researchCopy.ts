export const researchCopy = {
  en: {
    mode: "Research mode", quick: "Quick", deep: "Deep Research", quickHint: "Ask a filing question with the existing RAG pipeline.",
    deepHint: "Only this explicit goal is sent to the Agent. Quick filters and previous answers are not passed as hidden context.",
    connect: "Connect local workspace", reconnect: "Reconnect to read this run", disconnected: "This run is saved as a reference. Reconnect to read its current state and result.",
    consent: "Allow bounded decision-provider calls for this run", send: "Start Deep Research", deeper: "Research deeper", details: "Research details", fullRun: "Open full run",
    providerUnavailable: "No decision provider is configured. A new run will record that it is unavailable; it will not produce an answer.",
    readOnly: "This workspace does not permit creating runs.", error: "The run could not be created or linked. Your draft is retained. Check the Agent inspector before submitting again.",
    unavailable: "This run is unavailable. Its conversation reference is retained.", summary: "Research summary", genericSummary: "This run uses a generic goal. No structured objective coverage or gap report is available.", sourceUnavailable: "This evidence cannot be opened in the document reader.", close: "Close connection",
  },
  vi: {
    mode: "Chế độ nghiên cứu", quick: "Nhanh", deep: "Nghiên cứu sâu", quickHint: "Hỏi về hồ sơ bằng pipeline RAG hiện có.",
    deepHint: "Chỉ mục tiêu này được gửi cho Agent. Bộ lọc Nhanh và câu trả lời trước không được truyền làm ngữ cảnh ẩn.",
    connect: "Kết nối workspace cục bộ", reconnect: "Kết nối lại để đọc lần chạy", disconnected: "Hội thoại chỉ lưu tham chiếu lần chạy. Kết nối lại để đọc trạng thái và kết quả hiện tại.",
    consent: "Cho phép gọi provider quyết định có giới hạn cho lần chạy này", send: "Bắt đầu nghiên cứu sâu", deeper: "Nghiên cứu sâu hơn", details: "Chi tiết nghiên cứu", fullRun: "Mở toàn bộ lần chạy",
    providerUnavailable: "Chưa cấu hình provider quyết định. Lần chạy mới sẽ ghi nhận không khả dụng và không tạo câu trả lời.",
    readOnly: "Workspace này không cho phép tạo lần chạy.", error: "Không thể tạo hoặc liên kết lần chạy. Bản nháp được giữ lại. Kiểm tra không gian Agent trước khi gửi lại.",
    unavailable: "Lần chạy này không khả dụng. Tham chiếu trong hội thoại được giữ lại.", summary: "Tóm tắt nghiên cứu", genericSummary: "Lần chạy dùng mục tiêu thông thường. Không có báo cáo độ phủ hay khoảng trống theo mục tiêu có cấu trúc.", sourceUnavailable: "Không thể mở bằng chứng này trong trình đọc tài liệu.", close: "Đóng kết nối",
  },
} as const;

# Lời nói đầu

Từ cuối năm 2022, các mô hình ngôn ngữ lớn (Large Language Model, LLM) mà đại diện là ChatGPT đã như một cơn sóng thần công nghệ, thay đổi hoàn toàn cách chúng ta tương tác với trí tuệ nhân tạo. Năng lực hiểu và sinh ngôn ngữ tự nhiên mạnh mẽ của LLM đã cho chúng ta thấy tia sáng trên con đường dẫn tới trí tuệ nhân tạo tổng quát (AGI). Tuy nhiên, khi sự kinh ngạc ban đầu lắng xuống, các nhà phát triển bắt đầu khám phá biên giới tiếp theo: làm thế nào để AI không chỉ là một công cụ “hỏi gì đáp nấy”, mà trở thành một “người hành động” có thể tự chủ lập kế hoạch, gọi công cụ và giải quyết các vấn đề phức tạp?

Câu trả lời chính là Agent.

Nếu năm 2024 là năm đầu tiên của “cuộc chiến trăm mô hình”, thì năm 2025 chắc chắn đã mở ra “Năm của Agent”. Chúng ta thấy trọng tâm công nghệ đang chuyển từ huấn luyện những mô hình nền tảng lớn hơn, mạnh hơn sang xây dựng những ứng dụng Agent thông minh hơn, hiệu quả hơn. Một Agent đơn lẻ đã có thể đảm nhận các nhiệm vụ trong những lĩnh vực cụ thể, còn hệ thống đa Agent (Multi-Agent System, MAS), nơi nhiều Agent phân công, cộng tác, thậm chí tranh luận để cùng hoàn thành một mục tiêu lớn, được xem là chìa khóa để giải phóng toàn bộ tiềm năng của LLM và giải quyết những vấn đề phức tạp trong thế giới thực.

Tuy nhiên, hệ sinh thái hiện nay tồn tại một khoảng trống rõ rệt: một mặt là các framework và ứng dụng Agent xuất hiện liên tục, khiến người ta hoa mắt; mặt khác là kiến thức có hệ thống lại cực kỳ khan hiếm. Phần lớn các hướng dẫn chỉ tập trung vào việc gọi API của một framework cụ thể, khiến người học thường “biết làm mà không biết vì sao”, và vẫn cảm thấy bất lực khi đối mặt với những yêu cầu phức tạp. Chúng ta thiếu một cuốn hướng dẫn thực chiến có thể xuyên qua lớp vỏ của framework, bắt đầu từ những nguyên lý đầu tiên, giải thích một cách hệ thống việc thiết kế, xây dựng và cộng tác của Agent.

Trước thực trạng đó, chúng tôi khởi động dự án Hello-Agents, mong muốn mang đến cho cộng đồng một cuốn hướng dẫn xây dựng hệ thống Agent từ con số 0, coi trọng cả lý thuyết lẫn thực chiến. Chúng tôi không chỉ đưa bạn tới những công nghệ tiên tiến nhất trong lĩnh vực Agent, mà còn dẫn dắt bạn đi sâu vào kiến trúc cốt lõi, hiểu các mô hình kinh điển, và cuối cùng tự tay xây dựng ứng dụng đa Agent của riêng mình.

Chúng tôi tin rằng cách học tốt nhất là thực hành. Mong rằng cuốn hướng dẫn này sẽ trở thành điểm khởi đầu để bạn khám phá thế giới Agent, giúp bạn chuyển mình từ một “người dùng” mô hình ngôn ngữ lớn thành một “người xây dựng” hệ thống Agent.

## Gợi ý dành cho độc giả

Chào mừng bạn, người xây dựng hệ thống thông minh của tương lai! Trước khi bắt đầu hành trình thú vị này, hãy để chúng tôi đưa ra một vài gợi ý nhỏ.

Trước khi đọc dự án, chúng tôi mong bạn:

- Có năng lực lập trình Python cơ bản.

- Có hiểu biết khái niệm cơ bản về mô hình ngôn ngữ lớn (ví dụ: biết cách lấy API của LLM).

- Hãy yên tâm, bạn không cần có nền tảng sâu về thuật toán hay huấn luyện mô hình; trọng tâm của dự án là ứng dụng và xây dựng.

Dự án được chia thành năm phần, bao quát từ cơ bản đến thực chiến, tiến bước tuần tự, các phần gắn kết chặt chẽ với nhau:

Phần một (Nền tảng): Chúng tôi sẽ đặt nền móng kiến thức cốt lõi về trí tuệ nhân tạo và LLM, giúp bạn có cái nhìn tổng quan về bối cảnh ra đời của Agent.

Phần hai (Agent đơn lẻ): Đây là khởi đầu cho thực hành của bạn. Chúng tôi sẽ đưa bạn xây dựng từ con số 0 một Agent đơn lẻ đầy đủ chức năng, hiểu sâu cấu trúc “tinh thần” bên trong của nó.

Phần ba (Nâng cao): Ở đây, Agent của bạn sẽ “học” cách suy nghĩ, có bộ nhớ và công cụ, nắm vững giao thức giao tiếp giữa các Agent, và cuối cùng hoàn thành vòng lặp đánh giá khép kín.

Phần bốn (Thực chiến): Đây là nơi chứa giá trị cốt lõi của dự án. Bạn sẽ vận dụng tổng hợp kiến thức đã học thông qua một loạt ca tổng hợp được thiết kế kỹ lưỡng, rèn vàng thật trong thực chiến.

Phần năm (Triển vọng): Điểm cuối của hành trình là một khởi đầu mới. Bạn sẽ tự tay tạo ra “tác phẩm tốt nghiệp” của riêng mình, đặt dấu chấm tròn đầy đủ cho hành trình học tập.

“Trên giấy học được vẫn còn nông cạn, muốn biết rõ việc ắt phải thực hành.” Để đạt hiệu quả học tập tốt nhất, chúng tôi cung cấp toàn bộ mã nguồn đi kèm trong thư mục `code` của dự án, và rất khuyến khích bạn kết hợp lý thuyết với thực hành. Hãy nhất định tự tay chạy, gỡ lỗi và thậm chí sửa đổi từng đoạn mã được cung cấp trong dự án. Chúng tôi khuyến khích bạn suy rộng và vận dụng những công nghệ đã học vào những tình huống thực tế mà bạn quan tâm — đó mới là mục đích cuối cùng của việc học.

Cuối cùng, với tư cách là một dự án mã nguồn mở, chúng tôi nhiệt liệt hoan nghênh sự tham gia và đóng góp của bạn. Khi gặp vấn đề, bạn có thể đặt câu hỏi trong cộng đồng của chúng tôi; khi có ý tưởng hoặc phát hiện mới, bạn cũng luôn được chào đón tham gia vào quá trình cùng xây dựng dự án.

Cảm ơn bạn đã chọn đọc Hello-Agents, chúc bạn học tập vui vẻ, khám phá không giới hạn!

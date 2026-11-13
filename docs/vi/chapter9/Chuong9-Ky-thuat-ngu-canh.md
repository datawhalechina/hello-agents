# Chương 9: Kỹ thuật ngữ cảnh

Ở các chương trước, chúng ta đã đưa hệ thống bộ nhớ và RAG vào Agent. Tuy nhiên, để Agent có thể "suy nghĩ" và "hành động" một cách ổn định trong những kịch bản phức tạp của thực tế, chỉ có bộ nhớ và truy xuất là chưa đủ — chúng ta cần một bộ phương pháp kỹ thuật để liên tục và có hệ thống xây dựng "ngữ cảnh" phù hợp cho mô hình. Đó chính là chủ đề của chương này: kỹ thuật ngữ cảnh (Context Engineering). Nó quan tâm đến câu hỏi "trước mỗi lần gọi mô hình, làm thế nào lắp ghép và tối ưu ngữ cảnh đầu vào theo cách có thể tái sử dụng, có thể đo lường và có thể tiến hóa", từ đó nâng cao tính đúng đắn, tính bền vững và hiệu quả<sup>[1][2]</sup>.

Để bạn đọc có thể nhanh chóng trải nghiệm đầy đủ chức năng của chương này, chúng tôi cung cấp một gói Python có thể cài đặt trực tiếp. Bạn có thể cài đặt phiên bản tương ứng của chương này bằng lệnh sau:

```bash
pip install "hello-agents[all]==0.2.8"
```

Chương này chủ yếu giới thiệu khái niệm cốt lõi và thực hành của kỹ thuật ngữ cảnh, đồng thời bổ sung vào framework HelloAgents một trình xây dựng ngữ cảnh và hai công cụ đi kèm:

- **ContextBuilder** (`hello_agents/context/builder.py`): trình xây dựng ngữ cảnh, hiện thực quy trình GSSC (Gather-Select-Structure-Compress), cung cấp giao diện quản lý ngữ cảnh thống nhất
- **NoteTool** (`hello_agents/tools/builtin/note_tool.py`): công cụ ghi chú có cấu trúc, hỗ trợ Agent quản lý bộ nhớ lưu trữ bền vững
- **TerminalTool** (`hello_agents/tools/builtin/terminal_tool.py`): công cụ terminal, hỗ trợ Agent thao tác trên hệ thống tệp và truy xuất ngữ cảnh tức thời

Các thành phần này cùng nhau tạo thành một giải pháp kỹ thuật ngữ cảnh hoàn chỉnh, là chìa khóa để hiện thực quản lý nhiệm vụ dài hạn và tìm kiếm dạng Agent, sẽ được giới thiệu chi tiết trong các chương sau.

Ngoài việc cài đặt framework, bạn còn cần cấu hình API của LLM trong `.env`. Các ví dụ trong chương này chủ yếu dùng mô hình ngôn ngữ lớn để quản lý ngữ cảnh và ra quyết định thông minh.

Sau khi cấu hình xong, bạn có thể bắt đầu hành trình học của chương này!



## 9.1 Kỹ thuật ngữ cảnh là gì

Sau nhiều năm kỹ thuật prompt (Prompt Engineering) trở thành tâm điểm của AI ứng dụng, một thuật ngữ mới bắt đầu bước ra sân khấu: <strong>kỹ thuật ngữ cảnh (Context Engineering)</strong>. Ngày nay, xây dựng hệ thống bằng mô hình ngôn ngữ không còn chỉ là tìm đúng cấu trúc câu và cách diễn đạt trong prompt, mà là trả lời một câu hỏi vĩ mô hơn: <strong>cấu hình ngữ cảnh như thế nào thì mô hình có khả năng cao nhất tạo ra hành vi mà chúng ta mong muốn?</strong>

"Ngữ cảnh" ở đây chỉ tập hợp các token được đưa vào khi lấy mẫu từ mô hình ngôn ngữ lớn (LLM). Bài toán kỹ thuật trước mắt là, dưới những ràng buộc cố hữu của LLM, <strong>tối ưu hóa tính hữu dụng của các token này</strong> để có thể ổn định đạt được kết quả mong đợi. Muốn điều khiển LLM một cách hiệu quả, thường cần "suy nghĩ trong ngữ cảnh" — nghĩa là: ở mỗi lần gọi, đều phải xem xét toàn bộ trạng thái mà LLM có thể thấy, và dự đoán những hành vi mà trạng thái đó có thể gợi ra.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/9-figures/9-1.webp" alt="" width="85%"/>
  <p>Hình 9.1 Kỹ thuật prompt so với kỹ thuật ngữ cảnh</p>
</div>

Mục này sẽ thảo luận về kỹ thuật ngữ cảnh đang nổi lên, và đưa ra một mô hình tư duy tinh gọn để xây dựng những Agent <strong>có thể điều khiển và hiệu quả</strong>.

<strong>Kỹ thuật ngữ cảnh so với kỹ thuật prompt</strong>

Như Hình 9.1 cho thấy, dưới góc nhìn của các nhà cung cấp mô hình tiên phong hiện nay, kỹ thuật ngữ cảnh là bước tiến tự nhiên của kỹ thuật prompt. Kỹ thuật prompt quan tâm đến cách viết và tổ chức chỉ dẫn cho LLM để có kết quả tốt hơn (ví dụ cách viết system prompt và chiến lược cấu trúc hóa); còn kỹ thuật ngữ cảnh là <strong>ở giai đoạn suy luận, làm thế nào tuyển chọn và duy trì "tập thông tin tối ưu (các token)"</strong>, trong đó không chỉ có bản thân prompt mà còn tất cả thông tin khác sẽ đi vào cửa sổ ngữ cảnh.

Trong giai đoạn đầu của kỹ thuật LLM, prompt thường là công việc chính, bởi phần lớn trường hợp sử dụng (ngoài trò chuyện thường ngày) đều cần tối ưu prompt theo kiểu tinh chỉnh cho phân loại đơn lượt hoặc sinh văn bản. Đúng như tên gọi, cốt lõi của kỹ thuật prompt là "làm thế nào viết một prompt hiệu quả", đặc biệt là system prompt. Tuy nhiên, khi chúng ta bắt đầu xây dựng các Agent mạnh hơn một cách có hệ thống, chúng làm việc trong khoảng thời gian dài hơn, qua nhiều vòng suy luận, thì chúng ta cần những chiến lược có thể quản lý <strong>toàn bộ trạng thái ngữ cảnh</strong> — bao gồm chỉ dẫn hệ thống, công cụ, MCP (Model Context Protocol), dữ liệu bên ngoài, lịch sử tin nhắn, v.v.

Một Agent chạy theo vòng lặp sẽ liên tục sinh ra dữ liệu có thể liên quan đến vòng suy luận tiếp theo, và những thông tin này phải được <strong>tinh lọc định kỳ</strong>. Vì vậy, "nghệ thuật và kỹ thuật" của kỹ thuật ngữ cảnh nằm ở chỗ, từ "vũ trụ thông tin ứng viên" không ngừng mở rộng, <strong>phân định xem nội dung nào nên đi vào cửa sổ ngữ cảnh hữu hạn</strong>.

## 9.2 Vì sao kỹ thuật ngữ cảnh quan trọng

Dù mô hình ngày càng nhanh, quy mô dữ liệu có thể xử lý ngày càng lớn, chúng ta vẫn quan sát thấy: LLM cũng giống con người, đến một điểm nào đó sẽ "mất tập trung" hoặc "hỗn loạn". Các benchmark kiểu tìm kim trong đống cỏ (needle-in-a-haystack) đã hé lộ một hiện tượng: <strong>sự ăn mòn ngữ cảnh (context rot)</strong> — khi số token trong cửa sổ ngữ cảnh tăng lên, khả năng mô hình ghi nhớ chính xác thông tin từ ngữ cảnh lại giảm đi.

Đường cong suy giảm ở các mô hình khác nhau có thể mượt hơn, nhưng đặc điểm này xuất hiện gần như ở mọi mô hình. Vì vậy, <strong>ngữ cảnh phải được coi là một tài nguyên hữu hạn, và có lợi ích biên giảm dần</strong>. Giống như con người có dung lượng bộ nhớ làm việc hữu hạn, LLM cũng có một "ngân sách chú ý". Mỗi token thêm vào đều tiêu tốn một phần ngân sách này, nên chúng ta càng cần cẩn trọng sàng lọc những token nào nên được cung cấp cho LLM.

Sự khan hiếm này không phải ngẫu nhiên, mà bắt nguồn từ ràng buộc kiến trúc của LLM. Transformer cho phép mỗi token thiết lập liên kết với <strong>toàn bộ</strong> token trong ngữ cảnh, về mặt lý thuyết tạo ra quan hệ chú ý từng cặp ở mức \(n^2\). Khi độ dài ngữ cảnh tăng lên, năng lực mô hình hóa các quan hệ từng cặp này bị "kéo mỏng", từ đó tự nhiên sinh ra sự căng thẳng giữa "quy mô ngữ cảnh" và "độ tập trung chú ý". Ngoài ra, mẫu chú ý của mô hình bắt nguồn từ phân phối dữ liệu huấn luyện — chuỗi ngắn thường phổ biến hơn chuỗi dài, nên mô hình có ít kinh nghiệm hơn và ít tham số chuyên dụng hơn cho "phụ thuộc toàn ngữ cảnh".

Các kỹ thuật như nội suy mã hóa vị trí (position encoding interpolation) có thể giúp mô hình "thích ứng" với chuỗi dài hơn giai đoạn huấn luyện khi suy luận, nhưng phải hy sinh một phần hiểu biết chính xác về vị trí token. Nhìn chung, các yếu tố này cùng nhau tạo thành một <strong>gradient hiệu năng</strong>, chứ không phải sụp đổ kiểu "vách đá": mô hình vẫn mạnh với ngữ cảnh dài, nhưng so với ngữ cảnh ngắn, độ chính xác trong truy xuất thông tin và suy luận đường dài sẽ giảm đi.

Dựa trên thực tế đó, <strong>kỹ thuật ngữ cảnh có ý thức</strong> trở thành thứ thiết yếu để xây dựng những Agent vững chắc.

### 9.2.1 "Giải phẫu học" của một ngữ cảnh hiệu quả

Dưới ràng buộc của "ngân sách chú ý hữu hạn", mục tiêu của kỹ thuật ngữ cảnh tốt là: <strong>dùng càng ít token nhưng có mật độ tín hiệu cao càng tốt, để tối đa hóa xác suất đạt kết quả mong đợi</strong>. Khi đi vào thực hành, chúng tôi khuyến nghị xây dựng có hệ thống quanh các thành phần sau:

- <strong>System prompt</strong>: ngôn ngữ rõ ràng, trực tiếp, mức độ thông tin giữ ở độ cao "vừa đủ". Hai thái cực sai lầm thường gặp:
  - Mã hóa cứng quá mức: viết vào prompt những logic if-else phức tạp, dễ vỡ, chi phí bảo trì dài hạn cao.
  - Quá chung chung: chỉ đưa ra mục tiêu vĩ mô và chỉ dẫn tổng quát, thiếu <strong>tín hiệu cụ thể</strong> về đầu ra mong đợi hoặc giả định sai về "ngữ cảnh chia sẻ".
  Khuyến nghị tổ chức prompt theo phân vùng (như <background_information>, <instructions>, chỉ dẫn công cụ, mô tả đầu ra, v.v.), dùng XML/Markdown để phân tách. Dù định dạng thế nào, đích đến vẫn là <strong>"tập thông tin tối thiểu cần thiết" có thể phác họa đầy đủ hành vi mong đợi</strong> ("tối thiểu" không đồng nghĩa với "ngắn nhất"). Trước tiên hãy dùng mô hình tốt nhất chạy thử trên prompt tối thiểu, rồi bổ sung chỉ dẫn và ví dụ rõ ràng dựa trên các mẫu thất bại.

- <strong>Công cụ</strong>: công cụ định nghĩa khế ước giữa Agent với không gian thông tin/hành động, phải thúc đẩy hiệu quả: vừa trả về thông tin <strong>thân thiện với token</strong>, vừa khuyến khích hành vi Agent hiệu quả. Công cụ nên:
  - Có trách nhiệm đơn nhất, ít chồng lấn với nhau, ngữ nghĩa giao diện rõ ràng;
  - Bền vững với lỗi;
  - Mô tả tham số đầu vào rõ ràng, không mơ hồ, phát huy đầy đủ năng lực diễn đạt và suy luận mà mô hình giỏi.
  Mẫu thất bại thường gặp là "bộ công cụ phình to": ranh giới chức năng mờ nhạt, khiến quyết định "chọn công cụ nào" trở nên mơ hồ ngay từ đầu. <strong>Nếu kỹ sư con người còn không chắc nên dùng công cụ nào, đừng mong Agent làm tốt hơn</strong>. Việc chọn lọc kỹ lưỡng một "bộ công cụ khả thi tối thiểu (MVTS)" thường nâng cao rõ rệt tính ổn định và khả năng bảo trì trong tương tác dài hạn.

- <strong>Ví dụ (Few-shot)</strong>: luôn khuyến nghị cung cấp ví dụ, nhưng không nên nhồi tất cả "các điều kiện biên" vào prompt. Hãy chọn lọc một nhóm ví dụ <strong>đa dạng và tiêu biểu</strong> để trực tiếp phác họa "hành vi mong đợi". Với LLM, <strong>một ví dụ tốt hơn ngàn lời nói</strong>.

Tư tưởng chỉ đạo tổng thể là: <strong>thông tin đầy đủ nhưng cô đọng</strong>. Như Hình 9.2, đó là truy xuất động khi bước vào thời gian chạy.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/9-figures/9-2.webp" alt="" width="85%"/>
  <p>Hình 9.2 Hiệu chỉnh system prompt</p>
</div>


### 9.2.2 Truy xuất ngữ cảnh và tìm kiếm dạng Agent

Một định nghĩa ngắn gọn: <strong>Agent = LLM tự chủ gọi công cụ trong vòng lặp</strong>. Khi năng lực của mô hình nền tảng tăng lên, mức độ tự trị của Agent cũng có thể nâng cao: có thể độc lập khám phá không gian vấn đề phức tạp hơn, và phục hồi từ sai lầm.

Thực hành kỹ thuật đang dần chuyển từ "truy xuất một lần trước khi suy luận (truy xuất embedding)" sang "<strong>ngữ cảnh đúng lúc (Just-in-time, JIT)</strong>". Cách sau không tải trước toàn bộ dữ liệu liên quan, mà duy trì <strong>tham chiếu nhẹ</strong> (đường dẫn tệp, truy vấn lưu trữ, URL, v.v.), rồi nạp động dữ liệu cần thiết khi chạy thông qua công cụ. Điều này cho phép mô hình viết truy vấn có mục tiêu, lưu đệm kết quả cần thiết, và dùng các lệnh như <code>head</code>/<code>tail</code> để phân tích khối dữ liệu lớn — không cần nhồi toàn bộ khối dữ liệu vào ngữ cảnh một lần. Mô thức nhận thức này gần với con người hơn: chúng ta không học thuộc toàn bộ thông tin, mà dùng hệ thống tệp, hộp thư, bookmark và các chỉ mục bên ngoài khác để trích xuất theo nhu cầu.

Ngoài hiệu quả lưu trữ, <strong>siêu dữ liệu của tham chiếu</strong> cũng giúp tinh chỉnh hành vi: cấu trúc thư mục, quy ước đặt tên, dấu thời gian đều ngầm truyền tải "mục đích và tính thời sự". Ví dụ, <code>tests/test_utils.py</code> và <code>src/core/test_utils.py</code> gợi ý ngữ nghĩa khác nhau.

Cho phép Agent tự chủ điều hướng và truy xuất còn hiện thực được <strong>tiết lộ dần dần (progressive disclosure)</strong>: mỗi bước tương tác sinh ra ngữ cảnh mới, đến lượt nó lại định hướng quyết định bước tiếp theo — kích thước tệp gợi ý độ phức tạp, tên gợi ý mục đích, dấu thời gian gợi ý mức liên quan. Agent có thể xây dựng hiểu biết theo từng lớp, chỉ giữ "tập con cần thiết hiện tại" trong bộ nhớ làm việc, và bổ sung lưu trữ bền vững bằng cách "ghi chú", từ đó duy trì sự tập trung thay vì "bị choáng ngợp bởi tính bao quát".

Cần cân nhắc là: khám phá khi chạy thường chậm hơn truy xuất tính trước, và cần thiết kế kỹ thuật "có chủ kiến" để đảm bảo mô hình có đúng công cụ và heuristic. Nếu thiếu định hướng, Agent có thể dùng sai công cụ, đuổi theo ngõ cụt hoặc bỏ lỡ thông tin then chốt, gây lãng phí ngữ cảnh.

Trong không ít kịch bản, <strong>chiến lược kết hợp</strong> hiệu quả hơn: nạp trước một lượng nhỏ ngữ cảnh "giá trị cao" để đảm bảo tốc độ, sau đó cho phép Agent tiếp tục tự chủ khám phá theo nhu cầu. Việc chọn ranh giới phụ thuộc vào tính động của nhiệm vụ và yêu cầu về tính thời sự. Về kỹ thuật, có thể đặt trước những tệp như "mô tả quy ước dự án (như README/hướng dẫn)", đồng thời cung cấp các nguyên thủy như <code>glob</code>, <code>grep</code> để Agent truy xuất tức thời tệp cụ thể, từ đó tránh chi phí chìm của chỉ mục lỗi thời và cây cú pháp phức tạp.


### 9.2.3 Kỹ thuật ngữ cảnh cho nhiệm vụ dài hạn

Nhiệm vụ dài hạn đòi hỏi Agent vẫn giữ được tính liên tục, nhất quán ngữ cảnh và định hướng mục tiêu trong chuỗi hành động dài vượt quá cửa sổ ngữ cảnh. Ví dụ di cư cơ sở mã lớn, nghiên cứu có hệ thống kéo dài nhiều giờ. Hy vọng vào việc tăng vô hạn cửa sổ ngữ cảnh không thể chữa tận gốc "ô nhiễm ngữ cảnh" và suy giảm mức liên quan, nên cần những phương pháp kỹ thuật hướng trực tiếp vào các ràng buộc này: <strong>nén tích hợp (Compaction)</strong>, <strong>ghi chú có cấu trúc (Structured note-taking)</strong> và <strong>kiến trúc sub-agent (Sub-agent architectures)</strong>.

- <strong>Nén tích hợp (Compaction)</strong>
  - Định nghĩa: khi cuộc hội thoại gần chạm giới hạn ngữ cảnh, tóm tắt nó với độ trung thực cao, rồi dùng bản tóm tắt đó để khởi động một cửa sổ ngữ cảnh mới, nhằm duy trì tính liên tục đường dài.
  - Thực hành: để mô hình nén và giữ lại các quyết định kiến trúc, khiếm khuyết chưa giải quyết, chi tiết hiện thực; loại bỏ đầu ra công cụ trùng lặp và nhiễu; cửa sổ mới mang theo bản tóm tắt nén + một lượng nhỏ artifact có mức liên quan cao gần đây (như "một vài tệp vừa truy cập").
  - Khuyến nghị tinh chỉnh tham số: trước tiên tối ưu <strong>độ phủ nhận (recall)</strong> (đảm bảo không bỏ sót thông tin then chốt), sau đó tối ưu <strong>độ chính xác (precision)</strong> (loại bỏ nội dung dư thừa); một cách nén "chạm nhẹ" an toàn là dọn dẹp "các lệnh gọi công cụ và kết quả trong lịch sử sâu".

- <strong>Ghi chú có cấu trúc (Structured note-taking)</strong>
  - Định nghĩa: còn gọi là "bộ nhớ Agent". Agent ghi thông tin then chốt vào <strong>kho lưu trữ bền vững ngoài ngữ cảnh</strong> với tần suất cố định, rồi kéo lại theo nhu cầu ở giai đoạn sau.
  - Giá trị: duy trì trạng thái bền vững và quan hệ phụ thuộc với chi phí ngữ cảnh cực thấp. Ví dụ duy trì danh sách TODO, tệp NOTES.md của dự án, chỉ mục các kết luận/phụ thuộc/điểm tắc then chốt, vẫn giữ được tiến độ và tính nhất quán qua hàng chục lệnh gọi công cụ và nhiều lần đặt lại ngữ cảnh.
  - Ghi chú: cũng hiệu quả trong các kịch bản phi lập trình (như nhiệm vụ chiến lược dài hạn, quản lý mục tiêu và đếm thống kê trong game/mô phỏng). Kết hợp với <code>MemoryTool</code> của Chương 8, có thể dễ dàng hiện thực bộ nhớ bên ngoài dạng tệp/dạng vector và truy xuất khi chạy.

- <strong>Kiến trúc sub-agent (Sub-agent architectures)</strong>
  - Tư tưởng: Agent chính phụ trách quy hoạch cấp cao và tổng hợp, nhiều sub-agent chuyên trách đào sâu, gọi công cụ và khám phá trong "cửa sổ ngữ cảnh sạch", cuối cùng chỉ trả về <strong>bản tóm tắt cô đọng</strong> (thường 1.000–2.000 token).
  - Lợi ích: hiện thực tách biệt mối quan tâm. Ngữ cảnh tìm kiếm cồng kềnh ở lại bên trong sub-agent, Agent chính tập trung vào tổng hợp và suy luận; phù hợp với nhiệm vụ nghiên cứu/phân tích phức tạp cần khám phá song song.
  - Kinh nghiệm: các hệ thống nghiên cứu đa Agent công khai cho thấy mô thức này có ưu thế rõ rệt so với baseline đơn Agent trên nhiệm vụ nghiên cứu phức tạp.

Việc chọn phương pháp có thể tuân theo các quy tắc kinh nghiệm sau:

- <strong>Nén tích hợp</strong>: phù hợp với nhiệm vụ cần tính liên tục của hội thoại dài, nhấn mạnh "chuyền tay" ngữ cảnh.
- <strong>Ghi chú có cấu trúc</strong>: phù hợp với phát triển và nghiên cứu lặp có cột mốc/thành quả theo giai đoạn.
- <strong>Kiến trúc sub-agent</strong>: phù hợp với nghiên cứu và phân tích phức tạp, có thể hưởng lợi từ khám phá song song.

Ngay cả khi năng lực mô hình tiếp tục nâng cao, "duy trì tính liên tục và tập trung trong tương tác dài" vẫn là thách thức cốt lõi khi xây dựng Agent vững chắc. Kỹ thuật ngữ cảnh cẩn trọng và có hệ thống sẽ còn giữ giá trị then chốt trong thời gian dài.

## 9.3 Thực hành trong Hello-Agents: ContextBuilder

Mục này sẽ giới thiệu chi tiết thực hành kỹ thuật ngữ cảnh trong framework HelloAgents. Chúng ta sẽ đi từ động cơ thiết kế, cấu trúc dữ liệu cốt lõi, chi tiết hiện thực đến ví dụ hoàn chỉnh, từng bước trình bày cách xây dựng một hệ thống quản lý ngữ cảnh cấp sản xuất. Triết lý thiết kế của ContextBuilder là "đơn giản và hiệu quả", loại bỏ sự phức tạp không cần thiết, thống nhất lựa chọn theo điểm "mức liên quan + độ mới", phù hợp với định hướng kỹ thuật về tính mô-đun và khả năng bảo trì của Agent.

### 9.3.1 Động cơ thiết kế và mục tiêu

Trước khi xây dựng ContextBuilder, chúng ta cần làm rõ mục tiêu thiết kế và giá trị cốt lõi của nó. Một hệ thống quản lý ngữ cảnh xuất sắc nên giải quyết các vấn đề then chốt sau:

1. <strong>Cửa vào thống nhất</strong>: trừu tượng hóa "Thu thập (Gather) - Chọn lọc (Select) - Cấu trúc hóa (Structure) - Nén (Compress)" thành một quy trình có thể tái sử dụng, giảm mã mẫu lặp lại trong hiện thực Agent. Thiết kế giao diện thống nhất này giúp nhà phát triển không phải viết lại logic quản lý ngữ cảnh trong từng Agent.

2. <strong>Hình thái ổn định</strong>: xuất ra mẫu ngữ cảnh có bộ khung cố định, thuận tiện cho gỡ lỗi, kiểm thử A/B và đánh giá. Chúng tôi dùng cấu trúc mẫu tổ chức theo phân vùng:
   - `[Role & Policies]`: làm rõ định vị vai trò và chuẩn mực hành vi của Agent
   - `[Task]`: nhiệm vụ cụ thể cần hoàn thành hiện tại
   - `[State]`: trạng thái hiện tại và thông tin ngữ cảnh của Agent
   - `[Evidence]`: thông tin bằng chứng truy xuất từ kho tri thức bên ngoài
   - `[Context]`: hội thoại lịch sử và bộ nhớ liên quan
   - `[Output]`: định dạng đầu ra và yêu cầu mong đợi

3. <strong>Bảo vệ ngân sách</strong>: trong ngân sách token, cố gắng giữ lại thông tin giá trị cao, đồng thời cung cấp chiến lược nén dự phòng cho ngữ cảnh vượt giới hạn. Điều này đảm bảo hệ thống vẫn chạy ổn định ngay cả trong kịch bản lượng thông tin rất lớn.

4. <strong>Quy tắc tối thiểu</strong>: không đưa vào các chiều phân loại như nguồn/độ ưu tiên, tránh gia tăng độ phức tạp. Thực tiễn cho thấy cơ chế chấm điểm đơn giản dựa trên mức liên quan và độ mới đã đủ hiệu quả trong phần lớn kịch bản.

### 9.3.2 Cấu trúc dữ liệu cốt lõi

Hiện thực ContextBuilder dựa trên hai cấu trúc dữ liệu cốt lõi, chúng định nghĩa cấu hình và đơn vị thông tin của hệ thống.

(1) ContextPacket: gói thông tin ứng viên

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class ContextPacket:
    """Gói thông tin ứng viên

    Attributes:
        content: Nội dung thông tin
        timestamp: Dấu thời gian
        token_count: Số lượng token
        relevance_score: Điểm mức liên quan (0.0-1.0)
        metadata: Siêu dữ liệu tùy chọn
    """
    content: str
    timestamp: datetime
    token_count: int
    relevance_score: float = 0.5
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Xử lý sau khởi tạo"""
        if self.metadata is None:
            self.metadata = {}
        # Đảm bảo điểm mức liên quan nằm trong khoảng hợp lệ
        self.relevance_score = max(0.0, min(1.0, self.relevance_score))
```

`ContextPacket` là đơn vị cơ bản của thông tin trong hệ thống. Mỗi thông tin ứng viên đều được đóng gói thành một ContextPacket, chứa các thuộc tính cốt lõi như nội dung, dấu thời gian, số token và điểm mức liên quan. Cấu trúc dữ liệu thống nhất này đơn giản hóa logic chọn lọc và sắp xếp phía sau.

(2) ContextConfig: quản lý cấu hình

```python
@dataclass
class ContextConfig:
    """Cấu hình xây dựng ngữ cảnh

    Attributes:
        max_tokens: Số token tối đa
        reserve_ratio: Tỷ lệ dự trữ cho chỉ dẫn hệ thống (0.0-1.0)
        min_relevance: Ngưỡng mức liên quan tối thiểu
        enable_compression: Có bật nén hay không
        recency_weight: Trọng số độ mới (0.0-1.0)
        relevance_weight: Trọng số mức liên quan (0.0-1.0)
    """
    max_tokens: int = 3000
    reserve_ratio: float = 0.2
    min_relevance: float = 0.1
    enable_compression: bool = True
    recency_weight: float = 0.3
    relevance_weight: float = 0.7

    def __post_init__(self):
        """Kiểm tra tham số cấu hình"""
        assert 0.0 <= self.reserve_ratio <= 1.0, "reserve_ratio phải nằm trong khoảng [0, 1]"
        assert 0.0 <= self.min_relevance <= 1.0, "min_relevance phải nằm trong khoảng [0, 1]"
        assert abs(self.recency_weight + self.relevance_weight - 1.0) < 1e-6, \
            "recency_weight + relevance_weight phải bằng 1.0"
```

`ContextConfig` đóng gói toàn bộ tham số có thể cấu hình, giúp hành vi hệ thống có thể điều chỉnh linh hoạt. Đáng chú ý đặc biệt là tham số `reserve_ratio`, nó đảm bảo những thông tin then chốt như chỉ dẫn hệ thống luôn có đủ không gian, không bị thông tin khác chiếm chỗ.

### 9.3.3 Chi tiết quy trình GSSC

Cốt lõi của ContextBuilder là quy trình GSSC (Gather-Select-Structure-Compress), nó phân tách quá trình xây dựng ngữ cảnh thành bốn giai đoạn rõ ràng. Hãy cùng tìm hiểu chi tiết hiện thực của từng giai đoạn.

(1) Gather: thu thập thông tin từ nhiều nguồn

Giai đoạn đầu tiên là thu thập thông tin ứng viên từ nhiều nguồn. Điểm then chốt của giai đoạn này là khả năng chịu lỗi và tính linh hoạt.

```python
def _gather(
    self,
    user_query: str,
    conversation_history: Optional[List[Message]] = None,
    system_instructions: Optional[str] = None,
    custom_packets: Optional[List[ContextPacket]] = None
) -> List[ContextPacket]:
    """Thu thập toàn bộ thông tin ứng viên

    Args:
        user_query: Truy vấn của người dùng
        conversation_history: Lịch sử hội thoại
        system_instructions: Chỉ dẫn hệ thống
        custom_packets: Gói thông tin tùy chỉnh

    Returns:
        List[ContextPacket]: Danh sách thông tin ứng viên
    """
    packets = []

    # 1. Thêm chỉ dẫn hệ thống (ưu tiên cao nhất, không tham gia chấm điểm)
    if system_instructions:
        packets.append(ContextPacket(
            content=system_instructions,
            timestamp=datetime.now(),
            token_count=self._count_tokens(system_instructions),
            relevance_score=1.0,  # Chỉ dẫn hệ thống luôn được giữ lại
            metadata={"type": "system_instruction", "priority": "high"}
        ))

    # 2. Truy xuất bộ nhớ liên quan từ hệ thống bộ nhớ
    if self.memory_tool:
        try:
            memory_results = self.memory_tool.run({
                "action": "search",
                "query": user_query,
                "limit": 10,
                "min_importance": 0.3
            })
            # Phân tích kết quả bộ nhớ và chuyển thành ContextPacket
            memory_packets = self._parse_memory_results(memory_results, user_query)
            packets.extend(memory_packets)
        except Exception as e:
            print(f"[WARNING] Truy xuất bộ nhớ thất bại: {e}")

    # 3. Truy xuất tri thức liên quan từ hệ thống RAG
    if self.rag_tool:
        try:
            rag_results = self.rag_tool.run({
                "action": "search",
                "query": user_query,
                "limit": 5,
                "min_score": 0.3
            })
            # Phân tích kết quả RAG và chuyển thành ContextPacket
            rag_packets = self._parse_rag_results(rag_results, user_query)
            packets.extend(rag_packets)
        except Exception as e:
            print(f"[WARNING] Truy xuất RAG thất bại: {e}")

    # 4. Thêm lịch sử hội thoại (chỉ giữ N mục gần nhất)
    if conversation_history:
        recent_history = conversation_history[-5:]  # Mặc định giữ 5 mục gần nhất
        for msg in recent_history:
            packets.append(ContextPacket(
                content=f"{msg.role}: {msg.content}",
                timestamp=msg.timestamp if hasattr(msg, 'timestamp') else datetime.now(),
                token_count=self._count_tokens(msg.content),
                relevance_score=0.6,  # Mức liên quan cơ bản của tin nhắn lịch sử
                metadata={"type": "conversation_history", "role": msg.role}
            ))

    # 5. Thêm gói thông tin tùy chỉnh
    if custom_packets:
        packets.extend(custom_packets)

    print(f"[ContextBuilder] Đã thu thập {len(packets)} gói thông tin ứng viên")
    return packets
```
Cách hiện thực này thể hiện vài cân nhắc thiết kế quan trọng:

- <strong>Cơ chế chịu lỗi</strong>: mỗi lần gọi nguồn dữ liệu bên ngoài đều được bọc trong try-except, đảm bảo lỗi của một nguồn không ảnh hưởng đến toàn bộ quy trình
- <strong>Xử lý ưu tiên</strong>: chỉ dẫn hệ thống được đánh dấu ưu tiên cao, đảm bảo luôn được giữ lại
- <strong>Giới hạn lịch sử</strong>: lịch sử hội thoại chỉ giữ vài mục gần nhất, tránh để cửa sổ ngữ cảnh bị thông tin lịch sử chiếm chỗ

(2) Select: chọn lọc thông tin thông minh

Giai đoạn thứ hai là chấm điểm và chọn lọc thông tin ứng viên dựa trên mức liên quan và độ mới. Đây là cốt lõi của toàn bộ quy trình, quyết định trực tiếp chất lượng ngữ cảnh cuối cùng.

```python
def _select(
    self,
    packets: List[ContextPacket],
    user_query: str,
    available_tokens: int
) -> List[ContextPacket]:
    """Chọn các gói thông tin liên quan nhất

    Args:
        packets: Danh sách gói thông tin ứng viên
        user_query: Truy vấn của người dùng (dùng để tính mức liên quan)
        available_tokens: Số token khả dụng

    Returns:
        List[ContextPacket]: Danh sách gói thông tin được chọn
    """
    # 1. Tách chỉ dẫn hệ thống khỏi thông tin khác
    system_packets = [p for p in packets if p.metadata.get("type") == "system_instruction"]
    other_packets = [p for p in packets if p.metadata.get("type") != "system_instruction"]

    # 2. Tính số token mà chỉ dẫn hệ thống chiếm dụng
    system_tokens = sum(p.token_count for p in system_packets)
    remaining_tokens = available_tokens - system_tokens

    if remaining_tokens <= 0:
        print("[WARNING] Chỉ dẫn hệ thống đã chiếm hết ngân sách token")
        return system_packets

    # 3. Tính điểm tổng hợp cho thông tin khác
    scored_packets = []
    for packet in other_packets:
        # Tính điểm mức liên quan (nếu chưa được tính)
        if packet.relevance_score == 0.5:  # Giá trị mặc định, cần tính lại
            relevance = self._calculate_relevance(packet.content, user_query)
            packet.relevance_score = relevance

        # Tính điểm độ mới
        recency = self._calculate_recency(packet.timestamp)

        # Điểm tổng hợp = trọng số mức liên quan × mức liên quan + trọng số độ mới × độ mới
        combined_score = (
            self.config.relevance_weight * packet.relevance_score +
            self.config.recency_weight * recency
        )

        # Lọc bỏ thông tin dưới ngưỡng mức liên quan tối thiểu
        if packet.relevance_score >= self.config.min_relevance:
            scored_packets.append((combined_score, packet))

    # 4. Sắp xếp theo điểm giảm dần
    scored_packets.sort(key=lambda x: x[0], reverse=True)

    # 5. Chọn tham lam: lấp đầy theo điểm từ cao xuống thấp cho đến khi đạt giới hạn token
    selected = system_packets.copy()
    current_tokens = system_tokens

    for score, packet in scored_packets:
        if current_tokens + packet.token_count <= available_tokens:
            selected.append(packet)
            current_tokens += packet.token_count
        else:
            # Ngân sách token đã đầy, dừng chọn lọc
            break

    print(f"[ContextBuilder] Đã chọn {len(selected)} gói thông tin, tổng {current_tokens} token")
    return selected

def _calculate_relevance(self, content: str, query: str) -> float:
    """Tính mức liên quan giữa nội dung và truy vấn

    Dùng thuật toán trùng lặp từ khóa đơn giản. Trong môi trường sản xuất, có thể thay bằng tính độ tương đồng vector.

    Args:
        content: Văn bản nội dung
        query: Văn bản truy vấn

    Returns:
        float: Điểm mức liên quan (0.0-1.0)
    """
    # Tách từ (hiện thực đơn giản, có thể dùng bộ tách từ phức tạp hơn)
    content_words = set(content.lower().split())
    query_words = set(query.lower().split())

    if not query_words:
        return 0.0

    # Độ tương đồng Jaccard
    intersection = content_words & query_words
    union = content_words | query_words

    return len(intersection) / len(union) if union else 0.0

def _calculate_recency(self, timestamp: datetime) -> float:
    """Tính điểm độ mới theo thời gian

    Dùng mô hình suy giảm hàm mũ, giữ điểm cao trong 24 giờ, sau đó suy giảm dần.

    Args:
        timestamp: Dấu thời gian của thông tin

    Returns:
        float: Điểm độ mới (0.0-1.0)
    """
    import math

    age_hours = (datetime.now() - timestamp).total_seconds() / 3600

    # Suy giảm hàm mũ: giữ điểm cao trong 24 giờ, sau đó suy giảm dần
    decay_factor = 0.1  # Hệ số suy giảm
    recency_score = math.exp(-decay_factor * age_hours / 24)

    return max(0.1, min(1.0, recency_score))  # Giới hạn trong khoảng [0.1, 1.0]
```

Thuật toán cốt lõi của giai đoạn chọn lọc thể hiện vài cân nhắc kỹ thuật quan trọng:

- <strong>Cơ chế chấm điểm</strong>: dùng kết hợp có trọng số giữa mức liên quan và độ mới, trọng số có thể cấu hình
- <strong>Thuật toán tham lam</strong>: lấp đầy theo điểm từ cao xuống thấp, đảm bảo chọn được thông tin giá trị nhất trong ngân sách hữu hạn
- <strong>Cơ chế lọc</strong>: lọc thông tin chất lượng thấp qua tham số `min_relevance`

(3) Structure: đầu ra có cấu trúc

Giai đoạn thứ ba là tổ chức thông tin đã chọn thành mẫu ngữ cảnh có cấu trúc.

```python
def _structure(self, selected_packets: List[ContextPacket], user_query: str) -> str:
    """Tổ chức các gói thông tin đã chọn thành mẫu ngữ cảnh có cấu trúc

    Args:
        selected_packets: Danh sách gói thông tin đã chọn
        user_query: Truy vấn của người dùng

    Returns:
        str: Chuỗi ngữ cảnh có cấu trúc
    """
    # Nhóm theo loại
    system_instructions = []
    evidence = []
    context = []

    for packet in selected_packets:
        packet_type = packet.metadata.get("type", "general")

        if packet_type == "system_instruction":
            system_instructions.append(packet.content)
        elif packet_type in ["rag_result", "knowledge"]:
            evidence.append(packet.content)
        else:
            context.append(packet.content)

    # Xây dựng mẫu có cấu trúc
    sections = []

    # [Role & Policies]
    if system_instructions:
        sections.append("[Role & Policies]\n" + "\n".join(system_instructions))

    # [Task]
    sections.append(f"[Task]\n{user_query}")

    # [Evidence]
    if evidence:
        sections.append("[Evidence]\n" + "\n---\n".join(evidence))

    # [Context]
    if context:
        sections.append("[Context]\n" + "\n".join(context))

    # [Output]
    sections.append("[Output]\nHãy dựa trên thông tin trên để đưa ra câu trả lời chính xác, có căn cứ.")

    return "\n\n".join(sections)
```

Giai đoạn cấu trúc hóa tổ chức các gói thông tin rời rạc thành những phân vùng rõ ràng; thiết kế này có vài ưu điểm:

- <strong>Tính dễ đọc</strong>: phân vùng rõ ràng giúp cả con người và mô hình hiểu cấu trúc ngữ cảnh dễ hơn
- <strong>Tính dễ gỡ lỗi</strong>: định vị vấn đề dễ hơn, có thể nhanh chóng xác định thông tin ở vùng nào có vấn đề
- <strong>Tính mở rộng</strong>: thêm nguồn thông tin mới chỉ cần tạo phân vùng mới

(4) Compress: nén dự phòng

Giai đoạn thứ tư là nén ngữ cảnh vượt giới hạn.

```python
def _compress(self, context: str, max_tokens: int) -> str:
    """Nén ngữ cảnh vượt giới hạn

    Args:
        context: Ngữ cảnh gốc
        max_tokens: Giới hạn token tối đa

    Returns:
        str: Ngữ cảnh sau khi nén
    """
    current_tokens = self._count_tokens(context)

    if current_tokens <= max_tokens:
        return context  # Không cần nén

    print(f"[ContextBuilder] Ngữ cảnh vượt giới hạn ({current_tokens} > {max_tokens}), thực hiện nén")

    # Nén theo phân vùng: giữ tính toàn vẹn cấu trúc
    sections = context.split("\n\n")
    compressed_sections = []
    current_total = 0

    for section in sections:
        section_tokens = self._count_tokens(section)

        if current_total + section_tokens <= max_tokens:
            # Giữ nguyên toàn bộ
            compressed_sections.append(section)
            current_total += section_tokens
        else:
            # Giữ một phần
            remaining_tokens = max_tokens - current_total
            if remaining_tokens > 50:  # Giữ ít nhất 50 token
                # Cắt đơn giản (trong môi trường sản xuất có thể dùng LLM tóm tắt)
                truncated = self._truncate_text(section, remaining_tokens)
                compressed_sections.append(truncated + "\n[... nội dung đã được nén ...]")
            break

    compressed_context = "\n\n".join(compressed_sections)
    final_tokens = self._count_tokens(compressed_context)
    print(f"[ContextBuilder] Nén hoàn tất: {current_tokens} -> {final_tokens} token")

    return compressed_context

def _truncate_text(self, text: str, max_tokens: int) -> str:
    """Cắt văn bản đến số token chỉ định

    Args:
        text: Văn bản gốc
        max_tokens: Số token tối đa

    Returns:
        str: Văn bản sau khi cắt
    """
    # Hiện thực đơn giản: ước lượng theo tỷ lệ ký tự
    # Trong môi trường sản xuất nên dùng tokenizer chính xác
    char_per_token = len(text) / self._count_tokens(text) if self._count_tokens(text) > 0 else 4
    max_chars = int(max_tokens * char_per_token)

    return text[:max_chars]

def _count_tokens(self, text: str) -> int:
    """Ước lượng số token của văn bản

    Args:
        text: Nội dung văn bản

    Returns:
        int: Số lượng token
    """
    # Ước lượng đơn giản: tiếng Trung 1 ký tự ≈ 1 token, tiếng Anh 1 từ ≈ 1.3 token
    # Trong môi trường sản xuất nên dùng tokenizer thực tế
    chinese_chars = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    english_words = len([w for w in text.split() if w])

    return int(chinese_chars + english_words * 1.3)
```

Thiết kế của giai đoạn nén thể hiện nguyên tắc "giữ tính toàn vẹn cấu trúc": ngay cả khi ngân sách token eo hẹp, vẫn cố gắng giữ thông tin then chốt của mỗi phân vùng.

### 9.3.4 Ví dụ sử dụng hoàn chỉnh

Bây giờ chúng ta hãy xem một ví dụ hoàn chỉnh, trình bày cách dùng ContextBuilder trong dự án thực tế.

(1) Sử dụng cơ bản

```python
from hello_agents.context import ContextBuilder, ContextConfig
from hello_agents.tools import MemoryTool, RAGTool
from hello_agents.core.message import Message
from datetime import datetime

# 1. Khởi tạo công cụ
memory_tool = MemoryTool(user_id="user123")
rag_tool = RAGTool(knowledge_base_path="./knowledge_base")

# 2. Tạo ContextBuilder
config = ContextConfig(
    max_tokens=3000,
    reserve_ratio=0.2,
    min_relevance=0.2,
    enable_compression=True
)

builder = ContextBuilder(
    memory_tool=memory_tool,
    rag_tool=rag_tool,
    config=config
)

# 3. Chuẩn bị lịch sử hội thoại
conversation_history = [
    Message(content="Tôi đang phát triển một công cụ phân tích dữ liệu", role="user", timestamp=datetime.now()),
    Message(content="Rất tốt! Công cụ phân tích dữ liệu thường cần xử lý lượng lớn dữ liệu. Bạn dự định dùng công nghệ nào?", role="assistant", timestamp=datetime.now()),
    Message(content="Tôi định dùng Python và Pandas, đã hoàn thành mô-đun đọc CSV", role="user", timestamp=datetime.now()),
    Message(content="Lựa chọn tốt! Pandas rất mạnh trong xử lý dữ liệu. Tiếp theo bạn có thể cần cân nhắc làm sạch và chuyển đổi dữ liệu.", role="assistant", timestamp=datetime.now()),
]

# 4. Thêm một vài bộ nhớ
memory_tool.run({
    "action": "add",
    "content": "Người dùng đang phát triển công cụ phân tích dữ liệu, dùng Python và Pandas",
    "memory_type": "semantic",
    "importance": 0.8
})

memory_tool.run({
    "action": "add",
    "content": "Đã hoàn thành phát triển mô-đun đọc CSV",
    "memory_type": "episodic",
    "importance": 0.7
})

# 5. Xây dựng ngữ cảnh
context = builder.build(
    user_query="Làm thế nào để tối ưu mức chiếm bộ nhớ của Pandas?",
    conversation_history=conversation_history,
    system_instructions="Bạn là một cố vấn kỹ thuật dữ liệu Python dày dạn kinh nghiệm. Câu trả lời của bạn cần: 1) đưa ra khuyến nghị cụ thể, khả thi 2) giải thích nguyên lý kỹ thuật 3) đưa ra ví dụ mã"
)

print("=" * 80)
print("Ngữ cảnh được xây dựng:")
print("=" * 80)
print(context)
print("=" * 80)
```

(2) Trình bày hiệu quả chạy

Sau khi chạy đoạn mã trên, bạn sẽ thấy đầu ra ngữ cảnh có cấu trúc như sau:

```
================================================================================
Ngữ cảnh được xây dựng:
================================================================================
[Role & Policies]
Bạn là một cố vấn kỹ thuật dữ liệu Python dày dạn kinh nghiệm. Câu trả lời của bạn cần: 1) đưa ra khuyến nghị cụ thể, khả thi 2) giải thích nguyên lý kỹ thuật 3) đưa ra ví dụ mã

[Task]
Làm thế nào để tối ưu mức chiếm bộ nhớ của Pandas?

[Evidence]
Các chiến lược cốt lõi để tối ưu bộ nhớ Pandas bao gồm:
1. Dùng kiểu dữ liệu phù hợp (như dùng category thay cho object)
2. Đọc tệp lớn theo khối
3. Dùng tham số chunksize
---
Tối ưu kiểu dữ liệu có thể giảm đáng kể mức chiếm bộ nhớ. Ví dụ, hạ int64 xuống int32 có thể tiết kiệm 50% bộ nhớ.

[Context]
user: Tôi đang phát triển một công cụ phân tích dữ liệu
assistant: Rất tốt! Công cụ phân tích dữ liệu thường cần xử lý lượng lớn dữ liệu. Bạn dự định dùng công nghệ nào?
user: Tôi định dùng Python và Pandas, đã hoàn thành mô-đun đọc CSV
assistant: Lựa chọn tốt! Pandas rất mạnh trong xử lý dữ liệu. Tiếp theo bạn có thể cần cân nhắc làm sạch và chuyển đổi dữ liệu.
Bộ nhớ: Người dùng đang phát triển công cụ phân tích dữ liệu, dùng Python và Pandas
Bộ nhớ: Đã hoàn thành phát triển mô-đun đọc CSV

[Output]
Hãy dựa trên thông tin trên để đưa ra câu trả lời chính xác, có căn cứ.
================================================================================
```

Ngữ cảnh có cấu trúc này chứa toàn bộ thông tin cần thiết:

- <strong>[Role & Policies]</strong>: làm rõ vai trò của AI và yêu cầu trả lời
- <strong>[Task]</strong>: diễn đạt rõ ràng câu hỏi của người dùng
- <strong>[Evidence]</strong>: tri thức liên quan truy xuất từ hệ thống RAG
- <strong>[Context]</strong>: lịch sử hội thoại và bộ nhớ liên quan, cung cấp thông tin nền đầy đủ
- <strong>[Output]</strong>: chỉ dẫn LLM cách tổ chức câu trả lời

(3) Tích hợp với Agent

Cuối cùng, chúng ta hãy xem cách tích hợp ContextBuilder vào Agent:

```python
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.context import ContextBuilder, ContextConfig
from hello_agents.tools import MemoryTool, RAGTool

class ContextAwareAgent(SimpleAgent):
    """Agent có năng lực nhận biết ngữ cảnh"""

    def __init__(self, name: str, llm: HelloAgentsLLM, **kwargs):
        super().__init__(name=name, llm=llm, system_prompt=kwargs.get("system_prompt", ""))

        # Khởi tạo trình xây dựng ngữ cảnh
        self.memory_tool = MemoryTool(user_id=kwargs.get("user_id", "default"))
        self.rag_tool = RAGTool(knowledge_base_path=kwargs.get("knowledge_base_path", "./kb"))

        self.context_builder = ContextBuilder(
            memory_tool=self.memory_tool,
            rag_tool=self.rag_tool,
            config=ContextConfig(max_tokens=4000)
        )

        self.conversation_history = []

    def run(self, user_input: str) -> str:
        """Chạy Agent, tự động xây dựng ngữ cảnh được tối ưu"""

        # 1. Dùng ContextBuilder xây dựng ngữ cảnh được tối ưu
        optimized_context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.conversation_history,
            system_instructions=self.system_prompt
        )

        # 2. Gọi LLM với ngữ cảnh đã tối ưu
        messages = [
            {"role": "system", "content": optimized_context},
            {"role": "user", "content": user_input}
        ]
        response = self.llm.invoke(messages)

        # 3. Cập nhật lịch sử hội thoại
        from hello_agents.core.message import Message
        from datetime import datetime

        self.conversation_history.append(
            Message(content=user_input, role="user", timestamp=datetime.now())
        )
        self.conversation_history.append(
            Message(content=response, role="assistant", timestamp=datetime.now())
        )

        # 4. Ghi tương tác quan trọng vào hệ thống bộ nhớ
        self.memory_tool.run({
            "action": "add",
            "content": f"Q: {user_input}\nA: {response[:200]}...",  # Tóm tắt
            "memory_type": "episodic",
            "importance": 0.6
        })

        return response

# Ví dụ sử dụng
agent = ContextAwareAgent(
    name="Cố vấn phân tích dữ liệu",
    llm=HelloAgentsLLM(),
    system_prompt="Bạn là một cố vấn kỹ thuật dữ liệu Python dày dạn kinh nghiệm.",
    user_id="user123",
    knowledge_base_path="./data_science_kb"
)

response = agent.run("Làm thế nào để tối ưu mức chiếm bộ nhớ của Pandas?")
print(response)
```

Bằng cách này, ContextBuilder trở thành "bộ não quản lý ngữ cảnh" của Agent, tự động xử lý việc thu thập, sàng lọc và tổ chức thông tin, giúp Agent luôn có thể suy luận và sinh nội dung dưới ngữ cảnh tối ưu.

### 9.3.5 Thực hành tốt nhất và khuyến nghị tối ưu

Khi áp dụng ContextBuilder trong thực tế, vài thực hành tốt nhất sau đây đáng lưu ý:

1. <strong>Điều chỉnh ngân sách token linh hoạt</strong>: điều chỉnh `max_tokens` động theo độ phức tạp nhiệm vụ, nhiệm vụ đơn giản dùng ngân sách nhỏ hơn, nhiệm vụ phức tạp tăng ngân sách.

2. <strong>Tối ưu tính toán mức liên quan</strong>: trong môi trường sản xuất, thay thuật toán trùng lặp từ khóa đơn giản bằng tính độ tương đồng vector để nâng cao chất lượng truy xuất.

3. <strong>Cơ chế lưu đệm</strong>: với chỉ dẫn hệ thống và nội dung kho tri thức không thay đổi, có thể hiện thực cơ chế lưu đệm để tránh tính toán lặp lại.

4. <strong>Giám sát và nhật ký</strong>: ghi lại thông tin thống kê mỗi lần xây dựng ngữ cảnh (số thông tin được chọn, tỷ lệ sử dụng token, v.v.) để thuận tiện tối ưu về sau.

5. <strong>Kiểm thử A/B</strong>: với các tham số then chốt (như trọng số mức liên quan, trọng số độ mới), tìm cấu hình tối ưu thông qua kiểm thử A/B.

## 9.4 NoteTool: ghi chú có cấu trúc

NoteTool là thành phần bộ nhớ ngoài có cấu trúc được cung cấp cho "nhiệm vụ dài hạn". Nó dùng tệp Markdown làm vật mang, phần đầu dùng YAML front matter để ghi thông tin then chốt, phần thân dùng để ghi trạng thái, kết luận, điểm tắc và các mục hành động. Thiết kế này kết hợp tính dễ đọc với con người, tính thân thiện với kiểm soát phiên bản và đặc tính dễ đưa ngược vào ngữ cảnh, là công cụ quan trọng để xây dựng Agent dài hạn.

### 9.4.1 Triết lý thiết kế và kịch bản ứng dụng

Trước khi đi sâu vào chi tiết hiện thực, chúng ta hãy cùng hiểu triết lý thiết kế và kịch bản ứng dụng tiêu biểu của NoteTool.

(1) Vì sao cần NoteTool?

Ở Chương 8, chúng ta đã giới thiệu MemoryTool, nó cung cấp năng lực quản lý bộ nhớ mạnh mẽ. Tuy nhiên, MemoryTool chủ yếu quan tâm đến <strong>bộ nhớ hội thoại</strong> — bộ nhớ làm việc ngắn hạn, bộ nhớ tình huống và bộ nhớ ngữ nghĩa. Với <strong>nhiệm vụ dạng dự án</strong> cần theo dõi dài hạn và quản lý có cấu trúc, chúng ta cần một cách ghi chép nhẹ hơn, thân thiện với con người hơn.

NoteTool lấp đầy khoảng trống này, nó cung cấp:

- <strong>Ghi chép có cấu trúc</strong>: dùng định dạng Markdown + YAML, vừa phù hợp để máy phân tích, vừa thuận tiện cho con người đọc và chỉnh sửa
- <strong>Thân thiện với phiên bản</strong>: định dạng văn bản thuần, tự nhiên hỗ trợ các hệ thống kiểm soát phiên bản như Git
- <strong>Chi phí thấp</strong>: không cần thao tác cơ sở dữ liệu phức tạp, phù hợp theo dõi trạng thái nhẹ
- <strong>Phân loại linh hoạt</strong>: tổ chức ghi chú linh hoạt qua `type` và `tags`, hỗ trợ truy xuất đa chiều

(2) Kịch bản ứng dụng tiêu biểu

NoteTool đặc biệt phù hợp với các kịch bản sau:

<strong>Kịch bản 1: theo dõi dự án dài hạn</strong>

Hãy hình dung một Agent đang hỗ trợ hoàn thành nhiệm vụ tái cấu trúc một cơ sở mã lớn, có thể mất vài ngày thậm chí vài tuần. NoteTool có thể ghi lại:

- `task_state`: trạng thái nhiệm vụ và tiến độ của giai đoạn hiện tại
- `conclusion`: kết luận then chốt sau khi mỗi giai đoạn kết thúc
- `blocker`: vấn đề gặp phải và điểm tắc
- `action`: kế hoạch hành động tiếp theo

```python
# Ghi lại trạng thái nhiệm vụ
notes.run({
    "action": "create",
    "title": "Dự án tái cấu trúc - Giai đoạn một",
    "content": "Đã hoàn thành tái cấu trúc tầng mô hình dữ liệu, độ phủ kiểm thử đạt 85%. Bước tiếp theo sẽ tái cấu trúc tầng logic nghiệp vụ.",
    "note_type": "task_state",
    "tags": ["refactoring", "phase1"]
})

# Ghi lại điểm tắc
notes.run({
    "action": "create",
    "title": "Vấn đề xung đột phụ thuộc",
    "content": "Phát hiện một số thư viện bên thứ ba có phiên bản không tương thích, cần giải quyết. Phạm vi ảnh hưởng: 3 mô-đun của tầng logic nghiệp vụ.",
    "note_type": "blocker",
    "tags": ["dependency", "urgent"]
})
```

<strong>Kịch bản 2: quản lý nhiệm vụ nghiên cứu</strong>

Một trợ lý nghiên cứu thông minh khi thực hiện tổng quan tài liệu có thể dùng NoteTool ghi lại:

- Quan điểm cốt lõi của mỗi bài báo (`conclusion`)
- Chủ đề cần khảo sát sâu thêm (`action`)
- Tài liệu tham khảo quan trọng (`reference`)

<strong>Kịch bản 3: phối hợp với ContextBuilder</strong>

Trước mỗi vòng hội thoại, Agent có thể truy xuất ghi chú liên quan qua thao tác `search` hoặc `list`, và đưa chúng vào ngữ cảnh:

```python
# Trong phương thức run của Agent
def run(self, user_input: str) -> str:
    # 1. Truy xuất ghi chú liên quan
    relevant_notes = self.note_tool.run({
        "action": "search",
        "query": user_input,
        "limit": 3
    })

    # 2. Chuyển nội dung ghi chú thành ContextPacket
    note_packets = []
    for note in relevant_notes:
        note_packets.append(ContextPacket(
            content=note['content'],
            timestamp=note['updated_at'],
            token_count=self._count_tokens(note['content']),
            relevance_score=0.7,
            metadata={"type": "note", "note_type": note['type']}
        ))

    # 3. Truyền ghi chú khi xây dựng ngữ cảnh
    context = self.context_builder.build(
        user_query=user_input,
        custom_packets=note_packets,
        ...
    )
```

### 9.4.2 Chi tiết định dạng lưu trữ

NoteTool dùng định dạng kết hợp Markdown + YAML, thiết kế này cân bằng giữa cấu trúc hóa và tính dễ đọc.

(1) Định dạng tệp ghi chú

Mỗi ghi chú là một tệp `.md` độc lập, định dạng như sau:

```markdown
---
id: note_20250119_153000_0
title: Tiến độ dự án - Giai đoạn một
type: task_state
tags: [refactoring, phase1, backend]
created_at: 2025-01-19T15:30:00
updated_at: 2025-01-19T15:30:00
---

# Tiến độ dự án - Giai đoạn một

## Tình hình hoàn thành

Đã hoàn thành tái cấu trúc tầng mô hình dữ liệu, các thay đổi chính bao gồm:

1. Thống nhất quy ước đặt tên cho các lớp thực thể
2. Đưa vào gợi ý kiểu (type hint), nâng cao khả năng bảo trì mã
3. Tối ưu hiệu năng truy vấn cơ sở dữ liệu

## Độ phủ kiểm thử

- Độ phủ kiểm thử đơn vị: 85%
- Độ phủ kiểm thử tích hợp: 70%

## Kế hoạch tiếp theo

1. Tái cấu trúc tầng logic nghiệp vụ
2. Giải quyết vấn đề xung đột phụ thuộc
3. Nâng độ phủ kiểm thử tích hợp lên 85%
```

Ưu điểm của định dạng này:

- <strong>Siêu dữ liệu YAML</strong>: máy có thể phân tích, hỗ trợ trích xuất và truy xuất trường chính xác
- <strong>Thân Markdown</strong>: con người dễ đọc, hỗ trợ định dạng phong phú (tiêu đề, danh sách, khối mã, v.v.)
- <strong>Tên tệp chính là ID</strong>: đơn giản hóa quản lý, tên tệp của mỗi ghi chú chính là định danh duy nhất của nó

(2) Tệp chỉ mục

NoteTool duy trì một tệp `notes_index.json` để truy xuất nhanh và quản lý ghi chú:

```json
{
  "note_20250119_153000_0": {
    "id": "note_20250119_153000_0",
    "title": "Tiến độ dự án - Giai đoạn một",
    "type": "task_state",
    "tags": ["refactoring", "phase1", "backend"],
    "created_at": "2025-01-19T15:30:00",
    "updated_at": "2025-01-19T15:30:00",
    "file_path": "./notes/note_20250119_153000_0.md"
  }
}
```

Vai trò của tệp chỉ mục này:

- <strong>Truy xuất nhanh</strong>: không cần mở từng tệp, tìm trực tiếp từ chỉ mục
- <strong>Quản lý siêu dữ liệu</strong>: quản lý tập trung siêu dữ liệu của tất cả ghi chú
- <strong>Kiểm tra tính toàn vẹn</strong>: có thể phát hiện tệp bị thiếu hoặc hỏng

### 9.4.3 Chi tiết các thao tác cốt lõi

NoteTool cung cấp bảy thao tác cốt lõi, bao phủ toàn bộ vòng đời quản lý ghi chú.

(1) create: tạo ghi chú

```python
def _create_note(
    self,
    title: str,
    content: str,
    note_type: str = "general",
    tags: Optional[List[str]] = None
) -> str:
    """Tạo ghi chú

    Args:
        title: Tiêu đề ghi chú
        content: Nội dung ghi chú (định dạng Markdown)
        note_type: Loại ghi chú (task_state/conclusion/blocker/action/reference/general)
        tags: Danh sách thẻ

    Returns:
        str: ID ghi chú
    """
    from datetime import datetime

    # 1. Sinh ID duy nhất
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    note_id = f"note_{timestamp}_{len(self.index)}"

    # 2. Xây dựng siêu dữ liệu
    metadata = {
        "id": note_id,
        "title": title,
        "type": note_type,
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # 3. Xây dựng nội dung tệp Markdown hoàn chỉnh
    md_content = self._build_markdown(metadata, content)

    # 4. Lưu vào tệp
    file_path = os.path.join(self.workspace, f"{note_id}.md")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    # 5. Cập nhật chỉ mục
    metadata["file_path"] = file_path
    self.index[note_id] = metadata
    self._save_index()

    return note_id

def _build_markdown(self, metadata: Dict, content: str) -> str:
    """Xây dựng nội dung tệp Markdown (YAML + thân)"""
    import yaml

    # YAML front matter
    yaml_header = yaml.dump(metadata, allow_unicode=True, sort_keys=False)

    # Định dạng kết hợp
    return f"---\n{yaml_header}---\n\n{content}"
```

Ví dụ sử dụng:

```python
from hello_agents.tools import NoteTool

notes = NoteTool(workspace="./project_notes")

note_id = notes.run({
    "action": "create",
    "title": "Dự án tái cấu trúc - Giai đoạn một",
    "content": """## Tình hình hoàn thành
Đã hoàn thành tái cấu trúc tầng mô hình dữ liệu, độ phủ kiểm thử đạt 85%.

## Bước tiếp theo
Tái cấu trúc tầng logic nghiệp vụ""",
    "note_type": "task_state",
    "tags": ["refactoring", "phase1"]
})

print(f"✅ Tạo ghi chú thành công, ID: {note_id}")
```

(2) read: đọc ghi chú

```python
def _read_note(self, note_id: str) -> Dict:
    """Đọc nội dung ghi chú

    Args:
        note_id: ID ghi chú

    Returns:
        Dict: Từ điển chứa siêu dữ liệu và nội dung
    """
    if note_id not in self.index:
        raise ValueError(f"Ghi chú không tồn tại: {note_id}")

    file_path = self.index[note_id]["file_path"]

    # Đọc tệp
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    # Phân tích siêu dữ liệu YAML và thân Markdown
    metadata, content = self._parse_markdown(raw_content)

    return {
        "metadata": metadata,
        "content": content
    }

def _parse_markdown(self, raw_content: str) -> Tuple[Dict, str]:
    """Phân tích tệp Markdown (tách YAML và thân)"""
    import yaml

    # Tìm dấu phân cách YAML
    parts = raw_content.split('---\n', 2)

    if len(parts) >= 3:
        # Có YAML front matter
        yaml_str = parts[1]
        content = parts[2].strip()
        metadata = yaml.safe_load(yaml_str)
    else:
        # Không có siêu dữ liệu, toàn bộ là thân
        metadata = {}
        content = raw_content.strip()

    return metadata, content
```

(3) update: cập nhật ghi chú

```python
def _update_note(
    self,
    note_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    note_type: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> str:
    """Cập nhật ghi chú

    Args:
        note_id: ID ghi chú
        title: Tiêu đề mới (tùy chọn)
        content: Nội dung mới (tùy chọn)
        note_type: Loại mới (tùy chọn)
        tags: Thẻ mới (tùy chọn)

    Returns:
        str: Thông báo kết quả thao tác
    """
    if note_id not in self.index:
        raise ValueError(f"Ghi chú không tồn tại: {note_id}")

    # 1. Đọc ghi chú hiện có
    note = self._read_note(note_id)
    metadata = note["metadata"]
    old_content = note["content"]

    # 2. Cập nhật các trường
    if title:
        metadata["title"] = title
    if note_type:
        metadata["type"] = note_type
    if tags is not None:
        metadata["tags"] = tags
    if content is not None:
        old_content = content

    # Cập nhật dấu thời gian
    from datetime import datetime
    metadata["updated_at"] = datetime.now().isoformat()

    # 3. Xây dựng lại và lưu
    md_content = self._build_markdown(metadata, old_content)
    file_path = metadata["file_path"]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    # 4. Cập nhật chỉ mục
    self.index[note_id] = metadata
    self._save_index()

    return f"✅ Ghi chú đã được cập nhật: {metadata['title']}"
```

(4) search: tìm kiếm ghi chú

```python
def _search_notes(
    self,
    query: str,
    limit: int = 10,
    note_type: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> List[Dict]:
    """Tìm kiếm ghi chú

    Args:
        query: Từ khóa tìm kiếm
        limit: Giới hạn số lượng trả về
        note_type: Lọc theo loại (tùy chọn)
        tags: Lọc theo thẻ (tùy chọn)

    Returns:
        List[Dict]: Danh sách ghi chú khớp
    """
    results = []
    query_lower = query.lower()

    for note_id, metadata in self.index.items():
        # Lọc theo loại
        if note_type and metadata.get("type") != note_type:
            continue

        # Lọc theo thẻ
        if tags:
            note_tags = set(metadata.get("tags", []))
            if not note_tags.intersection(tags):
                continue

        # Đọc nội dung ghi chú
        try:
            note = self._read_note(note_id)
            content = note["content"]
            title = metadata.get("title", "")

            # Tìm trong tiêu đề và nội dung
            if query_lower in title.lower() or query_lower in content.lower():
                results.append({
                    "note_id": note_id,
                    "title": title,
                    "type": metadata.get("type"),
                    "tags": metadata.get("tags", []),
                    "content": content,
                    "updated_at": metadata.get("updated_at")
                })
        except Exception as e:
            print(f"[WARNING] Đọc ghi chú {note_id} thất bại: {e}")
            continue

    # Sắp xếp theo thời gian cập nhật
    results.sort(key=lambda x: x["updated_at"], reverse=True)

    return results[:limit]
```

(5) list: liệt kê ghi chú

```python
def _list_notes(
    self,
    note_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20
) -> List[Dict]:
    """Liệt kê ghi chú (theo thời gian cập nhật giảm dần)

    Args:
        note_type: Lọc theo loại (tùy chọn)
        tags: Lọc theo thẻ (tùy chọn)
        limit: Giới hạn số lượng trả về

    Returns:
        List[Dict]: Danh sách siêu dữ liệu ghi chú
    """
    results = []

    for note_id, metadata in self.index.items():
        # Lọc theo loại
        if note_type and metadata.get("type") != note_type:
            continue

        # Lọc theo thẻ
        if tags:
            note_tags = set(metadata.get("tags", []))
            if not note_tags.intersection(tags):
                continue

        results.append(metadata)

    # Sắp xếp theo thời gian cập nhật
    results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    return results[:limit]
```

(6) summary: tóm tắt ghi chú

```python
def _summary(self) -> Dict[str, Any]:
    """Tạo thống kê tóm tắt ghi chú

    Returns:
        Dict: Thông tin thống kê
    """
    total_count = len(self.index)

    # Thống kê theo loại
    type_counts = {}
    for metadata in self.index.values():
        note_type = metadata.get("type", "general")
        type_counts[note_type] = type_counts.get(note_type, 0) + 1

    # Ghi chú cập nhật gần đây
    recent_notes = sorted(
        self.index.values(),
        key=lambda x: x.get("updated_at", ""),
        reverse=True
    )[:5]

    return {
        "total_notes": total_count,
        "type_distribution": type_counts,
        "recent_notes": [
            {
                "id": note["id"],
                "title": note.get("title", ""),
                "type": note.get("type"),
                "updated_at": note.get("updated_at")
            }
            for note in recent_notes
        ]
    }
```

(7) delete: xóa ghi chú

```python
def _delete_note(self, note_id: str) -> str:
    """Xóa ghi chú

    Args:
        note_id: ID ghi chú

    Returns:
        str: Thông báo kết quả thao tác
    """
    if note_id not in self.index:
        raise ValueError(f"Ghi chú không tồn tại: {note_id}")

    # 1. Xóa tệp
    file_path = self.index[note_id]["file_path"]
    if os.path.exists(file_path):
        os.remove(file_path)

    # 2. Xóa khỏi chỉ mục
    title = self.index[note_id].get("title", note_id)
    del self.index[note_id]
    self._save_index()

    return f"✅ Ghi chú đã bị xóa: {title}"
```

### 9.4.4 Tích hợp sâu với ContextBuilder

Sức mạnh thực sự của NoteTool nằm ở việc phối hợp với ContextBuilder. Hãy cùng xem một trường hợp hoàn chỉnh để trình bày sự tích hợp này.

(1) Thiết lập kịch bản

Giả sử chúng ta đang xây dựng một trợ lý dự án dài hạn, nó cần:

1. Ghi lại tiến triển theo giai đoạn của dự án
2. Theo dõi các vấn đề cần giải quyết
3. Ở mỗi cuộc hội thoại, tự động xem lại ghi chú liên quan
4. Dựa trên ghi chú lịch sử để đưa ra khuyến nghị nhất quán

(2) Ví dụ hiện thực

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.context import ContextBuilder, ContextConfig, ContextPacket
from hello_agents.tools import MemoryTool, RAGTool, NoteTool
from datetime import datetime

class ProjectAssistant(SimpleAgent):
    """Trợ lý dự án dài hạn, tích hợp NoteTool và ContextBuilder"""

    def __init__(self, name: str, project_name: str, **kwargs):
        super().__init__(name=name, llm=HelloAgentsLLM(), **kwargs)

        self.project_name = project_name

        # Khởi tạo công cụ
        self.memory_tool = MemoryTool(user_id=project_name)
        self.rag_tool = RAGTool(knowledge_base_path=f"./{project_name}_kb")
        self.note_tool = NoteTool(workspace=f"./{project_name}_notes")

        # Khởi tạo trình xây dựng ngữ cảnh
        self.context_builder = ContextBuilder(
            memory_tool=self.memory_tool,
            rag_tool=self.rag_tool,
            config=ContextConfig(max_tokens=4000)
        )

        self.conversation_history = []

    def run(self, user_input: str, note_as_action: bool = False) -> str:
        """Chạy trợ lý, tự động tích hợp ghi chú"""

        # 1. Truy xuất ghi chú liên quan từ NoteTool
        relevant_notes = self._retrieve_relevant_notes(user_input)

        # 2. Chuyển ghi chú thành ContextPacket
        note_packets = self._notes_to_packets(relevant_notes)

        # 3. Xây dựng ngữ cảnh được tối ưu
        context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.conversation_history,
            system_instructions=self._build_system_instructions(),
            custom_packets=note_packets
        )

        # 4. Gọi LLM
        response = self.llm.invoke(context)

        # 5. Nếu cần, ghi lại tương tác thành ghi chú
        if note_as_action:
            self._save_as_note(user_input, response)

        # 6. Cập nhật lịch sử hội thoại
        self._update_history(user_input, response)

        return response

    def _retrieve_relevant_notes(self, query: str, limit: int = 3) -> List[Dict]:
        """Truy xuất ghi chú liên quan"""
        try:
            # Ưu tiên truy xuất ghi chú loại blocker và action
            blockers = self.note_tool.run({
                "action": "list",
                "note_type": "blocker",
                "limit": 2
            })

            # Tìm kiếm tổng quát
            search_results = self.note_tool.run({
                "action": "search",
                "query": query,
                "limit": limit
            })

            # Hợp nhất và loại trùng
            all_notes = {note['note_id']: note for note in blockers + search_results}
            return list(all_notes.values())[:limit]

        except Exception as e:
            print(f"[WARNING] Truy xuất ghi chú thất bại: {e}")
            return []

    def _notes_to_packets(self, notes: List[Dict]) -> List[ContextPacket]:
        """Chuyển ghi chú thành gói ngữ cảnh"""
        packets = []

        for note in notes:
            content = f"[Ghi chú: {note['title']}]\n{note['content']}"

            packets.append(ContextPacket(
                content=content,
                timestamp=datetime.fromisoformat(note['updated_at']),
                token_count=len(content) // 4,  # Ước lượng đơn giản
                relevance_score=0.75,  # Ghi chú có mức liên quan cao
                metadata={
                    "type": "note",
                    "note_type": note['type'],
                    "note_id": note['note_id']
                }
            ))

        return packets

    def _save_as_note(self, user_input: str, response: str):
        """Lưu tương tác thành ghi chú"""
        try:
            # Xác định nên lưu thành loại ghi chú nào
            if "vấn đề" in user_input or "tắc" in user_input:
                note_type = "blocker"
            elif "kế hoạch" in user_input or "bước tiếp theo" in user_input:
                note_type = "action"
            else:
                note_type = "conclusion"

            self.note_tool.run({
                "action": "create",
                "title": f"{user_input[:30]}...",
                "content": f"## Vấn đề\n{user_input}\n\n## Phân tích\n{response}",
                "note_type": note_type,
                "tags": [self.project_name, "auto_generated"]
            })

        except Exception as e:
            print(f"[WARNING] Lưu ghi chú thất bại: {e}")

    def _build_system_instructions(self) -> str:
        """Xây dựng chỉ dẫn hệ thống"""
        return f"""Bạn là trợ lý dài hạn của dự án {self.project_name}.

Trách nhiệm của bạn:
1. Dựa trên ghi chú lịch sử để đưa ra khuyến nghị nhất quán
2. Theo dõi tiến triển dự án và các vấn đề cần giải quyết
3. Trích dẫn ghi chú lịch sử liên quan khi trả lời
4. Đưa ra khuyến nghị bước tiếp theo cụ thể, có thể hành động

Lưu ý:
- Ưu tiên quan tâm đến các vấn đề được đánh dấu là blocker
- Nêu rõ nguồn căn cứ trong khuyến nghị (ghi chú, bộ nhớ hoặc kho tri thức)
- Duy trì nhận thức về tiến độ tổng thể của dự án"""

    def _update_history(self, user_input: str, response: str):
        """Cập nhật lịch sử hội thoại"""
        from hello_agents.core.message import Message

        self.conversation_history.append(
            Message(content=user_input, role="user", timestamp=datetime.now())
        )
        self.conversation_history.append(
            Message(content=response, role="assistant", timestamp=datetime.now())
        )

        # Giới hạn độ dài lịch sử
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

# Ví dụ sử dụng
assistant = ProjectAssistant(
    name="Trợ lý dự án",
    project_name="data_pipeline_refactoring"
)

# Tương tác lần một: ghi lại trạng thái dự án
response = assistant.run(
    "Chúng tôi đã hoàn thành tái cấu trúc tầng mô hình dữ liệu, độ phủ kiểm thử đạt 85%. Bước tiếp theo dự định tái cấu trúc tầng logic nghiệp vụ.",
    note_as_action=True
)

# Tương tác lần hai: nêu vấn đề
response = assistant.run(
    "Khi tái cấu trúc tầng logic nghiệp vụ, tôi gặp vấn đề xung đột phiên bản phụ thuộc, nên giải quyết thế nào?"
)

# Xem tóm tắt ghi chú
summary = assistant.note_tool.run({"action": "summary"})
print(summary)
```

(3) Trình bày hiệu quả chạy

```bash
[ContextBuilder] Đã thu thập 8 gói thông tin ứng viên
[ContextBuilder] Đã chọn 7 gói thông tin, tổng 3500 token

✅ Trợ lý trả lời:

Tôi nhận thấy ghi chú bạn đã ghi trước đó có đề cập đến vấn đề này. Theo ghi chú [Dự án tái cấu trúc - Giai đoạn một], độ phủ kiểm thử hiện tại của bạn đã đạt 85%, đây là nền tảng rất tốt.

Về vấn đề xung đột phiên bản phụ thuộc, tôi khuyến nghị:

1. **Dùng môi trường ảo để cô lập**: tạo môi trường ảo riêng cho tầng logic nghiệp vụ, tránh xung đột phụ thuộc với các mô-đun khác
2. **Khóa phiên bản**: chỉ định rõ phiên bản chính xác của mọi phụ thuộc trong requirements.txt
3. **Dùng pipdeptree**: phân tích cây phụ thuộc, tìm ra gốc rễ xung đột

Vấn đề này tôi sẽ đánh dấu là blocker, khuyến nghị ưu tiên giải quyết.

[Nguồn căn cứ: ghi chú note_20250119_153000_0, kho tri thức dự án]

---

📋 Tóm tắt ghi chú:
{
  "total_notes": 2,
  "type_distribution": {
    "action": 1,
    "blocker": 1
  },
  "recent_notes": [
    {
      "id": "note_20250119_154500_1",
      "title": "Khi tái cấu trúc tầng logic nghiệp vụ, tôi gặp vấn đề xung đột phiên bản phụ thuộc...",
      "type": "blocker",
      "updated_at": "2025-01-19T15:45:00"
    },
    {
      "id": "note_20250119_153000_0",
      "title": "Chúng tôi đã hoàn thành tái cấu trúc tầng mô hình dữ liệu...",
      "type": "action",
      "updated_at": "2025-01-19T15:30:00"
    }
  ]
}
```

### 9.4.5 Thực hành tốt nhất

Khi dùng NoteTool trong thực tế, những thực hành tốt nhất sau đây sẽ giúp bạn xây dựng Agent dài hạn mạnh hơn:

1. <strong>Phân loại ghi chú hợp lý</strong>:
   - `task_state`: ghi lại tiến triển và trạng thái theo giai đoạn
   - `conclusion`: ghi lại kết luận và phát hiện quan trọng
   - `blocker`: ghi lại vấn đề tắc nghẽn, ưu tiên cao nhất
   - `action`: ghi lại kế hoạch hành động tiếp theo
   - `reference`: ghi lại tài liệu tham khảo quan trọng

2. <strong>Dọn dẹp và lưu trữ định kỳ</strong>:
   - Với blocker đã giải quyết, cập nhật thành conclusion
   - Với action đã lỗi thời, xóa hoặc cập nhật kịp thời
   - Dùng tags để quản lý phiên bản, như `["v1.0", "completed"]`

3. <strong>Phối hợp với ContextBuilder</strong>:
   - Truy xuất ghi chú liên quan trước mỗi vòng hội thoại
   - Đặt điểm mức liên quan khác nhau theo loại ghi chú (blocker > action > conclusion)
   - Giới hạn số lượng ghi chú, tránh quá tải ngữ cảnh

4. <strong>Hợp tác người-máy</strong>:
   - Ghi chú ở định dạng Markdown con người đọc được, hỗ trợ chỉnh sửa thủ công
   - Dùng Git để kiểm soát phiên bản, theo dõi sự tiến hóa của ghi chú
   - Ở giai đoạn then chốt, con người rà soát ghi chú do Agent sinh ra

5. <strong>Quy trình tự động hóa</strong>:
   - Định kỳ tạo báo cáo tóm tắt ghi chú
   - Tự động tạo tài liệu tiến độ dự án dựa trên ghi chú
   - Đồng bộ nội dung ghi chú sang hệ thống khác (như Notion, Confluence)

## 9.5 TerminalTool: truy cập hệ thống tệp tức thời

Ở các chương trước, chúng ta đã giới thiệu MemoryTool và RAGTool, chúng lần lượt cung cấp năng lực bộ nhớ hội thoại và truy xuất tri thức. Tuy nhiên, trong nhiều kịch bản thực tế, Agent cần <strong>truy cập và khám phá hệ thống tệp tức thời</strong> — xem tệp nhật ký, phân tích cấu trúc cơ sở mã, truy xuất tệp cấu hình, v.v. Đó chính là đất dụng võ của TerminalTool.

TerminalTool cung cấp cho Agent <strong>năng lực thực thi dòng lệnh an toàn</strong>, hỗ trợ các lệnh hệ thống tệp và xử lý văn bản thông dụng, đồng thời đảm bảo an toàn hệ thống qua nhiều lớp cơ chế bảo mật. Thiết kế này hiện thực ý tưởng "ngữ cảnh đúng lúc (Just-in-time, JIT)" đã nêu ở mục 9.2.2 — Agent không cần nạp trước toàn bộ tệp, mà khám phá và truy xuất theo nhu cầu.

### 9.5.1 Triết lý thiết kế và cơ chế bảo mật

(1) Vì sao cần TerminalTool?

Khi xây dựng Agent dài hạn, chúng ta thường gặp các kịch bản sau:

<strong>Kịch bản 1: khám phá cơ sở mã</strong>

Một trợ lý phát triển cần giúp người dùng hiểu cấu trúc của một cơ sở mã lớn:

```python
# Cách truyền thống: lập chỉ mục trước toàn bộ tệp (chi phí cao, có thể lỗi thời)
rag_tool.add_document("./project/**/*.py")  # Tốn thời gian, chiếm nhiều lưu trữ

# Cách TerminalTool: khám phá tức thời
terminal.run({"command": "find . -name '*.py' -type f"})  # Nhanh, thời gian thực
terminal.run({"command": "grep -r 'class UserService' ."})  # Định vị chính xác
terminal.run({"command": "head -n 50 src/services/user.py"})  # Xem theo nhu cầu
```

<strong>Kịch bản 2: phân tích tệp nhật ký</strong>

Một trợ lý vận hành cần phân tích nhật ký ứng dụng:

```python
# Kiểm tra kích thước tệp nhật ký
terminal.run({"command": "ls -lh /var/log/app.log"})

# Xem nhật ký lỗi mới nhất
terminal.run({"command": "tail -n 100 /var/log/app.log | grep ERROR"})

# Thống kê phân bố loại lỗi
terminal.run({"command": "grep ERROR /var/log/app.log | cut -d':' -f3 | sort | uniq -c"})
```

<strong>Kịch bản 3: xem trước tệp dữ liệu</strong>

Một trợ lý phân tích dữ liệu cần nhanh chóng hiểu cấu trúc tệp dữ liệu:

```python
# Xem vài dòng đầu của tệp CSV
terminal.run({"command": "head -n 5 data/sales.csv"})

# Thống kê số dòng
terminal.run({"command": "wc -l data/*.csv"})

# Xem tên cột
terminal.run({"command": "head -n 1 data/sales.csv | tr ',' '\n'"})
```

Đặc điểm chung của các kịch bản này là: <strong>cần truy cập hệ thống tệp theo thời gian thực, nhẹ, thay vì lập chỉ mục và vector hóa trước</strong>. TerminalTool được thiết kế chính cho quy trình làm việc "khám phá" này.

(2) Chi tiết cơ chế bảo mật

Cho phép Agent thực thi lệnh là một năng lực mạnh mẽ nhưng nguy hiểm. TerminalTool đảm bảo an toàn hệ thống qua nhiều lớp cơ chế bảo mật:

<strong>Lớp thứ nhất: danh sách trắng lệnh</strong>

Chỉ cho phép các lệnh chỉ đọc an toàn, cấm hoàn toàn mọi thao tác có thể sửa đổi hệ thống:

```python
ALLOWED_COMMANDS = {
    # Liệt kê tệp và thông tin
    'ls', 'dir', 'tree',
    # Xem nội dung tệp
    'cat', 'head', 'tail', 'less', 'more',
    # Tìm kiếm tệp
    'find', 'grep', 'egrep', 'fgrep',
    # Xử lý văn bản
    'wc', 'sort', 'uniq', 'cut', 'awk', 'sed',
    # Thao tác thư mục
    'pwd', 'cd',
    # Thông tin tệp
    'file', 'stat', 'du', 'df',
    # Khác
    'echo', 'which', 'whereis',
}
```

Nếu Agent cố gắng thực thi lệnh ngoài danh sách trắng, nó sẽ bị từ chối ngay:

```python
terminal.run({"command": "rm -rf /"})
# ❌ Lệnh không được phép: rm
# Các lệnh được phép: cat, cd, cut, dir, du, ...
```

<strong>Lớp thứ hai: giới hạn thư mục làm việc (sandbox)</strong>

TerminalTool chỉ có thể truy cập thư mục làm việc được chỉ định và các thư mục con của nó, không thể truy cập phần khác của hệ thống:

```python
# Chỉ định thư mục làm việc khi khởi tạo
terminal = TerminalTool(workspace="./project")

# Được phép: truy cập tệp trong thư mục làm việc
terminal.run({"command": "cat ./src/main.py"})  # ✅

# Bị cấm: truy cập tệp ngoài thư mục làm việc
terminal.run({"command": "cat /etc/passwd"})  # ❌ Không được phép truy cập đường dẫn ngoài thư mục làm việc

# Bị cấm: thoát ra ngoài bằng ..
terminal.run({"command": "cd ../../../etc"})  # ❌ Không được phép truy cập đường dẫn ngoài thư mục làm việc
```

Cơ chế sandbox này đảm bảo ngay cả khi hành vi của Agent bất thường, nó cũng không thể ảnh hưởng đến phần khác của hệ thống.

<strong>Lớp thứ ba: kiểm soát thời gian chờ</strong>

Mỗi lệnh đều có giới hạn thời gian thực thi, ngăn vòng lặp vô hạn hoặc cạn kiệt tài nguyên:

```python
terminal = TerminalTool(
    workspace="./project",
    timeout=30  # Chờ tối đa 30 giây
)

# Nếu lệnh thực thi quá 30 giây
terminal.run({"command": "find / -name '*.log'"})
# ❌ Thực thi lệnh quá thời gian (vượt quá 30 giây)
```

<strong>Lớp thứ tư: giới hạn kích thước đầu ra</strong>

Giới hạn kích thước đầu ra của lệnh, ngăn tràn bộ nhớ:

```python
terminal = TerminalTool(
    workspace="./project",
    max_output_size=10 * 1024 * 1024  # 10MB
)

# Nếu đầu ra vượt 10MB
terminal.run({"command": "cat huge_file.log"})
# ... (nội dung 10MB đầu tiên) ...
# ⚠️ Đầu ra bị cắt (vượt quá 10485760 byte)
```

Qua bốn lớp cơ chế bảo mật này, TerminalTool vừa cung cấp năng lực mạnh mẽ, vừa đảm bảo an toàn hệ thống ở mức tối đa.

### 9.5.2 Chi tiết chức năng cốt lõi

Hiện thực TerminalTool tập trung vào hai chức năng cốt lõi: thực thi lệnh và điều hướng thư mục.

(1) Thực thi lệnh

Phương thức cốt lõi `_execute_command` chịu trách nhiệm thực thi lệnh thực tế:

```python
def _execute_command(self, command: str) -> str:
    """Thực thi lệnh"""
    try:
        # Thực thi lệnh trong thư mục hiện tại
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(self.current_dir),  # Thực thi trong thư mục làm việc hiện tại
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=os.environ.copy()
        )

        # Hợp nhất đầu ra chuẩn và lỗi chuẩn
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"

        # Kiểm tra kích thước đầu ra
        if len(output) > self.max_output_size:
            output = output[:self.max_output_size]
            output += f"\n\n⚠️ Đầu ra bị cắt (vượt quá {self.max_output_size} byte)"

        # Thêm thông tin mã trả về
        if result.returncode != 0:
            output = f"⚠️ Mã trả về của lệnh: {result.returncode}\n\n{output}"

        return output if output else "✅ Lệnh thực thi thành công (không có đầu ra)"

    except subprocess.TimeoutExpired:
        return f"❌ Thực thi lệnh quá thời gian (vượt quá {self.timeout} giây)"
    except Exception as e:
        return f"❌ Thực thi lệnh thất bại: {e}"
```

Các điểm then chốt của hiện thực này:

- <strong>Nhận biết thư mục hiện tại</strong>: dùng tham số `cwd` để thực thi lệnh trong thư mục đúng
- <strong>Xử lý lỗi</strong>: bắt và hợp nhất lỗi chuẩn, cung cấp thông tin chẩn đoán đầy đủ
- <strong>Kiểm tra mã trả về</strong>: mã trả về khác 0 sẽ được đánh dấu cảnh báo
- <strong>Thiết kế chịu lỗi</strong>: thời gian chờ và ngoại lệ đều được xử lý thỏa đáng, không làm Agent sụp đổ

(2) Điều hướng thư mục

Xử lý đặc biệt của lệnh `cd` hỗ trợ Agent điều hướng trong hệ thống tệp:

```python
def _handle_cd(self, parts: List[str]) -> str:
    """Xử lý lệnh cd"""
    if not self.allow_cd:
        return "❌ Lệnh cd đã bị vô hiệu hóa"

    if len(parts) < 2:
        # cd không có tham số, trả về thư mục hiện tại
        return f"Thư mục hiện tại: {self.current_dir}"

    target_dir = parts[1]

    # Xử lý đường dẫn tương đối
    if target_dir == "..":
        new_dir = self.current_dir.parent
    elif target_dir == ".":
        new_dir = self.current_dir
    elif target_dir == "~":
        new_dir = self.workspace
    else:
        new_dir = (self.current_dir / target_dir).resolve()

    # Kiểm tra có nằm trong thư mục làm việc không
    try:
        new_dir.relative_to(self.workspace)
    except ValueError:
        return f"❌ Không được phép truy cập đường dẫn ngoài thư mục làm việc: {new_dir}"

    # Kiểm tra thư mục có tồn tại không
    if not new_dir.exists():
        return f"❌ Thư mục không tồn tại: {new_dir}"

    if not new_dir.is_dir():
        return f"❌ Không phải thư mục: {new_dir}"

    # Cập nhật thư mục hiện tại
    self.current_dir = new_dir
    return f"✅ Đã chuyển đến thư mục: {self.current_dir}"
```

Thiết kế này hỗ trợ Agent khám phá hệ thống tệp qua nhiều bước:

```python
# Bước một: xem cấu trúc dự án
terminal.run({"command": "ls -la"})

# Bước hai: vào thư mục mã nguồn
terminal.run({"command": "cd src"})

# Bước ba: tìm tệp cụ thể
terminal.run({"command": "find . -name '*service*.py'"})

# Bước bốn: xem nội dung tệp
terminal.run({"command": "cat user_service.py"})
```

### 9.5.3 Mô thức sử dụng tiêu biểu

TerminalTool hỗ trợ nhiều mô thức thao tác hệ thống tệp thông dụng.

(1) Điều hướng kiểu khám phá

Agent có thể khám phá cơ sở mã từng bước như một nhà phát triển con người:

```python
from hello_agents.tools import TerminalTool

terminal = TerminalTool(workspace="./my_project")

# Bước một: xem thư mục gốc dự án
print(terminal.run({"command": "ls -la"}))
"""
total 24
drwxr-xr-x  6 user  staff   192 Jan 19 16:00 .
drwxr-xr-x  5 user  staff   160 Jan 19 15:30 ..
-rw-r--r--  1 user  staff  1234 Jan 19 15:30 README.md
drwxr-xr-x  4 user  staff   128 Jan 19 15:30 src
drwxr-xr-x  3 user  staff    96 Jan 19 15:30 tests
-rw-r--r--  1 user  staff   456 Jan 19 15:30 requirements.txt
"""

# Bước hai: xem cấu trúc thư mục mã nguồn
terminal.run({"command": "cd src"})
print(terminal.run({"command": "tree"}))

# Bước ba: tìm mẫu cụ thể
print(terminal.run({"command": "grep -r 'def process' ."}))
```

(2) Phân tích tệp dữ liệu

Nhanh chóng hiểu cấu trúc và nội dung tệp dữ liệu:

```python
terminal = TerminalTool(workspace="./data")

# Xem vài dòng đầu của tệp CSV
print(terminal.run({"command": "head -n 5 sales_2024.csv"}))
"""
date,product,quantity,revenue
2024-01-01,Widget A,150,4500.00
2024-01-01,Widget B,200,8000.00
2024-01-02,Widget A,180,5400.00
2024-01-02,Widget C,120,3600.00
"""

# Thống kê tổng số dòng
print(terminal.run({"command": "wc -l *.csv"}))
"""
  10234 sales_2024.csv
   8567 sales_2023.csv
  18801 total
"""

# Trích xuất và thống kê danh mục sản phẩm
print(terminal.run({"command": "tail -n +2 sales_2024.csv | cut -d',' -f2 | sort | uniq -c"}))
"""
  3456 Widget A
  4123 Widget B
  2655 Widget C
"""
```

(3) Phân tích tệp nhật ký

Phân tích nhật ký ứng dụng theo thời gian thực, nhanh chóng định vị vấn đề:

```python
terminal = TerminalTool(workspace="/var/log")

# Xem nhật ký lỗi mới nhất
print(terminal.run({"command": "tail -n 50 app.log | grep ERROR"}))

# Thống kê phân bố loại lỗi
print(terminal.run({"command": "grep ERROR app.log | awk '{print $4}' | sort | uniq -c | sort -rn"}))
"""
  245 DatabaseConnectionError
  123 TimeoutException
   67 ValidationError
   34 AuthenticationError
"""

# Tìm nhật ký trong khoảng thời gian cụ thể
print(terminal.run({"command": "grep '2024-01-19 15:' app.log | tail -n 20"}))
```

(4) Phân tích cơ sở mã

Hỗ trợ rà soát và hiểu mã:

```python
terminal = TerminalTool(workspace="./codebase")

# Thống kê số dòng mã
print(terminal.run({"command": "find . -name '*.py' -exec wc -l {} + | tail -n 1"}))

# Tìm tất cả chú thích TODO
print(terminal.run({"command": "grep -rn 'TODO' --include='*.py'"}))

# Tìm định nghĩa của hàm cụ thể
print(terminal.run({"command": "grep -rn 'def process_data' --include='*.py'"}))

# Xem hiện thực của hàm
print(terminal.run({"command": "sed -n '/def process_data/,/^def /p' src/processor.py | head -n -1"}))
```

### 9.5.4 Phối hợp với các công cụ khác

Sức mạnh thực sự của TerminalTool nằm ở việc phối hợp sử dụng với MemoryTool, NoteTool và ContextBuilder.

(1) Phối hợp với MemoryTool

Thông tin mà TerminalTool phát hiện có thể lưu vào hệ thống bộ nhớ:

```python
# Dùng TerminalTool khám phá cấu trúc dự án
structure = terminal.run({"command": "tree -L 2 src"})

# Lưu vào bộ nhớ ngữ nghĩa
memory_tool.run({
    "action": "add",
    "content": f"Cấu trúc dự án:\n{structure}",
    "memory_type": "semantic",
    "importance": 0.8,
    "metadata": {"type": "project_structure"}
})
```

(2) Phối hợp với NoteTool

Những phát hiện quan trọng có thể được ghi thành ghi chú có cấu trúc:

```python
# Phát hiện một nút thắt hiệu năng
log_analysis = terminal.run({"command": "grep 'slow query' app.log | tail -n 10"})

# Ghi thành ghi chú blocker
note_tool.run({
    "action": "create",
    "title": "Vấn đề truy vấn chậm cơ sở dữ liệu",
    "content": f"## Mô tả vấn đề\nPhát hiện nhiều truy vấn chậm, ảnh hưởng hiệu năng hệ thống\n\n## Phân tích nhật ký\n```\n{log_analysis}\n```\n\n## Bước tiếp theo\n1. Phân tích SQL truy vấn chậm\n2. Thêm chỉ mục\n3. Tối ưu logic truy vấn",
    "note_type": "blocker",
    "tags": ["performance", "database"]
})
```

(3) Phối hợp với ContextBuilder

Đầu ra của TerminalTool có thể trở thành một phần của ngữ cảnh:

```python
# Khám phá cơ sở mã
code_structure = terminal.run({"command": "ls -R src"})
recent_changes = terminal.run({"command": "git log --oneline -10"})

# Chuyển thành ContextPacket
from hello_agents.context import ContextPacket
from datetime import datetime

packets = [
    ContextPacket(
        content=f"Cấu trúc cơ sở mã:\n{code_structure}",
        timestamp=datetime.now(),
        token_count=len(code_structure) // 4,
        relevance_score=0.7,
        metadata={"type": "code_structure", "source": "terminal"}
    ),
    ContextPacket(
        content=f"Các commit gần đây:\n{recent_changes}",
        timestamp=datetime.now(),
        token_count=len(recent_changes) // 4,
        relevance_score=0.8,
        metadata={"type": "git_history", "source": "terminal"}
    )
]

# Đưa thông tin này vào khi xây dựng ngữ cảnh
context = context_builder.build(
    user_query="Làm thế nào để tái cấu trúc mô-đun dịch vụ người dùng?",
    custom_packets=packets
)
```

## 9.6 Thực chiến Agent dài hạn: trợ lý bảo trì cơ sở mã

Bây giờ, chúng ta hãy tích hợp ContextBuilder, NoteTool và TerminalTool để xây dựng một Agent dài hạn hoàn chỉnh — <strong>trợ lý bảo trì cơ sở mã</strong>. Trợ lý này có thể:

1. Khám phá và hiểu cấu trúc cơ sở mã
2. Ghi lại các vấn đề và điểm cải tiến phát hiện được
3. Theo dõi nhiệm vụ tái cấu trúc dài hạn
4. Duy trì tính liên tục dưới giới hạn cửa sổ ngữ cảnh

### 9.6.1 Thiết lập kịch bản và phân tích yêu cầu

<strong>Kịch bản nghiệp vụ</strong>

Giả sử chúng ta đang bảo trì một ứng dụng web Python quy mô trung bình, cơ sở mã này gồm khoảng 50 tệp Python, xây dựng bằng framework Flask, bao phủ nhiều mô-đun như mô hình dữ liệu, logic nghiệp vụ, giao diện API, đồng thời tồn tại một số nợ kỹ thuật cần dọn dẹp dần. Trong kịch bản này, chúng ta cần một trợ lý thông minh giúp chúng ta khám phá cơ sở mã, hiểu cấu trúc dự án, quan hệ phụ thuộc và phong cách mã; nhận diện vấn đề trong mã, như trùng lặp mã, độ phức tạp quá cao, thiếu kiểm thử; theo dõi tiến độ nhiệm vụ, ghi lại việc cần làm, công việc đã hoàn thành và điểm tắc gặp phải; và dựa trên ngữ cảnh lịch sử đưa ra khuyến nghị tái cấu trúc nhất quán.

<strong>Thách thức và giải pháp</strong>

Kịch bản này đối mặt với vài thách thức nhiệm vụ dài hạn tiêu biểu. Đầu tiên là vấn đề lượng thông tin vượt cửa sổ ngữ cảnh: toàn bộ cơ sở mã có thể chứa hàng chục nghìn dòng mã, không thể đặt hết vào cửa sổ ngữ cảnh trong một lần; chúng ta giải quyết bằng cách dùng TerminalTool để khám phá mã tức thời, theo nhu cầu, chỉ xem tệp cụ thể khi cần. Thứ hai là thách thức quản lý trạng thái xuyên phiên: nhiệm vụ tái cấu trúc có thể kéo dài nhiều ngày, cần giữ tiến độ qua nhiều phiên; chúng ta dùng NoteTool ghi lại tiến triển theo giai đoạn, việc cần làm và quyết định then chốt để đối phó. Cuối cùng là vấn đề chất lượng và mức liên quan của ngữ cảnh: mỗi cuộc hội thoại cần xem lại thông tin lịch sử liên quan, nhưng không bị nhấn chìm bởi thông tin không liên quan; chúng ta dùng ContextBuilder sàng lọc và tổ chức ngữ cảnh thông minh, đảm bảo mật độ tín hiệu cao.

### 9.6.2 Thiết kế kiến trúc hệ thống

Trợ lý bảo trì cơ sở mã của chúng ta dùng kiến trúc ba tầng, như Hình 9.3:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/9-figures/9-3.png" alt="" width="85%"/>
  <p>Hình 9.3 Kiến trúc ba tầng của trợ lý bảo trì cơ sở mã</p>
</div>


### 9.6.3 Hiện thực cốt lõi

Bây giờ chúng ta hãy hiện thực lớp cốt lõi của hệ thống này:

```python
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.context import ContextBuilder, ContextConfig, ContextPacket
from hello_agents.tools import MemoryTool, NoteTool, TerminalTool
from hello_agents.core.message import Message


class CodebaseMaintainer:
    """Trợ lý bảo trì cơ sở mã - ví dụ Agent dài hạn

    Tích hợp ContextBuilder + NoteTool + TerminalTool + MemoryTool
    Hiện thực quản lý nhiệm vụ bảo trì cơ sở mã xuyên phiên
    """

    def __init__(
        self,
        project_name: str,
        codebase_path: str,
        llm: Optional[HelloAgentsLLM] = None
    ):
        self.project_name = project_name
        self.codebase_path = codebase_path
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Khởi tạo LLM
        self.llm = llm or HelloAgentsLLM()

        # Khởi tạo công cụ
        self.memory_tool = MemoryTool(user_id=project_name)
        self.note_tool = NoteTool(workspace=f"./{project_name}_notes")
        self.terminal_tool = TerminalTool(workspace=codebase_path, timeout=60)

        # Khởi tạo trình xây dựng ngữ cảnh
        self.context_builder = ContextBuilder(
            memory_tool=self.memory_tool,
            rag_tool=None,  # Trường hợp này không dùng RAG
            config=ContextConfig(
                max_tokens=4000,
                reserve_ratio=0.15,
                min_relevance=0.2,
                enable_compression=True
            )
        )

        # Lịch sử hội thoại
        self.conversation_history: List[Message] = []

        # Thông tin thống kê
        self.stats = {
            "session_start": datetime.now(),
            "commands_executed": 0,
            "notes_created": 0,
            "issues_found": 0
        }

        print(f"✅ Trợ lý bảo trì cơ sở mã đã khởi tạo: {project_name}")
        print(f"📁 Thư mục làm việc: {codebase_path}")
        print(f"🆔 ID phiên: {self.session_id}")

    def run(self, user_input: str, mode: str = "auto") -> str:
        """Chạy trợ lý

        Args:
            user_input: Đầu vào của người dùng
            mode: Chế độ chạy
                - "auto": tự động quyết định có dùng công cụ hay không
                - "explore": thiên về khám phá mã
                - "analyze": thiên về phân tích vấn đề
                - "plan": thiên về quy hoạch nhiệm vụ

        Returns:
            str: Câu trả lời của trợ lý
        """
        print(f"\n{'='*80}")
        print(f"👤 Người dùng: {user_input}")
        print(f"{'='*80}\n")

        # Bước một: thực hiện tiền xử lý theo chế độ
        pre_context = self._preprocess_by_mode(user_input, mode)

        # Bước hai: truy xuất ghi chú liên quan
        relevant_notes = self._retrieve_relevant_notes(user_input)
        note_packets = self._notes_to_packets(relevant_notes)

        # Bước ba: xây dựng ngữ cảnh được tối ưu
        context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.conversation_history,
            system_instructions=self._build_system_instructions(mode),
            custom_packets=note_packets + pre_context
        )

        # Bước bốn: gọi LLM
        print("🤖 Đang suy nghĩ...")
        response = self.llm.invoke(context)

        # Bước năm: hậu xử lý
        self._postprocess_response(user_input, response)

        # Bước sáu: cập nhật lịch sử hội thoại
        self._update_history(user_input, response)

        print(f"\n🤖 Trợ lý: {response}\n")
        print(f"{'='*80}\n")

        return response

    def _preprocess_by_mode(
        self,
        user_input: str,
        mode: str
    ) -> List[ContextPacket]:
        """Thực hiện tiền xử lý theo chế độ, thu thập thông tin liên quan"""
        packets = []

        if mode == "explore" or mode == "auto":
            # Chế độ khám phá: tự động xem cấu trúc dự án
            print("🔍 Đang khám phá cấu trúc cơ sở mã...")

            structure = self.terminal_tool.run({"command": "find . -type f -name '*.py' | head -n 20"})
            self.stats["commands_executed"] += 1

            packets.append(ContextPacket(
                content=f"[Cấu trúc cơ sở mã]\n{structure}",
                timestamp=datetime.now(),
                token_count=len(structure) // 4,
                relevance_score=0.6,
                metadata={"type": "code_structure", "source": "terminal"}
            ))

        if mode == "analyze":
            # Chế độ phân tích: kiểm tra độ phức tạp và vấn đề của mã
            print("📊 Đang phân tích chất lượng mã...")

            # Thống kê số dòng mã
            loc = self.terminal_tool.run({"command": "find . -name '*.py' -exec wc -l {} + | tail -n 1"})

            # Tìm TODO và FIXME
            todos = self.terminal_tool.run({"command": "grep -rn 'TODO\\|FIXME' --include='*.py' | head -n 10"})

            self.stats["commands_executed"] += 2

            packets.append(ContextPacket(
                content=f"[Thống kê mã]\n{loc}\n\n[Việc cần làm]\n{todos}",
                timestamp=datetime.now(),
                token_count=(len(loc) + len(todos)) // 4,
                relevance_score=0.7,
                metadata={"type": "code_analysis", "source": "terminal"}
            ))

        if mode == "plan":
            # Chế độ quy hoạch: nạp các ghi chú gần đây
            print("📋 Đang nạp quy hoạch nhiệm vụ...")

            task_notes = self.note_tool.run({
                "action": "list",
                "note_type": "task_state",
                "limit": 3
            })

            if task_notes:
                content = "\n".join([f"- {note['title']}" for note in task_notes])
                packets.append(ContextPacket(
                    content=f"[Nhiệm vụ hiện tại]\n{content}",
                    timestamp=datetime.now(),
                    token_count=len(content) // 4,
                    relevance_score=0.8,
                    metadata={"type": "task_plan", "source": "notes"}
                ))

        return packets

    def _retrieve_relevant_notes(self, query: str, limit: int = 3) -> List[Dict]:
        """Truy xuất ghi chú liên quan"""
        try:
            # Ưu tiên truy xuất blocker
            blockers = self.note_tool.run({
                "action": "list",
                "note_type": "blocker",
                "limit": 2
            })

            # Tìm kiếm ghi chú liên quan
            search_results = self.note_tool.run({
                "action": "search",
                "query": query,
                "limit": limit
            })

            # Hợp nhất và loại trùng
            all_notes = {note.get('note_id') or note.get('id'): note for note in (blockers or []) + (search_results or [])}
            return list(all_notes.values())[:limit]

        except Exception as e:
            print(f"[WARNING] Truy xuất ghi chú thất bại: {e}")
            return []

    def _notes_to_packets(self, notes: List[Dict]) -> List[ContextPacket]:
        """Chuyển ghi chú thành gói ngữ cảnh"""
        packets = []

        for note in notes:
            # Đặt điểm mức liên quan khác nhau theo loại ghi chú
            relevance_map = {
                "blocker": 0.9,
                "action": 0.8,
                "task_state": 0.75,
                "conclusion": 0.7
            }

            note_type = note.get('type', 'general')
            relevance = relevance_map.get(note_type, 0.6)

            content = f"[Ghi chú: {note.get('title', 'Untitled')}]\nLoại: {note_type}\n\n{note.get('content', '')}"

            packets.append(ContextPacket(
                content=content,
                timestamp=datetime.fromisoformat(note.get('updated_at', datetime.now().isoformat())),
                token_count=len(content) // 4,
                relevance_score=relevance,
                metadata={
                    "type": "note",
                    "note_type": note_type,
                    "note_id": note.get('note_id') or note.get('id')
                }
            ))

        return packets

    def _build_system_instructions(self, mode: str) -> str:
        """Xây dựng chỉ dẫn hệ thống"""
        base_instructions = f"""Bạn là trợ lý bảo trì cơ sở mã của dự án {self.project_name}.

Năng lực cốt lõi của bạn:
1. Dùng TerminalTool khám phá cơ sở mã (ls, cat, grep, find, v.v.)
2. Dùng NoteTool ghi lại phát hiện và nhiệm vụ
3. Dựa trên ghi chú lịch sử đưa ra khuyến nghị nhất quán

ID phiên hiện tại: {self.session_id}
"""

        mode_specific = {
            "explore": """
Chế độ hiện tại: khám phá cơ sở mã

Bạn nên:
- Chủ động dùng lệnh terminal để hiểu cấu trúc mã
- Nhận diện các mô-đun và tệp then chốt
- Ghi kiến trúc dự án vào ghi chú
""",
            "analyze": """
Chế độ hiện tại: phân tích chất lượng mã

Bạn nên:
- Tìm vấn đề trong mã (trùng lặp, độ phức tạp, TODO, v.v.)
- Đánh giá chất lượng mã
- Ghi các vấn đề phát hiện thành ghi chú blocker hoặc action
""",
            "plan": """
Chế độ hiện tại: quy hoạch nhiệm vụ

Bạn nên:
- Xem lại ghi chú và nhiệm vụ lịch sử
- Xây dựng kế hoạch hành động tiếp theo
- Cập nhật ghi chú trạng thái nhiệm vụ
""",
            "auto": """
Chế độ hiện tại: tự động ra quyết định

Bạn nên:
- Chọn chiến lược linh hoạt theo nhu cầu người dùng
- Dùng công cụ khi cần
- Giữ câu trả lời chuyên nghiệp và thực dụng
"""
        }

        return base_instructions + mode_specific.get(mode, mode_specific["auto"])

    def _postprocess_response(self, user_input: str, response: str):
        """Hậu xử lý: phân tích câu trả lời, tự động ghi lại thông tin quan trọng"""

        # Nếu phát hiện vấn đề, tự động tạo ghi chú blocker
        if any(keyword in response.lower() for keyword in ["vấn đề", "bug", "lỗi", "tắc"]):
            try:
                self.note_tool.run({
                    "action": "create",
                    "title": f"Phát hiện vấn đề: {user_input[:30]}...",
                    "content": f"## Đầu vào người dùng\n{user_input}\n\n## Phân tích vấn đề\n{response[:500]}...",
                    "note_type": "blocker",
                    "tags": [self.project_name, "auto_detected", self.session_id]
                })
                self.stats["notes_created"] += 1
                self.stats["issues_found"] += 1
                print("📝 Đã tự động tạo ghi chú vấn đề")
            except Exception as e:
                print(f"[WARNING] Tạo ghi chú thất bại: {e}")

        # Nếu là quy hoạch nhiệm vụ, tự động tạo ghi chú action
        elif any(keyword in user_input.lower() for keyword in ["kế hoạch", "bước tiếp theo", "nhiệm vụ", "todo"]):
            try:
                self.note_tool.run({
                    "action": "create",
                    "title": f"Quy hoạch nhiệm vụ: {user_input[:30]}...",
                    "content": f"## Thảo luận\n{user_input}\n\n## Kế hoạch hành động\n{response[:500]}...",
                    "note_type": "action",
                    "tags": [self.project_name, "planning", self.session_id]
                })
                self.stats["notes_created"] += 1
                print("📝 Đã tự động tạo ghi chú kế hoạch hành động")
            except Exception as e:
                print(f"[WARNING] Tạo ghi chú thất bại: {e}")

    def _update_history(self, user_input: str, response: str):
        """Cập nhật lịch sử hội thoại"""
        self.conversation_history.append(
            Message(content=user_input, role="user", timestamp=datetime.now())
        )
        self.conversation_history.append(
            Message(content=response, role="assistant", timestamp=datetime.now())
        )

        # Giới hạn độ dài lịch sử (giữ 10 vòng hội thoại gần nhất)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    # === Phương thức tiện lợi ===

    def explore(self, target: str = ".") -> str:
        """Khám phá cơ sở mã"""
        return self.run(f"Hãy khám phá cấu trúc mã của {target}", mode="explore")

    def analyze(self, focus: str = "") -> str:
        """Phân tích chất lượng mã"""
        query = f"Hãy phân tích chất lượng mã" + (f", tập trung vào {focus}" if focus else "")
        return self.run(query, mode="analyze")

    def plan_next_steps(self) -> str:
        """Quy hoạch nhiệm vụ tiếp theo"""
        return self.run("Dựa trên tiến độ hiện tại, hãy quy hoạch nhiệm vụ tiếp theo", mode="plan")

    def execute_command(self, command: str) -> str:
        """Thực thi lệnh terminal"""
        result = self.terminal_tool.run({"command": command})
        self.stats["commands_executed"] += 1
        return result

    def create_note(
        self,
        title: str,
        content: str,
        note_type: str = "general",
        tags: List[str] = None
    ) -> str:
        """Tạo ghi chú"""
        result = self.note_tool.run({
            "action": "create",
            "title": title,
            "content": content,
            "note_type": note_type,
            "tags": tags or [self.project_name]
        })
        self.stats["notes_created"] += 1
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Lấy thông tin thống kê"""
        duration = (datetime.now() - self.stats["session_start"]).total_seconds()

        # Lấy tóm tắt ghi chú
        try:
            note_summary = self.note_tool.run({"action": "summary"})
        except:
            note_summary = {}

        return {
            "session_info": {
                "session_id": self.session_id,
                "project": self.project_name,
                "duration_seconds": duration
            },
            "activity": {
                "commands_executed": self.stats["commands_executed"],
                "notes_created": self.stats["notes_created"],
                "issues_found": self.stats["issues_found"]
            },
            "notes": note_summary
        }

    def generate_report(self, save_to_file: bool = True) -> Dict[str, Any]:
        """Tạo báo cáo phiên"""
        report = self.get_stats()

        if save_to_file:
            report_file = f"maintainer_report_{self.session_id}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            report["report_file"] = report_file
            print(f"📄 Báo cáo đã được lưu: {report_file}")

        return report
```

### 9.6.4 Ví dụ sử dụng hoàn chỉnh

Bây giờ chúng ta hãy xem một kịch bản sử dụng hoàn chỉnh, trình bày quy trình làm việc của Agent dài hạn này:

```python
# ========== Khởi tạo trợ lý ==========

from hello_agents import HelloAgentsLLM

maintainer = CodebaseMaintainer(
    project_name="my_flask_app",
    codebase_path="./my_flask_app",
    llm=HelloAgentsLLM()
)


# ========== Ngày thứ nhất: khám phá cơ sở mã ==========
# 1. Khám phá ban đầu
response = maintainer.explore()
"""
🔍 Đang khám phá cấu trúc cơ sở mã...
🤖 Đang suy nghĩ...

🤖 Trợ lý: Tôi đã quét cơ sở mã, đây là một ứng dụng web Flask, chủ yếu gồm các mô-đun sau:

📁 Cấu trúc dự án:
- app/
  ├── models/      # Mô hình dữ liệu (User, Product, Order, v.v.)
  ├── routes/      # Định tuyến API
  ├── services/    # Logic nghiệp vụ
  └── utils/       # Hàm tiện ích
- tests/           # Tệp kiểm thử
- migrations/      # Di cư cơ sở dữ liệu
- config.py        # Tệp cấu hình

Tổng cộng khoảng 3.500 dòng mã Python.

Khuyến nghị bước tiếp theo:
1. Xem định nghĩa các mô hình cốt lõi
2. Kiểm tra định tuyến và thiết kế API
3. Đánh giá độ phủ kiểm thử
"""

# 2. Phân tích sâu một mô-đun
response = maintainer.run("Hãy phân tích thiết kế mô hình dữ liệu trong thư mục app/models/")
"""
🤖 Trợ lý: Tôi đã xem thư mục app/models/, phát hiện các mô hình dữ liệu sau:

1. User (user.py)
   - Trường: id, username, email, password_hash, created_at
   - Quan hệ: một-nhiều với Order
   - Vấn đề: ⚠️ Thiếu chỉ mục, trường email chưa đặt ràng buộc duy nhất

2. Product (product.py)
   - Trường: id, name, description, price, stock
   - Vấn đề: ✅ Thiết kế hợp lý

3. Order (order.py)
   - Trường: id, user_id, product_id, quantity, status
   - Vấn đề: ⚠️ Thiếu trường thời gian tạo, không thuận lợi cho phân tích dữ liệu

Khuyến nghị:
1. Thêm ràng buộc duy nhất cho User.email
2. Thêm trường created_at và updated_at cho Order
3. Cân nhắc thêm hỗ trợ xóa mềm

Tôi đã ghi các vấn đề này thành ghi chú blocker.
"""
# [Tự động tạo ghi chú blocker]


# ========== Ngày thứ hai: phân tích chất lượng mã ==========

# 1. Phân tích chất lượng tổng thể
response = maintainer.analyze()
"""
📊 Đang phân tích chất lượng mã...
🤖 Đang suy nghĩ...

🤖 Trợ lý: Báo cáo phân tích chất lượng mã:

📊 Thống kê mã:
- Tổng số dòng: 3.542 dòng
- Độ dài tệp trung bình: khoảng 150 dòng
- Tệp lớn nhất: services/order_service.py (456 dòng)

⚠️ Vấn đề phát hiện:

1. Trùng lặp mã (HIGH):
   - user_service.py và product_service.py có logic CRUD tương tự
   - Khuyến nghị: trích xuất lớp cơ sở BaseService

2. Độ phức tạp quá cao (MEDIUM):
   - Phương thức order_service.py::process_order có 8 tầng lồng nhau
   - Khuyến nghị: tách thành nhiều phương thức nhỏ

3. Thiếu kiểm thử (HIGH):
   - Độ phủ kiểm thử chỉ 45%
   - Thư mục services/ hoàn toàn không có kiểm thử

4. TODO/FIXME (12 mục):
   - Phần lớn là chú thích kiểu "tối ưu sau"
   - Khuyến nghị: dọn dẹp hoặc chuyển thành nhiệm vụ chính thức

Tôi đã ghi các vấn đề này thành ghi chú, và đánh dấu mức ưu tiên.
"""
# [Tự động tạo nhiều ghi chú blocker]

# 2. Xem vấn đề cụ thể
response = maintainer.run("Hãy xem phương thức process_order của order_service.py, đưa ra khuyến nghị tái cấu trúc")
"""
🤖 Trợ lý: Tôi đã xem mã của phương thức process_order:

[Mã gốc]
def process_order(self, order_id):
    order = Order.query.get(order_id)
    if order:
        if order.status == 'pending':
            product = Product.query.get(order.product_id)
            if product:
                if product.stock >= order.quantity:
                    # ... 8 tầng lồng nhau tiếp tục ...

[Phân tích vấn đề]
1. Lồng nhau quá sâu khiến khó đọc
2. Thiếu xử lý lỗi
3. Logic nghiệp vụ trộn lẫn với truy cập dữ liệu

[Khuyến nghị tái cấu trúc]
def process_order(self, order_id):
    # 1. Mô thức trả về sớm, giảm lồng nhau
    order = self._get_order(order_id)
    if not order or order.status != 'pending':
        return False

    # 2. Tách phương thức, trách nhiệm đơn nhất
    if not self._check_stock(order):
        return False

    # 3. Dùng giao dịch để đảm bảo nhất quán
    with db.transaction():
        self._update_stock(order)
        self._update_order_status(order, 'processing')

    return True

[Bước tiếp theo]
1. Tôi đã tạo ghi chú kế hoạch tái cấu trúc
2. Khuyến nghị viết ca kiểm thử trước
3. Tái cấu trúc từng bước, giữ nguyên chức năng
"""
# [Tự động tạo ghi chú action]


# ========== Ngày thứ ba: quy hoạch nhiệm vụ tái cấu trúc ==========

# 1. Xem lại tiến độ
response = maintainer.plan_next_steps()
"""
📋 Đang nạp quy hoạch nhiệm vụ...
🤖 Đang suy nghĩ...

🤖 Trợ lý: Dựa trên khám phá và phân tích hai ngày trước, tôi đã sắp xếp mức ưu tiên nhiệm vụ tái cấu trúc:

🔴 Ưu tiên cao (hoàn thành trong tuần này):
1. [blocker] Thêm ràng buộc duy nhất cho User.email
   - Rủi ro: thấp, chỉ là di cư cơ sở dữ liệu
   - Khối lượng: 1 giờ

2. [blocker] Trích xuất BaseService giảm trùng lặp mã
   - Rủi ro: trung bình, ảnh hưởng nhiều lớp dịch vụ
   - Khối lượng: nửa ngày

3. [blocker] Tái cấu trúc phương thức process_order
   - Rủi ro: cao, logic nghiệp vụ cốt lõi
   - Khối lượng: 1 ngày (bao gồm viết kiểm thử)

🟡 Ưu tiên trung bình (tuần sau):
4. Thêm kiểm thử đơn vị cho services/
5. Dọn dẹp chú thích TODO
6. Thêm trường thời gian cho Order

🟢 Ưu tiên thấp (chưa định):
7. Tối ưu hiệu năng
8. Cập nhật tài liệu

Khuyến nghị:
- Tuần này giải quyết vấn đề mô hình dữ liệu trước (nhiệm vụ 1, 6)
- Tuần sau tái cấu trúc mã (nhiệm vụ 2, 3)
- Liên tục tăng độ phủ kiểm thử (nhiệm vụ 4)

Tôi đã cập nhật ghi chú trạng thái nhiệm vụ, bạn có thể xem tiến độ bất cứ lúc nào.
"""

# 2. Tạo thủ công kế hoạch tái cấu trúc chi tiết
maintainer.create_note(
    title="Kế hoạch tái cấu trúc tuần này - Week 1",
    content="""## Mục tiêu
Hoàn thành tối ưu tầng mô hình dữ liệu

## Danh sách nhiệm vụ
- [ ] Thêm ràng buộc duy nhất cho User.email
- [ ] Thêm trường created_at, updated_at cho Order
- [ ] Viết script di cư cơ sở dữ liệu
- [ ] Cập nhật các ca kiểm thử liên quan

## Sắp xếp thời gian
- Thứ hai: thiết kế script di cư
- Thứ ba - thứ tư: thực thi di cư và kiểm thử
- Thứ năm: cập nhật ca kiểm thử
- Thứ sáu: Code Review

## Rủi ro
- Di cư cơ sở dữ liệu có thể ảnh hưởng môi trường trực tuyến, cần thực thi ngoài giờ cao điểm
- Dữ liệu hiện có có thể có email trùng lặp, cần dọn dẹp trước
""",
    note_type="task_state",
    tags=["refactoring", "week1", "high_priority"]
)

print("✅ Đã tạo kế hoạch tái cấu trúc chi tiết")


# ========== Một tuần sau: kiểm tra tiến độ ==========

# Xem tóm tắt ghi chú
summary = maintainer.note_tool.run({"action": "summary"})
print("📊 Tóm tắt ghi chú:")
print(json.dumps(summary, indent=2, ensure_ascii=False))
"""
{
  "total_notes": 8,
  "type_distribution": {
    "blocker": 3,
    "action": 2,
    "task_state": 2,
    "conclusion": 1
  },
  "recent_notes": [
    {
      "id": "note_20250119_160000_7",
      "title": "Kế hoạch tái cấu trúc tuần này - Week 1",
      "type": "task_state",
      "updated_at": "2025-01-19T16:00:00"
    },
    ...
  ]
}
"""

# Tạo báo cáo hoàn chỉnh
report = maintainer.generate_report()
print("\n📄 Báo cáo phiên:")
print(json.dumps(report, indent=2, ensure_ascii=False))
"""
{
  "session_info": {
    "session_id": "session_20250119_150000",
    "project": "my_flask_app",
    "duration_seconds": 172800  # 2 ngày
  },
  "activity": {
    "commands_executed": 24,
    "notes_created": 8,
    "issues_found": 3
  },
  "notes": { ... }
}
"""
```

### 9.6.5 Phân tích hiệu quả chạy

Qua trường hợp hoàn chỉnh này, chúng ta có thể thấy vài đặc tính then chốt của Agent dài hạn. Đầu tiên là tính liên tục xuyên phiên: Agent duy trì tính liên tục nhiệm vụ qua nhiều ngày, nhiều phiên nhờ NoteTool; vấn đề khám phá ngày thứ nhất được tự động cân nhắc khi phân tích ngày thứ hai, khi quy hoạch ngày thứ ba có thể tổng hợp toàn bộ phát hiện của hai ngày trước, và khi kiểm tra sau một tuần toàn bộ lịch sử đều được giữ lại. Thứ hai là quản lý ngữ cảnh thông minh: ContextBuilder đảm bảo mỗi cuộc hội thoại đều có ngữ cảnh chất lượng cao, tự động tập hợp ghi chú liên quan (đặc biệt là loại blocker), điều chỉnh động chiến lược tiền xử lý theo chế độ hội thoại, chọn thông tin liên quan nhất trong ngân sách token.

Đặc tính thứ ba là truy cập hệ thống tệp tức thời: TerminalTool hỗ trợ khám phá mã linh hoạt, không cần lập chỉ mục trước toàn bộ cơ sở mã, có thể xem nội dung tệp cụ thể ngay lập tức, hỗ trợ xử lý văn bản phức tạp (grep, awk, v.v.). Thứ tư là quản lý tri thức tự động hóa: hệ thống tự động quản lý tri thức phát hiện được, tự động tạo ghi chú blocker khi phát hiện vấn đề, tự động tạo ghi chú action khi thảo luận kế hoạch, tự động lưu thông tin then chốt vào hệ thống bộ nhớ. Cuối cùng là hợp tác người-máy: hệ thống này hỗ trợ mô thức hợp tác người-máy linh hoạt, Agent có thể tự động hoàn thành khám phá và phân tích, con người có thể can thiệp và định hướng qua hệ thống ghi chú, hỗ trợ tạo thủ công ghi chú kế hoạch chi tiết.

Khung nền tảng này có thể mở rộng thêm, ví dụ tích hợp RAGTool để xây chỉ mục vector cho cơ sở mã kết hợp truy xuất ngữ nghĩa, tách thành các vai trò chuyên biệt người khám phá, người phân tích, người quy hoạch để hiện thực hợp tác đa Agent, tích hợp công cụ kiểm thử để tự động xác minh kết quả tái cấu trúc, thực thi lệnh git qua TerminalTool để theo dõi thay đổi mã, hoặc dùng Gradio/Streamlit xây giao diện trực quan.

## 9.7 Tóm tắt chương

Trong chương này, chúng ta đã đi sâu vào nền tảng lý thuyết và thực hành kỹ thuật của kỹ thuật ngữ cảnh:

### Về lý thuyết

1. <strong>Bản chất của kỹ thuật ngữ cảnh</strong>: sự tiến hóa từ "kỹ thuật prompt" sang "kỹ thuật ngữ cảnh", cốt lõi là quản lý ngân sách chú ý hữu hạn
2. <strong>Sự ăn mòn ngữ cảnh</strong>: hiểu sự suy giảm hiệu năng do ngữ cảnh dài mang lại, nhận thức rằng ngữ cảnh là tài nguyên khan hiếm
3. <strong>Ba chiến lược lớn</strong>: nén tích hợp, ghi chú có cấu trúc, kiến trúc sub-agent

### Về thực hành kỹ thuật

1. <strong>ContextBuilder</strong>: hiện thực quy trình GSSC, cung cấp giao diện quản lý ngữ cảnh thống nhất
2. <strong>NoteTool</strong>: định dạng kết hợp Markdown+YAML, hỗ trợ bộ nhớ dài hạn có cấu trúc
3. <strong>TerminalTool</strong>: công cụ dòng lệnh an toàn, hỗ trợ truy cập hệ thống tệp tức thời
4. <strong>Agent dài hạn</strong>: tích hợp ba công cụ lớn, xây dựng trợ lý bảo trì cơ sở mã xuyên phiên

### Thu hoạch cốt lõi

- <strong>Thiết kế phân tầng</strong>: truy cập tức thời (TerminalTool) + bộ nhớ phiên (MemoryTool) + ghi chú bền vững (NoteTool)
- <strong>Sàng lọc thông minh</strong>: cơ chế chấm điểm dựa trên mức liên quan và độ mới
- <strong>An toàn là trên hết</strong>: nhiều lớp cơ chế bảo mật đảm bảo hệ thống ổn định
- <strong>Hợp tác người-máy</strong>: cân bằng giữa tự động hóa và khả năng kiểm soát

Qua việc học chương này, bạn không chỉ nắm vững kỹ thuật cốt lõi của kỹ thuật ngữ cảnh, mà quan trọng hơn là hiểu cách xây dựng những hệ thống Agent có thể duy trì tính liên tục và hiệu quả trong khoảng thời gian dài. Những kỹ năng này sẽ trở thành nền tảng quan trọng để bạn xây dựng ứng dụng Agent cấp sản xuất.

Ở chương tiếp theo, chúng ta sẽ thảo luận về giao thức giao tiếp của Agent, học cách để Agent tương tác rộng hơn với thế giới bên ngoài.

## Bài tập

> <strong>Lưu ý</strong>: một số bài tập không có đáp án chuẩn, trọng tâm là bồi dưỡng năng lực hiểu tổng hợp và thực hành của người học về kỹ thuật ngữ cảnh và quản lý nhiệm vụ dài hạn.

1. Chương này giới thiệu sự khác biệt giữa kỹ thuật ngữ cảnh và kỹ thuật prompt. Hãy phân tích:

   - Trong mục 9.1 có nêu "ngữ cảnh phải được coi là một tài nguyên hữu hạn, và có lợi ích biên giảm dần". Hãy giải thích hiện tượng "sự ăn mòn ngữ cảnh" (context rot) là gì? Vì sao ngay cả khi mô hình hỗ trợ cửa sổ ngữ cảnh 100K thậm chí 200K, chúng ta vẫn cần quản lý ngữ cảnh cẩn trọng?
   - Giả sử bạn cần xây dựng một "trợ lý rà soát mã", cần phân tích một cơ sở mã gồm 50 tệp. Hãy so sánh hai chiến lược: (1) nạp toàn bộ nội dung tất cả tệp vào ngữ cảnh một lần; (2) dùng ngữ cảnh JIT (Just-in-time), truy xuất tệp theo nhu cầu qua công cụ. Phân tích ưu nhược điểm và kịch bản phù hợp của mỗi cách.
   - Trong mục 9.2.1 có nêu hai thái cực sai lầm của system prompt: "mã hóa cứng quá mức" và "quá chung chung". Hãy mỗi loại nêu một ví dụ thực tế, và giải thích cách tìm điểm cân bằng phù hợp.

2. Quy trình GSSC (Gather-Select-Structure-Compress) là kỹ thuật cốt lõi của chương này. Hãy suy nghĩ sâu:

   > <strong>Lưu ý</strong>: đây là bài tập thực hành, khuyến nghị thao tác thực tế

   - Trong hiện thực ContextBuilder ở mục 9.3, bốn giai đoạn có trách nhiệm khác nhau. Hãy phân tích: nếu một giai đoạn mất hiệu lực (ví dụ giai đoạn Select chọn thông tin không liên quan, hoặc giai đoạn Compress nén quá mức gây mất thông tin), sẽ ảnh hưởng thế nào đến hiệu năng cuối cùng của Agent?
   - Dựa trên mã ở mục 9.3.4, hãy thêm cho ContextBuilder một chức năng "đánh giá chất lượng ngữ cảnh": sau mỗi lần xây dựng ngữ cảnh, tự động đánh giá mật độ thông tin, mức liên quan và tính đầy đủ của ngữ cảnh, đồng thời đưa ra khuyến nghị tối ưu.
   - Giai đoạn "nén" trong quy trình GSSC dùng LLM để tóm tắt thông minh. Hãy suy nghĩ: trong trường hợp nào, chiến lược cắt đơn giản (truncation) hoặc cửa sổ trượt (sliding window) có thể phù hợp hơn tóm tắt bằng LLM? Hãy thiết kế một chiến lược nén kết hợp, tận dụng ưu điểm của nhiều phương pháp nén.

3. NoteTool và TerminalTool là công cụ then chốt hỗ trợ nhiệm vụ dài hạn. Dựa trên nội dung mục 9.4 và 9.5, hãy hoàn thành các thực hành mở rộng sau:

   > <strong>Lưu ý</strong>: đây là bài tập thực hành, khuyến nghị thao tác thực tế

   - NoteTool dùng hệ thống ghi chú phân tầng (ghi chú dự án, ghi chú nhiệm vụ, ghi chú tạm thời). Hãy thiết kế một cơ chế "tự động sắp xếp ghi chú": khi ghi chú tạm thời tích lũy đến một số lượng nhất định, Agent có thể tự động phân tích các ghi chú này, nâng thông tin quan trọng thành ghi chú nhiệm vụ hoặc ghi chú dự án, và dọn dẹp nội dung dư thừa.
   - TerminalTool cung cấp năng lực thao tác hệ thống tệp, nhưng trong mục 9.5.2 đã nhấn mạnh thiết kế an toàn. Hãy phân tích: cơ chế bảo mật hiện tại (xác minh đường dẫn, danh sách trắng lệnh, kiểm tra quyền) đã đủ chưa? Nếu Agent cần truy cập tệp nhạy cảm hoặc thực thi thao tác nguy hiểm, nên thiết kế quy trình "phê duyệt hợp tác người-máy" thế nào?
   - Kết hợp NoteTool và TerminalTool, hãy thiết kế một "trợ lý tái cấu trúc mã thông minh": có thể phân tích cấu trúc cơ sở mã, ghi lại kế hoạch tái cấu trúc, thực thi từng bước thao tác tái cấu trúc, và theo dõi tiến độ cùng vấn đề gặp phải trong ghi chú. Hãy vẽ sơ đồ quy trình làm việc hoàn chỉnh.

4. Trong trường hợp "quản lý nhiệm vụ dài hạn" ở mục 9.6, chúng ta đã thấy giá trị của kỹ thuật ngữ cảnh trong ứng dụng thực tế. Hãy phân tích sâu:

   - Trường hợp này dùng chiến lược "quản lý ngữ cảnh phân tầng": truy cập tức thời (TerminalTool) + bộ nhớ phiên (MemoryTool) + ghi chú bền vững (NoteTool). Hãy phân tích: ba tầng này nên phối hợp thế nào? Thông tin nào nên đặt ở tầng nào? Làm sao tránh dư thừa và không nhất quán thông tin?
   - Giả sử trong quá trình thực thi nhiệm vụ xảy ra gián đoạn (như hệ thống sụp đổ, mạng ngắt), Agent cần khôi phục trạng thái từ ghi chú và tiếp tục thực thi. Hãy thiết kế cơ chế "tiếp tục từ điểm dừng": làm sao ghi đủ thông tin trạng thái trong ghi chú? Làm sao xác minh trạng thái sau khôi phục là đúng?
   - Nhiệm vụ dài hạn thường liên quan đến thực thi song song hoặc tuần tự nhiều nhiệm vụ con. Hãy thiết kế một hệ thống "quản lý phụ thuộc nhiệm vụ": có thể biểu đạt quan hệ phụ thuộc giữa các nhiệm vụ (như "nhiệm vụ B phải thực thi sau khi nhiệm vụ A hoàn thành"), và tự động điều phối thứ tự thực thi nhiệm vụ. Hệ thống này nên tích hợp với NoteTool thế nào?

5. Chương này nhiều lần nhắc đến khái niệm "tiết lộ dần dần" (progressive disclosure). Hãy suy nghĩ:

   - Trong mục 9.2.2, tiết lộ dần dần được mô tả là "mỗi bước tương tác sinh ra ngữ cảnh mới, đến lượt nó lại định hướng quyết định bước tiếp theo". Hãy thiết kế một kịch bản ứng dụng cụ thể (như viết bài báo học thuật, gỡ lỗi vấn đề phức tạp), trình bày cách tiết lộ dần dần giúp Agent hoàn thành nhiệm vụ hiệu quả hơn.
   - Một rủi ro tiềm ẩn của tiết lộ dần dần là "hiệu quả khám phá thấp": Agent có thể lãng phí thời gian vào chi tiết không quan trọng, hoặc bỏ lỡ thông tin then chốt. Hãy thiết kế một cơ chế "định hướng khám phá": thông qua quy tắc heuristic hoặc chiến lược siêu nhận thức, giúp Agent quyết định "bước tiếp theo nên khám phá gì" thông minh hơn.
   - So sánh "tiết lộ dần dần" với "nạp toàn bộ ngữ cảnh một lần" truyền thống: trong loại nhiệm vụ nào, cách trước có ưu thế rõ rệt? Trong loại nhiệm vụ nào, cách sau có thể phù hợp hơn? Hãy đưa ra ít nhất 3 ví dụ nhiệm vụ khác loại.

## Tài liệu tham khảo

[1] Anthropic. Effective Context Engineering for AI Agents. `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`

[2] David Kim. Context-Engineering (GitHub). `https://github.com/davidkimai/Context-Engineering`

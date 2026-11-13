# Chương 5: Xây dựng Agent với nền tảng low-code

Ở chương trước, thông qua việc viết mã Python, chúng ta đã hiện thực từ con số không nhiều quy trình làm việc Agent kinh điển như ReAct, Plan-and-Solve và Reflection. Quá trình này đặt nền tảng kỹ thuật vững chắc cho chúng ta, giúp hiểu sâu cơ chế vận hành bên trong của Agent. Tuy nhiên, với một lĩnh vực phát triển nhanh, mô hình phát triển thuần mã nguồn không phải lúc nào cũng là lựa chọn hiệu quả nhất, đặc biệt trong các tình huống cần nhanh chóng kiểm chứng ý tưởng, hoặc khi nhà phát triển không chuyên muốn tham gia xây dựng.

## 5.1 Sự trỗi dậy của việc xây dựng theo nền tảng

Khi công nghệ trưởng thành, chúng ta thấy ngày càng nhiều năng lực được “nền tảng hóa”. Cũng như việc phát triển website đã tiến hóa từ viết tay HTML/CSS/JS sang sử dụng các nền tảng dựng website như WordPress, Wix, việc xây dựng Agent cũng đón làn sóng nền tảng hóa. Chương này sẽ tập trung vào cách sử dụng các nền tảng low-code đồ họa, mô-đun hóa để nhanh chóng, trực quan xây dựng, gỡ lỗi và triển khai ứng dụng Agent, chuyển trọng tâm từ “chi tiết hiện thực” sang “logic nghiệp vụ”.

### 5.1.1 Vì sao cần nền tảng low-code

“Phát minh lại bánh xe” rất quan trọng để học sâu, nhưng trong thực chiến theo đuổi hiệu quả kỹ thuật và đổi mới, chúng ta thường cần đứng trên vai người khổng lồ. Mặc dù ở chương 4 chúng ta đã đóng gói các lớp có thể tái sử dụng như `ReActAgent`, `PlanAndSolveAgent`, nhưng khi logic nghiệp vụ trở nên phức tạp, chi phí bảo trì và chu kỳ phát triển của mã thuần sẽ tăng vọt. Sự xuất hiện của nền tảng low-code chính là để giải quyết những điểm đau này.

Giá trị cốt lõi của nó chủ yếu thể hiện ở các khía cạnh sau:

1. <strong>Hạ thấp ngưỡng kỹ thuật</strong>: nền tảng low-code đóng gói các chi tiết kỹ thuật phức tạp (như gọi API, quản lý trạng thái, điều khiển đồng thời) thành từng “nút” hoặc “mô-đun” dễ hiểu. Người dùng không cần tinh thông lập trình, chỉ cần kéo thả, kết nối các nút này là có thể xây dựng quy trình làm việc mạnh mẽ. Điều này cho phép các nhân sự phi kỹ thuật như quản lý sản phẩm, nhà thiết kế, chuyên gia nghiệp vụ cũng tham gia vào thiết kế và sáng tạo Agent, mở rộng rất lớn biên giới đổi mới.
2. <strong>Nâng cao hiệu quả phát triển</strong>: với nhà phát triển chuyên nghiệp, nền tảng cũng mang lại nâng cao hiệu quả to lớn. Ở giai đoạn đầu dự án, khi cần nhanh chóng kiểm chứng một ý tưởng hoặc dựng một nguyên mẫu (Prototype), dùng nền tảng low-code có thể hoàn thành trong vài giờ thậm chí vài phút công việc vốn cần vài ngày viết mã. Nhà phát triển có thể dồn sức hơn vào sắp xếp logic nghiệp vụ và tối ưu kỹ thuật prompt, thay vì hiện thực kỹ thuật tầng dưới.
3. <strong>Cung cấp khả năng trực quan hóa và quan sát tốt hơn</strong>: so với in nhật ký trong terminal, nền tảng đồ họa tự nhiên cung cấp khả năng trực quan hóa đầu-cuối quỹ đạo vận hành của Agent. Bạn có thể thấy rõ dữ liệu chảy giữa từng nút như thế nào, mắt xích nào tốn thời gian nhất, lời gọi công cụ nào thất bại. Trải nghiệm gỡ lỗi trực quan này khó có thể so sánh với phát triển thuần mã nguồn.
4. <strong>Chuẩn hóa và tích lũy thực tiễn tốt nhất</strong>: các nền tảng low-code xuất sắc thường tích hợp sẵn nhiều thực tiễn tốt nhất trong ngành. Ví dụ, nó cung cấp mẫu ReAct đặt trước, công cụ truy xuất kho tri thức được tối ưu, quy chuẩn kết nối công cụ được chuẩn hóa, v.v. Điều này không chỉ giúp nhà phát triển tránh “giẫm bẫy”, mà còn khiến cộng tác nhóm thuận lợi hơn, vì mọi người đều phát triển dựa trên cùng một bộ chuẩn và thành phần.

Nói ngắn gọn, nền tảng low-code không phải để thay thế mã nguồn, mà cung cấp một mức trừu tượng cao hơn. Nó giải phóng chúng ta khỏi hiện thực tầng dưới rườm rà, tập trung hơn vào chính logic “suy nghĩ” và “hành động” của Agent, từ đó nhanh hơn, tốt hơn biến ý tưởng thành hiện thực.

### 5.1.2 Lựa chọn nền tảng low-code

Hiện nay, thị trường nền tảng low-code cho Agent và ứng dụng LLM đang nở rộ, mỗi nền tảng có định vị và ưu thế riêng. Việc chọn nền tảng nào thường phụ thuộc vào nhu cầu cốt lõi, nền tảng kỹ thuật và mục tiêu cuối cùng của dự án. Trong các mục sau của chương này, chúng ta sẽ tập trung giới thiệu và thực hành một số nền tảng tiêu biểu: Coze, Dify, FastGPT và n8n. Trước đó, chúng ta giới thiệu khái quát về chúng.

<strong>Coze</strong>

- <strong>Định vị cốt lõi</strong>: Coze<sup>[1]</sup> do ByteDance ra mắt, tập trung vào trải nghiệm xây dựng Agent không cần mã/ít mã, để người dùng không có nền tảng lập trình cũng có thể dễ dàng sáng tạo.
- <strong>Phân tích đặc điểm</strong>: Coze có giao diện trực quan cực kỳ thân thiện; người dùng có thể giống như lắp ghép lego, kéo thả plugin, cấu hình kho tri thức và thiết lập quy trình làm việc để tạo Agent. Nó tích hợp sẵn thư viện plugin cực kỳ phong phú, hỗ trợ xuất bản một cú nhấp đến nhiều nền tảng chủ lưu như Douyin, Feishu, WeChat Official Account, đơn giản hóa rất nhiều quy trình phân phối.
- <strong>Đối tượng phù hợp</strong>: người mới dùng ứng dụng AI, quản lý sản phẩm, nhân sự vận hành, và nhà sáng tạo cá nhân muốn nhanh chóng biến ý tưởng thành sản phẩm tương tác.

<strong>Dify</strong>

- <strong>Định vị cốt lõi</strong>: Dify là nền tảng phát triển và vận hành ứng dụng LLM mã nguồn mở, đầy đủ chức năng<sup>[2]</sup>, nhằm cung cấp cho nhà phát triển giải pháp một cửa từ dựng nguyên mẫu đến triển khai sản xuất.
- <strong>Phân tích đặc điểm</strong>: nó kết hợp tư tưởng dịch vụ backend và vận hành mô hình, hỗ trợ nhiều năng lực như quy trình làm việc Agent, RAG Pipeline, gán nhãn dữ liệu và tinh chỉnh. Với ứng dụng cấp doanh nghiệp theo đuổi tính chuyên nghiệp, ổn định và khả năng mở rộng, Dify cung cấp nền tảng vững chắc.
- <strong>Đối tượng phù hợp</strong>: nhà phát triển có nền tảng kỹ thuật nhất định, đội ngũ cần xây dựng ứng dụng AI cấp doanh nghiệp có thể mở rộng.

<strong>FastGPT</strong>

- <strong>Định vị cốt lõi</strong>: FastGPT là nền tảng hỏi đáp kho tri thức và công cụ xây dựng Agent mã nguồn mở dựa trên mô hình ngôn ngữ lớn LLM<sup>[3]</sup>, tập trung cung cấp giải pháp RAG (truy xuất tăng cường sinh) đơn giản dễ dùng và năng lực biên soạn quy trình làm việc trực quan.
- <strong>Phân tích đặc điểm</strong>: ưu thế cốt lõi nhất của FastGPT nằm ở tối ưu cực hạn cho tình huống hỏi đáp kho tri thức. Nó cung cấp chuỗi RAG hoàn chỉnh từ nhập dữ liệu, tự động chia đoạn văn bản, lưu trữ vector đến truy xuất thông minh, và hỗ trợ biên soạn luồng hội thoại phức tạp cũng như quy trình làm việc Agent qua giao diện trực quan (mô-đun Flow). Nền tảng áp dụng thiết kế trung lập mô hình, có thể kết nối linh hoạt nhiều mô hình lớn chủ lưu trong và ngoài nước như OpenAI, Claude, Qwen, đồng thời cung cấp API hoàn chỉnh và chợ plugin, thuận tiện tích hợp nhanh với các hệ thống hiện có như WeCom, DingTalk, Feishu.
- <strong>Đối tượng phù hợp</strong>: nhà phát triển và đội ngũ doanh nghiệp vừa và nhỏ muốn nhanh chóng xây dựng chăm sóc khách hàng thông minh, trợ lý tri thức nội bộ doanh nghiệp, robot hỏi đáp tài liệu dựa trên kho tri thức riêng; cùng những người yêu công nghệ quan tâm RAG nhưng muốn hạ thấp ngưỡng hiện thực.

<strong>n8n</strong>

- <strong>Định vị cốt lõi</strong>: n8n về bản chất là công cụ tự động hóa quy trình làm việc mã nguồn mở<sup>[4]</sup>, không phải nền tảng LLM thuần túy. Những năm gần đây, nó tích cực tích hợp năng lực AI.
- <strong>Phân tích đặc điểm</strong>: điểm mạnh của n8n nằm ở “kết nối”. Nó có hàng trăm nút đặt trước, có thể dễ dàng kết nối các dịch vụ SaaS, cơ sở dữ liệu, API thành quy trình nghiệp vụ tự động phức tạp. Bạn có thể nhúng nút LLM vào quy trình này, biến nó thành một mắt xích trong toàn bộ chuỗi tự động hóa. Mặc dù về mức độ chuyên biệt cho chức năng LLM không bằng hai nền tảng trước, năng lực tự động hóa tổng quát của nó là độc nhất. Tuy nhiên, đường cong học tập của nó cũng tương đối dốc.
- <strong>Đối tượng phù hợp</strong>: nhà phát triển và doanh nghiệp cần tích hợp sâu năng lực AI vào quy trình nghiệp vụ hiện có, hiện thực tự động hóa tùy biến cao.

Trong các mục tiếp theo, chúng ta sẽ lần lượt trải nghiệm các nền tảng này, thông qua thao tác thực tế để cảm nhận trực quan hơn sức hấp dẫn riêng của từng nền tảng.

## 5.2 Nền tảng một: Coze ([coze.cn](https://www.coze.cn/home))

Coze (扣子) là một công cụ tạo Agent AI cực ngầu! Đây cũng là nền tảng Agent được ứng dụng rộng rãi nhất trên thị trường hiện nay. Với giao diện trực quan và các mô-đun chức năng phong phú, nền tảng cho phép người dùng dễ dàng tạo nhiều loại ứng dụng Agent, như robot trò chuyện cùng bạn, máy sáng tác tự động viết truyện, thậm chí trực tiếp biến truyện thành MV điện ảnh! Một điểm sáng của nó là năng lực tích hợp hệ sinh thái mạnh mẽ. Agent đã phát triển có thể xuất bản một cú nhấp đến các nền tảng chủ lưu như WeChat, Feishu, Doubao, hiện thực triển khai liền mạch đa nền tảng. Với người dùng doanh nghiệp, Coze còn cung cấp giao diện API linh hoạt, hỗ trợ tích hợp năng lực Agent vào hệ thống nghiệp vụ hiện có, hiện thực xây dựng ứng dụng AI kiểu “lắp ghép khối”.

### 5.2.1 Các mô-đun chức năng của Coze

(1) Tổng quan giao diện nền tảng

Giới thiệu bố cục tổng thể: gần đây Coze lại cập nhật giao diện UI, như trong Hình 5.1. Thanh bên trái hiện nay là không gian phát triển của trang chủ nền tảng Coze, gồm phát triển dự án cốt lõi, thư viện tài nguyên, đánh giá hiệu quả và cấu hình không gian. Khu vực bên dưới là không gian tài liệu hỗ trợ phát triển Coze, gồm mẫu chính thức sao chép một cú nhấp, cửa hàng plugin phong phú đa dạng – ưu thế lớn nhất của Coze, cộng đồng Agent lớn nhất với vô vàn nội dung, quản lý API dùng để kiểm thử API, tài liệu hướng dẫn chi tiết và quản lý tổng quát dành cho doanh nghiệp. Khu vực bên phải có bốn mẫu; trên cùng là thông báo cập nhật mới nhất của Coze cho bạn biết tiến độ mới nhất, thuận tiện tìm hiểu công cụ và chức năng mới. Tiếp theo là hướng dẫn cho người mới; nhấp vào là mở tài liệu hướng dẫn, bắt đầu xây dựng Agent trong vài phút. Sau đó là nội dung bạn theo dõi và gợi ý Agent; tại đây bạn cũng có thể theo dõi nhà phát triển AI yêu thích và lưu Agent của họ để dùng.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-01.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.1 Sơ đồ tổng thể nền tảng Agent Coze</p>
</div>

(2) Giới thiệu các chức năng cốt lõi

Trước tiên, nhấp vào dấu cộng ở thanh bên trái để thấy lối vào tạo Agent. Hiện có hai loại ứng dụng AI: một là tạo Agent, hai là tạo Ứng dụng. Trong đó Agent lại chia thành chế độ một Agent tự lập kế hoạch, chế độ một Agent luồng hội thoại và chế độ đa Agent. Ứng dụng AI cũng chia hai loại: không chỉ có thể thiết kế giao diện người dùng trên web máy tính, mà còn dễ dàng dựng giao diện tiểu chương trình và H5, như trong Hình 5.2.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-02.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.2 Lối vào tạo Agent của Coze</p>
</div>
Không gian dự án là kho Agent của bạn, nơi lưu tất cả Agent bạn phát triển hoặc Agent/ứng dụng đã sao chép; đây cũng là nơi bạn thường xuyên ghé nhất khi phát triển Agent trên Coze, như trong Hình 5.3.
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-03.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.3 Không gian dự án Agent của Coze</p>
</div>
Thư viện tài nguyên là kho vũ khí cốt lõi để bạn phát triển Agent Coze; thư viện tài nguyên lưu quy trình làm việc, kho tri thức, thẻ, thư viện prompt và một loạt công cụ phát triển Agent. Bạn có thể tạo ra Agent gì trước tiên phụ thuộc vào năng lực mô hình, nhưng quan trọng nhất vẫn là cách bạn “trang bị và kỹ năng” cho Agent. Mô hình quyết định giới hạn dưới của Agent, nhưng thư viện tài nguyên Coze trao cho bạn giới hạn trên vô hạn cho năng lực Agent, để bạn phát triển Agent theo ý tưởng, trí tưởng tượng và óc sáng tạo của mình, như trong Hình 5.4.
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-04.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.4 Thư viện tài nguyên Agent của Coze</p>
</div>
Cấu hình không gian gồm một kênh quản lý thống nhất cho Agent, plugin, quy trình làm việc và kênh xuất bản, cùng quản lý mô hình – nơi bạn có thể thấy các mô hình lớn mình gọi, như trong Hình 5.5.
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-05.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.5 Kênh xuất bản Agent của Coze</p>
</div>
Nếu phải tóm tắt đơn giản việc phát triển Agent trên Coze, tôi sẽ ví nó như các thành phần của một trò chơi; các phần phối hợp tạo nên từng Agent tuyệt vời, rất giống chơi “game”; mỗi lần làm xong một Agent giống như đánh xong một boss và thu hoạch đầy ắp, dù là “kinh nghiệm” hay “trang bị”.

- Quy trình làm việc (工作流): bản đồ tuyến qua ải
- Luồng hội thoại (对话流): đối thoại NPC qua ải
- Plugin (插件): thẻ kỹ năng nhân vật
- Kho tri thức (知识库): bách khoa toàn thư trò chơi
- Thẻ (卡片): thanh đạo cụ nhanh
- Prompt (提示词): phím di chuyển nhân vật
- Cơ sở dữ liệu (数据库): “lưu trữ đám mây”
- Quản lý xuất bản (发布管理): người kiểm duyệt màn chơi
- Quản lý mô hình (模型管理): kho nhân vật trò chơi, hay còn gọi là hệ thống tạo hình
- Đánh giá hiệu quả (效果评测): hệ thống chấm điểm vượt ải

### 5.2.2 Xây dựng trợ lý “Bản tin AI hằng ngày”

<strong>Mô tả ca:</strong> ca thực hành này nhằm phân tích sâu năng lực tích hợp plugin của nền tảng Coze, hướng dẫn người đọc từ con số không xây dựng một Agent “Bản tin AI hằng ngày” mạnh mẽ. Agent này có thể tự động thu thập tin tức đầu ngành AI, bài báo học thuật và cập nhật dự án mã nguồn mở mới nhất trong ngày từ nhiều nguồn thông tin (gồm 36Kr, Hổ Phún, ITHome, InfoQ, GitHub, arXiv), rồi tích hợp chúng một cách có cấu trúc, chuyên nghiệp thành một bản tin sinh động, súc tích.

Qua ca này, bạn sẽ nắm một cách hệ thống các kỹ năng cốt lõi sau:

* <strong>Tổng hợp đa nguồn thông tin:</strong> tận dụng hệ sinh thái plugin của Coze để hiện thực tích hợp liền mạch luồng dữ liệu đa nền tảng, đa loại hình.
* <strong>Định nghĩa hành vi Agent:</strong> thông qua thiết lập vai trò và kỹ thuật prompt, kiểm soát chính xác việc thực thi nhiệm vụ và sinh nội dung của Agent, đảm bảo đầu ra đáp ứng chuẩn chuyên nghiệp đặt trước.
* <strong>Xây dựng quy trình làm việc tự động:</strong> học cách nối nhiều bước như thu thập dữ liệu, xử lý nội dung và xuất ra theo định dạng thành một quy trình làm việc tự động, hiệu quả.

<strong>Lưu ý: cập nhật lối vào nền tảng Coze</strong>

Do nền tảng Coze liên tục cập nhật, lối vào trang hiện tại đã thay đổi so với khi biên soạn hướng dẫn.

Khi truy cập [trang chủ Coze trong nước](https://www.coze.cn/home), trang có thể tự động chuyển hướng đến trang chủ phiên bản mới https://www.coze.cn. Trong giao diện mới, có thể vào không gian làm việc phiên bản cũ để tiếp tục xây dựng Agent qua lối vào sau, như trong Hình 5.6.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-06.jpg" alt="Lối vào không gian làm việc phiên bản cũ từ trang chủ mới của Coze" width="90%"/>
  <p>Hình 5.6 Lối vào không gian làm việc phiên bản cũ từ trang chủ mới của Coze</p>
</div>

Nếu trang không hiển thị lối vào tương tự, cũng có thể truy cập trực tiếp [https://www.coze.cn/space/](https://www.coze.cn/space/) để vào không gian làm việc và tạo Agent.

<strong>Bước một: tạo quy trình làm việc</strong>

Trong giao diện thư viện tài nguyên, chọn `+Tài nguyên (资源)`——`Quy trình làm việc (工作流)`, tạo quy trình làm việc, như trong Hình 5.7.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-07.png" alt="Trang tạo quy trình làm việc" width="90%"/>
  <p>Hình 5.7 Trang tạo quy trình làm việc</p>
</div>

<strong>Bước hai: thêm và cấu hình plugin nguồn thông tin</strong>

Nhiệm vụ đầu tiên khi xây dựng Agent “Bản tin AI hằng ngày” là kết nối cho nó những nguồn thông tin phong phú và có uy tín. Trên nền tảng Coze, việc này được hiện thực bằng cách thêm và cấu hình plugin tương ứng.

1. <strong>Tích hợp plugin:</strong> trong thư viện plugin của Coze, tìm kiếm và thêm plugin cần thiết. Ví dụ, dùng plugin <strong>RSS</strong> để đăng ký nguồn RSS của nền tảng truyền thông (như Hình 5.8), dùng plugin <strong>GitHub</strong> để theo dõi dự án mã nguồn mở (như Hình 5.9), và dùng plugin <strong>arXiv</strong> để lấy kết quả nghiên cứu học thuật mới nhất (như Hình 5.10).

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-08.png" alt="Plugin nguồn RSS của nền tảng truyền thông" width="90%"/>
  <p>Hình 5.8 Plugin nguồn RSS của nền tảng truyền thông</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-09.png" alt="Plugin GitHub" width="90%"/>
  <p>Hình 5.9 Plugin GitHub</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-10.png" alt="Plugin Arxiv" width="90%"/>
  <p>Hình 5.10 Plugin Arxiv</p>
</div>
2. <strong>Cấu hình cá nhân hóa:</strong> cấu hình chi tiết từng plugin để đảm bảo nó lấy chính xác dữ liệu cần thiết. Ví dụ, trong plugin RSS, nhập liên kết đăng ký RSS cụ thể của các trang như 36Kr, Hổ Phún; trong plugin GitHub, đặt số truy vấn từ khóa cần theo dõi và thiết lập cập nhật mới nhất; trong plugin arXiv, định nghĩa từ khóa lĩnh vực quan tâm như “LLM”, “AI”, v.v., định nghĩa số lượng và thiết lập cập nhật mới nhất.

```
Cấu hình liên kết RSS

url: 36Kr: https://www.36kr.com/feed
url: Hổ Phún: https://rss.huxiu.com/
url: ITHome: http://www.ithome.com/rss/
url: InfoQ: https://feed.infoq.com/ai-ml-data-eng/

Cấu hình plugin GitHub

q:AI
per_page:10
sort:updated

Cấu hình plugin Arxiv

count：5
search_query：AI
sort_by：2
```

3. <strong>Biên soạn kết nối:</strong> trong giao diện biên soạn trực quan của Agent, dùng các plugin nguồn thông tin đã cấu hình (ví dụ `rss_24Hbj`, `searchRepository`, `arxiv`, v.v.) làm nút đầu vào dữ liệu, và kết nối chúng đến mô-đun xử lý logic tiếp theo (ví dụ mô-đun <strong>mô hình lớn</strong>), để xây dựng đường xử lý dữ liệu hoàn chỉnh, như trong Hình 5.11.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-11.png" alt="Sơ đồ quy trình biên soạn Bản tin AI hằng ngày" width="90%"/>
  <p>Hình 5.11 Sơ đồ quy trình biên soạn Bản tin AI hằng ngày</p>
</div>

<strong>Bước ba: thiết lập vai trò và prompt cho Agent</strong>

Thiết lập vai trò và viết prompt là mắt xích cốt lõi quyết định hành vi và chất lượng đầu ra của Agent. Bước này nhằm chuyển chỉ thị trừu tượng thành nhiệm vụ cụ thể mà Agent có thể hiểu và thực thi.

Trên nền tảng Coze, có thể định nghĩa logic hành vi của Agent bằng cách cấu hình system prompt và user prompt, như trong Hình 5.12.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-12.png" alt="Trang cấu hình prompt" width="90%"/>
  <p>Hình 5.12 Trang cấu hình prompt</p>
</div>

(1) Thiết lập vai trò

Chúng ta đặt Agent vào vai một <strong>biên tập viên truyền thông công nghệ lão luyện và có uy tín</strong>. Vai trò này trao cho Agent định vị chuyên môn rõ ràng, để trong quá trình sáng tạo nội dung sau đó, nó có thể mô phỏng mô hình tư duy của biên tập viên chuyên nghiệp, thực hiện sàng lọc, tích hợp và khái quát thông tin hiệu quả.

(2) Viết prompt và cấu trúc hóa

Prompt là sổ tay hướng dẫn Agent thực thi nhiệm vụ. Chúng ta chia nó thành <strong>system prompt và user prompt</strong> để đảm bảo chỉ thị rõ ràng, đầy đủ và có thể kiểm soát.
<strong>System prompt</strong>

```
# Vai trò
Bạn là một biên tập viên truyền thông công nghệ lão luyện và có uy tín, giỏi tích hợp và sáng tạo bản tin công nghệ có tính chuyên môn cao một cách hiệu quả, chính xác, đặc biệt có năng lực phân tích và tích hợp sâu về xu hướng kỹ thuật trong lĩnh vực AI, kết quả nghiên cứu học thuật tiên phong và dự án mã nguồn mở nổi bật.
## Quy trình làm việc
### Định dạng đầu ra bản tin hằng ngày
1. Ở đầu bản tin, đánh dấu rõ “Bản tin AI”, “by@jasonhuang” và ngày trong ngày, ví dụ: “Bản tin AI | 24 tháng 9 năm 2025 | by@jasonhuang”.
2. <!!!important!!!> Dựa trên nội dung khác nhau của mỗi tin tức công nghệ AI, mỗi bài báo học thuật AI, mỗi dự án mã nguồn mở AI, thêm một biểu tượng Emoji riêng ở đầu tiêu đề của mục đó.
3. Toàn bộ nội dung xuất ra phải có liên quan cao đến các chủ đề công nghệ như AI, LLM, AIGC, mô hình lớn; kiên quyết loại bỏ mọi thông tin không liên quan, quảng cáo và nội dung tiếp thị.
4. Bắt buộc cung cấp liên kết gốc tương ứng cho mỗi mục (gồm tin tức công nghệ AI, bài báo học thuật AI, dự án mã nguồn mở AI).
5. Với mỗi tin tức hoặc dự án xuất ra, cung cấp một mô tả khái quát ngắn gọn, chính xác.
```
System prompt dùng để định nghĩa chuẩn mực hành vi dài hạn và quy phạm định dạng đầu ra của Agent. User prompt dùng để định nghĩa chỉ thị nhiệm vụ cụ thể và nguồn dữ liệu.
<strong>User prompt</strong>

```
- **Trích xuất và tích hợp thông tin:** từ các nguồn đầu vào `{{articles}}`, `{{articles1}}`, `{{articles2}}` và `{{articles3}}`, sàng lọc và trích xuất tiêu đề bài viết cùng liên kết tương ứng về các chủ đề AI, mô hình lớn, AIGC, LLM, v.v., sắp xếp thành mô-đun **“Tin tức công nghệ AI”**.
- **Tóm tắt bài báo học thuật:** từ nguồn đầu vào `{{arxiv}}`, dựa trên các trường `arxiv_title` và `arxiv_link`, tóm tắt và sắp xếp nội dung bài báo mới nhất, tạo thành mô-đun **“Bài báo học thuật AI”**.
- **Sàng lọc dự án mã nguồn mở:** từ nguồn đầu vào `{{GitHub}}`, sàng lọc **5 dự án mã nguồn mở AI** được chú ý và có ảnh hưởng nhất. Trích xuất tiêu đề và liên kết tương ứng của các dự án này, sắp xếp thành mô-đun **“Dự án mã nguồn mở AI”**.
# Lưu ý (Attention)
- Tuân thủ nghiêm ngặt định dạng đầu ra bản tin hằng ngày đã định nghĩa trong system prompt.
- Tổng lượng nội dung xuất ra phải là: **10 tin tức công nghệ AI, 5 bài báo học thuật AI, 5 dự án mã nguồn mở AI**.
```

<strong>Bước bốn: kiểm thử, gỡ lỗi và xuất bản đa kênh</strong>

Sau khi hoàn thành xây dựng logic cốt lõi của Agent, bắt buộc phải kiểm thử và gỡ lỗi nghiêm ngặt để đảm bảo đầu ra đáp ứng mong đợi.

<strong>Xem trước khi chạy:</strong> chạy Agent trong giao diện xem trước của nền tảng Coze, quan sát nội dung bản tin nó sinh ra.

```
# Bản tin AI by@jasonhuang 2025-09-24

## 🚀 Tin tức công nghệ AI

🤖 **Mô hình nền tảng embodied tổng quát GO-1 của robot Zhiyuan chính thức mã nguồn mở hoàn toàn**
Liên kết: https://36kr.com/p/3479085489708163?f=rss
Khái quát: Robot Zhiyuan công bố mô hình nền tảng embodied tổng quát GO-1 mã nguồn mở hoàn toàn, cung cấp năng lực AI nền tảng mạnh mẽ cho lĩnh vực robot.

🔬 **Microsoft giải bài toán tản nhiệt chip trung tâm dữ liệu: vi lưu chất + AI làm mát chính xác**
Liên kết: https://www.ithome.com/0/885/391.htm
Khái quát: Microsoft kết hợp công nghệ vi lưu chất với thuật toán AI để hiện thực kiểm soát nhiệt độ chính xác cho chip trung tâm dữ liệu, nâng cao hiệu suất năng lượng.
......

## 📚 Bài báo học thuật AI

🧪 **Lyra: Tái dựng cảnh 3D sinh tạo qua tự chưng cất mô hình khuếch tán video**
Liên kết: http://arxiv.org/pdf/2509.19296v1
Khái quát: đề xuất framework đổi mới tạo cảnh 3D bằng tự chưng cất mô hình khuếch tán video, không cần dữ liệu huấn luyện đa góc nhìn.

📊 **Thí nghiệm xếp hạng ICML 2023: Xem xét tự đánh giá của tác giả trong bình duyệt ML/AI**
Liên kết: http://arxiv.org/pdf/2408.13430v3
Khái quát: nghiên cứu tính hiệu quả của tự đánh giá của tác giả trong quá trình bình duyệt hội nghị học máy, đề xuất phương pháp cải thiện cơ chế bình duyệt.
......

## 💻 Dự án mã nguồn mở AI

🤖 **llmling-agent - Framework quy trình làm việc đa Agent**
Liên kết: https://github.com/phil65/llmling-agent
Khái quát: framework tương tác đa Agent hỗ trợ cấu hình YAML và lập trình, tích hợp hỗ trợ giao thức MCP và ACP.

🚌 **College_EV_AI_Transportation - Hệ thống giao thông điện AI trong khuôn viên trường**
Liên kết: https://github.com/LuisMc2005v/College_EV_AI_Transportation
Khái quát: hệ thống tối ưu giao thông điện trong khuôn viên do AI dẫn dắt, hiện thực theo dõi thời gian thực và dịch vụ đi chung xe hiệu quả.
......
```

Kiểm tra kỹ tính chính xác nội dung, tính đầy đủ định dạng và phong cách ngôn ngữ của bản tin. Nếu phát hiện phần không đáp ứng mong đợi, cần quay lại bước prompt hoặc cấu hình plugin để điều chỉnh chi tiết. Ví dụ, nếu nội dung chưa súc tích, có thể sửa yêu cầu khái quát trong prompt; nếu thu thập dữ liệu không chính xác, cần kiểm tra tham số cấu hình plugin.

Xuất bản đa kênh: Coze cung cấp năng lực xuất bản Agent một cú nhấp đến nhiều nền tảng ứng dụng chủ lưu (như WeChat, Doubao, Feishu), mở rộng rất lớn tình huống ứng dụng của Agent, như trong Hình 5.13.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-13.png" alt="Các kênh xuất bản đa dạng của nền tảng Coze" width="60%"/>
  <p>Hình 5.13 Các kênh xuất bản đa dạng của nền tảng Coze</p>
</div>

Sau khi xuất bản, có thể thấy Agent AI chúng ta tạo trong cửa hàng Coze, đồng thời tích hợp nó vào ứng dụng AI để cung cấp dịch vụ cho người dùng, như trong Hình 5.14 và Hình 5.15. Ở đây cũng đính kèm [liên kết trải nghiệm Agent Bản tin AI hằng ngày](https://www.coze.cn/store/agent/7506052197071962153?bot_id=true&bid=6hkt3je8o2g16)

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-14.png" alt="Agent AI - Bản tin AI hằng ngày" width="90%"/>
  <p>Hình 5.14 Agent AI - Bản tin AI hằng ngày</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-15.png" alt="Bản tin AI hằng ngày trong ứng dụng AI" width="90%"/>
  <p>Hình 5.15 Bản tin AI hằng ngày trong ứng dụng AI</p>
</div>

<strong>Cấu hình xuất bản:</strong> nếu muốn xuất bản Agent của mình, trước khi xuất bản cần cấu hình tên, ảnh đại diện và lời chào phù hợp cho Agent, để mang lại trải nghiệm người dùng thân thiện hơn, như trong Hình 5.16 và Hình 5.17.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-16.png" alt="Cấu hình thông tin cơ bản cho Agent" width="50%"/>
  <p>Hình 5.16 Cấu hình thông tin cơ bản cho Agent</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/coze-17.png" alt="Cấu hình lời mở đầu và câu hỏi đặt trước cho Agent" width="50%"/>
  <p>Hình 5.17 Cấu hình lời mở đầu và câu hỏi đặt trước cho Agent</p>
</div>

### 5.2.3 Phân tích ưu điểm và hạn chế của Coze

<strong>Ưu điểm:</strong>

* <strong>Hệ sinh thái plugin mạnh mẽ:</strong> ưu thế cốt lõi của nền tảng Coze nằm ở thư viện plugin phong phú, giúp Agent dễ dàng kết nối dịch vụ bên ngoài và nguồn dữ liệu, từ đó hiện thực khả năng mở rộng chức năng cao.
* <strong>Biên soạn trực quan trực tiếp:</strong> nền tảng cung cấp giao diện biên soạn quy trình làm việc trực quan với ngưỡng thấp; người dùng không cần kiến thức lập trình sâu, chỉ cần “kéo thả” là có thể xây dựng quy trình làm việc phức tạp, giảm mạnh độ khó phát triển.
* <strong>Kiểm soát prompt linh hoạt:</strong> thông qua thiết lập vai trò chính xác và viết prompt, người dùng có thể kiểm soát chi tiết hành vi và sinh nội dung của Agent, hiện thực đầu ra tùy biến cao. Nó còn hỗ trợ quản lý và mẫu prompt, tạo thuận lợi rất lớn cho nhà phát triển khi xây dựng Agent.
* <strong>Triển khai đa nền tảng thuận tiện:</strong> hỗ trợ xuất bản cùng một Agent đến các nền tảng ứng dụng khác nhau, hiện thực tích hợp và ứng dụng liền mạch đa nền tảng. Coze còn không ngừng tích hợp nền tảng mới vào hệ sinh thái; ngày càng nhiều nhà sản xuất điện thoại và phần cứng lần lượt hỗ trợ xuất bản Agent Coze.

<strong>Hạn chế:</strong>

* <strong>Không hỗ trợ MCP:</strong> tôi cho rằng đây là điều chí mạng nhất. Mặc dù chợ plugin của Coze cực kỳ phong phú và hấp dẫn, việc không hỗ trợ MCP có thể trở thành gông cùm hạn chế sự phát triển của nó; nếu mở ra, đó sẽ là một át chủ bài nữa.
* <strong>Một số plugin có cấu hình phức tạp:</strong> với plugin cần API Key hoặc tham số nâng cao khác, người dùng có thể cần nền tảng kỹ thuật nhất định mới cấu hình đúng. Việc biên soạn quy trình làm việc phức tạp cũng không phải chỉ cần trình độ từ con số không là nắm được; cần một số kiến thức cơ bản về JS hoặc Python.
* <strong>Không thể nhập trực tiếp tệp JSON biên soạn:</strong> trước đây Coze không có chức năng xuất/nhập, nhưng hiện phiên bản trả phí đã có thể xuất/nhập; tuy nhiên tệp xuất/nhập không phải JSON như Dify, n8n mà là một tệp zip. Nghĩa là bạn chỉ có thể xuất trên Coze rồi nhập zip đó lại vào Coze. Tuy nhiên nếu muốn lách, bạn cũng có thể chọn sao chép bản biên soạn: trong giao diện biên soạn nhấn Ctrl+A chọn tất cả, Ctrl+C sao chép, rồi dán sang một quy trình làm việc trống khác hoặc quy trình làm việc khác.

## 5.3 Nền tảng hai: Dify

### 5.3.1 Giới thiệu và hệ sinh thái Dify

Dify là nền tảng phát triển ứng dụng mô hình ngôn ngữ lớn (LLM) mã nguồn mở, kết hợp tư tưởng backend dưới dạng dịch vụ (BaaS) và LLMOps, cung cấp hỗ trợ toàn quy trình từ thiết kế nguyên mẫu đến triển khai sản xuất, như trong Hình 5.18. Nó áp dụng kiến trúc mô-đun phân tầng, chia thành tầng dữ liệu, tầng phát triển, tầng biên soạn và tầng nền tảng; các tầng được tách rời để dễ mở rộng.

Dify có tính trung lập cao với mô hình và khả năng tương thích mạnh: dù là mô hình mã nguồn mở hay thương mại, người dùng đều có thể kết nối bằng cấu hình đơn giản và gọi năng lực suy luận qua giao diện thống nhất. Nó tích hợp sẵn hỗ trợ hàng trăm LLM mã nguồn mở hoặc độc quyền, bao gồm các mô hình GPT, Deepseek, Llama, cùng bất kỳ mô hình nào tương thích OpenAI API.

Đồng thời, Dify hỗ trợ triển khai cục bộ (chính thức cung cấp Docker Compose khởi động một lệnh) và triển khai đám mây. Người dùng có thể chọn tự triển khai Dify trong môi trường cục bộ/riêng tư (bảo đảm quyền riêng tư dữ liệu), hoặc dùng dịch vụ SaaS đám mây chính thức (phần mô hình kinh doanh dưới đây sẽ trình bày chi tiết). Tính linh hoạt triển khai này khiến nó phù hợp với môi trường mạng nội bộ doanh nghiệp có yêu cầu bảo mật, hoặc nhóm nhà phát triển có yêu cầu thuận tiện vận hành.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-01.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.18 Trang chủ Dify</p>
</div>

Hệ sinh thái plugin Marketplace: Dify Marketplace cung cấp chức năng quản lý plugin một cửa và triển khai một cú nhấp, cho phép nhà phát triển khám phá, mở rộng hoặc gửi plugin, mang lại nhiều khả năng hơn cho cộng đồng, như trong Hình 5.19.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-02.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.19 Hệ sinh thái plugin Dify Marketplace</p>
</div>
Marketplace bao gồm:

- Mô hình (Models)
- Công cụ (Tools)
- Chiến lược Agent (Agent Strategies)
- Tiện ích mở rộng (Extensions)
- Gói kết hợp (Bundles)

Hiện nay, Dify Marketplace đã có hơn 8677 plugin, bao phủ nhiều chức năng và tình huống ứng dụng. Trong đó, các plugin được chính thức khuyến nghị gồm:

- Google Search: langgenius/google
- Azure OpenAI: langgenius/azure_openai
- Notion: langgenius/notion
- DuckDuckGo: langgenius/duckduckgo

Dify cung cấp hỗ trợ phát triển mạnh mẽ cho nhà phát triển plugin, gồm chức năng gỡ lỗi từ xa, có thể cộng tác liền mạch với các IDE phổ biến, chỉ cần thiết lập môi trường tối thiểu. Nhà phát triển có thể kết nối dịch vụ SaaS của Dify, đồng thời chuyển tiếp mọi thao tác plugin đến môi trường cục bộ để kiểm thử; cách làm thân thiện với nhà phát triển này nhằm trao quyền cho người tạo plugin và tăng tốc đổi mới hệ sinh thái Dify. Đây cũng là lý do Dify có thể trở thành một trong những nền tảng Agent thành công nhất hiện nay: mô hình đều có thể kết nối, prompt và bản biên soạn có thể sao chép, nhưng việc có công cụ plugin hay không, có phong phú hay không quyết định trực tiếp Agent của bạn có thể tạo ra hiệu quả tốt hơn hoặc chức năng mạnh mẽ ngoài sức tưởng tượng hay không.

### 5.3.2 Xây dựng một trợ lý cá nhân siêu Agent

> **✨✨ Hướng dẫn thao tác chi tiết**: vui lòng tham khảo **[Quy trình thao tác tạo Agent Dify cấp độ “bảo mẫu”](https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra03-Dify智能体创建保姆级操作流程.md)**

Trong ca Coze ở mục trước, chúng ta đã xây dựng một Agent Bản tin AI hằng ngày. Mặc dù chức năng rõ ràng, năng lực sinh bản tin đơn lẻ của nó có phần hạn chế. Mục này sẽ dùng Dify xây dựng một trợ lý cá nhân siêu Agent đầy đủ chức năng, bao phủ nhiều tình huống như hỏi đáp hằng ngày, tối ưu văn bản, sinh nội dung đa phương thức, phân tích dữ liệu. Trước khi bắt đầu, chúng ta tìm hiểu ngắn gọn giao diện và các mô-đun chức năng chính của Dify.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-14.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.20 Trang chủ xây dựng Agent Dify</p>
</div>
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-18.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.21 Thư viện mẫu chính thức Dify</p>
</div>
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-15.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.22 Kho tri thức Dify</p>
</div>
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-16.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.23 Chợ plugin Dify</p>
</div>
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-17.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.24 Cấu hình mô hình lớn Dify</p>
</div>

<strong>(1) Tạo plugin và cấu hình MCP</strong>

Trước khi xây dựng Agent, cần hoàn thành cài đặt plugin cần thiết và cấu hình MCP. Như trong Hình 5.25, đây là các plugin cốt lõi cần cho ca này.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-19.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.25 Cài đặt và cấu hình plugin Dify</p>
</div>

Các plugin được đánh dấu khung đỏ trong hình cần tìm kiếm và cài đặt từ chợ plugin Dify. Người dùng có thể nhấp xem chi tiết để hiểu chức năng cụ thể của từng plugin.

Tiếp theo, cấu hình MCP (Model Context Protocol). Nguyên lý chi tiết của MCP không được trình bày ở đây; chúng ta tập trung trình diễn cách dùng dịch vụ MCP triển khai trên đám mây. Ca này dùng chợ MCP của cộng đồng ModelScope trong nước để trình diễn, như trong Hình 5.26.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-20.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.26 Chợ MCP cộng đồng ModelScope</p>
</div>

Mở chợ MCP cộng đồng ModelScope, chọn loại hosted. Lấy MCP Amap làm ví dụ; sau khi vào trang chủ của nó, chọn chế độ SSE ở bên phải và nhấp cấu hình kết nối, là có thể sinh JSON cấu hình MCP riêng, như trong Hình 5.27. MCP hỗ trợ nhiều chế độ giao tiếp, nhưng dùng chế độ SSE trong Dify giao tiếp mượt và ổn định hơn, vì vậy khuyến nghị chọn SSE.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-21.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.27 Ví dụ cấu hình MCP Amap</p>
</div>

<strong>(2) Thiết kế Agent và trình diễn hiệu quả</strong>

Ca này sẽ tạo một trợ lý cá nhân toàn diện, bao gồm các mô-đun chức năng sau:

- Hỏi đáp trong đời sống hằng ngày
- Trau chuốt và tối ưu văn bản
- Sinh nội dung đa phương thức (hình ảnh, video)
- Truy vấn dữ liệu và phân tích trực quan hóa
- Tích hợp công cụ MCP (bản đồ Amap, gợi ý ăn uống, tin tức thời sự)

Kiến trúc biên soạn của toàn bộ Agent như trong Hình 5.28.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-12.png" alt="Mô tả hình ảnh" width="60%"/>
  <p>Hình 5.28 Biên soạn Agent</p>
</div>

Với kiến trúc đa Agent, chúng ta dùng bộ phân loại vấn đề để định tuyến thông minh. Trong bộ phân loại, định nghĩa chức năng cốt lõi và phạm vi nhiệm vụ cho từng Agent, đảm bảo yêu cầu người dùng được phân phối chính xác đến mô-đun xử lý tương ứng.

<strong>Mô-đun trợ lý hằng ngày</strong>

Đây là một mô-đun hội thoại cơ bản, cấu hình mô hình ngôn ngữ lớn và công cụ thời gian, đóng vai dịch vụ hỏi đáp tổng quát dự phòng.

Cấu hình prompt:

```
# Role: Chuyên gia tư vấn vấn đề hằng ngày

## Profile
- language: tiếng Trung
- description: chuyên trả lời các câu hỏi thông thường trong đời sống hằng ngày của người dùng, cung cấp lời khuyên và giải đáp thiết thực, chính xác, dễ hiểu
- background: có kinh nghiệm sống phong phú và kho kiến thức rộng, giỏi đơn giản hóa vấn đề phức tạp
- personality: thân thiện, kiên nhẫn tỉ mỉ, thực tế đáng tin
- expertise: đời sống hằng ngày, sức khỏe dưỡng sinh, quản lý gia đình, quan hệ giữa người, kỹ năng thực dụng


## Skills

1. Năng lực phân tích vấn đề
   - Hiểu nhanh: nắm bắt nhanh điểm cốt lõi của vấn đề người dùng
   - Phân loại nhận diện: phán đoán chính xác lĩnh vực đời sống mà vấn đề thuộc về
   - Khai thác nhu cầu: hiểu sâu nhu cầu tiềm ẩn của người dùng
   - Sắp xếp ưu tiên: đánh giá hợp lý tầm quan trọng và tính khẩn cấp của vấn đề

2. Năng lực cung cấp giải đáp
   - Tích hợp kiến thức: vận dụng tổng hợp kiến thức đa lĩnh vực để giải đáp
   - Lập phương án: cung cấp giải pháp cụ thể, khả thi
   - Phân rã bước: chia vấn đề phức tạp thành các bước đơn giản
   - Phương án thay thế: chuẩn bị nhiều phương án để người dùng lựa chọn

3. Năng lực giao tiếp diễn đạt
   - Ngôn ngữ phổ thông: dùng từ ngữ hằng ngày đơn giản dễ hiểu
   - Logic rõ ràng: tổ chức nội dung trả lời mạch lạc
   - Nêu ví dụ: dùng ca cụ thể giúp hiểu
   - Nhấn mạnh trọng tâm: nhấn mạnh thông tin then chốt và điểm cần lưu ý

## Rules

1. Nguyên tắc trả lời:
   - Ưu tiên thực dụng: đảm bảo lời khuyên có thể thao tác
   - Bảo đảm chính xác: trả lời dựa trên thông tin đáng tin và thường thức
   - Trung lập khách quan: tránh thành kiến cá nhân và suy đoán chủ quan
   - Gợi ý vừa phải: cung cấp giải đáp với độ sâu phù hợp theo mức độ phức tạp của vấn đề

2. Chuẩn mực hành vi:
   - Phản hồi kịp thời: nhanh chóng trả lời câu hỏi của người dùng
   - Kiên nhẫn tỉ mỉ: giữ kiên nhẫn với câu hỏi lặp lại hoặc đơn giản
   - Chủ động dẫn dắt: khuyến khích người dùng cung cấp thêm thông tin nền
   - Cải tiến liên tục: tối ưu chất lượng trả lời theo phản hồi


## Workflows

- Mục tiêu: cung cấp cho người dùng giải pháp vấn đề hằng ngày thiết thực, đáng tin
- Bước 1: đọc kỹ và hiểu vấn đề hằng ngày người dùng nêu
- Bước 2: phân tích loại vấn đề và nhu cầu tiềm ẩn của người dùng
- Bước 3: dựa trên thường thức và kinh nghiệm, cung cấp gợi ý cụ thể khả thi
- Bước 4: dùng ngôn ngữ dễ hiểu tổ chức nội dung trả lời
- Bước 5: kiểm tra tính thực dụng và an toàn của câu trả lời


## Initialization
Với vai trò chuyên gia tư vấn vấn đề hằng ngày, bạn phải tuân thủ các Rules trên và thực thi nhiệm vụ theo Workflows.
```

Trình diễn hiệu quả như trong Hình 5.29:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-03.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.29 Trợ lý hằng ngày</p>
</div>

<strong>Mô-đun tối ưu văn bản</strong>

Theo báo cáo dữ liệu của OpenAI, hơn 60% người dùng dùng ChatGPT cho các nhiệm vụ liên quan tối ưu văn bản, gồm trau chuốt, sửa, mở rộng, rút gọn, v.v. Vì vậy, tối ưu văn bản là tình huống nhu cầu tần suất cao; chúng ta đưa nó thành mô-đun chức năng cốt lõi thứ hai.

Cấu hình prompt:

```
# 1. Nhân vật vai trò (Role)
Bạn là một chuyên gia tối ưu văn bản chuyên nghiệp, có kinh nghiệm phong phú về viết và tối ưu văn bản tiếp thị, giỏi nâng cao sức hấp dẫn, tỷ lệ chuyển đổi và khả năng đọc của văn bản. Góc nhìn của bạn là đứng từ phía đối tượng mục tiêu và mục tiêu tiếp thị; biên giới chuyên môn giới hạn trong lĩnh vực tối ưu văn bản, không liên quan hiện thực kỹ thuật hay phát triển sản phẩm.

# 2. Bối cảnh (Background)
Người dùng cung cấp một đoạn văn bản gốc và cần bạn tối ưu để nâng cao hiệu quả tổng thể. Thông tin bối cảnh gồm: văn bản có thể dùng cho tiếp thị, quảng bá thương hiệu hoặc truyền đạt thông tin, nhưng mục đích cụ thể chưa được nói rõ. Điều kiện đã biết là người dùng muốn văn bản hấp dẫn hơn, rõ ràng hơn hoặc có sức thuyết phục hơn, nhưng chưa cung cấp nội dung văn bản gốc, vì vậy bạn cần làm việc dựa trên nguyên tắc tối ưu tổng quát.

# 3. Mục tiêu nhiệm vụ (Task)
- Phân tích và tối ưu cấu trúc, ngôn ngữ và phong cách văn bản, để phù hợp hơn với sở thích của đối tượng mục tiêu.
- Nâng cao sức hấp dẫn, khả năng đọc và tiềm năng chuyển đổi của văn bản, đảm bảo truyền đạt thông tin rõ ràng.
- Điều chỉnh theo các nguyên tắc tối ưu thông thường (như súc tích, đồng cảm cảm xúc, kêu gọi hành động, v.v.), không viết lại nội dung trừ khi cần thiết.
- Trên tiền đề giữ thông tin cốt lõi, mở rộng và làm phong phú nội dung văn bản một cách phù hợp, cung cấp phiên bản tối ưu toàn diện hơn.

# 4. Gợi ý giới hạn (Limit)
- Tránh thay đổi thông tin cốt lõi hoặc ý định của văn bản gốc, trừ khi người dùng yêu cầu rõ ràng.
- Không thêm nội dung hư cấu hoặc không liên quan, đảm bảo tối ưu dựa trên logic và thực tiễn tốt nhất.
- Tránh dùng thuật ngữ quá kỹ thuật hoặc chuyên môn, trừ khi đối tượng mục tiêu là chuyên gia.
- Không liên quan tối ưu hình ảnh, bố cục hoặc các yếu tố phi văn bản khác.

# 5. Yêu cầu định dạng đầu ra (Example)
Đầu ra phải là văn bản đã tối ưu, cấu trúc rõ ràng, ngôn ngữ trôi chảy, nội dung đầy đủ. Ví dụ:
- Nếu văn bản gốc là “Sản phẩm của chúng tôi rất tốt, mau mua đi”
Sau tối ưu có thể là: “Trong thời đại tràn ngập lựa chọn này, điều thực sự chạm đến lòng người chưa bao giờ là lời quảng cáo phóng đại, mà là sản phẩm tốt chịu được thử thách của thời gian và người dùng. Sản phẩm của chúng tôi chính là như vậy. Nó không chỉ chú trọng chi tiết và chất lượng trong thiết kế, mà còn không ngừng mài giũa và đổi mới về chức năng, chỉ để mang lại trải nghiệm sử dụng tốt hơn cho mỗi người dùng. Dù là chất cảm của ngoại hình hay sự ổn định của hiệu năng, chúng tôi luôn kiên trì chuẩn mực cao và yêu cầu nghiêm ngặt, nỗ lực để mỗi khách hàng chọn chúng tôi đều cảm nhận được bất ngờ xứng đáng với đồng tiền.
Chúng tôi hiểu sâu rằng mua một sản phẩm không chỉ là một lần tiêu dùng đơn giản, mà còn là một lựa chọn phương thức sống. Vì vậy, từ chọn nguyên liệu, quy trình đến dịch vụ hậu mãi, mỗi khâu chúng tôi đều dồn trọn thành ý và chuyên môn, tận tâm bảo vệ mỗi trải nghiệm của bạn. Dù bạn theo đuổi tính thực dụng, chú trọng chất lượng, hay muốn sự cá nhân hóa khác biệt, sản phẩm của chúng tôi đều có thể cung cấp giải pháp lý tưởng cho bạn.
Bây giờ, hãy để chúng tôi chứng minh mọi thứ bằng hành động. Sản phẩm tốt thực sự không cần quá nhiều tô điểm; bản thân nó đã là người đại diện tốt nhất. Hành động ngay, chọn chúng tôi, để chất lượng thay đổi cuộc sống, từ đó có trải nghiệm khác biệt!”
- Đầu ra phải trực tiếp trình bày nội dung đã tối ưu, không cần giải thích hoặc chú thích bổ sung, trừ khi người dùng yêu cầu. Hãy đảm bảo nội dung văn bản tối ưu phong phú và đầy đủ hơn; văn bản tối ưu phải dài hơn 500 từ.
```

Trình diễn hiệu quả như trong Hình 5.30:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-04.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.30 Trợ lý văn bản</p>
</div>

<strong>Mô-đun sinh đa phương thức</strong>

Sinh hình ảnh và video là một tình huống ứng dụng tần suất cao khác. Cùng với sự tiến hóa của các mô hình như Doubao sinh ảnh, Google Imagen, và đột phá của công nghệ sinh video như Kling, Google Veo 3, seedance2.0, chất lượng sinh nội dung đa phương thức đã đạt mức thực dụng.

Ca này dùng plugin Jimeng để hiện thực sinh hình ảnh và video. Các bước cấu hình:

1. Thêm plugin Jimeng sinh ảnh/sinh video vào quy trình làm việc.
2. Cấu hình tham số (ví dụ tỷ lệ hình ảnh 1:1, chọn mô hình seedream4.5/5.0 và seedance1.5/2.0).
3. Xuất tệp `file` được sinh.

Ở đây chúng ta dùng plugin Jimeng để gọi các mô hình mới nhất, tức seedream5.0 và seedance2.0. Chất lượng hình ảnh và video đều được nâng cao rõ rệt. Đồng thời ở đây chúng ta dùng vòng lặp để lấy nhiệm vụ video, bổ sung trình diễn ca lấy tham số và phán đoán điều kiện; nội dung cụ thể có thể xem [quy trình làm việc đầy đủ](../../../code/chapter5/HelloAgent_difyCase.yml).

Cấu hình sinh ảnh và hiệu quả như trong Hình 5.31 và Hình 5.32.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-13.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.31 Cài đặt sinh ảnh</p>
</div>
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-05.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.32 Trợ lý sinh ảnh</p>
</div>

Hiệu quả sinh video như trong Hình 5.33.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-06.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.33 Trợ lý video</p>
</div>

<strong>Mô-đun truy vấn và phân tích dữ liệu</strong>

Xử lý dữ liệu là một trong những năng lực quan trọng của Agent. Mô-đun này trình diễn cách kết nối cơ sở dữ liệu trong Dify, hiện thực truy vấn dữ liệu và phân tích trực quan hóa.

Trước tiên cài plugin công cụ truy vấn dữ liệu; ca này dùng plugin `rookie-text2data`. Điểm then chốt của truy vấn dữ liệu là cung cấp cho mô hình lớn cấu trúc bảng và thông tin trường rõ ràng, để nó sinh câu lệnh SQL chính xác. Các cách làm phổ biến gồm:

- Cung cấp trực tiếp câu lệnh DDL của bảng dữ liệu.
- Cung cấp giải thích quan hệ tương ứng giữa tên bảng và tên trường.

Cấu hình thông tin kết nối cơ sở dữ liệu (địa chỉ IP, tên cơ sở dữ liệu, cổng, tài khoản, mật khẩu, v.v.), như trong Hình 5.34. Kết quả truy vấn cần được nút mô hình lớn sắp xếp, chuyển thành đầu ra ngôn ngữ tự nhiên dễ hiểu.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-22.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.34 Cấu hình cơ sở dữ liệu</p>
</div>

Cài đặt prompt:

```
# 1. Nhân vật vai trò (Role)
Bạn là một chuyên gia truy vấn dữ liệu chuyên nghiệp, giỏi sắp xếp dữ liệu, có tư duy logic rõ ràng và khả năng diễn đạt súc tích.

# 2. Bối cảnh (Background)
Người dùng cung cấp dữ liệu gốc truy vấn từ cơ sở dữ liệu; dữ liệu này có thể có các vấn đề như định dạng không thống nhất, thiếu trường, bản ghi trùng lặp, cần được sắp xếp chuyên nghiệp mới có thể trình bày hiệu quả.

# 3. Mục tiêu nhiệm vụ (Task)
1. Tổng hợp và sắp xếp dữ liệu gốc
2. Phân loại và sắp xếp dữ liệu theo logic đúng
3. Trình bày dữ liệu làm nổi bật thông tin then chốt và insight dữ liệu
4. Cung cấp cách trình bày dữ liệu dễ hiểu

# 4. Gợi ý giới hạn (Limit)
1. Không được tùy tiện xóa dữ liệu quan trọng
2. Tránh dùng thuật ngữ thống kê quá phức tạp hoặc chuyên môn
3. Không được sửa đổi giá trị thật của dữ liệu gốc
4. Tránh trình bày quá nhiều thông tin dư thừa, giữ súc tích rõ ràng
5. Không được tiết lộ dữ liệu nhạy cảm hoặc thông tin riêng tư cá nhân

# 5. Yêu cầu định dạng đầu ra (Example)
 Tổng quan dữ liệu: chỉ cần giải thích ngắn gọn nội dung dữ liệu
```

Trình diễn hiệu quả như trong Hình 5.35:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-07.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.35 Trợ lý truy vấn dữ liệu</p>
</div>

Cài đặt prompt:

```
# 1. Nhân vật vai trò (Role)
Bạn là một chuyên gia phân tích dữ liệu chuyên nghiệp, có năng lực sắp xếp, làm sạch và trực quan hóa dữ liệu, có thể trích xuất thông tin then chốt từ dữ liệu gốc và chuyển thành trình bày trực quan.

# 2. Bối cảnh (Background)
Người dùng đã truy vấn một lô dữ liệu gốc từ cơ sở dữ liệu; dữ liệu này có thể gồm nhiều trường, có giá trị thiếu hoặc định dạng không thống nhất, cần được sắp xếp rồi tạo biểu đồ trực quan.

# 3. Mục tiêu nhiệm vụ (Task)
#Quy trình làm việc
1. Phân tích dữ liệu
Phân tích, sắp xếp và tổng kết dữ liệu theo quy tắc hợp lý
2. Phân tích & trực quan hóa
Tạo ít nhất 1 biểu đồ (chọn 1 hoặc nhiều hơn trong biểu đồ cột / đường / tròn)
Có thể gọi công cụ: “generate_pie_chart” | “generate_column_chart” | “generate_line_chart”

# 4. Gợi ý giới hạn (Limit)
1. Tránh dùng loại biểu đồ quá phức tạp, đảm bảo kết quả trực quan dễ hiểu
2. Không bỏ qua vấn đề chất lượng dữ liệu; phải làm sạch dữ liệu cần thiết
3. Tránh dùng quá nhiều màu sắc hoặc yếu tố trong trực quan hóa, giữ súc tích rõ ràng
4. Không bỏ sót chú thích và giải thích của dữ liệu then chốt
5. Bắt buộc tổng kết và tạo biểu đồ, bất kể dữ liệu nhiều hay ít

# 5. Yêu cầu định dạng đầu ra (Example)
Hãy xuất theo định dạng sau:
1. Tổng kết tổng quan dữ liệu (không xuất tên trường, không chia điểm, chỉ một đoạn ngắn)
2. Trình bày biểu đồ đã tạo
```

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-08.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.36 Trợ lý phân tích dữ liệu</p>
</div>

Điểm khác biệt duy nhất của trợ lý phân tích dữ liệu là chúng ta thêm các công cụ trực quan hóa dữ liệu, tức các plugin công cụ tạo biểu đồ “generate_pie_chart” | “generate_column_chart” | “generate_line_chart”; nếu đã cài đặt theo yêu cầu ở phần trước thì có thể thêm trực tiếp để khởi động và sử dụng, đồng thời thêm mô tả tương ứng như prompt ở trên.

<strong>Tích hợp công cụ MCP</strong>

Cuối cùng là ứng dụng tích hợp công cụ MCP. Ở phần trước chúng ta đã hoàn thành cấu hình MCP; bây giờ tích hợp nó vào Agent. Các bước cấu hình:

1. Chọn chiến lược Agent hỗ trợ gọi MCP
2. Chọn chế độ ReAct
3. Cấu hình dịch vụ MCP (lưu ý xóa tiền tố `mcp-server`, chọn chế độ SSE)
4. Điền prompt tương ứng

Giao diện cấu hình như trong Hình 5.37.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-23.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.37 Cấu hình MCP của Agent</p>
</div>

Hiệu quả của trợ lý Amap, trợ lý ăn uống và trợ lý tin tức lần lượt như trong Hình 5.38, Hình 5.39 và Hình 5.40.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-09.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.38 Trợ lý Amap</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-10.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.39 Trợ lý ăn uống</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/dify-11.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.40 Trợ lý tin tức</p>
</div>

Đến đây, chúng ta đã hoàn thành một trợ lý cá nhân siêu Agent đầy đủ chức năng. Trợ lý này bao phủ nhiều khía cạnh của cuộc sống: khi cần quần áo mới, có thể để Doubao sinh thiết kế; trước khi ra ngoài, có thể để trợ lý Amap lập lộ trình; khi không biết ăn gì, có thể nhận gợi ý ăn uống; khi muốn hiểu tình hình học tập, có thể phân tích dữ liệu. Agent này có thể xử lý nhiều loại nhiệm vụ công việc và đời sống; hy vọng sẽ thấy mọi người xây dựng thêm nhiều trợ lý cá nhân sáng tạo.

### 5.3.3 Phân tích ưu điểm và hạn chế của Dify

Dify, với tư cách một nền tảng phát triển ứng dụng AI hàng đầu, thể hiện ưu thế rõ rệt ở nhiều khía cạnh:

1. Ưu điểm cốt lõi

- Trải nghiệm phát triển toàn ngăn xếp: Dify tích hợp các chức năng như pipeline RAG, quy trình làm việc AI, quản lý mô hình vào một nền tảng, cung cấp trải nghiệm phát triển một cửa.
- Cân bằng giữa low-code và khả năng mở rộng cao: Dify đạt cân bằng tốt giữa thuận tiện của phát triển low-code và linh hoạt của phát triển chuyên nghiệp.
- Bảo mật và tuân thủ cấp doanh nghiệp: Dify cung cấp mã hóa AES-256, kiểm soát quyền RBAC và nhật ký kiểm toán, đáp ứng yêu cầu bảo mật và tuân thủ nghiêm ngặt.
- Năng lực tích hợp công cụ phong phú: Dify hỗ trợ hơn 9000 công cụ và tiện ích API, cung cấp khả năng mở rộng chức năng rộng rãi.
- Cộng đồng mã nguồn mở sôi động: Dify có cộng đồng mã nguồn mở sôi động, cung cấp nhiều tài nguyên học tập và hỗ trợ.

2. Hạn chế chính

- Đường cong học tập khá dốc: với người dùng hoàn toàn không có nền tảng kỹ thuật, vẫn tồn tại đường cong học tập nhất định.
- Nút thắt hiệu năng: trong tình huống đồng thời cao có thể gặp thách thức hiệu năng, cần tối ưu phù hợp. Các thành phần dịch vụ máy chủ cốt lõi của hệ thống Dify được hiện thực bằng Python; so với C++, Golang, Rust, hiệu năng tương đối kém hơn.
- Hỗ trợ đa phương thức chưa đủ: hiện chủ yếu xử lý văn bản, hỗ trợ hình ảnh, video, HTML còn hạn chế.
- Chi phí bản doanh nghiệp cao: giá bản doanh nghiệp Dify tương đối cao, có thể vượt ngân sách nhóm nhỏ.
- Vấn đề tương thích API: định dạng API của Dify không tương thích OpenAI, có thể hạn chế tích hợp với một số hệ thống bên thứ ba.

## 5.4 Nền tảng ba: FastGPT

### 5.4.1 Giới thiệu và chức năng cốt lõi của FastGPT

FastGPT là nền tảng hỏi đáp kho tri thức và công cụ xây dựng Agent mã nguồn mở dựa trên mô hình ngôn ngữ lớn, có định vị cốt lõi là “công cụ năng suất AI cấp doanh nghiệp”, tập trung cung cấp giải pháp RAG (truy xuất tăng cường sinh) đơn giản dễ dùng và năng lực biên soạn quy trình làm việc trực quan. Khác với trải nghiệm không cần mã của Coze và năng lực phát triển toàn ngăn xếp của Dify, FastGPT coi hỏi đáp kho tri thức là công dân hạng nhất, tối ưu sâu xoay quanh chuỗi hoàn chỉnh “nhập dữ liệu — chia khối thông minh — truy xuất vector — sinh hội thoại”.

Truy cập trang chủ FastGPT, điều đầu tiên đập vào mắt là tuyên ngôn sản phẩm ngắn gọn mà mạnh mẽ – “công cụ năng suất AI cấp doanh nghiệp”, nhấn mạnh việc xây dựng Agent AI cấp doanh nghiệp an toàn, có thể kiểm soát, như trong Hình 5.41.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-01.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.41 Trang chủ FastGPT</p>
</div>

Sau khi đăng nhập nền tảng, có thể thấy bố cục bàn làm việc rõ ràng. Thanh điều hướng bên trái chia chức năng cốt lõi thành bốn mô-đun: cổng hội thoại, bàn làm việc, kho tri thức và tài khoản. Trong đó mô-đun Agent lại chia thành ba loại: quy trình làm việc, Agent hội thoại và Agent hội thoại V2 (Beta), thuận tiện để người dùng chọn chế độ xây dựng phù hợp với tình huống nghiệp vụ. Khu vực chính cung cấp lối vào nhanh “tạo từ mẫu”, tích hợp sẵn các mẫu chính thức như bậc thầy luyện tập bán hàng, trợ lý dịch tài liệu, bản tin insight xu hướng ngành; bên dưới là danh sách Agent do người dùng tự tạo, như trong Hình 5.42.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-02.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.42 Giao diện chính nền tảng FastGPT</p>
</div>

Về tài khoản và gói dịch vụ, FastGPT cung cấp bản miễn phí để nhà phát triển cá nhân trải nghiệm. Bản miễn phí gồm 100 điểm, 600 chỉ mục kho tri thức, 1 thành viên nhóm, 10 Agent, 3 kho tri thức, lưu lịch sử hội thoại 30 ngày, tốc độ gọi 30 QPM, và quyền tải lên 5 tệp 50MB mỗi lần, như trong Hình 5.43. Với doanh nghiệp vừa và nhỏ và nhóm, nền tảng cũng cung cấp phương án nâng cấp trả phí để đáp ứng nhu cầu đồng thời và lưu trữ cao hơn.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-03.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.43 Gói miễn phí và mức sử dụng của FastGPT</p>
</div>

Năng lực cạnh tranh cốt lõi nhất của FastGPT nằm ở năng lực kho tri thức mạnh mẽ. Nền tảng hỗ trợ nhập nhiều định dạng tệp, gồm các loại tài liệu phổ biến như Word, Markdown, PDF. Như trong Hình 5.44, trong “kho tri thức tổng quát test”, chúng ta có thể tải lên nhiều tệp như giới thiệu học sâu, nhập môn học máy, nội dung tài liệu đấu thầu; hệ thống sẽ tự động chia khối và lập chỉ mục cho tệp; khi trạng thái hiển thị “đã sẵn sàng” là có thể được truy xuất và trích dẫn trong hội thoại.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-12.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.44 Quản lý tệp kho tri thức FastGPT</p>
</div>

Về xử lý tệp, FastGPT cung cấp cấu hình tham số chi tiết. Như trong Hình 5.45, người dùng có thể chọn hai cách xử lý “lưu theo khối” hoặc “trích xuất cặp hỏi đáp”, đặt điều kiện chia khối (ví dụ khi độ dài văn bản gốc lớn hơn 1000 ký tự thì kích hoạt chia khối), và bật nhiều tùy chọn tăng cường chỉ mục, gồm thêm tiêu đề vào chỉ mục, tự động sinh chỉ mục bổ sung và tự động lập chỉ mục hình ảnh. Với tài liệu có nhiều nội dung xen kẽ hình và chữ (như giáo trình, báo cáo nghiên cứu), chức năng tự động lập chỉ mục hình ảnh đặc biệt quan trọng, cho phép mô hình lớn hiểu và trích dẫn thông tin hình ảnh trong tài liệu khi trả lời.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-14.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.45 Cài đặt tham số xử lý dữ liệu kho tri thức</p>
</div>

Sau khi tải lên, người dùng có thể xem nội dung cụ thể sau khi tệp được chia khối. Như trong Hình 5.46, lấy “sách điện tử toàn bộ học kỳ hai tiếng Anh lớp 4.pdf” làm ví dụ, nền tảng hiển thị bản xem trước văn bản của từng khối, đồng thời bảng siêu dữ liệu bên phải hiển thị các thông tin then chốt như kích thước tệp (62MB), độ dài văn bản gốc (37797 ký tự), chế độ xử lý (lưu theo khối), trạng thái chỉ mục hình ảnh. Cách hiển thị chia khối minh bạch này thuận tiện cho nhà phát triển gỡ lỗi và tối ưu kho tri thức.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-13.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.46 Chi tiết chia khối và siêu dữ liệu tệp kho tri thức</p>
</div>

Ngoài kho tri thức, FastGPT cũng bám sát xu hướng hệ sinh thái về tích hợp công cụ. Nền tảng hỗ trợ native công cụ MCP (Model Context Protocol); người dùng có thể quản lý thống nhất các dịch vụ MCP trong mô-đun “công cụ của tôi”. Như trong Hình 5.47, trong thư mục “ai tài chính”, chúng ta đã cấu hình nhiều công cụ MCP như tổng hợp xu hướng tiếng Trung, MCP cổ phiếu thời gian thực, MCP quỹ Qieman, Minimax-MCP, công cụ vẽ BI; những công cụ này trao cho Agent năng lực gọi dữ liệu thời gian thực bên ngoài và dịch vụ chuyên nghiệp.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-04.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.47 Quản lý công cụ MCP của FastGPT</p>
</div>

### 5.4.2 Xây dựng “trợ lý cố vấn đầu tư thông minh”

**Mô tả ca:** ca này dựa trên nền tảng FastGPT, kết hợp kho tri thức, công cụ MCP và biên soạn quy trình làm việc để xây dựng một “trợ lý cố vấn đầu tư thông minh” chuyên nghiệp. Trợ lý có thể trả lời câu hỏi lý thuyết đầu tư tài chính, tra cứu giá cổ phiếu thời gian thực, đánh giá hồ sơ rủi ro người dùng và sinh báo cáo phân tích chiến lược đầu tư cá nhân hóa. Qua ca này, bạn sẽ nắm mô hình phát triển cốt lõi của FastGPT: xây dựng kho tri thức, kết nối công cụ MCP, biên soạn quy trình làm việc trực quan và thiết kế tương tác hội thoại nhiều lượt.

**Bước một: cấu hình công cụ MCP**

Một trong những năng lực cốt lõi của trợ lý cố vấn đầu tư thông minh là lấy dữ liệu tài chính thời gian thực. Trong FastGPT, chúng ta hiện thực chức năng này bằng cách kết nối công cụ MCP.

Ca này cần hai loại dịch vụ MCP sau:

1. **Tra cứu giá cổ phiếu thời gian thực**: dùng để lấy giá hiện tại, mức tăng/giảm, khối lượng giao dịch của từng cổ phiếu.
2. **Dữ liệu tài chính và sinh biểu đồ**: dùng để lấy dữ liệu tài chính vĩ mô và tạo biểu đồ trực quan.

Như trong Hình 5.48, chúng ta có thể tìm “Máy chủ MCP biểu đồ trực quan” trong chợ MCP của cộng đồng ModelScope. Dịch vụ này phát triển bằng TypeScript, tương thích giao thức MCP, cung cấp khả năng tạo nhiều loại biểu đồ như biểu đồ vùng, cột, tròn, có thể chuyển dữ liệu khô khan thành kết quả trực quan dễ hiểu.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-05.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.48 Máy chủ MCP biểu đồ trực quan của cộng đồng ModelScope</p>
</div>

Ngoài ra, như trong Hình 5.49, nền tảng Alibaba Cloud Bailian cũng cung cấp nhiều dịch vụ MCP chính thức phong phú. Trong trang quản lý MCP, chúng ta có thể tìm các dịch vụ MCP tài chính như “Today Investment - Tài chính thực...”, “Qieman”, cùng các công cụ như tra cứu giá cổ phiếu thời gian thực, Wanxiang - sinh video. Sau khi thêm các dịch vụ này vào thư viện công cụ MCP của FastGPT, Agent có thể gọi chúng theo nhu cầu trong hội thoại.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-06.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.49 Quản lý MCP của Alibaba Cloud Bailian</p>
</div>

Trong giao diện cấu hình công cụ MCP của FastGPT, điền địa chỉ dịch vụ, thông tin xác thực tương ứng là có thể hoàn thành kết nối công cụ. Mỗi công cụ MCP có thể đặt mô tả và tham số gọi độc lập, thuận tiện để Agent hiểu mục đích của từng công cụ khi ra quyết định.

**Bước hai: thiết kế quy trình làm việc cố vấn đầu tư thông minh**

Sau khi cấu hình công cụ, bước vào mắt xích cốt lõi là biên soạn quy trình làm việc. FastGPT cung cấp giao diện biên soạn Flow trực quan; người dùng có thể xây dựng luồng hội thoại phức tạp bằng cách kéo thả nút, nối đường.

Như trong Hình 5.50, quy trình làm việc hoàn chỉnh của “trợ lý cố vấn đầu tư thông minh” gồm nhiều nhánh xử lý: nhận diện ý định người dùng, truy xuất kho tri thức, thu thập bảng hỏi rủi ro, gọi công cụ MCP, sinh báo cáo, v.v. Toàn bộ quy trình thể hiện cấu trúc mô-đun rõ ràng, dữ liệu chảy có trật tự giữa các nút. Cách biên soạn trực quan này cho phép nhà phát triển hiểu và gỡ lỗi đường đi quyết định của Agent một cách trực quan.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-07.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.50 Biên soạn quy trình làm việc trợ lý cố vấn đầu tư thông minh</p>
</div>

Logic cốt lõi của quy trình làm việc như sau:

1. **Nút nhận diện ý định**: trước tiên phán đoán loại đầu vào của người dùng. Nếu là tư vấn khái niệm tài chính, đi nhánh truy xuất kho tri thức; nếu là tra cứu cổ phiếu, đi nhánh gọi công cụ MCP; nếu là chẩn đoán đầu tư, vào quy trình thu thập bảng hỏi rủi ro.
2. **Chuyên viên giáo dục kiến thức đầu tư**: kết nối đến kho tri thức tài chính đã xây dựng trước, truy xuất lý thuyết đầu tư, giải thích khái niệm và phân tích ca liên quan.
3. **Chuyên viên phân tích đánh giá rủi ro**: qua nút nhập biểu mẫu dẫn dắt người dùng hoàn thành bảng hỏi đánh giá rủi ro, gồm các chiều như tuổi, kinh nghiệm đầu tư, mức thu nhập hằng tháng, khả năng chịu rủi ro và mục tiêu đầu tư; sau đó truyền dữ liệu cho nút mô hình lớn tiếp theo để phân tích môi trường thị trường, yếu tố cơ bản, cảm xúc tin tức, tích hợp hồ sơ người dùng, dữ liệu thị trường và thông tin tin tức, gọi mô hình lớn sinh báo cáo phân tích chiến lược đầu tư có cấu trúc.
4. **Chuyên viên tình báo tin tức thị trường**: theo nhu cầu người dùng, gọi MCP cổ phiếu thời gian thực hoặc MCP sinh biểu đồ để lấy dữ liệu bên ngoài.
5. **Chuyên viên tư vấn tổng quát**: trả lời nội dung đơn giản theo câu hỏi tư vấn của người dùng, như “xin chào”, “bạn khỏe không”.

**Bước ba: cấu hình prompt và kho tri thức**

Trong FastGPT, cấu hình prompt (System Prompt) cũng cực kỳ quan trọng. Với trợ lý cố vấn đầu tư thông minh, chúng ta cần đặt cho nó vai cố vấn đầu tư tài chính chuyên nghiệp:

```
# 1. Nhân vật vai trò (Role)
Bạn là một cố vấn đầu tư tài chính chuyên nghiệp, có kinh nghiệm phong phú về đánh giá rủi ro và quản lý danh mục đầu tư. Nền tảng chuyên môn của bạn gồm tài chính học, tài chính hành vi và tâm lý học đầu tư, có thể phân tích khả năng chịu rủi ro của người dùng từ nhiều chiều. Phong cách giọng điệu của bạn phải chuyên nghiệp, trung lập và dễ hiểu, tránh dùng thuật ngữ tài chính quá phức tạp, đảm bảo nhà đầu tư thông thường cũng dễ hiểu phân tích của bạn.

# 2. Bối cảnh
Người dùng sẽ cung cấp các thông tin sau: tuổi, kinh nghiệm đầu tư, mức thu nhập hằng tháng, mức lỗ tối đa có thể chịu, mục tiêu đầu tư. Những thông tin này là nền tảng đánh giá rủi ro; bạn cần dựa trên dữ liệu này, kết hợp nguyên tắc tài chính thông thường (như lý thuyết vòng đời, nguyên tắc khớp rủi ro – lợi nhuận) để phân tích. Giới hạn tình huống là bạn không thể lấy thông tin cá nhân khác của người dùng (như tổng tài sản, tình trạng gia đình), vì vậy phân tích nên tập trung vào thông tin được cung cấp, tránh suy đoán quá mức.

# 3. Mục tiêu nhiệm vụ (Task)
Dựa trên tuổi, kinh nghiệm đầu tư, mức thu nhập hằng tháng, mức lỗ tối đa có thể chịu, mục tiêu đầu tư do người dùng cung cấp, thực hiện đánh giá rủi ro tổng hợp.
Xuất một kết quả đánh giá cấp độ rủi ro rõ ràng (ví dụ: thận trọng, ổn định, tích cực, v.v.), và giải thích ngắn gọn lý do.
Đảm bảo logic phân tích mạch lạc, dễ hiểu và dễ áp dụng với người dùng.

# 4. Gợi ý giới hạn (Limit)
Tránh cung cấp khuyến nghị sản phẩm tài chính cụ thể (như tên cổ phiếu hoặc quỹ cụ thể), chỉ thảo luận loại tài sản chung.
Không được đưa ra bất kỳ cam kết hoặc dự đoán đảm bảo lợi nhuận; nhấn mạnh đầu tư có rủi ro.
Tránh dùng ngôn ngữ quá kỹ thuật hoặc chuyên môn hóa, đảm bảo nội dung đầu ra thân thiện với nhà đầu tư không chuyên.
Không mở rộng thông tin người dùng dựa trên giả định hoặc suy đoán; chỉ dùng tuổi, kinh nghiệm đầu tư, thu nhập hằng tháng, khả năng chịu lỗ tối đa và mục tiêu đầu tư được cung cấp để phân tích.
Đầu ra không được chứa bất kỳ phát biểu phân biệt đối xử, thành kiến hoặc chủ quan mạnh; giữ khách quan trung lập.

# 5. Yêu cầu định dạng đầu ra (Example)
Đầu ra phải được tổ chức theo cấu trúc sau:
**Đánh giá cấp độ rủi ro**: [ví dụ: ổn định]
**Lý do đánh giá**: giải thích ngắn gọn phân tích dựa trên tuổi, kinh nghiệm đầu tư, thu nhập, khả năng chịu lỗ và mục tiêu đầu tư của người dùng.
**Cảnh báo rủi ro**: nhắc lại rủi ro đầu tư, khuyến khích người dùng điều chỉnh theo tình hình bản thân.
```

Đồng thời, chúng ta cần cấu hình kho tri thức tài chính cho trợ lý. Tải các tài liệu như cơ sở đầu tư học, phân tích báo cáo tài chính, giải thích chỉ số kinh tế vĩ mô lên kho tri thức, hoàn thành chia khối và lập chỉ mục theo quy trình trong Hình 5.44 ~ Hình 5.46. Như vậy, khi người dùng hỏi các câu hỏi khái niệm như “tỷ lệ P/E và tỷ lệ P/B khác nhau thế nào”, Agent có thể truy xuất định nghĩa chính xác và phân tích so sánh từ kho tri thức, thay vì hoàn toàn dựa vào kiến thức tiền huấn luyện của mô hình lớn, từ đó giảm hiệu quả rủi ro ảo giác.

**Bước bốn: kiểm thử và trình diễn hiệu quả**

Sau khi hoàn thành cấu hình quy trình làm việc và prompt, chúng ta có thể kiểm thử trong giao diện hội thoại của FastGPT. Như trong Hình 5.51, lời mở đầu của trợ lý cố vấn đầu tư thông minh giới thiệu rõ ba đặc điểm chức năng của nó: tinh thông lý thuyết đầu tư tài chính, cung cấp tin tức và dữ liệu thị trường thời gian thực, đưa ra gợi ý phân bổ tài sản theo đánh giá hồ sơ rủi ro. Bên dưới giao diện còn có các nút thao tác nhanh, thuận tiện để người dùng kích hoạt nhiệm vụ thường gặp bằng một cú nhấp.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-08.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.51 Giao diện hội thoại trợ lý cố vấn đầu tư thông minh</p>
</div>

Khi người dùng nhấp “thực hiện đánh giá tài sản để nhận ý kiến đầu tư”, trợ lý sẽ lần lượt mở bảng hỏi đánh giá rủi ro, thu thập thông tin như tuổi, kinh nghiệm đầu tư, mức thu nhập hằng tháng, mức lỗ tối đa có thể chịu và mục tiêu đầu tư. Dựa trên những thông tin này, trợ lý sinh một báo cáo phân tích chiến lược đầu tư hoàn chỉnh.

Như trong Hình 5.52, báo cáo gồm các mô-đun cốt lõi sau:

- **Đánh giá rủi ro người dùng**: dựa trên kết quả bảng hỏi, phân tích cấp độ khả năng chịu rủi ro của người dùng (như ổn định).
- **Gợi ý tỷ lệ phân bổ tài sản**: trình bày tỷ lệ phân bổ các loại tài sản lớn như cổ phiếu, trái phiếu, tiền mặt dưới dạng biểu đồ tròn trực quan (ví dụ cổ phiếu 45%, trái phiếu 40%, tiền mặt 15%).
- **Phân tích yếu tố cơ bản thị trường**: kết hợp môi trường kinh tế vĩ mô hiện tại và xu hướng ngành để đưa ra phán đoán thị trường.
- **Chiến lược tái cân bằng**: cung cấp phương án gợi ý điều chỉnh danh mục định kỳ, gồm chu kỳ điều chỉnh và điều kiện kích hoạt.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-09.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.52 Báo cáo phân tích chiến lược đầu tư</p>
</div>

Với tình huống truy vấn dữ liệu thời gian thực, như trong Hình 5.53, khi người dùng hỏi “tra cứu thông tin giá cổ phiếu Kweichow Moutai hiện tại”, Agent sẽ tự động gọi công cụ MCP (`get_stock_quote_realtime`) để lấy dữ liệu thị trường thời gian thực. Kết quả trả về gồm tiêu đề, nguồn dữ liệu, điểm chính (giá mở cửa, giá cao nhất, khoảng giá trong ngày, khối lượng giao dịch, tổng vốn hóa, vốn hóa lưu hành, v.v.), cùng phân tích ảnh hưởng tiềm năng và hành động gợi ý. Đầu ra có cấu trúc, chuyên nghiệp này thể hiện giá trị thực tế của năng lực gọi công cụ của Agent.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-10.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.53 Tra cứu giá cổ phiếu thời gian thực</p>
</div>

Về giải thích khái niệm, như trong Hình 5.54, khi người dùng hỏi “tỷ lệ P/E và tỷ lệ P/B khác nhau thế nào”, trợ lý dựa trên kho tri thức và sự hiểu biết của mô hình lớn đưa ra phân tích so sánh có hệ thống: bắt đầu từ định nghĩa, giải thích chi tiết cách tính tỷ lệ P/E (P/E Ratio) và tỷ lệ P/B (P/B Ratio); so sánh từ bốn chiều (cơ sở tính toán, ngành áp dụng, thông tin phản ánh, hạn chế); cuối cùng đưa ra gợi ý ứng dụng thực tế, giải thích khi nào nên chú trọng P/E, khi nào nên chú trọng P/B. Đầu ra phân tầng rõ ràng, logic chặt chẽ này chính là ưu thế điển hình của mô hình lớn được tăng cường RAG trong hỏi đáp lĩnh vực chuyên môn.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/fastgpt-11.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 5.54 Phân tích khái niệm tỷ lệ P/E và tỷ lệ P/B</p>
</div>

### 5.4.3 Phân tích ưu điểm và hạn chế của FastGPT

Qua thực hành xây dựng “trợ lý cố vấn đầu tư thông minh” ở trên, chúng ta có thể hình thành nhận thức tương đối toàn diện về nền tảng FastGPT.

**Ưu điểm:**

- **Trải nghiệm kho tri thức cực hạn**: ưu thế cốt lõi nhất của FastGPT nằm ở việc mài giũa sâu chuỗi RAG. Từ tải tệp, chia khối thông minh, tăng cường chỉ mục, nhận diện hình ảnh đến truy xuất và gọi lại, mỗi mắt xích đều cung cấp tùy chọn cấu hình chi tiết và giao diện gỡ lỗi minh bạch. Với tình huống cần xây dựng hệ thống hỏi đáp dựa trên kho tri thức riêng (như trợ lý tri thức doanh nghiệp, chăm sóc khách hàng thông minh, tư vấn lĩnh vực chuyên môn), FastGPT cung cấp trải nghiệm xuất sắc dùng được ngay.
- **Hỗ trợ MCP native**: khác với Coze, FastGPT hỗ trợ native giao thức MCP, có thể kết nối liền mạch lượng lớn dịch vụ MCP trong hệ sinh thái như cộng đồng ModelScope, Alibaba Cloud Bailian. Điều này khiến năng lực mở rộng công cụ của Agent không còn bị giới hạn bởi thư viện plugin tích hợp của nền tảng; nhà phát triển có thể tự do kết nối bất kỳ công cụ bên thứ ba nào đáp ứng chuẩn MCP.
- **Thiết kế trung lập mô hình**: FastGPT hỗ trợ kết nối linh hoạt nhiều mô hình lớn chủ lưu trong và ngoài nước như OpenAI, Claude, Qwen, DeepSeek; người dùng có thể tự do chuyển đổi mô hình nền tảng theo nhu cầu nghiệp vụ và cân nhắc chi phí, tránh rủi ro bị ràng buộc bởi một nhà cung cấp mô hình duy nhất.
- **Biên soạn quy trình làm việc trực quan**: mô-đun Flow cung cấp giao diện biên soạn dạng nút trực quan; logic nhiều nhánh phức tạp (như nhận diện ý định, thu thập bảng hỏi, sinh báo cáo trong ca này) có thể xây dựng nhanh bằng kéo thả, hạ thấp ngưỡng tiếp cận cho người không phải nhà phát triển.

**Hạn chế:**

- **Hệ sinh thái mẫu tương đối yếu**: so với cửa hàng plugin phong phú của Coze và Marketplace hơn 8000 plugin của Dify, số lượng mẫu chính thức và công cụ đặt trước của FastGPT tương đối hạn chế. Mặc dù giao thức MCP bù đắp phần nào điểm yếu này, với người dùng phi kỹ thuật, việc tìm và cấu hình dịch vụ MCP phù hợp vẫn có ngưỡng nhất định.
- **Hạn mức bản miễn phí khá eo hẹp**: bản miễn phí chỉ cung cấp 100 điểm và tốc độ gọi 30 QPM; với nhà phát triển cần kiểm thử và lặp thường xuyên, hạn mức tiêu hao khá nhanh. Giới hạn số chỉ mục kho tri thức và số thành viên nhóm cũng khiến bản miễn phí khó hỗ trợ cộng tác nhóm ở quy mô hơi lớn.
- **Cộng đồng và tài liệu vẫn đang hoàn thiện**: là một dự án mã nguồn mở tương đối trẻ, mức độ sôi động của cộng đồng và độ hoàn thiện tài liệu tiếng Anh của FastGPT còn khoảng cách nhất định so với các nền tảng trưởng thành như Dify, n8n. Khi gặp vấn đề biên, có thể cần đi sâu vào mã nguồn hoặc nhờ cộng đồng.

Tổng thể, FastGPT là một nền tảng có sức cạnh tranh rất lớn trong lĩnh vực hỏi đáp kho tri thức. Nếu nhu cầu cốt lõi của bạn là xây dựng hệ thống hỏi đáp thông minh dựa trên tài liệu riêng, và muốn có năng lực kiểm soát chi tiết toàn bộ quy trình RAG, FastGPT là lựa chọn rất đáng thử. Còn với tình huống cần hệ sinh thái plugin cực mạnh hoặc tự động hóa quy trình nghiệp vụ phức tạp, có thể kết hợp bổ trợ với Dify hoặc n8n.

## 5.5 Nền tảng bốn: n8n

Như đã giới thiệu trước đó, thân phận cốt lõi của n8n là một nền tảng tự động hóa quy trình làm việc tổng quát, không phải công cụ xây dựng ứng dụng LLM thuần túy. Hiểu điều này là chìa khóa nắm vững n8n. Khi dùng n8n xây dựng ứng dụng thông minh, thực chất chúng ta đang thiết kế một quy trình tự động hóa lớn hơn, và mô hình ngôn ngữ lớn chỉ là một (hoặc nhiều) “nút xử lý” mạnh mẽ trong quy trình đó.

### 5.5.1 Nút và quy trình làm việc của n8n

Thế giới n8n được tạo thành từ hai khái niệm cơ bản nhất: <strong>nút (Node)</strong> và <strong>quy trình làm việc (Workflow)</strong>.

- <strong>Nút (Node)</strong>: nút là đơn vị nhỏ nhất thực hiện thao tác cụ thể trong quy trình làm việc. Có thể hình dung nó như một “khối lego” có chức năng nhất định. n8n cung cấp hàng trăm nút đặt trước, bao phủ nhiều thao tác thường gặp từ gửi email, đọc/ghi cơ sở dữ liệu, gọi API đến xử lý tệp. Mỗi nút có đầu vào và đầu ra, đồng thời cung cấp giao diện cấu hình đồ họa. Nút đại khái có thể chia hai loại:
  - <strong>Nút kích hoạt (Trigger Node)</strong>: là điểm khởi đầu của toàn bộ quy trình làm việc, chịu trách nhiệm khởi động luồng. Ví dụ “khi nhận được một email Gmail mới”, “kích hoạt định kỳ mỗi giờ” hoặc “khi nhận được yêu cầu Webhook”. Một quy trình làm việc phải có và chỉ có một nút kích hoạt.
  - <strong>Nút thông thường (Regular Node)</strong>: chịu trách nhiệm xử lý dữ liệu và logic cụ thể. Ví dụ “đọc bảng Google Sheets”, “gọi mô hình OpenAI” hoặc “chèn một bản ghi vào cơ sở dữ liệu”.
- <strong>Quy trình làm việc (Workflow)</strong>: quy trình làm việc là sơ đồ tự động hóa được tạo bằng cách kết nối nhiều nút. Nó định nghĩa đường đi hoàn chỉnh của dữ liệu từ nút kích hoạt, được truyền và xử lý từng bước giữa các nút như thế nào, và cuối cùng hoàn thành nhiệm vụ đặt trước. Dữ liệu được truyền giữa các nút dưới định dạng JSON có cấu trúc, cho phép chúng ta kiểm soát chính xác đầu vào và đầu ra của từng mắt xích.

Sức mạnh thực sự của n8n nằm ở năng lực “kết nối” mạnh mẽ. Nó có thể nối các ứng dụng và dịch vụ vốn cô lập (như CRM nội bộ doanh nghiệp, nền tảng mạng xã hội bên ngoài, cơ sở dữ liệu của bạn và mô hình ngôn ngữ lớn) thành một chuỗi, hiện thực tự động hóa quy trình nghiệp vụ đầu-cuối mà trước đây cần mã hóa phức tạp mới làm được. Trong thực chiến tiếp theo, chúng ta sẽ tự tay trải nghiệm cách dùng hệ thống nút và quy trình làm việc này để xây dựng một ứng dụng tự động hóa tích hợp năng lực AI.

### 5.5.2 Xây dựng trợ lý email thông minh

Về cấu hình môi trường và cách dùng cơ bản nhất của n8n, đã có tài liệu trong thư mục `Additional-Chapter` của dự án; ở đây không giới thiệu quá nhiều. Ở mục trước, chúng ta đã hiểu khái niệm cơ bản của n8n. Ca này sẽ thể hiện rõ sự khác biệt cốt lõi giữa Agent AI hiện đại và quy trình tự động hóa truyền thống. Quy trình truyền thống là tuyến tính, còn Agent chúng ta sắp xây dựng có thể nhận email người dùng, “suy nghĩ” qua một <strong>nút AI Agent</strong> cốt lõi, tự chủ hiểu ý định người dùng, ra quyết định và lựa chọn trong nhiều “công cụ” khả dụng, cuối cùng tự động sinh và gửi phản hồi có liên quan cao.

Toàn bộ quá trình mô phỏng logic ra quyết định cao cấp hơn: `nhận -> AI Agent (suy nghĩ -> quyết định -> gọi công cụ) -> trả lời`, như trong Hình 5.55.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-01.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 5.55 Sơ đồ kiến trúc Agent email thông minh tích hợp</p>
</div>

Khác với phương pháp truyền thống chia công cụ thành nhiều quy trình làm việc con, nút `AI Agent` của n8n cho phép tích hợp các thành phần như mô hình ngôn ngữ lớn (LLM), bộ nhớ (Memory), công cụ (Tools) vào một giao diện thống nhất, đơn giản hóa rất nhiều quá trình xây dựng.

Toàn bộ quá trình xây dựng chia thành hai bước cốt lõi:

1. <strong>Chuẩn bị “bộ nhớ” cho Agent</strong>: tạo một quy trình độc lập để nạp kho tri thức riêng cho Agent.
2. <strong>Xây dựng thân Agent</strong>: tạo quy trình làm việc chính nhận email, suy nghĩ và trả lời.

### 5.5.3 Xây dựng kho tri thức riêng cho Agent

Để Agent có thể trả lời câu hỏi về lĩnh vực cụ thể (như thông tin cá nhân hoặc tài liệu dự án của bạn), chúng ta cần chuẩn bị trước cho nó một “bộ não bên ngoài” – kho tri thức vector.

Trong n8n, chúng ta có thể dùng nút `Simple Vector Store` để nhanh chóng xây dựng kho tri thức trong bộ nhớ. Quy trình chuẩn bị này thường chỉ cần chạy một lần khi cập nhật tri thức.

<strong>(1) Định nghĩa nguồn tri thức</strong>

Trước tiên, chúng ta dùng nút `Code` để lưu văn bản tri thức gốc. Đây là cách đơn giản nhanh chóng; trong dự án thực tế, dữ liệu cũng có thể đến từ tệp, cơ sở dữ liệu, v.v.

- <strong>Nút</strong>: `Code`
- <strong>Nội dung</strong>: ghi tri thức của bạn dưới định dạng JSON.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-02.png" alt="Ảnh chụp nút Code điền văn bản JSON kho tri thức" width="90%"/>
  <p>Hình 5.56 Định nghĩa nguồn tri thức trong nút Code</p>
</div>

```javascript
return [
  {
    "doc_id": "work-schedule-001",
    "content": "Giờ làm việc của tôi là từ thứ Hai đến thứ Sáu, 9 giờ sáng đến 5 giờ chiều. Múi giờ là Giờ chuẩn Đông Úc (AEST)."
  },
  {

  {
    "doc_id": "off-hours-policy-001",
    "content": "Ngoài giờ làm việc (gồm cuối tuần và ngày lễ), tôi không thể trả lời email ngay lập tức."
  },
  {
    "doc_id": "auto-reply-instruction-001",
    "content": "Nếu email được nhận ngoài giờ làm việc, trợ lý AI nên thông báo cho người gửi rằng email đã được nhận, và tôi sẽ xử lý và trả lời sớm nhất có thể trong khoảng 9 giờ đến 5 giờ của ngày làm việc tiếp theo."
  }
];
```

<strong>(2) Vector hóa văn bản (Embeddings)</strong>

Máy tính không thể hiểu trực tiếp văn bản; cần chuyển nó thành vector. Chúng ta dùng nút `Embeddings` để hoàn thành công việc “dịch” này.

- <strong>Nút</strong>: `Embeddings Google Gemini`, chọn mô hình `gemini-embedding-exp-03-07`. Ở đây dùng Google API để trình diễn; nếu không biết cách lấy Google API, có thể tham khảo [tài liệu chính thức](https://gemini-api.apifox.cn/).
- <strong>Cấu hình</strong>: kết nối nó sau nút `Code`; nó sẽ tự động chuyển văn bản do nút phía trước truyền vào thành dữ liệu vector.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-03.png" alt="" width="90%"/>
  <p>Hình 5.57 Vector hóa dữ liệu trong Code</p>
</div>

<strong>(3) Lưu vào kho vector</strong>

Cuối cùng, chúng ta lưu tri thức đã vector hóa vào cơ sở dữ liệu bộ nhớ, như trong Hình 5.58.

- <strong>Nút</strong>: `Simple Vector Store`
- <strong>Cấu hình</strong>:
  - <strong>Operation Mode</strong>: `Insert Documents` (chế độ ghi).
  - <strong>Memory Key</strong>: đặt một tên duy nhất cho kho tri thức này, ví dụ `my-dailytime`. Key này tương đương “tên bảng” của cơ sở dữ liệu; Agent sau đó sẽ dùng nó để tra cứu thông tin.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-04.png" alt="" width="90%"/>
  <p>Hình 5.58 Lưu dữ liệu trong Code vào kho vector</p>
</div>

Sau khi cấu hình xong, <strong>thực thi thủ công một lần</strong> quy trình này. Sau khi thành công, tri thức riêng của bạn đã được nạp vào bộ nhớ n8n, như trong Hình 5.59.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-05.png" alt="" width="90%"/>
  <p>Hình 5.59 Quy trình làm việc nạp kho tri thức hoàn chỉnh</p>
</div>

### 5.5.4 Tạo quy trình làm việc chính của Agent

Đã có công cụ, bây giờ chúng ta bắt đầu xây dựng luồng chính của Agent. Nó sẽ chịu trách nhiệm nhận email, suy nghĩ và ra quyết định, gọi công cụ chúng ta vừa tạo vào thời điểm phù hợp, và cuối cùng thực hiện trả lời email.

(1) Cấu hình trigger Gmail

Tạo một quy trình làm việc mới, đặt tên `Agent: Customer Support`. Dùng nút `Gmail` làm trigger, đặt <strong>Event</strong> thành `Message Received`, và cấu hình tài khoản email của bạn. Như vậy, mỗi khi có email mới vào hộp thư, quy trình làm việc sẽ tự động được kích hoạt, như trong Hình 5.60.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-06.png" alt="" width="90%"/>
  <p>Hình 5.60 Sơ đồ nút Gmail mới</p>
</div>

Quá trình cấu hình có thể tham khảo [tài liệu chính thức n8n](https://docs.n8n.io/integrations/builtin/credentials/google/oauth-single-service/?utm_source=n8n_app&utm_medium=credential_settings&utm_campaign=create_new_credentials_modal#enable-apis). API Gmail được [cấu hình tại đây](https://console.cloud.google.com/apis/library/gmail.googleapis.com?project=apt-entropy-471905-b9); cần tạo thông tin xác thực, chọn loại ứng dụng Web, cuối cùng nhận được Client ID và Client Secret cần thiết. Đồng thời cần thêm OAuth Redirect URL mà n8n vừa cung cấp vào mục URI chuyển hướng được ủy quyền. Ngoài ra, cần thêm địa chỉ email của bạn vào Add users trong [đối tượng mục tiêu](https://console.cloud.google.com/auth/audience?project=apt-entropy-471905-b9). Trang cấu hình hoàn chỉnh như trong Hình 5.61.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-07.png" alt="" width="90%"/>
  <p>Hình 5.61 Trang tải tài khoản Gmail thành công</p>
</div>

Bây giờ chúng ta có thể nhấp `Fetch Test Event` để lấy email, như trong Hình 5.62!

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-08.png" alt="" width="90%"/>
  <p>Hình 5.62 Hình ảnh lấy email thời gian thực</p>
</div>

(2) Cấu hình nút AI Agent

Đây là bộ não của toàn bộ quy trình làm việc. Kéo một nút `AI Agent` từ menu nút, và cấu hình như sau:

- <strong>Chat Model</strong>: kết nối mô hình ngôn ngữ lớn bạn chọn, ví dụ `Google Gemini Chat Model`. Đây là “lõi suy nghĩ” của Agent.
- <strong>Memory</strong>: kết nối một nút `Simple Memory`. Điều này cho phép Agent ghi nhớ lịch sử hội thoại trước đó khi xử lý nhiều email qua lại trong cùng một luồng email.
- <strong>Tools</strong>: chúng ta có thể kết nối nhiều công cụ vào đây. Trong ca của chúng ta, kết nối hai công cụ:
  1. `SerpAPI`: API đã dùng trong ca chương 4, cho phép Agent có năng lực tìm kiếm thông tin công khai trên mạng.
  2. `Simple Vector Store`: cho phép Agent truy vấn kho tri thức riêng đã tạo ở phần một.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-09.png" alt="" width="90%"/>
  <p>Hình 5.63 Sơ đồ cài đặt nút AI Agent</p>
</div>

Đây là bước đầu tiên Agent “suy nghĩ”. Thêm một nút `Gemini` (hoặc nút LLM khác), đặt chế độ `Chat`. Mục tiêu là để nó phân tích nội dung email và phán đoán ý định người dùng. Thiết kế prompt rất quan trọng; một chỉ thị rõ ràng giúp LLM hoàn thành nhiệm vụ chính xác hơn. Chúng ta truyền nội dung và tiêu đề email (`{{ $json.snippet }}{{ $json.Subject }}`) làm biến vào prompt. Nếu không có API, có thể vào [Google AI Studio](https://aistudio.google.com/prompts/new_chat) nhấp Get API key để tạo một API khả dụng.

Trong đó, với nút AI Agent, phần chính cần điền là `User Message` và `System Message`, như trong Hình 5.64.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-10.png" alt="" width="90%"/>
  <p>Hình 5.64 Sơ đồ chi tiết nút AI Agent</p>
</div>

Dưới đây là prompt dùng trong ca của chúng ta:

```json
# Prompt (User Message)
# Thông tin ngữ cảnh
- Thời gian hiện tại: {{ new Date().toLocaleString('en-AU', { timeZone: 'Australia/Sydney', hour12: false }) }} (giờ Sydney, Úc)
- Người gửi: {{ $json.From }}
- Chủ đề: {{ $json.Subject }}
- Nội dung email: {{ $json.snippet }}

# System Message
# Vai trò và mục tiêu
Bạn là trợ lý email AI trực chiến 24/7, chuyên nghiệp và hiệu quả. Nhiệm vụ của bạn là: ngay từ đầu, dùng thông tin công khai để cố gắng trả lời mọi câu hỏi trong email, và dựa trên lịch làm việc của tôi, thêm nhắc nhở trạng thái ngữ cảnh ở đầu phản hồi.

# Thông tin ngữ cảnh
- Thời gian hiện tại: {{ new Date().toLocaleString('en-AU', { timeZone: 'Australia/Sydney', hour12: false }) }} (giờ Sydney, Úc)
- Thông tin email nằm trong dữ liệu đầu vào.

# Công cụ khả dụng
- Simple Vector Store2: dùng để truy vấn giờ làm việc chính xác của tôi (ví dụ: thứ Hai đến thứ Sáu, 9 giờ sáng đến 5 giờ chiều).
- SerpAPI: **[nguồn thông tin chính]** ưu tiên dùng công cụ này để tìm kiếm trên internet, nhằm trả lời câu hỏi cụ thể trong email.

# Các bước thực hiện
1.  **Phân tích vấn đề**: trước tiên, đọc kỹ nội dung email, rút ra câu hỏi cốt lõi của người gửi.

2.  **Thu thập thông tin song song**: đồng thời thực hiện hai thao tác sau để thu thập thông tin:
    a. Dùng công cụ `SerpAPI`, tìm kiếm trên mạng câu trả lời cho vấn đề của người gửi.
    b. Dùng công cụ `Simple Vector Store2`, lấy giờ làm việc chính xác tôi đã đặt.

3.  **Soạn phản hồi cốt lõi**: dựa trên thông tin `SerpAPI` thu thập được, trả lời rõ ràng, trực tiếp câu hỏi của người gửi; phần này sẽ là thân chính của email trả lời.

4.  **Thêm tiền tố trạng thái và tích hợp**:
    a. So sánh “thời gian hiện tại” với giờ làm việc tôi lấy từ công cụ.
    b. **Nếu hiện là “ngoài giờ làm việc”**: tạo một đoạn tiền tố nhắc trạng thái. Đoạn tiền tố này **bắt buộc phải chứa** giờ làm việc cụ thể lấy từ `Simple Vector Store2`.
        * **Ví dụ tiền tố**: "Xin chào, cảm ơn email của bạn. Bạn đã liên hệ với tôi ngoài giờ làm việc (giờ làm việc của tôi là: [chèn giờ làm việc truy vấn được ở đây]). Tôi sẽ đích thân xem xét email này vào ngày làm việc tiếp theo. Trong lúc đó, đây là câu trả lời sơ bộ dựa trên thông tin công khai: **<br><br>---<br><br>**"
    c. **Nếu hiện là “giờ làm việc”**: chỉ cần dùng lời chào đơn giản.
        * **Ví dụ tiền tố**: "Xin chào, về câu hỏi bạn nêu, câu trả lời như sau: **<br><br>---<br><br>**"
    d. Ghép tiền tố đã tạo với phản hồi cốt lõi bạn đã soạn (kết quả bước 3) để tạo thành nội dung email cuối cùng.

5.  **Định dạng đầu ra**: bạn bắt buộc phải xuất nội dung email cuối cùng dưới định dạng JSON nghiêm ngặt. Định dạng như sau, không thêm bất kỳ giải thích hoặc văn bản bổ sung nào:
    {
      "shouldReply": true,
      "subject": "Re: [chủ đề email gốc]",
      "body": "[đây là nội dung email trả lời hoàn chỉnh đã ghép, **mọi xuống dòng phải dùng thẻ <br> của HTML**]"
    }

# Quy tắc và giới hạn
- **Luôn ưu tiên thử trả lời**: bất kể khi nào, nhiệm vụ đầu tiên của bạn là dùng `SerpAPI` cung cấp phản hồi có giá trị cho người dùng.
- **Bắt buộc tuyên bố trạng thái**: nếu trả lời ngoài giờ làm việc, bắt buộc tuyên bố rõ ở đầu email và đính kèm giờ làm việc chính xác của tôi.
- **Nguồn thông tin phải chính xác**: giờ làm việc phải nghiêm ngặt lấy theo kết quả của `Simple Vector Store2`; câu trả lời chủ yếu đến từ `SerpAPI`, không được bịa thông tin.
- **Định dạng đầu ra**: **trong JSON đầu ra cuối cùng, mọi xuống dòng trong trường `body` đều phải dùng thẻ `<br>`, không dùng `\n`.**
```

(3) Cấu hình công cụ cho Agent

Với công cụ `Simple Vector Store`, chúng ta cần cấu hình then chốt để đảm bảo nó “đọc” đúng tri thức đã lưu trước đó:

- <strong>Operation Mode</strong>: `Retrieve Documents (As Tool for AI Agent)` (chế độ đọc làm công cụ).
- <strong>Memory Key</strong>: phải điền Key <strong>hoàn toàn giống</strong> phần một, tức `my-dailytime`.
- <strong>Embeddings</strong>: phải dùng mô hình `Embeddings Google Gemini` <strong>hoàn toàn giống</strong> phần một.

Chỉ khi `Memory Key` và mô hình `Embeddings` hoàn toàn nhất quán, Agent mới có thể dùng đúng “chìa khóa” và “ngôn ngữ” để truy cập kho tri thức, như trong Hình 5.65.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-11.png" alt="" width="90%"/>
  <p>Hình 5.65 Cấu hình công cụ Simple Vector Store</p>
</div>

Tham số Description chính là định nghĩa mô tả công cụ khi AI Agent gọi nó; ở đây cũng cung cấp prompt tương ứng:

```json
Đây là công cụ Simple Vector Store2, dùng để truy vấn thông tin cá nhân của tôi, đặc biệt là giờ làm việc và chiến lược trả lời email. Khi cần phán đoán hiện có phải giờ làm việc hay không, hoặc cần thông báo cho đối phương khi nào tôi sẽ trả lời email, bắt buộc phải dùng công cụ này.
```

Với Memory, điều duy nhất cần lưu ý là ở đây chúng ta dùng tên luồng của mỗi email làm định danh duy nhất, đảm bảo tính duy nhất của lưu trữ; Key được đặt là `{{ $('Gmail').item.json.threadId }}`

(4) Gửi phản hồi cuối cùng

Bước cuối cùng là thực thi. Kết nối đầu ra của nút `AI Agent` đến một nút `Gmail`, đặt <strong>Operation</strong> thành `Send`. Dùng biểu thức n8n để liên kết người nhận, chủ đề và nội dung với các trường tương ứng trong dữ liệu JSON đầu ra của `AI Agent`, là có thể hiện thực tự động trả lời email, như trong Hình 5.66.

- <strong>To</strong>: `{{ $('Gmail').item.json.From }}` (hoặc trường người gửi trong trigger khác)
- <strong>Subject</strong>: `Re:  {{ $('Gmail').item.json.Subject }}`
- <strong>Message</strong>: `{{ $json.output }}`

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-12.png" alt="" width="90%"/>
  <p>Hình 5.66 Sơ đồ công cụ trả lời cuối cùng</p>
</div>

Đồng thời khi gửi thành công, hộp thư cá nhân cũng nhận được thông tin email trả lời thật, như trong Hình 5.67.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-13.png" alt="" width="90%"/>
  <p>Hình 5.67 Định dạng email trả về trong hộp thư cá nhân</p>
</div>

Đến đây, một hệ thống chăm sóc khách hàng thông minh tích hợp dựa trên nút `AI Agent` đã được xây dựng xong; bạn có thể gửi một email thử để kiểm tra kết quả. Kiến trúc này có khả năng mở rộng rất mạnh. Trong tương lai, bạn có thể trực tiếp thêm nhiều công cụ hơn vào nút `AI Agent` (như lịch, cơ sở dữ liệu, CRM, v.v.); chỉ cần dạy Agent cách dùng chúng trong prompt, là có thể liên tục trao cho Agent của bạn năng lực mạnh mẽ hơn.

### 5.5.5 Phân tích ưu điểm và hạn chế của n8n

Qua thực hành xây dựng trợ lý email thông minh từ con số không ở trên, chúng ta đã có cảm nhận trực quan về chế độ làm việc của n8n. Là một nền tảng tự động hóa low-code mạnh mẽ, n8n thể hiện xuất sắc trong việc trao quyền phát triển ứng dụng Agent, nhưng nó cũng không phải vạn năng. Như trong Bảng 5.1, chúng ta sẽ phân tích khách quan ưu điểm và hạn chế tiềm ẩn của nó.

<div align="center">
  <p>Bảng 5.1 Tổng kết ưu điểm và hạn chế của nền tảng n8n</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/5-figures/n8n-14.png" alt="" width="90%"/>
</div>

Trước tiên, ưu thế rõ rệt nhất của n8n nằm ở <strong>hiệu quả phát triển</strong>. Nó trừu tượng hóa logic phức tạp thành quy trình làm việc trực quan; dù là nhận email, ra quyết định AI, gọi công cụ hay phản hồi cuối cùng, toàn bộ luồng dữ liệu và chuỗi xử lý đều rõ ràng trên canvas. Đặc tính low-code này hạ thấp rất nhiều ngưỡng kỹ thuật, cho phép nhà phát triển nhanh chóng dựng và kiểm chứng logic cốt lõi của Agent, rút ngắn rất nhiều khoảng cách từ ý tưởng đến nguyên mẫu.

Thứ hai, <strong>chức năng mạnh mẽ và tích hợp cao</strong>. n8n có thư viện nút tích hợp phong phú, có thể dễ dàng kết nối hàng trăm dịch vụ phổ biến như Gmail, Google Gemini. Quan trọng hơn, nút `AI Agent` tiên tiến của nó tích hợp cao mô hình, bộ nhớ và quản lý công cụ, cho phép chúng ta hiện thực quyết định tự chủ phức tạp chỉ với một nút, thanh lịch và mạnh mẽ hơn nhiều so với cách định tuyến thủ công nhiều nút truyền thống. Đồng thời, với tình huống chức năng tích hợp không bao phủ, nút `Code` cũng cung cấp tính linh hoạt khi viết mã tùy chỉnh, đảm bảo giới hạn trên của chức năng.

Cuối cùng, về <strong>triển khai và vận hành</strong>, n8n hỗ trợ <strong>triển khai riêng tư</strong>, và cũng là phương án Agent riêng tư tương đối đơn giản hiện nay có thể triển khai phiên bản dự án đầy đủ; điều này cực kỳ quan trọng với doanh nghiệp chú trọng bảo mật dữ liệu và quyền riêng tư. Chúng ta có thể triển khai toàn bộ dịch vụ trên máy chủ của mình, đảm bảo thông tin nhạy cảm như email nội bộ, dữ liệu khách hàng không rời khỏi môi trường riêng, tạo nền tảng vững chắc cho tính tuân thủ của ứng dụng Agent.

Tất nhiên, mỗi công cụ đều có đánh đổi. Khi tận hưởng tiện lợi n8n mang lại, chúng ta cũng phải nhận thức hạn chế của nó.

Đằng sau <strong>hiệu quả phát triển</strong> là <strong>gỡ lỗi và xử lý lỗi tương đối rườm rà</strong>. Khi quy trình làm việc trở nên phức tạp, một khi xảy ra lỗi định dạng dữ liệu, nhà phát triển có thể phải kiểm tra đầu vào/đầu ra từng nút để định vị vấn đề, đôi khi không trực tiếp bằng đặt breakpoint trong mã.

Về chức năng, hạn chế lớn nhất là <strong>tính không bền vững của lưu trữ tích hợp</strong>. `Simple Memory` và `Simple Vector Store` dùng trong ca của chúng ta đều dựa trên bộ nhớ; nghĩa là khi dịch vụ n8n khởi động lại, toàn bộ lịch sử hội thoại và kho tri thức sẽ mất. Điều này chí mạng với ứng dụng môi trường sản xuất. Vì vậy, khi triển khai thực tế, bắt buộc phải thay bằng cơ sở dữ liệu bền vững bên ngoài như Redis, Pinecone, điều này cũng làm tăng chi phí cấu hình và bảo trì.

Ngoài ra, về <strong>triển khai vận hành</strong> và cộng tác nhóm, <strong>kiểm soát phiên bản và cộng tác nhiều người của n8n chưa trưởng thành bằng mã truyền thống</strong>. Mặc dù có thể xuất quy trình làm việc thành tệp JSON để quản lý, nhưng so sánh thay đổi của nó không rõ ràng như `git diff` mã nguồn; nhiều người cùng sửa một quy trình làm việc cũng dễ xung đột.

Cuối cùng về <strong>hiệu năng</strong>, n8n hoàn toàn đáp ứng được phần lớn tự động hóa doanh nghiệp và nhiệm vụ Agent tần suất trung bình thấp. Nhưng với tình huống cần xử lý yêu cầu đồng thời cực cao, cơ chế điều phối nút của nó có thể mang lại chi phí hiệu năng nhất định, có thể kém hơn dịch vụ hiện thực thuần mã.

## 5.6 Tổng kết chương

Chương này giới thiệu một cách hệ thống quan niệm, phương pháp và thực hành xây dựng ứng dụng Agent dựa trên nền tảng low-code, đánh dấu bước chuyển quan trọng từ “viết mã thủ công” sang “phát triển theo nền tảng”.

Ở mục đầu tiên, chúng ta trình bày bối cảnh và giá trị của sự trỗi dậy nền tảng low-code. So với Agent hiện thực thuần mã ở chương 4, nền tảng low-code thông qua cách đồ họa, mô-đun hóa đã hạ thấp rõ rệt ngưỡng kỹ thuật, nâng cao hiệu quả phát triển và cung cấp trải nghiệm gỡ lỗi trực quan tốt hơn. “Mức trừu tượng cao hơn” này cho phép nhà phát triển tập trung sức lực vào logic nghiệp vụ và kỹ thuật prompt, thay vì chi tiết hiện thực tầng dưới.

Sau đó, chúng ta thực hành sâu bốn nền tảng tiêu biểu có đặc sắc riêng:

**Coze** nổi bật với trải nghiệm thân thiện không cần mã và hệ sinh thái plugin phong phú. Qua ca “Bản tin AI hằng ngày”, chúng ta trải nghiệm cách nhanh chóng tích hợp thông tin đa nguồn bằng cấu hình kéo thả, và xuất bản một cú nhấp đến nhiều nền tảng chủ lưu. Coze đặc biệt phù hợp với người dùng phi kỹ thuật và tình huống cần nhanh chóng kiểm chứng ý tưởng, nhưng hạn chế không hỗ trợ MCP và không thể xuất tệp cấu hình chuẩn hóa cũng đáng lưu ý.

**Dify**, với tư cách nền tảng mã nguồn mở cấp doanh nghiệp, thể hiện năng lực phát triển toàn ngăn xếp. Ca “trợ lý cá nhân siêu Agent” bao gồm nhiều mô-đun như hỏi đáp hằng ngày, tối ưu văn bản, sinh đa phương thức, phân tích dữ liệu và tích hợp công cụ MCP, thể hiện đầy đủ năng lực biên soạn mạnh mẽ của Dify trong tình huống nghiệp vụ phức tạp. Chợ plugin phong phú (8000+), cách triển khai linh hoạt và đặc tính bảo mật cấp doanh nghiệp khiến nó trở thành lựa chọn lý tưởng cho nhà phát triển chuyên nghiệp và nhóm doanh nghiệp. Tuy nhiên, đường cong học tập tương đối dốc và thách thức hiệu năng trong tình huống đồng thời cao cũng cần cân nhắc.

**FastGPT** nhờ trải nghiệm kho tri thức RAG cực hạn trở thành đối thủ mạnh trong tình huống hỏi đáp lĩnh vực chuyên môn. Qua ca “trợ lý cố vấn đầu tư thông minh”, chúng ta trải nghiệm mô hình phát triển hoàn chỉnh từ xây dựng kho tri thức, kết nối công cụ MCP đến biên soạn quy trình làm việc trực quan. FastGPT kiểm soát chi tiết các khâu như chia khối tệp, tăng cường chỉ mục, nhận diện hình ảnh, khiến nó có ưu thế độc đáo trong các tình huống như trợ lý tri thức doanh nghiệp, chăm sóc khách hàng thông minh. Nhưng hệ sinh thái mẫu tương đối yếu và hạn mức bản miễn phí có hạn cũng hạn chế khả năng phát huy trong tình huống nghiệp vụ phức tạp hơn.

**n8n** mở ra một con đường khác bằng năng lực “kết nối” độc đáo. Qua ca “trợ lý email thông minh”, chúng ta thấy cách nhúng năng lực AI liền mạch vào quy trình tự động hóa nghiệp vụ phức tạp. Nút AI Agent của n8n tích hợp cao mô hình, bộ nhớ và công cụ; kết hợp với hàng trăm nút đặt trước, có thể hiện thực phương án tự động hóa tùy biến cao. Đặc tính hỗ trợ triển khai riêng tư đặc biệt quan trọng với doanh nghiệp chú trọng bảo mật dữ liệu. Nhưng tính không bền vững của lưu trữ tích hợp và kiểm soát phiên bản chưa trưởng thành cần xử lý kỹ thuật bổ sung trong môi trường sản xuất.

Qua thực hành so sánh bốn nền tảng, chúng ta có thể đưa ra các gợi ý chọn sau:

- **Kiểm chứng nguyên mẫu nhanh, người dùng phi kỹ thuật**: ưu tiên Coze
- **Ứng dụng cấp doanh nghiệp, logic nghiệp vụ phức tạp, sinh đa phương thức**: ưu tiên Dify
- **Hệ thống hỏi đáp dựa trên kho tri thức riêng, chăm sóc khách hàng thông minh**: ưu tiên FastGPT
- **Tích hợp nghiệp vụ sâu, quy trình tự động hóa tổng quát**: ưu tiên n8n

Cần nhấn mạnh rằng nền tảng low-code không phải để thay thế phát triển mã nguồn, mà cung cấp một lựa chọn bổ trợ. Trong dự án thực tế, chúng ta hoàn toàn có thể chuyển đổi linh hoạt theo nhu cầu từng giai đoạn: dùng nền tảng low-code kiểm chứng ý tưởng nhanh, dùng mã nguồn hiện thực kiểm soát chi tiết; dùng nền tảng xử lý quy trình chuẩn hóa, dùng mã nguồn xử lý logic đặc biệt. Tư duy “phát triển hỗn hợp” này mới là thực tiễn tốt nhất của kỹ thuật hóa Agent.

Chương tiếp theo, chúng ta sẽ tìm hiểu sâu hơn các framework Agent ở tầng thấp hơn, giúp người đọc xây dựng ứng dụng đáng tin cậy và thú vị hơn.

## Bài tập

1. Chương này giới thiệu bốn nền tảng low-code có đặc sắc riêng: `Coze`, `Dify`, `FastGPT` và `n8n`. Hãy phân tích:

   - Bốn nền tảng này khác nhau thế nào về định vị cốt lõi và triết lý thiết kế? Chúng lần lượt giải quyết những điểm đau nào trong phát triển Agent?
   - Nền tảng low-code và phát triển thuần mã đều có ưu, nhược điểm; ngoài ra còn có chế độ “phát triển hỗn hợp” dùng nền tảng cho một số chức năng và mã nguồn cho số khác. Hãy suy nghĩ ba chế độ phát triển phù hợp với những tình huống nào? Nêu ví dụ.
2. Trong ca `Coze` ở mục 5.2, chúng ta xây dựng Agent “Bản tin AI hằng ngày”. Hãy mở rộng suy nghĩ dựa trên ca này:

   > <strong>Gợi ý</strong>: đây là bài thực hành tay, khuyến nghị thao tác thực tế
   >

   - Việc sinh bản tin hiện tại được kích hoạt thụ động (người dùng chủ động hỏi). Cải tạo Agent này thế nào để nó có thể tự động sinh bản tin lúc 8 giờ mỗi sáng và đẩy đến nhóm Feishu hoặc WeChat Official Account được chỉ định?
   - Chất lượng bản tin phụ thuộc rất lớn vào thiết kế prompt. Hãy thử tối ưu prompt ở mục 5.2.2 để bản tin sinh ra chuyên nghiệp hơn, cấu trúc rõ ràng hơn, hoặc thêm chức năng mới như “phân tích điểm nóng”, “dự đoán xu hướng”.
   - Việc `Coze` hiện không hỗ trợ giao thức `MCP` được coi là hạn chế quan trọng (trong quá trình viết bài tập, `feature-mcp` tuy đã có trong [`Coze Studio Q4 2025 Product Roadmap`](https://github.com/coze-dev/coze-studio/issues/2218) nhưng chưa được hiện thực). Hãy trình bày ngắn gọn giao thức `MCP` là gì? Vì sao nó quan trọng? Nếu `Coze` hỗ trợ `MCP` trong tương lai sẽ mang lại những khả năng mới nào?
3. Trong ca `Dify` ở mục 5.3, chúng ta xây dựng một “trợ lý cá nhân siêu Agent” đầy đủ chức năng. Hãy phân tích sâu:

   - Ca này dùng “bộ phân loại vấn đề” để định tuyến thông minh, phân phối các loại yêu cầu khác nhau đến các Agent con khác nhau. Kiến trúc đa Agent này có ưu điểm gì? Nếu không dùng bộ phân loại mà để một Agent duy nhất xử lý mọi nhiệm vụ, sẽ gặp vấn đề gì?
   - Mô-đun truy vấn dữ liệu cần cung cấp cho mô hình lớn thông tin cấu trúc bảng rõ ràng. Nếu cơ sở dữ liệu có 50 bảng, mỗi bảng 20 trường, đưa trực tiếp tất cả câu lệnh `DDL` vào prompt sẽ khiến ngữ cảnh quá dài. Hãy thiết kế một phương án thông minh hơn để giải quyết vấn đề này.
   - `Dify` hỗ trợ hai chế độ triển khai cục bộ và đám mây. Hãy so sánh hai chế độ này về bảo mật dữ liệu, chi phí, hiệu năng, độ khó bảo trì, và giải thích tình huống áp dụng của từng chế độ.
4. Trong ca `n8n` ở mục 5.5, chúng ta xây dựng “trợ lý email thông minh”. Hãy suy nghĩ các vấn đề sau:

   > <strong>Gợi ý</strong>: đây là bài thực hành tay, khuyến nghị thao tác thực tế
   >

   - `Simple Vector Store` và `Simple Memory` dùng trong ca đều dựa trên bộ nhớ; dữ liệu sẽ mất sau khi dịch vụ khởi động lại. Hãy tra tài liệu `n8n`, thử thay bằng phương án lưu trữ bền vững (như `Pinecone`, `Redis`, v.v.), và giải thích quá trình cấu hình.
   - Trợ lý email hiện tại chỉ xử lý email văn bản. Nếu email người dùng gửi có tệp đính kèm (như tài liệu `PDF`, hình ảnh), bạn sẽ mở rộng quy trình làm việc này thế nào để Agent hiểu nội dung tệp đính kèm và phản hồi tương ứng?
   - Ưu thế cốt lõi của `n8n` nằm ở năng lực “kết nối”. Hãy thiết kế một tình huống tự động hóa phức tạp hơn: khi khách hàng đặt hàng trên nền tảng thương mại điện tử, tự động kích hoạt một loạt thao tác (gửi email xác nhận, cập nhật cơ sở dữ liệu tồn kho, thông báo hệ thống logistics, ghi thông tin khách hàng vào `CRM`). Hãy vẽ sơ đồ kết nối nút của quy trình làm việc và giải thích cấu hình then chốt.
5. Kỹ thuật prompt cũng quan trọng không kém trên nền tảng low-code. Chương này trình bày các ca thiết kế prompt của nhiều nền tảng. Hãy phân tích:

   - So sánh thiết kế prompt ở mục 5.2.2 (`Coze`), 5.3.2 (`Dify`) và 5.5.4 (`n8n`); chúng khác nhau thế nào về cấu trúc, phong cách và trọng tâm? Những khác biệt này có liên quan đến đặc tính nền tảng không?
   - Trong “mô-đun tối ưu văn bản” của `Dify`, prompt yêu cầu đầu ra “hơn 500 từ”. Yêu cầu cứng về độ dài đầu ra này có hợp lý không? Khi nào nên giới hạn độ dài đầu ra, khi nào nên để mô hình tự do phát huy?
6. Công cụ và plugin là cách mở rộng năng lực cốt lõi của nền tảng low-code. Hãy suy nghĩ:

   - `Coze` có cửa hàng plugin phong phú, `Dify` có chợ plugin 8000+, `FastGPT` hỗ trợ native giao thức MCP, `n8n` có hàng trăm nút đặt trước. Nếu cả ba nền tảng đều không có công cụ cụ thể bạn cần (như “`API` kết nối hệ thống nội bộ công ty”), bạn sẽ giải quyết thế nào?
   - Trong mục 5.3.2, chúng ta dùng giao thức `MCP` để tích hợp các dịch vụ như bản đồ Amap, gợi ý ăn uống. Hãy nghiên cứu và giải thích: giao thức `MCP` khác gì so với `RESTful API` truyền thống và `Tool Calling`? Vì sao nói `MCP` là “chuẩn mới” cho gọi công cụ của Agent?
   - Giả sử bạn cần phát triển một plugin tùy chỉnh cho `Dify`, để nó có thể gọi hệ thống kho tri thức nội bộ công ty bạn. Hãy tra tài liệu phát triển plugin `Dify`, tóm tắt quy trình phát triển và điểm kỹ thuật then chốt.
7. Chọn nền tảng là một trong những quyết định then chốt cho thành công của sản phẩm Agent. Giả sử bạn là người phụ trách kỹ thuật của một công ty khởi nghiệp; công ty dự định phát triển ba ứng dụng AI sau; hãy chọn nền tảng phù hợp nhất cho mỗi ứng dụng (`Coze`, `Dify`, `FastGPT`, `n8n` hoặc phát triển thuần mã), và giải thích chi tiết lý do:

   <strong>Ứng dụng A</strong>: tiểu chương trình “trợ lý viết AI” hướng người dùng C-end, cần nhanh chóng ra mắt để kiểm chứng nhu cầu thị trường, ngân sách hạn chế, nhóm chỉ có 1 kỹ sư frontend và 1 quản lý sản phẩm.

   <strong>Ứng dụng B</strong>: “hệ thống kiểm duyệt hợp đồng thông minh” hướng khách hàng doanh nghiệp, cần xử lý tài liệu pháp lý nhạy cảm, yêu cầu dữ liệu không rời môi trường riêng của khách hàng, cần tích hợp sâu với hệ thống OA và hệ thống quản lý tài liệu hiện có của khách hàng.

   <strong>Ứng dụng C</strong>: “công cụ nâng cao hiệu suất R&D” dùng nội bộ, cần tự động hóa nhiều khâu quy trình R&D như kiểm duyệt mã, sinh báo cáo kiểm thử, theo dõi Bug, đồng bộ tiến độ dự án; nhóm có năng lực kỹ thuật mạnh.

   Với mỗi ứng dụng, hãy phân tích từ các chiều sau (bao gồm nhưng không giới hạn):

   > <strong>Gợi ý</strong>: năng lực nền tảng có đáp ứng nhu cầu không, bao lâu có thể ra mắt, chi phí phát triển, chi phí vận hành, độ khó lặp sau này, không gian mở rộng chức năng tương lai
   >

   - Tính khả thi kỹ thuật
   - Hiệu quả phát triển
   - Kiểm soát chi phí
   - Khả năng bảo trì
   - Khả năng mở rộng
   - Bảo mật dữ liệu và tuân thủ

## Tài liệu tham khảo

[1] Coze - Nền tảng phát triển ứng dụng AI thế hệ mới. https://www.coze.cn/

[2] Dify - Nền tảng phát triển ứng dụng LLM mã nguồn mở. https://dify.ai/

[3] FastGPT - Nền tảng hỏi đáp kho tri thức và công cụ xây dựng Agent mã nguồn mở. https://fastgpt.io/en/

[4] n8n - Công cụ tự động hóa quy trình làm việc. https://n8n.io/

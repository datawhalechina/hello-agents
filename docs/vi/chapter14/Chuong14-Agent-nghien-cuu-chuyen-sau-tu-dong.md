# Chương 14: Agent nghiên cứu chuyên sâu tự động

Trong dự án trợ lý du lịch ở Chương 13, chúng ta đã trải nghiệm cách áp dụng HelloAgents vào một sản phẩm đa agent. Chương này tiếp tục tiến xa hơn, tập trung vào “ứng dụng chuyên sâu về tri thức”: <strong>xây dựng một trợ lý agent có khả năng tự động thực thi các nhiệm vụ nghiên cứu chuyên sâu.</strong>

So với lập kế hoạch du lịch, khó khăn của nghiên cứu chuyên sâu nằm ở chỗ thông tin không ngừng phân tán, dữ kiện nhanh chóng thay đổi và người dùng đòi hỏi cao về nguồn trích dẫn. Để tạo ra một báo cáo nghiên cứu đáng tin cậy, chúng ta cần trang bị cho agent ba năng lực cốt lõi:

<strong>(1) Phân tích vấn đề</strong>: chia nhỏ chủ đề mở của người dùng thành các câu truy vấn có thể tìm kiếm.

<strong>(2) Thu thập thông tin nhiều vòng</strong>: kết hợp nhiều API tìm kiếm khác nhau để liên tục khai thác tư liệu, loại bỏ trùng lặp và hợp nhất.

<strong>(3) Suy ngẫm và tổng kết</strong>: dựa trên kết quả từng giai đoạn để nhận diện lỗ hổng tri thức, quyết định có tiếp tục tìm kiếm hay không, và tạo bản tổng kết có cấu trúc.

## 14.1 Tổng quan dự án và thiết kế kiến trúc

### 14.1.1 Vì sao cần trợ lý nghiên cứu chuyên sâu

Trong thời đại bùng nổ thông tin, mỗi ngày chúng ta đều cần nhanh chóng hiểu các công nghệ, khái niệm hoặc sự kiện mới. Phương pháp nghiên cứu truyền thống có vài điểm bất cập. Thứ nhất là <strong>quá tải thông tin</strong>. Công cụ tìm kiếm trả về hàng nghìn đến hàng chục nghìn kết quả, bạn phải lần lượt mở từng liên kết, đọc lượng lớn nội dung mới tìm được thông tin hữu ích. Thứ hai là <strong>thiếu cấu trúc</strong>. Ngay cả khi tìm được thông tin liên quan, thông tin thường bị phân mảnh, thiếu tổ chức có hệ thống. Cuối cùng là <strong>lao động lặp lại</strong>. Mỗi lần nghiên cứu một chủ đề mới, đều phải lặp lại quá trình "tìm kiếm → đọc → tóm tắt → sắp xếp".

Đây chính là vấn đề mà trợ lý nghiên cứu chuyên sâu cần giải quyết. Nó không chỉ là một công cụ tìm kiếm, mà là một trợ lý nghiên cứu có khả năng tự chủ lập kế hoạch, thực thi và tổng kết.

<strong>Giá trị cốt lõi của trợ lý nghiên cứu chuyên sâu:</strong>

1. <strong>Tiết kiệm thời gian</strong>: nén công việc nghiên cứu 1-2 giờ xuống còn 5-10 phút
2. <strong>Nâng cao chất lượng</strong>: quy trình nghiên cứu có hệ thống, tránh bỏ sót thông tin quan trọng
3. <strong>Có thể truy vết</strong>: ghi lại toàn bộ kết quả tìm kiếm và nguồn, thuận tiện kiểm chứng và trích dẫn
4. <strong>Có thể mở rộng</strong>: dễ dàng thêm công cụ tìm kiếm, nguồn dữ liệu và công cụ phân tích mới

### 14.1.2 Tổng quan kiến trúc kỹ thuật

Hệ thống lần này vẫn sử dụng <strong>kiến trúc tách biệt frontend/backend</strong> kinh điển, như thể hiện trong Hình 14.1.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-1.png" alt="" width="85%"/>
  <p>Hình 14.1 Kiến trúc kỹ thuật của trợ lý nghiên cứu chuyên sâu</p>
</div>

Hệ thống được chia thành kiến trúc bốn tầng:

<strong>Tầng frontend (Vue3+TypeScript)</strong>: UI hộp thoại modal toàn màn hình, trực quan hóa kết quả Markdown

<strong>Tầng backend (FastAPI)</strong>: định tuyến API (`/research/stream`)

<strong>Tầng agent (HelloAgents)</strong>: ba Agent chuyên trách (TODO Planner, Task Summarizer, Report Writer) + hai công cụ cốt lõi (SearchTool, NoteTool)

<strong>Tầng dịch vụ bên ngoài</strong>: công cụ tìm kiếm + nhà cung cấp LLM

Hãy xem một yêu cầu nghiên cứu hoàn chỉnh được luân chuyển trong hệ thống như thế nào, như thể hiện trong Hình 14.2:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-2.png" alt="" width="85%"/>
  <p>Hình 14.2 Quá trình luân chuyển dữ liệu của trợ lý nghiên cứu chuyên sâu</p>
</div>

1. <strong>Người dùng nhập</strong>: người dùng nhập chủ đề nghiên cứu ở frontend
2. <strong>Frontend gửi</strong>: frontend kết nối tới `/research/stream` qua SSE
3. <strong>Backend tiếp nhận</strong>: FastAPI nhận yêu cầu, tạo trạng thái nghiên cứu
4. <strong>Giai đoạn lập kế hoạch</strong>: gọi Agent lập kế hoạch nghiên cứu, phân rã thành 3 nhiệm vụ con
5. <strong>Giai đoạn thực thi</strong>: thực thi từng nhiệm vụ con
   - Dùng SearchTool để tìm kiếm
   - Gọi Agent tóm tắt nhiệm vụ để tóm tắt
   - Dùng NoteTool để ghi lại kết quả
6. <strong>Giai đoạn báo cáo</strong>: gọi Agent tạo báo cáo, hợp nhất tất cả các bản tóm tắt
7. <strong>Trả về dạng stream</strong>: đẩy tiến độ và kết quả tới frontend qua SSE
8. <strong>Frontend hiển thị</strong>: frontend cập nhật trạng thái nhiệm vụ, thanh tiến độ, log, báo cáo theo thời gian thực

Cấu trúc thư mục của dự án như sau:

```
helloagents-deepresearch/
├── backend/                    # Mã nguồn backend
│   ├── src/
│   │   ├── agent.py           # Bộ điều phối cốt lõi
│   │   ├── main.py            # Điểm vào FastAPI
│   │   ├── models.py          # Mô hình dữ liệu
│   │   ├── prompts.py         # Mẫu prompt
│   │   ├── config.py          # Quản lý cấu hình
│   │   └── services/          # Tầng dịch vụ
│   │       ├── planner.py     # Dịch vụ lập kế hoạch
│   │       ├── summarizer.py  # Dịch vụ tóm tắt
│   │       ├── reporter.py    # Dịch vụ báo cáo
│   │       └── search.py      # Dịch vụ tìm kiếm
│   ├── .env                   # Biến môi trường
│   ├── pyproject.toml         # Quản lý phụ thuộc
│   └── workspace/             # Ghi chú nghiên cứu
│
└── frontend/                   # Mã nguồn frontend
    ├── src/
    │   ├── App.vue            # Thành phần chính
    │   ├── components/        # Thành phần UI
    │   │   └── ResearchModal.vue
    │   └── composables/       # Hàm composable
    │       └── useResearch.ts
    ├── package.json           # Phụ thuộc npm
    └── vite.config.ts         # Cấu hình build
```

### 14.1.3 Trải nghiệm nhanh: chạy dự án trong 5 phút

Trước khi đi sâu vào chi tiết triển khai, hãy chạy dự án trước để xem hiệu quả cuối cùng. Như vậy bạn sẽ có nhận thức trực quan về toàn bộ hệ thống.

Bạn có thể kiểm tra phiên bản bằng các lệnh sau:

```bash
python --version  # nên hiển thị Python 3.10.x trở lên
node --version    # nên hiển thị v16.x.x trở lên
npm --version     # nên hiển thị 8.x.x trở lên
```

(1) Khởi động backend

```bash
# 1. Vào thư mục backend
cd helloagents-deepresearch/backend

# 2. Cài đặt phụ thuộc
# Cách 1: dùng uv (khuyến nghị, trình quản lý gói Python nhanh hơn)
uv sync

# Cách 2: dùng pip
pip install -e .

# 3. Cấu hình biến môi trường
cp .env.example .env

# 4. Sửa tệp .env, điền API key của bạn
# Mở tệp .env bằng trình soạn thảo bạn thích
# Tối thiểu cần cấu hình:
# - LLM_PROVIDER (như openai, deepseek, qwen)
# - LLM_API_KEY (API key LLM của bạn)
# - SEARCH_API (như duckduckgo, tavily)

# 5. Khởi động backend
python src/main.py
```

Nếu mọi thứ bình thường, bạn sẽ thấy đầu ra tương tự:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

(2) Khởi động frontend

Mở một cửa sổ terminal mới:

```bash
# 1. Vào thư mục frontend
cd helloagents-deepresearch/frontend

# 2. Cài đặt phụ thuộc
npm install

# 3. Khởi động frontend
npm run dev
```

Nếu mọi thứ bình thường, bạn sẽ thấy đầu ra tương tự:

```
  VITE v5.0.0  ready in 500 ms

  ➜  Local:   http://localhost:5174/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

(3) Bắt đầu nghiên cứu

Mở trình duyệt truy cập `http://localhost:5174`, bạn sẽ thấy một thẻ nhập liệu ở giữa, như thể hiện trong Hình 14.3. Nhập chủ đề nghiên cứu, ví dụ `Datawhale là một tổ chức như thế nào?`, chọn công cụ tìm kiếm (nếu đã cấu hình nhiều công cụ), nhấn nút "Bắt đầu nghiên cứu".

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-3.png" alt="" width="85%"/>
  <p>Hình 14.3 Trang tìm kiếm của trợ lý nghiên cứu chuyên sâu</p>
</div>

Như thể hiện trong Hình 14.4, hệ thống sẽ tự động mở rộng toàn màn hình, bên trái hiển thị thông tin nghiên cứu, bên phải hiển thị tiến độ và kết quả nghiên cứu theo thời gian thực. Toàn bộ quá trình nghiên cứu mất khoảng 1-3 phút, tùy thuộc độ phức tạp của chủ đề và tốc độ phản hồi của công cụ tìm kiếm.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-4.png" alt="" width="85%"/>
  <p>Hình 14.4 Trợ lý nghiên cứu chuyên sâu mở rộng nghiên cứu</p>
</div>

Sau khi nghiên cứu hoàn tất, bạn sẽ thấy:

- <strong>Danh sách nhiệm vụ</strong>: hiển thị tất cả nhiệm vụ con và trạng thái của chúng
- <strong>Log tiến độ</strong>: hiển thị mọi thao tác trong quá trình nghiên cứu
- <strong>Báo cáo cuối cùng</strong>: báo cáo Markdown có cấu trúc, bao gồm tóm tắt của tất cả nhiệm vụ con và trích dẫn nguồn

Bây giờ bạn đã chạy thành công trợ lý nghiên cứu chuyên sâu và có nhận thức trực quan về hệ thống.

## 14.2 Mô hình nghiên cứu hướng TODO

### 14.2.1 Nghiên cứu hướng TODO là gì

Công cụ tìm kiếm truyền thống chỉ có thể trả lời một câu hỏi đơn lẻ, trong khi nghiên cứu chuyên sâu cần trả lời một chuỗi câu hỏi liên quan. Mô hình nghiên cứu hướng TODO phân rã chủ đề nghiên cứu phức tạp thành nhiều nhiệm vụ con (TODO), thực thi lần lượt và hợp nhất kết quả.

Tư tưởng cốt lõi của mô hình này là: <strong>chuyển nhiệm vụ phức tạp "nghiên cứu" thành quy trình "lập kế hoạch → thực thi → hợp nhất"</strong>.

Hãy hiểu sự chuyển đổi này qua một ví dụ. Giả sử bạn muốn nghiên cứu "Datawhale là một tổ chức như thế nào?", cách tìm kiếm truyền thống là:

```
Người dùng nhập: Datawhale là một tổ chức như thế nào?
Công cụ tìm kiếm: trả về 10-20 liên kết
Người dùng: lần lượt mở liên kết, đọc nội dung, ghi chú
Kết quả: thông tin phân mảnh, thiếu tính hệ thống
```

Vấn đề của cách này là mỗi liên kết chỉ bao quát một khía cạnh của chủ đề, thiếu cấu trúc hệ thống, cần sắp xếp và tóm tắt thủ công.

<strong>Cách hướng TODO: nghiên cứu có hệ thống</strong>

```
Người dùng nhập: Datawhale là một tổ chức như thế nào?

Hệ thống lập kế hoạch:
  ├─ TODO 1: Thông tin cơ bản của Datawhale (định vị tổ chức)
  ├─ TODO 2: Các dự án chính của Datawhale (nội dung cốt lõi)
  ├─ TODO 3: Văn hóa cộng đồng của Datawhale (giá trị)
  └─ TODO 4: Ảnh hưởng của Datawhale (đóng góp xã hội)

Hệ thống thực thi:
  Với mỗi TODO:
    1. Tìm kiếm tư liệu liên quan
    2. Tóm tắt thông tin then chốt
    3. Ghi lại trích dẫn nguồn

Hệ thống hợp nhất:
  Tạo báo cáo có cấu trúc:
    ├─ Phần một: Định vị tổ chức (từ TODO 1)
    ├─ Phần hai: Nội dung cốt lõi (từ TODO 2)
    ├─ Phần ba: Giá trị (từ TODO 3)
    ├─ Phần bốn: Đóng góp xã hội (từ TODO 4)
    └─ Tài liệu tham khảo: tất cả trích dẫn nguồn
```

Ưu điểm của cách này là phân rã chủ đề phức tạp thành các câu hỏi con rõ ràng, kết quả tìm kiếm và bản tóm tắt của mỗi nhiệm vụ con đều được ghi lại, thuận tiện truy vết. Đồng thời, quy trình nghiên cứu có hệ thống tránh bỏ sót thông tin quan trọng, có thể dễ dàng thêm nhiệm vụ con mới hoặc điều chỉnh thứ tự thực thi.

Một hệ thống nghiên cứu hướng TODO hoàn chỉnh bao gồm ba yếu tố cốt lõi:

<strong>(1) Bộ lập kế hoạch thông minh (TODO Planner)</strong>: chịu trách nhiệm phân rã chủ đề nghiên cứu thành nhiệm vụ con. Một bộ lập kế hoạch tốt cần hiểu các khía cạnh then chốt và mục tiêu nghiên cứu của chủ đề, phân rã chủ đề thành 3-5 nhiệm vụ con (quá ít thì bao quát không đủ, quá nhiều thì dư thừa), và thiết kế truy vấn tìm kiếm phù hợp cho mỗi nhiệm vụ con.

<strong>(2) Bộ thực thi nhiệm vụ (Task Executor)</strong>: chịu trách nhiệm thực thi từng nhiệm vụ con. Bộ thực thi cần dùng công cụ tìm kiếm để lấy tư liệu liên quan, trích xuất thông tin then chốt và loại bỏ nội dung dư thừa, đồng thời lưu tất cả trích dẫn nguồn để thuận tiện kiểm chứng.

<strong>(3) Bộ tạo báo cáo (Report Writer)</strong>: chịu trách nhiệm hợp nhất kết quả của tất cả nhiệm vụ con. Bộ tạo báo cáo cần tổ chức nội dung theo thứ tự logic, hợp nhất thông tin trùng lặp, và thêm trích dẫn nguồn cho mỗi luận điểm.

Trong trường hợp của chúng ta, quy trình nghiên cứu hướng TODO như thể hiện trong Hình 14.5:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-5.png" alt="" width="85%"/>
  <p>Hình 14.5 Quy trình nghiên cứu hướng TODO</p>
</div>


Toàn bộ quy trình là tuyến tính, nhưng mỗi giai đoạn đều có đầu vào và đầu ra rõ ràng. Thiết kế này giúp hệ thống dễ hiểu và dễ gỡ lỗi.

### 14.2.2 Quy trình nghiên cứu ba giai đoạn

Quy trình nghiên cứu hướng TODO được chia thành ba giai đoạn: lập kế hoạch (Planning), thực thi (Execution), báo cáo (Reporting). Mỗi giai đoạn có một Agent chuyên trách.

<strong>(1) Giai đoạn 1: Lập kế hoạch</strong>

Mục tiêu của giai đoạn lập kế hoạch là phân rã chủ đề nghiên cứu thành 3-5 nhiệm vụ con. Hệ thống nhận chủ đề nghiên cứu và ngày hiện tại làm đầu vào, xuất ra danh sách nhiệm vụ con ở định dạng JSON. Mỗi nhiệm vụ con gồm ba trường: title (tiêu đề nhiệm vụ), intent (ý định nghiên cứu) và query (truy vấn tìm kiếm).

Agent lập kế hoạch nghiên cứu sẽ áp dụng các chiến lược phân rã khác nhau tùy theo đặc điểm chủ đề, thường bắt đầu từ khái niệm cơ bản, sau đó tìm hiểu hiện trạng kỹ thuật, ứng dụng thực tế và xu hướng phát triển, khi cần thiết còn tiến hành phân tích so sánh. Ví dụ, với "Datawhale là một tổ chức như thế nào?", Agent lập kế hoạch có thể tạo các nhiệm vụ con sau:

```json
[
  {
    "title": "Thông tin cơ bản của Datawhale",
    "intent": "Tìm hiểu định vị tổ chức, thời điểm thành lập, quá trình phát triển của Datawhale",
    "query": "Datawhale organization introduction history 2024"
  },
  {
    "title": "Các dự án chính của Datawhale",
    "intent": "Tìm hiểu các dự án mã nguồn mở và hướng dẫn cốt lõi của Datawhale",
    "query": "Datawhale projects tutorials open source 2024"
  },
......
]
```

Một kế hoạch tốt nên bao quát toàn diện, logic rõ ràng, truy vấn chính xác, số lượng mục vừa phải.

<strong>(2) Giai đoạn 2: Thực thi</strong>

Giai đoạn thực thi lần lượt thực hiện từng nhiệm vụ con, tìm kiếm và tóm tắt tư liệu liên quan. Hệ thống nhận danh sách nhiệm vụ con và cấu hình công cụ tìm kiếm làm đầu vào, xuất ra bản tóm tắt của mỗi nhiệm vụ con (định dạng Markdown) và danh sách trích dẫn nguồn. Quy trình thực thi như sau:

Với mỗi nhiệm vụ con, bộ thực thi sẽ:

1. <strong>Tìm kiếm tư liệu</strong>: dùng công cụ tìm kiếm đã cấu hình để thực hiện tìm kiếm

   ```python
   search_results = search_tool.run({
       "input": task.query,
       "backend": "tavily",
       "mode": "structured",
       "max_results": 5
   })
   ```

2. <strong>Lấy kết quả tìm kiếm</strong>: trích xuất tiêu đề, URL, tóm tắt

   ```json
   {
     "results": [
       {
         "title": "What is a Multimodal Model?",
         "url": "https://example.com/multimodal-model",
         "snippet": "A multimodal model is an AI model that can process multiple types of data..."
       },
       ...
     ]
   }
   ```

3. <strong>Gọi Agent tóm tắt</strong>: tóm tắt kết quả tìm kiếm

   ```python
   summary = summarizer_agent.run(
       task=task,
       search_results=search_results
   )
   ```

4. <strong>Ghi lại bản tóm tắt và nguồn</strong>: lưu vào NoteTool

   ```python
   note_tool.run({
       "action": "create",
       "title": task.title,
       "content": f"## {task.title}\n\n{summary}\n\n## Nguồn\n{sources}",
       "tags": ["research", "summary"]
   })
   ```

Agent tóm tắt nhiệm vụ sẽ trích xuất luận điểm cốt lõi từ mỗi kết quả tìm kiếm, hợp nhất thông tin tương tự, giữ lại các dữ liệu then chốt như số liệu, ngày tháng, tên riêng, và thêm trích dẫn nguồn cho mỗi luận điểm. Ví dụ, với kết quả tìm kiếm của "Thông tin cơ bản của Datawhale", Agent tóm tắt có thể tạo ra:

```markdown
## Thông tin cơ bản của Datawhale

Datawhale là một tổ chức mã nguồn mở tập trung vào lĩnh vực khoa học dữ liệu và AI, được thành lập năm 2018[1]. Sứ mệnh cốt lõi của tổ chức là "for the learner, cùng học hỏi và phát triển với người học", hướng tới xây dựng một cộng đồng học tập thuần túy[2].

**Định vị cốt lõi:**

1. **Nền tảng giáo dục mã nguồn mở**: cung cấp tài nguyên học tập AI và khoa học dữ liệu chất lượng cao[1]
2. **Cộng đồng người học**: quy tụ hàng chục nghìn người học và người thực hành AI[3]
3. **Chia sẻ tri thức**: đề cao tinh thần mã nguồn mở, mọi nội dung hoàn toàn miễn phí và mở[2]

**Quá trình phát triển:**

- **Năm 2018**: Datawhale được thành lập, phát hành hướng dẫn mã nguồn mở đầu tiên[1]
- **Năm 2020**: trở thành một trong những cộng đồng học tập AI hàng đầu trong nước[3]
- **Năm 2024**: tích lũy phát hành hơn 50 dự án mã nguồn mở, ảnh hưởng tới hơn 100.000 người học[4]

## Nguồn

[1] https://github.com/datawhalechina
[2] https://datawhale.club/about
[3] https://www.zhihu.com/org/datawhale
[4] https://datawhale.cn
```

Trong quá trình thực thi, hệ thống đẩy thông tin tiến độ tới frontend theo thời gian thực:

```json
{
  "type": "status",
  "message": "Đang tìm kiếm: Thông tin cơ bản của Datawhale"
}
```

```json
{
  "type": "status",
  "message": "Đang tóm tắt kết quả tìm kiếm..."
}
```

```json
{
  "type": "task",
  "task": {
    "id": 1,
    "title": "Thông tin cơ bản của Datawhale",
    "status": "completed"
  }
}
```

<strong>(3) Giai đoạn 3: Báo cáo</strong>

Mục tiêu của giai đoạn báo cáo là hợp nhất bản tóm tắt của tất cả nhiệm vụ con, tạo báo cáo cuối cùng. Hệ thống nhận bản tóm tắt của tất cả nhiệm vụ con và chủ đề nghiên cứu làm đầu vào, xuất ra báo cáo cuối cùng ở định dạng Markdown. Báo cáo gồm năm phần: tiêu đề, tổng quan, phân tích chi tiết từng nhiệm vụ con, tổng kết và tài liệu tham khảo. Ví dụ, với "Datawhale là một tổ chức như thế nào?", báo cáo cuối cùng có thể là:

```markdown
# Datawhale là một tổ chức như thế nào?

## Tổng quan

Báo cáo này nghiên cứu một cách hệ thống tổ chức mã nguồn mở Datawhale, bao gồm bốn khía cạnh: thông tin cơ bản, các dự án chính, văn hóa cộng đồng và ảnh hưởng.

## 1. Thông tin cơ bản của Datawhale

Datawhale là một tổ chức mã nguồn mở tập trung vào lĩnh vực khoa học dữ liệu và AI, được thành lập năm 2018...

(chèn bản tóm tắt nhiệm vụ 1 tại đây)

## 2. Các dự án chính của Datawhale

Datawhale đã phát hành nhiều hướng dẫn mã nguồn mở chất lượng cao, bao gồm Hello-Agents, Joyful-Pandas...

(chèn bản tóm tắt nhiệm vụ 2 tại đây)
......
## Tổng kết

Qua nghiên cứu này, chúng ta đã hiểu định vị tổ chức, các dự án cốt lõi, văn hóa cộng đồng và đóng góp xã hội của Datawhale. Datawhale là một cộng đồng học tập thuần túy, đã có đóng góp quan trọng cho giáo dục AI.

## Tài liệu tham khảo

[1] https://github.com/datawhalechina
[2] https://datawhale.club/about
...
```

Agent tạo báo cáo sẽ tổ chức nội dung theo thứ tự logic của nhiệm vụ con, thêm tổng quan ngắn ở đầu, hợp nhất thông tin trùng lặp, thống nhất định dạng Markdown, và sắp xếp tất cả trích dẫn nguồn vào phần tài liệu tham khảo.

## 14.3 Thiết kế hệ thống agent

### 14.3.1 Phân chia trách nhiệm giữa các Agent

Trong trợ lý nghiên cứu chuyên sâu, chúng ta thiết kế ba Agent chuyên trách, mỗi Agent đảm nhận một nhiệm vụ cụ thể. Điều này khiến mỗi Agent đều đơn giản, dễ hiểu và dễ bảo trì.

Trong Chương 7, chúng ta đã học cách dùng `SimpleAgent` để xây dựng agent. Triết lý thiết kế của `SimpleAgent` là đơn giản trực tiếp: mỗi lần gọi phương thức `run()`, Agent sẽ phân tích câu hỏi của người dùng, quyết định có cần gọi công cụ hay không, rồi trả về kết quả. Thiết kế này rất hiệu quả với nhiệm vụ đơn giản, nhưng khi đối mặt với nhiệm vụ phức tạp như nghiên cứu chuyên sâu, chúng ta cần tiếp tục áp dụng phương án cộng tác đa agent.

Như thể hiện trong Bảng 14.1, ba Agent lần lượt chịu trách nhiệm lập kế hoạch, tóm tắt và tạo báo cáo.

<div align="center">
  <p>Bảng 14.1 Phân chia trách nhiệm của ba Agent</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-table-1.png" alt="" width="85%"/>
</div>

Hãy giới thiệu chi tiết thiết kế của từng Agent.

<strong>Agent 1: Chuyên gia lập kế hoạch nghiên cứu (TODO Planner)</strong>

<strong>Trách nhiệm</strong>: phân rã chủ đề nghiên cứu thành 3-5 nhiệm vụ con

<strong>Triết lý thiết kế</strong>: nhiệm vụ cốt lõi của chuyên gia lập kế hoạch nghiên cứu là hiểu chủ đề nghiên cứu của người dùng, phân tích các khía cạnh then chốt của chủ đề, rồi tạo một chuỗi nhiệm vụ con. Quá trình này tương tự giai đoạn "động não" của nhà nghiên cứu con người trước khi bắt đầu nghiên cứu.

<strong>Thiết kế Prompt</strong>:

```python
todo_planner_instructions = """
Bạn là một chuyên gia lập kế hoạch nghiên cứu. Nhiệm vụ của bạn là phân rã chủ đề nghiên cứu của người dùng thành 3-5 nhiệm vụ con.

Ngày hiện tại: {current_date}

Chủ đề nghiên cứu: {research_topic}

Hãy phân tích chủ đề nghiên cứu này và phân rã thành 3-5 nhiệm vụ con. Mỗi nhiệm vụ con nên:
1. Bao quát một khía cạnh quan trọng của chủ đề
2. Có mục tiêu nghiên cứu rõ ràng
3. Có thể tìm được tư liệu liên quan qua công cụ tìm kiếm

Hãy trả về danh sách nhiệm vụ con ở định dạng JSON, mỗi nhiệm vụ con gồm:
- title: tiêu đề nhiệm vụ (ngắn gọn, rõ ràng)
- intent: ý định nhiệm vụ (vì sao cần nghiên cứu điều này)
- query: truy vấn tìm kiếm (chuỗi truy vấn dùng cho công cụ tìm kiếm, có thể dùng tiếng Anh để có kết quả tốt hơn)

Ví dụ đầu ra:
[
  {{
    "title": "Mô hình đa phương thức là gì",
    "intent": "Tìm hiểu khái niệm cơ bản về mô hình đa phương thức, đặt nền tảng cho nghiên cứu tiếp theo",
    "query": "multimodal model definition concept 2024"
  }},
  ...
]

Hãy đảm bảo:
1. Số lượng nhiệm vụ con nằm trong khoảng 3-5
2. Các nhiệm vụ con có quan hệ logic (như từ cơ bản đến ứng dụng, từ hiện trạng đến xu hướng)
3. Truy vấn tìm kiếm có thể tìm chính xác tư liệu liên quan
4. Chỉ trả về JSON, không kèm văn bản khác
"""
```

<strong>Điểm thiết kế then chốt</strong>: prompt bao gồm ngày hiện tại để lấy thông tin mới nhất, yêu cầu rõ ràng đầu ra định dạng JSON để dễ phân tích, dùng ví dụ giúp Agent hiểu đầu ra mong đợi, và nhấn mạnh các ràng buộc như số lượng nhiệm vụ con, quan hệ logic.

<strong>Mã triển khai</strong>:

ToolAwareSimpleAgent ở đây được mở rộng từ SimpleAgent, có thể tìm hiểu ở mục 14.3.2, không cần đi sâu ở đây.

```python
class PlanningService:
    def __init__(self, llm: HelloAgentsLLM):
        self._agent = ToolAwareSimpleAgent(
            name="TODO Planner",
            system_prompt="Bạn là một chuyên gia lập kế hoạch nghiên cứu",
            llm=llm,
            tool_call_listener=self._on_tool_call
        )

    def plan_todo_list(self, state: SummaryState) -> List[TodoItem]:
        prompt = todo_planner_instructions.format(
            current_date=get_current_date(),
            research_topic=state.research_topic,
        )

        response = self._agent.run(prompt)
        tasks_payload = self._extract_tasks(response)

        todo_items = []
        for idx, item in enumerate(tasks_payload, start=1):
            task = TodoItem(
                id=idx,
                title=item["title"],
                intent=item["intent"],
                query=item["query"],
            )
            todo_items.append(task)

        return todo_items

    def _extract_tasks(self, response: str) -> List[dict]:
        """Trích xuất JSON từ phản hồi của Agent"""
        # Dùng biểu thức chính quy để trích xuất phần JSON
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            raise ValueError("Không thể trích xuất JSON từ phản hồi")
```

<strong>Agent 2: Chuyên gia tóm tắt nhiệm vụ (Task Summarizer)</strong>

<strong>Trách nhiệm</strong>: tóm tắt kết quả tìm kiếm, trích xuất thông tin then chốt

<strong>Triết lý thiết kế</strong>: nhiệm vụ cốt lõi của chuyên gia tóm tắt nhiệm vụ là đọc kết quả tìm kiếm, trích xuất thông tin then chốt và trình bày theo cách có cấu trúc. Quá trình này tương tự việc nhà nghiên cứu con người ghi chú sau khi đọc tài liệu.

<strong>Thiết kế Prompt</strong>:

```python
task_summarizer_instructions = """
Bạn là một chuyên gia tóm tắt nhiệm vụ. Nhiệm vụ của bạn là tóm tắt kết quả tìm kiếm và trích xuất thông tin then chốt.

Tiêu đề nhiệm vụ: {task_title}
Ý định nhiệm vụ: {task_intent}
Truy vấn tìm kiếm: {task_query}

Kết quả tìm kiếm:
{search_results}

Hãy đọc kỹ các kết quả tìm kiếm trên, trích xuất thông tin then chốt và trả về bản tóm tắt ở định dạng Markdown.

Bản tóm tắt nên bao gồm:
1. **Luận điểm cốt lõi**: các luận điểm và kết luận cốt lõi trong kết quả tìm kiếm
2. **Dữ liệu then chốt**: các số liệu, ngày tháng, tên riêng quan trọng
3. **Trích dẫn nguồn**: thêm trích dẫn nguồn cho mỗi luận điểm (dùng ký hiệu [1], [2]...)

Hãy đảm bảo:
1. Bản tóm tắt ngắn gọn, rõ ràng, tránh dư thừa
2. Giữ lại các chi tiết và dữ liệu quan trọng
3. Thêm trích dẫn nguồn cho mỗi luận điểm
4. Dùng định dạng Markdown (tiêu đề, danh sách, in đậm...)

Ví dụ đầu ra:
## Luận điểm cốt lõi

Mô hình đa phương thức là một mô hình AI có khả năng xử lý nhiều loại dữ liệu[1]. Khác với mô hình đơn phương thức truyền thống, mô hình đa phương thức có thể đồng thời hiểu văn bản, hình ảnh, âm thanh...[2].

**Đặc điểm then chốt:**
- Hiểu xuyên phương thức[1]
- Biểu diễn thống nhất[3]
- Huấn luyện đầu-cuối[2]

## Nguồn

[1] https://example.com/source1
[2] https://example.com/source2
[3] https://example.com/source3
"""
```

<strong>Điểm thiết kế then chốt</strong>: prompt bao gồm ngữ cảnh như tiêu đề, ý định, truy vấn của nhiệm vụ để giúp Agent hiểu nhiệm vụ, yêu cầu rõ ràng đầu ra gồm luận điểm cốt lõi, dữ liệu then chốt, trích dẫn nguồn, nhấn mạnh việc thêm trích dẫn nguồn cho mỗi luận điểm, và dùng ví dụ giúp Agent hiểu định dạng đầu ra mong đợi.

<strong>Mã triển khai</strong>:

```python
class SummarizationService:
    def __init__(self, llm: HelloAgentsLLM):
        self._agent = ToolAwareSimpleAgent(
            name="Task Summarizer",
            system_prompt="Bạn là một chuyên gia tóm tắt nhiệm vụ",
            llm=llm,
            tool_call_listener=self._on_tool_call
        )

    def summarize_task(
        self,
        task: TodoItem,
        search_results: List[dict]
    ) -> str:
        # Định dạng kết quả tìm kiếm
        formatted_sources = self._format_sources(search_results)

        prompt = task_summarizer_instructions.format(
            task_title=task.title,
            task_intent=task.intent,
            task_query=task.query,
            search_results=formatted_sources,
        )

        summary = self._agent.run(prompt)
        return summary

    def _format_sources(self, search_results: List[dict]) -> str:
        """Định dạng kết quả tìm kiếm"""
        formatted = []
        for idx, result in enumerate(search_results, start=1):
            formatted.append(
                f"[{idx}] {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Tóm tắt: {result['snippet']}\n"
            )
        return "\n".join(formatted)
```

<strong>Agent 3: Chuyên gia viết báo cáo (Report Writer)</strong>

<strong>Trách nhiệm</strong>: hợp nhất bản tóm tắt của tất cả nhiệm vụ con, tạo báo cáo cuối cùng

<strong>Triết lý thiết kế</strong>: nhiệm vụ cốt lõi của chuyên gia viết báo cáo là hợp nhất bản tóm tắt của tất cả nhiệm vụ con thành một báo cáo có cấu trúc. Quá trình này tương tự việc nhà nghiên cứu con người viết báo cáo nghiên cứu sau khi hoàn thành mọi khảo sát.

<strong>Thiết kế Prompt</strong>:

```python
report_writer_instructions = """
Bạn là một chuyên gia viết báo cáo. Nhiệm vụ của bạn là hợp nhất bản tóm tắt của tất cả nhiệm vụ con để tạo một báo cáo nghiên cứu có cấu trúc.

Chủ đề nghiên cứu: {research_topic}

Bản tóm tắt các nhiệm vụ con:
{task_summaries}

Hãy hợp nhất bản tóm tắt của tất cả nhiệm vụ con trên để tạo một báo cáo nghiên cứu có cấu trúc.

Báo cáo nên bao gồm:
1. **Tiêu đề**: chủ đề nghiên cứu
2. **Tổng quan**: giới thiệu ngắn về chủ đề nghiên cứu và cấu trúc báo cáo (2-3 đoạn)
3. **Phân tích chi tiết từng nhiệm vụ con**: tổ chức theo thứ tự logic (dùng tiêu đề cấp hai)
4. **Tổng kết**: tổng kết các phát hiện chính của nghiên cứu (1-2 đoạn)
5. **Tài liệu tham khảo**: tất cả trích dẫn nguồn (nhóm theo nhiệm vụ con)

Hãy đảm bảo:
1. Cấu trúc báo cáo rõ ràng, logic mạch lạc
2. Loại bỏ thông tin trùng lặp
3. Giữ lại tất cả trích dẫn nguồn
4. Dùng định dạng Markdown

Ví dụ đầu ra:
# Những tiến bộ mới nhất của mô hình lớn đa phương thức

## Tổng quan

Báo cáo này nghiên cứu một cách hệ thống những tiến bộ mới nhất của mô hình lớn đa phương thức...

## 1. Mô hình đa phương thức là gì

(chèn bản tóm tắt nhiệm vụ 1 tại đây)

## 2. Các mô hình đa phương thức mới nhất gồm những gì

(chèn bản tóm tắt nhiệm vụ 2 tại đây)

...

## Tổng kết

Qua nghiên cứu này, chúng ta đã hiểu...

## Tài liệu tham khảo

### Nhiệm vụ 1: Mô hình đa phương thức là gì
[1] https://example.com/source1
...
"""
```

<strong>Điểm thiết kế then chốt</strong>: prompt yêu cầu rõ ràng báo cáo gồm các cấu trúc như tiêu đề, tổng quan, phân tích chi tiết, tổng kết, tài liệu tham khảo, nhấn mạnh tổ chức nội dung theo thứ tự logic, yêu cầu hợp nhất thông tin trùng lặp để loại bỏ dư thừa, và giữ lại tất cả trích dẫn nguồn.

<strong>Mã triển khai</strong>:

```python
class ReportingService:
    def __init__(self, llm: HelloAgentsLLM):
        self._agent = ToolAwareSimpleAgent(
            name="Report Writer",
            system_prompt="Bạn là một chuyên gia viết báo cáo",
            llm=llm,
            tool_call_listener=self._on_tool_call
        )

    def generate_report(
        self,
        research_topic: str,
        task_summaries: List[Tuple[TodoItem, str]]
    ) -> str:
        # Định dạng bản tóm tắt nhiệm vụ con
        formatted_summaries = self._format_summaries(task_summaries)

        prompt = report_writer_instructions.format(
            research_topic=research_topic,
            task_summaries=formatted_summaries,
        )

        report = self._agent.run(prompt)
        return report

    def _format_summaries(
        self,
        task_summaries: List[Tuple[TodoItem, str]]
    ) -> str:
        """Định dạng bản tóm tắt nhiệm vụ con"""
        formatted = []
        for idx, (task, summary) in enumerate(task_summaries, start=1):
            formatted.append(
                f"## Nhiệm vụ {idx}: {task.title}\n"
                f"Ý định: {task.intent}\n\n"
                f"{summary}\n"
            )
        return "\n".join(formatted)
```

### 14.3.2 Thiết kế ToolAwareSimpleAgent

Trong Chương 7, chúng ta đã triển khai `SimpleAgent`, agent nền tảng của framework HelloAgents. Nhưng trong trợ lý nghiên cứu chuyên sâu, chúng ta cần một Agent có khả năng <strong>ghi lại các lần gọi công cụ</strong>. Đó là nguồn gốc của `ToolAwareSimpleAgent`.

Trong trợ lý nghiên cứu chuyên sâu, chúng ta cần ghi lại tình hình gọi công cụ của mỗi Agent, phục vụ:

1. <strong>Gỡ lỗi</strong>: xem Agent đã gọi những công cụ nào, truyền tham số gì
2. <strong>Ghi log</strong>: ghi lại mọi thao tác trong quá trình nghiên cứu
3. <strong>Phân tích</strong>: phân tích mô hình hành vi của Agent
4. <strong>Hiển thị tiến độ</strong>: hiển thị theo thời gian thực Agent đang làm gì

Bản thân `SimpleAgent` không hỗ trợ lắng nghe lời gọi công cụ, nên chúng ta cần mở rộng nó.

`ToolAwareSimpleAgent` thêm một tham số `tool_call_listener` trên cơ sở `SimpleAgent`; đây là một hàm callback, được gọi mỗi khi có lời gọi công cụ.

<strong>Ví dụ sử dụng:</strong>

```python
from hello_agents import ToolAwareSimpleAgent

def tool_listener(call_info):
    print(f"Agent: {call_info['agent_name']}")
    print(f"Công cụ: {call_info['tool_name']}")
    print(f"Tham số: {call_info['parsed_parameters']}")
    print(f"Kết quả: {call_info['result']}")

agent = ToolAwareSimpleAgent(
    name="Trợ lý nghiên cứu",
    system_prompt="Bạn là một trợ lý nghiên cứu",
    llm=llm,
    tool_call_listener=tool_listener
)
```

`ToolAwareSimpleAgent` kế thừa từ `SimpleAgent`, ghi đè phương thức `_execute_tool_call`:

```python
class ToolAwareSimpleAgent(SimpleAgent):
    def __init__(
        self,
        name: str,
        system_prompt: str,
        llm: HelloAgentsLLM,
        tool_registry: Optional[ToolRegistry] = None,
        tool_call_listener: Optional[Callable] = None,
    ):
        super().__init__(
            name=name,
            system_prompt=system_prompt,
            llm=llm,
            tool_registry=tool_registry,
        )
        self._tool_call_listener = tool_call_listener

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """Thực thi lời gọi công cụ và thông báo cho listener"""
        # Phân tích tham số
        parsed_parameters = self._parse_parameters(parameters)

        # Gọi công cụ
        result = super()._execute_tool_call(tool_name, parameters)

        # Thông báo cho listener
        if self._tool_call_listener:
            self._tool_call_listener({
                "agent_name": self.name,
                "tool_name": tool_name,
                "parsed_parameters": parsed_parameters,
                "result": result,
            })

        return result
```

Trong trợ lý nghiên cứu chuyên sâu, chúng ta dùng `ToolAwareSimpleAgent` để ghi lại lời gọi công cụ của tất cả Agent:

```python
class DeepResearchAgent:
    def __init__(self, config: Configuration):
        self.config = config
        self.llm = HelloAgentsLLM(...)

        # Tạo listener cho lời gọi công cụ
        def tool_listener(call_info):
            self._emit_event({
                "type": "tool_call",
                "agent": call_info["agent_name"],
                "tool": call_info["tool_name"],
                "parameters": call_info["parsed_parameters"],
            })

        # Tạo ba Agent, đều dùng cùng một listener
        self.planner = PlanningService(self.llm, tool_listener)
        self.summarizer = SummarizationService(self.llm, tool_listener)
        self.reporter = ReportingService(self.llm, tool_listener)
```

Như vậy, mọi lời gọi công cụ của tất cả Agent đều được ghi lại, đẩy tới frontend qua SSE và hiển thị cho người dùng theo thời gian thực.

### 14.3.3 Mô hình cộng tác giữa các Agent

Ba Agent có quan hệ <strong>cộng tác tuần tự</strong>, như thể hiện trong Hình 14.6.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-6.png" alt="" width="85%"/>
  <p>Hình 14.6 Quy trình cộng tác giữa các Agent</p>
</div>

Đặc điểm của mô hình cộng tác tuần tự là:

1. <strong>Quy trình tuyến tính</strong>: các Agent thực thi theo thứ tự cố định
2. <strong>Đầu vào/đầu ra rõ ràng</strong>: đầu vào của mỗi Agent đến từ đầu ra của Agent trước
3. <strong>Không đồng thời</strong>: tại cùng một thời điểm chỉ có một Agent làm việc

`DeepResearchAgent` là bộ điều phối cốt lõi của toàn bộ hệ thống, chịu trách nhiệm điều phối ba Agent:

```python
class DeepResearchAgent:
    def run(self, research_topic: str) -> str:
        # 1. Giai đoạn lập kế hoạch
        self._emit_event({"type": "status", "message": "Đang lập kế hoạch nhiệm vụ nghiên cứu..."})
        todo_list = self.planner.plan_todo_list(research_topic)
        self._emit_event({"type": "tasks", "tasks": todo_list})

        # 2. Giai đoạn thực thi
        task_summaries = []
        for task in todo_list:
            self._emit_event({
                "type": "status",
                "message": f"Đang nghiên cứu: {task.title}"
            })

            # Tìm kiếm
            search_results = self.search_service.search(task.query)

            # Tóm tắt
            summary = self.summarizer.summarize_task(task, search_results)
            task_summaries.append((task, summary))

            self._emit_event({
                "type": "task_completed",
                "task_id": task.id
            })

        # 3. Giai đoạn báo cáo
        self._emit_event({"type": "status", "message": "Đang tạo báo cáo..."})
        report = self.reporter.generate_report(research_topic, task_summaries)
        self._emit_event({"type": "report", "content": report})

        return report
```

## 14.4 Tích hợp hệ thống công cụ

### 14.4.1 Mở rộng SearchTool

Trong Chương 7, chúng ta đã triển khai phiên bản cơ bản của `SearchTool`, tích hợp hai công cụ tìm kiếm Tavily và SerpApi, thể hiện tư tưởng thiết kế tìm kiếm đa nguồn. Trong trợ lý nghiên cứu chuyên sâu của chương này, chúng ta mở rộng thêm năng lực của `SearchTool`, bổ sung các công cụ tìm kiếm DuckDuckGo, Perplexity, SearXNG..., và triển khai chế độ Advanced (kết hợp nhiều công cụ tìm kiếm). Tìm kiếm là chức năng cốt lõi nhất của trợ lý nghiên cứu chuyên sâu; những mở rộng này giúp hệ thống thích ứng với các tình huống sử dụng và nhu cầu khác nhau.

Như thể hiện trong Bảng 14.2, các công cụ tìm kiếm được bổ sung lần này có đặc điểm và tình huống áp dụng khác nhau.

<div align="center">
  <p>Bảng 14.2 So sánh các công cụ tìm kiếm</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-table-2.png" alt="" width="85%"/>
</div>

Chúng ta không thảo luận riêng về cách mở rộng nữa, có thể tham khảo mã nguồn và ví dụ mở rộng ở Chương 7. `SearchTool` cung cấp giao diện tìm kiếm thống nhất; dù dùng công cụ tìm kiếm nào, cách gọi đều giống nhau.

Trong trợ lý nghiên cứu chuyên sâu, chúng ta chọn công cụ tìm kiếm qua tệp cấu hình:

```python
# config.py
class SearchAPI(str, Enum):
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"
    PERPLEXITY = "perplexity"
    SEARXNG = "searxng"
    ADVANCED = "advanced"

class Configuration(BaseModel):
    search_api: SearchAPI = SearchAPI.DUCKDUCKGO
    # ...
```

```python
# .env
SEARCH_API=tavily
```

Như vậy, người dùng có thể chọn công cụ tìm kiếm bằng cách sửa tệp `.env` mà không cần sửa mã.

Kết quả `SearchTool` trả về là một từ điển, bao gồm:

- `results`: danh sách kết quả tìm kiếm, mỗi kết quả gồm tiêu đề, URL, tóm tắt
- `backend`: công cụ tìm kiếm được dùng
- `answer`: câu trả lời do AI tạo (chỉ Perplexity)
- `notices`: thông tin thông báo (như giới hạn API, lỗi...)

Dưới đây là cách xử lý một số trường hợp đặc biệt.

Kết quả tìm kiếm có thể chứa URL trùng lặp, chúng ta cần loại bỏ trùng:

```python
def deduplicate_sources(sources: List[dict]) -> List[dict]:
    """Loại bỏ URL trùng lặp"""
    seen_urls = set()
    unique_sources = []

    for source in sources:
        if source["url"] not in seen_urls:
            seen_urls.add(source["url"])
            unique_sources.append(source)

    return unique_sources
```

Kết quả tìm kiếm có thể chứa lượng lớn văn bản, chúng ta cần giới hạn số Token của mỗi nguồn:

```python
def limit_source_tokens(source: dict, max_tokens: int = 2000) -> dict:
    """Giới hạn số Token của nguồn"""
    snippet = source["snippet"]

    # Ước lượng Token đơn giản: 1 Token xấp xỉ 4 ký tự
    max_chars = max_tokens * 4

    if len(snippet) > max_chars:
        snippet = snippet[:max_chars] + "..."

    return {
        **source,
        "snippet": snippet
    }
```

### 14.4.2 Sử dụng NoteTool

Trong trợ lý nghiên cứu chuyên sâu, chúng ta dùng `NoteTool` để lưu bền tiến độ nghiên cứu. `NoteTool` là công cụ tích hợp được giới thiệu ở Chương 9, dùng để tạo, đọc, cập nhật và xóa ghi chú.

Trong quá trình nghiên cứu, chúng ta cần ghi lại kết quả tìm kiếm, bản tóm tắt của mỗi nhiệm vụ con và báo cáo nghiên cứu cuối cùng. Những thông tin này cần được lưu bền xuống đĩa, để khi quá trình nghiên cứu bị gián đoạn có thể tiếp tục từ tiến độ lần trước, đồng thời thuận tiện xem lại mọi thao tác trong quá trình nghiên cứu, phân tích chất lượng và hiệu quả nghiên cứu.

`NoteTool` lưu ghi chú trong thư mục workspace được chỉ định, mỗi ghi chú là một tệp Markdown. Tên tệp ghi chú là ID nhiệm vụ, nội dung gồm tiêu đề nhiệm vụ, ý định nhiệm vụ, truy vấn tìm kiếm, kết quả tìm kiếm và bản tóm tắt.

Phong cách tệp được tạo cuối cùng sẽ như sơ đồ cây dưới đây:

```
workspace/
├── notes/
│   ├── 1.md  # Ghi chú nhiệm vụ 1
│   ├── 2.md  # Ghi chú nhiệm vụ 2
│   ├── 3.md  # Ghi chú nhiệm vụ 3
│   └── ...
└── reports/
    └── final_report.md  # Báo cáo cuối cùng
```

Trong trợ lý nghiên cứu chuyên sâu, chúng ta dùng `NoteTool` để ghi lại tiến độ nghiên cứu của mỗi nhiệm vụ con:

```python
class NotesService:
    def __init__(self, workspace: str):
        self.note_tool = NoteTool(workspace=workspace)

    def save_task_summary(
        self,
        task: TodoItem,
        search_results: List[dict],
        summary: str
    ):
        """Lưu bản tóm tắt nhiệm vụ"""
        # Định dạng nội dung ghi chú
        content = self._format_note_content(
            task=task,
            search_results=search_results,
            summary=summary
        )

        # Tạo ghi chú
        self.note_tool.run({
            "action": "create",
            "title": f"Nhiệm vụ {task.id}: {task.title}",
            "content": content,
            "tags": ["research", "summary"]
        })

    def _format_note_content(
        self,
        task: TodoItem,
        search_results: List[dict],
        summary: str
    ) -> str:
        """Định dạng nội dung ghi chú"""
        content = f"# Nhiệm vụ {task.id}: {task.title}\n\n"
        content += f"## Thông tin nhiệm vụ\n\n"
        content += f"- **Ý định**: {task.intent}\n"
        content += f"- **Truy vấn**: {task.query}\n\n"

        content += f"## Kết quả tìm kiếm\n\n"
        for idx, result in enumerate(search_results, start=1):
            content += f"[{idx}] {result['title']}\n"
            content += f"URL: {result['url']}\n"
            content += f"Tóm tắt: {result['snippet']}\n\n"

        content += f"## Tổng kết\n\n{summary}\n"

        return content
```

### 14.4.3 Quản lý công cụ với ToolRegistry

`ToolRegistry` là sổ đăng ký công cụ của framework HelloAgents, cũng được hỗ trợ từ Chương 7, dùng để quản lý việc đăng ký và gọi tất cả công cụ. Trong trợ lý nghiên cứu chuyên sâu, chúng ta dùng `ToolRegistry` để quản lý `SearchTool` và `NoteTool`.

Trước khi tạo Agent, chúng ta cần đăng ký công cụ:

```python
from hello_agents import ToolAwareSimpleAgent
from hello_agents.tools import ToolRegistry
from hello_agents.tools import SearchTool
from hello_agents.tools import NoteTool

# Tạo công cụ
search_tool = SearchTool(backend="hybrid")
note_tool = NoteTool(workspace="./workspace/notes")

# Tạo sổ đăng ký
registry = ToolRegistry()

# Đăng ký công cụ
registry.register_tool(search_tool)
registry.register_tool(note_tool)

# Tạo Agent
agent = ToolAwareSimpleAgent(
    name="Trợ lý nghiên cứu",
    system_prompt="Bạn là một trợ lý nghiên cứu",
    llm=llm,
    tool_registry=registry
)
```

Khi Agent cần gọi công cụ, nó sẽ tạo chỉ thị gọi công cụ, như thể hiện trong Hình 14.7.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-7.png" alt="" width="85%"/>
  <p>Hình 14.7 Quy trình gọi công cụ</p>
</div>

<strong>Quy trình gọi công cụ</strong>:

1. <strong>Agent tạo chỉ thị</strong>: Agent tạo chỉ thị gọi công cụ, như `[TOOL_CALL:search_tool:{"input": "tổ chức Datawhale", "backend": "tavily"}]`
2. <strong>Phân tích chỉ thị</strong>: `ToolRegistry` phân tích chỉ thị, trích xuất tên công cụ và tham số
3. <strong>Tìm công cụ</strong>: `ToolRegistry` tìm công cụ tương ứng theo tên công cụ
4. <strong>Gọi công cụ</strong>: gọi phương thức `run` của công cụ, truyền tham số
5. <strong>Trả về kết quả</strong>: công cụ trả về kết quả thực thi
6. <strong>Định dạng kết quả</strong>: định dạng kết quả thành chuỗi, trả về cho Agent

## 14.5 Triển khai tầng dịch vụ

Phần này sẽ giới thiệu chi tiết việc triển khai các dịch vụ cốt lõi, bao gồm PlanningService, SummarizationService, ReportingService và SearchService. Những dịch vụ này là cầu nối giữa Agent và công cụ, chịu trách nhiệm logic nghiệp vụ cụ thể.

### 14.5.1 Dịch vụ lập kế hoạch nhiệm vụ

`PlanningService` chịu trách nhiệm gọi Agent lập kế hoạch nghiên cứu, phân rã chủ đề nghiên cứu thành nhiệm vụ con. Đây là bước đầu tiên và cũng là bước then chốt nhất của toàn bộ quy trình nghiên cứu.

<strong>(1) Triển khai phương án</strong>

Trách nhiệm cốt lõi của nó là:

1. <strong>Xây dựng Prompt lập kế hoạch</strong>: xây dựng Prompt dựa trên chủ đề nghiên cứu và ngày hiện tại
2. <strong>Gọi Agent lập kế hoạch</strong>: gọi TODO Planner Agent để tạo danh sách nhiệm vụ con
3. <strong>Phân tích phản hồi JSON</strong>: trích xuất danh sách nhiệm vụ con định dạng JSON từ phản hồi của Agent
4. <strong>Xác thực định dạng nhiệm vụ con</strong>: đảm bảo mỗi nhiệm vụ con chứa các trường bắt buộc (title, intent, query)

```python
import re
import json
from typing import List, Callable, Optional
from datetime import datetime

from hello_agents import HelloAgentsLLM
from hello_agents import ToolAwareSimpleAgent
from models import TodoItem, SummaryState
from prompts import todo_planner_instructions

class PlanningService:
    """Dịch vụ lập kế hoạch nhiệm vụ"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_call_listener: Optional[Callable] = None
    ):
        self._llm = llm
        self._tool_call_listener = tool_call_listener

        # Tạo Agent lập kế hoạch
        self._agent = ToolAwareSimpleAgent(
            name="TODO Planner",
            system_prompt="Bạn là một chuyên gia lập kế hoạch nghiên cứu, giỏi phân rã chủ đề nghiên cứu phức tạp thành các nhiệm vụ con rõ ràng.",
            llm=llm,
            tool_call_listener=tool_call_listener
        )

    def plan_todo_list(self, state: SummaryState) -> List[TodoItem]:
        """Lập kế hoạch danh sách TODO

        Args:
            state: trạng thái nghiên cứu, bao gồm chủ đề nghiên cứu

        Returns:
            Danh sách nhiệm vụ con
        """
        # Xây dựng Prompt
        prompt = todo_planner_instructions.format(
            current_date=self._get_current_date(),
            research_topic=state.research_topic,
        )

        # Gọi Agent
        response = self._agent.run(prompt)

        # Phân tích JSON
        tasks_payload = self._extract_tasks(response)

        # Xác thực và tạo TodoItem
        todo_items = []
        for idx, item in enumerate(tasks_payload, start=1):
            # Xác thực trường bắt buộc
            if not all(key in item for key in ["title", "intent", "query"]):
                raise ValueError(f"Nhiệm vụ {idx} thiếu trường bắt buộc")

            task = TodoItem(
                id=idx,
                title=item["title"],
                intent=item["intent"],
                query=item["query"],
            )
            todo_items.append(task)

        return todo_items

    def _get_current_date(self) -> str:
        """Lấy ngày hiện tại"""
        return datetime.now().strftime("%d/%m/%Y")

    def _extract_tasks(self, response: str) -> List[dict]:
        """Trích xuất JSON từ phản hồi của Agent

        Phản hồi của Agent có thể chứa văn bản thừa, như:
        "Được, tôi sẽ lập kế hoạch các nhiệm vụ sau cho bạn:\n[{...}, {...}]\nCác nhiệm vụ này bao quát..."

        Chúng ta cần trích xuất phần JSON trong đó.
        """
        # Cách 1: dùng biểu thức chính quy để trích xuất mảng JSON
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Phân tích JSON thất bại: {e}")

        # Cách 2: nếu không tìm thấy mảng JSON, thử phân tích trực tiếp toàn bộ phản hồi
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError("Không thể trích xuất JSON từ phản hồi")
```

<strong>(2) Phân tích và xác thực JSON</strong>

JSON do Agent trả về có thể chứa văn bản thừa hoặc lỗi định dạng, chúng ta cần logic phân tích robust:

<strong>Vấn đề thường gặp</strong>:

1. <strong>Chứa văn bản thừa</strong>: Agent có thể thêm văn bản giải thích trước/sau JSON
2. <strong>Lỗi định dạng</strong>: JSON có thể thiếu dấu ngoặc kép, dấu phẩy...
3. <strong>Thiếu trường</strong>: một số nhiệm vụ con có thể thiếu trường bắt buộc

<strong>Giải pháp</strong>:

1. <strong>Dùng biểu thức chính quy</strong>: trích xuất phần JSON
2. <strong>Nhiều chiến lược phân tích</strong>: thử trích xuất mảng JSON trước, rồi thử phân tích trực tiếp
3. <strong>Xác thực trường</strong>: đảm bảo mỗi nhiệm vụ con chứa trường bắt buộc

<strong>Ví dụ</strong>:

```python
# Ví dụ phản hồi Agent 1: chứa văn bản thừa
response1 = """
Được, tôi sẽ lập kế hoạch các nhiệm vụ sau cho bạn:

[
  {
    "title": "Mô hình đa phương thức là gì",
    "intent": "Tìm hiểu khái niệm cơ bản",
    "query": "multimodal model definition"
  },
  {
    "title": "Các mô hình đa phương thức mới nhất",
    "intent": "Tìm hiểu hiện trạng kỹ thuật",
    "query": "latest multimodal models 2024"
  }
]

Các nhiệm vụ này bao quát thông tin cơ bản và các dự án cốt lõi của tổ chức Datawhale.
"""

# Trích xuất JSON
tasks1 = service._extract_tasks(response1)
# Kết quả: [{"title": "Thông tin cơ bản của Datawhale", ...}, ...]

# Ví dụ phản hồi Agent 2: JSON thuần
response2 = """
[
  {"title": "Thông tin cơ bản của Datawhale", "intent": "Tìm hiểu định vị tổ chức", "query": "Datawhale organization introduction"},
  {"title": "Các dự án chính của Datawhale", "intent": "Tìm hiểu nội dung cốt lõi", "query": "Datawhale projects tutorials 2024"}
]
"""

# Trích xuất JSON
tasks2 = service._extract_tasks(response2)
# Kết quả: [{"title": "Mô hình đa phương thức là gì", ...}, ...]
```

<strong>(3) Đánh giá chất lượng lập kế hoạch</strong>

Một kế hoạch tốt nên đáp ứng các tiêu chuẩn sau:

1. <strong>Bao quát toàn diện</strong>: bao quát mọi khía cạnh quan trọng của chủ đề
2. <strong>Logic rõ ràng</strong>: các nhiệm vụ con có quan hệ logic rõ ràng
3. <strong>Truy vấn chính xác</strong>: truy vấn tìm kiếm có thể tìm chính xác tư liệu liên quan
4. <strong>Số lượng vừa phải</strong>: 3-5 nhiệm vụ con

Chúng ta có thể thêm một phương thức đánh giá:

```python
def evaluate_plan(self, todo_items: List[TodoItem]) -> dict:
    """Đánh giá chất lượng lập kế hoạch

    Returns:
        Kết quả đánh giá, gồm điểm số và gợi ý
    """
    score = 100
    suggestions = []

    # Kiểm tra số lượng
    if len(todo_items) < 3:
        score -= 20
        suggestions.append("Số lượng nhiệm vụ con quá ít, có thể bỏ sót thông tin quan trọng")
    elif len(todo_items) > 5:
        score -= 10
        suggestions.append("Số lượng nhiệm vụ con quá nhiều, có thể dư thừa")

    # Kiểm tra chất lượng truy vấn
    for task in todo_items:
        if len(task.query.split()) < 2:
            score -= 10
            suggestions.append(f"Truy vấn của nhiệm vụ “{task.title}” quá đơn giản")

    # Kiểm tra quan hệ logic
    # (có thể thêm kiểm tra logic phức tạp hơn ở đây)

    return {
        "score": score,
        "suggestions": suggestions
    }
```

### 14.5.2 Dịch vụ tóm tắt

`SummarizationService` chịu trách nhiệm gọi Agent tóm tắt nhiệm vụ, tóm tắt kết quả tìm kiếm. Đây là khâu cốt lõi của quy trình nghiên cứu, quyết định chất lượng nghiên cứu.

Nhiệm vụ của nó là:

1. <strong>Định dạng kết quả tìm kiếm</strong>: định dạng kết quả tìm kiếm thành văn bản dễ đọc
2. <strong>Xây dựng Prompt tóm tắt</strong>: xây dựng Prompt dựa trên thông tin nhiệm vụ và kết quả tìm kiếm
3. <strong>Gọi Agent tóm tắt</strong>: gọi Task Summarizer Agent để tạo bản tóm tắt
4. <strong>Trích xuất trích dẫn nguồn</strong>: trích xuất trích dẫn nguồn từ bản tóm tắt

Mã cốt lõi:

```python
from typing import List, Callable, Optional, Tuple

from hello_agents import HelloAgentsLLM
from hello_agents import ToolAwareSimpleAgent
from models import TodoItem
from prompts import task_summarizer_instructions

class SummarizationService:
    """Dịch vụ tóm tắt"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_call_listener: Optional[Callable] = None
    ):
        self._llm = llm
        self._tool_call_listener = tool_call_listener

        # Tạo Agent tóm tắt
        self._agent = ToolAwareSimpleAgent(
            name="Task Summarizer",
            system_prompt="Bạn là một chuyên gia tóm tắt nhiệm vụ, giỏi trích xuất thông tin then chốt từ kết quả tìm kiếm.",
            llm=llm,
            tool_call_listener=tool_call_listener
        )

    def summarize_task(
        self,
        task: TodoItem,
        search_results: List[dict]
    ) -> Tuple[str, List[str]]:
        """Tóm tắt nhiệm vụ

        Args:
            task: thông tin nhiệm vụ
            search_results: danh sách kết quả tìm kiếm

        Returns:
            (văn bản tóm tắt, danh sách URL nguồn)
        """
        # Định dạng kết quả tìm kiếm
        formatted_sources = self._format_sources(search_results)

        # Xây dựng Prompt
        prompt = task_summarizer_instructions.format(
            task_title=task.title,
            task_intent=task.intent,
            task_query=task.query,
            search_results=formatted_sources,
        )

        # Gọi Agent
        summary = self._agent.run(prompt)

        # Trích xuất URL nguồn
        source_urls = [result["url"] for result in search_results]

        return summary, source_urls

    def _format_sources(self, search_results: List[dict]) -> str:
        """Định dạng kết quả tìm kiếm

        Định dạng kết quả tìm kiếm thành văn bản dễ đọc, bao gồm:
        - Số thứ tự
        - Tiêu đề
        - URL
        - Đoạn trích
        """
        formatted = []
        for idx, result in enumerate(search_results, start=1):
            formatted.append(
                f"[{idx}] {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Snippet: {result['snippet']}\n"
            )
        return "\n".join(formatted)
```

### Thiết kế cấu trúc báo cáo

Báo cáo cuối cùng nên bao gồm các phần sau,.......

## Tài liệu tham khảo

### Nhiệm vụ 1: Mô hình đa phương thức là gì
- https://example.com/multimodal-model-definition
....

### Nhiệm vụ 2: Các mô hình đa phương thức mới nhất gồm những gì
- https://example.com/gpt4v
....
...

### 14.5.3 Dịch vụ tạo báo cáo

`ReportingService` chịu trách nhiệm gọi Agent tạo báo cáo, hợp nhất bản tóm tắt của tất cả nhiệm vụ con. Đây là bước cuối cùng của quy trình nghiên cứu, tạo báo cáo nghiên cứu cuối cùng.

Nhiệm vụ của nó là:

1. <strong>Định dạng bản tóm tắt nhiệm vụ con</strong>: định dạng bản tóm tắt của tất cả nhiệm vụ con thành định dạng thống nhất
2. <strong>Xây dựng Prompt báo cáo</strong>: xây dựng Prompt dựa trên chủ đề nghiên cứu và bản tóm tắt nhiệm vụ con
3. <strong>Gọi Agent báo cáo</strong>: gọi Report Writer Agent để tạo báo cáo cuối cùng
4. <strong>Sắp xếp trích dẫn</strong>: sắp xếp tất cả trích dẫn nguồn vào phần tài liệu tham khảo

<strong>Mã triển khai cốt lõi</strong>:

```python
from typing import List, Callable, Optional, Tuple

from hello_agents import HelloAgentsLLM
from hello_agents import ToolAwareSimpleAgent
from models import TodoItem
from prompts import report_writer_instructions

class ReportingService:
    """Dịch vụ tạo báo cáo"""

    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_call_listener: Optional[Callable] = None
    ):
        self._llm = llm
        self._tool_call_listener = tool_call_listener

        # Tạo Agent báo cáo
        self._agent = ToolAwareSimpleAgent(
            name="Report Writer",
            system_prompt="Bạn là một chuyên gia viết báo cáo, giỏi hợp nhất thông tin và tạo báo cáo có cấu trúc.",
            llm=llm,
            tool_call_listener=tool_call_listener
        )

    def generate_report(
        self,
        research_topic: str,
        task_summaries: List[Tuple[TodoItem, str, List[str]]]
    ) -> str:
        """Tạo báo cáo cuối cùng

        Args:
            research_topic: chủ đề nghiên cứu
            task_summaries: danh sách bản tóm tắt nhiệm vụ con, mỗi phần tử là (nhiệm vụ, tóm tắt, danh sách URL nguồn)

        Returns:
            Báo cáo cuối cùng (định dạng Markdown)
        """
        # Định dạng bản tóm tắt nhiệm vụ con
        formatted_summaries = self._format_summaries(task_summaries)

        # Xây dựng Prompt
        prompt = report_writer_instructions.format(
            research_topic=research_topic,
            task_summaries=formatted_summaries,
        )

        # Gọi Agent
        report = self._agent.run(prompt)

        return report

    def _format_summaries(
        self,
        task_summaries: List[Tuple[TodoItem, str, List[str]]]
    ) -> str:
        """Định dạng bản tóm tắt nhiệm vụ con

        Định dạng bản tóm tắt của tất cả nhiệm vụ con thành định dạng thống nhất, bao gồm:
        - Số thứ tự nhiệm vụ
        - Tiêu đề nhiệm vụ
        - Ý định nhiệm vụ
        - Nội dung tóm tắt
        - URL nguồn
        """
        formatted = []
        for idx, (task, summary, source_urls) in enumerate(task_summaries, start=1):
            formatted.append(
                f"## Nhiệm vụ {idx}: {task.title}\n\n"
                f"**Ý định**: {task.intent}\n\n"
                f"{summary}\n\n"
                f"**Nguồn**:\n"
            )
            for url in source_urls:
                formatted.append(f"- {url}\n")
            formatted.append("\n")

        return "".join(formatted)
```

### 14.5.4 Dịch vụ điều phối tìm kiếm

`SearchService` chịu trách nhiệm điều phối công cụ tìm kiếm, thực hiện tìm kiếm và trả về kết quả. Đây là cầu nối giữa Agent và SearchTool. Ở đây chúng ta không dùng hình thức để SimpleAgent gọi công cụ trực tiếp như thường lệ, mà trả kết quả thực thi của SearchTool cho Agent thông qua một tầng trung gian; như vậy Agent sẽ tập trung hơn vào việc xử lý thông tin nhận được.

Nhiệm vụ của nó là:

1. <strong>Điều phối công cụ tìm kiếm</strong>: chọn công cụ tìm kiếm theo cấu hình
2. <strong>Thực hiện tìm kiếm</strong>: gọi SearchTool để thực hiện tìm kiếm
3. <strong>Xử lý kết quả</strong>: loại trùng, giới hạn Token, định dạng
4. <strong>Xử lý lỗi</strong>: xử lý trường hợp tìm kiếm thất bại

Mã cốt lõi:

```python
from typing import List, Optional
import logging

from hello_agents.tools import SearchTool
from config import Configuration

logger = logging.getLogger(__name__)

class SearchService:
    """Dịch vụ điều phối tìm kiếm"""

    def __init__(self, config: Configuration):
        self.config = config

        # Tạo SearchTool
        self.search_tool = SearchTool(backend="hybrid")

    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[dict]:
        """Thực hiện tìm kiếm

        Args:
            query: truy vấn tìm kiếm
            max_results: số kết quả tối đa

        Returns:
            Danh sách kết quả tìm kiếm
        """
        try:
            # Gọi SearchTool
            raw_response = self.search_tool.run({
                "input": query,
                "backend": self.config.search_api.value,
                "mode": "structured",
                "max_results": max_results
            })

            # Trích xuất kết quả
            results = raw_response.get("results", [])

            # Xử lý kết quả
            results = self._deduplicate_sources(results)
            results = self._limit_source_tokens(results)

            logger.info(f"Tìm kiếm thành công: {query}, trả về {len(results)} kết quả")

            return results

        except Exception as e:
            logger.error(f"Tìm kiếm thất bại: {query}, lỗi: {e}")
            return []

    def _deduplicate_sources(self, sources: List[dict]) -> List[dict]:
        """Loại bỏ URL trùng lặp"""
        seen_urls = set()
        unique_sources = []

        for source in sources:
            url = source.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_sources.append(source)

        return unique_sources

    def _limit_source_tokens(
        self,
        sources: List[dict],
        max_tokens_per_source: int = 2000
    ) -> List[dict]:
        """Giới hạn số Token của mỗi nguồn"""
        limited_sources = []

        for source in sources:
            snippet = source.get("snippet", "")

            # Ước lượng Token đơn giản: 1 Token xấp xỉ 4 ký tự
            max_chars = max_tokens_per_source * 4

            if len(snippet) > max_chars:
                snippet = snippet[:max_chars] + "..."

            limited_sources.append({
                **source,
                "snippet": snippet
            })

        return limited_sources
```

Chọn công cụ tìm kiếm theo cấu hình, như thể hiện trong Hình 14.8:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-8.png" alt="" width="85%"/>
  <p>Hình 14.8 Quy trình điều phối công cụ tìm kiếm</p>
</div>

<strong>Logic điều phối</strong>:

1. <strong>Đọc cấu hình</strong>: đọc cấu hình `SEARCH_API` từ tệp `.env`
2. <strong>Chọn công cụ</strong>: chọn công cụ tìm kiếm theo cấu hình (tavily, duckduckgo, perplexity...)
3. <strong>Thực hiện tìm kiếm</strong>: gọi SearchTool để thực hiện tìm kiếm
4. <strong>Xử lý kết quả</strong>: loại trùng, giới hạn Token, định dạng
5. <strong>Trả về kết quả</strong>: trả về kết quả tìm kiếm đã xử lý

Để nâng cao hiệu quả và giảm chi phí, chúng ta có thể thêm bộ nhớ đệm kết quả tìm kiếm:

```python
import hashlib
import json
from pathlib import Path

class SearchService:
    def __init__(self, config: Configuration):
        self.config = config
        self.search_tool = SearchTool(backend="hybrid")

        # Thư mục bộ nhớ đệm
        self.cache_dir = Path("./cache/search")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def search(
        self,
        query: str,
        max_results: int = 5,
        use_cache: bool = True
    ) -> List[dict]:
        """Thực hiện tìm kiếm (có bộ nhớ đệm)"""
        # Tạo khóa bộ nhớ đệm
        cache_key = self._generate_cache_key(query, max_results)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Thử đọc từ bộ nhớ đệm
        if use_cache and cache_file.exists():
            logger.info(f"Đọc kết quả tìm kiếm từ bộ nhớ đệm: {query}")
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # Thực hiện tìm kiếm
        results = self._execute_search(query, max_results)

        # Lưu vào bộ nhớ đệm
        if use_cache and results:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        return results

    def _generate_cache_key(self, query: str, max_results: int) -> str:
        """Tạo khóa bộ nhớ đệm"""
        # Dùng truy vấn và số kết quả tối đa để tạo mã băm MD5
        content = f"{query}_{max_results}_{self.config.search_api.value}"
        return hashlib.md5(content.encode()).hexdigest()
```

Thông qua bốn dịch vụ cốt lõi (PlanningService, SummarizationService, ReportingService, SearchService), chúng ta đã xây dựng một quy trình nghiên cứu hoàn chỉnh. Các dịch vụ này đảm nhận chức năng riêng, cộng tác qua giao diện rõ ràng, hiện thực hóa quy trình tự động từ chủ đề nghiên cứu đến báo cáo cuối cùng.

## 14.6 Thiết kế tương tác giao diện người dùng

Trong các chương trước, chúng ta đã triển khai hệ thống backend hoàn chỉnh. Phần này sẽ giới thiệu chi tiết thiết kế tương tác frontend, bao gồm UI hộp thoại modal toàn màn hình, hiển thị tiến độ theo thời gian thực và trực quan hóa kết quả nghiên cứu.

### 14.6.1 Thiết kế UI hộp thoại modal toàn màn hình

Trợ lý nghiên cứu chuyên sâu áp dụng thiết kế UI hộp thoại modal toàn màn hình, thiết kế này có các ưu điểm sau:

1. <strong>Trải nghiệm đắm chìm</strong>: hiển thị toàn màn hình, tránh xao nhãng, tập trung vào nghiên cứu
2. <strong>Phân cấp rõ ràng</strong>: trang chính và trang nghiên cứu tách biệt, phân cấp rõ ràng
3. <strong>Dễ đóng</strong>: nhấn nút đóng hoặc phím ESC để quay về trang chính
4. <strong>Thiết kế responsive</strong>: thích ứng với các kích thước màn hình khác nhau

Như thể hiện trong Hình 14.9, hộp thoại modal toàn màn hình gồm các phần sau:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-9.png" alt="" width="85%"/>
  <p>Hình 14.9 UI hộp thoại modal toàn màn hình</p>
</div>

<strong>Thành phần UI</strong>:

1. <strong>Thanh trên cùng</strong>: chứa chủ đề nghiên cứu và nút đóng
2. <strong>Vùng tiến độ</strong>: hiển thị tiến độ nghiên cứu hiện tại (lập kế hoạch, thực thi, báo cáo)
3. <strong>Vùng nội dung</strong>: hiển thị kết quả nghiên cứu (định dạng Markdown)
4. <strong>Thanh dưới cùng</strong>: hiển thị thông tin trạng thái (như "Đang nghiên cứu...", "Đã hoàn thành")

Triển khai Vue tương ứng như sau (ResearchModal.vue):

```vue
<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="close">
    <div class="modal-container">
      <!-- Thanh trên cùng -->
      <div class="modal-header">
        <h2>{{ researchTopic }}</h2>
        <button @click="close" class="close-button">
          <svg><!-- Biểu tượng đóng --></svg>
        </button>
      </div>

      <!-- Vùng tiến độ -->
      <div class="progress-section">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: progressPercentage + '%' }"
          ></div>
        </div>
        <div class="progress-text">{{ progressText }}</div>
      </div>

      <!-- Vùng nội dung -->
      <div class="content-section">
        <div v-if="isLoading" class="loading-spinner">
          <div class="spinner"></div>
          <p>Đang nghiên cứu, vui lòng chờ...</p>
        </div>

        <div v-else class="markdown-content" v-html="renderedMarkdown"></div>
      </div>

      <!-- Thanh dưới cùng -->
      <div class="modal-footer">
        <span class="status-text">{{ statusText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'

interface Props {
  isOpen: boolean
  researchTopic: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()

// Trạng thái
const isLoading = ref(true)
const progressPercentage = ref(0)
const progressText = ref('Đang chuẩn bị...')
const statusText = ref('Đang nghiên cứu...')
const markdownContent = ref('')

// Render Markdown
const renderedMarkdown = computed(() => {
  return marked(markdownContent.value)
})

// Đóng modal
const close = () => {
  emit('close')
}

// Lắng nghe phím ESC
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    close()
  }
}

// Thêm listener bàn phím khi mount
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    document.addEventListener('keydown', handleKeydown)
  } else {
    document.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
......
</style>
```

Để thích ứng với các kích thước màn hình khác nhau, chúng ta thêm media query:

```css
/* Thiết bị tablet */
@media (max-width: 768px) {
  .modal-container {
    width: 95vw;
    height: 95vh;
  }

  .modal-header,
  .progress-section,
  .content-section,
  .modal-footer {
    padding: 15px 20px;
  }
}

/* Thiết bị di động */
@media (max-width: 480px) {
  .modal-container {
    width: 100vw;
    height: 100vh;
    border-radius: 0;
  }

  .modal-header h2 {
    font-size: 18px;
  }
}
```

### 14.6.2 Hiển thị tiến độ theo thời gian thực

Trợ lý nghiên cứu chuyên sâu dùng SSE để hiển thị tiến độ theo thời gian thực. SSE là công nghệ server push, cho phép server chủ động gửi dữ liệu tới client; nội dung này cũng đã được giải thích trong chương về giao thức.

Như thể hiện trong Hình 14.10, quy trình SSE gồm các bước sau:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/14-figures/14-10.png" alt="" width="85%"/>
  <p>Hình 14.10 Quy trình SSE</p>
</div>

<strong>Mô tả quy trình</strong>:

1. <strong>Client khởi tạo yêu cầu</strong>: gửi yêu cầu POST tới `/api/research`, kèm chủ đề nghiên cứu
2. <strong>Server thiết lập kết nối SSE</strong>: trả về phản hồi `text/event-stream`
3. <strong>Server đẩy tiến độ</strong>: định kỳ đẩy tiến độ nghiên cứu (lập kế hoạch, thực thi, báo cáo)
4. <strong>Client nhận tiến độ</strong>: lắng nghe sự kiện SSE, cập nhật UI
5. <strong>Nghiên cứu hoàn tất</strong>: server đẩy báo cáo cuối cùng, đóng kết nối

Nếu muốn dùng SSE trong dự án frontend/backend, cần cấu hình thêm như sau.

<strong>Endpoint SSE của backend FastAPI</strong>:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json

app = FastAPI()

async def research_stream(topic: str) -> AsyncGenerator[str, None]:
    """Bộ sinh stream nghiên cứu

    Tạo dữ liệu định dạng SSE:
    data: {"type": "progress", "data": {...}}

    """
    try:
        # 1. Giai đoạn lập kế hoạch
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'planning', 'percentage': 10, 'text': 'Đang lập kế hoạch nhiệm vụ nghiên cứu...'})}\n\n"

        # Gọi PlanningService
        todo_items = await planning_service.plan_todo_list(topic)

        yield f"data: {json.dumps({'type': 'plan', 'data': [item.dict() for item in todo_items]})}\n\n"

        # 2. Giai đoạn thực thi
        task_summaries = []
        for idx, task in enumerate(todo_items, start=1):
            # Cập nhật tiến độ
            percentage = 10 + (idx / len(todo_items)) * 70
            yield f"data: {json.dumps({'type': 'progress', 'stage': 'executing', 'percentage': percentage, 'text': f'Đang nghiên cứu nhiệm vụ {idx}/{len(todo_items)}: {task.title}'})}\n\n"

            # Tìm kiếm
            search_results = await search_service.search(task.query)

            # Tóm tắt
            summary, source_urls = await summarization_service.summarize_task(task, search_results)

            task_summaries.append((task, summary, source_urls))

            # Đẩy bản tóm tắt nhiệm vụ
            yield f"data: {json.dumps({'type': 'task_summary', 'task_id': task.id, 'summary': summary})}\n\n"

        # 3. Giai đoạn báo cáo
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'reporting', 'percentage': 90, 'text': 'Đang tạo báo cáo cuối cùng...'})}\n\n"

        # Tạo báo cáo
        report = await reporting_service.generate_report(topic, task_summaries)

        # Đẩy báo cáo cuối cùng
        yield f"data: {json.dumps({'type': 'report', 'data': report})}\n\n"

        # Hoàn tất
        yield f"data: {json.dumps({'type': 'progress', 'stage': 'completed', 'percentage': 100, 'text': 'Nghiên cứu hoàn tất!'})}\n\n"

    except Exception as e:
        # Xử lý lỗi
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

@app.post("/api/research")
async def research(request: ResearchRequest):
    """Endpoint nghiên cứu (SSE)"""
    return StreamingResponse(
        research_stream(request.topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

<strong>Frontend dùng EventSource để nhận SSE</strong>:

```typescript
// composables/useResearch.ts
import { ref } from 'vue'

export function useResearch() {
  const isLoading = ref(false)
  const progressPercentage = ref(0)
  const progressText = ref('')
  const markdownContent = ref('')
  const error = ref<string | null>(null)

  const startResearch = (topic: string) => {
    isLoading.value = true
    error.value = null

    // Tạo EventSource
    const eventSource = new EventSource(`/api/research?topic=${encodeURIComponent(topic)}`)

    // Lắng nghe message
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'progress':
          progressPercentage.value = data.percentage
          progressText.value = data.text
          break

        case 'plan':
          // Hiển thị kết quả lập kế hoạch
          console.log('Kết quả lập kế hoạch:', data.data)
          break

        case 'task_summary':
          // Nối bản tóm tắt nhiệm vụ vào Markdown
          markdownContent.value += `\n\n## Nhiệm vụ ${data.task_id}\n\n${data.summary}`
          break

        case 'report':
          // Hiển thị báo cáo cuối cùng
          markdownContent.value = data.data
          break

        case 'error':
          error.value = data.message
          eventSource.close()
          isLoading.value = false
          break

        case 'completed':
          eventSource.close()
          isLoading.value = false
          break
      }
    }

    // Xử lý lỗi
    eventSource.onerror = (err) => {
      console.error('Lỗi SSE:', err)
      error.value = 'Kết nối thất bại, vui lòng thử lại'
      eventSource.close()
      isLoading.value = false
    }
  }

  return {
    isLoading,
    progressPercentage,
    progressText,
    markdownContent,
    error,
    startResearch,
  }
}
```

<strong>Sử dụng trong component</strong>:

```vue
<script setup lang="ts">
import { useResearch } from '@/composables/useResearch'

const {
  isLoading,
  progressPercentage,
  progressText,
  markdownContent,
  error,
  startResearch
} = useResearch()

const handleStartResearch = (topic: string) => {
  startResearch(topic)
}
</script>
```

### 14.6.3 Trực quan hóa kết quả nghiên cứu

Kết quả nghiên cứu được hiển thị ở định dạng Markdown, bao gồm các yếu tố như tiêu đề, đoạn văn, danh sách, trích dẫn. Chúng ta dùng thư viện `marked` để chuyển Markdown thành HTML và thêm kiểu tùy chỉnh.

<strong>Render Markdown</strong>:

```typescript
import { marked } from 'marked'

// Cấu hình marked
marked.setOptions({
  breaks: true,  // Hỗ trợ xuống dòng
  gfm: true,     // Hỗ trợ GitHub Flavored Markdown
})

// Render
const renderedHtml = marked(markdownContent.value)
```

Báo cáo nghiên cứu chứa nhiều trích dẫn nguồn, chúng ta cần xử lý đặc biệt:

```markdown
## Tài liệu tham khảo

### Nhiệm vụ 1: Thông tin cơ bản của Datawhale
- [Datawhale GitHub](https://github.com/datawhalechina)
- [Trang web chính thức của Datawhale](https://datawhale.club)

### Nhiệm vụ 2: Các dự án chính của Datawhale
- [Hướng dẫn Hello-Agents](https://github.com/datawhalechina/Hello-Agents)
......
```

Thông qua UI hộp thoại modal toàn màn hình, hiển thị tiến độ SSE theo thời gian thực và trực quan hóa kết quả Markdown, chúng ta đã xây dựng một giao diện frontend thân thiện với người dùng. Người dùng có thể thấy rõ tiến độ nghiên cứu và xem kết quả nghiên cứu ở định dạng đẹp mắt.

## 14.7 Tóm tắt chương

Trong chương này, chúng ta đã xây dựng từ đầu một hệ thống agent nghiên cứu chuyên sâu tự động hoàn chỉnh. Hãy cùng nhìn lại các điểm cốt lõi:

<strong>(1) Mô hình nghiên cứu hướng TODO</strong>

Chúng ta đã đề xuất một mô hình nghiên cứu mới — nghiên cứu hướng TODO. Mô hình này phân rã chủ đề nghiên cứu phức tạp thành các nhiệm vụ con có thể thực thi, hoàn thành nghiên cứu qua ba giai đoạn:

- <strong>Giai đoạn lập kế hoạch</strong>: phân rã chủ đề nghiên cứu thành 3-5 nhiệm vụ con, mỗi nhiệm vụ con gồm tiêu đề, ý định và truy vấn tìm kiếm
- <strong>Giai đoạn thực thi</strong>: thực hiện tìm kiếm và tóm tắt cho mỗi nhiệm vụ con, tạo tri thức có cấu trúc
- <strong>Giai đoạn báo cáo</strong>: hợp nhất bản tóm tắt của tất cả nhiệm vụ con, tạo báo cáo nghiên cứu cuối cùng

Ưu điểm của mô hình này là:

1. <strong>Kiểm soát tốt</strong>: mỗi nhiệm vụ con có mục tiêu và phạm vi rõ ràng
2. <strong>Chất lượng đáng tin cậy</strong>: các Agent chuyên trách đảm bảo chất lượng từng khâu
3. <strong>Dễ gỡ lỗi</strong>: có thể gỡ lỗi riêng từng nhiệm vụ con
4. <strong>Khả năng mở rộng tốt</strong>: có thể dễ dàng thêm nhiệm vụ con mới hoặc sửa nhiệm vụ con hiện có

<strong>(2) Hệ thống cộng tác ba Agent</strong>

Chúng ta đã thiết kế ba Agent chuyên trách, mỗi Agent đảm nhận chức năng riêng:

- <strong>TODO Planner (Chuyên gia lập kế hoạch nghiên cứu)</strong>: chịu trách nhiệm phân rã chủ đề nghiên cứu thành nhiệm vụ con
- <strong>Task Summarizer (Chuyên gia tóm tắt nhiệm vụ)</strong>: chịu trách nhiệm tóm tắt kết quả tìm kiếm của mỗi nhiệm vụ con
- <strong>Report Writer (Chuyên gia viết báo cáo)</strong>: chịu trách nhiệm hợp nhất bản tóm tắt của tất cả nhiệm vụ con, tạo báo cáo cuối cùng

Ưu điểm của thiết kế này là:

1. <strong>Trách nhiệm rõ ràng</strong>: mỗi Agent tập trung vào một nhiệm vụ cụ thể
2. <strong>Tối ưu Prompt</strong>: có thể tùy chỉnh Prompt riêng cho từng Agent
3. <strong>Dễ bảo trì</strong>: sửa một Agent không ảnh hưởng tới các Agent khác
4. <strong>Đảm bảo chất lượng</strong>: mỗi Agent đều là "chuyên gia" trong lĩnh vực của mình

<strong>(3) Thiết kế ToolAwareSimpleAgent</strong>

Chúng ta đã mở rộng `SimpleAgent` của framework HelloAgents, triển khai `ToolAwareSimpleAgent`. Agent này có năng lực lắng nghe lời gọi công cụ, có thể:

- <strong>Lắng nghe lời gọi công cụ</strong>: lắng nghe mỗi lần gọi công cụ qua hàm callback
- <strong>Phản hồi theo thời gian thực</strong>: đẩy thông tin gọi công cụ tới frontend theo thời gian thực
- <strong>Hỗ trợ gỡ lỗi</strong>: ghi lại mọi lời gọi công cụ, thuận tiện gỡ lỗi

Agent này đã được tích hợp vào framework HelloAgents, có thể tái sử dụng trong các dự án khác.

<strong>(4) Tích hợp hệ thống công cụ</strong>

Chúng ta đã tận dụng đầy đủ hệ thống công cụ của framework HelloAgents:

- <strong>SearchTool</strong>: mở rộng hỗ trợ nhiều công cụ tìm kiếm hơn (Tavily, DuckDuckGo, Perplexity...)
- <strong>NoteTool</strong>: lưu bền tiến độ nghiên cứu, hỗ trợ khôi phục và kiểm toán
- <strong>ToolRegistry</strong>: quản lý thống nhất tất cả công cụ, hỗ trợ mở rộng tùy chỉnh

Thông qua thiết kế cấu hình hóa, người dùng có thể dễ dàng chuyển đổi công cụ tìm kiếm mà không cần sửa mã.

<strong>(5) Triển khai các dịch vụ cốt lõi</strong>

Chúng ta đã triển khai bốn dịch vụ cốt lõi, kết nối Agent và công cụ:

- <strong>PlanningService</strong>: gọi Agent lập kế hoạch, phân tích JSON, xác thực định dạng
- <strong>SummarizationService</strong>: gọi Agent tóm tắt, xử lý kết quả tìm kiếm, trích xuất nguồn
- <strong>ReportingService</strong>: gọi Agent báo cáo, hợp nhất bản tóm tắt, tạo báo cáo
- <strong>SearchService</strong>: điều phối công cụ tìm kiếm, xử lý kết quả, giảm cấp khi lỗi, bộ nhớ đệm kết quả

Các dịch vụ này đảm nhận chức năng riêng, cộng tác qua giao diện rõ ràng, hiện thực hóa quy trình tự động từ chủ đề nghiên cứu đến báo cáo cuối cùng.

<strong>(6) Thiết kế tương tác frontend</strong>

Chúng ta đã thiết kế giao diện frontend thân thiện với người dùng:

- <strong>Hộp thoại modal toàn màn hình</strong>: trải nghiệm đắm chìm, phân cấp rõ ràng
- <strong>Tiến độ SSE theo thời gian thực</strong>: hiển thị tiến độ nghiên cứu theo thời gian thực, trải nghiệm người dùng tốt
- <strong>Trực quan hóa Markdown</strong>: định dạng đẹp mắt, cấu trúc rõ ràng

Thông qua bộ công nghệ Vue 3 + TypeScript + SSE, chúng ta đã hiện thực hóa một ứng dụng web hiện đại.



Những kiến thức này không chỉ áp dụng cho trợ lý nghiên cứu chuyên sâu mà còn có thể áp dụng cho các ứng dụng AI khác. Hy vọng độc giả có thể dựa trên nền tảng của chương này để khám phá thêm nhiều khả năng, xây dựng những hệ thống AI mạnh mẽ hơn.

Trong chương tiếp theo, chúng ta sẽ xây dựng một hệ thống đa Agent kết hợp với game engine — Thị trấn Cyber, khám phá các mô hình tương tác và cộng tác phức tạp giữa các Agent. Hãy đón chờ!

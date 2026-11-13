# Chương 16: Đồ án tốt nghiệp: Xây dựng ứng dụng đa Agent của riêng bạn

Chúc mừng bạn đã đến chương cuối cùng của khóa học Hello-Agents! Trong 15 chương trước, chúng ta đã xây dựng framework HelloAgents từ con số 0, tìm hiểu các khái niệm cốt lõi của Agent, nhiều mô hình khác nhau, hệ thống công cụ, cơ chế bộ nhớ, giao thức giao tiếp, huấn luyện học tăng cường và đánh giá hiệu năng. Ở Chương 13-15, chúng ta còn thông qua ba dự án thực chiến hoàn chỉnh (trợ lý du lịch thông minh, Agent nghiên cứu chuyên sâu tự động, thị trấn cyber) để trình bày cách kết nối các kiến thức đã học.

Bây giờ, đã đến lúc bạn trở thành một người xây dựng hệ thống Agent thực thụ! Chương này sẽ hướng dẫn bạn <strong>xây dựng ứng dụng đa Agent của riêng bạn</strong>, và chia sẻ thành quả với cộng đồng thông qua cộng tác mã nguồn mở.

## 16.1 Ý nghĩa của đồ án tốt nghiệp

### 16.1.1 Vì sao phải làm đồ án tốt nghiệp

Cách tốt nhất để học công nghệ không phải là đọc hướng dẫn, mà là <strong>thực hành</strong>. Qua các chương trước, bạn đã nắm được kiến thức lý thuyết và công cụ kỹ thuật để xây dựng hệ thống Agent. Nhưng thách thức thực sự nằm ở: <strong>Làm thế nào để áp dụng những kiến thức này vào bài toán thực tế? Làm thế nào để thiết kế một hệ thống hoàn chỉnh? Làm thế nào để xử lý các trường hợp biên và ngoại lệ?</strong>

Giá trị cốt lõi của đồ án tốt nghiệp nằm ở việc rèn luyện năng lực ứng dụng tổng hợp của bạn, tích hợp có chọn lọc toàn bộ kiến thức đã học trước đó (mô hình Agent, hệ thống công cụ, cơ chế bộ nhớ, giao thức giao tiếp, v.v.) vào một dự án hoàn chỉnh.

Thông qua việc học và thực hành trong chương này, hy vọng bạn có thể độc lập thiết kế và hiện thực một ứng dụng Agent hoàn chỉnh, thành thạo các chức năng khác nhau của framework HelloAgents, nắm vững thao tác cơ bản với Git và GitHub, học cách viết tài liệu dự án rõ ràng, tham gia phát triển cộng tác trong cộng đồng mã nguồn mở, và cuối cùng có được một tác phẩm kỹ thuật có thể trình diễn.

### 16.1.2 Hình thức của đồ án tốt nghiệp

Đồ án tốt nghiệp của bạn sẽ được nộp dưới dạng <strong>dự án mã nguồn mở</strong> vào kho dự án đồng sáng tạo của Hello-Agents (thư mục `Co-creation-projects`). Yêu cầu cụ thể như sau:

1. <strong>Đặt tên dự án</strong>: Dùng định dạng `{ten-nguoi-dung-GitHub-cua-ban}-{ten-du-an}`, ví dụ `jjyaoao-CodeReviewAgent`

2. <strong>Nội dung dự án</strong>:
   - Một Jupyter Notebook có thể chạy được (tệp `.ipynb`) hoặc script Python
   - Danh sách phụ thuộc đầy đủ (`requirements.txt`)
   - Tài liệu README rõ ràng (`README.md`)
   - Tùy chọn: video demo, ảnh chụp màn hình, bộ dữ liệu, v.v.

3. <strong>Cách nộp</strong>: Nộp qua Pull Request (PR) trên GitHub

4. <strong>Quy trình đánh giá</strong>: Thành viên cộng đồng sẽ review mã của bạn, đưa ra gợi ý cải tiến, sau khi được chấp thuận sẽ hợp nhất vào kho chính

## 16.2 Hướng dẫn chọn đề tài dự án

### 16.2.1 Nguyên tắc chọn đề tài

Một đồ án tốt nghiệp tốt nên có tính thực dụng, giải quyết vấn đề thực tế chứ không phải công nghệ vì công nghệ; chúng ta cần hướng tới việc hoàn thành trong thời gian và nguồn lực có hạn, đồng thời thể hiện rõ năng lực kỹ thuật của bạn.

### 16.2.2 Các hướng đề tài gợi ý

Dưới đây là một số hướng dự án gợi ý, bạn có thể chọn một trong số đó, hoặc tự đề xuất ý tưởng mới:

<strong>(1) Công cụ năng suất</strong>

- <strong>Trợ lý đánh giá mã nguồn thông minh</strong>: Tự động phân tích chất lượng mã, phát hiện lỗi tiềm ẩn, đưa ra gợi ý tối ưu
- <strong>Trình tạo tài liệu thông minh</strong>: Tự động tạo tài liệu API, hướng dẫn sử dụng từ mã nguồn
- <strong>Trợ lý cuộc họp thông minh</strong>: Ghi lại nội dung cuộc họp, tạo biên bản cuộc họp, trích xuất các mục hành động
- <strong>Trợ lý email thông minh</strong>: Tự động phân loại email, tạo bản nháp trả lời, nhắc nhở việc quan trọng

<strong>(2) Hỗ trợ học tập</strong>

- <strong>Bạn đồng hành học tập thông minh</strong>: Gợi ý tài nguyên học theo tiến độ học tập, tạo bài tập, giải đáp thắc mắc
- <strong>Trợ lý bài báo học thuật thông minh</strong>: Giúp tìm tài liệu, tóm tắt bài báo, tạo trích dẫn
- <strong>Gia sư lập trình thông minh</strong>: Cung cấp bài tập lập trình, review mã nguồn, lập kế hoạch lộ trình học tập
- <strong>Trợ lý học ngôn ngữ thông minh</strong>: Cung cấp luyện hội thoại, sửa lỗi ngữ pháp, mở rộng từ vựng

<strong>(3) Sáng tạo và giải trí</strong>

- <strong>Trình tạo truyện thông minh</strong>: Tạo tiểu thuyết, kịch bản, thơ từ đầu vào của người dùng
- <strong>NPC trò chơi thông minh</strong>: Tạo nhân vật trò chơi có cá tính, có thể trò chuyện tự nhiên với người chơi
- <strong>Gợi ý âm nhạc thông minh</strong>: Gợi ý âm nhạc theo tâm trạng, bối cảnh, tạo danh sách phát
- <strong>Trợ lý công thức nấu ăn thông minh</strong>: Gợi ý công thức theo nguyên liệu, khẩu vị, tạo danh sách mua sắm

<strong>(4) Phân tích dữ liệu</strong>

- <strong>Chuyên gia phân tích dữ liệu thông minh</strong>: Tự động phân tích dữ liệu, tạo biểu đồ trực quan, viết báo cáo phân tích
- <strong>Phân tích chứng khoán thông minh</strong>: Phân tích dữ liệu chứng khoán, dư luận tin tức, đưa ra gợi ý đầu tư
- <strong>Giám sát dư luận thông minh</strong>: Giám sát mạng xã hội, trang tin tức, phân tích xu hướng dư luận
- <strong>Phân tích đối thủ cạnh tranh thông minh</strong>: Thu thập thông tin đối thủ cạnh tranh, phân tích so sánh, tạo báo cáo

<strong>(5) Dịch vụ đời sống</strong>

- <strong>Trợ lý sức khỏe thông minh</strong>: Ghi chép dữ liệu sức khỏe, đưa gợi ý sức khỏe, lập kế hoạch vận động
- <strong>Trợ lý quản lý tài chính thông minh</strong>: Ghi chép thu chi, phân tích thói quen tiêu dùng, đưa gợi ý quản lý tài chính
- <strong>Trợ lý mua sắm thông minh</strong>: So sánh giá, gợi ý sản phẩm, tạo danh sách mua sắm
- <strong>Điều khiển nhà thông minh</strong>: Điều khiển thiết bị nhà thông minh bằng ngôn ngữ tự nhiên

### 16.2.3 Ví dụ chọn đề tài

Hãy cùng thông qua một ví dụ cụ thể để minh họa cách chọn đề tài và thiết kế dự án.

<strong>Tên dự án</strong>: Trợ lý đánh giá mã nguồn thông minh (CodeReviewAgent)

<strong>Phân tích vấn đề</strong>: Đánh giá mã nguồn là một khâu quan trọng trong phát triển phần mềm, nhưng đánh giá thủ công tốn thời gian và dễ bỏ sót vấn đề. Các công cụ phân tích tĩnh hiện có chỉ có thể phát hiện lỗi cú pháp, không thể hiểu logic mã, vì vậy cần một trợ lý thông minh có thể hiểu ngữ nghĩa mã và cung cấp phân tích sâu.

<strong>Chức năng cốt lõi</strong>: Dự án này sẽ hiện thực phân tích chất lượng mã (kiểm tra phong cách mã, quy ước đặt tên, tính đầy đủ của chú thích), phát hiện lỗi tiềm ẩn (tìm lỗi logic, vấn đề điều kiện biên, rò rỉ tài nguyên), gợi ý tối ưu hiệu năng (nhận diện điểm nghẽn hiệu năng, đề xuất phương án tối ưu), quét lỗ hổng bảo mật (phát hiện SQL injection, XSS và các vấn đề bảo mật khác) cũng như gợi ý thực hành tốt nhất (đề xuất cải tiến dựa trên đặc điểm ngôn ngữ và mẫu thiết kế).

<strong>Kết quả dự kiến</strong>: Cuối cùng sẽ bàn giao một Jupyter Notebook có thể chạy được để trình diễn quy trình đánh giá hoàn chỉnh, hỗ trợ các ngôn ngữ phổ biến như Python, JavaScript, có thể tạo báo cáo đánh giá định dạng Markdown có cấu trúc, và cung cấp ví dụ mã cụ thể cùng gợi ý cải tiến.

## 16.3 Chuẩn bị môi trường phát triển

### 16.3.1 Cài đặt các công cụ cần thiết

Trước khi bắt đầu phát triển, hãy đảm bảo môi trường phát triển của bạn đã cài đặt các công cụ sau:

<strong>(1) Môi trường Python</strong>

```bash
# Cài đặt HelloAgents
pip install "hello-agents[all]"
```

<strong>(2) Git và GitHub</strong>

```bash
# Kiểm tra phiên bản Git
git --version

# Cấu hình thông tin người dùng Git
git config --global user.name "Tên của bạn"
git config --global user.email "email-cua-ban@example.com"

# Cấu hình khóa SSH GitHub (khuyến nghị)
# 1. Tạo khóa SSH
ssh-keygen -t ed25519 -C "email-cua-ban@example.com"

# 2. Thêm khóa công khai vào GitHub
# Sao chép nội dung của ~/.ssh/id_ed25519.pub
# Thêm trong GitHub Settings > SSH and GPG keys

# 3. Kiểm tra kết nối
ssh -T git@github.com
```

<strong>(3) Jupyter Notebook</strong>

```bash
# Cài đặt Jupyter
pip install jupyter notebook

# Hoặc dùng JupyterLab (khuyến nghị)
pip install jupyterlab

# Khởi động Jupyter
jupyter lab
```

### 16.3.2 Fork kho dự án

<strong>Bước 1: Fork kho</strong>

1. Truy cập kho Hello-Agents: https://github.com/datawhalechina/hello-agents
2. Nhấp nút "Fork" ở góc trên bên phải, như vị trí khung đỏ trong Hình 16.1
3. Chọn tài khoản GitHub của bạn, tạo Fork

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/hello-agents/main/docs/images/16-figures/16-1.png" alt="" width="85%"/>
  <p>Hình 16.1 Các bước Fork kho</p>
</div>

<strong>Bước 2: Sao chép về máy cục bộ</strong>

```bash
# Như minh họa trong Hình 16.2, sao chép kho bạn đã Fork
git clone git@github.com:ten-nguoi-dung-cua-ban/hello-agents.git

# Vào thư mục dự án
cd Hello-Agents

# Thêm kho upstream (để đồng bộ cập nhật)
git remote add upstream https://github.com/datawhalechina/hello-agents.git

# Xem các kho từ xa
git remote -v
```

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/hello-agents/main/docs/images/16-figures/16-2.png" alt="" width="85%"/>
  <p>Hình 16.2 Sao chép kho về máy cục bộ</p>
</div>

<strong>Bước 3: Tạo nhánh phát triển</strong>

```bash
# Tạo và chuyển sang nhánh mới
git checkout -b feature/ten-du-an-cua-ban

# Ví dụ:
git checkout -b feature/code-review-agent
```


### 16.3.3 Cấu trúc thư mục dự án

Tạo thư mục dự án của bạn trong thư mục `Co-creation-projects`:

```bash
# Vào thư mục dự án đồng sáng tạo
cd Co-creation-projects

# Tạo thư mục dự án (định dạng: ten-nguoi-dung-GitHub-ten-du-an)
mkdir ten-nguoi-dung-cua-ban-ten-du-an

# Ví dụ:
mkdir jjyaoao-CodeReviewAgent

# Vào thư mục dự án
cd jjyaoao-CodeReviewAgent
```

Cấu trúc dự án khuyến nghị:

```
jjyaoao-CodeReviewAgent/
├── README.md              # Tài liệu mô tả dự án
├── requirements.txt       # Danh sách phụ thuộc Python
├── main.ipynb            # Jupyter Notebook chính
├── data/                 # Tệp dữ liệu (tùy chọn)
│   ├── sample_code.py
│   └── test_cases.json
├── outputs/              # Kết quả đầu ra (tùy chọn)
│   ├── review_report.md
│   └── screenshots/
├── src/                  # Mã nguồn (tùy chọn, nếu mã nhiều)
│   ├── agents/
│   ├── tools/
│   └── utils/
└──
```

## 16.4 Hướng dẫn phát triển dự án

### 16.4.1 Viết tài liệu README

README là bộ mặt của dự án, một README tốt nên bao gồm các nội dung sau:

```markdown
# Tên dự án

> Mô tả dự án của bạn trong một câu

## 📝 Giới thiệu dự án

Giới thiệu chi tiết về dự án của bạn:
- Giải quyết vấn đề gì?
- Có chức năng đặc sắc gì?
- Phù hợp với bối cảnh nào?

## ✨ Chức năng cốt lõi

- [ ] Chức năng 1: mô tả
- [ ] Chức năng 2: mô tả
- [ ] Chức năng 3: mô tả

## 🛠️ Ngăn xếp công nghệ

- Framework HelloAgents
- Mô hình Agent được sử dụng (như ReAct, Plan-and-Solve, v.v.)
- Công cụ và API được sử dụng
- Các thư viện phụ thuộc khác

## 🚀 Bắt đầu nhanh

### Yêu cầu môi trường

- Python 3.10+
- Các yêu cầu khác

### Cài đặt phụ thuộc


pip install -r requirements.txt


### Cấu hình API key


# Tạo tệp .env
cp .env.example .env

# Chỉnh sửa tệp .env, điền API key của bạn


### Chạy dự án


# Khởi động Jupyter Notebook
jupyter lab

# Mở main.ipynb và chạy


## 📖 Ví dụ sử dụng

Trình bày cách sử dụng dự án của bạn, tốt nhất nên bao gồm ví dụ mã và kết quả chạy.

## 🎯 Điểm nổi bật của dự án

- Điểm nổi bật 1: giải thích
- Điểm nổi bật 2: giải thích
- Điểm nổi bật 3: giải thích

## 📊 Đánh giá hiệu năng

Nếu có kết quả đánh giá, hãy trình bày ở đây:
- Độ chính xác: XX%
- Thời gian phản hồi: XX giây
- Các chỉ số khác

## 🔮 Kế hoạch tương lai

- [ ] Chức năng chưa hiện thực 1
- [ ] Chức năng chưa hiện thực 2
- [ ] Phần cần tối ưu

## 🤝 Hướng dẫn đóng góp

Hoan nghênh bạn tạo Issue và Pull Request!

## 📄 Giấy phép

MIT License

## 👤 Tác giả

- GitHub: [@ten-nguoi-dung-cua-ban](https://github.com/ten-nguoi-dung-cua-ban)
- Email: email-cua-ban@example.com (tùy chọn)

## 🙏 Lời cảm ơn

Cảm ơn cộng đồng Datawhale và dự án Hello-Agents!
```

### 16.4.2 Viết requirements.txt

Liệt kê tất cả phụ thuộc Python mà dự án cần:

```txt
# Phụ thuộc cốt lõi
hello-agents[all]>=0.2.7

# Trực quan hóa (nếu cần)
matplotlib>=3.7.0
plotly>=5.14.0

# Framework Web (nếu cần)
fastapi>=0.109.0
uvicorn>=0.27.0
```

### 16.4.3 Phát triển Jupyter Notebook

<strong>(1) Gợi ý cấu trúc Notebook</strong>

Một Jupyter Notebook tốt nên bao gồm các phần sau:

```python
# ========================================
# Phần 1: Giới thiệu dự án
# ========================================

"""
# Tên dự án

## Giới thiệu dự án
Giới thiệu ngắn gọn mục tiêu và chức năng của dự án

## Thông tin tác giả
- Họ tên: XXX
- GitHub: @XXX
- Ngày: 2025-XX-XX
"""

# ========================================
# Phần 2: Cấu hình môi trường
# ========================================

# Cài đặt phụ thuộc
!pip install -q hello-agents[all]

# Nhập các thư viện cần thiết
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import BaseTool
import os
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

# ========================================
# Phần 3: Định nghĩa công cụ
# ========================================

class CustomTool(BaseTool):
    """Lớp công cụ tùy chỉnh"""

    name = "tool_name"
    description = "Mô tả công cụ"

    def run(self, query: str) -> str:
        """Logic thực thi công cụ"""
        # Hiện thực logic công cụ của bạn
        return "Kết quả"

# ========================================
# Phần 4: Xây dựng Agent
# ========================================

# Tạo LLM
llm = HelloAgentsLLM()

# Tạo Agent
agent = SimpleAgent(
    name="Tên Agent",
    llm=llm,
    system_prompt="System prompt"
)

# Thêm công cụ
agent.add_tool(CustomTool())

# ========================================
# Phần 5: Trình diễn chức năng
# ========================================

# Ví dụ 1: Chức năng cơ bản
print("=== Ví dụ 1: Chức năng cơ bản ===")
result = agent.run("Đầu vào của người dùng")
print(result)

# Ví dụ 2: Tình huống phức tạp
print("\n=== Ví dụ 2: Tình huống phức tạp ===")
result = agent.run("Đầu vào phức tạp của người dùng")
print(result)

# ========================================
# Phần 6: Đánh giá hiệu năng (tùy chọn)
# ========================================

# Mã đánh giá
# ...

# ========================================
# Phần 7: Tổng kết và triển vọng
# ========================================

"""
## Tổng kết dự án

### Chức năng đã hiện thực
- Chức năng 1
- Chức năng 2

### Thách thức gặp phải
- Thách thức 1 và giải pháp
- Thách thức 2 và giải pháp

### Hướng cải tiến tương lai
- Cải tiến 1
- Cải tiến 2
"""
```

### 16.4.4 Kiểm thử dự án của bạn

Trước khi nộp, bạn có thể dùng danh sách kiểm tra để đánh giá dự án của mình có đáp ứng yêu cầu nộp hay không:

```markdown
- [ ] Mã chạy được bình thường, không có lỗi
- [ ] Tài liệu README đầy đủ, mô tả rõ ràng
- [ ] requirements.txt bao gồm tất cả phụ thuộc
- [ ] Có ví dụ sử dụng rõ ràng
- [ ] Mã có chú thích phù hợp
- [ ] Kết quả đầu ra đúng như mong đợi
- [ ] Đã xử lý các trường hợp ngoại lệ phổ biến
- [ ] Cấu trúc dự án rõ ràng, đặt tên tệp chuẩn
- [ ] Tệp lớn đã được xử lý thỏa đáng (xem mục tiếp theo)
```

### 16.4.5 Hướng dẫn xử lý tệp lớn

<strong>⚠️ Quan trọng: Tránh để kho chính quá lớn</strong>

Để giữ kho Hello-Agents chính ở dạng nhẹ, hãy tuân thủ các quy định xử lý tệp lớn sau:

<strong>(1) Giới hạn kích thước tệp</strong>

- **Tổng kích thước dự án**: Không vượt quá 5MB
- **Không được nộp trực tiếp**: Tệp video, bộ dữ liệu lớn, tệp mô hình

<strong>(2) Phương án xử lý tệp lớn</strong>

Nếu dự án của bạn chứa tệp lớn (bộ dữ liệu, video, mô hình, v.v.), hãy dùng các phương án sau:

**Phương án 1: Dùng liên kết ngoài (khuyến nghị)**

Tải tệp lớn lên nền tảng bên ngoài, cung cấp liên kết tải trong README:

```markdown
## Bộ dữ liệu

Bộ dữ liệu mà dự án này sử dụng khá lớn, vui lòng tải từ các liên kết sau:

- Bộ dữ liệu 1: [Baidu Netdisk](liên kết) Mã trích xuất: xxxx
- Bộ dữ liệu 2: [Google Drive](liên kết)
- Video demo: [Bilibili](liên kết) / [YouTube](liên kết)
```

Các nền tảng bên ngoài được khuyến nghị:
- **Bộ dữ liệu**: Baidu Netdisk, Google Drive, Kaggle, HuggingFace Datasets
- **Video**: Bilibili, YouTube, Tencent Video
- **Mô hình**: HuggingFace Models, ModelScope
- **Hình ảnh**: GitHub Issues, dịch vụ lưu trữ ảnh

**Phương án 2: Tạo kho độc lập**

Nếu dự án có nhiều tài nguyên, khuyến nghị tạo kho dữ liệu độc lập:

```markdown
## Tài nguyên dự án

Do dự án chứa nhiều dữ liệu và tài nguyên trình diễn, đã tạo riêng kho tài nguyên:

- Kho tài nguyên: https://github.com/ten-nguoi-dung-cua-ban/ten-du-an-resources
- Nội dung bao gồm: bộ dữ liệu, video demo, tệp mô hình, dữ liệu kiểm thử, v.v.

### Cách sử dụng

\`\`\`bash
# Sao chép kho tài nguyên
git clone https://github.com/ten-nguoi-dung-cua-ban/ten-du-an-resources.git

# Đưa dữ liệu vào thư mục dự án
cp -r ten-du-an-resources/data ./data
\`\`\`
```

**Phương án 3: Dùng dữ liệu mẫu**

Chỉ cung cấp dữ liệu mẫu quy mô nhỏ trong kho chính:

```python
# Ghi chú trong README
## Mô tả dữ liệu

- `data/sample.csv`: dữ liệu mẫu (100 bản ghi)
- Bộ dữ liệu đầy đủ (100.000 bản ghi) vui lòng tải từ [đây](liên kết)
```

<strong>(3) Ví dụ thực hành tốt nhất</strong>

```
ten-nguoi-dung-cua-ban-ten-du-an/
├── README.md              # Chứa liên kết tài nguyên bên ngoài
├── requirements.txt
├── main.ipynb
├── .gitignore            # Bỏ qua tệp lớn
├── data/
│   └── sample.csv        # Chỉ dữ liệu mẫu (<1MB)
└── outputs/
    └── demo_result.png   # Chỉ kết quả trình diễn (<1MB)
```

Mô tả trong README:

```markdown
## Dữ liệu và tài nguyên

### Dữ liệu mẫu
Dự án bao gồm dữ liệu mẫu quy mô nhỏ để kiểm thử nhanh (nằm trong `data/sample.csv`)

### Bộ dữ liệu đầy đủ
Bộ dữ liệu đầy đủ (500MB) vui lòng tải từ các liên kết sau:
- Baidu Netdisk: [liên kết] Mã trích xuất: xxxx
- Sau khi tải, giải nén vào thư mục `data/`

### Video demo
- Bilibili: [Video trình diễn dự án](liên kết)
- YouTube: [Demo Video](liên kết)
```

## 16.5 Nộp Pull Request

### 16.5.1 Nộp mã lên GitHub

<strong>Bước 1: Kiểm tra thay đổi</strong>

```bash
# Xem các tệp đã thay đổi
git status
```

<strong>Bước 2: Thêm tệp</strong>

```bash
# Thêm tất cả tệp đã thay đổi
git add .

# Hoặc thêm tệp cụ thể
git add Co-creation-projects/ten-nguoi-dung-cua-ban-ten-du-an/
```

<strong>Bước 3: Commit thay đổi</strong>

Thông điệp commit nên tuân theo định dạng sau:

```bash
# Định dạng: loại: mô tả ngắn
git commit -m "feat: Thêm dự án đồ án tốt nghiệp XXX"
```

<strong>Quy định loại commit:</strong>

- `feat`: Thêm chức năng hoặc dự án mới (dự án đồ án tốt nghiệp dùng loại này)
- `fix`: Sửa lỗi
- `docs`: Cập nhật tài liệu
- `style`: Điều chỉnh định dạng mã (không ảnh hưởng chức năng)
- `refactor`: Tái cấu trúc mã
- `test`: Liên quan đến kiểm thử
- `chore`: Thay đổi khác (như cập nhật phụ thuộc)

<strong>Bước 4: Đẩy lên GitHub</strong>

```bash
# Đẩy lên kho Fork của bạn
git push origin feature/ten-du-an-cua-ban
```

### 16.5.2 Tạo Pull Request

<strong>Bước 1: Truy cập GitHub</strong>

1. Truy cập kho bạn đã Fork: `https://github.com/ten-nguoi-dung-cua-ban/hello-agents`
2. Nhấp tab "Pull requests", như Hình 16.3
3. Nhấp nút "New pull request"

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/hello-agents/main/docs/images/16-figures/16-3.png" alt="" width="85%"/>
  <p>Hình 16.3 Tạo Pull Request</p>
</div>


<strong>Bước 2: Chọn nhánh</strong>

- Base repository: `datawhalechina/hello-agents`
- Base branch: `main`
- Head repository: `ten-nguoi-dung-cua-ban/hello-agents`
- Compare branch: `feature/ten-du-an-cua-ban`

<strong>Bước 3: Điền thông tin PR</strong>

<strong>⚠️ Quan trọng: Định dạng thống nhất cho tiêu đề PR</strong>

Để thuận tiện quản lý và tìm kiếm, tiêu đề PR của tất cả dự án đồ án tốt nghiệp phải tuân theo định dạng sau:

```
[Đồ án tốt nghiệp] Tên dự án - Mô tả ngắn
```

Ví dụ:
- `[Đồ án tốt nghiệp] CodeReviewAgent - Trợ lý đánh giá mã nguồn thông minh`
- `[Đồ án tốt nghiệp] StudyBuddy - Bạn đồng hành học tập AI`
- `[Đồ án tốt nghiệp] DataAnalyst - Chuyên gia phân tích dữ liệu thông minh`

<strong>Mẫu mô tả PR:</strong>

```markdown
## Thông tin dự án

- **Tên dự án**: XXX
- **Tác giả**: @ten-nguoi-dung-cua-ban
- **Loại dự án**: Công cụ năng suất/Hỗ trợ học tập/Sáng tạo giải trí/Phân tích dữ liệu/Dịch vụ đời sống

## Giới thiệu dự án

Mô tả ngắn gọn dự án của bạn (2-3 câu)

## Chức năng cốt lõi

- [ ] Chức năng 1
- [ ] Chức năng 2
- [ ] Chức năng 3

## Điểm nổi bật kỹ thuật

- Đã sử dụng mô hình XXX
- Đã hiện thực chức năng XXX
- Đã tối ưu hiệu năng XXX

## Hiệu quả trình diễn

(tùy chọn) Thêm ảnh chụp màn hình hoặc GIF để trình diễn hiệu quả dự án

## Danh sách tự kiểm tra

- [ ] Mã chạy được bình thường
- [ ] Tài liệu README đầy đủ
- [ ] requirements.txt đầy đủ
- [ ] Có ví dụ sử dụng rõ ràng
- [ ] Mã có chú thích phù hợp

## Ghi chú khác

(tùy chọn) Nội dung khác cần giải thích
```

<strong>Bước 4: Nộp PR</strong>

Như Hình 16.4, nhấp nút "Create pull request" để nộp.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/hello-agents/main/docs/images/16-figures/16-4.png" alt="" width="85%"/>
  <p>Hình 16.4 Nộp Pull Request</p>
</div>



### 16.5.3 Phản hồi ý kiến Review

Sau khi nộp PR, thành viên cộng đồng sẽ review mã của bạn và đưa ra gợi ý. Hãy phản hồi kịp thời:

1. <strong>Xem bình luận</strong>: Xem bình luận của reviewer trên trang PR
2. <strong>Sửa mã</strong>: Sửa mã theo gợi ý
3. <strong>Nộp cập nhật</strong>:
   ```bash
   git add .
   git commit -m "fix: Sửa XXX theo ý kiến review"
   git push origin feature/ten-du-an-cua-ban
   ```
4. <strong>Trả lời bình luận</strong>: Trả lời reviewer trên GitHub, giải thích thay đổi của bạn

## 16.6 Trình diễn dự án mẫu

Để giúp bạn hiểu rõ hơn yêu cầu của đồ án tốt nghiệp, ở đây trình diễn một dự án mẫu hoàn chỉnh. Đừng lo, những ý tưởng nhỏ cũng có thể được đưa vào; miễn là tác phẩm do chính bạn làm đều đáng trân trọng.

<strong>Thông tin dự án</strong>

- **Tên dự án**: CodeReviewAgent
- **Tác giả**: @jjyaoao
- **Đường dẫn dự án**: `Co-creation-projects/jjyaoao-CodeReviewAgent/`

<strong>Cấu trúc dự án</strong>

```
jjyaoao-CodeReviewAgent/
├── README.md              # Tài liệu dự án
├── requirements.txt       # Danh sách phụ thuộc
├── main.ipynb            # Chương trình chính (gồm trình diễn nhanh và chức năng đầy đủ)
├── .env.example          # Mẫu biến môi trường
├── .gitignore            # Quy tắc bỏ qua của Git
├── data/
│   └── sample_code.py    # Mã mẫu
└── outputs/
    └── review_report.md  # Báo cáo mẫu
```

<strong>Đoạn mã cốt lõi (main.ipynb)</strong>

```python
# ========================================
# Trợ lý đánh giá mã nguồn thông minh
# ========================================

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import Tool, ToolParameter
from typing import Dict, Any, List
import ast
import os

# ========================================
# 0. Cấu hình tham số LLM
# ========================================

os.environ["LLM_MODEL_ID"] = "Qwen/Qwen2.5-72B-Instruct"
os.environ["LLM_API_KEY"] = "your_api_key_here"
os.environ["LLM_BASE_URL"] = "https://api-inference.modelscope.cn/v1/"
os.environ["LLM_TIMEOUT"] = "60"

# ========================================
# 1. Định nghĩa công cụ phân tích mã
# ========================================

class CodeAnalysisTool(Tool):
    """Công cụ phân tích tĩnh mã nguồn"""

    def __init__(self):
        super().__init__(
            name="code_analysis",
            description="Phân tích cấu trúc, độ phức tạp và vấn đề tiềm ẩn của mã Python"
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """Phân tích mã và trả về kết quả"""
        code = parameters.get("code", "")
        if not code:
            return "Lỗi: mã không được để trống"

        try:
            tree = ast.parse(code)
            functions = [node for node in ast.walk(tree)
                        if isinstance(node, ast.FunctionDef)]
            classes = [node for node in ast.walk(tree)
                      if isinstance(node, ast.ClassDef)]

            result = {
                "Số hàm": len(functions),
                "Số lớp": len(classes),
                "Số dòng mã": len(code.split('\n')),
                "Danh sách hàm": [f.name for f in functions],
                "Danh sách lớp": [c.name for c in classes]
            }
            return str(result)
        except SyntaxError as e:
            return f"Lỗi cú pháp: {str(e)}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="Mã Python cần phân tích",
                required=True
            )
        ]

class StyleCheckTool(Tool):
    """Công cụ kiểm tra phong cách mã"""

    def __init__(self):
        super().__init__(
            name="style_check",
            description="Kiểm tra mã có tuân thủ chuẩn PEP 8 hay không"
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        """Kiểm tra phong cách mã"""
        code = parameters.get("code", "")
        if not code:
            return "Lỗi: mã không được để trống"

        issues = []
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 79:
                issues.append(f"Dòng {i}: vượt quá 79 ký tự")
            if line.startswith(' ') and not line.startswith('    '):
                if len(line) - len(line.lstrip()) not in [0, 4, 8, 12]:
                    issues.append(f"Dòng {i}: thụt lề không chuẩn")

        if not issues:
            return "Phong cách mã tốt, tuân thủ chuẩn PEP 8"
        return "Phát hiện các vấn đề sau:\n" + "\n".join(issues)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="Mã Python cần kiểm tra",
                required=True
            )
        ]

# ========================================
# 2. Tạo registry công cụ và Agent
# ========================================

# Tạo registry công cụ
tool_registry = ToolRegistry()
tool_registry.register_tool(CodeAnalysisTool())
tool_registry.register_tool(StyleCheckTool())

# Khởi tạo LLM
llm = HelloAgentsLLM()

# Định nghĩa system prompt
system_prompt = """Bạn là một chuyên gia đánh giá mã nguồn giàu kinh nghiệm. Nhiệm vụ của bạn là:

1. Dùng công cụ code_analysis để phân tích cấu trúc mã
2. Dùng công cụ style_check để kiểm tra phong cách mã
3. Dựa trên kết quả phân tích, cung cấp báo cáo đánh giá chi tiết

Báo cáo đánh giá nên bao gồm:
- Phân tích cấu trúc mã
- Vấn đề phong cách
- Lỗi tiềm ẩn
- Gợi ý tối ưu hiệu năng
- Gợi ý thực hành tốt nhất

Vui lòng xuất báo cáo dưới định dạng Markdown."""

# Tạo Agent
agent = SimpleAgent(
    name="Trợ lý đánh giá mã nguồn",
    llm=llm,
    system_prompt=system_prompt,
    tool_registry=tool_registry
)

# ========================================
# 3. Chạy ví dụ
# ========================================

# Đọc mã mẫu
with open("data/sample_code.py", "r", encoding="utf-8") as f:
    sample_code = f.read()

print("=== Mã cần đánh giá ===")
print(sample_code)
print("\n" + "="*50 + "\n")

# Thực thi đánh giá mã
print("=== Bắt đầu đánh giá mã ===")
review_result = agent.run(f"Vui lòng đánh giá mã Python sau:\n\n```python\n{sample_code}\n```")

print(review_result)

# Lưu báo cáo đánh giá
with open("outputs/review_report.md", "w", encoding="utf-8") as f:
    f.write(review_result)

print("\nBáo cáo đánh giá đã được lưu vào outputs/review_report.md")
```

<strong>Ví dụ README.md</strong>

```markdown
# CodeReviewAgent - Trợ lý đánh giá mã nguồn thông minh

> Công cụ đánh giá mã nguồn thông minh dựa trên framework HelloAgents

## 📝 Giới thiệu dự án

CodeReviewAgent là một trợ lý đánh giá mã nguồn thông minh, có thể tự động phân tích chất lượng mã Python, phát hiện vấn đề tiềm ẩn và đưa ra gợi ý tối ưu.

### Chức năng cốt lõi

- ✅ Phân tích cấu trúc mã: thống kê hàm, lớp, số dòng mã, v.v.
- ✅ Kiểm tra phong cách: kiểm tra xem có tuân thủ chuẩn PEP 8 hay không
- ✅ Gợi ý thông minh: dựa trên LLM để phân tích sâu và đưa ra gợi ý tối ưu
- ✅ Tạo báo cáo: tạo báo cáo đánh giá định dạng Markdown

## 🛠️ Ngăn xếp công nghệ

- Framework HelloAgents (SimpleAgent + ToolRegistry)
- Mô-đun AST của Python (phân tích mã)
- API ModelScope (mô hình Qwen2.5-72B)

## 🚀 Bắt đầu nhanh

### Cài đặt phụ thuộc

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### Cấu hình tham số LLM

**Cách 1: Dùng tệp .env**

\`\`\`bash
cp .env.example .env
# Chỉnh sửa tệp .env, điền API key của bạn
\`\`\`

**Cách 2: Đặt trực tiếp trong Notebook**

Dự án đã cấu hình sẵn API ModelScope, có thể chạy trực tiếp. Nếu cần sửa, hãy chỉnh mã cấu hình ở phần 1 của main.ipynb.

### Chạy dự án

\`\`\`bash
jupyter lab
# Mở main.ipynb và chạy tất cả các cell
\`\`\`

## 📖 Ví dụ sử dụng

1. Đặt mã cần đánh giá vào `data/sample_code.py`
2. Chạy `main.ipynb`
3. Xem báo cáo đánh giá được tạo tại `outputs/review_report.md`

## 🎯 Điểm nổi bật của dự án

- **Tự động hóa**: không cần kiểm tra thủ công từng dòng, tự động phát hiện vấn đề
- **Thông minh**: dùng LLM để hiểu ngữ nghĩa mã, đưa ra gợi ý sâu sắc
- **Có thể mở rộng**: dễ dàng thêm quy tắc kiểm tra và công cụ mới

## 👤 Tác giả

- GitHub: [@jjyaoao](https://github.com/jjyaoao)
- Liên kết dự án: [CodeReviewAgent](https://github.com/datawhalechina/hello-agents/tree/main/Co-creation-projects/jjyaoao-CodeReviewAgent)

## 🙏 Lời cảm ơn

Cảm ơn cộng đồng Datawhale và dự án Hello-Agents!
```



## 16.7 Tổng kết và triển vọng

Qua việc hoàn thành đồ án tốt nghiệp, bạn hẳn đã nắm được toàn bộ quy trình thiết kế hệ thống Agent. Từ yêu cầu đến thiết kế kiến trúc hệ thống; thành thạo các chức năng và thành phần khác nhau của framework HelloAgents; phát triển công cụ tùy chỉnh để mở rộng năng lực Agent; hoàn thành phát triển dự án trọn vẹn từ phân tích yêu cầu đến hiện thực mã; học cách dùng Git và GitHub để cộng tác mã nguồn mở; cũng như viết tài liệu kỹ thuật rõ ràng.

Trong dự án này, chúng ta đã xây dựng framework HelloAgents từ con số 0 và dùng nó để hiện thực nhiều ứng dụng hữu ích. Hoàn thành đồ án tốt nghiệp chỉ là khởi đầu; bạn có thể tiếp tục học sâu hơn các mô hình Agent và thuật toán, kỹ thuật prompt và kỹ thuật ngữ cảnh, cơ chế cộng tác đa Agent, v.v.; cũng có thể mở rộng ngăn xếp công nghệ, học phát triển Web để xây dựng ứng dụng hoàn chỉnh, học cơ sở dữ liệu để hiện thực lưu trữ dữ liệu, học triển khai để đưa ứng dụng lên mạng; còn có thể liên tục tối ưu dự án, thêm nhiều chức năng, tối ưu hiệu năng và trải nghiệm người dùng, hoàn thiện kiểm thử và tài liệu; quan trọng hơn, hãy tích cực đóng góp cho cộng đồng, giúp đỡ những người học khác, tham gia phát triển framework Hello-Agents, chia sẻ kinh nghiệm và hiểu biết của bạn.

Từ Agent đơn giản ở chương đầu tiên, đến nay có thể độc lập xây dựng ứng dụng đa Agent hoàn chỉnh, bạn đã đi qua một hành trình học tập tuyệt vời. Nhưng đây không phải điểm kết thúc, mà là khởi điểm mới.

Công nghệ AI thay đổi từng ngày, lĩnh vực Agent càng chứa đựng vô vàn khả năng. Hy vọng bạn giữ được sự tò mò để tiếp tục học công nghệ mới, dũng cảm dùng công nghệ AI giải quyết vấn đề thực tế và tạo ra giá trị, sẵn lòng chia sẻ kinh nghiệm và thành quả của mình với cộng đồng, không ngừng trau chuốt tác phẩm để hướng tới sự xuất sắc.

Cuối cùng, cảm ơn bạn đã đọc trọn vẹn dự án này. Hy vọng bạn thu hoạch được điều gì đó trong quá trình học, và có thể áp dụng những gì đã học vào dự án thực tế, tạo ra những ứng dụng Agent đáng kinh ngạc. Tương lai của AI tràn đầy khả năng, hãy cùng nhau khám phá và sáng tạo!

<strong>Hãy nhớ: cách học tốt nhất chính là thực hành!</strong>

Bây giờ, hãy bắt đầu xây dựng ứng dụng Agent của riêng bạn! Chúng tôi mong được thấy tác phẩm tuyệt vời của bạn trong thư mục Co-creation-projects!

Nếu bạn thấy dự án Hello-Agents hữu ích, hãy cho chúng tôi một ⭐Star!

---
<div align="center">
  <strong>🎓 Chúc mừng bạn đã hoàn thành khóa học Hello-Agents! 🎉</strong>
</div>

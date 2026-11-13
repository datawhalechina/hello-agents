# Chương 12: Đánh giá hiệu năng Agent

Trong các chương trước, chúng ta đã xây dựng các chức năng cốt lõi của framework HelloAgents, hiện thực nhiều mẫu hình Agent, hệ thống công cụ, cơ chế bộ nhớ và huấn luyện học tăng cường, v.v. Khi xây dựng hệ thống Agent, chúng ta còn cần giải quyết một vấn đề cốt lõi: <strong>làm sao đánh giá hiệu năng của Agent một cách khách quan?</strong> Cụ thể, chúng ta cần trả lời các câu hỏi sau:

1. Agent có sở hữu năng lực như kỳ vọng hay không?
2. Hiệu quả của nó trên các nhiệm vụ khác nhau ra sao?
3. So với các Agent khác, nó đang ở mức nào?

Chương này sẽ bổ sung cho HelloAgents một <strong>hệ thống đánh giá hiệu năng (Evaluation System)</strong>. Chúng ta sẽ hiểu sâu nền tảng lý thuyết của đánh giá Agent, và hiện thực các công cụ đánh giá.

## 12.1 Nền tảng đánh giá Agent

### 12.1.1 Vì sao cần đánh giá Agent

SimpleAgent hiện tại của chúng ta đã có năng lực suy luận và gọi công cụ mạnh mẽ. Hãy xem một ca sử dụng điển hình:

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import SearchTool

# Tạo LLM và Agent
llm = HelloAgentsLLM()

# Tạo một system prompt nhấn mạnh việc sử dụng công cụ
system_prompt = """Bạn là một trợ lý AI, có thể dùng công cụ tìm kiếm để lấy thông tin mới nhất.

Khi cần tìm kiếm thông tin, vui lòng dùng định dạng sau:
[TOOL_CALL:search:từ khóa tìm kiếm]

Ví dụ:
- [TOOL_CALL:search:tin tức AI mới nhất]
- [TOOL_CALL:search:hướng dẫn lập trình Python]

Hãy dùng công cụ tìm kiếm để lấy thông tin mới nhất trước khi trả lời câu hỏi."""

agent = SimpleAgent(name="Trợ lý AI", llm=llm, system_prompt=system_prompt)

# Thêm công cụ tìm kiếm
agent.add_tool(SearchTool())

# Ví dụ: dùng công cụ tìm kiếm để trả lời câu hỏi
response = agent.run("Xu hướng phát triển công nghệ AI mới nhất là gì?")
print(f"\nCâu trả lời: {response}")
```

Agent này có thể hoạt động bình thường, nhưng chúng ta đối mặt với một vấn đề cốt lõi: làm sao đánh giá hiệu năng của nó một cách khách quan? Khi chúng ta tối ưu prompt hoặc thay đổi mô hình LLM, làm sao biết có thực sự cải thiện hay không? Trước khi triển khai vào môi trường sản xuất, làm sao đảm bảo độ tin cậy của Agent? Những vấn đề này đều cần được giải quyết bằng đánh giá có hệ thống.

Giá trị cốt lõi của đánh giá Agent nằm ở việc cung cấp phương pháp chuẩn hóa để đo lường năng lực của Agent. Thông qua đánh giá, chúng ta có thể dùng các chỉ số số học cụ thể để định lượng hiệu năng của Agent, so sánh khách quan ưu nhược điểm của các phương án thiết kế khác nhau, kịp thời phát hiện điểm yếu của Agent trong các kịch bản cụ thể, và chứng minh độ tin cậy của Agent với người dùng.

Khác với kiểm thử phần mềm truyền thống, đánh giá Agent đối mặt với những thách thức đặc thù. Thứ nhất là tính không xác định của đầu ra: cùng một câu hỏi có thể có nhiều đáp án đúng, rất khó phán đoán đúng sai bằng cách đơn giản. Thứ hai là tính đa dạng của tiêu chí đánh giá: các nhiệm vụ khác nhau cần phương pháp đánh giá khác nhau; gọi công cụ cần kiểm tra chữ ký hàm, còn nhiệm vụ hỏi đáp cần đánh giá độ tương đồng ngữ nghĩa. Cuối cùng là chi phí đánh giá cao: mỗi lần đánh giá cần lượng lớn lệnh gọi API, chi phí có thể lên tới hàng trăm tệ hoặc hơn.

Để ứng phó những thách thức này, giới học thuật và công nghiệp đã đề xuất nhiều <strong>benchmark</strong> chuẩn hóa. Các benchmark này cung cấp tập dữ liệu, chỉ số đánh giá và phương pháp chấm điểm thống nhất, cho phép chúng ta đánh giá và so sánh các hệ thống Agent khác nhau dưới cùng một tiêu chuẩn.

### 12.1.2 Tổng quan các benchmark đánh giá chủ lưu

Lĩnh vực đánh giá Agent đã xuất hiện nhiều bài kiểm thử benchmark có ảnh hưởng. Dưới đây giới thiệu một số benchmark và chỉ số đánh giá chủ lưu:

<strong>(1) Đánh giá năng lực gọi công cụ</strong>

Gọi công cụ là một trong những năng lực cốt lõi của Agent. Agent cần hiểu ý định người dùng, chọn công cụ phù hợp và cấu trúc lệnh gọi hàm một cách chính xác. Các benchmark liên quan gồm:

- <strong>BFCL (Berkeley Function Calling Leaderboard)</strong><sup>[1]</sup>: do UC Berkeley đề xuất, gồm 1120+ mẫu kiểm thử, bao phủ bốn hạng mục simple, multiple, parallel, irrelevance, dùng thuật toán so khớp AST để đánh giá, quy mô tập dữ liệu vừa phải, cộng đồng sôi động.
- <strong>ToolBench</strong><sup>[2]</sup>: do Đại học Thanh Hoa đề xuất, gồm 16000+ kịch bản gọi API thực tế, bao phủ các kịch bản sử dụng công cụ phức tạp trong thế giới thực.
- <strong>API-Bank</strong><sup>[3]</sup>: do Microsoft Research đề xuất, gồm 53 công cụ API thông dụng, tập trung đánh giá năng lực hiểu và gọi tài liệu API của Agent.

<strong>(2) Đánh giá năng lực tổng quát</strong>

Đánh giá hiệu suất tổng hợp của Agent trong các nhiệm vụ thế giới thực, bao gồm suy luận nhiều bước, vận dụng tri thức, hiểu đa phương thức, v.v.:

- <strong>GAIA (General AI Assistants)</strong><sup>[4]</sup>: do Meta AI và Hugging Face đồng đề xuất, gồm 466 câu hỏi thế giới thực, chia thành ba mức độ khó Level 1/2/3, đánh giá năng lực suy luận nhiều bước, sử dụng công cụ, xử lý tệp, duyệt web, dùng thuật toán khớp gần đúng chính xác (Quasi Exact Match), nhiệm vụ chân thực và có tính tổng hợp cao.
- <strong>AgentBench</strong><sup>[5]</sup>: do Đại học Thanh Hoa đề xuất, gồm 8 nhiệm vụ thuộc các lĩnh vực khác nhau, đánh giá toàn diện năng lực tổng quát của Agent.
- <strong>WebArena</strong><sup>[6]</sup>: do CMU đề xuất, đánh giá năng lực hoàn thành nhiệm vụ và tương tác trang web của Agent trong môi trường web thực tế.

<strong>(3) Đánh giá cộng tác đa Agent</strong>

Đánh giá năng lực phối hợp làm việc của nhiều Agent:

- <strong>ChatEval</strong><sup>[7]</sup>: đánh giá chất lượng hệ thống đối thoại đa Agent.
- <strong>SOTOPIA</strong><sup>[8]</sup>: đánh giá năng lực tương tác của Agent trong các kịch bản xã hội.
- <strong>Kịch bản cộng tác tùy biến</strong>: các nhiệm vụ đánh giá được thiết kế theo kịch bản ứng dụng cụ thể.

<strong>(4) Các chỉ số đánh giá thông dụng</strong>

Các benchmark khác nhau dùng chỉ số đánh giá khác nhau, phổ biến gồm:

- <strong>Chỉ số độ chính xác</strong>: Accuracy (độ chính xác), Exact Match (khớp chính xác), F1 Score (điểm F1), dùng để đo tính đúng đắn của câu trả lời.
- <strong>Chỉ số hiệu quả</strong>: Response Time (thời gian phản hồi), Token Usage (lượng token sử dụng), dùng để đo hiệu quả thực thi.
- <strong>Chỉ số độ bền vững</strong>: Error Rate (tỷ lệ lỗi), Failure Recovery (khôi phục sau sự cố), dùng để đo năng lực chịu lỗi.
- <strong>Chỉ số cộng tác</strong>: Communication Efficiency (hiệu quả giao tiếp), Task Completion (mức hoàn thành nhiệm vụ), dùng để đo hiệu quả cộng tác.

### 12.1.3 Thiết kế hệ thống đánh giá HelloAgents

Xét đến đường cong học tập và tính thực dụng, chương này sẽ tập trung giới thiệu các kịch bản đánh giá sau:

1. <strong>BFCL</strong>: đánh giá năng lực gọi công cụ
   - Lý do lựa chọn: quy mô tập dữ liệu vừa phải, chỉ số đánh giá rõ ràng, cộng đồng sôi động
   - Kịch bản áp dụng: đánh giá độ chính xác gọi hàm của Agent

2. <strong>GAIA</strong>: đánh giá năng lực trợ lý AI tổng quát
   - Lý do lựa chọn: nhiệm vụ chân thực, phân cấp độ khó, tính tổng hợp cao
   - Kịch bản áp dụng: đánh giá năng lực giải quyết vấn đề tổng hợp của Agent

3. <strong>Đánh giá chất lượng sinh dữ liệu</strong>: đánh giá chất lượng dữ liệu do LLM sinh ra
   - Lý do lựa chọn: qua ca này có thể trải nghiệm trọn vẹn cách dùng Agent để tạo dữ liệu, cùng bản minh họa đầy đủ về đánh giá dữ liệu.
   - Kịch bản áp dụng: đánh giá chất lượng dữ liệu huấn luyện, dữ liệu kiểm thử được sinh ra
   - Phương pháp đánh giá: LLM Judge, Win Rate, xác minh thủ công

Qua ba kịch bản đánh giá này, chúng ta sẽ xây dựng một hệ thống đánh giá hoàn chỉnh; Hình 12.1 trình bày tư duy xây dựng hệ thống đánh giá của chúng ta.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-1.png" alt="" width="85%"/>
  <p>Hình 12.1 Sơ đồ kiến trúc hệ thống đánh giá HelloAgents</p>
</div>



### 12.1.4 Mục tiêu học tập của chương và trải nghiệm nhanh

Trước tiên hãy xem nội dung học tập của chương 12:

```
hello_agents/
├── evaluation/                         # Mô-đun đánh giá
│   └── benchmarks/                     # Hiện thực các benchmark đánh giá
│       ├── bfcl/                       # Hiện thực đánh giá BFCL
│       │   ├── dataset.py              # Bộ nạp tập dữ liệu BFCL
│       │   ├── evaluator.py            # Bộ đánh giá BFCL (so khớp AST)
│       │   ├── metrics.py              # Chỉ số dành riêng cho BFCL
│       │   └── ast_matcher.py          # Thuật toán so khớp AST
│       ├── gaia/                       # Hiện thực đánh giá GAIA
│       │   ├── dataset.py              # Bộ nạp tập dữ liệu GAIA
│       │   ├── evaluator.py            # Bộ đánh giá GAIA (khớp gần đúng chính xác)
│       │   ├── metrics.py              # Chỉ số dành riêng cho GAIA
│       │   └── quasi_exact_match.py    # Thuật toán khớp gần đúng chính xác
│       └── data_generation/            # Hiện thực đánh giá sinh dữ liệu
│           ├── dataset.py              # Bộ nạp tập dữ liệu AIME
│           ├── llm_judge.py            # Bộ đánh giá LLM Judge
│           └── win_rate.py             # Bộ đánh giá Win Rate
└── tools/builtin/                      # Mô-đun công cụ tích hợp
    ├── bfcl_evaluation_tool.py         # Công cụ đánh giá BFCL
    ├── gaia_evaluation_tool.py         # Công cụ đánh giá GAIA
    ├── llm_judge_tool.py               # Công cụ LLM Judge
    └── win_rate_tool.py                # Công cụ Win Rate
```

Với nội dung chương này, mục tiêu học tập là nắm vững năng lực vận dụng công cụ đánh giá. Trước tiên hãy chuẩn bị môi trường phát triển:

```bash
# Cài đặt framework HelloAgents (phiên bản chương 12)
pip install "hello-agents[evaluation]==0.2.7"

# Thiết lập biến môi trường
export HF_TOKEN="your_huggingface_token"     # Dùng cho tập dữ liệu GAIA (các bước thiết lập cũng sẽ có sau)

# Do gói chính thức `bfcl-eval` bắt buộc numpy<=2.0.0, xung đột với phiên bản phụ thuộc chính của HelloAgents, nên cần cài riêng
pip install "numpy==1.26.4" bfcl-eval
```

Trong các mục tiếp theo, chúng ta sẽ đi sâu vào cách dùng và giới thiệu chi tiết của từng phương pháp đánh giá.

## 12.2 BFCL: Đánh giá năng lực gọi công cụ

### 12.2.1 Giới thiệu benchmark BFCL

BFCL (Berkeley Function Calling Leaderboard) là benchmark đánh giá năng lực gọi hàm do Đại học California, Berkeley đề xuất<sup>[1]</sup>. Trong hệ thống Agent, gọi công cụ (Tool Calling) là một trong những năng lực cốt lõi. Agent cần hoàn thành các nhiệm vụ sau:

1. <strong>Hiểu yêu cầu nhiệm vụ</strong>: trích xuất thông tin then chốt từ mô tả ngôn ngữ tự nhiên của người dùng
2. <strong>Chọn công cụ phù hợp</strong>: chọn công cụ phù hợp nhất từ tập công cụ khả dụng
3. <strong>Cấu trúc lệnh gọi hàm</strong>: điền đúng tên hàm và tham số
4. <strong>Xử lý kịch bản phức tạp</strong>: hỗ trợ các kịch bản nâng cao như gọi nhiều hàm, gọi song song

Benchmark BFCL gồm bốn hạng mục đánh giá với độ khó tăng dần. Bắt đầu từ gọi một hàm đơn giản nhất (Simple), tăng dần đến kịch bản cần gọi nhiều hàm (Multiple), rồi đến kịch bản phức tạp cần gọi song song nhiều hàm (Parallel), cuối cùng là kịch bản cần phán đoán có cần gọi hàm hay không (Irrelevance). Bốn hạng mục này bao phủ các kịch bản gọi công cụ khác nhau mà Agent có thể gặp trong ứng dụng thực tế, như Bảng 12.1 minh họa:

<div align="center">
  <p>Bảng 12.1 Bốn hạng mục đánh giá trong benchmark BFCL</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-table-1.png" alt="" width="85%"/>
</div>
Quy trình đánh giá của BFCL theo quy trình kiểm thử benchmark tiêu chuẩn: trước tiên nạp tập dữ liệu và chọn hạng mục đánh giá, sau đó chạy Agent để lấy kết quả dự đoán, tiếp theo phân tích kết quả dự đoán thành cây cú pháp trừu tượng (AST), cuối cùng qua thuật toán so khớp AST để phán đoán dự đoán có đúng hay không. Toàn bộ quy trình duyệt qua mọi mẫu kiểm thử, cuối cùng tính các chỉ số đánh giá như độ chính xác và sinh báo cáo đánh giá. Quy trình đánh giá hoàn chỉnh như Hình 12.2:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-2.png" alt="" width="85%"/>
  <p>Hình 12.2 Sơ đồ quy trình đánh giá BFCL</p>
</div>
<strong>(1) Cấu trúc tập dữ liệu BFCL</strong>

Tập dữ liệu BFCL dùng định dạng JSON, mỗi mẫu kiểm thử gồm các trường sau:

```json
{
  "id": "simple_001",
  "question": "What's the weather like in Beijing today?",
  "function": [
    {
      "name": "get_weather",
      "description": "Get the current weather for a location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "The city name"
          }
        },
        "required": ["location"]
      }
    }
  ],
  "ground_truth": [
    {
      "name": "get_weather",
      "arguments": {
        "location": "Beijing"
      }
    }
  ]
}
```

<strong>Mô tả các trường then chốt:</strong>

- `question`: yêu cầu ngôn ngữ tự nhiên của người dùng
- `function`: danh sách hàm khả dụng (gồm chữ ký hàm và mô tả)
- `ground_truth`: đáp án chuẩn (lệnh gọi hàm kỳ vọng)

<strong>(2) Mô tả so khớp AST</strong>

BFCL dùng <strong>so khớp AST (Abstract Syntax Tree Matching)</strong> làm thuật toán đánh giá cốt lõi, vì vậy phần dưới đây sẽ giúp bạn hiểu chiến lược đánh giá này.

BFCL dùng cây cú pháp trừu tượng (AST) để so khớp thông minh thay vì so khớp chuỗi đơn giản. Tư tưởng cốt lõi của so khớp AST là: <strong>phân tích lệnh gọi hàm thành cây cú pháp, sau đó so sánh cấu trúc và giá trị nút của cây</strong>.

Cho lệnh gọi hàm dự đoán $P$ và đáp án chuẩn $G$, hàm so khớp AST được định nghĩa là:

$$
\text{AST\_Match}(P, G) = \begin{cases}
1 & \text{if } \text{AST}(P) \equiv \text{AST}(G) \\
0 & \text{otherwise}
\end{cases}
$$

Trong đó $\text{AST}(x)$ biểu thị việc phân tích lệnh gọi hàm thành cây cú pháp trừu tượng, $\equiv$ biểu thị hai cây cú pháp tương đương.

Hai cây cú pháp tương đương cần thỏa mãn ba điều kiện cốt lõi: tên hàm phải hoàn toàn nhất quán (khớp chính xác), tập cặp khóa-giá trị tham số bằng nhau (bỏ qua thứ tự), và giá trị của mỗi tham số tương đương về ngữ nghĩa (ví dụ `2+3` tương đương `5`). Trong quá trình so khớp cụ thể, khớp tên hàm yêu cầu chuỗi khớp chính xác, ví dụ `get_weather` và `get_temperature` được coi là hai hàm khác nhau. Khớp tham số thì dùng AST để so sánh thông minh, cho phép thứ tự tham số khác nhau (`f(a=1, b=2)` tương đương `f(b=2, a=1)`), cho phép biểu thức tương đương (`f(x=2+3)` tương đương `f(x=5)`), cũng cho phép cách biểu diễn chuỗi khác nhau (`f(s="hello")` tương đương `f(s='hello')`). Với kịch bản gọi nhiều hàm, thuật toán so khớp yêu cầu số lượng hàm được gọi bằng nhau, mỗi lệnh gọi hàm đều phải khớp, nhưng thứ tự gọi có thể khác nhau (dùng so khớp tập hợp).

<strong>Ví dụ so khớp AST:</strong>

```python
# Ví dụ 1: thứ tự tham số khác nhau (khớp thành công)
Dự đoán: get_weather(city="Beijing", unit="celsius")
Chuẩn: get_weather(unit="celsius", city="Beijing")
Kết quả: ✅ Khớp thành công

# Ví dụ 2: biểu thức tương đương (khớp thành công)
Dự đoán: calculate(x=2+3)
Chuẩn: calculate(x=5)
Kết quả: ✅ Khớp thành công

# Ví dụ 3: tên hàm sai (khớp thất bại)
Dự đoán: get_temperature(city="Beijing")
Chuẩn: get_weather(city="Beijing")
Kết quả: ❌ Khớp thất bại

# Ví dụ 4: giá trị tham số sai (khớp thất bại)
Dự đoán: get_weather(city="Shanghai")
Chuẩn: get_weather(city="Beijing")
Kết quả: ❌ Khớp thất bại
```

<strong>(3) Chỉ số đánh giá BFCL</strong>

BFCL dùng các chỉ số sau để đánh giá hiệu năng Agent:

<strong>1. Độ chính xác (Accuracy)</strong>

Độ chính xác là chỉ số cốt lõi nhất, được định nghĩa là tỷ lệ mẫu so khớp AST thành công:

$$
\text{Accuracy} = \frac{1}{N} \sum_{i=1}^{N} \text{AST\_Match}(P_i, G_i)
$$

Trong đó:
- $N$ là tổng số mẫu
- $P_i$ là kết quả dự đoán của mẫu thứ $i$
- $G_i$ là đáp án chuẩn của mẫu thứ $i$
- $\text{AST\_Match}(P_i, G_i) \in \{0, 1\}$ là hàm so khớp AST

<strong>2. Tỷ lệ so khớp AST (AST Match Rate)</strong>

Giống với độ chính xác, nhấn mạnh việc dùng thuật toán so khớp AST:

$$
\text{AST Match Rate} = \text{Accuracy}
$$

<strong>3. Độ chính xác theo hạng mục (Category-wise Accuracy)</strong>

Với mỗi hạng mục $c \in \{\text{simple}, \text{multiple}, \text{parallel}, \ldots\}$, tính độ chính xác của hạng mục đó:

$$
\text{Accuracy}_c = \frac{1}{|D_c|} \sum_{i \in D_c} \text{AST\_Match}(P_i, G_i)
$$

Trong đó $D_c$ là tập mẫu của hạng mục $c$, $|D_c|$ là số mẫu của hạng mục đó.

<strong>4. Độ chính xác có trọng số (Weighted Accuracy)</strong>

Xét trọng số độ khó của các hạng mục khác nhau:

$$
\text{Weighted Accuracy} = \sum_{c} w_c \cdot \text{Accuracy}_c
$$

Trong đó $w_c$ là trọng số của hạng mục $c$, thỏa mãn $\sum_c w_c = 1$.

<strong>5. Tỷ lệ lỗi (Error Rate)</strong>

Tỷ lệ mẫu không gọi hàm đúng:

$$
\text{Error Rate} = 1 - \text{Accuracy} = \frac{1}{N} \sum_{i=1}^{N} (1 - \text{AST\_Match}(P_i, G_i))
$$

<strong>Giải thích chỉ số:</strong>

- <strong>Accuracy = 1.0</strong>: tất cả mẫu đều hoàn toàn đúng
- <strong>Accuracy = 0.8</strong>: 80% mẫu đúng, 20% mẫu sai
- <strong>Accuracy = 0.0</strong>: tất cả mẫu đều sai

<strong>Ví dụ độ chính xác theo hạng mục:</strong>

```python
# Giả sử kết quả đánh giá
simple_accuracy = 0.95      # Hạng mục Simple: 95% đúng
multiple_accuracy = 0.82    # Hạng mục Multiple: 82% đúng
parallel_accuracy = 0.68    # Hạng mục Parallel: 68% đúng

# Độ chính xác có trọng số (giả sử trọng số bằng nhau)
weighted_accuracy = (0.95 + 0.82 + 0.68) / 3 = 0.817
```

<strong>(4) Công cụ đánh giá chính thức BFCL</strong>

BFCL cung cấp công cụ CLI chính thức để đánh giá:

```bash
# Cài đặt công cụ đánh giá BFCL
pip install bfcl

# Chạy đánh giá chính thức
bfcl evaluate \
    --model-result-path ./results.json \
    --test-category simple_python
```

Ưu thế của việc dùng công cụ đánh giá chính thức là: nó dùng thuật toán so khớp AST chính thức, kết quả đánh giá hoàn toàn nhất quán với bảng xếp hạng, hỗ trợ tất cả hạng mục BFCL v4, và có thể tự động sinh báo cáo đánh giá chi tiết.


### 12.2.2 Lấy tập dữ liệu BFCL

Tập dữ liệu BFCL có thể lấy theo các cách sau:

<strong>Cách 1: clone từ kho GitHub chính thức (khuyến nghị)</strong>

Đây là cách đáng tin cậy nhất, có thể lấy tập dữ liệu đầy đủ và ground truth:

```bash
# Clone kho BFCL
git clone https://github.com/ShishirPatil/gorilla.git temp_gorilla
cd temp_gorilla/berkeley-function-call-leaderboard

# Xem tập dữ liệu BFCL v4
ls bfcl_eval/data/
# Đầu ra: BFCL_v4_simple_python.json  BFCL_v4_multiple.json  BFCL_v4_parallel.json  ...

# Xem ground truth
ls bfcl_eval/data/possible_answer/
# Đầu ra: BFCL_v4_simple_python.json  BFCL_v4_multiple.json  ...
```

Lý do khuyến nghị cách này: nó chứa ground truth (đáp án chuẩn) đầy đủ, định dạng dữ liệu hoàn toàn nhất quán với công cụ đánh giá chính thức, có thể dùng trực tiếp script đánh giá chính thức, và hỗ trợ phiên bản mới nhất BFCL v4.

<strong>Cách 2: dùng HelloAgents nạp dữ liệu chính thức</strong>

Sau khi clone kho, dùng HelloAgents nạp dữ liệu:

```python
from hello_agents.evaluation import BFCLDataset

# Nạp dữ liệu BFCL chính thức
dataset = BFCLDataset(
    bfcl_data_dir="./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data",
    category="simple_python"  # Hạng mục BFCL v4
)

# Nạp dữ liệu (gồm dữ liệu kiểm thử và ground truth)
data = dataset.load()

print(f"✅ Đã nạp {len(data)} mẫu kiểm thử")
print(f"✅ Đã nạp {len(dataset.ground_truth)} ground truth")
# Đầu ra:
# ✅ Đã nạp 400 mẫu kiểm thử
# ✅ Đã nạp 400 ground truth
```

Nguyên lý hoạt động của bộ nạp này là: trước tiên nạp dữ liệu kiểm thử từ `bfcl_eval/data/`, sau đó nạp ground truth từ `bfcl_eval/data/possible_answer/`, tiếp theo tự động hợp nhất dữ liệu kiểm thử và ground truth, cuối cùng giữ nguyên định dạng dữ liệu BFCL gốc. Các hạng mục của tập dữ liệu BFCL v4 có thể xem ở Bảng 12.2.

<div align="center">
  <p>Bảng 12.2 Bốn hạng mục đánh giá trong benchmark BFCL</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-table-2.png" alt="" width="85%"/>
</div>

Tất nhiên cũng có thể xem các hạng mục khả dụng bằng mã:

```python
# Lấy tất cả hạng mục được hỗ trợ
categories = dataset.get_available_categories()
print(f"Các hạng mục được hỗ trợ: {categories}")
# Đầu ra: ['simple_python', 'simple_java', 'simple_javascript', 'multiple', ...]
```

### 12.2.3 Hiện thực đánh giá BFCL trong HelloAgents

Giờ hãy xem cách hiện thực đánh giá BFCL trong framework HelloAgents. Chúng ta cung cấp ba cách sử dụng:

<strong>Cách 1: dùng BFCLEvaluationTool (khuyến nghị)</strong>

Đây là cách đơn giản nhất, một dòng mã hoàn thành đánh giá, sinh báo cáo và đánh giá chính thức:

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import BFCLEvaluationTool

# 1. Tạo Agent cần đánh giá
llm = HelloAgentsLLM()
agent = SimpleAgent(name="TestAgent", llm=llm)

# 2. Tạo công cụ đánh giá BFCL
bfcl_tool = BFCLEvaluationTool()

# 3. Chạy đánh giá (tự động hoàn thành tất cả các bước)
results = bfcl_tool.run(
    agent=agent,
    category="simple_python",  # Hạng mục đánh giá
    max_samples=5              # Số mẫu đánh giá (0 nghĩa là tất cả)
)

# 4. Xem kết quả
print(f"Độ chính xác: {results['overall_accuracy']:.2%}")
print(f"Số mẫu đúng: {results['correct_samples']}/{results['total_samples']}")
```

<strong>Đầu ra khi chạy:</strong>

```
============================================================
Đánh giá một chạm BFCL
============================================================

Cấu hình:
   Hạng mục đánh giá: simple_python
   Số lượng mẫu: 5
   Agent: TestAgent

============================================================
Bước 1: Chạy đánh giá HelloAgents
============================================================
✅ Nạp tập dữ liệu BFCL hoàn tất
   Thư mục dữ liệu: ./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data
   Hạng mục: simple_python
   Số mẫu: 400
   Số ground truth: 400

🔧 Bắt đầu đánh giá BFCL...
   Tiến độ: 1/5
   Tiến độ: 5/5

✅ Đánh giá BFCL hoàn tất
   Độ chính xác tổng thể: 100.00%
   simple_python: 100.00% (5/5)

📊 Kết quả đánh giá:
   Độ chính xác: 100.00%
   Số mẫu đúng: 5/5

============================================================
Bước 2: Xuất kết quả định dạng BFCL
============================================================
✅ Đã xuất kết quả định dạng BFCL
   Tệp đầu ra: ./evaluation_results/bfcl_official/BFCL_v4_simple_python_result.json

============================================================
Bước 3: Chạy đánh giá BFCL chính thức
============================================================
✅ Đã sao chép tệp kết quả tới: ./result/Qwen_Qwen3-8B/BFCL_v4_simple_python_result.json

🔄 Chạy lệnh: bfcl evaluate --model Qwen/Qwen3-8B --test-category simple_python --partial-eval

============================================================
Kết quả đánh giá BFCL chính thức
============================================================
📊 Tổng hợp kết quả đánh giá:
Model,Overall Acc,simple_python
Qwen/Qwen3-8B,100.00,100.00

🎯 Kết quả cuối cùng:
   Độ chính xác: 100.00%
   Số mẫu đúng: 5/5

============================================================
Bước 4: Sinh báo cáo đánh giá
============================================================
📄 Báo cáo đã được sinh: ./evaluation_reports/bfcl_report_20251011_005938.md

Độ chính xác: 100.00%
Số mẫu đúng: 5/5
```

<strong>Báo cáo Markdown được sinh tự động:</strong>

Sau khi đánh giá hoàn tất, một báo cáo Markdown chi tiết sẽ được sinh tự động, bao gồm:

```markdown
# Báo cáo đánh giá BFCL
**Thời điểm sinh**: 2025-10-11 00:59:38

## 📊 Tổng quan đánh giá

- **Agent**: TestAgent
- **Hạng mục đánh giá**: simple_python
- **Độ chính xác tổng thể**: 100.00%
- **Số mẫu đúng**: 5/5

## 📈 Chỉ số chi tiết

### Độ chính xác theo hạng mục

- **simple_python**: 100.00% (5/5)

## 📝 Chi tiết mẫu

| ID mẫu | Câu hỏi | Kết quả dự đoán | Đáp án đúng | Có đúng không |
|--------|------|----------|----------|----------|
| simple_python_0 | Find the area of a triangle... | [{'name': 'calculate_triangle_area'...}] | [{'function_name': {'base': [10]...}}] | ✅ |
| simple_python_1 | Calculate the factorial of 5... | [{'name': 'calculate_factorial'...}] | [{'function_name': {'number': [5]}}] | ✅ |
...

## 📊 Trực quan hóa độ chính xác
Độ chính xác: ██████████████████████████████████████████████████ 100.00%

## 💡 Khuyến nghị
- ✅ Hiệu năng xuất sắc! Agent thể hiện rất tốt trong việc gọi công cụ.
```

<strong>Cách 2: Dùng script đánh giá một chạm</strong>

Phù hợp để đánh giá nhanh trên dòng lệnh; trong bộ mã ví dụ kèm chương này, chúng ta cung cấp `04_run_bfcl_evaluation.py`, hỗ trợ gọi đánh giá trực tiếp từ dòng lệnh:

```bash
# Chạy script đánh giá
python chapter12/04_run_bfcl_evaluation.py --category simple_python --samples 10

# Chỉ định tên mô hình (dùng cho đánh giá BFCL chính thức)
python examples/04_run_bfcl_evaluation.py \
    --category simple_python \
    --samples 10 \
    --model-name "Qwen/Qwen3-8B"
```

Script hỗ trợ ba tham số: `--category` chỉ định hạng mục đánh giá (mặc định simple_python), `--samples` chỉ định số mẫu đánh giá (mặc định 5, 0 nghĩa là tất cả), `--model-name` chỉ định tên mô hình dùng cho đánh giá BFCL chính thức (mặc định Qwen/Qwen3-8B).

<strong>Cách 3: Dùng trực tiếp Dataset và Evaluator</strong>

Phù hợp với kịch bản cần tùy biến quy trình đánh giá:

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.evaluation import BFCLDataset, BFCLEvaluator

# 1. Tạo Agent
llm = HelloAgentsLLM()
agent = SimpleAgent(name="TestAgent", llm=llm)

# 2. Nạp tập dữ liệu
dataset = BFCLDataset(
    bfcl_data_dir="./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data",
    category="simple_python"
)
data = dataset.load()

# 3. Tạo bộ đánh giá
evaluator = BFCLEvaluator(
    dataset=dataset,
    category="simple_python",
    evaluation_mode="ast"  # Dùng chế độ so khớp AST
)

# 4. Chạy đánh giá
results = evaluator.evaluate(agent, max_samples=10)

# 5. Xem kết quả
print(f"Độ chính xác: {results['overall_accuracy']:.2%}")
print(f"Số mẫu đúng: {results['correct_samples']}/{results['total_samples']}")

# 6. Xuất kết quả định dạng BFCL (tùy chọn)
evaluator.export_to_bfcl_format(
    results,
    output_path="./evaluation_results/my_results.json"
)
```

Qua ba cách trên, chúng ta có thể chọn phương pháp đánh giá phù hợp với nhu cầu khác nhau. Nếu chỉ muốn nhanh chóng biết biểu hiện của Agent, dùng đánh giá một chạm của BFCLEvaluationTool là tiện lợi nhất; nếu cần đánh giá hàng loạt hoặc tích hợp vào quy trình CI/CD, dùng script dòng lệnh sẽ phù hợp hơn; nếu cần tùy biến sâu quy trình đánh giá hoặc tích hợp vào hệ thống của mình, dùng trực tiếp Dataset và Evaluator mang lại độ linh hoạt lớn nhất.




### 12.2.4 Tích hợp công cụ đánh giá chính thức BFCL

Ở phần trước, chúng ta đã học cách dùng chức năng đánh giá tích hợp của HelloAgents. Trên thực tế, `BFCLEvaluationTool` đã <strong>tự động tích hợp công cụ đánh giá chính thức BFCL</strong>, giúp bạn có được kết quả đánh giá có thẩm quyền và có thể so sánh được.

Toàn bộ quy trình đánh giá gồm bốn bước: trước tiên nạp dữ liệu kiểm thử từ tập dữ liệu BFCL v4, sau đó dùng HelloAgents chạy đánh giá để lấy kết quả dự đoán của Agent, tiếp theo xuất kết quả sang định dạng chính thức của BFCL (JSONL), cuối cùng dùng script đánh giá chính thức để tính điểm cuối cùng. Quy trình này đảm bảo kết quả đánh giá hoàn toàn nhất quán với bảng xếp hạng BFCL, như Hình 12.3:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-3.png" alt="" width="85%"/>
  <p>Hình 12.3 Quy trình tải và đánh giá BFCL của Helloagents</p>
</div>
Khi dùng `BFCLEvaluationTool`, đánh giá chính thức sẽ <strong>tự động chạy</strong> (mặc định bật):

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import BFCLEvaluationTool

# Tạo Agent
llm = HelloAgentsLLM()
agent = SimpleAgent(name="TestAgent", llm=llm)

# Tạo công cụ đánh giá
bfcl_tool = BFCLEvaluationTool()

# Chạy đánh giá (tự động chạy đánh giá chính thức)
results = bfcl_tool.run(
    agent=agent,
    category="simple_python",
    max_samples=5,
    # run_official_eval=True  # Mặc định là True, có thể bỏ qua
    model_name="Qwen/Qwen3-8B"  # Tùy chọn, chỉ định tên mô hình
)
```

Công cụ sẽ tự động thực hiện quy trình đánh giá đầy đủ: trước tiên chạy đánh giá HelloAgents để lấy kết quả dự đoán, sau đó xuất kết quả sang định dạng BFCL và lưu vào thư mục `evaluation_results/bfcl_official/`, tiếp theo sao chép tệp kết quả vào thư mục `result/{model_name}/` để phù hợp yêu cầu của công cụ đánh giá chính thức, sau đó chạy lệnh đánh giá chính thức BFCL để tính điểm, cuối cùng hiển thị kết quả đánh giá chính thức và sinh báo cáo đánh giá định dạng Markdown.

<strong>Ví dụ đầu ra của đánh giá chính thức:</strong>

```
============================================================
Bước 3: Chạy đánh giá BFCL chính thức
============================================================

✅ Đã sao chép tệp kết quả tới:
   ./result/Qwen_Qwen3-8B/BFCL_v4_simple_python_result.json

🔄 Chạy lệnh: bfcl evaluate --model Qwen/Qwen3-8B --test-category simple_python --partial-eval

============================================================
Kết quả đánh giá BFCL chính thức
============================================================

📊 Tổng hợp kết quả đánh giá:
Model,Overall Acc,simple_python
Qwen/Qwen3-8B,100.00,100.00

🎯 Kết quả cuối cùng:
   Độ chính xác: 100.00%
   Số mẫu đúng: 5/5
```

Nếu bạn muốn tự kiểm soát quy trình đánh giá, có thể tắt đánh giá chính thức tự động:

```python
# Tắt đánh giá chính thức
results = bfcl_tool.run(
    agent=agent,
    category="simple_python",
    max_samples=5,
    run_official_eval=False  # Tắt đánh giá chính thức
)

# Sau đó tự chạy đánh giá chính thức
import subprocess
subprocess.run([
    "bfcl", "evaluate",
    "--model", "Qwen/Qwen3-8B",
    "--test-category", "simple_python",
    "--partial-eval"
])
```

Bạn cũng có thể tự sinh báo cáo:

```python
# Chạy đánh giá
results = bfcl_tool.run(agent, category="simple_python", max_samples=5)

# Tự sinh báo cáo
report = bfcl_tool.generate_report(
    results,
    output_file="./my_reports/custom_report.md"
)

# In nội dung báo cáo
print(report)
```



### 12.2.5 Chi tiết hiện thực các thành phần cốt lõi

Trong các mục trước, chúng ta đã học cách dùng công cụ đánh giá BFCL. Giờ hãy đi sâu tìm hiểu các thành phần cốt lõi của hệ thống đánh giá HelloAgents được hiện thực như thế nào. Hiểu các chi tiết hiện thực này không chỉ giúp bạn dùng hệ thống đánh giá tốt hơn, mà còn giúp bạn tùy biến và mở rộng theo nhu cầu của mình.

<strong>(1) BFCLDataset: bộ nạp tập dữ liệu</strong>

BFCLDataset chịu trách nhiệm nạp và quản lý tập dữ liệu BFCL:

````python
class BFCLDataset:
    """Bộ nạp tập dữ liệu BFCL"""

    def __init__(self, category: str = "simple", local_data_path: Optional[str] = None):
        self.category = category
        self.local_data_path = local_data_path
        self.data = []

    def load(self) -> List[Dict[str, Any]]:
        """Nạp tập dữ liệu"""
        # Ưu tiên nạp từ cục bộ
        if self.local_data_path:
            return self._load_from_local()
        # Ngược lại nạp từ Hugging Face
        return self._load_from_huggingface()
````
Vì tập dữ liệu BFCL nằm ngay trong kho chính thức, cách được khuyến nghị ở đây là clone một bản về cục bộ để đánh giá. Chỉ khi không tìm thấy mới nạp từ huggingface.

<strong>(2) BFCLEvaluator: bộ thực thi đánh giá</strong>

BFCLEvaluator chịu trách nhiệm thực thi quy trình đánh giá. Cốt lõi của nó là phương thức `evaluate()`, phương thức này điều phối toàn bộ quá trình đánh giá:

````python
class BFCLEvaluator:
    """Bộ đánh giá BFCL"""

    def evaluate(self, agent: Any, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """Thực hiện đánh giá"""
        results = []

        for item in self.dataset[:max_samples]:
            # 1. Dựng prompt
            prompt = self._build_prompt(item)

            # 2. Gọi Agent
            response = agent.run(prompt)

            # 3. Trích xuất lệnh gọi hàm
            predicted_calls = self._extract_function_calls(response)

            # 4. So sánh với đáp án chuẩn
            is_correct = self._compare_calls(predicted_calls, item["ground_truth"])

            results.append({
                "id": item["id"],
                "prediction": predicted_calls,
                "ground_truth": item["ground_truth"],
                "is_correct": is_correct
            })

        return {"results": results, "total_samples": len(results)}
````
Thiết kế của bộ đánh giá này gồm ba điểm cốt lõi: thứ nhất là dựng prompt, cần chuyển câu hỏi và định nghĩa hàm trong tập dữ liệu thành prompt mà Agent hiểu được; thứ hai là trích xuất lệnh gọi hàm, cần trích xuất lệnh gọi hàm từ phản hồi của Agent, hỗ trợ nhiều định dạng (JSON, khối mã, v.v.); cuối cùng là so khớp AST, dùng cây cú pháp trừu tượng để so sánh lệnh gọi hàm, chính xác hơn so khớp chuỗi đơn giản.

Hãy xem hiện thực của việc trích xuất lệnh gọi hàm:

```python
def _extract_function_calls(self, response: str) -> List[Dict[str, Any]]:
    """Trích xuất lệnh gọi hàm từ phản hồi

    Hỗ trợ nhiều định dạng:
    1. Định dạng JSON: {"name": "func", "arguments": {...}}
    2. Định dạng khối mã: ```python\nfunc(arg1=val1)\n```
    3. Định dạng văn bản thuần: func(arg1=val1)
    """
    calls = []

    # Thử phân tích JSON
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if isinstance(data, dict) and "name" in data:
                calls.append(data)
            elif isinstance(data, list):
                calls.extend(data)
    except json.JSONDecodeError:
        pass

    # Thử trích xuất từ khối mã
    code_blocks = re.findall(r'```(?:python)?\n(.*?)\n```', response, re.DOTALL)
    for code in code_blocks:
        # Phân tích lệnh gọi hàm Python
        parsed_calls = self._parse_python_calls(code)
        calls.extend(parsed_calls)

    return calls
```

<strong>(3) BFCLMetrics: bộ tính chỉ số</strong>

BFCLMetrics chịu trách nhiệm tính các chỉ số đánh giá khác nhau:

````python
class BFCLMetrics:
    """Bộ tính chỉ số BFCL"""

    def compute_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tính tất cả chỉ số"""
        return {
            "accuracy": self._compute_accuracy(results),
            "ast_match_rate": self._compute_ast_match_rate(results),
            "parameter_accuracy": self._compute_parameter_accuracy(results),
            "f1_score": self._compute_f1_score(results),
            "category_statistics": self._compute_category_stats(results)
        }
````
<strong>Hiện thực so khớp AST</strong>:

So khớp AST là kỹ thuật cốt lõi của đánh giá BFCL. Nó thông minh hơn so khớp chuỗi đơn giản, có khả năng nhận diện các lệnh gọi hàm tương đương về ngữ nghĩa:

```python
def _ast_match(self, pred_call: Dict, true_call: Dict) -> bool:
    """Dùng AST để so khớp lệnh gọi hàm

    Ưu điểm của so khớp AST:
    1. Bỏ qua thứ tự tham số: func(a=1, b=2) tương đương func(b=2, a=1)
    2. Nhận diện biểu thức tương đương: 2+3 tương đương 5
    3. Bỏ qua khác biệt khoảng trắng và định dạng
    """
    # 1. Tên hàm phải khớp hoàn toàn
    if pred_call.get("name") != true_call.get("name"):
        return False

    # 2. Chuyển tham số thành nút AST
    pred_args = self._args_to_ast(pred_call.get("arguments", {}))
    true_args = self._args_to_ast(true_call.get("arguments", {}))

    # 3. So sánh nút AST
    return ast.dump(pred_args) == ast.dump(true_args)

def _args_to_ast(self, args: Dict[str, Any]) -> ast.AST:
    """Chuyển dict tham số thành nút AST"""
    # Dựng một lệnh gọi hàm giả
    code = f"func({', '.join(f'{k}={repr(v)}' for k, v in args.items())})"
    tree = ast.parse(code)
    return tree.body[0].value  # Trả về nút Call
```

<strong>(4) Đóng gói thành công cụ: BFCLEvaluationTool</strong>

Cuối cùng, chúng ta đóng gói các thành phần này thành một Tool để Agent có thể gọi trực tiếp:

````python
class BFCLEvaluationTool(Tool):
    """Công cụ đánh giá BFCL"""

    def __init__(self, local_data_path: Optional[str] = None):
        super().__init__(
            name="bfcl_evaluation",
            description="Đánh giá năng lực gọi công cụ của Agent"
        )
        self.dataset = None
        self.evaluator = None
        self.metrics_calculator = BFCLMetrics()

    def run(self, parameters: Dict[str, Any]) -> str:
        """Thực hiện đánh giá"""
        # 1. Nạp tập dữ liệu
        self.dataset = BFCLDataset(...)

        # 2. Tạo bộ đánh giá
        self.evaluator = BFCLEvaluator(...)

        # 3. Chạy đánh giá
        results = self.evaluator.evaluate(...)

        # 4. Tính chỉ số
        metrics = self.metrics_calculator.compute_metrics(...)

        # 5. Trả về kết quả JSON
        return json.dumps(results, ensure_ascii=False)
````
Thiết kế của công cụ này tuân theo ba nguyên tắc cốt lõi: thứ nhất kế thừa lớp cơ sở Tool để tuân thủ quy chuẩn công cụ của HelloAgents, đảm bảo tích hợp liền mạch với framework; thứ hai thực hiện kiểm tra tham số nghiêm ngặt, kiểm tra tham số bắt buộc và đưa ra thông báo lỗi thân thiện, nâng cao trải nghiệm người dùng; cuối cùng định dạng kết quả, trả về chuỗi JSON để dễ phân tích và hiển thị. Qua thiết kế mô-đun hóa này, chúng ta hiện thực một hệ thống đánh giá vừa dễ dùng vừa linh hoạt: người dùng có thể dùng trực tiếp giao diện Tool cấp cao để nhanh chóng hoàn thành đánh giá, cũng có thể đi sâu vào các thành phần tầng dưới để tùy biến nhằm đáp ứng nhu cầu đặc biệt.

### 12.2.6 Khuyến nghị mở rộng và tối ưu

Qua phần học trước, chúng ta đã nắm cách dùng HelloAgents để đánh giá BFCL. Cần lưu ý, hiện thực hiện tại của chúng ta là bản tái hiện đơn giản dựa trên SimpleAgent, chủ yếu hoàn thành các chức năng cơ bản của đánh giá BFCL. Trong ứng dụng thực tế, benchmark BFCL bao gồm nhiều mức độ khó và kịch bản; để đạt điểm cao hơn trên bảng xếp hạng, cần tối ưu và mở rộng thêm.

<strong>(1) Hạn chế của hiện thực hiện tại</strong>

Hiện thực SimpleAgent hiện tại của chúng ta chủ yếu tập trung vào việc dựng quy trình đánh giá, năng lực gọi công cụ vẫn còn dư địa cải thiện. SimpleAgent dùng định dạng gọi công cụ tùy biến `[TOOL_CALL:tool_name:parameters]`; định dạng này đòi hỏi LLM chủ động học và sử dụng, biểu hiện trong kịch bản phức tạp có thể không bằng Agent dùng gọi hàm gốc (Function Calling). Ngoài ra, hiện tại chúng ta mới kiểm thử các hạng mục cơ bản như simple_python; với các kịch bản phức tạp hơn như multiple, parallel, irrelevance, vẫn cần tối ưu có mục tiêu.

<strong>(2) Hướng nâng cao điểm BFCL</strong>

Để nâng cao hơn điểm đánh giá BFCL, có thể bắt đầu từ các hướng sau. Thứ nhất là tối ưu năng lực gọi công cụ của Agent, có thể cân nhắc dùng LLM hỗ trợ gọi hàm gốc (như GPT-4, Claude, v.v.), hoặc cải thiện prompt để LLM hiểu định dạng gọi công cụ tốt hơn. Thứ hai là mở rộng thư viện công cụ; bài kiểm thử BFCL liên quan đến nhiều loại hàm khác nhau, có thể dựa trên đặc điểm của tập dữ liệu kiểm thử để hiện thực trước các loại công cụ thông dụng, nâng cao độ phủ công cụ của Agent. Thứ ba là thiết kế chiến lược khác nhau cho các mức độ khó khác nhau, ví dụ trong kịch bản multiple cần Agent có khả năng lập kế hoạch chuỗi gọi công cụ nhiều bước, trong kịch bản parallel cần nhận diện các lệnh gọi công cụ có thể thực thi song song, trong kịch bản irrelevance cần phán đoán có thực sự cần gọi công cụ hay không.

<strong>(3) Khuyến nghị thực hành</strong>

Với nhà phát triển muốn đạt kết quả tốt hơn trên BFCL, khuyến nghị áp dụng các chiến lược thực hành sau. Trước tiên, bắt đầu từ hạng mục simple, đảm bảo gọi một hàm cơ bản hoạt động ổn định, đây là nền tảng cho các tối ưu tiếp theo. Sau đó, dần kiểm thử các hạng mục phức tạp hơn như multiple, parallel, phân tích các ca thất bại, tìm ra khâu yếu của Agent. Trong quá trình tối ưu, có thể tham khảo các mô hình điểm cao trên bảng xếp hạng BFCL, học tư duy thiết kế và kỹ thuật tối ưu của chúng. Đồng thời, khuyến nghị dùng công cụ đánh giá chính thức để xác minh, đảm bảo kết quả sau tối ưu nhất quán với tiêu chuẩn bảng xếp hạng.

Dưới đây tổng kết một số khuyến nghị có thể xử lý thêm khi đánh giá:

<strong>1. Đánh giá tiệm tiến</strong>

Bắt đầu từ mẫu nhỏ, tăng dần số mẫu:

```python
# Bước 1: kiểm thử nhanh (5 mẫu)
results_quick = bfcl_tool.run(agent, category="simple_python", max_samples=5)

# Bước 2: kiểm thử quy mô trung bình (50 mẫu)
if results_quick['overall_accuracy'] > 0.8:
    results_medium = bfcl_tool.run(agent, category="simple_python", max_samples=50)

# Bước 3: đánh giá đầy đủ (toàn bộ mẫu)
if results_medium['overall_accuracy'] > 0.8:
    results_full = bfcl_tool.run(agent, category="simple_python", max_samples=0)
```

<strong>2. Đánh giá đa hạng mục</strong>

Đánh giá các nhiệm vụ có độ khó khác nhau:

```python
categories = ["simple_python", "multiple", "parallel", "irrelevance"]

for category in categories:
    print(f"\nHạng mục đánh giá: {category}")
    results = bfcl_tool.run(agent, category=category, max_samples=10)
    print(f"Độ chính xác: {results['overall_accuracy']:.2%}")
```

<strong>3. Đánh giá so sánh</strong>

So sánh các cấu hình Agent khác nhau:

```python
# Cấu hình 1: prompt mặc định
agent1 = SimpleAgent(name="Agent-Default", llm=llm)
results1 = bfcl_tool.run(agent1, category="simple_python", max_samples=10)

# Cấu hình 2: prompt tối ưu
agent2 = SimpleAgent(name="Agent-Optimized", llm=llm)
# ... thiết lập system prompt tối ưu ...
results2 = bfcl_tool.run(agent2, category="simple_python", max_samples=10)

# So sánh kết quả
print(f"Độ chính xác cấu hình mặc định: {results1['overall_accuracy']:.2%}")
print(f"Độ chính xác cấu hình tối ưu: {results2['overall_accuracy']:.2%}")
```

Nếu kết quả đánh giá của bạn tốt, có thể cân nhắc gửi lên bảng xếp hạng chính thức BFCL!

<strong>Bước 1: chuẩn bị tài liệu gửi</strong>

1. Tài liệu mô tả mô hình
2. Tệp kết quả đánh giá (tất cả hạng mục)
3. Cách truy cập mô hình (API hoặc liên kết mã nguồn mở)

<strong>Bước 2: gửi lên GitHub</strong>

Truy cập kho chính thức BFCL, gửi Pull Request theo hướng dẫn:

- Địa chỉ kho: https://github.com/ShishirPatil/gorilla
- Hướng dẫn gửi: tham khảo `CONTRIBUTING.md`

<strong>Bước 3: chờ xét duyệt</strong>

Nhóm BFCL sẽ xét duyệt bài gửi của bạn, xác minh tính chính xác của kết quả. Sau khi được duyệt, mô hình của bạn sẽ xuất hiện trên bảng xếp hạng chính thức!



## 12.3 GAIA: Đánh giá năng lực trợ lý AI tổng quát

### 12.3.1 Giới thiệu benchmark GAIA

GAIA (General AI Assistants) là benchmark đánh giá do Meta AI và Hugging Face đồng đề xuất, tập trung đánh giá <strong>năng lực tổng quát</strong> của trợ lý AI<sup>[2]</sup>. Khác với BFCL tập trung vào gọi công cụ, GAIA đánh giá hiệu suất tổng hợp của Agent trong các nhiệm vụ thế giới thực.

Triết lý thiết kế của GAIA là: <strong>vấn đề trong thế giới thực thường cần vận dụng tổng hợp nhiều năng lực</strong>. Một trợ lý AI xuất sắc không chỉ cần gọi công cụ, mà còn cần:

- <strong>Suy luận nhiều bước</strong>: phân rã vấn đề phức tạp thành nhiều vấn đề con
- <strong>Vận dụng tri thức</strong>: tận dụng tri thức tích hợp và cơ sở tri thức bên ngoài
- <strong>Hiểu đa phương thức</strong>: xử lý nhiều loại đầu vào như văn bản, hình ảnh, tệp
- <strong>Duyệt web</strong>: lấy thông tin mới nhất từ Internet
- <strong>Thao tác tệp</strong>: đọc và xử lý tệp ở nhiều định dạng

<strong>(1) Cấu trúc tập dữ liệu GAIA</strong>

Sau khi hiểu triết lý đánh giá của GAIA, hãy đi sâu vào cấu trúc cụ thể của tập dữ liệu GAIA. GAIA gồm 466 câu hỏi thế giới thực được thiết kế kỹ lưỡng; các câu hỏi này được chia thành ba mức độ khó theo độ phức tạp và số bước suy luận cần thiết, từ nhiệm vụ suy luận không bước đơn giản đến nhiệm vụ khó cần suy luận phức tạp nhiều bước, bao phủ toàn diện các kịch bản khác nhau mà Agent có thể gặp trong ứng dụng thực tế, như Bảng 12.3:

<div align="center">
  <p>Bảng 12.3 Phân bố mức độ khó của tập dữ liệu GAIA</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-table-3.png" alt="" width="85%"/>
</div>
Về ví dụ mẫu của tập dữ liệu GAIA, có thể tham khảo đoạn mã dưới đây:

```json
{
  "task_id": "gaia_001",
  "Question": "What is the total population of the top 3 most populous cities in California?",
  "Level": 2,
  "Final answer": "12847521",
  "file_name": "",
  "file_path": "",
  "Annotator Metadata": {
    "Steps": [
      "Search for most populous cities in California",
      "Get population data for top 3 cities",
      "Sum the populations"
    ],
    "Number of steps": 3,
    "How long did this take?": "5 minutes",
    "Tools": ["web_search", "calculator"]
  }
}
```

<strong>Mô tả các trường then chốt:</strong>
- `Question`: mô tả câu hỏi
- `Level`: mức độ khó (1-3)
- `Final answer`: đáp án chuẩn (có thể là số, văn bản hoặc tệp)
- `file_name/file_path`: tệp đính kèm (nếu có)
- `Annotator Metadata`: siêu dữ liệu do người chú thích cung cấp (các bước suy luận, công cụ cần thiết, v.v.)

<strong>(2) Giới thiệu khớp gần đúng chính xác</strong>

GAIA dùng thuật toán đánh giá <strong>khớp gần đúng chính xác (Quasi Exact Match)</strong>, đây là tiêu chuẩn đánh giá do GAIA chính thức định nghĩa. Tư tưởng cốt lõi của thuật toán là: <strong>trước tiên chuẩn hóa câu trả lời, sau đó khớp chính xác</strong>.

Cho câu trả lời dự đoán $A_{\text{pred}}$ và đáp án chuẩn $A_{\text{true}}$, hàm khớp gần đúng chính xác được định nghĩa là:

$$
\text{Quasi\_Exact\_Match}(A_{\text{pred}}, A_{\text{true}}) = \begin{cases}
1 & \text{if } \mathcal{N}(A_{\text{pred}}) = \mathcal{N}(A_{\text{true}}) \\
0 & \text{otherwise}
\end{cases}
$$

Trong đó $\mathcal{N}(\cdot)$ là hàm chuẩn hóa, áp dụng các quy tắc khác nhau theo loại câu trả lời.

Hàm chuẩn hóa áp dụng các quy tắc khác nhau theo loại câu trả lời. Với kiểu số, cần loại bỏ dấu phân cách hàng nghìn (`1,000` → `1000`) và ký hiệu đơn vị (`$100` → `100`, `50%` → `50`), ví dụ `"$1,234.56"` chuẩn hóa thành `"1234.56"`. Với kiểu chuỗi, cần chuyển thành chữ thường (`"Apple"` → `"apple"`), loại bỏ mạo từ (`"the apple"` → `"apple"`), loại bỏ khoảng trắng thừa (`"hello  world"` → `"hello world"`) và loại bỏ dấu câu cuối (`"hello."` → `"hello"`), ví dụ `"The United States"` chuẩn hóa thành `"united states"`. Với kiểu danh sách, cần tách các phần tử theo dấu phẩy, áp dụng chuẩn hóa chuỗi cho từng phần tử, sắp xếp theo thứ tự chữ cái rồi nối lại, ví dụ `"Paris, London, Berlin"` chuẩn hóa thành `"berlin,london,paris"`.

<strong>Ví dụ chuẩn hóa:</strong>

```python
# Câu trả lời dạng số
Câu trả lời gốc: "$1,234.56"
Sau chuẩn hóa: "1234.56"

# Câu trả lời dạng chuỗi
Câu trả lời gốc: "The United States of America"
Sau chuẩn hóa: "united states of america"

# Câu trả lời dạng danh sách
Câu trả lời gốc: "Paris, London, Berlin"
Sau chuẩn hóa: "berlin, london, paris"
```

<strong>(3) Chỉ số đánh giá GAIA</strong>

GAIA dùng các chỉ số sau để đánh giá hiệu năng Agent:

<strong>1. Tỷ lệ khớp chính xác (Exact Match Rate)</strong>

Tỷ lệ khớp chính xác là chỉ số cốt lõi của GAIA, được định nghĩa là tỷ lệ mẫu khớp gần đúng chính xác thành công:

$$
\text{Exact Match Rate} = \frac{1}{N} \sum_{i=1}^{N} \text{Quasi\_Exact\_Match}(A_{\text{pred},i}, A_{\text{true},i})
$$

Trong đó:
- $N$ là tổng số mẫu
- $A_{\text{pred},i}$ là câu trả lời dự đoán của mẫu thứ $i$
- $A_{\text{true},i}$ là đáp án chuẩn của mẫu thứ $i$
- $\text{Quasi\_Exact\_Match}(\cdot, \cdot) \in \{0, 1\}$ là hàm khớp gần đúng chính xác

<strong>2. Độ chính xác theo cấp độ (Level-wise Accuracy)</strong>

Với mỗi mức độ khó $\ell \in \{1, 2, 3\}$, tính độ chính xác của mức đó:

$$
\text{Accuracy}_\ell = \frac{1}{|D_\ell|} \sum_{i \in D_\ell} \text{Quasi\_Exact\_Match}(A_{\text{pred},i}, A_{\text{true},i})
$$

Trong đó $D_\ell$ là tập mẫu của mức độ khó $\ell$, $|D_\ell|$ là số mẫu của mức đó.

<strong>3. Tỷ lệ giảm khi tăng độ khó (Difficulty Progression Drop Rate)</strong>

Đo mức suy giảm hiệu năng của Agent khi độ khó tăng:

$$
\text{Drop Rate}_{\ell \to \ell+1} = \frac{\text{Accuracy}_\ell - \text{Accuracy}_{\ell+1}}{\text{Accuracy}_\ell}
$$

- $\text{Drop Rate}_{1 \to 2}$: tỷ lệ giảm từ Level 1 sang Level 2
- $\text{Drop Rate}_{2 \to 3}$: tỷ lệ giảm từ Level 2 sang Level 3

<strong>4. Số bước suy luận trung bình (Average Reasoning Steps)</strong>

Đánh giá số bước trung bình Agent cần để hoàn thành nhiệm vụ:

$$
\text{Avg Steps} = \frac{1}{N_{\text{correct}}} \sum_{i \in \text{Correct}} \text{steps}_i
$$

Trong đó $N_{\text{correct}}$ là số mẫu trả lời đúng, $\text{steps}_i$ là số bước suy luận của mẫu thứ $i$.

<strong>Giải thích chỉ số:</strong>

- <strong>Exact Match Rate = 1.0</strong>: tất cả mẫu đều hoàn toàn đúng
- <strong>Exact Match Rate = 0.5</strong>: 50% mẫu đúng, 50% mẫu sai
- <strong>Drop Rate = 0.3</strong>: độ khó tăng khiến độ chính xác giảm 30%
- <strong>Drop Rate = 0.0</strong>: độ khó tăng không ảnh hưởng độ chính xác (trường hợp lý tưởng)

<strong>Ví dụ đánh giá:</strong>

Giả sử chúng ta đánh giá 10 mẫu, kết quả có thể tham khảo như Bảng 12.4:

<div align="center">
  <p>Bảng 12.4 Phân bố mức độ khó của tập dữ liệu GAIA</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-table-4.png" alt="" width="85%"/>
</div>

Nếu muốn tính chỉ số cho ca này, có thể tham khảo script Python dưới đây.

```python
# 1. Tỷ lệ khớp chính xác
total_samples = 10
correct_samples = 7  # Mẫu 1,2,3,5,6,8,9
exact_match_rate = correct_samples / total_samples = 0.70  # 70%

# 2. Độ chính xác theo cấp độ
level_1_correct = 3  # Mẫu 1,2,3
level_1_total = 3
level_1_accuracy = 3 / 3 = 1.00  # 100%

level_2_correct = 2  # Mẫu 5,6
level_2_total = 3
level_2_accuracy = 2 / 3 = 0.67  # 67%

level_3_correct = 2  # Mẫu 8,9
level_3_total = 4
level_3_accuracy = 2 / 4 = 0.50  # 50%

# 3. Tỷ lệ giảm khi tăng độ khó
drop_rate_1_to_2 = (1.00 - 0.67) / 1.00 = 0.33  # 33%
drop_rate_2_to_3 = (0.67 - 0.50) / 0.67 = 0.25  # 25%

print(f"Tỷ lệ khớp chính xác: {exact_match_rate:.2%}")  # 70.00%
print(f"Độ chính xác Level 1: {level_1_accuracy:.2%}")  # 100.00%
print(f"Độ chính xác Level 2: {level_2_accuracy:.2%}")  # 66.67%
print(f"Độ chính xác Level 3: {level_3_accuracy:.2%}")  # 50.00%
print(f"Tỷ lệ giảm Level 1→2: {drop_rate_1_to_2:.2%}")  # 33.00%
print(f"Tỷ lệ giảm Level 2→3: {drop_rate_2_to_3:.2%}")  # 25.00%
```

<strong>Phân tích kết quả:</strong>

- <strong>Hiệu năng tổng thể</strong>: tỷ lệ khớp chính xác 70%, biểu hiện tốt
- <strong>Độ nhạy với độ khó</strong>: từ Level 1 sang Level 2 giảm 33%, cho thấy Agent suy giảm rõ rệt trên nhiệm vụ độ khó trung bình
- <strong>Ranh giới năng lực</strong>: độ chính xác Level 3 là 50%, cho thấy Agent vẫn còn dư địa cải thiện trên nhiệm vụ phức tạp

Tỷ lệ giảm càng lớn, mức suy giảm năng lực của Agent khi xử lý nhiệm vụ phức tạp càng rõ.

<strong>(4) System prompt chính thức của GAIA</strong>

GAIA yêu cầu dùng một system prompt cụ thể, đảm bảo đầu ra của mô hình phù hợp định dạng đánh giá:

```python
GAIA_SYSTEM_PROMPT = """You are a general AI assistant. I will ask you a question. Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER].

YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.

If you are asked for a number, don't use comma to write your number neither use units such as $ or percent sign unless specified otherwise.

If you are asked for a string, don't use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.

If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string."""
```

GAIA có yêu cầu nghiêm ngặt về định dạng câu trả lời: câu trả lời phải được đưa ra theo định dạng `FINAL ANSWER: [câu trả lời]`; với câu trả lời kiểu số, không dùng dấu phân cách hàng nghìn và ký hiệu đơn vị; với câu trả lời kiểu chuỗi, không dùng mạo từ và viết tắt; với câu trả lời kiểu danh sách, dùng dấu phẩy phân tách và sắp xếp theo thứ tự chữ cái.

### 12.3.2 Lấy tập dữ liệu GAIA

<strong>Lưu ý quan trọng</strong>: GAIA là <strong>tập dữ liệu hạn chế (Gated Dataset)</strong>, cần xin quyền truy cập trên HuggingFace trước.

<strong>Bước 1: xin quyền truy cập</strong>

1. Truy cập https://huggingface.co/datasets/gaia-benchmark/GAIA
2. Nhấn nút "Request access"
3. Điền biểu mẫu xin quyền (thường được duyệt trong vài giây)
4. Lấy HuggingFace Token của bạn: https://huggingface.co/settings/tokens

<strong>Bước 2: cấu hình biến môi trường</strong>

Thêm HuggingFace Token của bạn vào tệp `.env`:

```bash
# Cấu hình HuggingFace API
HF_TOKEN=hf_your_token_here
```

<strong>Cách 1: dùng HelloAgents tự động tải (khuyến nghị)</strong>

HelloAgents sẽ tự động xử lý việc tải và lưu đệm tập dữ liệu GAIA:

```python
from hello_agents.evaluation import GAIADataset
import os

# Đảm bảo đã thiết lập HF_TOKEN; nếu đã thiết lập trong .env thì không cần dòng này
os.environ["HF_TOKEN"] = "hf_your_token_here"

# Tự động tải về ./data/gaia/
dataset = GAIADataset(
    dataset_name="gaia-benchmark/GAIA",
    split="validation",  # hoặc "test"
    level=1  # tùy chọn: 1, 2, 3, None(tất cả)
)
items = dataset.load()

print(f"Đã nạp {len(items)} mẫu kiểm thử")
# Đầu ra: Đã nạp 53 mẫu kiểm thử (Level 1)
```

<strong>Nguyên lý hoạt động</strong>:

- Lần chạy đầu tiên, dùng `snapshot_download` tải toàn bộ tập dữ liệu về `./data/gaia/`
- Tập dữ liệu gồm 114 tệp (câu hỏi, hình ảnh, PDF và các tài liệu khác)
- Các lần sau nạp trực tiếp từ cục bộ, tốc độ rất nhanh

<strong>Cấu trúc thư mục tập dữ liệu</strong>:
```
./data/gaia/
├── 2023/
│   ├── validation/
│   │   ├── metadata.jsonl  (165 câu hỏi)
│   │   ├── *.png, *.pdf, *.csv, *.xlsx  (tệp đính kèm)
│   └── test/
│       ├── metadata.jsonl  (301 câu hỏi)
│       └── ... (tệp đính kèm)
├── GAIA.py
└── README.md
```

<strong>Cách 2: tải thủ công</strong>

Nếu bạn muốn tự tải tập dữ liệu:

```python
from huggingface_hub import snapshot_download
import os

# Thiết lập Token
os.environ["HF_TOKEN"] = "hf_your_token_here"

# Tải tập dữ liệu
snapshot_download(
    repo_id="gaia-benchmark/GAIA",
    repo_type="dataset",
    local_dir="./data/gaia",
    token=os.getenv("HF_TOKEN")
)
```

<strong>Xem thống kê tập dữ liệu</strong>:

```python
# Xem thống kê tập dữ liệu
stats = dataset.get_statistics()
print(f"Tổng số mẫu: {stats['total_samples']}")
print(f"Phân bố cấp độ: {stats['level_distribution']}")
# Đầu ra:
# Tổng số mẫu: 165
# Phân bố cấp độ: {1: 53, 2: 62, 3: 50}
```


### 12.3.3 Hiện thực đánh giá GAIA trong HelloAgents

Tương tự BFCL, chúng ta cung cấp hai cách đánh giá, khuyến nghị dùng <strong>cách 1</strong>.

<strong>Cách 1: dùng GAIAEvaluationTool đánh giá một chạm</strong>

Đây là cách đơn giản nhất, tự động hoàn thành việc tải tập dữ liệu, thực thi đánh giá, xuất kết quả và sinh báo cáo:

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import GAIAEvaluationTool

# System prompt chính thức của GAIA (từ bài báo)
GAIA_SYSTEM_PROMPT = """You are a general AI assistant. I will ask you a question. Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER].

YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.

If you are asked for a number, don't use comma to write your number neither use units such as $ or percent sign unless specified otherwise.

If you are asked for a string, don't use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.

If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string."""

# 1. Tạo Agent (dùng system prompt chính thức của GAIA)
llm = HelloAgentsLLM()
agent = SimpleAgent(
    name="TestAgent",
    llm=llm,
    system_prompt=GAIA_SYSTEM_PROMPT  # Then chốt: dùng prompt chính thức của GAIA
)

# 2. Tạo công cụ đánh giá GAIA
gaia_tool = GAIAEvaluationTool()

# 3. Chạy đánh giá một chạm
results = gaia_tool.run(
    agent=agent,
    level=1,  # Level 1: nhiệm vụ đơn giản
    max_samples=5,  # Đánh giá 5 mẫu
    export_results=True,  # Xuất kết quả định dạng GAIA
    generate_report=True  # Sinh báo cáo đánh giá
)

# 4. Xem kết quả
print(f"Tỷ lệ khớp chính xác: {results['exact_match_rate']:.2%}")
print(f"Tỷ lệ khớp một phần: {results['partial_match_rate']:.2%}")
print(f"Số mẫu đúng: {results['exact_matches']}/{results['total_samples']}")
```

<strong>Kết quả chạy:</strong>

```
============================================================
Đánh giá một chạm GAIA
============================================================

Cấu hình:
   Agent: TestAgent
   Mức độ khó: 1
   Số lượng mẫu: 5

============================================================
Bước 1: Chạy đánh giá HelloAgents
============================================================
   Đang tải từ HuggingFace: gaia-benchmark/GAIA
   📥 Đang tải tập dữ liệu GAIA...
   ✓ Tải tập dữ liệu hoàn tất
   ✓ Đã nạp 165 mẫu
✅ Nạp tập dữ liệu GAIA hoàn tất
   Nguồn dữ liệu: gaia-benchmark/GAIA
   Phân chia: validation
   Cấp độ: 1
   Số mẫu: 53

🌟 Bắt đầu đánh giá GAIA...
   Số lượng mẫu: 5
   Tiến độ: 5/5
✅ Đánh giá GAIA hoàn tất
   Tỷ lệ khớp chính xác: 80.00%
   Tỷ lệ khớp một phần: 80.00%

============================================================
Bước 2: Xuất kết quả định dạng GAIA
============================================================
✅ Đã xuất kết quả định dạng GAIA
   Tệp đầu ra: evaluation_results\gaia_official\gaia_level1_result_20251011_012648.jsonl
   Số mẫu: 5
   Bao gồm vết suy luận: True
📄 Đã sinh hướng dẫn gửi: evaluation_results\gaia_official\SUBMISSION_GUIDE_20251011_012648.md

============================================================
Bước 3: Sinh báo cáo đánh giá
============================================================
📄 Báo cáo đã được sinh: evaluation_reports\gaia_report_20251011_012648.md

============================================================
🎯 Kết quả cuối cùng
============================================================
   Tỷ lệ khớp chính xác: 80.00%
   Tỷ lệ khớp một phần: 80.00%
   Số mẫu đúng: 4/5
```

Sau khi đánh giá hoàn tất, ba loại tệp sẽ được sinh tự động: thứ nhất là tệp kết quả định dạng GAIA (`evaluation_results/gaia_official/gaia_level1_result_*.jsonl`), dùng định dạng JSONL (mỗi dòng một đối tượng JSON), có thể dùng trực tiếp để gửi lên bảng xếp hạng GAIA; thứ hai là tệp hướng dẫn gửi (`evaluation_results/gaia_official/SUBMISSION_GUIDE_*.md`), gồm các bước gửi chi tiết, mô tả định dạng tệp kết quả và các lưu ý; cuối cùng là báo cáo đánh giá (`evaluation_reports/gaia_report_*.md`), gồm tóm tắt kết quả đánh giá, chỉ số chi tiết, chi tiết mẫu và biểu đồ trực quan hóa.

<strong>Lưu ý</strong>: nếu bạn thấy kết quả đánh giá được sinh ra không lý tưởng (ví dụ độ chính xác thấp), đây là hiện tượng bình thường. Tuy Level 1 là nhiệm vụ suy luận một bước, nhưng vẫn cần Agent có năng lực gọi công cụ (như công cụ tìm kiếm, máy tính, v.v.) mới trả lời đúng được câu hỏi. SimpleAgent mà chúng ta đang dùng chủ yếu để minh họa quy trình đánh giá, năng lực gọi công cụ vẫn còn dư địa cải thiện.

<strong>Cách 2: dùng Dataset + Evaluator (tùy biến linh hoạt)</strong>

Nếu cần kiểm soát chi tiết hơn, có thể dùng trực tiếp các thành phần tầng dưới:

```python
from hello_agents.evaluation import GAIADataset, GAIAEvaluator

# 1. Nạp tập dữ liệu
dataset = GAIADataset(level=1)
items = dataset.load()
print(f"Đã nạp {len(items)} mẫu")

# 2. Tạo bộ đánh giá
evaluator = GAIAEvaluator(dataset=dataset, level=1)

# 3. Chạy đánh giá
results = evaluator.evaluate(agent, max_samples=5)

# 4. Xuất kết quả định dạng GAIA
evaluator.export_to_gaia_format(
    results,
    "gaia_results.jsonl",
    include_reasoning=True
)
```

Báo cáo đánh giá được sinh (`gaia_report_*.md`) có thể tham khảo tệp dưới đây:

```markdown
# Báo cáo đánh giá GAIA

**Thời điểm sinh**: 2025-10-11 01:26:48

## 📊 Tổng quan đánh giá

- **Agent**: TestAgent
- **Mức độ khó**: 1
- **Tổng số mẫu**: 2
- **Số khớp chính xác**: 1
- **Số khớp một phần**: 1
- **Tỷ lệ khớp chính xác**: 50.00%
- **Tỷ lệ khớp một phần**: 50.00%

## 📈 Chỉ số chi tiết

### Độ chính xác theo cấp độ

- **Level 1**: 50.00% chính xác / 50.00% một phần (1/2)

## 📝 Chi tiết mẫu (10 mẫu đầu)

| ID nhiệm vụ | Cấp độ | Câu trả lời dự đoán | Câu trả lời đúng | Khớp chính xác | Khớp một phần |
|--------|------|----------|----------|----------|----------|
| e1fc63a2-da7a-432f-be78-7c4a95598703 | 1 | 24000 | 17 | ❌ | ❌ |
| 8e867cd7-cff9-4e6c-867a-ff5ddc2550be | 1 | 3 | 3 | ✅ | ✅ |

## 📊 Trực quan hóa độ chính xác

Khớp chính xác: █████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░ 50.00%
Khớp một phần: █████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░ 50.00%


## 💡 Khuyến nghị

- ⚠️ Hiệu năng trung bình, cần cải thiện.
- 💡 Khuyến nghị kiểm tra năng lực sử dụng công cụ và suy luận nhiều bước.
```

**Kết quả định dạng GAIA được sinh (`gaia_level1_result_*.jsonl`):**

```json
{"task_id": "e1fc63a2-da7a-432f-be78-7c4a95598703", "model_answer": "24000", "reasoning_trace": "24000"}
{"task_id": "8e867cd7-cff9-4e6c-867a-ff5ddc2550be", "model_answer": "3", "reasoning_trace": "3"}
```

### 12.3.4 Gửi kết quả lên bảng xếp hạng chính thức GAIA

Sau khi dùng GAIAEvaluationTool chạy đánh giá, trong thư mục `evaluation_results/gaia_official/` sẽ sinh các tệp cần thiết để gửi và hướng dẫn gửi chi tiết.

1. **Tệp kết quả định dạng GAIA**: `gaia_level1_result_*.jsonl`
   ```json
   {"task_id": "xxx", "model_answer": "câu trả lời", "reasoning_trace": "quá trình suy luận"}
   {"task_id": "yyy", "model_answer": "câu trả lời", "reasoning_trace": "quá trình suy luận"}
   ```

2. <strong>Tệp hướng dẫn gửi</strong>: `SUBMISSION_GUIDE_*.md`

Mở tệp `SUBMISSION_GUIDE_*.md` được sinh tự động, trong đó có hướng dẫn gửi đầy đủ:

Cụ thể, mở trình duyệt và truy cập:
```
https://huggingface.co/spaces/gaia-benchmark/leaderboard
```

Như Hình 12.4, chỉ cần điền thông tin vào biểu mẫu gửi:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-4.png" alt="" width="85%"/>
  <p>Hình 12.4 Sơ đồ quy trình đánh giá GAIA</p>
</div>

Trước khi gửi, có thể kiểm tra thủ công tệp JSON được sinh:

```python
import json

# Đọc tệp kết quả
with open("evaluation_results/gaia_official/gaia_level1_result_*.jsonl", "r") as f:
    for line in f:
        result = json.loads(line)
        print(f"Task ID: {result['task_id']}")
        print(f"Answer: {result['model_answer']}")
        print(f"Reasoning: {result['reasoning_trace']}")
        print("-" * 50)
```

### 12.3.5 Chi tiết hiện thực các thành phần cốt lõi

Hiện thực hệ thống đánh giá GAIA tương tự BFCL, nhưng có một số thiết kế đặc biệt cho đánh giá năng lực tổng quát.

<strong>(1) GAIADataset: bộ nạp dữ liệu hỗ trợ đa phương thức</strong>

Điểm đặc biệt của tập dữ liệu GAIA là nó chứa dữ liệu đa phương thức (văn bản, tệp, hình ảnh, v.v.):

````python
class GAIADataset:
    """Bộ nạp tập dữ liệu GAIA

    Hỗ trợ nạp tập dữ liệu GAIA từ HuggingFace (tập dữ liệu hạn chế)
    """

    def __init__(
        self,
        level: Optional[int] = None,
        split: str = "validation",
        local_data_dir: Optional[str] = None
    ):
        self.level = level
        self.split = split
        self.local_data_dir = local_data_dir or "./data/gaia"
        self.data = []

    def load(self) -> List[Dict[str, Any]]:
        """Nạp tập dữ liệu"""
        # Tải từ HuggingFace
        items = self._load_from_huggingface()

        # Lọc theo cấp độ
        if self.level:
            items = [item for item in items if item.get("level") == self.level]

        self.data = items
        return items

    def _load_from_huggingface(self) -> List[Dict[str, Any]]:
        """Tải tập dữ liệu GAIA từ HuggingFace"""
        from huggingface_hub import snapshot_download
        import json

        # Tải tập dữ liệu
        repo_id = "gaia-benchmark/GAIA"
        local_dir = snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=self.local_data_dir,
            local_dir_use_symlinks=False
        )

        # Nạp tệp JSONL
        data_file = Path(local_dir) / "2023" / self.split / "metadata.jsonl"
        items = []
        with open(data_file, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                items.append(self._standardize_item(item))

        return items
````
<strong>(2) GAIAEvaluator: hiện thực thuật toán đánh giá chính thức GAIA</strong>

Đánh giá GAIA dùng thuật toán <strong>khớp gần đúng chính xác (Quasi Exact Match)</strong>, cần logic chuẩn hóa và so khớp câu trả lời đặc biệt:

````python
class GAIAEvaluator:
    """Bộ đánh giá GAIA

    Hiện thực thuật toán đánh giá khớp gần đúng chính xác (Quasi Exact Match) chính thức của GAIA
    """

    def evaluate(self, agent: Any, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """Thực hiện đánh giá"""
        dataset_items = self.dataset.load()

        if max_samples:
            dataset_items = dataset_items[:max_samples]

        results = []
        for i, item in enumerate(dataset_items, 1):
            # 1. Dựng prompt
            prompt = self._build_prompt(item["question"], item)

            # 2. Gọi Agent
            response = agent.run(prompt)

            # 3. Trích xuất câu trả lời (định dạng GAIA: FINAL ANSWER: [câu trả lời])
            predicted_answer = self._extract_answer(response)

            # 4. Chuẩn hóa câu trả lời (quy tắc chính thức GAIA)
            normalized_pred = self._normalize_answer(predicted_answer)
            normalized_truth = self._normalize_answer(item["final_answer"])

            # 5. Khớp gần đúng chính xác
            exact_match = (normalized_pred == normalized_truth)

            results.append({
                "task_id": item["task_id"],
                "predicted": predicted_answer,
                "expected": item["final_answer"],
                "exact_match": exact_match,
                "level": item.get("level", 0)
            })

        return self._format_results(results)
````
GAIA dùng các quy tắc chuẩn hóa riêng để xử lý các loại câu trả lời khác nhau:

```python
def _normalize_answer(self, answer: str) -> str:
    """Chuẩn hóa chuỗi câu trả lời (quy tắc chuẩn hóa chính thức GAIA)

    Quy tắc:
    1. Số: loại bỏ dấu phân cách hàng nghìn và ký hiệu đơn vị
    2. Chuỗi: loại bỏ mạo từ, chuyển chữ thường, loại bỏ khoảng trắng thừa
    3. Danh sách: phân tách bằng dấu phẩy, sắp xếp theo thứ tự chữ cái
    """
    if not answer:
        return ""

    answer = answer.strip()

    # Kiểm tra xem có phải danh sách phân tách bằng dấu phẩy
    if ',' in answer:
        parts = [self._normalize_single_answer(p.strip()) for p in answer.split(',')]
        parts.sort()  # GAIA yêu cầu sắp xếp theo thứ tự chữ cái
        return ','.join(parts)
    else:
        return self._normalize_single_answer(answer)

def _normalize_single_answer(self, answer: str) -> str:
    """Chuẩn hóa một câu trả lời đơn (câu trả lời không chứa dấu phẩy)"""
    answer = answer.strip().lower()

    # Loại bỏ mạo từ thường gặp
    articles = ['the', 'a', 'an']
    words = answer.split()
    if words and words[0] in articles:
        words = words[1:]
        answer = ' '.join(words)

    # Loại bỏ ký hiệu tiền tệ và dấu phần trăm
    answer = answer.replace('$', '').replace('%', '').replace('€', '').replace('£', '')

    # Loại bỏ dấu phân cách hàng nghìn trong số
    answer = re.sub(r'(\d),(\d)', r'\1\2', answer)

    # Loại bỏ khoảng trắng thừa
    answer = ' '.join(answer.split())

    # Loại bỏ dấu câu ở cuối
    answer = answer.rstrip('.,;:!?')

    return answer
```

GAIA yêu cầu định dạng đầu ra của mô hình là `FINAL ANSWER: [câu trả lời]`:

```python
def _extract_answer(self, response: str) -> str:
    """Trích xuất câu trả lời từ phản hồi (định dạng GAIA)

    GAIA yêu cầu định dạng câu trả lời là: FINAL ANSWER: [câu trả lời]
    """
    # Trước tiên thử trích xuất câu trả lời theo định dạng chính thức GAIA
    final_answer_pattern = r'FINAL ANSWER:\s*(.+?)(?:\n|$)'
    match = re.search(final_answer_pattern, response, re.IGNORECASE | re.MULTILINE)
    if match:
        answer = match.group(1).strip()
        # Loại bỏ dấu ngoặc vuông có thể có
        answer = answer.strip('[]')
        return answer

    # Phương án dự phòng: tìm các dấu hiệu câu trả lời khác
    answer_patterns = [
        r'答案[：:]\s*(.+)',
        r'最终答案[：:]\s*(.+)',
        r'Final answer[：:]\s*(.+)',
        r'Answer[：:]\s*(.+)',
    ]

    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Nếu không tìm thấy dấu hiệu, trả về dòng không rỗng cuối cùng
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line and not line.startswith('#'):
            return line

    return response.strip()
```

Sau khi đánh giá hoàn tất, có thể xuất sang định dạng JSONL mà GAIA chính thức yêu cầu:

```python
def export_to_gaia_format(
    self,
    results: Dict[str, Any],
    output_path: Union[str, Path],
    include_reasoning: bool = True
) -> None:
    """Xuất sang định dạng chính thức GAIA (JSONL)

    Định dạng GAIA yêu cầu:
    {"task_id": "xxx", "model_answer": "câu trả lời", "reasoning_trace": "quá trình suy luận"}
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for result in results.get("detailed_results", []):
            entry = {
                "task_id": result["task_id"],
                "model_answer": result["predicted"]
            }

            if include_reasoning:
                entry["reasoning_trace"] = result.get("response", result["predicted"])

            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
```

<strong>(3) GAIAEvaluationTool: công cụ đánh giá một chạm</strong>

GAIAEvaluationTool đóng gói toàn bộ quy trình đánh giá, cung cấp chức năng đánh giá một chạm:

````python
class GAIAEvaluationTool(Tool):
    """Công cụ đánh giá GAIA

    Cung cấp chức năng đánh giá một chạm:
    1. Chạy đánh giá HelloAgents
    2. Xuất kết quả định dạng GAIA
    3. Sinh báo cáo đánh giá
    4. Sinh hướng dẫn gửi
    """

    def run(
        self,
        agent: Any,
        level: Optional[int] = None,
        max_samples: Optional[int] = None,
        local_data_dir: Optional[str] = None,
        export_results: bool = True,
        generate_report: bool = True
    ) -> Dict[str, Any]:
        """Thực hiện đánh giá một chạm GAIA"""
        # Bước 1: chạy đánh giá HelloAgents
        results = self._run_evaluation(agent, level, max_samples, local_data_dir)

        # Bước 2: xuất kết quả định dạng GAIA
        if export_results:
            self._export_results(results)

        # Bước 3: sinh báo cáo đánh giá
        if generate_report:
            self.generate_report(results)

        return results
````
GAIAEvaluationTool sẽ tự động sinh báo cáo đánh giá:

```python
def generate_report(
    self,
    results: Dict[str, Any],
    output_file: Optional[Union[str, Path]] = None
) -> str:
    """Sinh báo cáo đánh giá"""
    report = f"""# Báo cáo đánh giá GAIA

**Thời điểm sinh**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 Tổng quan đánh giá

- **Agent**: {results.get("agent_name", "Unknown")}
- **Mức độ khó**: {results.get("level_filter") or 'tất cả'}
- **Tổng số mẫu**: {results.get("total_samples", 0)}
- **Số khớp chính xác**: {results.get("exact_matches", 0)}
- **Tỷ lệ khớp chính xác**: {results.get("exact_match_rate", 0):.2%}

## 📈 Chỉ số chi tiết

### Độ chính xác theo cấp độ

{self._format_level_metrics(results.get("level_metrics", {}))}

## 📝 Chi tiết mẫu (10 mẫu đầu)

{self._format_sample_details(results.get("detailed_results", [])[:10])}

## 📊 Trực quan hóa độ chính xác

{self._format_visualization(results.get("exact_match_rate", 0))}

## 💡 Khuyến nghị

{self._format_suggestions(results.get("exact_match_rate", 0))}
"""

    # Lưu báo cáo
    if output_file is None:
        output_dir = Path("./evaluation_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"gaia_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    return report
```

## 12.4 Đánh giá chất lượng sinh dữ liệu

Trong phát triển hệ thống AI, dữ liệu huấn luyện chất lượng cao là nền tảng cho hiệu năng của hệ thống. Mục này giới thiệu cách dùng framework HelloAgents đánh giá chất lượng dữ liệu được sinh, lấy ví dụ sinh đề toán theo phong cách AIME (Kỳ thi Mời Toán học Hoa Kỳ)<sup>[9]</sup>.

AIME là cuộc thi toán có độ khó trung bình do Hiệp hội Toán học Hoa Kỳ (MAA) tổ chức, nằm giữa AMC 10/12 và Olympic Toán học Hoa Kỳ (USAMO). Đề AIME có những đặc điểm rõ rệt: đáp án mỗi câu là số nguyên từ 0 đến 999, đề bao phủ nhiều lĩnh vực toán như đại số, hình học, lý thuyết số, tổ hợp, xác suất, cần suy luận nhiều bước nhưng không liên quan lý thuyết quá sâu, độ khó vừa phải (tương đương trình độ câu 6-9 của AIME). Những đặc điểm này khiến đề AIME trở thành benchmark lý tưởng để đánh giá chất lượng sinh đề toán: định dạng đáp án thống nhất thuận tiện cho đánh giá tự động, độ khó vừa phải phù hợp sinh quy mô lớn. Chúng ta dùng tập dữ liệu `TianHongZXY/aime-1983-2025` trên HuggingFace làm tham chiếu; tập dữ liệu này gồm hơn 900 đề AIME thực tế từ năm 1983 đến 2025, cung cấp mẫu tham chiếu phong phú cho việc sinh và đánh giá của chúng ta.

### 12.4.1 Tổng quan phương pháp đánh giá

Trong đánh giá chất lượng sinh dữ liệu, chúng ta dùng ba phương pháp đánh giá bổ trợ nhau: LLM Judge, Win Rate và chấm điểm thủ công. Chọn ba phương pháp này vì hai lý do quan trọng. Thứ nhất, từ góc độ phương pháp luận, đây là các phương án đánh giá tự động thường dùng trong lĩnh vực Agent hiện nay, cũng là cách làm chủ lưu trong nhiều bài báo học thuật, có độ công nhận và nền tảng thực hành rộng rãi. Thứ hai, từ góc độ tính phù hợp, ba phương pháp này tự nhiên phù hợp với kịch bản đánh giá của chúng ta: LLM Judge và Win Rate dùng để đánh giá chất lượng sinh đề (đánh giá đa chiều từ góc độ tính đúng đắn, tính rõ ràng, độ khớp độ khó, v.v.), còn chấm điểm thủ công dùng để đánh giá chất lượng sinh đáp án (qua chuyên gia con người xác minh tính chính xác của đáp án); sự phân công này rất hợp lý và dễ hiểu.

Dưới đây chúng ta giới thiệu chi tiết cách hiện thực ba phương pháp đánh giá này. Quy trình hiện thực toàn bộ ca như Hình 12.5:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-5.png" alt="" width="85%"/>
  <p>Hình 12.5 Sơ đồ quy trình đánh giá chất lượng sinh dữ liệu</p>
</div>
<strong>(1) Đánh giá bằng LLM Judge</strong>

<strong>Động cơ thiết kế</strong>: trong đánh giá chất lượng sinh dữ liệu, chúng ta cần đánh giá chất lượng nhanh chóng và nhất quán cho lượng lớn đề được sinh. Đánh giá thủ công truyền thống tuy chính xác nhưng chi phí cao, hiệu quả thấp, khó đáp ứng nhu cầu sinh dữ liệu quy mô lớn. LLM Judge dùng mô hình ngôn ngữ lớn làm giám khảo, có thể tự động đánh giá chất lượng dữ liệu được sinh từ nhiều chiều, không chỉ nâng cao đáng kể hiệu quả đánh giá mà còn giữ được tính nhất quán của tiêu chuẩn đánh giá. Quan trọng hơn, LLM Judge có thể cung cấp lý do chấm điểm và khuyến nghị cải thiện chi tiết, giúp chúng ta hiểu ưu nhược điểm của dữ liệu được sinh, định hướng cho tối ưu tiếp theo.

Trong hiện thực của chúng ta, LLM Judge đánh giá chất lượng đề AIME từ bốn chiều then chốt:

<div align="center">
  <p>Bảng 12.5 Các chiều đánh giá đề AIME của LLM Judge</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-table-5.png" alt="" width="85%"/>
</div>

Sau khi có điểm của bốn chiều, chúng ta cần tổng hợp các điểm này thành chỉ số đánh giá tổng thể. Chúng ta định nghĩa ba chỉ số then chốt để đo mức chất lượng của đề được sinh:

<strong>Chỉ số đánh giá</strong>:

<strong>1. Điểm trung bình (Average Score)</strong>: tính điểm trung bình trên bốn chiều của tất cả đề, phản ánh mức chất lượng tổng thể của đề được sinh.
$$
\text{Average Score} = \frac{1}{N} \sum_{i=1}^{N} \frac{\sum_{d=1}^{4} S_{i,d}}{4}
$$

<strong>2. Tỷ lệ đạt (Pass Rate)</strong>: thống kê tỷ lệ đề có điểm trung bình từ 3.5 trở lên, phản ánh mức đảm bảo chất lượng cơ bản của đề được sinh.

$$
\text{Pass Rate} = \frac{|\{i : \text{Score}_i \geq 3.5\}|}{N}
$$

<strong>3. Tỷ lệ xuất sắc (Excellent Rate)</strong>: thống kê tỷ lệ đề có điểm trung bình từ 4.5 trở lên, phản ánh tỷ lệ chất lượng cao của đề được sinh.

$$
\text{Excellent Rate} = \frac{|\{i : \text{Score}_i \geq 4.5\}|}{N}
$$

Trong đó:
- $N$ là tổng số đề được đánh giá
- $S_{i,d}$ là điểm của đề thứ $i$ ở chiều thứ $d$ (thang 1-5)
- $\text{Score}_i$ là điểm trung bình của đề thứ $i$ (trung bình điểm bốn chiều)

Ba chỉ số này phản ánh chất lượng sinh từ các góc độ khác nhau: điểm trung bình cho biết mức tổng thể, tỷ lệ đạt đảm bảo chất lượng cơ bản, tỷ lệ xuất sắc đo năng lực tạo ra sản phẩm chất lượng cao.

<strong>(2) Đánh giá bằng Win Rate</strong>

<strong>Động cơ thiết kế</strong>: tuy LLM Judge có thể cung cấp điểm tuyệt đối đa chiều, chúng ta vẫn cần một chỉ số đánh giá tương đối để đo khoảng cách chất lượng giữa đề được sinh và đề thực tế. Đánh giá Win Rate thông qua so sánh từng cặp, để LLM trực tiếp phán đoán đề được sinh hay đề thực tế tốt hơn; cách so sánh tương đối này phù hợp hơn với thói quen phán đoán của con người so với chấm điểm tuyệt đối, cũng dễ phát hiện ưu nhược điểm tương đối của đề được sinh. Trong trường hợp lý tưởng, nếu chất lượng đề được sinh gần với đề thực tế, Win Rate nên ở khoảng 50% (tức đề được sinh và đề thực tế mỗi bên thắng 50%). Chỉ số này đơn giản trực quan, có thể nhanh chóng phán đoán mức chất lượng tổng thể của hệ thống sinh.

Trong hiện thực của chúng ta, đánh giá Win Rate được thực hiện theo quy trình như Hình 12.6:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-6.png" alt="" width="85%"/>
  <p>Hình 12.6 Sơ đồ quy trình đánh giá chất lượng sinh dữ liệu</p>
</div>

Trong đánh giá so sánh từng cặp, mỗi lần so sánh sinh ra ba kết quả có thể: đề được sinh thắng (Win), đề thực tế thắng (Loss) hoặc hòa (Tie). Chúng ta đánh giá chất lượng đề được sinh bằng cách thống kê tỷ lệ của ba kết quả này:

<strong>Chỉ số đánh giá</strong>:

<strong>1. Tỷ lệ thắng (Win Rate)</strong>: tỷ lệ đề được sinh được đánh giá là tốt hơn, phản ánh ưu thế của đề được sinh so với đề thực tế.

$$
\text{Win Rate} = \frac{\text{Wins}}{\text{Total Comparisons}}
$$

<strong>2. Tỷ lệ thua (Loss Rate)</strong>: tỷ lệ đề thực tế được đánh giá là tốt hơn, phản ánh bất lợi của đề được sinh so với đề thực tế.

$$
\text{Loss Rate} = \frac{\text{Losses}}{\text{Total Comparisons}}
$$

<strong>3. Tỷ lệ hòa (Tie Rate)</strong>: tỷ lệ cả hai được đánh giá là chất lượng tương đương, phản ánh mức tương đồng giữa đề được sinh và đề thực tế.

$$
\text{Tie Rate} = \frac{\text{Ties}}{\text{Total Comparisons}}
$$

Trong đó, Total Comparisons là tổng số lần so sánh, Wins, Losses và Ties lần lượt là số lần đề được sinh thắng, thua và hòa. Ba chỉ số này thỏa mãn: Win Rate + Loss Rate + Tie Rate = 100%.

<strong>Kết quả lý tưởng</strong>: Win Rate ≈ 50% (chất lượng sinh gần với đề thực tế). Nếu Win Rate thấp hơn 50% rõ rệt, chất lượng đề được sinh không bằng đề thực tế, cần tối ưu chiến lược sinh; nếu Win Rate cao hơn 50% rõ rệt, có thể đề được sinh đã vượt đề thực tế ở một số mặt, hoặc tiêu chuẩn đánh giá có sai lệch.

<strong>(3) Xác minh thủ công</strong>

<strong>Động cơ thiết kế</strong>: dù LLM Judge và Win Rate có thể tự động đánh giá chất lượng đề, với nội dung cần suy luận logic nghiêm ngặt như đề toán, xác minh thủ công vẫn không thể thiếu. Đặc biệt khi đánh giá chất lượng sinh đáp án, cần chuyên gia con người xác minh tính chính xác của đáp án, tính đầy đủ của các bước giải và tính chặt chẽ của suy luận toán học. Ngoài ra, xác minh thủ công còn có thể phát hiện những vấn đề mà đánh giá tự động có thể bỏ sót, như tính sáng tạo, tính thú vị của đề. Để nâng cao hiệu quả và trải nghiệm xác minh thủ công, chúng ta phát triển giao diện Web dựa trên Gradio, cho phép người xác minh dễ dàng duyệt đề, chấm điểm, đánh dấu trạng thái và thêm bình luận, giảm đáng kể rào cản xác minh thủ công.

Trong hiện thực của chúng ta, xác minh thủ công được thực hiện theo các bước sau:

1. Đọc đề, đáp án, lời giải
2. Chấm điểm (thang 1-5): tính đúng đắn, tính rõ ràng, độ khớp độ khó, tính đầy đủ
3. Đánh dấu trạng thái:
   - ✅ approved (đã duyệt)
   - ❌ rejected (từ chối)
   - 🔄 needs_revision (cần sửa)
4. Thêm bình luận

### 12.4.2 Kiến trúc hệ thống

Hệ thống sinh và đánh giá dữ liệu dùng thiết kế mô-đun hóa:

```
data_generation/
├── aime_generator.py              # Bộ sinh đề AIME
├── human_verification_ui.py       # Giao diện xác minh thủ công
├── run_complete_evaluation.py     # Quy trình đánh giá đầy đủ
│
├── generated_data/                # Dữ liệu được sinh
│   ├── aime_generated_XXXXXX.json
│   └── generation_report_XXXXXX.md
│
└── evaluation_results/            # Kết quả đánh giá
    └── XXXXXX/
        ├── llm_judge/
        ├── win_rate/
        └── comprehensive_report.md
```

Hệ thống gồm bốn thành phần cốt lõi: thứ nhất là AIMEGenerator (bộ sinh đề), dùng framework HelloAgents sinh đề theo phong cách AIME, hỗ trợ sinh hàng loạt và lưu tiến độ, tự động xử lý giới hạn tốc độ API; thứ hai là LLMJudgeTool (công cụ đánh giá LLM Judge), cung cấp đánh giá chất lượng 4 chiều, tự động sinh kết quả JSON và báo cáo Markdown; thứ ba là WinRateTool (công cụ đánh giá Win Rate), tính tỷ lệ thắng, tỷ lệ thua và tỷ lệ hòa qua đánh giá so sánh từng cặp; cuối cùng là HumanVerificationUI (giao diện xác minh thủ công), dựa trên giao diện Web Gradio, hỗ trợ chấm điểm và đánh dấu trạng thái.

### 12.4.3 Hiện thực bộ sinh đề AIME

```python
class AIMEGenerator:
    """AIME Problem Generator"""

    def __init__(
        self,
        llm: HelloAgentsLLM = None,
        delay_seconds: float = 1.0,
        use_reference_examples: bool = True,
        reference_dataset: str = "TianHongZXY/aime-1983-2025"
    ):
        self.llm = llm or HelloAgentsLLM()
        self.agent = SimpleAgent(
            name="AIME Generator",
            llm=self.llm,
            system_prompt="You are a professional mathematics competition problem designer."
        )
        self.delay_seconds = delay_seconds
        self.use_reference_examples = use_reference_examples

        # Load reference examples from 900+ AIME problems (1983-2025)
        if use_reference_examples:
            dataset = load_dataset(reference_dataset, split="test")
            self.reference_examples = list(dataset)
```
Mục tiêu của chúng ta là sinh tập dữ liệu có phong cách tương tự, nên chọn ngẫu nhiên mẫu tham chiếu từ hơn 900 đề AIME thực tế (1983-2025)

Thiết kế prompt sinh đề (tiếng Anh):

```python
GENERATION_PROMPT = """You are a professional mathematics competition problem designer, skilled in creating AIME (American Invitational Mathematics Examination) style problems.

【Reference Example】(For style reference only, please generate a completely different problem)
Problem: {example_problem}
Answer: {example_answer}

AIME Problem Characteristics:
1. Answer: An integer between 0 and 999
2. Topics: Algebra, Geometry, Number Theory, Combinatorics, Probability, etc.
3. Style: Requires multi-step reasoning, but no advanced theory
4. Difficulty: Medium to hard (similar to AIME problems 6-9)

Please generate a **completely different** AIME-style mathematics problem, including:
1. Problem statement (clear and complete, different from the reference)
2. Answer (an integer between 0 and 999, different from the reference)
3. Detailed solution (including all reasoning steps)
4. Topic classification (Algebra/Geometry/Number Theory/Combinatorics/Probability)

Please output in the following JSON format:
{
    "problem": "Problem statement in English",
    "answer": 123,
    "solution": "Detailed solution steps in English",
    "topic": "Algebra"
}
"""
```
Chúng ta chọn sinh đề bằng tiếng Anh vì bốn lý do quan trọng: thứ nhất là nhất quán với đề AIME thực tế (AIME là cuộc thi tiếng Anh, sinh đề tiếng Anh hợp lý hơn), thứ hai là đảm bảo tính công bằng của đánh giá (LLM Judge đánh giá tiếng Anh vs tiếng Anh công bằng hơn), thứ ba là thuận tiện quốc tế hóa (đề tiếng Anh có thể được dùng rộng rãi hơn), cuối cùng là tránh vấn đề dịch thuật (không cần lo tính chính xác của dịch Trung-Anh).

Hiện thực sinh hàng loạt:

```python
def generate_and_save(self, num_problems: int = 30, output_dir: str = "data_generation/generated_data"):
    """Generate and save problems with intelligent delay"""
    # Clean old checkpoints
    for file in os.listdir(output_dir):
        if file.startswith("checkpoint_") and file.endswith(".json"):
            os.remove(os.path.join(output_dir, file))

    # Generate with tqdm progress bar
    with tqdm(total=num_problems, desc="Generating AIME problems", unit="problem") as pbar:
        last_call_time = 0

        for i in range(num_problems):
            # Ensure minimum delay between API calls
            if last_call_time > 0:
                elapsed = time.time() - last_call_time
                if elapsed < self.delay_seconds:
                    wait_time = self.delay_seconds - elapsed
                    time.sleep(wait_time)

            # Generate problem (randomly select reference example)
            start_time = time.time()
            problem = self.generate_single()
            last_call_time = time.time()
            generation_time = last_call_time - start_time

            # Update progress bar
            pbar.set_postfix({
                "topic": problem.get('topic', 'N/A'),
                "answer": problem.get('answer', 'N/A'),
                "time": f"{generation_time:.1f}s"
            })
            pbar.update(1)

    return generated_data_path
```
Hỗ trợ công thức toán LaTeX:

Đề AIME được sinh chứa công thức toán LaTeX (như `$\frac{a}{b}$`, `$\sqrt{x}$`), cần xử lý đặc biệt khi phân tích JSON:

```python
def _parse_response(self, response: str) -> Dict[str, Any]:
    """Phân tích phản hồi LLM (hỗ trợ công thức toán LaTeX)"""
    import re

    # Trích xuất phần JSON
    if "```json" in response:
        json_str = response.split("```json")[1].split("```")[0].strip()
    else:
        json_str = response.strip()

    try:
        problem_data = json.loads(json_str)
    except json.JSONDecodeError:
        # Sửa vấn đề escape LaTeX: chuyển \frac thành \\frac
        # Biểu thức chính quy: tìm dấu gạch chéo ngược chưa được escape
        fixed_json_str = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', json_str)
        problem_data = json.loads(fixed_json_str)

    return problem_data
```
Dấu gạch chéo ngược trong công thức LaTeX (như `\frac`, `\sqrt`) là ký tự escape không hợp lệ trong JSON, sẽ khiến phân tích thất bại:
```
Invalid \escape: line 4 column 185 (char 375)
```

Dùng biểu thức chính quy thay dấu gạch chéo ngược chưa escape bằng hai dấu gạch chéo ngược, làm cho nó hợp lệ trong JSON.

### 12.4.4 Công cụ đánh giá LLM Judge

Công cụ LLM Judge dùng LLM làm giám khảo, đánh giá đa chiều các đề được sinh.

```python
class LLMJudgeTool(Tool):
    """Công cụ đánh giá LLM Judge"""

    def run(self, params: Dict[str, Any]) -> str:
        """Chạy đánh giá LLM Judge"""
        # 1. Nạp dữ liệu được sinh
        gen_dataset = AIDataset(dataset_type="generated", data_path=params["generated_data_path"])
        gen_problems = gen_dataset.load()

        # 2. Nạp dữ liệu tham chiếu (AIME 2025)
        ref_dataset = AIDataset(dataset_type="real", year=2025)
        ref_problems = ref_dataset.load()

        # 3. Tạo bộ đánh giá
        evaluator = LLMJudgeEvaluator(llm=self.llm, judge_model=params.get("judge_model", "gpt-4o"))

        # 4. Chạy đánh giá
        results = evaluator.evaluate_batch(gen_problems, max_samples=params.get("max_samples"))

        # 5. Lưu kết quả
        evaluator.export_results(results, result_file)

        # 6. Sinh báo cáo
        self._generate_report(results, report_file)

        return json.dumps({"status": "success", "metrics": results["metrics"]})
```
**Prompt đánh giá**:

```python
EVALUATION_PROMPT = """Hãy đánh giá chất lượng của đề toán AIME sau đây.

Đề bài:
{problem}

Đáp án: {answer}

Lời giải:
{solution}

Hãy chấm điểm theo 4 chiều sau (thang 1-5):

1. <strong>Tính đúng đắn (Correctness)</strong>: logic toán học có đúng không, đáp án có chính xác không
2. <strong>Tính rõ ràng (Clarity)</strong>: đề bài có diễn đạt rõ ràng không, lời giải có dễ hiểu không
3. <strong>Độ khớp độ khó (Difficulty Match)</strong>: độ khó có phù hợp tiêu chuẩn AIME không (trung bình đến khó)
4. <strong>Tính đầy đủ (Completeness)</strong>: các bước giải có đầy đủ không, có bao gồm suy luận cần thiết không

Hãy xuất theo định dạng JSON sau:
{
    "correctness": 5,
    "clarity": 4,
    "difficulty_match": 4,
    "completeness": 5,
    "comments": "lý do đánh giá"
}
"""
```

**Ví dụ báo cáo đánh giá**:

```markdown
# Báo cáo đánh giá LLM Judge

## Điểm tổng thể

- <strong>Điểm trung bình tổng</strong>: 4.2/5.0
- <strong>Tỷ lệ đạt</strong>: 85.0% (≥3.5 điểm)
- <strong>Tỷ lệ xuất sắc</strong>: 40.0% (≥4.5 điểm)

## Điểm từng chiều

| Chiều | Điểm trung bình | Xếp loại |
|------|--------|------|
| Tính đúng đắn | 4.3/5.0 | Tốt ⭐⭐⭐⭐ |
| Tính rõ ràng | 4.1/5.0 | Tốt ⭐⭐⭐⭐ |
| Độ khớp độ khó | 4.0/5.0 | Tốt ⭐⭐⭐⭐ |
| Tính đầy đủ | 4.4/5.0 | Tốt ⭐⭐⭐⭐ |
```

### 12.4.5 Công cụ đánh giá Win Rate

Công cụ Win Rate đánh giá chất lượng dữ liệu được sinh so với đề thực tế qua so sánh từng cặp.

```python
class WinRateTool(Tool):
    """Công cụ đánh giá Win Rate"""

    def run(self, params: Dict[str, Any]) -> str:
        """Chạy đánh giá Win Rate"""
        # 1. Nạp dữ liệu được sinh
        gen_dataset = AIDataset(dataset_type="generated", data_path=params["generated_data_path"])
        gen_problems = gen_dataset.load()

        # 2. Nạp dữ liệu tham chiếu (AIME 2025)
        ref_dataset = AIDataset(dataset_type="real", year=2025)
        ref_problems = ref_dataset.load()

        # 3. Tạo bộ đánh giá
        evaluator = WinRateEvaluator(llm=self.llm, judge_model=params.get("judge_model", "gpt-4o"))

        # 4. Chạy đánh giá
        results = evaluator.evaluate_win_rate(gen_problems, ref_problems, num_comparisons=params.get("num_comparisons"))

        # 5. Lưu kết quả và báo cáo
        evaluator.export_results(results, result_file)
        self._generate_report(results, report_file)

        return json.dumps({"status": "success", "metrics": results["metrics"]})
```
AIDataset chịu trách nhiệm nạp dữ liệu được sinh và dữ liệu đề AIME thực tế, hỗ trợ hai loại dữ liệu:

```python
class AIDataset:
    """Bộ nạp tập dữ liệu AI

    Hỗ trợ hai loại dữ liệu:
    1. generated: dữ liệu được sinh (định dạng JSON)
    2. real: đề AIME thực tế (nạp từ HuggingFace)
    """

    def __init__(
        self,
        dataset_type: str = "generated",
        data_path: Optional[str] = None,
        year: Optional[int] = None
    ):
        self.dataset_type = dataset_type
        self.data_path = data_path
        self.year = year  # Chỉ dùng cho loại real, mặc định 2025

    def load(self) -> List[Dict[str, Any]]:
        """Nạp tập dữ liệu"""
        if self.dataset_type == "generated":
            return self._load_generated_data()
        elif self.dataset_type == "real":
            return self._load_real_data()

    def _load_real_data(self) -> List[Dict[str, Any]]:
        """Nạp đề AIME 2025 thực tế từ HuggingFace"""
        from huggingface_hub import snapshot_download

        # Dùng tập dữ liệu AIME 2025
        repo_id = "math-ai/aime25"

        # Tải tập dữ liệu
        local_dir = snapshot_download(
            repo_id=repo_id,
            repo_type="dataset"
        )

        # Đọc tệp JSONL
        data_file = list(Path(local_dir).glob("*.jsonl"))[0]
        data = []
        with open(data_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))

        # Chuẩn hóa định dạng dữ liệu (AIME 2025 dùng tên trường chữ thường)
        problems = []
        for idx, item in enumerate(data):
            problem = {
                "problem_id": item.get("id", f"aime_2025_{idx}"),
                "problem": item.get("problem", ""),
                "answer": item.get("answer", ""),
                "solution": item.get("solution", ""),  # AIME 2025 không có trường solution
            }
            problems.append(problem)

        return problems
```
Chúng ta chọn chỉ dùng tập dữ liệu AIME 2025 vì bốn lý do: thứ nhất là tính thời sự của dữ liệu (2025 là dữ liệu kỳ thi AIME mới nhất), thứ hai là đơn giản hóa bảo trì (chỉ bảo trì một tập dữ liệu, mã gọn hơn), thứ ba là định dạng thống nhất (định dạng JSONL, tên trường thống nhất chữ thường), cuối cùng là tính đại diện đầy đủ (30 đề đủ để đánh giá chất lượng sinh).

**Prompt so sánh**:

```python
COMPARISON_PROMPT = """Hãy so sánh chất lượng của hai đề toán AIME sau đây và phán đoán đề nào tốt hơn.

[Đề A - đề được sinh]
Đề bài: {problem_a}
Đáp án: {answer_a}
Lời giải: {solution_a}

[Đề B - đề AIME thực tế]
Đề bài: {problem_b}
Đáp án: {answer_b}
Lời giải: {solution_b}

Hãy so sánh theo các mặt sau:
1. Tính chặt chẽ của logic toán học
2. Tính rõ ràng của đề bài
3. Tính hợp lý của độ khó
4. Tính đầy đủ của lời giải

Hãy xuất theo định dạng JSON sau:
{
    "winner": "A" hoặc "B" hoặc "Tie",
    "reason": "lý do phán đoán"
}
"""
```

**Ví dụ báo cáo đánh giá**:

```markdown
# Báo cáo đánh giá Win Rate

## Thống kê tỷ lệ thắng

| Chỉ số | Giá trị | Phần trăm |
|------|------|--------|
| Dữ liệu được sinh thắng | 9 lần | 45.0% |
| Đề AIME thực tế thắng | 8 lần | 40.0% |
| Hòa | 3 lần | 15.0% |

<strong>Win Rate</strong>: 45.0%

✅ <strong>Tốt</strong>: chất lượng dữ liệu được sinh gần với dữ liệu tham chiếu (chênh lệch <10%).
```

### 12.4.6 Giao diện xác minh thủ công

Dùng Gradio tạo giao diện Web, hỗ trợ xác minh thủ công các đề được sinh.

```python
class HumanVerificationUI:
    """Giao diện xác minh thủ công"""

    def launch(self, share: bool = False):
        """Khởi động giao diện Gradio"""
        with gr.Blocks(title="Xác minh thủ công đề AIME") as demo:
            gr.Markdown("# 🎯 Hệ thống xác minh thủ công đề AIME")

            with gr.Row():
                with gr.Column(scale=2):
                    # Vùng hiển thị đề
                    problem_text = gr.Textbox(label="Mô tả đề bài", lines=5, interactive=False)
                    answer_text = gr.Textbox(label="Đáp án", interactive=False)
                    solution_text = gr.Textbox(label="Quá trình giải", lines=10, interactive=False)

                with gr.Column(scale=1):
                    # Vùng chấm điểm
                    correctness_slider = gr.Slider(1, 5, value=3, step=1, label="Tính đúng đắn")
                    clarity_slider = gr.Slider(1, 5, value=3, step=1, label="Tính rõ ràng")
                    difficulty_slider = gr.Slider(1, 5, value=3, step=1, label="Độ khớp độ khó")
                    completeness_slider = gr.Slider(1, 5, value=3, step=1, label="Tính đầy đủ")

                    # Chọn trạng thái
                    status_radio = gr.Radio(
                        choices=["approved", "rejected", "needs_revision"],
                        value="approved",
                        label="Trạng thái"
                    )

                    # Nút xác minh
                    verify_btn = gr.Button("✅ Gửi xác minh", variant="primary")

            demo.launch(share=share, server_name="127.0.0.1", server_port=7860)
```
**Cách dùng**:

```bash
# Khởi động giao diện xác minh thủ công
python data_generation/human_verification_ui.py data_generation/generated_data/aime_generated_XXXXXX.json

# Mở trình duyệt truy cập
http://127.0.0.1:7860
```

Hiệu ứng cuối cùng có thể tham khảo như Hình 12.7; với tính đúng đắn của đề, tốt nhất nên gắn nhãn đánh giá thủ công Review:
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/12-figures/12-7.png" alt="" width="85%"/>
  <p>Hình 12.7 Trang xác minh thủ công đề AIME</p>
</div>

**Quy trình xác minh**:

1. Mở giao diện xác minh trên trình duyệt
2. Đọc đề, đáp án, lời giải
3. Chấm điểm theo 4 chiều (thang 1-5)
4. Chọn trạng thái xác minh (approved/rejected/needs_revision)
5. Thêm bình luận (tùy chọn)
6. Nhấn "Gửi xác minh"
7. Xem đề tiếp theo

**Lưu kết quả xác minh**:

Kết quả xác minh được tự động lưu thành `<data_path>_verifications.json`:

```json
{
  "gen_aime_1": {
    "problem_id": "gen_aime_1",
    "scores": {
      "correctness": 5,
      "clarity": 4,
      "difficulty_match": 4,
      "completeness": 5
    },
    "total_score": 4.5,
    "status": "approved",
    "comments": "Chất lượng đề rất tốt, logic chặt chẽ",
    "verified_at": "2025-01-10T12:00:00"
  }
}
```

### 12.4.7 Quy trình đánh giá đầy đủ

Tích hợp tất cả phương pháp đánh giá vào một quy trình hoàn chỉnh.

```python
def run_complete_evaluation(
    num_problems: int = 30,
    delay_seconds: float = 3.0
):
    """
    Chạy quy trình đánh giá đầy đủ

    Args:
        num_problems: số lượng đề cần sinh
        delay_seconds: độ trễ giữa các lần sinh (giây), tránh giới hạn tốc độ API
    """
    # Bước 1: sinh đề AIME
    generator = AIMEGenerator(delay_seconds=delay_seconds)
    generated_data_path = generator.generate_and_save(
        num_problems=num_problems,
        output_dir="data_generation/generated_data"
    )

    # Bước 2: đánh giá
    # Tạo thư mục kết quả đánh giá
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    evaluation_dir = f"data_generation/evaluation_results/{timestamp}"
    os.makedirs(evaluation_dir, exist_ok=True)
    os.makedirs(os.path.join(evaluation_dir, "llm_judge"), exist_ok=True)
    os.makedirs(os.path.join(evaluation_dir, "win_rate"), exist_ok=True)

    # Tạo LLM
    llm = HelloAgentsLLM()

    # Bước 2.1: đánh giá LLM Judge
    llm_judge_result = None
    try:
        llm_judge_tool = LLMJudgeTool(llm=llm)
        llm_judge_result_json = llm_judge_tool.run({
            "generated_data_path": generated_data_path,
            "reference_year": 2025,
            "max_samples": num_problems,
            "output_dir": os.path.join(evaluation_dir, "llm_judge"),
            "judge_model": "gpt-4o"
        })
        llm_judge_result = json.loads(llm_judge_result_json)
    except Exception as e:
        print(f"❌ Đánh giá LLM Judge thất bại: {e}")

    # Bước 2.2: đánh giá Win Rate
    win_rate_result = None
    try:
        win_rate_tool = WinRateTool(llm=llm)
        win_rate_result_json = win_rate_tool.run({
            "generated_data_path": generated_data_path,
            "reference_year": 2025,
            "num_comparisons": min(num_problems, 20),
            "output_dir": os.path.join(evaluation_dir, "win_rate"),
            "judge_model": "gpt-4o"
        })
        win_rate_result = json.loads(win_rate_result_json)
    except Exception as e:
        print(f"❌ Đánh giá Win Rate thất bại: {e}")

    # Bước 3: sinh báo cáo tổng hợp
    comprehensive_report_path = None
    if llm_judge_result or win_rate_result:
        comprehensive_report_path = os.path.join(evaluation_dir, "comprehensive_report.md")
        report = generate_comprehensive_report(
            generated_data_path,
            llm_judge_result,
            win_rate_result
        )
        with open(comprehensive_report_path, 'w', encoding='utf-8') as f:
            f.write(report)

    return {
        "generated_data_path": generated_data_path,
        "llm_judge_result": llm_judge_result,
        "win_rate_result": win_rate_result,
        "comprehensive_report_path": comprehensive_report_path
    }
```
**Cách chạy**:

```bash
# Cách dùng cơ bản (mặc định độ trễ 3 giây)
python data_generation/run_complete_evaluation.py 30

# Tùy chỉnh độ trễ (khuyến nghị 3-5 giây, tránh giới hạn tốc độ API)
python data_generation/run_complete_evaluation.py 30 3.0

# Mô tả tham số:
# - 30: số lượng đề cần sinh
# - 3.0: độ trễ giữa các lần sinh (giây)

# Ghi chú:
# - Giai đoạn sinh: chọn ngẫu nhiên mẫu tham chiếu từ hơn 900 đề AIME thực tế (1983-2025)
# - Giai đoạn đánh giá: so sánh chất lượng với đề AIME 2025 thực tế
# - Nguồn tập dữ liệu: math-ai/aime25 (định dạng JSONL)
```

**Ví dụ đầu ra**:

```
================================================================================
🚀 Quy trình đầy đủ sinh và đánh giá dữ liệu AIME
================================================================================

Thông tin cấu hình:
  - Số lượng đề cần sinh: 30
  - Độ trễ API: 3.0 giây/đề
  - Dữ liệu tham chiếu khi sinh: TianHongZXY/aime-1983-2025 (900+ đề)
  - Tham chiếu đánh giá: đề AIME 2025 thực tế

================================================================================
📝 Bước 1: Sinh đề AIME
================================================================================
📚 Nạp tập dữ liệu đề AIME thực tế: TianHongZXY/aime-1983-2025
   ✓ Đã nạp 963 đề tham chiếu

🎯 Bắt đầu sinh đề AIME
   Số lượng mục tiêu: 30
   Mô hình sinh: gpt-4o
   Thiết lập độ trễ: 3.0 giây/đề

Sinh đề AIME:  100%|██████████| 30/30 [01:30<00:00, 3.00s/đề, chủ đề=Algebra, đáp án=123, thời gian=3.0s]

✅ Bước 1 hoàn tất! Dữ liệu được sinh lưu tại: data_generation/generated_data/aime_generated_20250110_120000.json

🎯 Bước 2.1: Đánh giá LLM Judge (vs AIME 2025)

✅ Đánh giá LLM Judge hoàn tất!
   Điểm trung bình tổng: 4.2/5.0
   Tỷ lệ đạt: 85.0%

🏆 Bước 2.2: Đánh giá Win Rate (vs AIME 2025)

✅ Đánh giá Win Rate hoàn tất!
   Win Rate: 45.0%

================================================================================
📊 Bước 3: Sinh báo cáo tổng hợp
================================================================================

✅ Báo cáo tổng hợp đã được lưu: data_generation/evaluation_results/20250110_120000/comprehensive_report.md

================================================================================
🎉 Quy trình đánh giá đầy đủ hoàn tất!
================================================================================

📁 Tệp đầu ra:
   - Dữ liệu được sinh: data_generation/generated_data/aime_generated_20250110_120000.json
   - Thư mục kết quả đánh giá: data_generation/evaluation_results/20250110_120000
   - Báo cáo LLM Judge: data_generation/evaluation_results/20250110_120000/llm_judge/llm_judge_report_20250110_120000.md
   - Báo cáo Win Rate: data_generation/evaluation_results/20250110_120000/win_rate/win_rate_report_20250110_120000.md
   - Báo cáo tổng hợp: data_generation/evaluation_results/20250110_120000/comprehensive_report.md

💡 Bước tiếp theo:
   1. Xem báo cáo tổng hợp: data_generation/evaluation_results/20250110_120000/comprehensive_report.md
   2. Chạy xác minh thủ công: python data_generation/human_verification_ui.py data_generation/generated_data/aime_generated_20250110_120000.json
```

### 12.4.8 Báo cáo đánh giá tổng hợp

Hệ thống tự động sinh báo cáo đánh giá tổng hợp, tập hợp tất cả kết quả đánh giá. Dưới đây là báo cáo mẫu:

```markdown
# Báo cáo tổng hợp sinh và đánh giá dữ liệu AIME

## 1. Thông tin cơ bản

- <strong>Thời điểm sinh</strong>: 2025-01-10 12:00:00
- <strong>Số lượng đề được sinh</strong>: 30
- <strong>Năm AIME tham chiếu</strong>: 2025

## 2. Thống kê sinh dữ liệu

### Phân bố chủ đề

| Chủ đề | Số lượng | Tỷ lệ |
|------|------|------|
| Đại số | 10 | 33.3% |
| Hình học | 8 | 26.7% |
| Lý thuyết số | 7 | 23.3% |
| Tổ hợp | 3 | 10.0% |
| Xác suất | 2 | 6.7% |

## 3. Kết quả đánh giá LLM Judge

### Điểm tổng thể

- <strong>Điểm trung bình tổng</strong>: 4.2/5.0
- <strong>Tỷ lệ đạt</strong>: 85.0% (≥3.5 điểm)
- <strong>Tỷ lệ xuất sắc</strong>: 40.0% (≥4.5 điểm)

### Điểm từng chiều

| Chiều | Điểm trung bình | Xếp loại |
|------|--------|------|
| Tính đúng đắn | 4.3/5.0 | Tốt ⭐⭐⭐⭐ |
| Tính rõ ràng | 4.1/5.0 | Tốt ⭐⭐⭐⭐ |
| Độ khớp độ khó | 4.0/5.0 | Tốt ⭐⭐⭐⭐ |
| Tính đầy đủ | 4.4/5.0 | Tốt ⭐⭐⭐⭐ |

## 4. Kết quả đánh giá Win Rate

### Thống kê tỷ lệ thắng

| Chỉ số | Giá trị | Phần trăm |
|------|------|--------|
| Dữ liệu được sinh thắng | 9 lần | 45.0% |
| Đề AIME thực tế thắng | 8 lần | 40.0% |
| Hòa | 3 lần | 15.0% |

<strong>Win Rate</strong>: 45.0%

✅ <strong>Tốt</strong>: chất lượng dữ liệu được sinh gần với dữ liệu tham chiếu (chênh lệch <10%).

## 5. Kết luận tổng hợp

Dựa trên kết quả của hai phương pháp đánh giá LLM Judge và Win Rate:

1. <strong>Đánh giá LLM Judge</strong>: chất lượng trung bình của dữ liệu được sinh là <strong>4.2/5.0</strong>
2. <strong>Đánh giá Win Rate</strong>: tỷ lệ thắng của dữ liệu được sinh so với đề AIME 2025 thực tế là <strong>45.0%</strong>

✅ <strong>Kết luận</strong>: chất lượng dữ liệu được sinh <strong>xuất sắc</strong>, đạt hoặc vượt mức đề AIME thực tế. Có thể dùng cho ứng dụng thực tế.

## 6. Khuyến nghị cải thiện

- ✅ Tiếp tục duy trì chiến lược sinh hiện tại
- ✅ Có thể cân nhắc tăng số lượng sinh
- ✅ Khuyến nghị xác minh thủ công để đảm bảo chất lượng

## 7. Hành động tiếp theo

1. <strong>Xác minh thủ công</strong>: chạy `python data_generation/human_verification_ui.py <data_path>` để xác minh thủ công
2. <strong>Xem kết quả chi tiết</strong>:
   - Báo cáo chi tiết LLM Judge
   - Báo cáo chi tiết Win Rate
3. <strong>Sử dụng dữ liệu</strong>: nếu hài lòng với chất lượng, có thể dùng dữ liệu được sinh cho huấn luyện hoặc kiểm thử
```

Dựa trên kinh nghiệm sử dụng thực tế, tổng kết nội dung sau:

Về sinh dữ liệu, nên dùng độ trễ phù hợp (2-3 giây) để tránh giới hạn tốc độ API, bật lưu điểm kiểm tra để tránh mất mát khi bị gián đoạn, kiểm thử lô nhỏ (10 đề) trước để xác nhận không có vấn đề rồi mới sinh lô lớn, và định kỳ kiểm tra chất lượng sinh để kịp thời điều chỉnh prompt. Về chiến lược đánh giá, khuyến nghị kết hợp hai phương pháp LLM Judge và Win Rate, trong đó LLM Judge dùng đánh giá chất lượng tuyệt đối, Win Rate dùng so sánh chất lượng tương đối, xác minh thủ công dùng kiểm soát chất lượng cuối cùng. Về tiêu chuẩn chất lượng, khuyến nghị điểm trung bình LLM Judge đạt 4.0/5.0 trở lên, Win Rate đạt 45% trở lên (gần 50%), tỷ lệ đạt đạt 80% trở lên, tỷ lệ đạt xác minh thủ công đạt 90% trở lên. Trong quá trình lặp tối ưu, nên điều chỉnh prompt sinh theo kết quả đánh giá, phân tích vấn đề chung của các đề điểm thấp, tham khảo ưu điểm của các đề điểm cao, không ngừng cải thiện chiến lược sinh.

Qua phần học này, chúng ta đã nắm cách dùng framework HelloAgents để đánh giá chất lượng sinh dữ liệu, gồm ba phương pháp: đánh giá LLM Judge, đánh giá Win Rate và xác minh thủ công. Hệ thống đánh giá hoàn chỉnh này có thể đảm bảo chất lượng cao của dữ liệu được sinh, cung cấp hỗ trợ dữ liệu đáng tin cậy cho huấn luyện và kiểm thử hệ thống AI.

Với đánh giá LLM Judge và Win Rate, HelloAgents cũng đã tích hợp công cụ và cung cấp mã ví dụ đầy đủ. Nếu bạn quan tâm chi tiết hiện thực của hai phương pháp đánh giá này, cũng có thể tham khảo mã ví dụ.

## 12.5 Tóm tắt chương

Trong chương này, chúng ta đã xây dựng một hệ thống đánh giá hiệu năng hoàn chỉnh cho framework HelloAgents. Hãy ôn lại những nội dung cốt lõi đã học:

<strong>(1) Tổng quan hệ thống đánh giá</strong>

Chúng ta đã thiết lập một hệ thống đánh giá ba tầng, bao phủ toàn diện các chiều năng lực khác nhau của Agent. Thứ nhất là đánh giá năng lực gọi công cụ (BFCL), tập trung đánh giá độ chính xác gọi hàm của Agent, gồm bốn hạng mục simple, multiple, parallel, irrelevance, dùng kỹ thuật so khớp AST để đánh giá chính xác. Thứ hai là đánh giá năng lực tổng quát (GAIA), đánh giá năng lực giải quyết vấn đề tổng hợp của Agent, gồm 466 câu hỏi thế giới thực ở ba mức độ khó, chú trọng năng lực suy luận nhiều bước, sử dụng công cụ, xử lý tệp. Thứ ba là đánh giá chất lượng sinh dữ liệu (AIME), đánh giá chất lượng dữ liệu do LLM sinh ra, dùng hai phương pháp LLM Judge và Win Rate, hỗ trợ xác minh thủ công và sinh báo cáo tổng hợp, đảm bảo dữ liệu được sinh đạt tiêu chuẩn chất lượng của dữ liệu tham chiếu.

<strong>(2) Các điểm kỹ thuật cốt lõi</strong>

Về hiện thực kỹ thuật, chúng ta áp dụng sáu điểm kỹ thuật cốt lõi. Thứ nhất là thiết kế mô-đun hóa, hệ thống đánh giá dùng kiến trúc ba tầng: tầng dữ liệu (Dataset chịu trách nhiệm nạp và quản lý dữ liệu), tầng đánh giá (Evaluator chịu trách nhiệm thực thi quy trình đánh giá) và tầng chỉ số (Metrics chịu trách nhiệm tính các chỉ số đánh giá khác nhau). Thứ hai là đóng gói thành công cụ, mọi chức năng đánh giá đều được đóng gói thành Tool, có thể được Agent gọi trực tiếp, tích hợp vào quy trình làm việc hoặc dùng qua giao diện thống nhất. Thứ ba là kỹ thuật so khớp AST, dùng cây cú pháp trừu tượng để so khớp lệnh gọi hàm, thông minh hơn so khớp chuỗi đơn giản, có thể bỏ qua thứ tự tham số, nhận diện biểu thức tương đương và bỏ qua khác biệt định dạng. Thứ tư là hỗ trợ đa phương thức, đánh giá GAIA hỗ trợ dữ liệu đa phương thức như câu hỏi văn bản, tệp đính kèm và đầu vào hình ảnh. Thứ năm là đánh giá bằng LLM Judge, dùng LLM làm giám khảo đánh giá chất lượng dữ liệu được sinh, cung cấp chấm điểm đa chiều (tính đúng đắn, tính rõ ràng, độ khớp độ khó, tính đầy đủ), quy trình đánh giá tự động, báo cáo đánh giá chi tiết, và hỗ trợ tùy biến chiều và tiêu chuẩn đánh giá. Thứ sáu là đánh giá so sánh Win Rate, đánh giá chất lượng sinh qua so sánh từng cặp (dữ liệu được sinh vs dữ liệu tham chiếu), LLM phán đoán cái nào tốt hơn và tính thống kê tỷ lệ thắng, gần 50% nghĩa là chất lượng tương đương.

<strong>(3) Hướng mở rộng</strong>

Dựa trên hệ thống đánh giá của chương này, bạn có thể mở rộng theo bốn hướng. Thứ nhất là thêm benchmark đánh giá mới: có thể tham khảo mô hình hiện thực của BFCL và GAIA, hiện thực ba thành phần Dataset, Evaluator, Metrics, và đóng gói thành Tool để sử dụng. Thứ hai là tùy biến chỉ số đánh giá: thêm phương thức tính chỉ số mới trong lớp Metrics, thiết kế chỉ số theo kịch bản ứng dụng cụ thể. Thứ ba là tích hợp vào quy trình CI/CD: tự động chạy đánh giá khi gửi mã, đặt ngưỡng hiệu năng để ngăn suy giảm hiệu năng, sinh báo cáo đánh giá và lưu trữ. Thứ tư là mở rộng đánh giá sinh dữ liệu: hỗ trợ thêm nhiều loại dữ liệu (mã, đối thoại, tài liệu, v.v.), thêm nhiều chiều đánh giá (tính sáng tạo, tính đa dạng, v.v.), tích hợp thêm tập dữ liệu tham chiếu, hỗ trợ đánh giá so sánh đa mô hình.

<strong>Chúc mừng bạn đã hoàn thành chương 12!</strong> 🎉

Đánh giá là khâu quan trọng trong phát triển Agent; nó cho phép chúng ta:

- Đo lường năng lực của Agent một cách khách quan
- Phát hiện và sửa chữa vấn đề
- Không ngừng cải thiện hệ thống

Ở chương tiếp theo, chúng ta sẽ tìm hiểu cách áp dụng framework HelloAgents vào các dự án thực tế.

<strong>Tiếp tục cố gắng nhé!</strong> 💪

## Bài tập

> <strong>Gợi ý</strong>: một số bài tập không có đáp án chuẩn; trọng tâm là rèn luyện hiểu biết tổng hợp và năng lực thực hành của người học về đánh giá hiệu năng Agent.

1. Chương này giới thiệu nhiều benchmark đánh giá Agent. Hãy phân tích:

   - Mục 12.1.2 đã giới thiệu các benchmark đánh giá như BFCL, GAIA, AgentBench. Hãy so sánh BFCL và GAIA: chúng đánh giá những năng lực cốt lõi nào của Agent? Vì sao BFCL dùng thuật toán so khớp AST, còn GAIA dùng khớp gần đúng chính xác (Quasi Exact Match)? Hai phương pháp đánh giá này có ưu nhược điểm gì?
   - Giả sử bạn cần xây dựng một "hệ thống chăm sóc khách hàng thông minh", cần đánh giá các năng lực sau: (1) độ chính xác trong việc hiểu ý định người dùng; (2) tính đúng đắn khi gọi API phía sau; (3) tính thân thiện và chuyên nghiệp của câu trả lời; (4) độ bền vững khi xử lý tình huống bất thường. Hãy chọn hoặc thiết kế chỉ số và phương pháp đánh giá phù hợp cho từng năng lực.
   - Mục 12.1.1 đề cập đánh giá Agent đối mặt ba thách thức lớn: "tính không xác định của đầu ra", "tính đa dạng của tiêu chuẩn đánh giá", "chi phí đánh giá cao". Hãy đề xuất giải pháp cụ thể cho từng thách thức, và phân tích tính khả thi, hạn chế của giải pháp.

2. BFCL (Berkeley Function Calling Leaderboard) là benchmark quan trọng để đánh giá năng lực gọi công cụ. Dựa trên nội dung mục 12.2, hãy suy nghĩ sâu:

   > <strong>Gợi ý</strong>: đây là bài tập thực hành, khuyến nghị thao tác thực tế

   - Trong thuật toán so khớp AST ở mục 12.2.3, chúng ta phán đoán lệnh gọi hàm có đúng hay không bằng cách so sánh cây cú pháp trừu tượng. Hãy phân tích: vì sao so khớp AST phù hợp hơn so khớp chuỗi đơn giản? Trong trường hợp nào so khớp AST có thể đưa ra phán đoán sai (dương tính giả hoặc âm tính giả)? Làm sao cải thiện thuật toán so khớp AST để nâng cao độ chính xác?
   - Tập dữ liệu BFCL gồm bốn hạng mục simple, multiple, parallel, irrelevance. Hãy thiết kế 2-3 mẫu kiểm thử mới cho mỗi hạng mục, yêu cầu có thể kiểm tra các trường hợp biên hoặc kịch bản dễ gây lỗi của Agent trong hạng mục đó.
   - Dựa trên mã ở mục 12.2.4, hãy mở rộng bộ đánh giá BFCL, thêm các chức năng sau: (1) hỗ trợ đánh giá thứ tự thực thi của lệnh gọi công cụ (với nhiều lệnh gọi công cụ có quan hệ phụ thuộc); (2) đánh giá hiệu quả gọi công cụ (ví dụ có dùng số lần gọi tối thiểu hay không); (3) sinh báo cáo phân tích lỗi chi tiết (ví dụ loại lỗi nào phổ biến nhất).

3. GAIA (General AI Assistants) đánh giá năng lực tổng hợp của Agent. Dựa trên nội dung mục 12.3, hãy hoàn thành các bài thực hành mở rộng sau:

   > <strong>Gợi ý</strong>: đây là bài tập thực hành, khuyến nghị thao tác thực tế

   - Mục 12.3.2 đã giới thiệu ba mức độ khó của GAIA (Level 1/2/3). Hãy phân tích: ba mức này khác nhau thế nào về độ phức tạp nhiệm vụ, năng lực cần thiết, tiêu chuẩn đánh giá? Nếu thiết kế Level 4 (độ khó siêu cao), nên bao gồm những loại nhiệm vụ nào?
   - GAIA dùng thuật toán "khớp gần đúng chính xác" để đánh giá tính đúng đắn của câu trả lời. Hãy phân tích: phương pháp này xử lý tính đa dạng của câu trả lời như thế nào (ví dụ "42", "bốn mươi hai", "42.0" đều nên được coi là đúng)? Trong trường hợp nào khớp gần đúng chính xác có thể không đủ dùng? Hãy thiết kế một thuật toán so khớp câu trả lời thông minh hơn, có thể xử lý các câu trả lời tương đương về ngữ nghĩa.
   - Dựa trên mã ở mục 12.3.4, hãy hiện thực một "tập đánh giá GAIA tùy biến": chọn một lĩnh vực cụ thể (như y tế, pháp luật, tài chính), thiết kế 10 câu hỏi thế giới thực, và hiện thực quy trình đánh giá đầy đủ. Yêu cầu câu hỏi bao phủ các mức độ khó khác nhau, cung cấp đáp án chuẩn và tiêu chuẩn chấm điểm.

4. LLM Judge là phương pháp đánh giá mới nổi dùng mô hình ngôn ngữ lớn. Dựa trên nội dung mục 12.4, hãy phân tích sâu:

   - Ở mục 12.4.2, chúng ta dùng GPT-4 làm giám khảo để đánh giá chất lượng câu trả lời của Agent. Hãy phân tích: LLM Judge có ưu thế gì so với so khớp quy tắc truyền thống hoặc tính chỉ số? Nó có những thiên lệch hoặc hạn chế tiềm tàng nào (như thiên vị một số phong cách trả lời, nhạy cảm với độ dài)?
   - Thiết kế tiêu chuẩn chấm điểm của LLM Judge rất quan trọng. Hãy thiết kế tiêu chuẩn chấm điểm chi tiết (gồm chiều chấm điểm, trọng số, ví dụ) cho ba kịch bản đánh giá khác nhau: (1) đánh giá chất lượng sinh mã; (2) đánh giá chất lượng viết sáng tạo; (3) đánh giá chất lượng tài liệu kỹ thuật.
   - Mục 12.4.3 đề cập có thể dùng nhiều LLM Judge để đánh giá kiểu "hội đồng giám khảo". Hãy thiết kế một "hệ thống đánh giá đa giám khảo": dùng 3-5 LLM khác nhau (như GPT-4, Claude, Qwen) làm giám khảo, làm sao tổng hợp điểm của chúng? Làm sao xử lý bất đồng giữa các giám khảo? Làm sao phát hiện và lọc điểm bất thường?

5. Ứng dụng thực hành đánh giá Agent cần xét nhiều mặt. Hãy suy nghĩ:

   - Trong dự án thực tế, đánh giá thường cần cân bằng giữa "chi phí đánh giá" và "chất lượng đánh giá". Hãy thiết kế một "chiến lược đánh giá phân tầng": (1) đánh giá nhanh (chi phí thấp, dùng cho lặp phát triển hàng ngày); (2) đánh giá chuẩn (chi phí trung bình, dùng trước khi phát hành phiên bản); (3) đánh giá toàn diện (chi phí cao, dùng cho cập nhật lớn hoặc phát hành ra ngoài). Mỗi tầng nên gồm những hạng mục đánh giá nào? Thiết kế quy trình đánh giá ra sao?
   - Hiệu năng của Agent có thể thay đổi theo thời gian (như API bên ngoài phụ thuộc thay đổi, nhu cầu người dùng thay đổi). Hãy thiết kế một "hệ thống đánh giá liên tục": có thể định kỳ tự động chạy đánh giá, giám sát xu hướng thay đổi hiệu năng của Agent, và cảnh báo kịp thời khi hiệu năng suy giảm. Hệ thống này nên gồm những thành phần nào? Thiết kế quy tắc cảnh báo ra sao?
   - Kết quả đánh giá cần được trình bày rõ ràng cho các đối tượng khác nhau (như nhà phát triển, quản lý sản phẩm, người dùng). Hãy thiết kế một "hệ thống sinh báo cáo đánh giá": có thể tự động sinh báo cáo với mức chi tiết khác nhau theo loại đối tượng. Báo cáo cho nhà phát triển nên gồm những chi tiết kỹ thuật nào? Báo cáo cho quản lý sản phẩm nên làm nổi bật những chỉ số nghiệp vụ nào? Báo cáo cho người dùng nên đơn giản hóa và trực quan hóa như thế nào?

## Tài liệu tham khảo

[1] Patil, S. G., Zhang, T., Wang, X., & Gonzalez, J. E. (2023). Gorilla: Large Language Model Connected with Massive APIs. arXiv preprint arXiv:2305.15334.

[2] Qin, Y., Liang, S., Ye, Y., Zhu, K., Yan, L., Lu, Y., ... & Sun, M. (2023). ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs. arXiv preprint arXiv:2307.16789.

[3] Li, M., Zhao, Y., Yu, B., Song, F., Li, H., Yu, H., ... & Li, Y. (2023). Api-bank: A comprehensive benchmark for tool-augmented llms. arXiv preprint arXiv:2304.08244.

[4] Mialon, G., Dessì, R., Lomeli, M., Nalmpantis, C., Pasunuru, R., Raileanu, R., ... & Scialom, T. (2023). GAIA: a benchmark for General AI Assistants. arXiv preprint arXiv:2311.12983.

[5] Liu, X., Yu, H., Zhang, H., Xu, Y., Lei, X., Lai, H., ... & Zhang, D. (2023). AgentBench: Evaluating LLMs as Agents. arXiv preprint arXiv:2308.03688.

[6] Zhou, S., Xu, F. F., Zhu, H., Zhou, X., Lo, R., Sridhar, A., ... & Neubig, G. (2023). WebArena: A Realistic Web Environment for Building Autonomous Agents. arXiv preprint arXiv:2307.13854.

[7] Chan, C. M., Chen, W., Su, Y., Yu, J., Xue, W., Zhang, S., ... & Liu, Z. (2023). ChatEval: Towards Better LLM-based Evaluators through Multi-Agent Debate. arXiv preprint arXiv:2308.07201.

[8] Zhou, X., Zhu, H., Mathur, L., Zhang, R., Yu, H., Qi, Z., ... & Neubig, G. (2023). SOTOPIA: Interactive Evaluation for Social Intelligence in Language Agents. arXiv preprint arXiv:2310.11667.

[9] Mathematical Association of America. (2024). American Invitational Mathematics Examination (AIME). Retrieved from https://www.maa.org/math-competitions/invitational-competitions/aime

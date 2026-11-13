# Chương 4: Xây dựng các mô hình Agent kinh điển

Ở chương trước, chúng ta đã đi sâu tìm hiểu mô hình ngôn ngữ lớn – “bộ não” của Agent hiện đại. Chúng ta đã biết về kiến trúc Transformer bên trong nó, cách tương tác với nó, cũng như ranh giới năng lực của nó. Giờ đây, đã đến lúc biến những kiến thức lý thuyết này thành thực hành, tự tay xây dựng một Agent.

Năng lực cốt lõi của một Agent hiện đại nằm ở việc kết nối khả năng suy luận của mô hình ngôn ngữ lớn với thế giới bên ngoài. Nó có thể tự chủ hiểu ý định của người dùng, phân rã các nhiệm vụ phức tạp, và thông qua việc gọi một loạt “công cụ” như trình thông dịch mã, công cụ tìm kiếm, API… để thu thập thông tin, thực hiện thao tác, và cuối cùng đạt được mục tiêu. Tuy nhiên, Agent không phải vạn năng; nó cũng đối mặt với vấn đề “ảo giác” đến từ chính mô hình lớn, nguy cơ rơi vào vòng lặp suy luận khi gặp nhiệm vụ phức tạp, cũng như việc sử dụng công cụ sai cách. Những điều này tạo nên ranh giới năng lực của Agent.

Để tổ chức quá trình “suy nghĩ” và “hành động” của Agent tốt hơn, ngành công nghiệp đã cho ra đời nhiều mô hình kiến trúc kinh điển. Trong chương này, chúng ta sẽ tập trung vào ba mô hình tiêu biểu nhất và từng bước hiện thực chúng từ con số không:

- **ReAct (Reasoning and Acting):** một mô hình kết hợp chặt chẽ “suy nghĩ” và “hành động”, cho phép Agent vừa nghĩ vừa làm và điều chỉnh linh hoạt.
- **Plan-and-Solve:** một mô hình “suy nghĩ kỹ rồi mới hành động”, trong đó Agent trước tiên tạo ra một kế hoạch hành động hoàn chỉnh, sau đó thực thi nghiêm ngặt.
- **Reflection:** một mô hình trao cho Agent khả năng “tự phản tư”, tối ưu hóa kết quả thông qua tự phê bình và sửa chữa.

Sau khi hiểu những điều này, bạn có thể sẽ hỏi: trên thị trường đã có nhiều framework xuất sắc như LangChain, LlamaIndex, tại sao lại phải “phát minh lại bánh xe”? Câu trả lời nằm ở chỗ: mặc dù các framework trưởng thành có ưu thế rõ rệt về hiệu quả kỹ thuật, việc trực tiếp sử dụng những công cụ được trừu tượng hóa cao không có lợi cho việc tìm hiểu cơ chế thiết kế bên trong vận hành ra sao, hoặc nó mang lại lợi ích gì. Thứ hai, quá trình này sẽ bộc lộ những thách thức kỹ thuật của dự án. Framework xử lý giúp chúng ta nhiều vấn đề, chẳng hạn như phân tích định dạng đầu ra của mô hình, thử lại khi gọi công cụ thất bại, ngăn Agent rơi vào vòng lặp vô hạn… Việc tự tay xử lý những vấn đề này là cách trực tiếp nhất để rèn luyện năng lực thiết kế hệ thống. Cuối cùng, và cũng là quan trọng nhất, khi đã nắm vững nguyên lý thiết kế, bạn mới thực sự có thể chuyển từ “người sử dụng” framework thành “người sáng tạo” ứng dụng Agent. Khi các thành phần tiêu chuẩn không thể đáp ứng nhu cầu phức tạp của bạn, bạn sẽ có khả năng tùy biến sâu, thậm chí xây dựng một Agent hoàn toàn mới từ con số không.

## 4.1 Chuẩn bị môi trường và định nghĩa công cụ cơ bản

Trước khi bắt đầu xây dựng, chúng ta cần thiết lập môi trường phát triển và định nghĩa một số thành phần cơ bản. Điều này giúp tránh công việc lặp lại khi hiện thực các mô hình khác nhau ở phần sau, và tập trung hơn vào logic cốt lõi.

### 4.1.1 Cài đặt thư viện phụ thuộc

Phần thực hành của cuốn sách này chủ yếu sử dụng ngôn ngữ Python, khuyến nghị dùng Python 3.10 trở lên. Trước tiên, hãy đảm bảo bạn đã cài đặt thư viện `openai` để tương tác với mô hình ngôn ngữ lớn, và thư viện `python-dotenv` để quản lý khóa API một cách an toàn.

Chạy lệnh sau trong terminal của bạn:

```bash
pip install openai python-dotenv
```

### 4.1.2 Cấu hình khóa API

Để mã nguồn của chúng ta có tính tổng quát cao hơn, chúng ta sẽ cấu hình thống nhất các thông tin liên quan đến dịch vụ mô hình (ID mô hình, khóa API, địa chỉ dịch vụ) trong biến môi trường.

1. Trong thư mục gốc của dự án, tạo một tệp có tên `.env`.
2. Thêm nội dung sau vào tệp này. Bạn có thể tùy theo nhu cầu mà trỏ nó đến dịch vụ chính thức của OpenAI, hoặc bất kỳ dịch vụ cục bộ/bên thứ ba nào tương thích giao diện OpenAI.
3. Nếu thực sự không biết cách lấy, có thể tham khảo [Cấu hình môi trường](https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra07-环境配置.md)

```bash
# .env file
LLM_API_KEY="YOUR-API-KEY"
LLM_MODEL_ID="YOUR-MODEL"
LLM_BASE_URL="YOUR-URL"
```

Mã nguồn của chúng ta sẽ tự động tải các cấu hình này từ tệp đó.

### 4.1.3 Đóng gói hàm gọi LLM cơ bản

Để cấu trúc mã nguồn rõ ràng hơn, dễ tái sử dụng hơn, chúng ta sẽ định nghĩa một lớp client LLM riêng. Lớp này sẽ đóng gói mọi chi tiết tương tác với dịch vụ mô hình, giúp logic chính của chúng ta tập trung hơn vào việc xây dựng Agent.

```python
import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

# Tải các biến môi trường từ tệp .env
load_dotenv()

class HelloAgentsLLM:
    """
    Client LLM được tùy biến cho cuốn sách "Hello Agents".
    Nó dùng để gọi bất kỳ dịch vụ nào tương thích giao diện OpenAI, và mặc định dùng phản hồi dạng luồng.
    """
    def __init__(self, model: str = None, apiKey: str = None, baseUrl: str = None, timeout: int = None):
        """
        Khởi tạo client. Ưu tiên dùng tham số truyền vào; nếu không được cung cấp thì tải từ biến môi trường.
        """
        self.model = model or os.getenv("LLM_MODEL_ID")
        apiKey = apiKey or os.getenv("LLM_API_KEY")
        baseUrl = baseUrl or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        if not all([self.model, apiKey, baseUrl]):
            raise ValueError("ID mô hình, khóa API và địa chỉ dịch vụ phải được cung cấp hoặc định nghĩa trong tệp .env.")

        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """
        Gọi mô hình ngôn ngữ lớn để suy nghĩ và trả về phản hồi của nó.
        """
        print(f"🧠 Đang gọi mô hình {self.model}...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )

            # Xử lý phản hồi dạng luồng
            print("✅ Mô hình ngôn ngữ lớn phản hồi thành công:")
            collected_content = []
            for chunk in response:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)
                collected_content.append(content)
            print()  # Xuống dòng sau khi kết thúc đầu ra dạng luồng
            return "".join(collected_content)

        except Exception as e:
            print(f"❌ Xảy ra lỗi khi gọi API LLM: {e}")
            return None

# --- Ví dụ sử dụng client ---
if __name__ == '__main__':
    try:
        llmClient = HelloAgentsLLM()

        exampleMessages = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "Viết một thuật toán sắp xếp nhanh"}
        ]

        print("--- Gọi LLM ---")
        responseText = llmClient.think(exampleMessages)
        if responseText:
            print("\n\n--- Phản hồi đầy đủ của mô hình ---")
            print(responseText)

    except ValueError as e:
        print(e)


>>>
--- Gọi LLM ---
🧠 Đang gọi mô hình xxxxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
Sắp xếp nhanh là một thuật toán sắp xếp rất hiệu quả...
```



## 4.2 ReAct

Sau khi đã có client LLM, chúng ta sẽ xây dựng mô hình Agent đầu tiên và cũng là kinh điển nhất: <strong>ReAct (Reason + Act)</strong>. ReAct được Shunyu Yao đề xuất năm 2022<sup>[1]</sup>, tư tưởng cốt lõi của nó là mô phỏng cách con người giải quyết vấn đề, kết hợp một cách tường minh <strong>suy luận (Reasoning)</strong> với <strong>hành động (Acting)</strong>, tạo thành vòng lặp “suy nghĩ – hành động – quan sát”.

### 4.2.1 Quy trình làm việc của ReAct

Trước khi ReAct ra đời, các phương pháp chủ lưu có thể chia thành hai loại: một loại là kiểu “chỉ suy nghĩ”, chẳng hạn như <strong>Chuỗi suy nghĩ (Chain-of-Thought)</strong>, có thể dẫn dắt mô hình thực hiện suy luận logic phức tạp nhưng không thể tương tác với thế giới bên ngoài, dễ sinh ra ảo giác sự kiện; loại còn lại là kiểu “chỉ hành động”, mô hình trực tiếp xuất ra hành động cần thực hiện nhưng thiếu năng lực lập kế hoạch và sửa lỗi.

Điều tinh tế của ReAct nằm ở chỗ nó nhận ra rằng <strong>suy nghĩ và hành động bổ trợ lẫn nhau</strong>. Suy nghĩ dẫn dắt hành động, còn kết quả của hành động lại hiệu chỉnh ngược lại suy nghĩ. Vì vậy, mô hình ReAct dẫn dắt mô hình thông qua một kỹ thuật prompt đặc biệt, khiến đầu ra ở mỗi bước tuân theo một quỹ đạo cố định:

- <strong>Thought (Suy nghĩ):</strong> đây là “độc thoại nội tâm” của Agent. Nó phân tích tình huống hiện tại, phân rã nhiệm vụ, đưa ra kế hoạch cho bước tiếp theo, hoặc phản tư về kết quả của bước trước.
- <strong>Action (Hành động):</strong> đây là thao tác cụ thể mà Agent quyết định thực hiện, thường là gọi một công cụ bên ngoài, ví dụ `Search['mẫu điện thoại mới nhất của Huawei']`.
- <strong>Observation (Quan sát):</strong> đây là kết quả trả về từ công cụ bên ngoài sau khi thực thi `Action`, ví dụ bản tóm tắt kết quả tìm kiếm hoặc giá trị trả về của API.

Agent sẽ liên tục lặp lại vòng <strong>Thought -> Action -> Observation</strong> này, nối kết quả quan sát mới vào lịch sử, tạo thành ngữ cảnh ngày càng tăng, cho đến khi nó cho rằng đã tìm ra câu trả lời cuối cùng trong `Thought` và xuất ra kết quả. Quá trình này tạo nên hiệu ứng cộng hưởng mạnh mẽ: <strong>suy luận khiến hành động có mục đích hơn, còn hành động cung cấp căn cứ thực tế cho suy luận.</strong>

Chúng ta có thể biểu diễn quá trình này một cách hình thức như trong Hình 4.1. Cụ thể, tại mỗi bước thời gian $t$, chiến lược của Agent (tức mô hình ngôn ngữ lớn $\pi$) sẽ dựa trên câu hỏi ban đầu $q$ và toàn bộ quỹ đạo lịch sử “hành động – quan sát” của các bước trước $((a_1,o_1),\dots,(a_{t-1},o_{t-1}))$ để sinh ra suy nghĩ hiện tại $th_t$ và hành động $a_t$:

$$\left(th_t,a_t\right)=\pi\left(q,(a_1,o_1),\ldots,(a_{t-1},o_{t-1})\right)$$

Sau đó, công cụ $T$ trong môi trường sẽ thực thi hành động $a_t$ và trả về một kết quả quan sát mới $o_t$:

$$o_t = T(a_t)$$

Vòng lặp này tiếp diễn không ngừng, nối cặp $(a_t,o_t)$ mới vào lịch sử, cho đến khi mô hình đánh giá trong suy nghĩ $th_t$ rằng nhiệm vụ đã hoàn thành.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/4-figures/4-1.png" alt="Vòng cộng hưởng “suy nghĩ – hành động – quan sát” trong mô hình ReAct" width="90%"/>
  <p>Hình 4.1 Vòng cộng hưởng “suy nghĩ – hành động – quan sát” trong mô hình ReAct</p>
</div>

Cơ chế này đặc biệt phù hợp với các tình huống sau:

- <strong>Nhiệm vụ cần tri thức bên ngoài</strong>: như tra cứu thông tin thời gian thực (thời tiết, tin tức, giá cổ phiếu), tìm kiếm tri thức trong lĩnh vực chuyên môn, v.v.
- <strong>Nhiệm vụ cần tính toán chính xác</strong>: giao các bài toán cho công cụ máy tính để tránh lỗi tính toán của LLM.
- <strong>Nhiệm vụ cần tương tác với API</strong>: như thao tác cơ sở dữ liệu, gọi API của một dịch vụ để hoàn thành chức năng cụ thể.

Vì vậy, chúng ta sẽ xây dựng một Agent ReAct có khả năng <strong>sử dụng công cụ bên ngoài</strong>, để trả lời một câu hỏi mà mô hình ngôn ngữ lớn không thể trả lời trực tiếp chỉ dựa vào kho tri thức của chính nó. Ví dụ: “Mẫu điện thoại mới nhất của Huawei là mẫu nào? Điểm bán chính của nó là gì?” Câu hỏi này đòi hỏi Agent hiểu rằng mình cần tìm kiếm trên mạng, gọi công cụ tìm kiếm và tóm tắt câu trả lời.

### 4.2.2 Định nghĩa và hiện thực công cụ

Nếu mô hình ngôn ngữ lớn là bộ não của Agent, thì <strong>công cụ (Tools)</strong> chính là “tay và chân” để nó tương tác với thế giới bên ngoài. Để mô hình ReAct thực sự giải quyết được bài toán chúng ta đặt ra, Agent cần có khả năng gọi công cụ bên ngoài.

Nhằm phục vụ mục tiêu đặt ra trong mục này – trả lời câu hỏi về “điện thoại mới nhất của Huawei” – chúng ta cần cung cấp cho Agent một công cụ tìm kiếm web. Ở đây chúng ta chọn <strong>SerpApi</strong>, dịch vụ cung cấp kết quả tìm kiếm Google có cấu trúc thông qua API, có thể trả về trực tiếp “hộp tóm tắt câu trả lời” hoặc thông tin knowledge graph chính xác.

Trước tiên, cần cài đặt thư viện này:

```bash
pip install google-search-results
```

Đồng thời, bạn cần truy cập [trang chủ SerpApi](https://serpapi.com/) để đăng ký một tài khoản miễn phí, lấy khóa API và thêm vào tệp `.env` ở thư mục gốc dự án:

```bash
# .env file
# ... (giữ cấu hình LLM trước đó)
SERPAPI_API_KEY="YOUR_SERPAPI_API_KEY"
```

Tiếp theo, chúng ta định nghĩa và quản lý công cụ này bằng mã nguồn. Chúng ta sẽ làm từng bước: trước tiên hiện thực chức năng cốt lõi của công cụ, sau đó xây dựng một bộ quản lý công cụ tổng quát.

(1) Hiện thực logic cốt lõi của công cụ tìm kiếm

Một công cụ được định nghĩa tốt nên bao gồm ba yếu tố cốt lõi sau:

1. <strong>Tên (Name)</strong>: một định danh ngắn gọn, duy nhất để Agent gọi trong `Action`, ví dụ `Search`.
2. <strong>Mô tả (Description)</strong>: một đoạn mô tả bằng ngôn ngữ tự nhiên rõ ràng, giải thích mục đích của công cụ. <strong>Đây là phần quan trọng nhất của toàn bộ cơ chế</strong>, vì mô hình ngôn ngữ lớn sẽ dựa vào đoạn mô tả này để quyết định khi nào dùng công cụ nào.
3. <strong>Logic thực thi (Execution Logic)</strong>: hàm hoặc phương thức thực sự thực hiện nhiệm vụ.

Công cụ đầu tiên của chúng ta là hàm `search`, có chức năng nhận một chuỗi truy vấn rồi trả về kết quả tìm kiếm.

```python
from serpapi import SerpApiClient

def search(query: str) -> str:
    """
    Một công cụ tìm kiếm web thực chiến dựa trên SerpApi.
    Nó phân tích kết quả tìm kiếm một cách thông minh, ưu tiên trả về câu trả lời trực tiếp hoặc thông tin knowledge graph.
    """
    print(f"🔍 Đang thực thi tìm kiếm web [SerpApi]: {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "Lỗi: SERPAPI_API_KEY chưa được cấu hình trong tệp .env."

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn",  # Mã quốc gia
            "hl": "zh-cn", # Mã ngôn ngữ
        }

        client = SerpApiClient(params)
        results = client.get_dict()

        # Phân tích thông minh: ưu tiên tìm câu trả lời trực tiếp nhất
        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            # Nếu không có câu trả lời trực tiếp, trả về tóm tắt của ba kết quả hữu cơ đầu tiên
            snippets = [
                f"[{i+1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)

        return f"Xin lỗi, không tìm thấy thông tin về '{query}'."

    except Exception as e:
        return f"Xảy ra lỗi khi tìm kiếm: {e}"
```

Trong đoạn mã trên, trước tiên chương trình kiểm tra xem có thông tin `answer_box` (hộp tóm tắt câu trả lời của Google) hoặc `knowledge_graph` (knowledge graph) hay không; nếu có thì trả về trực tiếp những câu trả lời chính xác nhất này. Nếu không có, nó mới lùi về phương án thứ hai là trả về tóm tắt của ba kết quả tìm kiếm thông thường đầu tiên. Cách “phân tích thông minh” này có thể cung cấp cho LLM đầu vào thông tin chất lượng cao hơn.

(2) Xây dựng bộ thực thi công cụ tổng quát

Khi Agent cần sử dụng nhiều công cụ (ví dụ ngoài tìm kiếm còn có thể cần tính toán, truy vấn cơ sở dữ liệu, v.v.), chúng ta cần một bộ quản lý thống nhất để đăng ký và điều phối các công cụ này. Vì vậy, chúng ta tạo lớp `ToolExecutor`.

```python
from typing import Dict, Any

class ToolExecutor:
    """
    Một bộ thực thi công cụ, chịu trách nhiệm quản lý và thực thi công cụ.
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        """
        Đăng ký một công cụ mới vào hộp công cụ.
        """
        if name in self.tools:
            print(f"Cảnh báo: công cụ '{name}' đã tồn tại và sẽ bị ghi đè.")
        self.tools[name] = {"description": description, "func": func}
        print(f"Công cụ '{name}' đã được đăng ký.")

    def getTool(self, name: str) -> callable:
        """
        Lấy hàm thực thi của một công cụ theo tên.
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        Lấy chuỗi mô tả đã định dạng của tất cả công cụ khả dụng.
        """
        return "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])

```

(3) Kiểm thử

Bây giờ, chúng ta sẽ đăng ký công cụ `search` vào `ToolExecutor` và mô phỏng một lần gọi để xác minh toàn bộ quy trình có hoạt động bình thường hay không.

```python
# --- Ví dụ khởi tạo và sử dụng công cụ ---
if __name__ == '__main__':
    # 1. Khởi tạo bộ thực thi công cụ
    toolExecutor = ToolExecutor()

    # 2. Đăng ký công cụ tìm kiếm thực chiến của chúng ta
    search_description = "Một công cụ tìm kiếm web. Khi bạn cần trả lời về thời sự, sự kiện thực tế và những thông tin không có trong kho tri thức của bạn, nên dùng công cụ này."
    toolExecutor.registerTool("Search", search_description, search)

    # 3. In ra các công cụ khả dụng
    print("\n--- Các công cụ khả dụng ---")
    print(toolExecutor.getAvailableTools())

    # 4. Agent gọi Action, lần này chúng ta hỏi một câu mang tính thời gian thực
    print("\n--- Thực thi Action: Search['Mẫu GPU mới nhất của NVIDIA là gì'] ---")
    tool_name = "Search"
    tool_input = "Mẫu GPU mới nhất của NVIDIA là gì"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- Quan sát (Observation) ---")
        print(observation)
    else:
        print(f"Lỗi: không tìm thấy công cụ có tên '{tool_name}'.")

>>>
Công cụ 'Search' đã được đăng ký.

--- Các công cụ khả dụng ---
- Search: Một công cụ tìm kiếm web. Khi bạn cần trả lời về thời sự, sự kiện thực tế và những thông tin không có trong kho tri thức của bạn, nên dùng công cụ này.

--- Thực thi Action: Search['Mẫu GPU mới nhất của NVIDIA là gì'] ---
🔍 Đang thực thi tìm kiếm web [SerpApi]: Mẫu GPU mới nhất của NVIDIA là gì
--- Quan sát (Observation) ---
[1] Dòng card đồ họa GeForce RTX 50
Dòng GPU GeForce RTX™ 50 trang bị kiến trúc NVIDIA Blackwell, mang lại trải nghiệm hoàn toàn mới cho game thủ và nhà sáng tạo. Dòng RTX 50 có năng lực tính toán AI mạnh mẽ, mang lại trải nghiệm nâng cấp và hình ảnh chân thực hơn.

[2] So sánh thế hệ card đồ họa GeForce mới nhất với thế hệ trước
So sánh dòng RTX 30 mới nhất với các dòng RTX 20, GTX 10 và 900 thế hệ trước. Xem thông số kỹ thuật, tính năng, hỗ trợ kỹ thuật, v.v.

[3] Card đồ họa GeForce | NVIDIA
DRIVE AGX. Năng lực tính toán trên xe mạnh mẽ, phù hợp với hệ thống xe thông minh do AI dẫn dắt · Clara AGX. Tính toán AI cho thiết bị y tế và hình ảnh sáng tạo. Trò chơi và sáng tạo. GeForce. Khám phá card đồ họa, giải pháp trò chơi, AI ...
```

Đến đây, chúng ta đã trang bị cho Agent công cụ `Search` kết nối với internet thực tế, tạo nền tảng vững chắc cho vòng lặp ReAct sau này.



### 4.2.3 Hiện thực mã nguồn Agent ReAct

Bây giờ, chúng ta sẽ lắp ghép tất cả các thành phần độc lập – client LLM và bộ thực thi công cụ – để xây dựng một Agent ReAct hoàn chỉnh. Chúng ta sẽ đóng gói logic cốt lõi của nó trong lớp `ReActAgent`. Để dễ hiểu, chúng ta chia quá trình hiện thực lớp này thành các phần chính sau để trình bày.

(1) Thiết kế system prompt

Prompt là nền tảng của toàn bộ cơ chế ReAct, nó cung cấp cho mô hình ngôn ngữ lớn chỉ thị vận hành để hành động. Chúng ta cần thiết kế cẩn thận một mẫu, trong đó sẽ chèn động các công cụ khả dụng, câu hỏi của người dùng và lịch sử tương tác của các bước trung gian.

```bash
# Mẫu prompt ReAct
REACT_PROMPT_TEMPLATE = """
Xin lưu ý, bạn là một trợ lý thông minh có khả năng gọi công cụ bên ngoài.

Các công cụ khả dụng như sau:
{tools}

Hãy trả lời nghiêm ngặt theo định dạng sau:

Thought: quá trình suy nghĩ của bạn, dùng để phân tích vấn đề, phân rã nhiệm vụ và lập kế hoạch cho bước tiếp theo.
Action: hành động bạn quyết định thực hiện, bắt buộc phải thuộc một trong các định dạng sau:
- `{{tool_name}}[{{tool_input}}]`: gọi một công cụ khả dụng.
- `Finish[câu trả lời cuối cùng]`: khi bạn cho rằng đã có câu trả lời cuối cùng.
- Khi bạn đã thu thập đủ thông tin để trả lời câu hỏi cuối cùng của người dùng, bạn bắt buộc phải dùng Finish[câu trả lời cuối cùng] sau trường Action: để xuất câu trả lời cuối cùng.

Bây giờ, hãy bắt đầu giải quyết câu hỏi sau:
Question: {question}
History: {history}
"""
```

Mẫu này định nghĩa quy chuẩn tương tác giữa Agent và LLM:

- <strong>Định nghĩa vai trò</strong>: “Bạn là một trợ lý thông minh có khả năng gọi công cụ bên ngoài” đặt ra vai trò cho LLM.
- <strong>Danh sách công cụ (`{tools}`)</strong>: cho LLM biết nó có những “tay chân” khả dụng nào.
- <strong>Quy ước định dạng (`Thought`/`Action`)</strong>: đây là phần quan trọng nhất, nó buộc đầu ra của LLM có cấu trúc để chúng ta có thể phân tích chính xác ý định của nó bằng mã nguồn.
- <strong>Ngữ cảnh động (`{question}`/`{history}`)</strong>: chèn câu hỏi gốc của người dùng và lịch sử tương tác đang tích lũy, để LLM ra quyết định dựa trên ngữ cảnh đầy đủ.

(2) Hiện thực vòng lặp cốt lõi

Cốt lõi của `ReActAgent` là một vòng lặp liên tục “định dạng prompt -> gọi LLM -> thực thi hành động -> tích hợp kết quả”, cho đến khi nhiệm vụ hoàn thành hoặc đạt giới hạn số bước tối đa.

```python
class ReActAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question: str):
        """
        Chạy Agent ReAct để trả lời một câu hỏi.
        """
        self.history = [] # Đặt lại lịch sử mỗi lần chạy
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"--- Bước {current_step} ---")

            # 1. Định dạng prompt
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 2. Gọi LLM để suy nghĩ
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)

            if not response_text:
                print("Lỗi: LLM không trả về phản hồi hợp lệ.")
                break

            # ... (các bước phân tích, thực thi, tích hợp tiếp theo)

```

Phương thức `run` là điểm vào của Agent. Vòng `while` của nó tạo thành phần thân của mô hình ReAct, còn tham số `max_steps` là một van an toàn quan trọng, ngăn Agent rơi vào vòng lặp vô hạn và cạn kiệt tài nguyên.

(3) Hiện thực bộ phân tích đầu ra

LLM trả về văn bản thuần, chúng ta cần trích xuất chính xác `Thought` và `Action` từ đó. Việc này được thực hiện qua một vài hàm phân tích phụ trợ, thường sử dụng biểu thức chính quy.

```python
# (Các phương thức này là một phần của lớp ReActAgent)
    def _parse_output(self, text: str):
        """Phân tích đầu ra của LLM, trích xuất Thought và Action.
        """
        # Thought: khớp đến Action: hoặc cuối văn bản
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: khớp đến cuối văn bản
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        """Phân tích chuỗi Action, trích xuất tên công cụ và đầu vào.
        """
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None
```

- `_parse_output`: chịu trách nhiệm tách hai phần chính `Thought` và `Action` khỏi phản hồi đầy đủ của LLM.
- `_parse_action`: chịu trách nhiệm phân tích tiếp chuỗi `Action`, ví dụ trích xuất tên công cụ `Search` và đầu vào `điện thoại mới nhất của Huawei` từ `Search[điện thoại mới nhất của Huawei]`.

(4) Gọi và thực thi công cụ

```python
# (Đoạn logic này nằm trong vòng while của phương thức run)
            # 3. Phân tích đầu ra của LLM
            thought, action = self._parse_output(response_text)

            if thought:
                print(f"Suy nghĩ: {thought}")

            if not action:
                print("Cảnh báo: không phân tích được Action hợp lệ, quy trình kết thúc.")
                break

            # 4. Thực thi Action
            if action.startswith("Finish"):
                # Nếu là chỉ thị Finish, trích xuất câu trả lời cuối cùng và kết thúc
                final_answer = re.match(r"Finish\[(.*)\]", action).group(1)
                print(f"🎉 Câu trả lời cuối cùng: {final_answer}")
                return final_answer

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                # ... xử lý định dạng Action không hợp lệ ...
                continue

            print(f"🎬 Hành động: {tool_name}[{tool_input}]")

            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"Lỗi: không tìm thấy công cụ có tên '{tool_name}'."
            else:
                observation = tool_function(tool_input) # Gọi công cụ thật

```

Đoạn mã này là trung tâm thực thi `Action`. Trước tiên nó kiểm tra xem có phải chỉ thị `Finish` hay không; nếu đúng thì quy trình kết thúc. Ngược lại, nó lấy hàm công cụ tương ứng thông qua `tool_executor` và thực thi, thu được `observation`.

(5) Tích hợp kết quả quan sát

Bước cuối cùng, cũng là then chốt để tạo thành vòng khép kín, là thêm chính `Action` và `Observation` sau khi công cụ thực thi vào lịch sử, cung cấp ngữ cảnh mới cho vòng lặp tiếp theo.

```python
# (Đoạn logic này nằm ngay sau lời gọi công cụ, ở cuối vòng while)
            print(f"👀 Quan sát: {observation}")

            # Thêm Action và Observation của vòng này vào lịch sử
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        # Kết thúc vòng lặp
        print("Đã đạt số bước tối đa, quy trình kết thúc.")
        return None
```

Bằng cách nối `Observation` vào `self.history`, ở vòng tiếp theo khi sinh prompt, Agent có thể “nhìn thấy” kết quả hành động của bước trước và từ đó thực hiện suy nghĩ, lập kế hoạch mới.

(6) Ví dụ chạy và phân tích

Kết hợp tất cả các phần trên, chúng ta có được lớp `ReActAgent` hoàn chỉnh. Ví dụ chạy mã đầy đủ có thể tìm thấy trong thư mục `code` của kho mã đi kèm cuốn sách.

Dưới đây là một bản ghi chạy thực tế:

```
Công cụ 'Search' đã được đăng ký.

--- Bước 1 ---
🧠 Đang gọi mô hình xxxxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
Thought: Để trả lời câu hỏi này, tôi cần tìm mẫu điện thoại mới nhất do Huawei phát hành và những đặc điểm chính của nó. Những thông tin này có thể nằm ngoài kho tri thức hiện có của tôi, vì vậy cần dùng công cụ tìm kiếm để lấy dữ liệu mới nhất.
Action: Search[mẫu điện thoại mới nhất và điểm bán chính của Huawei]
🤔 Suy nghĩ: Để trả lời câu hỏi này, tôi cần tìm mẫu điện thoại mới nhất do Huawei phát hành và những đặc điểm chính của nó. Những thông tin này có thể nằm ngoài kho tri thức hiện có của tôi, vì vậy cần dùng công cụ tìm kiếm để lấy dữ liệu mới nhất.
🎬 Hành động: Search[mẫu điện thoại mới nhất và điểm bán chính của Huawei]
🔍 Đang thực thi tìm kiếm web [SerpApi]: mẫu điện thoại mới nhất và điểm bán chính của Huawei
👀 Quan sát: [1] Điện thoại Huawei - Trang chủ Huawei
Điện thoại thông minh ; Dòng Mate. Siêu phẩm hàng đầu · HUAWEI Mate XTs. Bậc thầy phi thường ; Dòng Pura. Hình ảnh tiên phong · HUAWEI Pura 80 Pro+ ; Dòng Pocket. Chương mới của thẩm mỹ. HUAWEI Pocket 2 ; Dòng nova. Chân dung chuyên nghiệp.

[2] Điện thoại Huawei năm 2025 mẫu nào có hiệu suất giá tốt? Đánh giá và phân tích thị trường điện thoại Huawei ...
Hiện nay điểm bán lớn nhất còn lại của điện thoại Huawei chỉ là hệ điều hành HarmonyOS và niềm tin thương hiệu vốn gây nhiều tranh cãi. Dưới đây giới thiệu vài mẫu điện thoại Huawei đáng mua hiện nay, bạn có thể tự chọn theo ngân sách: ...

[3] Mẫu điện thoại Huawei mới năm 2025 nào có hiệu suất giá tốt? Gợi ý 10 mẫu điện thoại Huawei mới
Chọn Huawei chủ yếu vẫn nên ưu tiên điện thoại cao cấp; dòng Mate 70 và Pura 70 là những mẫu flagship mới nhất. HUAWEI Mate 70. Ưu điểm là cấu hình camera vẫn ở đỉnh cao, phủ toàn dải tiêu cự, phù hợp với nhiếp ảnh chuyên nghiệp, hoàn thiện xuất sắc, chống rơi ngoài trời tốt ...

--- Bước 2 ---
🧠 Đang gọi mô hình xxxxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
Thought: Theo kết quả tìm kiếm, các mẫu flagship mới nhất của Huawei gồm Mate 70 và Pura 80 Pro+. Để xác định mẫu mới nhất và điểm bán chính, tôi sẽ tập trung vào những thông tin này. Từ các liên kết được cung cấp, dòng Mate 70 và Pura 80 Pro+ đều là sản phẩm ra mắt gần đây, nhưng mẫu nào thực sự “mới nhất” vẫn cần xác nhận thêm. Đồng thời, tôi có thể trích xuất điểm bán chính của chúng từ những thông tin này.
Action: Finish[Theo thông tin mới nhất, điện thoại mới nhất của Huawei có thể là HUAWEI Pura 80 Pro+ hoặc HUAWEI Mate 70. Trong đó, điểm bán chính của HUAWEI Mate 70 gồm cấu hình camera đỉnh cao, phủ toàn dải tiêu cự, phù hợp với nhiếp ảnh chuyên nghiệp, hoàn thiện xuất sắc và khả năng chống rơi ngoài trời tốt. Còn HUAWEI Pura 80 Pro+ nhấn mạnh công nghệ hình ảnh tiên phong.]
🤔 Suy nghĩ: Theo kết quả tìm kiếm, các mẫu flagship mới nhất của Huawei gồm Mate 70 và Pura 80 Pro+. Để xác định mẫu mới nhất và điểm bán chính, tôi sẽ tập trung vào những thông tin này. Từ các liên kết được cung cấp, dòng Mate 70 và Pura 80 Pro+ đều là sản phẩm ra mắt gần đây, nhưng mẫu nào thực sự “mới nhất” vẫn cần xác nhận thêm. Đồng thời, tôi có thể trích xuất điểm bán chính của chúng từ những thông tin này.
🎉 Câu trả lời cuối cùng: Theo thông tin mới nhất, điện thoại mới nhất của Huawei có thể là HUAWEI Pura 80 Pro+ hoặc HUAWEI Mate 70. Trong đó, điểm bán chính của HUAWEI Mate 70 gồm cấu hình camera đỉnh cao, phủ toàn dải tiêu cự, phù hợp với nhiếp ảnh chuyên nghiệp, hoàn thiện xuất sắc và khả năng chống rơi ngoài trời tốt. Còn HUAWEI Pura 80 Pro+ nhấn mạnh công nghệ hình ảnh tiên phong.
```

Từ đầu ra trên có thể thấy Agent đã thể hiện rõ chuỗi suy nghĩ của nó: trước tiên nó nhận ra kiến thức của mình không đủ, cần dùng công cụ tìm kiếm; sau đó nó suy luận và tổng kết dựa trên kết quả tìm kiếm, và đưa ra câu trả lời cuối cùng trong vòng hai bước.

Điều đáng lưu ý là do kiến thức của mô hình và thông tin trên internet liên tục cập nhật, kết quả bạn chạy có thể không hoàn toàn giống như trên. Tính đến ngày 8 tháng 9 năm 2025 khi nội dung mục này được biên soạn, HUAWEI Mate 70 và HUAWEI Pura 80 Pro+ được nhắc trong kết quả tìm kiếm đúng là những mẫu flagship mới nhất của Huawei vào thời điểm đó. Điều này cho thấy đầy đủ năng lực mạnh mẽ của mô hình ReAct khi xử lý các vấn đề phụ thuộc thời gian.

### 4.2.4 Đặc điểm, hạn chế và kỹ thuật gỡ lỗi của ReAct

Qua việc tự tay hiện thực một Agent ReAct, chúng ta không chỉ nắm được quy trình làm việc của nó mà còn hiểu sâu hơn về cơ chế bên trong. Bất kỳ mô hình kỹ thuật nào cũng có điểm sáng và điểm cần cải thiện; mục này sẽ tổng kết về ReAct.

(1) Đặc điểm chính của ReAct

1. <strong>Khả năng giải thích cao</strong>: một trong những ưu điểm lớn nhất của ReAct là tính minh bạch. Thông qua chuỗi `Thought`, chúng ta có thể thấy rõ “hành trình tư tưởng” của Agent ở từng bước – tại sao nó chọn công cụ này, bước tiếp theo định làm gì. Điều này rất quan trọng để hiểu, tin tưởng và gỡ lỗi hành vi của Agent.
2. <strong>Năng lực lập kế hoạch động và sửa lỗi</strong>: khác với mô hình sinh ra toàn bộ kế hoạch một lần, ReAct là “đi một bước, nhìn một bước”. Nó điều chỉnh động `Thought` và `Action` tiếp theo dựa trên `Observation` nhận được từ thế giới bên ngoài ở mỗi bước. Nếu kết quả tìm kiếm ở bước trước không lý tưởng, nó có thể sửa từ khóa tìm kiếm và thử lại ở bước sau.
3. <strong>Năng lực cộng tác công cụ</strong>: mô hình ReAct kết hợp tự nhiên năng lực suy luận của mô hình ngôn ngữ lớn với năng lực thực thi của công cụ bên ngoài. LLM chịu trách nhiệm tính toán chiến lược (lập kế hoạch và suy luận), công cụ chịu trách nhiệm giải quyết vấn đề cụ thể (tìm kiếm, tính toán); hai bên cộng tác, phá vỡ những hạn chế cố hữu của một LLM đơn thuần về tính thời sự của tri thức, độ chính xác tính toán, v.v.

(2) Hạn chế cố hữu của ReAct

1. <strong>Phụ thuộc mạnh vào năng lực của chính LLM</strong>: thành công của quy trình ReAct phụ thuộc rất lớn vào năng lực tổng hợp của LLM nền tảng. Nếu LLM thiếu năng lực suy luận logic, tuân thủ chỉ thị hoặc xuất ra theo định dạng, nó rất dễ tạo ra kế hoạch sai ở bước `Thought`, hoặc sinh chỉ thị không đúng định dạng ở bước `Action`, khiến toàn bộ quy trình bị gián đoạn.
2. <strong>Vấn đề hiệu quả thực thi</strong>: do đặc tính tiến dần từng bước, để hoàn thành một nhiệm vụ thường cần gọi LLM nhiều lần. Mỗi lần gọi đều kèm theo độ trễ mạng và chi phí tính toán. Với nhiệm vụ phức tạp cần nhiều bước, vòng lặp “suy nghĩ – hành động” tuần tự này có thể dẫn đến tổng thời gian và chi phí cao.
3. <strong>Tính mong manh của prompt</strong>: toàn bộ cơ chế vận hành ổn định dựa trên một mẫu prompt được thiết kế cẩn thận. Bất kỳ thay đổi nhỏ nào trong mẫu, thậm chí là khác biệt về từ ngữ, đều có thể ảnh hưởng đến hành vi của LLM. Hơn nữa, không phải mô hình nào cũng có thể liên tục tuân thủ định dạng đặt trước một cách ổn định, điều này làm tăng tính không chắc chắn trong ứng dụng thực tế.
4. <strong>Có thể rơi vào cục bộ tối ưu</strong>: chế độ ra quyết định theo từng bước nghĩa là Agent thiếu kế hoạch tổng thể, dài hạn. Nó có thể vì `Observation` trước mắt mà chọn một con đường có vẻ đúng nhưng không tối ưu về lâu dài, thậm chí trong một số trường hợp rơi vào vòng lặp “giẫm chân tại chỗ”.

(3) Kỹ thuật gỡ lỗi

Khi Agent ReAct bạn xây dựng có hành vi không như mong đợi, có thể bắt đầu gỡ lỗi từ các khía cạnh sau:

- <strong>Kiểm tra prompt đầy đủ</strong>: trước mỗi lần gọi LLM, in ra prompt hoàn chỉnh đã được định dạng, bao gồm toàn bộ lịch sử. Đây là cách trực tiếp nhất để truy ngược nguồn gốc quyết định của LLM.
- <strong>Phân tích đầu ra gốc</strong>: khi phân tích đầu ra thất bại (ví dụ biểu thức chính quy không khớp `Action`), nhất định phải in ra văn bản gốc, chưa qua xử lý mà LLM trả về. Điều này giúp bạn xác định LLM không tuân thủ định dạng hay logic phân tích của bạn có lỗi.
- <strong>Xác minh đầu vào và đầu ra của công cụ</strong>: kiểm tra xem `tool_input` do Agent sinh ra có đúng định dạng mà hàm công cụ mong đợi hay không, đồng thời đảm bảo định dạng `observation` do công cụ trả về là thứ Agent có thể hiểu và xử lý.
- <strong>Điều chỉnh ví dụ trong prompt (Few-shot Prompting)</strong>: nếu mô hình thường xuyên mắc lỗi, có thể thêm một hoặc hai ví dụ thành công hoàn chỉnh “Thought-Action-Observation” vào prompt, dùng ví dụ để dẫn dắt mô hình tuân thủ chỉ thị tốt hơn.
- <strong>Thử mô hình hoặc tham số khác</strong>: đổi sang một mô hình mạnh hơn, hoặc điều chỉnh tham số `temperature` (thường đặt bằng 0 để đảm bảo tính xác định của đầu ra), đôi khi có thể giải quyết vấn đề trực tiếp.

## 4.3 Plan-and-Solve

Sau khi đã nắm vững ReAct – mô hình Agent phản ứng, ra quyết định theo từng bước – tiếp theo chúng ta sẽ tìm hiểu một phương pháp có phong cách khác biệt nhưng cũng mạnh mẽ không kém: <strong>Plan-and-Solve</strong>. Đúng như tên gọi, mô hình này chia rõ ràng việc xử lý nhiệm vụ thành hai giai đoạn: <strong>lập kế hoạch trước (Plan), thực thi sau (Solve)</strong>.

Nếu ReAct giống một thám tử giàu kinh nghiệm, dựa vào dấu vết tại hiện trường (`Observation`) để suy luận từng bước và điều chỉnh hướng điều tra bất cứ lúc nào; thì Plan-and-Solve giống một kiến trúc sư hơn: trước khi khởi công phải vẽ ra bản thiết kế hoàn chỉnh (Plan), sau đó thi công nghiêm ngặt theo bản thiết kế (Solve). Trên thực tế, chế độ Agent của nhiều công cụ mô hình lớn mà chúng ta dùng hiện nay đều tích hợp kiểu thiết kế này.

### 4.3.1 Nguyên lý làm việc của Plan-and-Solve

Plan-and-Solve Prompting được Lei Wang đề xuất năm 2023<sup>[2]</sup>. Động cơ cốt lõi của nó là giải quyết vấn đề chuỗi suy nghĩ dễ “lệch khỏi quỹ đạo” khi xử lý các vấn đề nhiều bước, phức tạp.

Khác với ReAct – nơi suy nghĩ và hành động được hòa quyện ở mỗi bước – Plan-and-Solve tách toàn bộ quy trình thành hai giai đoạn cốt lõi, như trong Hình 4.2:

1. <strong>Giai đoạn lập kế hoạch (Planning Phase)</strong>: trước tiên, Agent tiếp nhận toàn bộ vấn đề của người dùng. Nhiệm vụ đầu tiên của nó không phải là trực tiếp giải quyết vấn đề hay gọi công cụ, mà là <strong>phân rã vấn đề và lập ra một kế hoạch hành động rõ ràng, từng bước</strong>. Bản thân kế hoạch này là sản phẩm của một lần gọi mô hình ngôn ngữ lớn.
2. <strong>Giai đoạn thực thi (Solving Phase)</strong>: sau khi có kế hoạch hoàn chỉnh, Agent bước vào giai đoạn thực thi. Nó <strong>tuân thủ nghiêm ngặt các bước trong kế hoạch và thực hiện lần lượt</strong>. Việc thực thi mỗi bước có thể là một lần gọi LLM độc lập, hoặc là quá trình xử lý kết quả của bước trước, cho đến khi tất cả các bước trong kế hoạch hoàn thành và đưa ra câu trả lời cuối cùng.

Chiến lược “mưu tính trước rồi mới hành động” này giúp Agent duy trì tính nhất quán mục tiêu cao hơn khi xử lý các nhiệm vụ phức tạp cần lập kế hoạch dài hạn, tránh lạc hướng ở các bước trung gian.

Chúng ta có thể biểu diễn hình thức quá trình hai giai đoạn này. Trước tiên, mô hình lập kế hoạch $\pi_{\text{plan}}$ dựa trên vấn đề gốc $q$ sinh ra một kế hoạch gồm $n$ bước $P = (p_1, p_2, \dots, p_n)$:

$$
P = \pi_{\text{plan}}(q)
$$

Sau đó, ở giai đoạn thực thi, mô hình thực thi $\pi_{\text{solve}}$ hoàn thành lần lượt các bước trong kế hoạch. Với bước thứ $i$, việc sinh ra lời giải $s_i$ sẽ đồng thời phụ thuộc vào vấn đề gốc $q$, kế hoạch đầy đủ $P$ và kết quả thực thi của tất cả các bước trước đó $(s_1, \dots, s_{i-1})$:

$$
s_i = \pi_{\text{solve}}(q, P, (s_1, \dots, s_{i-1}))
$$

Câu trả lời cuối cùng chính là kết quả thực thi của bước cuối $s_n$.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/4-figures/4-2.png" alt="Quy trình hai giai đoạn của mô hình Plan-and-Solve" width="90%"/>
  <p>Hình 4.2 Quy trình hai giai đoạn của mô hình Plan-and-Solve</p>
</div>

Plan-and-Solve đặc biệt phù hợp với những nhiệm vụ phức tạp có cấu trúc mạnh, có thể phân rã rõ ràng, ví dụ:

- <strong>Bài toán ứng dụng toán học nhiều bước</strong>: cần liệt kê các bước tính toán trước, rồi giải lần lượt.
- <strong>Viết báo cáo cần tích hợp nhiều nguồn thông tin</strong>: cần lập kế hoạch cấu trúc báo cáo (mở đầu, nguồn dữ liệu A, nguồn dữ liệu B, tổng kết) trước, rồi điền nội dung lần lượt.
- <strong>Nhiệm vụ sinh mã nguồn</strong>: cần phác thảo cấu trúc hàm, lớp và mô-đun trước, rồi hiện thực lần lượt.

### 4.3.2 Giai đoạn lập kế hoạch

Để làm nổi bật ưu thế của mô hình Plan-and-Solve trong các nhiệm vụ suy luận có cấu trúc, chúng ta sẽ không sử dụng công cụ, mà hoàn thành một nhiệm vụ suy luận thông qua thiết kế prompt.

Đặc điểm của loại nhiệm vụ này là không thể có được câu trả lời chỉ qua một lần truy vấn hoặc tính toán; phải phân rã vấn đề thành một chuỗi các bước con logic liên tục, rồi giải theo thứ tự. Điều này đúng là có thể phát huy năng lực cốt lõi “lập kế hoạch trước, thực thi sau” của Plan-and-Solve.

<strong>Vấn đề mục tiêu của chúng ta là:</strong> “Một cửa hàng hoa quả bán được 15 quả táo vào thứ Hai. Số táo bán được vào thứ Ba gấp đôi thứ Hai. Số bán được vào thứ Tư ít hơn thứ Ba 5 quả. Hỏi cả ba ngày cửa hàng bán được tổng cộng bao nhiêu quả táo?”

Vấn đề này không quá khó đối với mô hình ngôn ngữ lớn, nhưng nó chứa một chuỗi logic rõ ràng để tham khảo. Trên một số bài toán logic thực tế, nếu mô hình lớn không thể suy luận ra câu trả lời chính xác với chất lượng cao, có thể tham khảo kiểu thiết kế này để thiết kế Agent của riêng bạn hoàn thành nhiệm vụ. Agent cần:

1. <strong>Giai đoạn lập kế hoạch</strong>: trước tiên, phân rã vấn đề thành ba bước tính toán độc lập (tính doanh số thứ Ba, tính doanh số thứ Tư, tính tổng doanh số).
2. <strong>Giai đoạn thực thi</strong>: sau đó, tuân thủ nghiêm ngặt kế hoạch, thực hiện tính toán từng bước và dùng kết quả của mỗi bước làm đầu vào cho bước tiếp theo, cuối cùng thu được tổng số.

Mục tiêu của giai đoạn lập kế hoạch là để mô hình ngôn ngữ lớn tiếp nhận vấn đề gốc và xuất ra một kế hoạch hành động rõ ràng, từng bước. Kế hoạch này phải có cấu trúc để mã nguồn của chúng ta có thể dễ dàng phân tích và thực thi lần lượt. Vì vậy, prompt chúng ta thiết kế cần nói rõ cho mô hình biết vai trò và nhiệm vụ của nó, đồng thời đưa ra một ví dụ về định dạng đầu ra.

````python
PLANNER_PROMPT_TEMPLATE = """
Bạn là một chuyên gia lập kế hoạch AI hàng đầu. Nhiệm vụ của bạn là phân rã vấn đề phức tạp do người dùng đưa ra thành một kế hoạch hành động gồm nhiều bước đơn giản.
Hãy đảm bảo mỗi bước trong kế hoạch là một nhiệm vụ con độc lập, có thể thực thi, và được sắp xếp nghiêm ngặt theo thứ tự logic.
Đầu ra của bạn bắt buộc phải là một danh sách Python, trong đó mỗi phần tử là một chuỗi mô tả nhiệm vụ con.

Vấn đề: {question}

Hãy xuất kế hoạch của bạn nghiêm ngặt theo định dạng sau; ```python và ``` là tiền tố, hậu tố bắt buộc:
```python
["bước 1", "bước 2", "bước 3", ...]
```
"""
````

Prompt này đảm bảo chất lượng và tính ổn định của đầu ra thông qua các điểm sau:
- <strong>Thiết lập vai trò</strong>: “chuyên gia lập kế hoạch AI hàng đầu” khơi dậy năng lực chuyên môn của mô hình.
- <strong>Mô tả nhiệm vụ</strong>: định nghĩa rõ ràng mục tiêu “phân rã vấn đề”.
- <strong>Ràng buộc định dạng</strong>: buộc đầu ra phải là một chuỗi theo định dạng danh sách Python, điều này đơn giản hóa rất nhiều công việc phân tích mã nguồn sau đó, khiến nó ổn định và đáng tin cậy hơn so với phân tích ngôn ngữ tự nhiên.

Tiếp theo, chúng ta đóng gói logic prompt này vào lớp `Planner`, đây cũng là bộ lập kế hoạch của chúng ta.

```python
# Giả định lớp HelloAgentsLLM trong llm_client.py đã được định nghĩa
# from llm_client import HelloAgentsLLM

class Planner:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        """
        Sinh một kế hoạch hành động dựa trên câu hỏi của người dùng.
        """
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)

        # Để sinh kế hoạch, chúng ta xây dựng một danh sách tin nhắn đơn giản
        messages = [{"role": "user", "content": prompt}]

        print("--- Đang sinh kế hoạch ---")
        # Dùng đầu ra dạng luồng để lấy kế hoạch đầy đủ
        response_text = self.llm_client.think(messages=messages) or ""

        print(f"✅ Kế hoạch đã được sinh:\n{response_text}")

        # Phân tích chuỗi danh sách do LLM xuất ra
        try:
            # Tìm nội dung giữa ```python và ```
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            # Dùng ast.literal_eval để thực thi chuỗi một cách an toàn, chuyển nó thành danh sách Python
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ Lỗi khi phân tích kế hoạch: {e}")
            print(f"Phản hồi gốc: {response_text}")
            return []
        except Exception as e:
            print(f"❌ Lỗi không xác định khi phân tích kế hoạch: {e}")
            return []
```

### 4.3.3 Bộ thực thi và quản lý trạng thái

Sau khi bộ lập kế hoạch (`Planner`) sinh ra bản thiết kế hành động rõ ràng, chúng ta cần một bộ thực thi (`Executor`) để hoàn thành lần lượt các nhiệm vụ trong kế hoạch. Bộ thực thi không chỉ chịu trách nhiệm gọi mô hình ngôn ngữ lớn để giải quyết từng vấn đề con, mà còn đảm nhận một vai trò cực kỳ quan trọng: <strong>quản lý trạng thái</strong>. Nó phải ghi lại kết quả thực thi của từng bước và cung cấp chúng làm ngữ cảnh cho các bước sau, đảm bảo thông tin luôn chảy thông suốt trong toàn bộ chuỗi nhiệm vụ.

Prompt của bộ thực thi khác với bộ lập kế hoạch. Mục tiêu của nó không phải phân rã vấn đề, mà là <strong>trên cơ sở ngữ cảnh đã có, tập trung giải quyết đúng bước hiện tại</strong>. Vì vậy, prompt cần bao gồm các thông tin then chốt sau:

- <strong>Vấn đề gốc</strong>: đảm bảo mô hình luôn hiểu mục tiêu cuối cùng.
- <strong>Kế hoạch đầy đủ</strong>: để mô hình biết vị trí của bước hiện tại trong toàn bộ nhiệm vụ.
- <strong>Các bước và kết quả lịch sử</strong>: cung cấp công việc đã hoàn thành đến nay, làm đầu vào trực tiếp cho bước hiện tại.
- <strong>Bước hiện tại</strong>: chỉ thị rõ ràng cho mô hình biết hiện cần giải quyết nhiệm vụ cụ thể nào.

```python
EXECUTOR_PROMPT_TEMPLATE = """
Bạn là một chuyên gia thực thi AI hàng đầu. Nhiệm vụ của bạn là tuân thủ nghiêm ngặt kế hoạch đã cho, giải quyết vấn đề từng bước một.
Bạn sẽ nhận được vấn đề gốc, kế hoạch đầy đủ, cùng các bước và kết quả đã hoàn thành cho đến nay.
Hãy tập trung giải quyết “bước hiện tại”, và chỉ xuất câu trả lời cuối cùng của bước đó, không xuất bất kỳ giải thích hoặc hội thoại bổ sung nào.

# Vấn đề gốc:
{question}

# Kế hoạch đầy đủ:
{plan}

# Các bước và kết quả lịch sử:
{history}

# Bước hiện tại:
{current_step}

Hãy chỉ xuất câu trả lời cho “bước hiện tại”:
"""
```

Chúng ta đóng gói logic thực thi vào lớp `Executor`. Lớp này sẽ duyệt vòng lặp qua kế hoạch, gọi LLM và duy trì một bản ghi lịch sử (trạng thái).

```python
class Executor:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, question: str, plan: list[str]) -> str:
        """
        Thực thi và giải quyết vấn đề từng bước theo kế hoạch.
        """
        history = "" # Chuỗi dùng để lưu các bước và kết quả lịch sử

        print("\n--- Đang thực thi kế hoạch ---")

        for i, step in enumerate(plan):
            print(f"\n-> Đang thực thi bước {i+1}/{len(plan)}: {step}")

            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan,
                history=history if history else "không có", # Nếu là bước đầu tiên, lịch sử để trống
                current_step=step
            )

            messages = [{"role": "user", "content": prompt}]

            response_text = self.llm_client.think(messages=messages) or ""

            # Cập nhật lịch sử để chuẩn bị cho bước tiếp theo
            history += f"Bước {i+1}: {step}\nKết quả: {response_text}\n\n"

            print(f"✅ Bước {i+1} đã hoàn thành, kết quả: {response_text}")

        # Sau khi vòng lặp kết thúc, phản hồi của bước cuối chính là câu trả lời cuối cùng
        final_answer = response_text
        return final_answer
```

Hiện tại chúng ta đã xây dựng riêng `Planner` phụ trách “lập kế hoạch” và `Executor` phụ trách “thực thi”. Bước cuối cùng là tích hợp hai thành phần này vào một Agent thống nhất `PlanAndSolveAgent`, và trao cho nó năng lực hoàn chỉnh để giải quyết vấn đề. Chúng ta sẽ tạo lớp chính `PlanAndSolveAgent`, với trách nhiệm rất rõ ràng: tiếp nhận một client LLM, khởi tạo bộ lập kế hoạch và bộ thực thi bên trong, đồng thời cung cấp một phương thức `run` đơn giản để khởi động toàn bộ quy trình.

```python
class PlanAndSolveAgent:
    def __init__(self, llm_client):
        """
        Khởi tạo Agent, đồng thời tạo các thực thể lập kế hoạch và thực thi.
        """
        self.llm_client = llm_client
        self.planner = Planner(self.llm_client)
        self.executor = Executor(self.llm_client)

    def run(self, question: str):
        """
        Chạy toàn bộ quy trình của Agent: lập kế hoạch trước, thực thi sau.
        """
        print(f"\n--- Bắt đầu xử lý vấn đề ---\nVấn đề: {question}")

        # 1. Gọi bộ lập kế hoạch để sinh kế hoạch
        plan = self.planner.plan(question)

        # Kiểm tra xem kế hoạch có được sinh thành công hay không
        if not plan:
            print("\n--- Nhiệm vụ kết thúc --- \nKhông thể sinh kế hoạch hành động hợp lệ.")
            return

        # 2. Gọi bộ thực thi để thực hiện kế hoạch
        final_answer = self.executor.execute(question, plan)

        print(f"\n--- Nhiệm vụ hoàn thành ---\nCâu trả lời cuối cùng: {final_answer}")
```

Thiết kế của lớp `PlanAndSolveAgent` này thể hiện nguyên tắc “kết hợp tốt hơn kế thừa”. Bản thân nó không chứa logic phức tạp, mà đóng vai trò điều phối viên (Orchestrator), gọi rõ ràng các thành phần bên trong để hoàn thành nhiệm vụ.

### 4.3.4 Ví dụ chạy và phân tích

Mã nguồn đầy đủ cũng có thể tham khảo thư mục `code` của kho mã đi kèm cuốn sách; ở đây chỉ trình diễn kết quả cuối cùng.

````bash
--- Bắt đầu xử lý vấn đề ---
Vấn đề: Một cửa hàng hoa quả bán được 15 quả táo vào thứ Hai. Số táo bán được vào thứ Ba gấp đôi thứ Hai. Số bán được vào thứ Tư ít hơn thứ Ba 5 quả. Hỏi cả ba ngày cửa hàng bán được tổng cộng bao nhiêu quả táo?
--- Đang sinh kế hoạch ---
🧠 Đang gọi mô hình xxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
```python
["Tính số táo bán được thứ Hai: 15 quả", "Tính số táo bán được thứ Ba: số lượng thứ Hai × 2 = 15 × 2 = 30 quả", "Tính số táo bán được thứ Tư: số lượng thứ Ba - 5 = 30 - 5 = 25 quả", "Tính tổng doanh số ba ngày: thứ Hai + thứ Ba + thứ Tư = 15 + 30 + 25 = 70 quả"]
```
✅ Kế hoạch đã được sinh:
```python
["Tính số táo bán được thứ Hai: 15 quả", "Tính số táo bán được thứ Ba: số lượng thứ Hai × 2 = 15 × 2 = 30 quả", "Tính số táo bán được thứ Tư: số lượng thứ Ba - 5 = 30 - 5 = 25 quả", "Tính tổng doanh số ba ngày: thứ Hai + thứ Ba + thứ Tư = 15 + 30 + 25 = 70 quả"]
```

--- Đang thực thi kế hoạch ---

-> Đang thực thi bước 1/4: Tính số táo bán được thứ Hai: 15 quả
🧠 Đang gọi mô hình xxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
15
✅ Bước 1 đã hoàn thành, kết quả: 15

-> Đang thực thi bước 2/4: Tính số táo bán được thứ Ba: số lượng thứ Hai × 2 = 15 × 2 = 30 quả
🧠 Đang gọi mô hình xxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
30
✅ Bước 2 đã hoàn thành, kết quả: 30

-> Đang thực thi bước 3/4: Tính số táo bán được thứ Tư: số lượng thứ Ba - 5 = 30 - 5 = 25 quả
🧠 Đang gọi mô hình xxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
25
✅ Bước 3 đã hoàn thành, kết quả: 25

-> Đang thực thi bước 4/4: Tính tổng doanh số ba ngày: thứ Hai + thứ Ba + thứ Tư = 15 + 30 + 25 = 70 quả
🧠 Đang gọi mô hình xxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
70
✅ Bước 4 đã hoàn thành, kết quả: 70

--- Nhiệm vụ hoàn thành ---
Câu trả lời cuối cùng: 70
````

Từ nhật ký đầu ra trên, chúng ta có thể thấy rõ quy trình làm việc của mô hình Plan-and-Solve:

1.  <strong>Giai đoạn lập kế hoạch</strong>: Agent trước tiên gọi `Planner`, phân rã thành công bài toán ứng dụng phức tạp thành một danh sách Python gồm bốn bước logic. Kế hoạch có cấu trúc này đặt nền tảng cho việc thực thi sau đó.
2.  <strong>Giai đoạn thực thi</strong>: `Executor` tuân thủ nghiêm ngặt kế hoạch đã sinh, thực thi từng bước một. Ở mỗi bước, nó dùng kết quả lịch sử làm ngữ cảnh, đảm bảo thông tin được truyền đúng (ví dụ bước 2 sử dụng đúng kết quả “15 quả” của bước 1, bước 3 cũng sử dụng đúng kết quả “30 quả” của bước 2).
3.  <strong>Kết quả</strong>: toàn bộ quá trình logic rõ ràng, các bước minh bạch, cuối cùng Agent đưa ra chính xác câu trả lời đúng “70 quả”.

## 4.4 Reflection

Trong các mô hình ReAct và Plan-and-Solve mà chúng ta đã hiện thực, công việc của Agent kết thúc ngay khi nó hoàn thành nhiệm vụ. Tuy nhiên, câu trả lời ban đầu mà chúng sinh ra – dù là quỹ đạo hành động hay kết quả cuối cùng – đều có thể chứa sai sót hoặc cần cải thiện. Tư tưởng cốt lõi của cơ chế Reflection chính là đưa vào Agent một <strong>vòng tự hiệu chỉnh hậu nghiệm (post-hoc)</strong>, để nó có thể giống con người, xem xét công việc của mình, phát hiện thiếu sót và tối ưu hóa lặp đi lặp lại.

### 4.4.1 Tư tưởng cốt lõi của cơ chế Reflection

Cơ chế Reflection lấy cảm hứng từ quá trình học tập của con người: sau khi hoàn thành bản nháp chúng ta sẽ hiệu đính, sau khi giải xong bài toán chúng ta sẽ kiểm tra lại. Tư tưởng này được thể hiện trong nhiều nghiên cứu, ví dụ framework Reflexion do Shinn, Noah đề xuất năm 2023<sup>[3]</sup>. Quy trình làm việc cốt lõi của nó có thể tóm gọn trong một vòng ba bước ngắn gọn: <strong>thực thi -> phản tư -> tối ưu</strong>.

1. <strong>Thực thi (Execution)</strong>: trước tiên, Agent sử dụng các phương pháp quen thuộc (như ReAct hoặc Plan-and-Solve) để thử hoàn thành nhiệm vụ, sinh ra một giải pháp hoặc quỹ đạo hành động ban đầu. Có thể xem đây là “bản nháp”.
2. <strong>Phản tư (Reflection)</strong>: tiếp theo, Agent bước vào giai đoạn phản tư. Nó gọi một thực thể mô hình ngôn ngữ lớn độc lập, hoặc có prompt đặc biệt, để đóng vai “người đánh giá”. “Người đánh giá” này sẽ xem xét “bản nháp” sinh ra ở bước một và đánh giá từ nhiều chiều, ví dụ:
   - <strong>Lỗi sự kiện</strong>: có nội dung trái với thường thức hoặc sự kiện đã biết hay không?
   - <strong>Lỗ hổng logic</strong>: quá trình suy luận có chỗ không liên tục hoặc mâu thuẫn hay không?
   - <strong>Vấn đề hiệu quả</strong>: có con đường trực tiếp hơn, ngắn gọn hơn để hoàn thành nhiệm vụ hay không?
   - <strong>Thiếu thông tin</strong>: có bỏ qua một số ràng buộc hoặc khía cạnh then chốt của vấn đề hay không? Dựa trên đánh giá, nó sinh ra một đoạn <strong>phản hồi (Feedback)</strong> có cấu trúc, chỉ ra vấn đề cụ thể và đề xuất cải thiện.
3. <strong>Tối ưu (Refinement)</strong>: cuối cùng, Agent dùng “bản nháp” và “phản hồi” làm ngữ cảnh mới, gọi lại mô hình ngôn ngữ lớn, yêu cầu nó sửa bản nháp theo nội dung phản hồi và sinh ra một “bản sửa đổi” hoàn thiện hơn.

Như trong Hình 4.3, vòng lặp này có thể lặp lại nhiều lần cho đến khi giai đoạn phản tư không còn phát hiện vấn đề mới, hoặc đạt giới hạn số lần lặp đặt trước. Chúng ta có thể biểu diễn hình thức quá trình tối ưu lặp này. Giả sử $O_i$ là đầu ra sinh ra ở lần lặp thứ $i$ ($O_0$ là đầu ra ban đầu), mô hình phản tư $\pi_{\text{reflect}}$ sẽ sinh phản hồi $F_i$ cho $O_i$:
$$
F_i = \pi_{\text{reflect}}(\text{Task}, O_i)
$$
Sau đó, mô hình tối ưu $\pi_{\text{refine}}$ sẽ kết hợp nhiệm vụ gốc, đầu ra phiên bản trước và phản hồi để sinh ra phiên bản đầu ra mới $O_{i+1}$:
$$
O_{i+1} = \pi_{\text{refine}}(\text{Task}, O_i, F_i)
$$



<div align="center">
<img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/4-figures/4-3.png" alt="Vòng lặp “thực thi – phản tư – tối ưu” trong cơ chế Reflection" width="70%"/>
<p>Hình 4.3 Vòng lặp “thực thi – phản tư – tối ưu” trong cơ chế Reflection</p>
</div>



So với hai mô hình trước, giá trị của Reflection nằm ở chỗ:

- Nó cung cấp cho Agent một vòng tự sửa lỗi nội bộ, khiến Agent không còn phụ thuộc hoàn toàn vào phản hồi từ công cụ bên ngoài (`Observation` của ReAct), từ đó có thể sửa được những lỗi logic và chiến lược ở tầng cao hơn.
- Nó biến việc thực thi nhiệm vụ một lần thành một quá trình tối ưu liên tục, nâng cao rõ rệt tỷ lệ thành công cuối cùng và chất lượng câu trả lời cho các nhiệm vụ phức tạp.
- Nó xây dựng cho Agent một <strong>“bộ nhớ ngắn hạn”</strong> tạm thời. Toàn bộ quỹ đạo “thực thi – phản tư – tối ưu” tạo thành một bản ghi kinh nghiệm quý giá; Agent không chỉ biết câu trả lời cuối cùng mà còn nhớ mình đã lặp từ bản nháp còn khiếm khuyết đến phiên bản cuối như thế nào. Hơn nữa, hệ thống bộ nhớ này còn có thể là <strong>đa phương thức</strong>, cho phép Agent phản tư và sửa đầu ra ngoài văn bản (như mã nguồn, hình ảnh, v.v.), đặt nền tảng cho việc xây dựng Agent đa phương thức mạnh mẽ hơn.

### 4.4.2 Thiết lập ca và thiết kế mô-đun bộ nhớ

Để thể hiện cơ chế Reflection trong thực chiến, chúng ta sẽ đưa vào cơ chế quản lý bộ nhớ, vì reflection thường tương ứng với việc lưu trữ và trích xuất thông tin; nếu ngữ cảnh đủ dài, việc để “người đánh giá” lấy trực tiếp toàn bộ thông tin rồi phản tư thường sẽ truyền vào rất nhiều thông tin dư thừa. Bước thực hành này chúng ta chủ yếu hoàn thành <strong>sinh mã nguồn và tối ưu lặp</strong>.

Nhiệm vụ mục tiêu của bước này là: “Viết một hàm Python tìm tất cả các số nguyên tố (prime numbers) từ 1 đến n.”

Nhiệm vụ này là cảnh tuyệt vời để kiểm chứng cơ chế Reflection:

1. <strong>Tồn tại con đường tối ưu rõ ràng</strong>: mã nguồn mô hình ngôn ngữ lớn sinh ra lần đầu rất có thể là một hiện thực đệ quy đơn giản nhưng kém hiệu quả.
2. <strong>Điểm phản tư rõ ràng</strong>: có thể phát hiện qua phản tư vấn đề “độ phức tạp thời gian quá cao” hoặc “có tính toán lặp”.
3. <strong>Hướng tối ưu rõ ràng</strong>: có thể tối ưu thành phiên bản lặp hiệu quả hơn hoặc phiên bản dùng mẫu ghi nhớ (memoization) dựa trên phản hồi.

Cốt lõi của Reflection là lặp, mà tiền đề của lặp là có thể ghi nhớ những lần thử trước và phản hồi nhận được. Vì vậy, một mô-đun “bộ nhớ ngắn hạn” là thứ thiết yếu để hiện thực mô hình này. Mô-đun bộ nhớ này sẽ chịu trách nhiệm lưu toàn bộ quỹ đạo của mỗi vòng “thực thi – phản tư”.

```python
from typing import List, Dict, Any, Optional

class Memory:
    """
    Một mô-đun bộ nhớ ngắn hạn đơn giản, dùng để lưu quỹ đạo hành động và phản tư của Agent.
    """

    def __init__(self):
        """
        Khởi tạo một danh sách rỗng để lưu tất cả bản ghi.
        """
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        """
        Thêm một bản ghi mới vào bộ nhớ.

        Tham số:
        - record_type (str): loại bản ghi ('execution' hoặc 'reflection').
        - content (str): nội dung cụ thể của bản ghi (ví dụ mã nguồn được sinh hoặc phản hồi phản tư).
        """
        record = {"type": record_type, "content": content}
        self.records.append(record)
        print(f"📝 Bộ nhớ đã cập nhật, thêm một bản ghi '{record_type}'.")

    def get_trajectory(self) -> str:
        """
        Định dạng tất cả bản ghi bộ nhớ thành một chuỗi văn bản liền mạch, dùng để xây dựng prompt.
        """
        trajectory_parts = []
        for record in self.records:
            if record['type'] == 'execution':
                trajectory_parts.append(f"--- Lần thử trước (mã nguồn) ---\n{record['content']}")
            elif record['type'] == 'reflection':
                trajectory_parts.append(f"--- Phản hồi của người đánh giá ---\n{record['content']}")

        return "\n\n".join(trajectory_parts)

    def get_last_execution(self) -> Optional[str]:
        """
        Lấy kết quả thực thi gần nhất (ví dụ mã nguồn mới nhất).
        Nếu không tồn tại, trả về None.
        """
        for record in reversed(self.records):
            if record['type'] == 'execution':
                return record['content']
        return None
```

Thiết kế của lớp `Memory` này khá ngắn gọn, phần chính như sau:

- Dùng danh sách `records` để lưu theo thứ tự từng hành động và phản tư.
- Phương thức `add_record` chịu trách nhiệm thêm mục mới vào bộ nhớ.
- Phương thức `get_trajectory` là cốt lõi, nó “tuần tự hóa” quỹ đạo bộ nhớ thành một đoạn văn bản, có thể chèn trực tiếp vào prompt sau đó, cung cấp ngữ cảnh đầy đủ cho phản tư và tối ưu của mô hình.
- `get_last_execution` giúp chúng ta lấy “bản nháp” mới nhất để phản tư.



### 4.4.3 Hiện thực mã nguồn Agent Reflection

Có mô-đun `Memory` làm nền tảng, giờ chúng ta có thể xây dựng logic cốt lõi của `ReflectionAgent`. Quy trình làm việc của toàn bộ Agent sẽ xoay quanh vòng lặp “thực thi – phản tư – tối ưu” đã bàn ở trên, và thông qua các prompt được thiết kế cẩn thận để dẫn dắt mô hình ngôn ngữ lớn đóng các vai khác nhau.

(1) Thiết kế prompt

Khác với các mô hình trước, cơ chế Reflection cần nhiều prompt với các vai trò khác nhau phối hợp với nhau.

1. <strong>Prompt thực thi ban đầu (Execution Prompt)</strong>: đây là prompt để Agent thử giải quyết vấn đề lần đầu, nội dung tương đối trực tiếp, chỉ yêu cầu mô hình hoàn thành nhiệm vụ được chỉ định.

```bash
INITIAL_PROMPT_TEMPLATE = """
Bạn là một lập trình viên Python giàu kinh nghiệm. Hãy viết một hàm Python theo yêu cầu sau.
Mã nguồn của bạn phải bao gồm chữ ký hàm đầy đủ, docstring, và tuân thủ quy ước mã hóa PEP 8.

Yêu cầu: {task}

Hãy xuất trực tiếp mã nguồn, không kèm bất kỳ giải thích bổ sung nào.
"""
```

2. <strong>Prompt phản tư (Reflection Prompt)</strong>: prompt này là linh hồn của cơ chế Reflection. Nó chỉ thị mô hình đóng vai “người đánh giá mã nguồn”, phân tích phê phán mã nguồn được sinh ở vòng trước, và đưa ra phản hồi cụ thể, có thể hành động.

````bash
REFLECT_PROMPT_TEMPLATE = """
Bạn là một chuyên gia đánh giá mã nguồn cực kỳ nghiêm khắc và một kỹ sư thuật toán giàu kinh nghiệm, có yêu cầu cực cao về hiệu năng mã nguồn.
Nhiệm vụ của bạn là xem xét mã Python dưới đây, và tập trung tìm ra nút thắt chính của nó về <strong>hiệu quả thuật toán</strong>.

# Nhiệm vụ gốc:
{task}

# Mã nguồn cần xem xét:
```python
{code}
```

Hãy phân tích độ phức tạp thời gian của mã nguồn này, và suy nghĩ xem có tồn tại một giải pháp <strong>tối ưu hơn về mặt thuật toán</strong> để nâng cao hiệu năng đáng kể hay không.
Nếu có, hãy chỉ rõ điểm yếu của thuật toán hiện tại và đề xuất gợi ý thuật toán cải tiến cụ thể, khả thi (ví dụ dùng sàng thay cho phép chia thử).
Nếu mã nguồn đã tối ưu ở tầng thuật toán, mới được trả lời “không cần cải thiện”.

Hãy xuất trực tiếp phản hồi của bạn, không kèm bất kỳ giải thích bổ sung nào.
"""
````

3. <strong>Prompt tối ưu (Refinement Prompt)</strong>: sau khi nhận phản hồi, prompt này sẽ dẫn dắt mô hình sửa và tối ưu mã nguồn cũ theo nội dung phản hồi.

````bash

REFINE_PROMPT_TEMPLATE = """
Bạn là một lập trình viên Python giàu kinh nghiệm. Bạn đang tối ưu mã nguồn của mình dựa trên phản hồi của một chuyên gia đánh giá mã nguồn.

# Nhiệm vụ gốc:
{task}

# Mã nguồn bạn đã thử ở vòng trước:
{last_code_attempt}
Phản hồi của người đánh giá:
{feedback}

Hãy sinh một phiên bản mã nguồn mới đã tối ưu dựa trên phản hồi của người đánh giá.
Mã nguồn của bạn phải bao gồm chữ ký hàm đầy đủ, docstring, và tuân thủ quy ước mã hóa PEP 8.
Hãy xuất trực tiếp mã nguồn đã tối ưu, không kèm bất kỳ giải thích bổ sung nào.
"""
````

(2) Đóng gói và hiện thực Agent

Bây giờ, chúng ta tích hợp bộ logic prompt này và mô-đun `Memory` vào lớp `ReflectionAgent`.

```python
# Giả định llm_client.py và memory.py đã được định nghĩa
# from llm_client import HelloAgentsLLM
# from memory import Memory

class ReflectionAgent:
    def __init__(self, llm_client, max_iterations=3):
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations

    def run(self, task: str):
        print(f"\n--- Bắt đầu xử lý nhiệm vụ ---\nNhiệm vụ: {task}")

        # --- 1. Thực thi ban đầu ---
        print("\n--- Đang thực hiện lần thử ban đầu ---")
        initial_prompt = INITIAL_PROMPT_TEMPLATE.format(task=task)
        initial_code = self._get_llm_response(initial_prompt)
        self.memory.add_record("execution", initial_code)

        # --- 2. Vòng lặp: phản tư và tối ưu ---
        for i in range(self.max_iterations):
            print(f"\n--- Vòng lặp {i+1}/{self.max_iterations} ---")

            # a. Phản tư
            print("\n-> Đang phản tư...")
            last_code = self.memory.get_last_execution()
            reflect_prompt = REFLECT_PROMPT_TEMPLATE.format(task=task, code=last_code)
            feedback = self._get_llm_response(reflect_prompt)
            self.memory.add_record("reflection", feedback)

            # b. Kiểm tra xem có cần dừng hay không
            if "không cần cải thiện" in feedback:
                print("\n✅ Phản tư cho rằng mã nguồn không cần cải thiện, nhiệm vụ hoàn thành.")
                break

            # c. Tối ưu
            print("\n-> Đang tối ưu...")
            refine_prompt = REFINE_PROMPT_TEMPLATE.format(
                task=task,
                last_code_attempt=last_code,
                feedback=feedback
            )
            refined_code = self._get_llm_response(refine_prompt)
            self.memory.add_record("execution", refined_code)

        final_code = self.memory.get_last_execution()
        print(f"\n--- Nhiệm vụ hoàn thành ---\nMã nguồn cuối cùng được sinh:\n```python\n{final_code}\n```")
        return final_code

    def _get_llm_response(self, prompt: str) -> str:
        """Một phương thức phụ trợ dùng để gọi LLM và lấy phản hồi dạng luồng đầy đủ."""
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm_client.think(messages=messages) or ""
        return response_text

```

### 4.4.4 Ví dụ chạy và phân tích

Mã nguồn đầy đủ cũng có thể tham khảo thư mục `code` của kho mã đi kèm cuốn sách; ở đây cung cấp một ví dụ đầu ra.

````python
--- Bắt đầu xử lý nhiệm vụ ---
Nhiệm vụ: Viết một hàm Python tìm tất cả các số nguyên tố (prime numbers) từ 1 đến n.

--- Đang thực hiện lần thử ban đầu ---
🧠 Đang gọi mô hình xxxxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
```python
def find_primes(n):
    ...
    return primes
```
📝 Bộ nhớ đã cập nhật, thêm một bản ghi 'execution'.

--- Vòng lặp 1/2 ---

-> Đang phản tư...
🧠 Đang gọi mô hình xxxxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
Độ phức tạp thời gian của mã nguồn hiện tại là O(n * sqrt(n)). Mặc dù với giá trị n nhỏ, cách hiện thực này có thể chấp nhận được, nhưng khi n rất lớn, hiệu năng sẽ giảm rõ rệt. Nút thắt chính nằm ở việc mỗi số đều cần kiểm tra bằng phép chia thử, dẫn đến chi phí thời gian cao.

Đề xuất dùng sàng Eratosthenes (Sieve of Eratosthenes), thuật toán này có độ phức tạp thời gian O(n log(log n)), có thể nâng cao đáng kể hiệu quả tìm số nguyên tố.

Mã nguồn cải tiến như sau:
```python
def find_primes(n):
    ...
    return primes
```
📝 Bộ nhớ đã cập nhật, thêm một bản ghi 'reflection'.

-> Đang tối ưu...
🧠 Đang gọi mô hình xxxxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
```python
def find_primes(n):
    ...
    return primes
```
📝 Bộ nhớ đã cập nhật, thêm một bản ghi 'execution'.

--- Vòng lặp 2/2 ---

-> Đang phản tư...
🧠 Đang gọi mô hình xxxxxx...
✅ Mô hình ngôn ngữ lớn phản hồi thành công:
Mã nguồn hiện tại sử dụng sàng Eratosthenes, độ phức tạp thời gian là O(n log log n), độ phức tạp không gian là O(n). Thuật toán này đã rất hiệu quả khi tìm tất cả số nguyên tố từ 1 đến n, thông thường không cần tối ưu thêm. Nhưng trong một số tình huống đặc biệt, có thể cân nhắc các cải tiến sau:

1. <strong>Sàng phân đoạn (Segmented Sieve)</strong>: phù hợp khi n rất lớn nhưng bộ nhớ hạn chế. Chia khoảng thành nhiều đoạn nhỏ, mỗi đoạn xử lý bằng sàng riêng, giảm mức sử dụng bộ nhớ.
2. <strong>Sàng số lẻ (Odd Number Sieve)</strong>: ngoài 2, mọi số nguyên tố đều là số lẻ. Có thể chỉ đánh dấu số lẻ khi khởi tạo mảng `is_prime`, nhờ đó giảm một nửa độ phức tạp không gian và giảm một số tính toán không cần thiết.

Tuy nhiên, những cải tiến này không bắt buộc với hầu hết ứng dụng, vì sàng Eratosthenes tiêu chuẩn đã đủ hiệu quả. Vì vậy, trong trường hợp thông thường, <strong>không cần cải thiện</strong>.
📝 Bộ nhớ đã cập nhật, thêm một bản ghi 'reflection'.

✅ Phản tư cho rằng mã nguồn không cần cải thiện, nhiệm vụ hoàn thành.

--- Nhiệm vụ hoàn thành ---
Mã nguồn cuối cùng được sinh:
```python
def find_primes(n):
    """
    Tìm tất cả số nguyên tố từ 1 đến n bằng thuật toán sàng Eratosthenes.

    :param n: Giới hạn trên của khoảng cần tìm số nguyên tố.
    :return: Danh sách tất cả số nguyên tố từ 1 đến n.
    """
    if n < 2:
        return []

    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False

    p = 2
    while p * p <= n:
        if is_prime[p]:
            for i in range(p * p, n + 1, p):
                is_prime[i] = False
        p += 1

    primes = [num for num in range(2, n + 1) if is_prime[num]]
    return primes
```
````

Ví dụ chạy này cho thấy cơ chế Reflection đã dẫn dắt Agent tối ưu sâu như thế nào:

1. <strong>“Phê bình” hiệu quả là tiền đề của tối ưu</strong>: trong vòng phản tư đầu tiên, nhờ dùng prompt “cực kỳ nghiêm khắc” và “tập trung vào hiệu quả thuật toán”, Agent không hài lòng với mã ban đầu đúng chức năng, mà chỉ ra chính xác nút thắt độ phức tạp thời gian `O(n * sqrt(n))` của nó, và đề xuất cải tiến ở tầng thuật toán – sàng Eratosthenes.
2. <strong>Cải tiến lặp</strong>: sau khi nhận phản hồi rõ ràng, ở giai đoạn tối ưu Agent hiện thực thành công sàng hiệu quả hơn, giảm độ phức tạp thuật toán xuống `O(n log log n)`, hoàn thành lần tự lặp có ý nghĩa đầu tiên.
3. <strong>Hội tụ và kết thúc</strong>: trong vòng phản tư thứ hai, trước một thuật toán sàng đã hiệu quả, Agent thể hiện kiến thức sâu hơn. Nó không chỉ khẳng định hiệu quả của thuật toán hiện tại mà còn nhắc đến các hướng tối ưu cao cấp hơn như sàng phân đoạn, nhưng cuối cùng đưa ra phán đoán đúng “trong trường hợp thông thường không cần cải thiện”. Phán đoán này kích hoạt điều kiện dừng của chúng ta, khiến quá trình tối ưu hội tụ.

Ca này chứng minh đầy đủ rằng một cơ chế Reflection được thiết kế tốt không chỉ có giá trị sửa lỗi, mà còn <strong>dẫn dắt giải pháp nâng cấp theo bậc về chất lượng và hiệu quả</strong>, khiến nó trở thành một trong những kỹ thuật then chốt để xây dựng Agent phức tạp, chất lượng cao.

### 4.4.5 Phân tích chi phí – lợi ích của cơ chế Reflection

Mặc dù cơ chế Reflection thể hiện xuất sắc trong việc nâng cao chất lượng giải quyết nhiệm vụ, nhưng năng lực này không phải không có cái giá. Trong ứng dụng thực tế, chúng ta cần cân nhắc lợi ích nó mang lại với chi phí tương ứng.

(1) Chi phí chính

1. <strong>Tăng chi phí gọi mô hình</strong>: đây là chi phí trực tiếp nhất. Mỗi vòng lặp cần gọi thêm ít nhất hai lần mô hình ngôn ngữ lớn (một lần phản tư, một lần tối ưu). Nếu lặp nhiều vòng, chi phí gọi API và tiêu hao tài nguyên tính toán sẽ tăng gấp bội.

2. <strong>Độ trễ nhiệm vụ tăng rõ rệt</strong>: Reflection là quá trình tuần tự, mỗi vòng tối ưu đều phải chờ vòng phản tư trước hoàn thành. Điều này kéo dài đáng kể tổng thời gian nhiệm vụ, không phù hợp với các tình huống yêu cầu thời gian thực cao.

3. <strong>Độ phức tạp kỹ thuật prompt tăng</strong>: như ca của chúng ta cho thấy, thành công của Reflection phụ thuộc rất lớn vào prompt chất lượng cao, có mục tiêu. Việc thiết kế và gỡ lỗi prompt hiệu quả cho các giai đoạn “thực thi”, “phản tư”, “tối ưu” đòi hỏi đầu tư nhiều công sức phát triển hơn.

(2) Lợi ích cốt lõi

1. <strong>Chất lượng giải pháp nhảy vọt</strong>: lợi ích lớn nhất là nó có thể lặp và tối ưu một giải pháp ban đầu “đạt yêu cầu” thành một giải pháp cuối cùng “xuất sắc”. Sự nâng cấp từ đúng chức năng đến hiệu năng cao, từ logic thô đến logic chặt chẽ này là cực kỳ quan trọng trong nhiều nhiệm vụ then chốt.

2. <strong>Tăng cường độ vững và độ tin cậy</strong>: thông qua vòng tự sửa lỗi nội bộ, Agent có thể phát hiện và sửa các vấn đề như lỗ hổng logic, lỗi sự kiện hoặc xử lý tình huống biên không thỏa đáng trong giải pháp ban đầu, từ đó nâng cao đáng kể độ tin cậy của kết quả cuối cùng.

Tóm lại, cơ chế Reflection là một chiến lược điển hình “đánh đổi chi phí lấy chất lượng”. Nó rất phù hợp với những tình huống <strong>có yêu cầu cực cao về chất lượng, độ chính xác và độ tin cậy của kết quả cuối cùng, đồng thời yêu cầu tương đối lỏng về tính thời gian thực của việc hoàn thành nhiệm vụ</strong>. Ví dụ:

- Sinh mã nghiệp vụ hoặc báo cáo kỹ thuật quan trọng.
- Thực hiện suy luận logic phức tạp trong nghiên cứu khoa học.
- Hệ thống hỗ trợ ra quyết định cần phân tích và lập kế hoạch sâu.

Ngược lại, nếu tình huống ứng dụng cần phản hồi nhanh, hoặc một câu trả lời “đại khái đúng” là đủ, thì dùng các mô hình nhẹ hơn như ReAct hoặc Plan-and-Solve có thể là lựa chọn hiệu quả về chi phí hơn.

## 4.5 Tổng kết chương

Trong chương này, dựa trên kiến thức về mô hình ngôn ngữ lớn đã nắm ở chương 3, chúng ta đã “tự tay phát minh lại bánh xe”, lập trình từ con số không để hiện thực ba mô hình xây dựng Agent kinh điển của ngành: ReAct, Plan-and-Solve và Reflection. Chúng ta không chỉ khám phá nguyên lý làm việc cốt lõi của chúng, mà còn thông qua các ca thực chiến cụ thể hiểu sâu ưu điểm, hạn chế và tình huống áp dụng của từng mô hình.

<strong>Điểm kiến thức cốt lõi cần nhớ:</strong>

1. ReAct: chúng ta đã xây dựng một Agent ReAct có thể tương tác với thế giới bên ngoài. Thông qua vòng động “suy nghĩ – hành động – quan sát”, nó sử dụng thành công công cụ tìm kiếm để trả lời các câu hỏi thời sự mà kho tri thức của bản thân không bao phủ. Ưu điểm cốt lõi của nó là <strong>khả năng thích ứng môi trường</strong> và <strong>năng lực sửa lỗi động</strong>, khiến nó trở thành lựa chọn số một cho các nhiệm vụ mang tính khám phá, cần đầu vào từ công cụ bên ngoài.
2. Plan-and-Solve: chúng ta đã hiện thực một Agent Plan-and-Solve lập kế hoạch trước rồi thực thi sau, và dùng nó giải quyết bài toán ứng dụng toán học cần suy luận nhiều bước. Nó phân rã nhiệm vụ phức tạp thành các bước rõ ràng, rồi thực thi lần lượt. Ưu điểm cốt lõi của nó là <strong>tính cấu trúc</strong> và <strong>tính ổn định</strong>, đặc biệt phù hợp với các nhiệm vụ có đường đi logic xác định, suy luận nội bộ dày đặc.
3. Reflection (tự phản tư và lặp): chúng ta đã xây dựng một Agent Reflection có năng lực tự tối ưu. Thông qua vòng lặp “thực thi – phản tư – tối ưu”, nó tối ưu thành công một giải pháp mã nguồn ban đầu kém hiệu quả thành một phiên bản hiệu năng cao có thuật toán tốt hơn. Giá trị cốt lõi của nó là <strong>nâng cao rõ rệt chất lượng giải pháp</strong>, phù hợp với các tình huống có yêu cầu cực cao về độ chính xác và độ tin cậy của kết quả.

Ba mô hình được bàn trong chương này đại diện cho ba chiến lược khác nhau để Agent giải quyết vấn đề, như trong Bảng 4.1. Trong ứng dụng thực tế, việc chọn mô hình nào phụ thuộc vào nhu cầu cốt lõi của nhiệm vụ:

<div align="center">
<p>Bảng 4.1 Chiến lược lựa chọn các Agent Loop khác nhau</p>
<img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/4-figures/4-4.png" alt="" width="70%"/>
</div>

Đến đây, chúng ta đã nắm vững kỹ thuật cốt lõi để xây dựng một Agent đơn lẻ. Để chuyển tiếp kiến thức và đi sâu hơn vào ứng dụng thực tế, mục tiếp theo sẽ khám phá cách sử dụng các nền tảng low-code khác nhau và phương án xây dựng Agent với ít mã (low-code).

## Bài tập

> <strong>Gợi ý</strong>: một số bài tập không có đáp án chuẩn; trọng tâm là rèn luyện năng lực hiểu tổng hợp và thực hành thiết kế mô hình Agent của người học.

1. Chương này giới thiệu ba mô hình Agent kinh điển: `ReAct`, `Plan-and-Solve` và `Reflection`. Hãy phân tích:

   - Ba mô hình này có khác biệt bản chất gì trong cách tổ chức “suy nghĩ” và “hành động”?
   - Nếu cần thiết kế một “trợ lý điều khiển nhà thông minh” (cần điều khiển đèn, điều hòa, rèm cửa và nhiều thiết bị khác, đồng thời tự động điều chỉnh theo thói quen người dùng), bạn sẽ chọn mô hình nào làm kiến trúc nền tảng? Vì sao?
   - Có thể kết hợp ba mô hình này với nhau hay không? Nếu có, hãy thử thiết kế một kiến trúc Agent lai và giải thích tình huống áp dụng của nó.

2. Trong hiện thực `ReAct` ở mục 4.2, chúng ta dùng biểu thức chính quy để phân tích đầu ra của mô hình ngôn ngữ lớn (như `Thought` và `Action`). Hãy suy nghĩ:

   - Phương pháp phân tích hiện tại có những điểm yếu tiềm ẩn nào? Trong tình huống nào có thể thất bại?
   - Ngoài biểu thức chính quy, còn có phương án phân tích đầu ra nào vững chắc hơn?
   - Thử sửa mã nguồn của chương này, dùng một định dạng đầu ra đáng tin cậy hơn, và so sánh ưu, nhược điểm của hai phương án.

3. Gọi công cụ là một trong những năng lực cốt lõi của Agent hiện đại. Dựa trên thiết kế `ToolExecutor` ở mục 4.2.2, hãy hoàn thành bài thực hành mở rộng sau:

   > <strong>Gợi ý</strong>: đây là bài thực hành tay, khuyến nghị thực sự viết mã nguồn.

   - Thêm một công cụ “máy tính” cho Agent `ReAct`, để nó có thể xử lý các bài toán tính toán phức tạp (như “tính kết quả của `(123 + 456) × 789/ 12 = ?`”).
   - Thiết kế và hiện thực một cơ chế xử lý “chọn công cụ thất bại”: khi Agent nhiều lần gọi sai công cụ hoặc cung cấp tham số sai, hệ thống nên hướng dẫn nó sửa như thế nào?
   - Suy nghĩ: nếu số công cụ có thể gọi tăng lên $50$ thậm chí $100$, cách mô tả công cụ hiện tại có còn hoạt động hiệu quả không? Khi số công cụ có thể gọi tăng đáng kể theo nhu cầu nghiệp vụ, từ góc độ kỹ thuật nên tối ưu cách tổ chức và truy xuất công cụ như thế nào?

4. Mô hình `Plan-and-Solve` phân rã nhiệm vụ thành hai giai đoạn “lập kế hoạch” và “thực thi”. Hãy phân tích sâu:

   - Trong hiện thực ở mục 4.3, kế hoạch sinh ở giai đoạn lập kế hoạch là “tĩnh” (sinh một lần, không thể sửa). Nếu trong quá trình thực thi phát hiện một bước không thể hoàn thành hoặc kết quả không như mong đợi, nên thiết kế cơ chế “tái lập kế hoạch động” như thế nào?
   - So sánh `Plan-and-Solve` với `ReAct`: khi xử lý nhiệm vụ như “đặt một chuyến công tác từ Bắc Kinh đến Thượng Hải (gồm vé máy bay, khách sạn, thuê xe)”, mô hình nào phù hợp hơn? Vì sao?
   - Thử thiết kế một hệ thống “lập kế hoạch phân tầng”: trước tiên sinh kế hoạch trừu tượng cấp cao, sau đó với mỗi bước cấp cao lại sinh kế hoạch con chi tiết. Thiết kế này có ưu điểm gì?

5. Cơ chế `Reflection` nâng cao chất lượng đầu ra thông qua vòng lặp “thực thi – phản tư – tối ưu”. Hãy suy nghĩ:

   - Trong ca sinh mã nguồn ở mục 4.4, các giai đoạn khác nhau dùng cùng một mô hình. Nếu dùng hai mô hình khác nhau (ví dụ dùng một mô hình mạnh hơn để phản tư, một mô hình nhanh hơn để thực thi) sẽ mang lại ảnh hưởng gì?
   - Điều kiện dừng của cơ chế `Reflection` là “phản hồi có chứa <strong>không cần cải thiện</strong>” hoặc “đạt số lần lặp tối đa”. Thiết kế này có hợp lý không? Có thể thiết kế một điều kiện dừng thông minh hơn không?
   - Giả sử bạn cần xây dựng một “trợ lý viết bài báo học thuật” có thể sinh bản nháp và liên tục tối ưu nội dung bài báo. Hãy thiết kế một cơ chế Reflection đa chiều, phản tư và cải thiện từ nhiều góc độ như tính logic của đoạn văn, tính đổi mới của phương pháp, cách diễn đạt ngôn ngữ, quy chuẩn trích dẫn, v.v.

6. Kỹ thuật prompt là công nghệ then chốt ảnh hưởng đến hiệu quả cuối cùng của Agent. Chương này trình bày nhiều mẫu prompt được thiết kế cẩn thận. Hãy phân tích:

   - So sánh prompt `ReAct` ở mục 4.2.3 với prompt `Plan-and-Solve` ở mục 4.3.2; rõ ràng chúng có khác biệt rõ rệt về thiết kế cấu trúc. Những khác biệt này phục vụ logic cốt lõi của mỗi mô hình như thế nào?
   - Trong prompt `Reflection` ở mục 4.4.3, chúng ta dùng thiết lập vai trò “bạn là một chuyên gia đánh giá mã nguồn cực kỳ nghiêm khắc”. Thử sửa thiết lập vai trò này (ví dụ đổi thành “bạn là người duy trì dự án mã nguồn mở chú trọng khả năng đọc của mã nguồn”), quan sát thay đổi của kết quả đầu ra, và tổng kết ảnh hưởng của thiết lập vai trò đến hành vi Agent.
   - Thêm ví dụ `few-shot` vào prompt thường có thể nâng cao rõ rệt khả năng tuân thủ định dạng cụ thể của mô hình. Hãy thử thêm ví dụ `few-shot` cho một Agent trong chương này và so sánh hiệu quả.

7. Một công ty khởi nghiệp thương mại điện tử hiện muốn dùng “Agent chăm sóc khách hàng” thay cho nhân viên chăm sóc khách hàng thật để giảm chi phí và tăng hiệu quả; nó cần có các chức năng sau:

   a. Hiểu lý do yêu cầu hoàn tiền của người dùng.

   b. Tra cứu thông tin đơn hàng và trạng thái vận chuyển của người dùng.

   c. Dựa trên chính sách công ty, thông minh phán đoán xem có nên phê duyệt hoàn tiền hay không.

   d. Sinh một email phản hồi phù hợp và gửi đến hộp thư người dùng.

   e. Nếu phán đoán quyết định có tranh cãi nhất định (độ tự tin thấp hơn ngưỡng), có thể tự phản tư và đưa ra đề xuất thận trọng hơn.

   Lúc này, với vai trò người phụ trách sản phẩm:
   - Bạn sẽ chọn mô hình nào (hoặc kết hợp những mô hình nào) trong chương này làm kiến trúc cốt lõi của hệ thống?
   - Hệ thống này cần những công cụ nào? Hãy liệt kê ít nhất 3 công cụ và mô tả chức năng của chúng.
   - Thiết kế prompt như thế nào để đảm bảo quyết định của Agent vừa phù hợp lợi ích công ty, vừa giữ thái độ thân thiện với người dùng?
   - Sản phẩm này sau khi ra mắt có thể đối mặt với những rủi ro và thách thức nào? Làm thế nào giảm thiểu những rủi ro này bằng phương tiện kỹ thuật?

## Tài liệu tham khảo

[1] Yao S, Zhao J, Yu D, et al. React: Synergizing reasoning and acting in language models[C]//International Conference on Learning Representations (ICLR). 2023.

[2] Wang L, Xu W, Lan Y, et al. Plan-and-solve prompting: Improving zero-shot chain-of-thought reasoning by large language models[J]. arXiv preprint arXiv:2305.04091, 2023.

[3] Shinn N, Cassano F, Gopinath A, et al. Reflexion: Language agents with verbal reinforcement learning[J]. Advances in Neural Information Processing Systems, 2023, 36: 8634-8652.

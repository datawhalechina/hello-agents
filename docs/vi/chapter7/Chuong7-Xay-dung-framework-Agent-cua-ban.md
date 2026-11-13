# Chương 7: Xây dựng framework Agent của bạn

Ở các chương trước, chúng ta đã trình bày kiến thức nền tảng về Agent và trải nghiệm sự thuận tiện mà các framework chủ lưu mang lại. Từ chương này, chúng ta bước vào một giai đoạn nhiều thách thức nhưng cũng có giá trị hơn: **từ con số không, từng bước xây dựng một framework Agent – HelloAgents**.

Để đảm bảo tính liên tục và khả năng tái lập của quá trình học, HelloAgents sẽ được phát triển theo hình thức lặp phiên bản. Mỗi chương sẽ thêm mô-đun chức năng mới trên nền chương trước, đồng thời trình bày và hiện thực các điểm kiến thức liên quan đến Agent. Cuối cùng, chúng ta sẽ dùng framework tự xây này để hiện thực hiệu quả các ca ứng dụng nâng cao trong các chương sau của cuốn sách.

## 7.1 Thiết kế kiến trúc tổng thể của framework

### 7.1.1 Vì sao cần tự xây framework Agent

Trong bối cảnh công nghệ Agent phát triển nhanh chóng hiện nay, trên thị trường đã có nhiều framework Agent trưởng thành. Vậy tại sao chúng ta vẫn phải xây một framework mới từ con số không?

(1) Sự lặp nhanh và hạn chế của framework trên thị trường

Lĩnh vực Agent là một lĩnh vực phát triển nhanh, khái niệm mới xuất hiện bất cứ lúc nào; với thiết kế Agent, mỗi framework có định vị và cách hiểu riêng, nhưng điểm kiến thức cốt lõi của Agent là nhất quán.

- **Độ phức tạp do trừu tượng hóa quá mức**: nhiều framework theo đuổi tính tổng quát đã đưa vào lượng lớn tầng trừu tượng và tùy chọn cấu hình. Lấy LangChain làm ví dụ; cơ chế gọi chuỗi của nó tuy linh hoạt nhưng với người mới, đường cong học tập dốc, thường cần hiểu nhiều khái niệm mới hoàn thành được nhiệm vụ đơn giản.
- **Tính không ổn định do lặp nhanh**: các framework thương mại để giành thị trường thường xuyên thay đổi giao diện API. Nhà phát triển thường gặp tình trạng mã không chạy được sau khi nâng phiên bản, chi phí bảo trì cao.
- **Logic hiện thực hộp đen**: nhiều framework đóng gói logic cốt lõi quá chặt, nhà phát triển khó hiểu cơ chế làm việc bên trong của Agent, thiếu năng lực tùy biến sâu. Khi gặp vấn đề chỉ có thể dựa vào tài liệu và hỗ trợ cộng đồng; đặc biệt nếu cộng đồng không đủ sôi động, một phản hồi có thể rất lâu không ai thúc đẩy, ảnh hưởng hiệu quả phát triển sau này.
- **Độ phức tạp của quan hệ phụ thuộc**: framework trưởng thành thường mang theo nhiều gói phụ thuộc, kích thước gói cài đặt lớn; khi cần phối hợp với mã dự án khác có thể xảy ra xung đột phụ thuộc.

(2) Bước nhảy năng lực từ người dùng sang người xây dựng

Xây framework Agent của riêng mình thực chất là quá trình chuyển từ “người dùng” sang “người xây dựng”. Giá trị của sự chuyển đổi này là lâu dài.

- **Hiểu sâu nguyên lý làm việc của Agent**: thông qua tự tay hiện thực từng thành phần, nhà phát triển có thể thực sự hiểu quá trình suy nghĩ của Agent, cơ chế gọi công cụ, cũng như ưu nhược điểm và khác biệt của các mẫu thiết kế.
- **Có toàn quyền kiểm soát**: tự xây framework nghĩa là kiểm soát hoàn toàn từng dòng mã, có thể tinh chỉnh chính xác theo nhu cầu cụ thể, không bị ràng buộc bởi triết lý thiết kế của framework bên thứ ba.
- **Rèn luyện năng lực thiết kế hệ thống**: quá trình xây framework liên quan đến các kỹ năng cốt lõi của kỹ thuật phần mềm như thiết kế mô-đun, trừu tượng hóa giao diện, xử lý lỗi; những năng lực này có giá trị quan trọng cho sự trưởng thành lâu dài của nhà phát triển.

(3) Nhu cầu tùy biến và sự cần thiết nắm vững sâu

Trong ứng dụng thực tế, nhu cầu về Agent ở các tình huống khác nhau rất lớn; thường cần phát triển thứ cấp trên nền framework tổng quát.

- **Nhu cầu tối ưu lĩnh vực cụ thể**: các lĩnh vực dọc như tài chính, y tế, giáo dục thường cần mẫu prompt có mục tiêu, tích hợp công cụ đặc biệt và chiến lược bảo mật tùy biến.
- **Kiểm soát chính xác hiệu năng và tài nguyên**: trong môi trường sản xuất, thời gian phản hồi, mức chiếm bộ nhớ, năng lực xử lý đồng thời đều có yêu cầu nghiêm ngặt; phương án “một cỡ cho tất cả” của framework tổng quát thường không đáp ứng nhu cầu tinh chỉnh.
- **Yêu cầu minh bạch cho học tập và giảng dạy**: trong cảnh giảng dạy của chúng ta, người học mong muốn thấy rõ từng bước xây dựng Agent, hiểu cơ chế làm việc của các mô hình khác nhau; điều này đòi hỏi framework có khả năng quan sát và giải thích cao.

### 7.1.2 Triết lý thiết kế của framework HelloAgents

Xây một framework Agent mới, điểm then chốt không nằm ở số lượng chức năng, mà ở việc triết lý thiết kế có thực sự giải quyết điểm đau của framework hiện có hay không. Thiết kế framework HelloAgents xoay quanh một câu hỏi cốt lõi: làm sao để người học vừa nhanh chóng bắt đầu, vừa hiểu sâu nguyên lý làm việc của Agent?

Khi lần đầu tiếp xúc bất kỳ framework trưởng thành nào, bạn có thể bị thu hút bởi chức năng phong phú của nó, nhưng sẽ nhanh chóng nhận ra một vấn đề: để hoàn thành một nhiệm vụ đơn giản, thường cần hiểu hơn mười khái niệm khác nhau như Chain, Agent, Tool, Memory, Retriever. Mỗi khái niệm có tầng trừu tượng riêng, đường cong học tập trở nên rất dốc. Độ phức tạp này tuy mang lại chức năng mạnh mẽ nhưng cũng trở thành rào cản với người mới. Framework HelloAgents cố gắng tìm điểm cân bằng giữa đầy đủ chức năng và thân thiện với học tập, hình thành bốn triết lý thiết kế cốt lõi.

(1) Cân bằng giữa nhẹ và thân thiện với giảng dạy

Một framework học tập xuất sắc nên có khả năng đọc hoàn chỉnh. HelloAgents chia mã cốt lõi theo chương, dựa trên nguyên tắc đơn giản: bất kỳ nhà phát triển có nền tảng lập trình nhất định đều có thể hiểu hoàn toàn nguyên lý làm việc của framework trong thời gian hợp lý. Về quản lý phụ thuộc, framework áp dụng chiến lược tối giản. Ngoài SDK chính thức của OpenAI và vài thư viện nền tảng cần thiết, không đưa vào phụ thuộc nặng nào. Khi gặp vấn đề, chúng ta có thể định vị trực tiếp vào mã của framework, không cần tìm câu trả lời trong quan hệ phụ thuộc phức tạp.

(2) Lựa chọn thực dụng dựa trên API chuẩn

API của OpenAI đã trở thành chuẩn ngành; gần như mọi nhà cung cấp LLM chủ lưu đều cố gắng tương thích giao diện này. HelloAgents chọn xây trên chuẩn này thay vì phát minh lại một bộ giao diện trừu tượng. Quyết định này xuất phát từ vài động cơ. Trước tiên là đảm bảo tương thích: khi đã nắm cách dùng HelloAgents, chuyển sang framework khác hoặc tích hợp vào dự án hiện có, logic gọi API tầng dưới hoàn toàn nhất quán. Thứ hai là giảm chi phí học. Bạn không cần học mô hình khái niệm mới, vì mọi thao tác đều dựa trên giao diện chuẩn bạn đã quen.

(3) Thiết kế cẩn thận lộ trình học tiến dần

HelloAgents cung cấp một lộ trình học rõ ràng. Chúng ta sẽ lưu mã học của từng chương thành một phiên bản lịch sử có thể tải bằng pip, nên không cần lo chi phí sử dụng mã, vì mỗi chức năng cốt lõi đều sẽ do chính bạn viết. Thiết kế này cho phép bạn tiến theo nhu cầu và nhịp độ của mình. Mỗi bước nâng cấp diễn ra tự nhiên, không tạo ra bước nhảy khái niệm hay đứt gãy hiểu biết. Đáng nói là nội dung chương này cũng được hoàn thiện dựa trên nội dung sáu chương trước. Đồng thời, chương này cũng đặt nền tảng framework cho phần học kiến thức nâng cao sau này.

(4) Trừu tượng “công cụ” thống nhất: vạn vật đều là công cụ

Để triệt để thực hiện triết lý nhẹ và thân thiện với giảng dạy, HelloAgents thực hiện một đơn giản hóa then chốt về kiến trúc: ngoài lớp Agent cốt lõi, mọi thứ đều là Tools. Nhiều mô-đun như Memory (bộ nhớ), RAG (truy xuất tăng cường sinh), RL (học tăng cường), MCP (giao thức) vốn cần học riêng trong framework khác, trong HelloAgents đều được trừu tượng hóa thống nhất thành một loại “công cụ”. Ý định ban đầu của thiết kế này là loại bỏ tầng trừu tượng không cần thiết, để người học quay về logic cốt lõi trực quan nhất “Agent gọi công cụ”, từ đó thực sự hiện thực sự thống nhất giữa bắt đầu nhanh và hiểu sâu.

### 7.1.3 Mục tiêu học tập của chương này

Trước tiên hãy xem nội dung học tập cốt lõi của chương 7:

```
hello-agents/
├── hello_agents/
│   │
│   ├── core/                     # Tầng framework cốt lõi
│   │   ├── agent.py              # Lớp cơ sở Agent
│   │   ├── llm.py                # Giao diện thống nhất HelloAgentsLLM
│   │   ├── message.py            # Hệ thống tin nhắn
│   │   ├── config.py             # Quản lý cấu hình
│   │   └── exceptions.py         # Hệ thống ngoại lệ
│   │
│   ├── agents/                   # Tầng hiện thực Agent
│   │   ├── simple_agent.py       # Hiện thực SimpleAgent
│   │   ├── react_agent.py        # Hiện thực ReActAgent
│   │   ├── reflection_agent.py   # Hiện thực ReflectionAgent
│   │   └── plan_solve_agent.py   # Hiện thực PlanAndSolveAgent
│   │
│   ├── tools/                    # Tầng hệ thống công cụ
│   │   ├── base.py               # Lớp cơ sở công cụ
│   │   ├── registry.py           # Cơ chế đăng ký công cụ
│   │   ├── chain.py              # Hệ thống quản lý chuỗi công cụ
│   │   ├── async_executor.py     # Bộ thực thi công cụ bất đồng bộ
│   │   └── builtin/              # Bộ công cụ tích hợp
│   │       ├── calculator.py     # Công cụ tính toán
│   │       └── search.py         # Công cụ tìm kiếm
└──
```

Trước khi bắt đầu viết mã cụ thể, chúng ta cần xây dựng một bản thiết kế kiến trúc rõ ràng. Thiết kế kiến trúc của HelloAgents tuân theo nguyên tắc cốt lõi “phân tầng tách rời, trách nhiệm đơn nhất, giao diện thống nhất”; điều này vừa giữ tính tổ chức của mã, vừa thuận tiện mở rộng nội dung theo chương.

**Bắt đầu nhanh: cài đặt framework HelloAgents**

Để người đọc nhanh chóng trải nghiệm đầy đủ chức năng của chương này, chúng ta cung cấp gói Python có thể cài trực tiếp. Bạn có thể cài phiên bản tương ứng của chương này bằng lệnh sau:

```bash
# Liên kết mã framework hello-agents: https://github.com/jjyaoao/helloagents
# Phiên bản Python yêu cầu >=3.10
pip install "hello-agents==0.1.1"
```

Việc học chương này có thể theo hai cách:

1. **Học qua trải nghiệm**: cài framework trực tiếp bằng `pip`, chạy mã ví dụ, nhanh chóng trải nghiệm các chức năng
2. **Học sâu**: theo nội dung chương này, tự hiện thực từng thành phần từ con số không, hiểu sâu tư tưởng thiết kế và chi tiết hiện thực của framework

Chúng ta khuyến nghị lộ trình “trải nghiệm trước, hiện thực sau”. Trong chương này, chúng ta cung cấp tệp kiểm thử hoàn chỉnh; bạn có thể viết lại hàm cốt lõi và chạy kiểm thử để kiểm tra hiện thực của mình có đúng hay không. Cách học này vừa đảm bảo tính thực hành, vừa đảm bảo hiệu quả học tập. Nếu muốn hiểu sâu chi tiết hiện thực của framework, hoặc muốn tham gia phát triển framework, có thể truy cập [kho GitHub](https://github.com/jjyaoao/helloagents).

Trước khi bắt đầu, hãy dùng 30 giây trải nghiệm xây Agent đơn giản với Hello-agents!

```python
# Cấu hình API mô hình lớn trong .env ở thư mục cùng cấp; có thể tham khảo .env.example đi kèm thư mục code, hoặc dùng lại .env của các ca ở chương trước.
from hello_agents import SimpleAgent, HelloAgentsLLM
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

# Tạo thực thể LLM - framework tự động phát hiện provider
llm = HelloAgentsLLM()

# Hoặc chỉ định provider thủ công (tùy chọn)
# llm = HelloAgentsLLM(provider="modelscope")

# Tạo SimpleAgent
agent = SimpleAgent(
    name="Trợ lý AI",
    llm=llm,
    system_prompt="Bạn là một trợ lý AI hữu ích"
)

# Hội thoại cơ bản
response = agent.run("Xin chào! Hãy giới thiệu về bạn")
print(response)

# Thêm chức năng công cụ (tùy chọn)
from hello_agents.tools import CalculatorTool
calculator = CalculatorTool()
# Cần hiện thực MySimpleAgent ở mục 7.4.1 để gọi; các chương sau sẽ hỗ trợ cách gọi này
# agent.add_tool(calculator)

# Bây giờ có thể sử dụng công cụ
response = agent.run("Hãy giúp tôi tính 2 + 3 * 4")
print(response)

# Xem lịch sử hội thoại
print(f"Số tin nhắn lịch sử: {len(agent.get_history())}")
```



## 7.2 Mở rộng HelloAgentsLLM

Nội dung mục này sẽ lặp và nâng cấp dựa trên `HelloAgentsLLM` đã tạo ở mục 4.1.3. Chúng ta sẽ biến client cơ bản này thành một trung tâm gọi mô hình có khả năng thích ứng cao hơn. Lần nâng cấp này xoay quanh ba mục tiêu sau:

1. **Hỗ trợ đa nhà cung cấp**: hiện thực chuyển đổi liền mạch giữa nhiều nhà cung cấp LLM chủ lưu như OpenAI, ModelScope, Zhipu AI, tránh framework bị ràng buộc với một nhà cung cấp cụ thể.
2. **Tích hợp mô hình cục bộ**: đưa vào VLLM và Ollama – hai phương án triển khai cục bộ hiệu năng cao – làm bổ sung cấp sản xuất cho phương án Hugging Face Transformers ở mục 3.2.3, đáp ứng nhu cầu quyền riêng tư dữ liệu và kiểm soát chi phí.
3. **Cơ chế tự động phát hiện**: thiết lập một cơ chế nhận diện tự động để framework có thể suy luận thông minh loại dịch vụ LLM đang dùng dựa trên thông tin môi trường, đơn giản hóa quá trình cấu hình của người dùng.

### 7.2.1 Hỗ trợ đa nhà cung cấp

Lớp `HelloAgentsLLM` chúng ta định nghĩa trước đó đã có thể kết nối bất kỳ dịch vụ tương thích giao diện OpenAI thông qua hai tham số cốt lõi `api_key` và `base_url`. Về lý thuyết, điều này đảm bảo tính tổng quát, nhưng trong ứng dụng thực tế, các nhà cung cấp khác nhau có khác biệt về cách đặt tên biến môi trường, địa chỉ API mặc định và mô hình khuyến nghị. Nếu mỗi lần chuyển nhà cung cấp người dùng đều phải tra cứu thủ công và sửa mã, hiệu quả phát triển sẽ bị ảnh hưởng lớn. Để giải quyết vấn đề này, chúng ta đưa vào `provider`. Ý tưởng cải tiến là: để `HelloAgentsLLM` xử lý bên trong chi tiết cấu hình của các nhà cung cấp khác nhau, từ đó cung cấp cho người dùng trải nghiệm gọi thống nhất, gọn gàng. Chi tiết hiện thực cụ thể sẽ được trình bày ở mục 7.2.3 “Cơ chế tự động phát hiện”; ở đây, trước tiên chúng ta tập trung vào cách dùng cơ chế này để mở rộng framework.

Dưới đây, chúng ta sẽ trình diễn cách kế thừa `HelloAgentsLLM` để thêm hỗ trợ nền tảng ModelScope. Chúng ta mong người đọc không chỉ học cách “sử dụng” framework mà còn nắm cách “mở rộng” framework. Sửa trực tiếp mã nguồn thư viện đã cài là cách làm không được khuyến nghị, vì nó khiến việc nâng cấp thư viện sau này trở nên khó khăn.

(1) Tạo lớp LLM tùy chỉnh và kế thừa

Giả sử thư mục dự án của chúng ta có tệp `my_llm.py`. Trước tiên, chúng ta import lớp cơ sở `HelloAgentsLLM` từ thư viện `hello_agents`, sau đó tạo lớp mới tên `MyLLM` kế thừa nó.

```python
# my_llm.py
import os
from typing import Optional
from openai import OpenAI
from hello_agents import HelloAgentsLLM

class MyLLM(HelloAgentsLLM):
    """
    Một client LLM tùy chỉnh, thêm hỗ trợ ModelScope thông qua kế thừa.
    """
    pass # Tạm để trống
```

(2) Ghi đè phương thức `__init__` để hỗ trợ nhà cung cấp mới

Tiếp theo, chúng ta ghi đè phương thức `__init__` trong lớp `MyLLM`. Mục tiêu là: khi người dùng truyền `provider="modelscope"`, thực thi logic tùy chỉnh của chúng ta; ngược lại, gọi logic gốc của lớp cha `HelloAgentsLLM`, để nó tiếp tục hỗ trợ các nhà cung cấp tích hợp khác như OpenAI.

```python
class MyLLM(HelloAgentsLLM):
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = "auto",
        **kwargs
    ):
        # Kiểm tra provider có phải 'modelscope' mà chúng ta muốn xử lý hay không
        if provider == "modelscope":
            print("Đang dùng Provider ModelScope tùy chỉnh")
            self.provider = "modelscope"

            # Phân giải thông tin xác thực của ModelScope
            self.api_key = api_key or os.getenv("MODELSCOPE_API_KEY")
            self.base_url = base_url or "https://api-inference.modelscope.cn/v1/"

            # Xác minh thông tin xác thực có tồn tại hay không
            if not self.api_key:
                raise ValueError("ModelScope API key not found. Please set MODELSCOPE_API_KEY environment variable.")

            # Đặt mô hình mặc định và các tham số khác
            self.model = model or os.getenv("LLM_MODEL_ID") or "Qwen/Qwen2.5-VL-72B-Instruct"
            self.temperature = kwargs.get('temperature', 0.7)
            self.max_tokens = kwargs.get('max_tokens')
            self.timeout = kwargs.get('timeout', 60)

            # Dùng các tham số đã lấy để tạo thực thể client OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)

        else:
            # Nếu không phải modelscope, dùng hoàn toàn logic gốc của lớp cha để xử lý
            super().__init__(model=model, api_key=api_key, base_url=base_url, provider=provider, **kwargs)

```

Đoạn mã này thể hiện tư tưởng “ghi đè”: chúng ta chặn trường hợp `provider="modelscope"` và xử lý đặc biệt; với mọi trường hợp khác, giao lại cho lớp cha qua `super().__init__(...)`, giữ nguyên toàn bộ chức năng của framework gốc.

(3) Sử dụng lớp `MyLLM` tùy chỉnh

Bây giờ, trong logic nghiệp vụ của dự án, chúng ta có thể dùng lớp `MyLLM` của mình giống như `HelloAgentsLLM` gốc.

Trước tiên, cấu hình khóa API của ModelScope trong tệp `.env`:

```bash
# .env file
MODELSCOPE_API_KEY="your-modelscope-api-key"
```

Sau đó, import và dùng `MyLLM` trong chương trình chính:

```python
# my_main.py
from dotenv import load_dotenv
from my_llm import MyLLM # Lưu ý: ở đây import lớp của chúng ta

# Tải biến môi trường
load_dotenv()

# Khởi tạo client chúng ta đã ghi đè, và chỉ định provider
llm = MyLLM(provider="modelscope")

# Chuẩn bị tin nhắn
messages = [{"role": "user", "content": "Xin chào, hãy giới thiệu về bạn."}]

# Thực hiện gọi; các phương thức như think đã kế thừa từ lớp cha, không cần ghi đè
response_stream = llm.think(messages)

# In phản hồi
print("ModelScope Response:")
for chunk in response_stream:
    # chunk đã được in một lần trong thư viện my_llm, ở đây chỉ cần pass
    # print(chunk, end="", flush=True)
    pass
```

Qua các bước trên, chúng ta đã mở rộng thành công chức năng mới cho thư viện `hello-agents` mà không sửa mã nguồn thư viện. Cách này không chỉ đảm bảo mã gọn gàng, dễ bảo trì, mà còn khiến chức năng tùy biến của chúng ta không bị mất khi nâng cấp thư viện `hello-agents` trong tương lai.

### 7.2.2 Gọi mô hình cục bộ

Ở mục 3.2.3, chúng ta đã học cách dùng thư viện Hugging Face Transformers để chạy trực tiếp mô hình mã nguồn mở cục bộ. Phương pháp này rất phù hợp cho học nhập môn và kiểm chứng chức năng, nhưng hiện thực tầng dưới của nó có hiệu năng hạn chế khi xử lý yêu cầu đồng thời cao, thường không phải lựa chọn đầu tiên cho môi trường sản xuất.

Để hiện thực dịch vụ suy luận mô hình cục bộ hiệu năng cao, cấp sản xuất, cộng đồng đã cho ra đời các công cụ xuất sắc như VLLM và Ollama. Chúng thông qua các kỹ thuật như continuous batching, PagedAttention, nâng cao rõ rệt thông lượng và hiệu quả vận hành của mô hình, đồng thời đóng gói mô hình thành dịch vụ API tương thích chuẩn OpenAI. Điều này có nghĩa chúng ta có thể tích hợp liền mạch chúng vào `HelloAgentsLLM`.

**VLLM**

VLLM là thư viện Python hiệu năng cao được thiết kế cho suy luận LLM. Thông qua các kỹ thuật tiên tiến như PagedAttention, nó có thể đạt thông lượng cao gấp nhiều lần hiện thực Transformers tiêu chuẩn. Dưới đây là các bước đầy đủ để triển khai dịch vụ VLLM cục bộ:

Trước tiên, cần cài VLLM theo môi trường phần cứng của bạn (đặc biệt là phiên bản CUDA). Khuyến nghị tuân theo [tài liệu chính thức](https://docs.vllm.ai/en/latest/getting_started/installation.html) để cài, tránh vấn đề không khớp phiên bản.

```python
pip install vllm
```

Sau khi cài xong, dùng lệnh sau để khởi động dịch vụ API tương thích OpenAI. VLLM sẽ tự động tải trọng số mô hình chỉ định từ Hugging Face Hub (nếu cục bộ chưa có). Chúng ta vẫn lấy mô hình Qwen1.5-0.5B-Chat làm ví dụ:

```
# Khởi động dịch vụ VLLM và tải mô hình Qwen1.5-0.5B-Chat
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen1.5-0.5B-Chat \
    --host 0.0.0.0 \
    --port 8000
```

Sau khi dịch vụ khởi động, nó sẽ cung cấp API tương thích OpenAI tại địa chỉ `http://localhost:8000/v1`.

**Ollama**

Ollama đơn giản hóa hơn nữa việc quản lý và triển khai mô hình cục bộ; nó đóng gói các bước tải mô hình, cấu hình và khởi động dịch vụ vào một lệnh, rất phù hợp để bắt đầu nhanh. Truy cập [trang chủ](https://ollama.com) của Ollama để tải và cài client phù hợp với hệ điều hành của bạn.

Sau khi cài, mở terminal, thực thi lệnh sau để tải và chạy một mô hình (lấy Llama 3 làm ví dụ). Ollama sẽ tự động xử lý tải mô hình, đóng gói dịch vụ và cấu hình tăng tốc phần cứng.

```
# Lần chạy đầu sẽ tự động tải mô hình; các lần sau khởi động dịch vụ trực tiếp
ollama run llama3
```

Khi bạn thấy lời nhắc tương tác của mô hình trong terminal, nghĩa là dịch vụ đã khởi động thành công ở chế độ nền. Ollama mặc định công khai giao diện API tương thích OpenAI tại địa chỉ `http://localhost:11434/v1`.

**Kết nối `HelloAgentsLLM`**

Vì VLLM và Ollama đều tuân theo API chuẩn ngành, quá trình kết nối chúng vào `HelloAgentsLLM` rất đơn giản. Chúng ta chỉ cần coi chúng là một `provider` mới khi khởi tạo client.

Ví dụ, kết nối dịch vụ **VLLM** chạy cục bộ:

```python
llm_client = HelloAgentsLLM(
    provider="vllm",
    model="Qwen/Qwen1.5-0.5B-Chat", # Phải khớp với mô hình chỉ định khi khởi động dịch vụ
    base_url="http://localhost:8000/v1",
    api_key="vllm" # Dịch vụ cục bộ thường không cần API Key thật; có thể điền chuỗi không rỗng bất kỳ
)
```

Hoặc, đặt biến môi trường và để client tự động phát hiện, hiện thực không cần sửa mã:

```bash
# Đặt trong tệp .env
LLM_BASE_URL="http://localhost:8000/v1"
LLM_API_KEY="vllm"

# Trong mã Python chỉ cần khởi tạo trực tiếp
llm_client = HelloAgentsLLM() # Sẽ tự động phát hiện là vllm
```

Tương tự, kết nối dịch vụ **Ollama** cục bộ cũng đơn giản như vậy:

```python
llm_client = HelloAgentsLLM(
    provider="ollama",
    model="llama3", # Phải khớp với mô hình chỉ định trong `ollama run`
    base_url="http://localhost:11434/v1",
    api_key="ollama" # Dịch vụ cục bộ cũng không cần Key thật
)
```

Với thiết kế thống nhất này, mã cốt lõi của Agent không cần sửa gì cũng có thể tự do chuyển đổi giữa API đám mây và mô hình cục bộ. Điều này mang lại tính linh hoạt rất lớn cho phát triển, triển khai, kiểm soát chi phí và bảo vệ quyền riêng tư dữ liệu của ứng dụng sau này.

### 7.2.3 Cơ chế tự động phát hiện

Để giảm tối đa gánh nặng cấu hình cho người dùng và tuân theo nguyên tắc “quy ước ưu việt hơn cấu hình”, `HelloAgentsLLM` thiết kế hai phương thức phụ trợ cốt lõi bên trong: `_auto_detect_provider` và `_resolve_credentials`. Chúng phối hợp với nhau; `_auto_detect_provider` chịu trách nhiệm suy luận nhà cung cấp dựa trên thông tin môi trường, còn `_resolve_credentials` hoàn thành cấu hình tham số cụ thể theo kết quả suy luận.

Phương thức `_auto_detect_provider` chịu trách nhiệm thử tự động suy luận nhà cung cấp theo thứ tự ưu tiên sau, dựa trên thông tin môi trường:

1. **Ưu tiên cao nhất: kiểm tra biến môi trường của nhà cung cấp cụ thể** Đây là căn cứ phán đoán trực tiếp và đáng tin cậy nhất. Framework sẽ lần lượt kiểm tra các biến môi trường như `MODELSCOPE_API_KEY`, `OPENAI_API_KEY`, `ZHIPU_API_KEY` có tồn tại hay không. Khi phát hiện bất kỳ biến nào, nó xác định ngay nhà cung cấp tương ứng.

2. **Ưu tiên thứ hai: phán đoán theo `base_url`** Nếu người dùng không đặt khóa của nhà cung cấp cụ thể nhưng đặt `LLM_BASE_URL` chung, framework sẽ chuyển sang phân tích URL này.

   - **Khớp tên miền**: nhận diện nhà cung cấp đám mây bằng cách kiểm tra URL có chứa các chuỗi đặc trưng như `"api-inference.modelscope.cn"`, `"api.openai.com"`.

   - **Khớp cổng**: nhận diện phương án triển khai cục bộ bằng cách kiểm tra URL có chứa cổng chuẩn của dịch vụ cục bộ như `:11434` (Ollama), `:8000` (VLLM).

3. **Phán đoán phụ trợ: phân tích định dạng khóa API** Trong một số trường hợp, nếu hai cách trên không xác định được, framework sẽ thử phân tích định dạng của biến môi trường chung `LLM_API_KEY`. Ví dụ, khóa API của một số nhà cung cấp có tiền tố cố định hoặc định dạng mã hóa đặc thù. Tuy nhiên, vì cách này có thể mơ hồ (ví dụ nhiều nhà cung cấp có định dạng khóa giống nhau), độ ưu tiên của nó thấp, chỉ dùng làm phương tiện phụ trợ.

Một phần mã then chốt của nó như sau:

```python
def _auto_detect_provider(self, api_key: Optional[str], base_url: Optional[str]) -> str:
    """
    Tự động phát hiện nhà cung cấp LLM
    """
    # 1. Kiểm tra biến môi trường của nhà cung cấp cụ thể (ưu tiên cao nhất)
    if os.getenv("MODELSCOPE_API_KEY"): return "modelscope"
    if os.getenv("OPENAI_API_KEY"): return "openai"
    if os.getenv("ZHIPU_API_KEY"): return "zhipu"
    # ... kiểm tra biến môi trường của các nhà cung cấp khác

    # Lấy biến môi trường chung
    actual_api_key = api_key or os.getenv("LLM_API_KEY")
    actual_base_url = base_url or os.getenv("LLM_BASE_URL")

    # 2. Phán đoán theo base_url
    if actual_base_url:
        base_url_lower = actual_base_url.lower()
        if "api-inference.modelscope.cn" in base_url_lower: return "modelscope"
        if "open.bigmodel.cn" in base_url_lower: return "zhipu"
        if "localhost" in base_url_lower or "127.0.0.1" in base_url_lower:
            if ":11434" in base_url_lower: return "ollama"
            if ":8000" in base_url_lower: return "vllm"
            return "local" # Cổng cục bộ khác

    # 3. Phán đoán phụ trợ theo định dạng API key
    if actual_api_key:
        if actual_api_key.startswith("ms-"): return "modelscope"
        # ... phán đoán định dạng khóa khác

    # 4. Mặc định trả về 'auto', dùng cấu hình chung
    return "auto"
```

Sau khi `provider` được xác định (dù người dùng chỉ định hay tự động phát hiện), phương thức `_resolve_credentials` sẽ tiếp nhận xử lý cấu hình khác biệt của nhà cung cấp. Nó sẽ dựa trên giá trị `provider`, chủ động tìm biến môi trường tương ứng và đặt `base_url` mặc định cho nó. Một phần hiện thực then chốt như sau:

```python
def _resolve_credentials(self, api_key: Optional[str], base_url: Optional[str]) -> tuple[str, str]:
    """Phân giải API key và base_url theo provider"""
    if self.provider == "openai":
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
        return resolved_api_key, resolved_base_url

    elif self.provider == "modelscope":
        resolved_api_key = api_key or os.getenv("MODELSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
        resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or "https://api-inference.modelscope.cn/v1/"
        return resolved_api_key, resolved_base_url

    # ... logic của các nhà cung cấp khác
```

Hãy cảm nhận sự thuận tiện của tự động phát hiện qua một ví dụ đơn giản. Giả sử người dùng muốn dùng dịch vụ Ollama cục bộ; họ chỉ cần cấu hình như sau trong tệp `.env`:

```bash
LLM_BASE_URL="http://localhost:11434/v1"
LLM_MODEL_ID="llama3"
```

Họ hoàn toàn không cần cấu hình `LLM_API_KEY` hay chỉ định `provider` trong mã. Sau đó, trong mã Python, họ chỉ cần khởi tạo `HelloAgentsLLM` đơn giản:

```python
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

load_dotenv()

# Không cần truyền provider; framework sẽ tự động phát hiện
llm = HelloAgentsLLM()
# Nhật ký bên trong framework sẽ hiển thị provider phát hiện được là 'ollama'

# Cách gọi sau đó hoàn toàn không đổi
messages = [{"role": "user", "content": "Xin chào!"}]
for chunk in llm.think(messages):
    print(chunk, end="")

```

Trong quá trình này, phương thức `_auto_detect_provider` phân tích `"localhost"` và `:11434` trong `LLM_BASE_URL`, suy luận thành công `provider` là `"ollama"`. Tiếp đó, phương thức `_resolve_credentials` đặt tham số mặc định đúng cho Ollama.

So với hiện thực cơ bản ở mục 4.1.3, HelloAgentsLLM hiện có các ưu thế rõ rệt sau:

<div align="center">
  <p>Bảng 7.1 So sánh đặc tính các phiên bản HelloAgentLLM</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/7-figures/table-01.png" alt="" width="90%"/>
</div>

Như Bảng 7.1 cho thấy, sự tiến hóa này thể hiện nguyên tắc quan trọng của thiết kế framework: **bắt đầu từ đơn giản, hoàn thiện dần**. Chúng ta giữ giao diện gọn gàng đồng thời tăng cường tính đầy đủ của chức năng.



## 7.3 Hiện thực giao diện framework

Ở mục trước, chúng ta đã xây dựng thành phần cốt lõi `HelloAgentsLLM`, giải quyết vấn đề then chốt giao tiếp với mô hình ngôn ngữ lớn. Tuy nhiên nó còn cần một loạt giao diện và thành phần phối hợp để xử lý luồng dữ liệu, quản lý cấu hình, ứng phó ngoại lệ, và cung cấp cấu trúc rõ ràng, thống nhất cho việc xây dựng ứng dụng tầng trên. Mục này sẽ trình bày ba tệp cốt lõi sau:

- `message.py`: định nghĩa định dạng tin nhắn thống nhất trong framework, đảm bảo chuẩn hóa việc truyền thông tin giữa Agent và mô hình.
- `config.py`: cung cấp phương án quản lý cấu hình tập trung, giúp hành vi framework dễ điều chỉnh và mở rộng.
- `agent.py`: định nghĩa lớp cơ sở trừu tượng (`Agent`) cho mọi Agent, cung cấp giao diện và quy phạm thống nhất để hiện thực các loại Agent khác nhau sau này.

### 7.3.1 Lớp Message

Trong tương tác giữa Agent và mô hình ngôn ngữ lớn, lịch sử hội thoại là ngữ cảnh cực kỳ quan trọng. Để quản lý chuẩn hóa những thông tin này, chúng ta thiết kế một lớp `Message` đơn giản. Trong chương kỹ thuật ngữ cảnh sau này, nó sẽ được mở rộng.

```python
"""Hệ thống tin nhắn"""
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel

# Định nghĩa kiểu vai trò tin nhắn, giới hạn giá trị
MessageRole = Literal["user", "assistant", "system", "tool"]

class Message(BaseModel):
    """Lớp tin nhắn"""

    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __init__(self, content: str, role: MessageRole, **kwargs):
        super().__init__(
            content=content,
            role=role,
            timestamp=kwargs.get('timestamp', datetime.now()),
            metadata=kwargs.get('metadata', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển sang định dạng từ điển (định dạng OpenAI API)"""
        return {
            "role": self.role,
            "content": self.content
        }

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
```

Thiết kế của lớp này có vài điểm then chốt. Trước tiên, chúng ta dùng `typing.Literal` giới hạn nghiêm ngặt giá trị trường `role` thành bốn loại `"user"`, `"assistant"`, `"system"`, `"tool"`, tương ứng trực tiếp quy phạm OpenAI API, đảm bảo an toàn kiểu. Ngoài hai trường cốt lõi `content` và `role`, chúng ta còn thêm `timestamp` và `metadata`, dành chỗ cho ghi nhật ký và mở rộng chức năng tương lai. Cuối cùng, phương thức `to_dict()` là một trong những chức năng cốt lõi, chịu trách nhiệm chuyển đối tượng `Message` dùng nội bộ thành định dạng từ điển tương thích OpenAI API, thể hiện nguyên tắc thiết kế “phong phú bên trong, tương thích bên ngoài”.

### 7.3.2 Lớp Config

Trách nhiệm của lớp `Config` là tập trung các tham số cấu hình bị mã hóa cứng trong mã, và hỗ trợ đọc từ biến môi trường.

```python
"""Quản lý cấu hình"""
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel

class Config(BaseModel):
    """Lớp cấu hình HelloAgents"""

    # Cấu hình LLM
    default_model: str = "gpt-3.5-turbo"
    default_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # Cấu hình hệ thống
    debug: bool = False
    log_level: str = "INFO"

    # Cấu hình khác
    max_history_length: int = 100

    @classmethod
    def from_env(cls) -> "Config":
        """Tạo cấu hình từ biến môi trường"""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển sang từ điển"""
        return self.dict()
```

Trước tiên, chúng ta chia các mục cấu hình theo logic thành `cấu hình LLM`, `cấu hình hệ thống`, v.v., để cấu trúc rõ ràng trong một cái nhìn. Thứ hai, mỗi mục cấu hình đều có giá trị mặc định hợp lý, đảm bảo framework vẫn hoạt động khi không cấu hình. Cốt lõi nhất là phương thức lớp `from_env()`, cho phép người dùng ghi đè cấu hình mặc định bằng cách đặt biến môi trường mà không cần sửa mã; điều này đặc biệt hữu ích khi triển khai đến các môi trường khác nhau.

### 7.3.3 Lớp cơ sở trừu tượng Agent

Lớp `Agent` là mức trừu tượng cao nhất của toàn bộ framework. Nó định nghĩa hành vi và thuộc tính chung mà một Agent nên có, nhưng không quan tâm cách hiện thực cụ thể. Chúng ta hiện thực nó thông qua mô-đun `abc` (Abstract Base Classes) của Python; điều này buộc mọi hiện thực Agent cụ thể (như `SimpleAgent`, `ReActAgent` ở các chương sau) đều phải tuân theo cùng một “giao diện”.

```python
"""Lớp cơ sở Agent"""
from abc import ABC, abstractmethod
from typing import Optional, Any
from .message import Message
from .llm import HelloAgentsLLM
from .config import Config

class Agent(ABC):
    """Lớp cơ sở Agent"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: list[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """Chạy Agent"""
        pass

    def add_message(self, message: Message):
        """Thêm tin nhắn vào lịch sử"""
        self._history.append(message)

    def clear_history(self):
        """Xóa lịch sử"""
        self._history.clear()

    def get_history(self) -> list[Message]:
        """Lấy lịch sử"""
        return self._history.copy()

    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
```

Thiết kế của lớp này thể hiện nguyên tắc trừu tượng trong lập trình hướng đối tượng. Trước tiên, nó được định nghĩa là lớp trừu tượng không thể khởi tạo trực tiếp thông qua kế thừa `ABC`. Hàm khởi tạo `__init__` định nghĩa rõ các phụ thuộc cốt lõi của Agent: tên, thực thể LLM, system prompt và cấu hình. Phần quan trọng nhất là phương thức `run` được trang trí bằng `@abstractmethod`; nó buộc mọi lớp con phải hiện thực phương thức này, từ đó đảm bảo mọi Agent có cùng điểm vào thực thi. Ngoài ra, lớp cơ sở còn cung cấp các phương thức quản lý lịch sử chung; các phương thức này phối hợp với lớp `Message`, thể hiện mối liên hệ giữa các thành phần.

Đến đây, chúng ta đã hoàn thành thiết kế và hiện thực các thành phần nền tảng cốt lõi của framework `HelloAgents`.

## 7.4 Hiện thực hóa framework cho các mô hình Agent

Nội dung mục này sẽ tái cấu trúc theo hướng framework ba mô hình Agent kinh điển đã xây ở chương 4 (ReAct, Plan-and-Solve, Reflection), đồng thời thêm SimpleAgent làm mô hình hội thoại cơ bản. Chúng ta sẽ biến các hiện thực Agent độc lập này thành thành phần framework dựa trên kiến trúc thống nhất. Lần tái cấu trúc này xoay quanh ba mục tiêu cốt lõi sau:

1. **Nâng cấp hệ thống kỹ thuật prompt**: tối ưu sâu prompt ở chương 4, chuyển từ định hướng nhiệm vụ cụ thể sang thiết kế tổng quát, đồng thời tăng cường ràng buộc định dạng và định nghĩa vai trò.
2. **Chuẩn hóa và thống nhất giao diện, định dạng**: thiết lập lớp cơ sở Agent thống nhất và giao diện chạy chuẩn hóa; mọi Agent tuân theo cùng tham số khởi tạo, chữ ký phương thức và cơ chế quản lý lịch sử.
3. **Năng lực tùy biến cấu hình cao**: hỗ trợ người dùng tùy biến mẫu prompt, tham số cấu hình và chiến lược thực thi.

### 7.4.1 SimpleAgent

SimpleAgent là hiện thực Agent cơ bản nhất, thể hiện cách xây dựng một Agent hội thoại hoàn chỉnh trên nền framework. Chúng ta sẽ kế thừa lớp `SimpleAgent` có sẵn trong framework và ghi đè các phương thức cốt lõi để hiện thực một phiên bản có thể mở rộng. Trước tiên, tạo tệp `my_simple_agent.py` trong thư mục dự án của bạn:

```python
# my_simple_agent.py
from typing import Optional, Iterator
from hello_agents import SimpleAgent, HelloAgentsLLM, Config, Message,ToolRegistry

class MySimpleAgent(SimpleAgent):
    """
    Agent hội thoại đơn giản được ghi đè
    Trình diễn cách xây Agent tùy chỉnh dựa trên lớp cơ sở của framework
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional['ToolRegistry'] = None,
        enable_tool_calling: bool = True
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        print(f"✅ {name} khởi tạo hoàn tất, gọi công cụ: {'bật' if self.enable_tool_calling else 'tắt'}")
```

Tiếp theo, chúng ta cần ghi đè phương thức `run`. SimpleAgent hỗ trợ chức năng gọi công cụ tùy chọn, cũng thuận tiện cho mở rộng ở các chương sau:

```python
# Tiếp tục thêm vào my_simple_agent.py
import re

class MySimpleAgent(SimpleAgent):
    # ... phương thức __init__ phía trên

    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """
        Phương thức chạy được ghi đè - hiện thực logic hội thoại đơn giản, hỗ trợ gọi công cụ tùy chọn
        """
        print(f"🤖 {self.name} đang xử lý: {input_text}")

        # Xây dựng danh sách tin nhắn
        messages = []

        # Thêm tin nhắn hệ thống (có thể chứa thông tin công cụ)
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append({"role": "system", "content": enhanced_system_prompt})

        # Thêm tin nhắn lịch sử
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})

        # Thêm tin nhắn người dùng hiện tại
        messages.append({"role": "user", "content": input_text})

        # Nếu không bật gọi công cụ, dùng logic hội thoại đơn giản
        if not self.enable_tool_calling:
            response = self.llm.invoke(messages, **kwargs)
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(response, "assistant"))
            print(f"✅ {self.name} phản hồi hoàn tất")
            return response

        # Logic hỗ trợ gọi công cụ nhiều vòng
        return self._run_with_tools(messages, input_text, max_tool_iterations, **kwargs)

    def _get_enhanced_system_prompt(self) -> str:
        """Xây dựng system prompt tăng cường, chứa thông tin công cụ"""
        base_prompt = self.system_prompt or "Bạn là một trợ lý AI hữu ích."

        if not self.enable_tool_calling or not self.tool_registry:
            return base_prompt

        # Lấy mô tả công cụ
        tools_description = self.tool_registry.get_tools_description()
        if not tools_description or tools_description == "暂无可用工具":
            return base_prompt

        tools_section = "\n\n## Công cụ khả dụng\n"
        tools_section += "Bạn có thể dùng các công cụ sau để giúp trả lời câu hỏi:\n"
        tools_section += tools_description + "\n"

        tools_section += "\n## Định dạng gọi công cụ\n"
        tools_section += "Khi cần dùng công cụ, hãy dùng định dạng sau:\n"
        tools_section += "`[TOOL_CALL:{tool_name}:{parameters}]`\n"
        tools_section += "Ví dụ: `[TOOL_CALL:search:lập trình Python]` hoặc `[TOOL_CALL:memory:recall=thông tin người dùng]`\n\n"
        tools_section += "Kết quả gọi công cụ sẽ tự động được chèn vào hội thoại, sau đó bạn có thể tiếp tục trả lời dựa trên kết quả.\n"

        return base_prompt + tools_section
```

Bây giờ chúng ta hiện thực logic cốt lõi của gọi công cụ:

```python
# Tiếp tục thêm vào my_simple_agent.py
class MySimpleAgent(SimpleAgent):
    # ... các phương thức phía trên

    def _run_with_tools(self, messages: list, input_text: str, max_tool_iterations: int, **kwargs) -> str:
        """Logic chạy hỗ trợ gọi công cụ"""
        current_iteration = 0
        final_response = ""

        while current_iteration < max_tool_iterations:
            # Gọi LLM
            response = self.llm.invoke(messages, **kwargs)

            # Kiểm tra có lời gọi công cụ hay không
            tool_calls = self._parse_tool_calls(response)

            if tool_calls:
                print(f"🔧 Phát hiện {len(tool_calls)} lời gọi công cụ")
                # Thực thi tất cả lời gọi công cụ và thu thập kết quả
                tool_results = []
                clean_response = response

                for call in tool_calls:
                    result = self._execute_tool_call(call['tool_name'], call['parameters'])
                    tool_results.append(result)
                    # Xóa dấu gọi công cụ khỏi phản hồi
                    clean_response = clean_response.replace(call['original'], "")

                # Xây dựng tin nhắn chứa kết quả công cụ
                messages.append({"role": "assistant", "content": clean_response})

                # Thêm kết quả công cụ
                tool_results_text = "\n\n".join(tool_results)
                messages.append({"role": "user", "content": f"Kết quả thực thi công cụ:\n{tool_results_text}\n\nHãy đưa ra câu trả lời đầy đủ dựa trên các kết quả này."})

                current_iteration += 1
                continue

            # Không có lời gọi công cụ; đây là câu trả lời cuối cùng
            final_response = response
            break

        # Nếu vượt số lần lặp tối đa, lấy câu trả lời cuối
        if current_iteration >= max_tool_iterations and not final_response:
            final_response = self.llm.invoke(messages, **kwargs)

        # Lưu vào lịch sử
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))
        print(f"✅ {self.name} phản hồi hoàn tất")

        return final_response

    def _parse_tool_calls(self, text: str) -> list:
        """Phân tích lời gọi công cụ trong văn bản"""
        pattern = r'\[TOOL_CALL:([^:]+):([^\]]+)\]'
        matches = re.findall(pattern, text)

        tool_calls = []
        for tool_name, parameters in matches:
            tool_calls.append({
                'tool_name': tool_name.strip(),
                'parameters': parameters.strip(),
                'original': f'[TOOL_CALL:{tool_name}:{parameters}]'
            })

        return tool_calls

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """Thực thi lời gọi công cụ"""
        if not self.tool_registry:
            return f"❌ Lỗi: chưa cấu hình bảng đăng ký công cụ"

        try:
            # Phân tích tham số thông minh
            if tool_name == 'calculator':
                # Công cụ tính toán truyền trực tiếp biểu thức
                result = self.tool_registry.execute_tool(tool_name, parameters)
            else:
                # Công cụ khác dùng phân tích tham số thông minh
                param_dict = self._parse_tool_parameters(tool_name, parameters)
                tool = self.tool_registry.get_tool(tool_name)
                if not tool:
                    return f"❌ Lỗi: không tìm thấy công cụ '{tool_name}'"
                result = tool.run(param_dict)

            return f"🔧 Kết quả thực thi công cụ {tool_name}:\n{result}"

        except Exception as e:
            return f"❌ Gọi công cụ thất bại: {str(e)}"

    def _parse_tool_parameters(self, tool_name: str, parameters: str) -> dict:
        """Phân tích tham số công cụ thông minh"""
        param_dict = {}

        if '=' in parameters:
            # Định dạng: key=value hoặc action=search,query=Python
            if ',' in parameters:
                # Nhiều tham số: action=search,query=Python,limit=3
                pairs = parameters.split(',')
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        param_dict[key.strip()] = value.strip()
            else:
                # Một tham số: key=value
                key, value = parameters.split('=', 1)
                param_dict[key.strip()] = value.strip()
        else:
            # Truyền trực tiếp tham số, suy luận thông minh theo loại công cụ
            if tool_name == 'search':
                param_dict = {'query': parameters}
            elif tool_name == 'memory':
                param_dict = {'action': 'search', 'query': parameters}
            else:
                param_dict = {'input': parameters}

        return param_dict
```

Chúng ta còn có thể thêm chức năng phản hồi dạng luồng và các phương thức tiện ích cho Agent tùy chỉnh:

```python
# Tiếp tục thêm vào my_simple_agent.py
class MySimpleAgent(SimpleAgent):
    # ... các phương thức phía trên

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """
        Phương thức chạy dạng luồng tùy chỉnh
        """
        print(f"🌊 {self.name} bắt đầu xử lý dạng luồng: {input_text}")

        messages = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": input_text})

        # Gọi LLM dạng luồng
        full_response = ""
        print("📝 Phản hồi thời gian thực: ", end="")
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full_response += chunk
            yield chunk

        print()  # Xuống dòng

        # Lưu hội thoại đầy đủ vào lịch sử
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(full_response, "assistant"))
        print(f"✅ {self.name} phản hồi dạng luồng hoàn tất")

    def add_tool(self, tool) -> None:
        """Thêm công cụ vào Agent (phương thức tiện ích)"""
        if not self.tool_registry:
            from hello_agents import ToolRegistry
            self.tool_registry = ToolRegistry()
            self.enable_tool_calling = True

        self.tool_registry.register_tool(tool)
        print(f"🔧 Công cụ '{tool.name}' đã được thêm")

    def has_tools(self) -> bool:
        """Kiểm tra có công cụ khả dụng hay không"""
        return self.enable_tool_calling and self.tool_registry is not None

    def remove_tool(self, tool_name: str) -> bool:
        """Xóa công cụ (phương thức tiện ích)"""
        if self.tool_registry:
            self.tool_registry.unregister(tool_name)
            return True
        return False

    def list_tools(self) -> list:
        """Liệt kê tất cả công cụ khả dụng"""
        if self.tool_registry:
            return self.tool_registry.list_tools()
        return []
```

Tạo tệp kiểm thử `test_simple_agent.py`:

```python
# test_simple_agent.py
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, ToolRegistry
from hello_agents.tools import CalculatorTool
from my_simple_agent import MySimpleAgent

# Tải biến môi trường
load_dotenv()

# Tạo thực thể LLM
llm = HelloAgentsLLM()

# Kiểm thử 1: Agent hội thoại cơ bản (không có công cụ)
print("=== Kiểm thử 1: hội thoại cơ bản ===")
basic_agent = MySimpleAgent(
    name="Trợ lý cơ bản",
    llm=llm,
    system_prompt="Bạn là một trợ lý AI thân thiện; hãy trả lời câu hỏi một cách ngắn gọn, rõ ràng."
)

response1 = basic_agent.run("Xin chào, hãy giới thiệu về bạn")
print(f"Phản hồi hội thoại cơ bản: {response1}\n")

# Kiểm thử 2: Agent có công cụ
print("=== Kiểm thử 2: hội thoại tăng cường công cụ ===")
tool_registry = ToolRegistry()
calculator = CalculatorTool()
tool_registry.register_tool(calculator)

enhanced_agent = MySimpleAgent(
    name="Trợ lý tăng cường",
    llm=llm,
    system_prompt="Bạn là một trợ lý thông minh, có thể dùng công cụ để giúp người dùng.",
    tool_registry=tool_registry,
    enable_tool_calling=True
)

response2 = enhanced_agent.run("Hãy giúp tôi tính 15 * 8 + 32")
print(f"Phản hồi tăng cường công cụ: {response2}\n")

# Kiểm thử 3: phản hồi dạng luồng
print("=== Kiểm thử 3: phản hồi dạng luồng ===")
print("Phản hồi dạng luồng: ", end="")
for chunk in basic_agent.stream_run("Hãy giải thích trí tuệ nhân tạo là gì"):
    pass  # Nội dung đã được in thời gian thực trong stream_run

# Kiểm thử 4: thêm công cụ động
print("\n=== Kiểm thử 4: quản lý công cụ động ===")
print(f"Trước khi thêm công cụ: {basic_agent.has_tools()}")
basic_agent.add_tool(calculator)
print(f"Sau khi thêm công cụ: {basic_agent.has_tools()}")
print(f"Công cụ khả dụng: {basic_agent.list_tools()}")

# Xem lịch sử hội thoại
print(f"\nLịch sử hội thoại: {len(basic_agent.get_history())} tin nhắn")
```

Trong mục này, thông qua kế thừa lớp cơ sở `Agent`, chúng ta đã xây dựng thành công một Agent hội thoại cơ bản đầy đủ chức năng và tuân theo quy phạm framework – `MySimpleAgent`. Nó không chỉ hỗ trợ hội thoại cơ bản mà còn có năng lực gọi công cụ tùy chọn, phản hồi dạng luồng và các phương thức quản lý công cụ tiện lợi.

### 7.4.2 ReActAgent

ReActAgent được framework hóa vẫn giữ nguyên logic cốt lõi đồng thời nâng cao tính tổ chức và khả năng bảo trì của mã, chủ yếu thông qua tối ưu prompt và tích hợp với hệ thống công cụ của framework.

(1) Cải tiến mẫu prompt

Giữ yêu cầu định dạng ban đầu, nhấn mạnh “mỗi lần chỉ thực hiện một bước”, tránh hỗn loạn, và làm rõ tình huống sử dụng của hai loại Action.

```python
MY_REACT_PROMPT = """Bạn là một trợ lý AI có năng lực suy luận và hành động. Bạn có thể phân tích vấn đề bằng suy nghĩ, sau đó gọi công cụ phù hợp để lấy thông tin, và cuối cùng đưa ra câu trả lời chính xác.

## Công cụ khả dụng
{tools}

## Quy trình làm việc
Hãy trả lời nghiêm ngặt theo định dạng sau, mỗi lần chỉ thực hiện một bước:

Thought: phân tích vấn đề hiện tại, suy nghĩ cần thông tin gì hoặc thực hiện hành động gì.
Action: chọn một hành động; định dạng bắt buộc phải là một trong các dạng sau:
- `{{tool_name}}[{{tool_input}}]` - gọi công cụ chỉ định
- `Finish[câu trả lời cuối cùng]` - khi bạn có đủ thông tin để đưa ra câu trả lời cuối cùng

## Nhắc nhở quan trọng
1. Mỗi phản hồi bắt buộc phải gồm hai phần Thought và Action
2. Định dạng gọi công cụ bắt buộc tuân thủ nghiêm ngặt: tên_công_cụ[tham_số]
3. Chỉ dùng Finish khi bạn chắc chắn có đủ thông tin trả lời câu hỏi
4. Nếu thông tin công cụ trả về chưa đủ, tiếp tục dùng công cụ khác hoặc tham số khác của cùng công cụ

## Nhiệm vụ hiện tại
**Question:** {question}

## Lịch sử thực thi
{history}

Bây giờ hãy bắt đầu suy luận và hành động:
"""
```

(2) Ghi đè toàn bộ hiện thực ReActAgent

Tạo tệp `my_react_agent.py` để ghi đè ReActAgent:

```python
# my_react_agent.py
import re
from typing import Optional, List, Tuple
from hello_agents import ReActAgent, HelloAgentsLLM, Config, Message, ToolRegistry

class MyReActAgent(ReActAgent):
    """
    ReAct Agent được ghi đè - Agent kết hợp suy luận và hành động
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5,
        custom_prompt: Optional[str] = None
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.current_history: List[str] = []
        self.prompt_template = custom_prompt if custom_prompt else MY_REACT_PROMPT
        print(f"✅ {name} khởi tạo hoàn tất, số bước tối đa: {max_steps}")
```

Ý nghĩa các tham số khởi tạo như sau:

- `name`: tên của Agent.
- `llm`: thực thể `HelloAgentsLLM`, chịu trách nhiệm giao tiếp với mô hình ngôn ngữ lớn.
- `tool_registry`: thực thể `ToolRegistry`, dùng để quản lý và thực thi các công cụ khả dụng của Agent.
- `system_prompt`: system prompt, dùng để đặt vai trò và chuẩn mực hành vi cho Agent.
- `config`: đối tượng cấu hình, dùng để truyền thiết lập cấp framework.
- `max_steps`: số bước thực thi tối đa của vòng lặp ReAct, ngăn vòng lặp vô hạn.
- `custom_prompt`: mẫu prompt tùy chỉnh, dùng để thay thế prompt ReAct mặc định.

ReActAgent được framework hóa chia quy trình thực thi thành các bước rõ ràng:

```python
def run(self, input_text: str, **kwargs) -> str:
    """Chạy ReAct Agent"""
    self.current_history = []
    current_step = 0

    print(f"\n🤖 {self.name} bắt đầu xử lý vấn đề: {input_text}")

    while current_step < self.max_steps:
        current_step += 1
        print(f"\n--- Bước {current_step} ---")

        # 1. Xây dựng prompt
        tools_desc = self.tool_registry.get_tools_description()
        history_str = "\n".join(self.current_history)
        prompt = self.prompt_template.format(
            tools=tools_desc,
            question=input_text,
            history=history_str
        )

        # 2. Gọi LLM
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm.invoke(messages, **kwargs)

        # 3. Phân tích đầu ra
        thought, action = self._parse_output(response_text)

        # 4. Kiểm tra điều kiện hoàn thành
        if action and action.startswith("Finish"):
            final_answer = self._parse_action_input(action)
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(final_answer, "assistant"))
            return final_answer

        # 5. Thực thi lời gọi công cụ
        if action:
            tool_name, tool_input = self._parse_action(action)
            observation = self.tool_registry.execute_tool(tool_name, tool_input)
            self.current_history.append(f"Action: {action}")
            self.current_history.append(f"Observation: {observation}")

    # Đạt số bước tối đa
    final_answer = "Xin lỗi, tôi không thể hoàn thành nhiệm vụ này trong số bước giới hạn."
    self.add_message(Message(input_text, "user"))
    self.add_message(Message(final_answer, "assistant"))
    return final_answer
```

Qua tái cấu trúc trên, chúng ta đã tích hợp thành công mô hình ReAct vào framework. Cải tiến cốt lõi nằm ở việc tận dụng giao diện `ToolRegistry` thống nhất, và thông qua một mẫu prompt có thể cấu hình, định dạng chặt chẽ hơn, nâng cao tính ổn định của vòng lặp suy nghĩ – hành động của Agent. Với ca kiểm thử ReAct, do cần gọi công cụ, mã kiểm thử được cung cấp thống nhất ở cuối bài.

### 7.4.3 ReflectionAgent

Vì các loại Agent này đã hiện thực logic cốt lõi ở chương 4, ở đây chỉ đưa ra prompt tương ứng. Khác với prompt chuyên cho sinh mã ở chương 4, phiên bản framework áp dụng thiết kế tổng quát, khiến nó phù hợp với nhiều tình huống như sinh văn bản, phân tích, sáng tác, và hỗ trợ người dùng tùy biến sâu thông qua tham số `custom_prompts`.

```python
DEFAULT_PROMPTS = {
    "initial": """
Hãy hoàn thành nhiệm vụ theo yêu cầu sau:

Nhiệm vụ: {task}

Hãy cung cấp một câu trả lời đầy đủ, chính xác.
""",
    "reflect": """
Hãy xem xét kỹ câu trả lời dưới đây và tìm ra vấn đề hoặc không gian cải thiện có thể có:

# Nhiệm vụ gốc:
{task}

# Câu trả lời hiện tại:
{content}

Hãy phân tích chất lượng của câu trả lời này, chỉ ra điểm chưa đạt và đề xuất cải thiện cụ thể.
Nếu câu trả lời đã tốt, hãy trả lời "无需改进" (không cần cải thiện).
""",
    "refine": """
Hãy cải thiện câu trả lời của bạn theo ý kiến phản hồi:

# Nhiệm vụ gốc:
{task}

# Câu trả lời vòng trước:
{last_attempt}

# Ý kiến phản hồi:
{feedback}

Hãy cung cấp một câu trả lời đã được cải thiện.
"""
}
```

Bạn có thể thử dựa trên mã chương 4 và hiện thực ReAct ở trên để xây `MyReflectionAgent` của riêng mình. Dưới đây cung cấp mã kiểm thử để kiểm chứng ý tưởng.

```python
# test_reflection_agent.py
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM
from my_reflection_agent import MyReflectionAgent

load_dotenv()
llm = HelloAgentsLLM()

# Dùng prompt tổng quát mặc định
general_agent = MyReflectionAgent(name="Trợ lý phản tư của tôi", llm=llm)

# Dùng prompt sinh mã tùy chỉnh (tương tự chương 4)
code_prompts = {
    "initial": "Bạn là chuyên gia Python, hãy viết hàm: {task}",
    "reflect": "Hãy xem xét hiệu quả thuật toán của mã:\nNhiệm vụ: {task}\nMã: {content}",
    "refine": "Hãy tối ưu mã theo phản hồi:\nNhiệm vụ: {task}\nPhản hồi: {feedback}"
}
code_agent = MyReflectionAgent(
    name="Trợ lý sinh mã của tôi",
    llm=llm,
    custom_prompts=code_prompts
)

# Sử dụng kiểm thử
result = general_agent.run("Viết một bài ngắn về lịch sử phát triển của trí tuệ nhân tạo")
print(f"Kết quả cuối cùng: {result}")
```

### 7.4.4 PlanAndSolveAgent

Khác với đầu ra kế hoạch dạng văn bản tự do ở chương 4, phiên bản framework buộc Planner xuất kế hoạch theo định dạng danh sách Python, và cung cấp cơ chế xử lý ngoại lệ hoàn chỉnh, đảm bảo các bước sau thực thi ổn định. Prompt Plan-and-Solve được framework hóa:

````bash
# Mẫu prompt lập kế hoạch mặc định
DEFAULT_PLANNER_PROMPT = """
Bạn là một chuyên gia lập kế hoạch AI hàng đầu. Nhiệm vụ của bạn là phân rã vấn đề phức tạp do người dùng đưa ra thành một kế hoạch hành động gồm nhiều bước đơn giản.
Hãy đảm bảo mỗi bước trong kế hoạch là một nhiệm vụ con độc lập, có thể thực thi, và được sắp xếp nghiêm ngặt theo thứ tự logic.
Đầu ra của bạn bắt buộc phải là một danh sách Python, trong đó mỗi phần tử là một chuỗi mô tả nhiệm vụ con.

Vấn đề: {question}

Hãy xuất kế hoạch của bạn nghiêm ngặt theo định dạng sau:
```python
["bước 1", "bước 2", "bước 3", ...]
```
"""

# Mẫu prompt thực thi mặc định
DEFAULT_EXECUTOR_PROMPT = """
Bạn là một chuyên gia thực thi AI hàng đầu. Nhiệm vụ của bạn là tuân thủ nghiêm ngặt kế hoạch đã cho, giải quyết vấn đề từng bước một.
Bạn sẽ nhận được vấn đề gốc, kế hoạch đầy đủ, cùng các bước và kết quả đã hoàn thành cho đến nay.
Hãy tập trung giải quyết "bước hiện tại", và chỉ xuất câu trả lời cuối cùng của bước đó, không xuất bất kỳ giải thích hoặc hội thoại bổ sung nào.

# Vấn đề gốc:
{question}

# Kế hoạch đầy đủ:
{plan}

# Các bước và kết quả lịch sử:
{history}

# Bước hiện tại:
{current_step}

Hãy chỉ xuất câu trả lời cho "bước hiện tại":
"""
````

Mục này vẫn cung cấp một tệp kiểm thử tổng hợp `test_plan_solve_agent.py`; bạn có thể tự thiết kế hiện thực.

```python
# test_plan_solve_agent.py
from dotenv import load_dotenv
from hello_agents.core.llm import HelloAgentsLLM
from my_plan_solve_agent import MyPlanAndSolveAgent

# Tải biến môi trường
load_dotenv()

# Tạo thực thể LLM
llm = HelloAgentsLLM()

# Tạo PlanAndSolveAgent tùy chỉnh
agent = MyPlanAndSolveAgent(
    name="Trợ lý lập kế hoạch và thực thi của tôi",
    llm=llm
)

# Kiểm thử vấn đề phức tạp
question = "Một cửa hàng hoa quả bán được 15 quả táo vào thứ Hai. Số táo bán được vào thứ Ba gấp đôi thứ Hai. Số bán được vào thứ Tư ít hơn thứ Ba 5 quả. Hỏi cả ba ngày cửa hàng bán được tổng cộng bao nhiêu quả táo?"

result = agent.run(question)
print(f"\nKết quả cuối cùng: {result}")

# Xem lịch sử hội thoại
print(f"Lịch sử hội thoại: {len(agent.get_history())} tin nhắn")
```

Cuối cùng có thể bổ sung một prompt mới; hãy thử hiện thực `custom_prompt` để nạp prompt tùy chỉnh.

```python
# Tạo prompt tùy chỉnh dành riêng cho bài toán
math_prompts = {
    "planner": """
Bạn là chuyên gia lập kế hoạch bài toán. Hãy phân rã bài toán thành các bước tính toán:

Vấn đề: {question}

Định dạng đầu ra:
python
["bước tính 1", "bước tính 2", "tính tổng"]

""",
    "executor": """
Bạn là chuyên gia tính toán. Hãy tính bước hiện tại:

Vấn đề: {question}
Kế hoạch: {plan}
Lịch sử: {history}
Bước hiện tại: {current_step}

Hãy chỉ xuất kết quả số:
"""
}

# Dùng prompt tùy chỉnh tạo Agent chuyên toán
math_agent = MyPlanAndSolveAgent(
    name="Trợ lý tính toán",
    llm=llm,
    custom_prompts=math_prompts
)

# Kiểm thử bài toán
math_result = math_agent.run(question)
print(f"Kết quả Agent chuyên toán: {math_result}")
```

Như Bảng 7.2, qua tái cấu trúc theo hướng framework này, chúng ta không chỉ giữ chức năng cốt lõi của các mô hình Agent ở chương 4 mà còn nâng cao đáng kể tính tổ chức, khả năng bảo trì và mở rộng của mã. Mọi Agent hiện chia sẻ hạ tầng cơ sở thống nhất, đồng thời giữ đặc sắc và ưu thế riêng.

<div align="center">
  <p>Bảng 7.2 So sánh hiện thực Agent ở các chương khác nhau</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/7-figures/table-02.png" alt="" width="90%"/>
</div>

### 7.4.5 FunctionCallAgent

FunctionCallAgent là Agent được hello-agents giới thiệu sau phiên bản 0.2.8; nó dựa trên cơ chế gọi hàm native của OpenAI, trình diễn cách dùng cơ chế gọi hàm của OpenAI để xây Agent.
Nó hỗ trợ các chức năng sau:

- _build_tool_schemas: xây dựng schema function calling của OpenAI thông qua description của công cụ
- _extract_message_content: trích xuất văn bản từ phản hồi của OpenAI
- _parse_function_call_arguments: phân tích tham số chuỗi JSON do mô hình trả về
- _convert_parameter_types: chuyển đổi kiểu tham số

Những chức năng này giúp nó có năng lực OpenAI Function Calling native; so với cách ràng buộc bằng prompt, nó có độ vững chắc cao hơn.
```python
def _invoke_with_tools(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], tool_choice: Union[str, dict], **kwargs):
        """Gọi client OpenAI tầng dưới để thực hiện function calling"""
        client = getattr(self.llm, "_client", None)
        if client is None:
            raise RuntimeError("HelloAgentsLLM chưa khởi tạo client đúng cách, không thể thực hiện function calling.")

        client_kwargs = dict(kwargs)
        client_kwargs.setdefault("temperature", self.llm.temperature)
        if self.llm.max_tokens is not None:
            client_kwargs.setdefault("max_tokens", self.llm.max_tokens)

        return client.chat.completions.create(
            model=self.llm.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            **client_kwargs,
        )

# Logic bên trong là đóng gói lại function call native của OpenAI
# Ví dụ function call native của OpenAI
from openai import OpenAI
client = OpenAI()

tools = [
  {
    "type": "function",
    "function": {
      "name": "get_current_weather",
      "description": "Get the current weather in a given location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "The city and state, e.g. San Francisco, CA",
          },
          "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["location"],
      },
    }
  }
]
messages = [{"role": "user", "content": "What's the weather like in Boston today?"}]
completion = client.chat.completions.create(
  model="gpt-5",
  messages=messages,
  tools=tools,
  tool_choice="auto"
)

print(completion)
```

## 7.5 Hệ thống công cụ

Nội dung mục này sẽ đi sâu vào thiết kế và hiện thực hệ thống công cụ trên nền hạ tầng Agent đã xây. Chúng ta sẽ bắt đầu từ xây dựng hạ tầng, tiến dần đến thiết kế phát triển tùy chỉnh. Mục tiêu học tập của mục này xoay quanh ba khía cạnh cốt lõi:

1. **Trừu tượng và quản lý công cụ thống nhất**: thiết lập lớp cơ sở Tool chuẩn hóa và cơ chế đăng ký ToolRegistry, cung cấp hạ tầng thống nhất cho phát triển, đăng ký, khám phá và thực thi công cụ.

2. **Phát triển công cụ do thực chiến dẫn dắt**: lấy công cụ tính toán làm ca, trình diễn cách thiết kế và hiện thực công cụ tùy chỉnh, giúp người đọc nắm quy trình đầy đủ của phát triển công cụ.

3. **Chiến lược tích hợp và tối ưu nâng cao**: thông qua thiết kế công cụ tìm kiếm đa nguồn, trình diễn cách tích hợp nhiều dịch vụ bên ngoài, hiện thực lựa chọn backend thông minh, hợp nhất kết quả và xử lý chịu lỗi, thể hiện tư duy thiết kế của hệ thống công cụ trong tình huống phức tạp.

### 7.5.1 Thiết kế lớp cơ sở và cơ chế đăng ký công cụ

Khi xây hệ thống công cụ có thể mở rộng, trước tiên cần thiết lập một bộ hạ tầng chuẩn hóa. Hạ tầng này gồm lớp cơ sở Tool, bảng đăng ký ToolRegistry và cơ chế quản lý công cụ.

(1) Thiết kế trừu tượng của lớp cơ sở Tool

Lớp cơ sở Tool là mức trừu tượng cốt lõi của toàn bộ hệ thống công cụ; nó định nghĩa quy phạm giao diện mà mọi công cụ phải tuân theo:

````python
class Tool(ABC):
    """Lớp cơ sở công cụ"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """Thực thi công cụ"""
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """Lấy định nghĩa tham số công cụ"""
        pass
````
Thiết kế này thể hiện tư tưởng cốt lõi của thiết kế hướng đối tượng: thông qua giao diện phương thức `run` thống nhất, mọi công cụ đều có thể thực thi theo cùng một cách, nhận tham số từ điển và trả về kết quả chuỗi, đảm bảo tính nhất quán của framework. Đồng thời, công cụ có năng lực tự mô tả; thông qua phương thức `get_parameters`, nó có thể nói rõ cho bên gọi biết mình cần tham số gì. Cơ chế nội quan này đặt nền tảng cho sinh tài liệu tự động và xác minh tham số. Thiết kế siêu dữ liệu như name và description khiến hệ thống công cụ có khả năng khám phá và dễ hiểu tốt.

(2) Hệ thống định nghĩa tham số ToolParameter

Để hỗ trợ xác minh tham số phức tạp và sinh tài liệu, chúng ta thiết kế lớp ToolParameter:

````python
class ToolParameter(BaseModel):
    """Định nghĩa tham số công cụ"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
````
Thiết kế này cho phép công cụ mô tả chính xác nhu cầu tham số của mình, hỗ trợ kiểm tra kiểu, đặt giá trị mặc định và sinh tài liệu tự động.

(3) Hiện thực bảng đăng ký ToolRegistry

ToolRegistry là trung tâm quản lý của hệ thống công cụ; nó cung cấp các chức năng cốt lõi như đăng ký, khám phá, thực thi công cụ. Trong mục này chúng ta chủ yếu dùng các chức năng sau:

````python
class ToolRegistry:
    """Bảng đăng ký công cụ HelloAgents"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._functions: dict[str, dict[str, Any]] = {}

    def register_tool(self, tool: Tool):
        """Đăng ký đối tượng Tool"""
        if tool.name in self._tools:
            print(f"⚠️ Cảnh báo: công cụ '{tool.name}' đã tồn tại và sẽ bị ghi đè.")
        self._tools[tool.name] = tool
        print(f"✅ Công cụ '{tool.name}' đã được đăng ký.")

    def register_function(self, name: str, description: str, func: Callable[[str], str]):
        """
        Đăng ký trực tiếp hàm làm công cụ (cách đơn giản)

        Args:
            name: tên công cụ
            description: mô tả công cụ
            func: hàm công cụ, nhận tham số chuỗi, trả về kết quả chuỗi
        """
        if name in self._functions:
            print(f"⚠️ Cảnh báo: công cụ '{name}' đã tồn tại và sẽ bị ghi đè.")

        self._functions[name] = {
            "description": description,
            "func": func
        }
        print(f"✅ Công cụ '{name}' đã được đăng ký.")
````
ToolRegistry hỗ trợ hai cách đăng ký:

1. **Đăng ký đối tượng Tool**: phù hợp với công cụ phức tạp, hỗ trợ định nghĩa và xác minh tham số đầy đủ
2. **Đăng ký trực tiếp hàm**: phù hợp với công cụ đơn giản, nhanh chóng tích hợp hàm hiện có

(4) Cơ chế khám phá và quản lý công cụ

Bảng đăng ký cung cấp chức năng quản lý công cụ phong phú:

````python
def get_tools_description(self) -> str:
    """Lấy chuỗi mô tả đã định dạng của tất cả công cụ khả dụng"""
    descriptions = []

    # Mô tả đối tượng Tool
    for tool in self._tools.values():
        descriptions.append(f"- {tool.name}: {tool.description}")

    # Mô tả công cụ dạng hàm
    for name, info in self._functions.items():
        descriptions.append(f"- {name}: {info['description']}")

    return "\n".join(descriptions) if descriptions else "Chưa có công cụ khả dụng"
````
Chuỗi mô tả do phương thức này sinh có thể dùng trực tiếp để xây prompt cho Agent, giúp Agent hiểu các công cụ khả dụng.

````python
def to_openai_schema(self) -> Dict[str, Any]:
        """Chuyển sang định dạng schema function calling của OpenAI

        Dùng cho FunctionCallAgent, để công cụ có thể được function calling native của OpenAI sử dụng

        Returns:
            Schema đáp ứng chuẩn function calling của OpenAI
        """
        parameters = self.get_parameters()

        # Xây dựng properties
        properties = {}
        required = []

        for param in parameters:
            # Định nghĩa thuộc tính cơ bản
            prop = {
                "type": param.type,
                "description": param.description
            }

            # Nếu có giá trị mặc định, thêm vào mô tả (schema OpenAI không hỗ trợ trường default)
            if param.default is not None:
                prop["description"] = f"{param.description} (mặc định: {param.default})"

            # Nếu là kiểu mảng, thêm định nghĩa items
            if param.type == "array":
                prop["items"] = {"type": "string"}  # Mảng chuỗi mặc định

            properties[param.name] = prop

            # Thu thập tham số bắt buộc
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
````
Schema do phương thức này sinh có thể dùng trực tiếp cho gọi công cụ của OpenAI SDK native.

### 7.5.2 Phát triển công cụ tùy chỉnh

Có hạ tầng rồi, chúng ta xem cách phát triển một công cụ tùy chỉnh hoàn chỉnh. Công cụ tính toán là ví dụ tốt vì đơn giản trực quan; cách trực tiếp nhất là dùng chức năng đăng ký hàm của ToolRegistry.

Hãy tạo một công cụ tính toán tùy chỉnh. Trước tiên, tạo tệp `my_calculator_tool.py` trong thư mục dự án:

```python
# my_calculator_tool.py
import ast
import operator
import math
from hello_agents import ToolRegistry

def my_calculate(expression: str) -> str:
    """Hàm tính toán đơn giản"""
    if not expression.strip():
        return "Biểu thức tính toán không được để trống"

    # Các phép toán cơ bản được hỗ trợ
    operators = {
        ast.Add: operator.add,      # +
        ast.Sub: operator.sub,      # -
        ast.Mult: operator.mul,     # *
        ast.Div: operator.truediv,  # /
    }

    # Các hàm cơ bản được hỗ trợ
    functions = {
        'sqrt': math.sqrt,
        'pi': math.pi,
    }

    try:
        node = ast.parse(expression, mode='eval')
        result = _eval_node(node.body, operators, functions)
        return str(result)
    except:
        return "Tính toán thất bại, hãy kiểm tra định dạng biểu thức"

def _eval_node(node, operators, functions):
    """Tính giá trị biểu thức đơn giản hóa"""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left, operators, functions)
        right = _eval_node(node.right, operators, functions)
        op = operators.get(type(node.op))
        return op(left, right)
    elif isinstance(node, ast.Call):
        func_name = node.func.id
        if func_name in functions:
            args = [_eval_node(arg, operators, functions) for arg in node.args]
            return functions[func_name](*args)
    elif isinstance(node, ast.Name):
        if node.id in functions:
            return functions[node.id]

def create_calculator_registry():
    """Tạo bảng đăng ký công cụ chứa máy tính"""
    registry = ToolRegistry()

    # Đăng ký hàm máy tính
    registry.register_function(
        name="my_calculator",
        description="Công cụ tính toán đơn giản, hỗ trợ phép toán cơ bản (+,-,*,/) và hàm sqrt",
        func=my_calculate
    )

    return registry
```

Công cụ không chỉ hỗ trợ bốn phép tính cơ bản mà còn bao gồm các hàm toán học và hằng số thường dùng, đáp ứng nhu cầu của hầu hết tình huống tính toán. Bạn cũng có thể tự mở rộng tệp này để tạo một hàm tính toán đầy đủ hơn. Chúng ta cung cấp tệp kiểm thử `test_my_calculator.py` giúp bạn xác minh hiện thực chức năng:

```python
# test_my_calculator.py
from dotenv import load_dotenv
from my_calculator_tool import create_calculator_registry

# Tải biến môi trường
load_dotenv()

def test_calculator_tool():
    """Kiểm thử công cụ tính toán tùy chỉnh"""

    # Tạo bảng đăng ký chứa máy tính
    registry = create_calculator_registry()

    print("🧪 Kiểm thử công cụ tính toán tùy chỉnh\n")

    # Ca kiểm thử đơn giản
    test_cases = [
        "2 + 3",           # Phép cộng cơ bản
        "10 - 4",          # Phép trừ cơ bản
        "5 * 6",           # Phép nhân cơ bản
        "15 / 3",          # Phép chia cơ bản
        "sqrt(16)",        # Căn bậc hai
    ]

    for i, expression in enumerate(test_cases, 1):
        print(f"Kiểm thử {i}: {expression}")
        result = registry.execute_tool("my_calculator", expression)
        print(f"Kết quả: {result}\n")

def test_with_simple_agent():
    """Kiểm thử tích hợp với SimpleAgent"""
    from hello_agents import HelloAgentsLLM

    # Tạo client LLM
    llm = HelloAgentsLLM()

    # Tạo bảng đăng ký chứa máy tính
    registry = create_calculator_registry()

    print("🤖 Kiểm thử tích hợp với SimpleAgent:")

    # Mô phỏng cảnh SimpleAgent sử dụng công cụ
    user_question = "Hãy giúp tôi tính sqrt(16) + 2 * 3"

    print(f"Câu hỏi người dùng: {user_question}")

    # Dùng công cụ tính toán
    calc_result = registry.execute_tool("my_calculator", "sqrt(16) + 2 * 3")
    print(f"Kết quả tính toán: {calc_result}")

    # Xây dựng câu trả lời cuối cùng
    final_messages = [
        {"role": "user", "content": f"Kết quả tính toán là {calc_result}; hãy trả lời câu hỏi của người dùng bằng ngôn ngữ tự nhiên: {user_question}"}
    ]

    print("\n🎯 Câu trả lời của SimpleAgent:")
    response = llm.think(final_messages)
    for chunk in response:
        print(chunk, end="", flush=True)
    print("\n")

if __name__ == "__main__":
    test_calculator_tool()
    test_with_simple_agent()
```

Qua ca công cụ tính toán đơn giản này, chúng ta đã học cách nhanh chóng phát triển công cụ tùy chỉnh: viết một hàm tính toán đơn giản, đăng ký qua ToolRegistry, rồi tích hợp với SimpleAgent. Để quan sát trực quan hơn, Hình 7.1 được cung cấp để hiểu rõ logic chạy của mã.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/7-figures/01.png" alt="" width="90%"/>
  <p>Hình 7.1 Quy trình làm việc của SimpleAgent dựa trên Helloagents</p>
</div>

### 7.5.3 Công cụ tìm kiếm đa nguồn

Trong ứng dụng thực tế, chúng ta thường cần tích hợp nhiều dịch vụ bên ngoài để cung cấp chức năng mạnh mẽ hơn. Công cụ tìm kiếm là ví dụ điển hình; nó tích hợp nhiều công cụ tìm kiếm, có thể cung cấp thông tin thật đầy đủ hơn. Ở chương 1 chúng ta đã dùng API tìm kiếm Tavily, ở chương 4 đã dùng API tìm kiếm SerpApi. Vì vậy lần này chúng ta dùng hai API này để hiện thực chức năng tìm kiếm đa nguồn. Nếu chưa cài phụ thuộc Python tương ứng, có thể chạy script sau:

```bash
pip install "hello-agents[search]==0.1.1"
```

(1) Thiết kế giao diện thống nhất cho công cụ tìm kiếm

SearchTool tích hợp trong framework HelloAgents trình diễn cách thiết kế một công cụ tìm kiếm đa nguồn nâng cao:

````python
class SearchTool(Tool):
    """
    Công cụ tìm kiếm hỗn hợp thông minh

    Hỗ trợ nhiều backend công cụ tìm kiếm, tự động chọn nguồn tìm kiếm tốt nhất:
    1. Chế độ hỗn hợp (hybrid) - tự động chọn TAVILY hoặc SERPAPI
    2. Tavily API (tavily) - tìm kiếm AI chuyên nghiệp
    3. SerpApi (serpapi) - tìm kiếm Google truyền thống
    """

    def __init__(self, backend: str = "hybrid", tavily_key: Optional[str] = None, serpapi_key: Optional[str] = None):
        super().__init__(
            name="search",
            description="Một công cụ tìm kiếm web thông minh. Hỗ trợ chế độ tìm kiếm hỗn hợp, tự động chọn nguồn tìm kiếm tốt nhất."
        )
        self.backend = backend
        self.tavily_key = tavily_key or os.getenv("TAVILY_API_KEY")
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_API_KEY")
        self.available_backends = []
        self._setup_backends()
````
Tư tưởng cốt lõi của thiết kế là tự động chọn backend tìm kiếm tốt nhất dựa trên API key và thư viện phụ thuộc khả dụng.

(2) Chiến lược tích hợp nguồn tìm kiếm TAVILY và SERPAPI

Framework hiện thực logic chọn backend thông minh:

````python
def _search_hybrid(self, query: str) -> str:
    """Tìm kiếm hỗn hợp - tự động chọn nguồn tìm kiếm tốt nhất"""
    # Ưu tiên dùng Tavily (tìm kiếm tối ưu cho AI)
    if "tavily" in self.available_backends:
        try:
            return self._search_tavily(query)
        except Exception as e:
            print(f"⚠️ Tìm kiếm Tavily thất bại: {e}")
            # Nếu Tavily thất bại, thử SerpApi
            if "serpapi" in self.available_backends:
                print("🔄 Chuyển sang tìm kiếm SerpApi")
                return self._search_serpapi(query)

    # Nếu Tavily không khả dụng, dùng SerpApi
    elif "serpapi" in self.available_backends:
        try:
            return self._search_serpapi(query)
        except Exception as e:
            print(f"⚠️ Tìm kiếm SerpApi thất bại: {e}")

    # Nếu cả hai đều không khả dụng, nhắc người dùng cấu hình API
    return "❌ Không có nguồn tìm kiếm khả dụng; hãy cấu hình biến môi trường TAVILY_API_KEY hoặc SERPAPI_API_KEY"
````
Thiết kế này thể hiện tư tưởng cốt lõi của hệ thống có tính khả dụng cao: thông qua cơ chế giảm cấp, hệ thống có thể từ nguồn tìm kiếm tối ưu giảm dần sang phương án dự phòng khả dụng. Khi mọi nguồn tìm kiếm đều không khả dụng, hệ thống thông báo rõ cho người dùng cấu hình API key đúng.

(3) Định dạng thống nhất kết quả tìm kiếm

Kết quả do các công cụ tìm kiếm khác nhau trả về có định dạng khác nhau; framework xử lý bằng phương thức định dạng thống nhất:

````python
def _search_tavily(self, query: str) -> str:
    """Dùng Tavily tìm kiếm"""
    response = self.tavily_client.search(
        query=query,
        search_depth="basic",
        include_answer=True,
        max_results=3
    )

    result = f"🎯 Kết quả tìm kiếm AI Tavily: {response.get('answer', 'không tìm thấy câu trả lời trực tiếp')}\n\n"

    for i, item in enumerate(response.get('results', [])[:3], 1):
        result += f"[{i}] {item.get('title', '')}\n"
        result += f"    {item.get('content', '')[:200]}...\n"
        result += f"    Nguồn: {item.get('url', '')}\n\n"

    return result
````

Dựa trên tư tưởng thiết kế của framework, chúng ta có thể tạo công cụ tìm kiếm nâng cao của riêng mình. Lần này chúng ta dùng cách lớp để trình diễn phương pháp hiện thực khác, tạo `my_advanced_search.py`:

```python
# my_advanced_search.py
import os
from typing import Optional, List, Dict, Any
from hello_agents import ToolRegistry

class MyAdvancedSearchTool:
    """
    Lớp công cụ tìm kiếm nâng cao tùy chỉnh
    Trình diễn mẫu thiết kế tích hợp đa nguồn và lựa chọn thông minh
    """

    def __init__(self):
        self.name = "my_advanced_search"
        self.description = "Công cụ tìm kiếm thông minh, hỗ trợ nhiều nguồn tìm kiếm, tự động chọn kết quả tốt nhất"
        self.search_sources = []
        self._setup_search_sources()

    def _setup_search_sources(self):
        """Thiết lập các nguồn tìm kiếm khả dụng"""
        # Kiểm tra tính khả dụng của Tavily
        if os.getenv("TAVILY_API_KEY"):
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
                self.search_sources.append("tavily")
                print("✅ Nguồn tìm kiếm Tavily đã bật")
            except ImportError:
                print("⚠️ Thư viện Tavily chưa được cài")

        # Kiểm tra tính khả dụng của SerpApi
        if os.getenv("SERPAPI_API_KEY"):
            try:
                import serpapi
                self.search_sources.append("serpapi")
                print("✅ Nguồn tìm kiếm SerpApi đã bật")
            except ImportError:
                print("⚠️ Thư viện SerpApi chưa được cài")

        if self.search_sources:
            print(f"🔧 Nguồn tìm kiếm khả dụng: {', '.join(self.search_sources)}")
        else:
            print("⚠️ Không có nguồn tìm kiếm khả dụng; hãy cấu hình API key")

    def search(self, query: str) -> str:
        """Thực hiện tìm kiếm thông minh"""
        if not query.strip():
            return "❌ Lỗi: truy vấn tìm kiếm không được để trống"

        # Kiểm tra có nguồn tìm kiếm khả dụng hay không
        if not self.search_sources:
            return """❌ Không có nguồn tìm kiếm khả dụng; hãy cấu hình một trong các API key sau:

1. Tavily API: đặt biến môi trường TAVILY_API_KEY
   Địa chỉ lấy: https://tavily.com/

2. SerpAPI: đặt biến môi trường SERPAPI_API_KEY
   Địa chỉ lấy: https://serpapi.com/

Sau khi cấu hình, chạy lại chương trình."""

        print(f"🔍 Bắt đầu tìm kiếm thông minh: {query}")

        # Thử nhiều nguồn tìm kiếm, trả về kết quả tốt nhất
        for source in self.search_sources:
            try:
                if source == "tavily":
                    result = self._search_with_tavily(query)
                    if result and "không tìm thấy" not in result:
                        return f"📊 Kết quả tìm kiếm AI Tavily:\n\n{result}"

                elif source == "serpapi":
                    result = self._search_with_serpapi(query)
                    if result and "không tìm thấy" not in result:
                        return f"🌐 Kết quả tìm kiếm Google SerpApi:\n\n{result}"

            except Exception as e:
                print(f"⚠️ {source} tìm kiếm thất bại: {e}")
                continue

        return "❌ Tất cả nguồn tìm kiếm đều thất bại; hãy kiểm tra kết nối mạng và cấu hình API key"

    def _search_with_tavily(self, query: str) -> str:
        """Dùng Tavily tìm kiếm"""
        response = self.tavily_client.search(query=query, max_results=3)

        if response.get('answer'):
            result = f"💡 Câu trả lời trực tiếp từ AI: {response['answer']}\n\n"
        else:
            result = ""

        result += "🔗 Kết quả liên quan:\n"
        for i, item in enumerate(response.get('results', [])[:3], 1):
            result += f"[{i}] {item.get('title', '')}\n"
            result += f"    {item.get('content', '')[:150]}...\n\n"

        return result

    def _search_with_serpapi(self, query: str) -> str:
        """Dùng SerpApi tìm kiếm"""
        import serpapi

        search = serpapi.GoogleSearch({
            "q": query,
            "api_key": os.getenv("SERPAPI_API_KEY"),
            "num": 3
        })

        results = search.get_dict()

        result = "🔗 Kết quả tìm kiếm Google:\n"
        if "organic_results" in results:
            for i, res in enumerate(results["organic_results"][:3], 1):
                result += f"[{i}] {res.get('title', '')}\n"
                result += f"    {res.get('snippet', '')}\n\n"

        return result

def create_advanced_search_registry():
    """Tạo bảng đăng ký chứa công cụ tìm kiếm nâng cao"""
    registry = ToolRegistry()

    # Tạo thực thể công cụ tìm kiếm
    search_tool = MyAdvancedSearchTool()

    # Đăng ký phương thức của công cụ tìm kiếm làm hàm
    registry.register_function(
        name="advanced_search",
        description="Công cụ tìm kiếm nâng cao, tích hợp nhiều nguồn Tavily và SerpAPI, cung cấp kết quả tìm kiếm toàn diện hơn",
        func=search_tool.search
    )

    return registry
```

Tiếp theo có thể kiểm thử công cụ chúng ta tự viết, tạo `test_advanced_search.py`:

```python
# test_advanced_search.py
from dotenv import load_dotenv
from my_advanced_search import create_advanced_search_registry, MyAdvancedSearchTool

# Tải biến môi trường
load_dotenv()

def test_advanced_search():
    """Kiểm thử công cụ tìm kiếm nâng cao"""

    # Tạo bảng đăng ký chứa công cụ tìm kiếm nâng cao
    registry = create_advanced_search_registry()

    print("🔍 Kiểm thử công cụ tìm kiếm nâng cao\n")

    # Truy vấn kiểm thử
    test_queries = [
        "Lịch sử ngôn ngữ lập trình Python",
        "Phát triển mới nhất của trí tuệ nhân tạo",
        "Xu hướng công nghệ năm 2024"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"Kiểm thử {i}: {query}")
        result = registry.execute_tool("advanced_search", query)
        print(f"Kết quả: {result}\n")
        print("-" * 60 + "\n")

def test_api_configuration():
    """Kiểm thử kiểm tra cấu hình API"""
    print("🔧 Kiểm thử kiểm tra cấu hình API:")

    # Tạo trực tiếp thực thể công cụ tìm kiếm
    search_tool = MyAdvancedSearchTool()

    # Nếu chưa cấu hình API, sẽ hiển thị gợi ý cấu hình
    result = search_tool.search("thuật toán học máy")
    print(f"Kết quả tìm kiếm: {result}")

def test_with_agent():
    """Kiểm thử tích hợp với Agent"""
    print("\n🤖 Kiểm thử tích hợp với Agent:")
    print("Công cụ tìm kiếm nâng cao đã sẵn sàng để tích hợp với Agent")

    # Hiển thị mô tả công cụ
    registry = create_advanced_search_registry()
    tools_desc = registry.get_tools_description()
    print(f"Mô tả công cụ:\n{tools_desc}")

if __name__ == "__main__":
    test_advanced_search()
    test_api_configuration()
    test_with_agent()
```

Qua thực hành thiết kế công cụ tìm kiếm nâng cao này, chúng ta đã học cách dùng cách lớp để xây hệ thống công cụ phức tạp. So với cách hàm, cách lớp phù hợp hơn với công cụ cần duy trì trạng thái (như client API, thông tin cấu hình).

### 7.5.4 Đặc tính nâng cao của hệ thống công cụ

Sau khi nắm phát triển công cụ cơ bản và tích hợp đa nguồn, chúng ta tìm hiểu các đặc tính nâng cao của hệ thống công cụ. Những đặc tính này giúp hệ thống công cụ chạy ổn định trong môi trường sản xuất phức tạp và cung cấp năng lực mạnh mẽ hơn cho Agent.

(1) Cơ chế gọi chuỗi công cụ

Trong ứng dụng thực tế, Agent thường cần kết hợp nhiều công cụ để hoàn thành nhiệm vụ phức tạp. Chúng ta có thể thiết kế một bộ quản lý chuỗi công cụ để hỗ trợ tình huống này; ở đây tham khảo khái niệm đồ thị đã nhắc ở chương 6:

```python
# tool_chain_manager.py
from typing import List, Dict, Any, Optional
from hello_agents import ToolRegistry

class ToolChain:
    """Chuỗi công cụ - hỗ trợ thực thi tuần tự nhiều công cụ"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []

    def add_step(self, tool_name: str, input_template: str, output_key: str = None):
        """
        Thêm bước thực thi công cụ

        Args:
            tool_name: tên công cụ
            input_template: mẫu đầu vào, hỗ trợ thay thế biến
            output_key: tên khóa của kết quả đầu ra, dùng để tham chiếu ở bước sau
        """
        self.steps.append({
            "tool_name": tool_name,
            "input_template": input_template,
            "output_key": output_key or f"step_{len(self.steps)}_result"
        })

    def execute(self, registry: ToolRegistry, initial_input: str, context: Dict[str, Any] = None) -> str:
        """Thực thi chuỗi công cụ"""
        context = context or {}
        context["input"] = initial_input

        print(f"🔗 Bắt đầu thực thi chuỗi công cụ: {self.name}")

        for i, step in enumerate(self.steps, 1):
            tool_name = step["tool_name"]
            input_template = step["input_template"]
            output_key = step["output_key"]

            # Thay thế biến trong mẫu
            try:
                tool_input = input_template.format(**context)
            except KeyError as e:
                return f"❌ Thực thi chuỗi công cụ thất bại: không tìm thấy biến mẫu {e}"

            print(f"  Bước {i}: dùng {tool_name} xử lý '{tool_input[:50]}...'")

            # Thực thi công cụ
            result = registry.execute_tool(tool_name, tool_input)
            context[output_key] = result

            print(f"  ✅ Bước {i} hoàn tất, độ dài kết quả: {len(result)} ký tự")

        # Trả về kết quả của bước cuối
        final_result = context[self.steps[-1]["output_key"]]
        print(f"🎉 Chuỗi công cụ '{self.name}' thực thi hoàn tất")
        return final_result

class ToolChainManager:
    """Bộ quản lý chuỗi công cụ"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.chains: Dict[str, ToolChain] = {}

    def register_chain(self, chain: ToolChain):
        """Đăng ký chuỗi công cụ"""
        self.chains[chain.name] = chain
        print(f"✅ Chuỗi công cụ '{chain.name}' đã được đăng ký")

    def execute_chain(self, chain_name: str, input_data: str, context: Dict[str, Any] = None) -> str:
        """Thực thi chuỗi công cụ chỉ định"""
        if chain_name not in self.chains:
            return f"❌ Chuỗi công cụ '{chain_name}' không tồn tại"

        chain = self.chains[chain_name]
        return chain.execute(self.registry, input_data, context)

    def list_chains(self) -> List[str]:
        """Liệt kê tất cả chuỗi công cụ"""
        return list(self.chains.keys())

# Ví dụ sử dụng
def create_research_chain() -> ToolChain:
    """Tạo chuỗi công cụ nghiên cứu: tìm kiếm -> tính toán -> tổng kết"""
    chain = ToolChain(
        name="research_and_calculate",
        description="Tìm kiếm thông tin và thực hiện tính toán liên quan"
    )

    # Bước 1: tìm kiếm thông tin
    chain.add_step(
        tool_name="search",
        input_template="{input}",
        output_key="search_result"
    )

    # Bước 2: tính toán dựa trên kết quả tìm kiếm (nếu cần)
    chain.add_step(
        tool_name="my_calculator",
        input_template="Tính các giá trị liên quan dựa trên thông tin sau: {search_result}",
        output_key="calculation_result"
    )

    return chain
```

(2) Hỗ trợ thực thi công cụ bất đồng bộ

Với thao tác công cụ tốn thời gian, chúng ta có thể cung cấp hỗ trợ thực thi bất đồng bộ:

```python
# async_tool_executor.py
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Callable
from hello_agents import ToolRegistry

class AsyncToolExecutor:
    """Bộ thực thi công cụ bất đồng bộ"""

    def __init__(self, registry: ToolRegistry, max_workers: int = 4):
        self.registry = registry
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    async def execute_tool_async(self, tool_name: str, input_data: str) -> str:
        """Thực thi bất đồng bộ một công cụ"""
        loop = asyncio.get_event_loop()

        def _execute():
            return self.registry.execute_tool(tool_name, input_data)

        result = await loop.run_in_executor(self.executor, _execute)
        return result

    async def execute_tools_parallel(self, tasks: List[Dict[str, str]]) -> List[str]:
        """Thực thi song song nhiều công cụ"""
        print(f"🚀 Bắt đầu thực thi song song {len(tasks)} nhiệm vụ công cụ")

        # Tạo nhiệm vụ bất đồng bộ
        async_tasks = []
        for task in tasks:
            tool_name = task["tool_name"]
            input_data = task["input_data"]
            async_task = self.execute_tool_async(tool_name, input_data)
            async_tasks.append(async_task)

        # Chờ tất cả nhiệm vụ hoàn thành
        results = await asyncio.gather(*async_tasks)

        print(f"✅ Tất cả nhiệm vụ công cụ đã thực thi xong")
        return results

    def __del__(self):
        """Dọn dẹp tài nguyên"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

# Ví dụ sử dụng
async def test_parallel_execution():
    """Kiểm thử thực thi công cụ song song"""
    from hello_agents import ToolRegistry

    registry = ToolRegistry()
    # Giả sử đã đăng ký công cụ tìm kiếm và tính toán

    executor = AsyncToolExecutor(registry)

    # Định nghĩa nhiệm vụ song song
    tasks = [
        {"tool_name": "search", "input_data": "lập trình Python"},
        {"tool_name": "search", "input_data": "học máy"},
        {"tool_name": "my_calculator", "input_data": "2 + 2"},
        {"tool_name": "my_calculator", "input_data": "sqrt(16)"},
    ]

    # Thực thi song song
    results = await executor.execute_tools_parallel(tasks)

    for i, result in enumerate(results):
        print(f"Kết quả nhiệm vụ {i+1}: {result[:100]}...")
```

Dựa trên kinh nghiệm thiết kế và hiện thực trên, chúng ta có thể tổng kết tư tưởng cốt lõi của phát triển hệ thống công cụ: ở tầng thiết kế, mỗi công cụ nên tuân theo nguyên tắc trách nhiệm đơn nhất, tập trung vào chức năng cụ thể đồng thời giữ tính thống nhất giao diện, và lấy xử lý ngoại lệ hoàn chỉnh cùng xác minh đầu vào ưu tiên an toàn làm yêu cầu cơ bản. Về tối ưu hiệu năng, tận dụng thực thi bất đồng bộ để nâng cao năng lực xử lý đồng thời, đồng thời quản lý hợp lý kết nối bên ngoài và tài nguyên hệ thống.



## 7.6 Tổng kết chương

Trước khi tổng kết chính thức, chúng ta muốn báo một tin tốt: với mọi phương thức và chức năng hiện thực trong chương này, kho GitHub đều cung cấp ca kiểm thử hoàn chỉnh. Bạn có thể truy cập [liên kết này](https://github.com/datawhalechina/hello-agents/tree/main/code/chapter7) để xem và chạy mã kiểm thử. Thư mục này gồm trình diễn bốn mô hình Agent, kiểm thử tích hợp hệ thống công cụ, ví dụ sử dụng chức năng nâng cao và trải nghiệm Agent tương tác. Nếu muốn xác minh hiện thực của mình có đúng hay không, hoặc muốn hiểu sâu cách dùng thực tế của framework, những ca kiểm thử này là tài liệu tham khảo có giá trị.

Nhìn lại chương này, chúng ta đã hoàn thành một nhiệm vụ đầy thách thức: từng bước xây dựng một framework Agent cơ bản – HelloAgents. Quá trình này luôn tuân theo nguyên tắc cốt lõi “phân tầng tách rời, trách nhiệm đơn nhất, giao diện thống nhất”.

Trong hiện thực cụ thể của framework, chúng ta một lần nữa hiện thực bốn mô hình Agent kinh điển. Từ chế độ hội thoại cơ bản của SimpleAgent, đến sự kết hợp suy luận và hành động của ReActAgent; từ tự phản tư và tối ưu lặp của ReflectionAgent, đến phân rã lập kế hoạch và thực thi từng bước của PlanAndSolveAgent. Còn hệ thống công cụ, với tư cách cốt lõi mở rộng năng lực Agent, quá trình xây dựng nó là một thực hành kỹ thuật hoàn chỉnh.

Quan trọng hơn, việc xây dựng chương 7 không phải điểm kết thúc, mà cung cấp nền tảng kỹ thuật cần thiết cho việc học sâu hơn sau này. Ngay từ đầu thiết kế, chúng ta đã cân nhắc đầy đủ khả năng mở rộng của nội dung sau, dành sẵn giao diện và điểm mở rộng cần thiết cho hiện thực chức năng nâng cao. Giao diện LLM thống nhất, hệ thống tin nhắn chuẩn hóa, cơ chế đăng ký công cụ chúng ta xây dựng cùng nhau tạo thành một nền tảng kỹ thuật hoàn chỉnh. Điều này cho phép chúng ta ở các chương sau ung dung hơn khi học các chủ đề nâng cao: hệ thống bộ nhớ và RAG ở chương 8 sẽ mở rộng biên giới năng lực Agent dựa trên nền này; kỹ thuật ngữ cảnh ở chương 9 sẽ đi sâu vào cơ chế xử lý tin nhắn chúng ta đã xây; giao thức Agent ở chương 10 sẽ cần mở rộng công cụ mới.

Tiếp theo, chúng ta sẽ cùng khám phá cách thêm hệ thống RAG và cơ chế Memory vào framework; hãy đón chờ chương 8!


## Bài tập

1. Chương này xây dựng framework `HelloAgents` và trình bày “vì sao cần tự xây framework Agent”. Hãy phân tích:

   - Mục 7.1.1 nêu bốn hạn chế chính của framework chủ lưu hiện nay. Kết hợp kinh nghiệm thực tế với một framework bạn đã dùng trong [bài tập chương 6](../chapter6/Chuong6-Thuc-hanh-phat-trien-voi-framework.md#bài-tập) hoặc trong dự án thực tế, giải thích những vấn đề này ảnh hưởng đến hiệu quả phát triển như thế nào.
   - `HelloAgents` đưa ra triết lý thiết kế “vạn vật đều là công cụ”, trừu tượng hóa các mô-đun như `Memory`, `RAG`, `MCP` thành công cụ. Thiết kế này có ưu điểm gì? Có hạn chế không? Nêu ví dụ.
   - So sánh mã Agent hiện thực từ con số không ở chương 4 với hiện thực framework hóa ở chương này; framework hóa mang lại cải tiến cụ thể nào? Nếu thiết kế một framework, bạn sẽ ưu tiên những nguyên tắc thiết kế nào?

2. Trong mục 7.2, chúng ta mở rộng `HelloAgentsLLM` để hỗ trợ đa nhà cung cấp mô hình và gọi mô hình cục bộ.

   > <strong>Gợi ý</strong>: đây là bài thực hành, khuyến nghị thao tác thực tế

   - Tham khảo ví dụ ở mục 7.2.1, thử thêm hỗ trợ một nhà cung cấp mô hình mới cho `HelloAgentsLLM` (như `Gemini`, `Anthropic`, `Kimi`). Yêu cầu hiện thực bằng kế thừa, và có thể tự động phát hiện biến môi trường của nhà cung cấp đó.
   - Mục 7.2.3 giới thiệu ba mức ưu tiên của cơ chế tự động phát hiện. Hãy phân tích: nếu đồng thời đặt `OPENAI_API_KEY` và `LLM_BASE_URL="http://localhost:11434/v1"`, framework cuối cùng sẽ chọn nhà cung cấp nào? Thiết kế ưu tiên này có hợp lý không?
   - Ngoài `VLLM` và `Ollama` được giới thiệu trong chương này, còn có các phương án triển khai mô hình cục bộ khác như `SGLang`. Hãy tìm hiểu thông tin và đặc điểm cơ bản của `SGLang`, sau đó so sánh ưu nhược điểm của `VLLM`, `SGLang` và `Ollama` về dễ sử dụng, mức chiếm tài nguyên, tốc độ suy luận, độ chính xác suy luận.

3. Trong mục 7.3, chúng ta hiện thực lớp `Message`, lớp `Config` và lớp cơ sở `Agent`. Hãy phân tích:

   - Lớp `Message` dùng `BaseModel` của `Pydantic` để xác minh dữ liệu. Thiết kế này có ưu điểm gì trong ứng dụng thực tế?
   - Lớp cơ sở `Agent` định nghĩa hai phương thức `run` và `_execute`, trong đó `run` là giao diện công khai, `_execute` là phương thức trừu tượng. Mẫu thiết kế này tên là gì? Có lợi ích gì?
   - Trong lớp `Config`, chúng ta dùng mẫu singleton. Hãy giải thích mẫu singleton là gì, vì sao quản lý cấu hình cần dùng mẫu singleton? Nếu không dùng singleton sẽ gây vấn đề gì?

4. Trong mục 7.4, chúng ta thực hành hiện thực framework hóa bốn mô hình `Agent`.

   > <strong>Gợi ý</strong>: đây là bài thực hành, khuyến nghị thao tác thực tế

   - So sánh `ReActAgent` hiện thực từ con số không ở chương 4 với `ReActAgent` được framework hóa ở chương này; liệt kê 3 điểm cải tiến cụ thể và giải thích những cải tiến này nâng cao khả năng bảo trì và mở rộng của mã như thế nào.
   - `ReflectionAgent` hiện thực vòng “thực thi – phản tư – tối ưu”. Hãy mở rộng hiện thực này, thêm cơ chế “chấm điểm chất lượng”: sau mỗi lần phản tư, để `LLM` chấm điểm đầu ra phiên bản hiện tại; chỉ khi điểm thấp hơn ngưỡng mới tiếp tục tối ưu, ngược lại dừng sớm.
   - Hãy thiết kế và hiện thực một mô hình `Agent` mới `Tree-of-Thought Agent`, yêu cầu kế thừa lớp cơ sở `Agent`; nó có thể sinh nhiều đường suy nghĩ khả dĩ ở mỗi bước, sau đó chọn đường tối ưu để tiếp tục.

5. Trong mục 7.5, chúng ta xây dựng hệ thống công cụ. Hãy suy nghĩ các vấn đề sau:

   - Lớp `BaseTool` định nghĩa phương thức trừu tượng `execute`; mọi công cụ đều phải hiện thực phương thức này. Hãy giải thích vì sao buộc mọi công cụ hiện thực giao diện thống nhất? Nếu một công cụ cần trả về nhiều giá trị (như công cụ tìm kiếm trả về tiêu đề, tóm tắt, liên kết), nên thiết kế thế nào?
   - Mục 7.5.3 hiện thực chuỗi công cụ (`ToolChain`). Hãy thiết kế một tình huống ứng dụng thực tế cần nối ít nhất 3 công cụ, và vẽ sơ đồ thực thi chuỗi công cụ.
   - Bộ thực thi công cụ bất đồng bộ (`AsyncToolExecutor`) dùng thread pool để thực thi công cụ song song. Hãy phân tích: trong trường hợp nào thực thi công cụ song song mang lại nâng cao hiệu năng?

6. Khả năng mở rộng của framework là một trong những cân nhắc thiết kế quan trọng. Bây giờ bạn cần mở rộng framework `HelloAgents`, hiện thực một số chức năng và đặc tính mới thú vị.

   - Trước tiên thêm chức năng “đầu ra dạng luồng” cho `HelloAgents`, để `Agent` có thể trả về kết quả trung gian theo thời gian thực khi sinh phản hồi (giống hiệu ứng gõ chữ trong giao diện người dùng `ChatGPT`). Hãy thiết kế phương án hiện thực chức năng này, giải thích cần sửa những lớp và phương thức nào.
   - Sau đó thêm chức năng “quản lý hội thoại nhiều lượt” cho framework, có thể tự động quản lý lịch sử hội thoại, hỗ trợ nhánh hội thoại và quay lui. Bạn sẽ thiết kế thế nào? Cần thêm những lớp nào? Tích hợp với hệ thống `Message` hiện có ra sao?
   - Cuối cùng thiết kế một “hệ thống plugin” cho `HelloAgents`, cho phép nhà phát triển bên thứ ba mở rộng chức năng framework bằng plugin (như thêm loại `Agent` mới, loại công cụ mới, v.v.) mà không cần sửa mã lõi framework. Yêu cầu vẽ sơ đồ kiến trúc hệ thống plugin và giải thích giao diện then chốt.

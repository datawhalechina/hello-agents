# Chương 10: Giao thức giao tiếp Agent

Ở các chương trước, chúng ta đã xây dựng những Agent đơn lẻ với đầy đủ chức năng, có năng lực suy luận, gọi công cụ và ghi nhớ. Tuy nhiên, khi cố gắng xây dựng những hệ thống AI phức tạp hơn, câu hỏi tự nhiên nảy sinh: <strong>làm sao để Agent tương tác hiệu quả với thế giới bên ngoài? Làm sao để nhiều Agent phối hợp với nhau?</strong>

Đây chính là vấn đề cốt lõi mà giao thức giao tiếp Agent cần giải quyết. Chương này sẽ đưa vào framework HelloAgents ba giao thức giao tiếp: <strong>MCP (Model Context Protocol)</strong> dùng cho giao tiếp chuẩn hóa giữa Agent và công cụ, <strong>A2A (Agent-to-Agent Protocol)</strong> dùng cho phối hợp ngang hàng giữa các Agent, và <strong>ANP (Agent Network Protocol)</strong> dùng để xây dựng mạng Agent quy mô lớn. Ba giao thức này cùng nhau tạo nên tầng hạ tầng của giao tiếp Agent.

Qua việc học chương này, bạn sẽ nắm được triết lý thiết kế và kỹ năng thực hành của giao thức giao tiếp Agent, hiểu sự khác biệt thiết kế giữa ba giao thức chủ lưu, và biết cách chọn giao thức phù hợp để giải quyết bài toán thực tế.

## 10.1 Nền tảng giao thức giao tiếp Agent

### 10.1.1 Vì sao cần giao thức giao tiếp

Nhìn lại Agent ReAct mà chúng ta đã xây dựng ở chương 7: nó đã có năng lực suy luận và gọi công cụ mạnh mẽ. Hãy xem một kịch bản sử dụng điển hình:

```python
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.tools import CalculatorTool, SearchTool

llm = HelloAgentsLLM()
agent = ReActAgent(name="Trợ lý AI", llm=llm)
agent.add_tool(CalculatorTool())
agent.add_tool(SearchTool())

# Agent có thể hoàn thành nhiệm vụ một cách độc lập
response = agent.run("Tìm tin tức AI mới nhất, và tính tổng vốn hóa của các công ty liên quan")
```

Agent này hoạt động khá tốt, nhưng nó đối mặt với ba giới hạn mang tính căn bản. Đầu tiên là <strong>tình thế khó xử khi tích hợp công cụ</strong>: mỗi khi cần truy cập một dịch vụ bên ngoài mới (như GitHub API, cơ sở dữ liệu, hệ thống tệp), chúng ta đều phải viết một lớp Tool chuyên dụng. Việc này không chỉ tốn công sức mà công cụ do các nhà phát triển khác nhau viết ra còn không thể tương thích với nhau. Thứ hai là <strong>nút thắt của việc mở rộng năng lực</strong>: năng lực của Agent bị giới hạn trong tập công cụ đã định nghĩa trước, không thể phát hiện và sử dụng dịch vụ mới một cách động. Cuối cùng là <strong>sự thiếu vắng phối hợp</strong>: khi nhiệm vụ phức tạp đến mức cần nhiều Agent chuyên môn phối hợp (như nhà nghiên cứu + người viết + biên tập viên), chúng ta chỉ có thể điều phối công việc của chúng bằng cách lập trình thủ công.

Hãy hiểu các giới hạn này qua một ví dụ cụ thể hơn. Giả sử bạn cần xây dựng một trợ lý nghiên cứu thông minh, nó cần:

```python
# Cách truyền thống: tích hợp thủ công từng dịch vụ
class GitHubTool(BaseTool):
    """Cần tự viết adapter cho GitHub API"""
    def run(self, repo_url):
        # Rất nhiều mã gọi API...
        pass

class DatabaseTool(BaseTool):
    """Cần tự viết adapter cho cơ sở dữ liệu"""
    def run(self, query):
        # Mã kết nối và truy vấn cơ sở dữ liệu...
        pass

class WeatherTool(BaseTool):
    """Cần tự viết adapter cho API thời tiết"""
    def run(self, location):
        # Mã gọi API thời tiết...
        pass

# Mỗi dịch vụ mới đều phải lặp lại quy trình này
agent.add_tool(GitHubTool())
agent.add_tool(DatabaseTool())
agent.add_tool(WeatherTool())
```

Cách làm này có những vấn đề rõ ràng: mã trùng lặp (mỗi công cụ đều phải xử lý yêu cầu HTTP, xử lý lỗi, xác thực, v.v.), khó bảo trì (API thay đổi thì phải sửa mọi công cụ liên quan), không thể tái sử dụng (công cụ của nhà phát triển khác không dùng trực tiếp được), khả năng mở rộng kém (thêm dịch vụ mới cần rất nhiều công sức viết mã).

<strong>Giá trị cốt lõi của giao thức giao tiếp</strong> chính là giải quyết những vấn đề này. Nó cung cấp một bộ quy chuẩn giao diện chuẩn hóa, cho phép Agent truy cập nhiều dịch vụ bên ngoài theo cách thống nhất mà không cần viết adapter riêng cho từng dịch vụ. Điều này giống như giao thức TCP/IP của Internet: nó cho phép các thiết bị khác nhau giao tiếp với nhau mà không cần viết mã giao tiếp riêng cho từng loại thiết bị.

Khi đã có giao thức giao tiếp, đoạn mã trên có thể được đơn giản hóa thành:

```python
from hello_agents.tools import MCPTool

# Kết nối tới máy chủ MCP, tự động nhận được mọi công cụ
mcp_tool = MCPTool()  # Máy chủ tích hợp sẵn cung cấp các công cụ cơ bản

# Hoặc kết nối tới máy chủ MCP chuyên nghiệp
github_mcp = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-github"])
database_mcp = MCPTool(server_command=["python", "database_mcp_server.py"])

# Agent tự động nhận được mọi năng lực, không cần viết tay adapter
agent.add_tool(mcp_tool)
agent.add_tool(github_mcp)
agent.add_tool(database_mcp)
```

Thay đổi mà giao thức giao tiếp mang lại mang tính căn bản: <strong>giao diện chuẩn hóa</strong> cho phép các dịch vụ khác nhau cung cấp cách truy cập thống nhất, <strong>khả năng tương tác</strong> khiến công cụ của những nhà phát triển khác nhau có thể tích hợp liền mạch, <strong>phát hiện động</strong> cho phép Agent tìm ra dịch vụ và năng lực mới ngay lúc chạy, <strong>khả năng mở rộng</strong> giúp hệ thống dễ dàng thêm mô-đun chức năng mới.

### 10.1.2 So sánh triết lý thiết kế của ba giao thức

Giao thức giao tiếp Agent không phải một giải pháp đơn nhất, mà là một loạt tiêu chuẩn được thiết kế cho các kịch bản giao tiếp khác nhau. Trong chương này, chúng ta lấy ba giao thức chủ lưu hiện nay MCP, A2A và ANP làm ví dụ để thực hành; dưới đây là một so sánh tổng quan.

<strong>(1) MCP: cầu nối giữa Agent và công cụ</strong>

MCP (Model Context Protocol) do nhóm Anthropic đề xuất<sup>[1]</sup>, triết lý thiết kế cốt lõi của nó là <strong>chuẩn hóa cách Agent giao tiếp với công cụ/tài nguyên bên ngoài</strong>. Hãy tưởng tượng Agent của bạn cần truy cập đủ loại dịch vụ như hệ thống tệp, cơ sở dữ liệu, GitHub, Slack. Cách làm truyền thống là viết adapter riêng cho từng dịch vụ, việc này vừa tốn công vừa khó bảo trì. MCP thông qua việc định nghĩa quy chuẩn giao thức thống nhất, cho phép mọi dịch vụ đều được truy cập theo cùng một cách.

Triết lý thiết kế của MCP là “chia sẻ ngữ cảnh”. Nó không chỉ là một giao thức RPC (gọi thủ tục từ xa), mà quan trọng hơn, nó cho phép Agent và công cụ chia sẻ thông tin ngữ cảnh phong phú. Như Hình 10.1 minh họa, khi Agent truy cập một kho mã, máy chủ MCP không chỉ cung cấp nội dung tệp mà còn cung cấp cả cấu trúc mã, quan hệ phụ thuộc, lịch sử commit và các thông tin ngữ cảnh khác, giúp Agent đưa ra quyết định thông minh hơn.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-1.png" alt="" width="85%"/>
  <p>Hình 10.1 Tư tưởng thiết kế MCP</p>
</div>

<strong>(2) A2A: cuộc đối thoại giữa các Agent</strong>

Giao thức A2A (Agent-to-Agent Protocol) do nhóm Google đề xuất<sup>2</sup>, triết lý thiết kế cốt lõi là <strong>hiện thực giao tiếp ngang hàng giữa các Agent</strong>. Khác với MCP vốn quan tâm giao tiếp giữa Agent và công cụ, A2A quan tâm cách các Agent phối hợp với nhau. Thiết kế này cho phép Agent đối thoại, thương lượng và phối hợp như một đội ngũ con người.

Triết lý thiết kế của A2A là “giao tiếp ngang hàng”. Như Hình 10.2 minh họa, trong mạng A2A, mỗi Agent vừa là nhà cung cấp dịch vụ vừa là người tiêu dùng dịch vụ. Agent có thể chủ động khởi tạo yêu cầu, cũng có thể phản hồi yêu cầu của Agent khác. Thiết kế ngang hàng này tránh được nút thắt của bộ điều phối tập trung, khiến mạng Agent linh hoạt và dễ mở rộng hơn.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-2.png" alt="" width="85%"/>
  <p>Hình 10.2 Tư tưởng thiết kế A2A</p>
</div>

<strong>(3) ANP: hạ tầng của mạng Agent</strong>

ANP (Agent Network Protocol) là một khung giao thức mang tính khái niệm<sup>3</sup>, hiện do cộng đồng mã nguồn mở duy trì và chưa có hệ sinh thái trưởng thành; triết lý thiết kế cốt lõi của nó là <strong>xây dựng hạ tầng cho mạng Agent quy mô lớn</strong>. Nếu MCP giải quyết “cách truy cập công cụ”, A2A giải quyết “cách đối thoại với Agent khác”, thì ANP giải quyết “cách phát hiện và kết nối Agent trong một mạng quy mô lớn”.

Triết lý thiết kế của ANP là “phát hiện dịch vụ phi tập trung”. Trong một mạng gồm hàng trăm hàng nghìn Agent, làm sao để Agent tìm được dịch vụ mà nó cần? Như Hình 10.3 minh họa, ANP cung cấp cơ chế đăng ký, phát hiện và định tuyến dịch vụ, cho phép Agent phát hiện động các dịch vụ khác trong mạng mà không cần cấu hình trước mọi quan hệ kết nối.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-3.png" alt="" width="85%"/>
  <p>Hình 10.3 Tư tưởng thiết kế ANP</p>
</div>

Cuối cùng, trong Bảng 10.1, hãy dùng một bảng so sánh để hiểu rõ hơn sự khác biệt giữa ba giao thức này:

<div align="center">
  <p>Bảng 10.1 So sánh ba giao thức</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-1.png" alt="" width="85%"/>
</div>

<strong>(4) Làm sao chọn giao thức phù hợp?</strong>

Hiện nay các giao thức vẫn đang ở giai đoạn phát triển sớm; hệ sinh thái của MCP tương đối trưởng thành, tuy nhiên tính thời sự của từng công cụ phụ thuộc vào người duy trì, nên ưu tiên chọn các công cụ MCP được các công ty lớn bảo trợ.

Then chốt của việc chọn giao thức là hiểu nhu cầu của bạn:

- Nếu Agent của bạn cần truy cập dịch vụ bên ngoài (tệp, cơ sở dữ liệu, API), hãy chọn <strong>MCP</strong>
- Nếu bạn cần nhiều Agent phối hợp với nhau để hoàn thành nhiệm vụ, hãy chọn <strong>A2A</strong>
- Nếu bạn muốn xây dựng một hệ sinh thái Agent quy mô lớn, hãy cân nhắc <strong>ANP</strong>

### 10.1.3 Thiết kế kiến trúc giao thức giao tiếp của HelloAgents

Sau khi đã hiểu triết lý thiết kế của ba giao thức, hãy xem cách hiện thực và sử dụng chúng trong framework HelloAgents. Mục tiêu thiết kế của chúng ta là: <strong>giúp người học sử dụng các giao thức này theo cách đơn giản nhất, đồng thời giữ đủ linh hoạt để đối phó với kịch bản phức tạp</strong>.

Như Hình 10.4 minh họa, kiến trúc giao thức giao tiếp của HelloAgents dùng thiết kế ba tầng, từ dưới lên trên lần lượt là: tầng hiện thực giao thức, tầng đóng gói công cụ và tầng tích hợp Agent.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-4.png" alt="" width="85%"/>
  <p>Hình 10.4 Thiết kế giao thức giao tiếp của HelloAgents</p>
</div>

<strong>(1) Tầng hiện thực giao thức</strong>: tầng này chứa hiện thực cụ thể của ba giao thức. MCP được hiện thực dựa trên thư viện FastMCP, cung cấp chức năng client và máy chủ; A2A được hiện thực dựa trên a2a-sdk chính thức của Google; ANP là hiện thực nhẹ do chúng ta tự phát triển, cung cấp chức năng phát hiện dịch vụ và quản lý mạng, tất nhiên hiện nay cũng đã có [hiện thực](https://github.com/agent-network-protocol/AgentConnect) chính thức, nhưng xét đến các vòng lặp về sau, ở đây chúng ta chỉ mô phỏng ở mức khái niệm.

<strong>(2) Tầng đóng gói công cụ</strong>: tầng này đóng gói hiện thực giao thức thành giao diện Tool thống nhất. MCPTool, A2ATool và ANPTool đều kế thừa từ BaseTool, cung cấp phương thức `run()` nhất quán. Thiết kế này cho phép Agent sử dụng các giao thức khác nhau theo cùng một cách.

<strong>(3) Tầng tích hợp Agent</strong>: tầng này là điểm tích hợp giữa Agent và giao thức. Mọi Agent (ReActAgent, SimpleAgent, v.v.) đều dùng công cụ giao thức thông qua Tool System, không cần quan tâm chi tiết giao thức bên dưới.

### 10.1.4 Mục tiêu học tập và trải nghiệm nhanh của chương này

Trước tiên hãy xem nội dung học tập của chương 10:

```
hello_agents/
├── protocols/                          # Mô-đun giao thức giao tiếp
│   ├── mcp/                            # Hiện thực giao thức MCP (Model Context Protocol)
│   │   ├── client.py                   # Client MCP (hỗ trợ 5 kiểu truyền tải)
│   │   ├── server.py                   # Máy chủ MCP (đóng gói FastMCP)
│   │   └── utils.py                    # Hàm tiện ích (create_context/parse_context)
│   ├── a2a/                            # Hiện thực giao thức A2A (Agent-to-Agent Protocol)
│   │   └── implementation.py           # Máy chủ/client A2A (dựa trên a2a-sdk, phụ thuộc tùy chọn)
│   └── anp/                            # Hiện thực giao thức ANP (Agent Network Protocol)
│       └── implementation.py           # Phát hiện/đăng ký dịch vụ ANP (hiện thực khái niệm)
└── tools/builtin/                      # Mô-đun công cụ tích hợp
    └── protocol_tools.py               # Bộ bọc công cụ giao thức (MCPTool/A2ATool/ANPTool)
```

Nội dung của chương này chủ yếu thiên về ứng dụng; mục tiêu học tập là có được năng lực áp dụng giao thức trong dự án của chính mình. Hơn nữa, các giao thức hiện vẫn ở giai đoạn phát triển sớm, nên không cần dành quá nhiều công sức để “phát minh lại bánh xe”. Trước khi bắt đầu thực hành, hãy chuẩn bị môi trường phát triển:

```bash
# Cài đặt framework HelloAgents (phiên bản chương 10)
pip install "hello-agents[protocol]==0.2.2"

# Cài đặt NodeJS, có thể tham khảo tài liệu trong Additional-Chapter
```

Hãy trải nghiệm chức năng cơ bản của ba giao thức bằng đoạn mã đơn giản nhất:

```python
from hello_agents.tools import MCPTool, A2ATool, ANPTool

# 1. MCP: truy cập công cụ
mcp_tool = MCPTool()
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "add",
    "arguments": {"a": 10, "b": 20}
})
print(f"Kết quả tính toán MCP: {result}")  # Đầu ra: 30.0

# 2. ANP: phát hiện dịch vụ
anp_tool = ANPTool()
anp_tool.run({
    "action": "register_service",
    "service_id": "calculator",
    "service_type": "math",
    "endpoint": "http://localhost:8080"
})
services = anp_tool.run({"action": "discover_services"})
print(f"Dịch vụ đã phát hiện: {services}")

# 3. A2A: giao tiếp Agent
a2a_tool = A2ATool("http://localhost:5000")
print("Tạo công cụ A2A thành công")
```

Ví dụ đơn giản này đã trình bày chức năng cốt lõi của ba giao thức. Trong các mục tiếp theo, chúng ta sẽ đi sâu học cách dùng chi tiết và thực hành tốt nhất của từng giao thức.

## 10.2 Thực hành giao thức MCP

Bây giờ, hãy đi sâu vào MCP để nắm cách giúp Agent truy cập công cụ và tài nguyên bên ngoài.

### 10.2.1 Giới thiệu khái niệm giao thức MCP

<strong>(1) MCP: “USB-C” của Agent</strong>

Hãy tưởng tượng Agent của bạn có thể cần làm nhiều việc cùng lúc, ví dụ:
- Đọc tài liệu trong hệ thống tệp cục bộ
- Truy vấn cơ sở dữ liệu PostgreSQL
- Tìm mã trên GitHub
- Gửi tin nhắn Slack
- Truy cập Google Drive

Theo cách truyền thống, bạn cần viết mã adapter cho từng dịch vụ, xử lý các API, cách xác thực, xử lý lỗi khác nhau, v.v. Việc này không chỉ tốn công mà còn khó bảo trì. Quan trọng hơn, cách hiện thực function call của các nền tảng LLM khác nhau rất khác biệt, nên khi chuyển mô hình bạn phải viết lại rất nhiều mã.

Sự xuất hiện của MCP đã thay đổi tất cả. Cũng giống như USB-C thống nhất cách kết nối của nhiều thiết bị, <strong>MCP thống nhất cách Agent tương tác với công cụ bên ngoài</strong>. Dù bạn dùng Claude, GPT hay mô hình khác, chỉ cần chúng hỗ trợ giao thức MCP là có thể truy cập liền mạch cùng một bộ công cụ và tài nguyên.

<strong>(2) Kiến trúc MCP</strong>

Giao thức MCP dùng kiến trúc ba tầng Host, Client, Servers; hãy dùng kịch bản trong Hình 10.5 để hiểu các thành phần này phối hợp với nhau thế nào.

Giả sử bạn đang dùng Claude Desktop và hỏi: “Trên màn hình của tôi có những tài liệu nào?”

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-5.png" alt="" width="85%"/>
  <p>Hình 10.5 Minh họa ca sử dụng MCP</p>
</div>

<strong>Trách nhiệm của kiến trúc ba tầng:</strong>

1. <strong>Host (tầng chủ nhà)</strong>: Claude Desktop đóng vai Host, chịu trách nhiệm nhận câu hỏi của người dùng và tương tác với mô hình Claude. Host là giao diện mà người dùng tương tác trực tiếp, nó quản lý toàn bộ luồng hội thoại.

2. <strong>Client (tầng client)</strong>: Khi mô hình Claude quyết định cần truy cập hệ thống tệp, MCP Client tích hợp trong Host được kích hoạt. Client chịu trách nhiệm thiết lập kết nối với MCP Server thích hợp, gửi yêu cầu và nhận phản hồi.

3. <strong>Server (tầng máy chủ)</strong>: Máy chủ MCP hệ thống tệp được gọi, thực hiện thao tác quét tệp thực tế, truy cập thư mục màn hình và trả về danh sách tài liệu tìm thấy.

<strong>Luồng tương tác đầy đủ:</strong> câu hỏi của người dùng → Claude Desktop (Host) → mô hình Claude phân tích → cần thông tin tệp → MCP Client kết nối → máy chủ MCP hệ thống tệp → thực hiện thao tác → trả kết quả → Claude sinh câu trả lời → hiển thị trên Claude Desktop

Ưu điểm của thiết kế kiến trúc này là <strong>tách biệt mối quan tâm</strong>: Host tập trung vào trải nghiệm người dùng, Client tập trung vào giao tiếp giao thức, Server tập trung vào hiện thực chức năng cụ thể. Nhà phát triển chỉ cần tập trung phát triển MCP Server tương ứng, không cần quan tâm chi tiết hiện thực của Host và Client.

<strong>(3) Năng lực cốt lõi của MCP</strong>

Như Bảng 10.2 trình bày, giao thức MCP cung cấp ba năng lực cốt lõi, tạo thành khung truy cập công cụ hoàn chỉnh:

<div align="center">
  <p>Bảng 10.2 Năng lực cốt lõi của MCP</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-2.png" alt="" width="85%"/>
</div>

Sự khác biệt giữa ba năng lực này nằm ở: <strong>Tools mang tính chủ động</strong> (thực hiện thao tác), <strong>Resources mang tính bị động</strong> (cung cấp dữ liệu), <strong>Prompts mang tính định hướng</strong> (cung cấp mẫu).

<strong>(4) Quy trình làm việc của MCP</strong>

Hãy hiểu quy trình làm việc đầy đủ của MCP qua một ví dụ cụ thể, như Hình 10.6 minh họa:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-6.png" alt="" width="85%"/>
  <p>Hình 10.6 Minh họa ca sử dụng MCP</p>
</div>

Một câu hỏi then chốt là: <strong>Claude (hoặc LLM khác) quyết định dùng những công cụ nào như thế nào?</strong>

Khi người dùng đặt câu hỏi, quy trình chọn công cụ đầy đủ diễn ra như sau:

1. <strong>Giai đoạn phát hiện công cụ</strong>: Sau khi MCP Client kết nối tới Server, trước tiên nó gọi `list_tools()` để lấy thông tin mô tả của mọi công cụ khả dụng (bao gồm tên công cụ, mô tả chức năng, định nghĩa tham số)

2. <strong>Xây dựng ngữ cảnh</strong>: Client chuyển danh sách công cụ sang định dạng LLM hiểu được, thêm vào system prompt. Ví dụ:
   ```
   Bạn có thể sử dụng các công cụ sau:
   - read_file(path: str): đọc nội dung tệp tại đường dẫn chỉ định
   - search_code(query: str, language: str): tìm kiếm trong kho mã
   ```

3. <strong>Mô hình suy luận</strong>: LLM phân tích câu hỏi của người dùng và các công cụ khả dụng, quyết định có cần gọi công cụ hay không và gọi công cụ nào. Quyết định này dựa trên mô tả công cụ và ngữ cảnh hội thoại hiện tại

4. <strong>Thực thi công cụ</strong>: Nếu LLM quyết định dùng công cụ, Client thực thi công cụ đã chọn thông qua MCP Server và lấy kết quả

5. <strong>Tích hợp kết quả</strong>: Kết quả thực thi công cụ được gửi lại cho LLM, LLM kết hợp kết quả để sinh câu trả lời cuối cùng

Quá trình này <strong>hoàn toàn tự động</strong>; LLM sẽ dựa vào chất lượng mô tả công cụ để quyết định có dùng công cụ hay không và dùng thế nào. Vì vậy, việc viết mô tả công cụ rõ ràng, chính xác là cực kỳ quan trọng.

<strong>(5) Khác biệt giữa MCP và Function Calling</strong>

Nhiều nhà phát triển sẽ hỏi: <strong>tôi đã dùng Function Calling rồi, vì sao còn cần MCP?</strong> Hãy dùng Bảng 10.3 để hiểu sự khác biệt giữa chúng.

<div align="center">
  <p>Bảng 10.3 So sánh Function Calling và MCP</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-3.png" alt="" width="85%"/>
</div>

Ở đây chúng ta lấy ví dụ Agent cần truy cập kho GitHub và hệ thống tệp cục bộ để so sánh chi tiết hai cách hiện thực cùng một nhiệm vụ.

<strong>Cách 1: dùng Function Calling</strong>

```python
# Bước 1: định nghĩa hàm cho từng nhà cung cấp LLM
# Định dạng OpenAI
openai_tools = [
    {
        "type": "function",
        "function": {
            "name": "search_github",
            "description": "Tìm kiếm kho GitHub",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Từ khóa tìm kiếm"}
                },
                "required": ["query"]
            }
        }
    }
]

# Định dạng Claude
claude_tools = [
    {
        "name": "search_github",
        "description": "Tìm kiếm kho GitHub",
        "input_schema": {  # Lưu ý: không phải parameters
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Từ khóa tìm kiếm"}
            },
            "required": ["query"]
        }
    }
]

# Bước 2: tự hiện thực hàm công cụ
def search_github(query):
    import requests
    response = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": query}
    )
    return response.json()

# Bước 3: xử lý định dạng phản hồi của các mô hình khác nhau
# Phản hồi của OpenAI
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    result = search_github(**json.loads(tool_call.function.arguments))

# Phản hồi của Claude
if response.content[0].type == "tool_use":
    tool_use = response.content[0]
    result = search_github(**tool_use.input)
```

<strong>Cách 2: dùng MCP</strong>

```python
from hello_agents.protocols import MCPClient

# Bước 1: kết nối tới máy chủ MCP do cộng đồng cung cấp (không cần tự hiện thực)
github_client = MCPClient([
    "npx", "-y", "@modelcontextprotocol/server-github"
])

fs_client = MCPClient([
    "npx", "-y", "@modelcontextprotocol/server-filesystem", "."
])

# Bước 2: cách gọi thống nhất (không phụ thuộc mô hình)
async with github_client:
    # Tự động phát hiện công cụ
    tools = await github_client.list_tools()

    # Gọi công cụ (giao diện chuẩn hóa)
    result = await github_client.call_tool(
        "search_repositories",
        {"query": "AI agents"}
    )

# Bước 3: mọi mô hình hỗ trợ MCP đều dùng được
# OpenAI, Claude, Llama... đều dùng cùng một client MCP
```

Trước tiên cần làm rõ: Function Calling và MCP không phải quan hệ cạnh tranh mà là bổ trợ cho nhau. Function Calling là một năng lực cốt lõi của mô hình ngôn ngữ lớn; nó thể hiện trí tuệ nội tại của mô hình, giúp mô hình hiểu khi nào cần gọi hàm và sinh chính xác tham số gọi tương ứng. Ngược lại, MCP đóng vai trò giao thức hạ tầng: nó giải quyết ở tầng kỹ thuật phần mềm vấn đề công cụ kết nối với mô hình như thế nào, thông qua cách chuẩn hóa để mô tả và gọi công cụ.

Chúng ta có thể hiểu bằng một phép so sánh đơn giản: Function Calling tương đương với việc bạn học được kỹ năng “cách gọi điện thoại”, bao gồm khi nào quay số, nói chuyện với đầu dây bên kia thế nào, khi nào cúp máy. Còn MCP chính là “tiêu chuẩn liên lạc điện thoại” thống nhất toàn cầu, đảm bảo bất kỳ chiếc điện thoại nào cũng gọi được tới chiếc khác một cách suôn sẻ.

Sau khi đã hiểu quan hệ bổ trợ giữa chúng, tiếp theo hãy xem cách dùng giao thức MCP trong HelloAgents.

### 10.2.2 Sử dụng MCP Client

HelloAgents hiện thực đầy đủ chức năng MCP client dựa trên FastMCP 2.0. Chúng ta cung cấp hai loại API bất đồng bộ và đồng bộ để phù hợp với các kịch bản sử dụng khác nhau. Với hầu hết ứng dụng, nên dùng API bất đồng bộ vì nó xử lý yêu cầu đồng thời và thao tác chạy lâu tốt hơn. Dưới đây là phần trình diễn thao tác được chia nhỏ.

<strong>(1) Kết nối tới máy chủ MCP</strong>

MCP client hỗ trợ nhiều cách kết nối; phổ biến nhất là chế độ Stdio (giao tiếp với tiến trình cục bộ qua đầu vào/đầu ra chuẩn):

```python
import asyncio
from hello_agents.protocols import MCPClient

async def connect_to_server():
    # Cách 1: kết nối tới máy chủ hệ thống tệp do cộng đồng cung cấp
    # npx sẽ tự động tải và chạy gói @modelcontextprotocol/server-filesystem
    client = MCPClient([
        "npx", "-y",
        "@modelcontextprotocol/server-filesystem",
        "."  # Chỉ định thư mục gốc
    ])

    # Dùng async with để đảm bảo kết nối được đóng đúng cách
    async with client:
        # Sử dụng client ở đây
        tools = await client.list_tools()
        print(f"Công cụ khả dụng: {[t['name'] for t in tools]}")

    # Cách 2: kết nối tới máy chủ MCP Python tùy chỉnh
    client = MCPClient(["python", "my_mcp_server.py"])
    async with client:
        # Sử dụng client...
        pass

# Chạy hàm bất đồng bộ
asyncio.run(connect_to_server())
```

<strong>(2) Phát hiện công cụ khả dụng</strong>

Sau khi kết nối thành công, bước đầu tiên thường là truy vấn xem máy chủ cung cấp những công cụ nào:

```python
async def discover_tools():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        # Lấy mọi công cụ khả dụng
        tools = await client.list_tools()

        print(f"Máy chủ cung cấp {len(tools)} công cụ:")
        for tool in tools:
            print(f"\nTên công cụ: {tool['name']}")
            print(f"Mô tả: {tool.get('description', 'Không có mô tả')}")

            # In thông tin tham số
            if 'inputSchema' in tool:
                schema = tool['inputSchema']
                if 'properties' in schema:
                    print("Tham số:")
                    for param_name, param_info in schema['properties'].items():
                        param_type = param_info.get('type', 'any')
                        param_desc = param_info.get('description', '')
                        print(f"  - {param_name} ({param_type}): {param_desc}")

asyncio.run(discover_tools())

# Ví dụ đầu ra:
# Máy chủ cung cấp 5 công cụ:
#
# Tên công cụ: read_file
# Mô tả: đọc nội dung tệp
# Tham số:
#   - path (string): đường dẫn tệp
#
# Tên công cụ: write_file
# Mô tả: ghi nội dung vào tệp
# Tham số:
#   - path (string): đường dẫn tệp
#   - content (string): nội dung tệp
```

<strong>(3) Gọi công cụ</strong>

Khi gọi công cụ, chỉ cần cung cấp tên công cụ và tham số phù hợp với JSON Schema:

```python
async def use_tools():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        # Đọc tệp
        result = await client.call_tool("read_file", {"path": "my_README.md"})
        print(f"Nội dung tệp:\n{result}")

        # Liệt kê thư mục
        result = await client.call_tool("list_directory", {"path": "."})
        print(f"Tệp trong thư mục hiện tại: {result}")

        # Ghi tệp
        result = await client.call_tool("write_file", {
            "path": "output.txt",
            "content": "Hello from MCP!"
        })
        print(f"Kết quả ghi: {result}")

asyncio.run(use_tools())
```

Ở đây chúng ta cung cấp thêm một cách an toàn hơn để gọi dịch vụ MCP, bạn có thể tham khảo:

```python
async def safe_tool_call():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        try:
            # Thử đọc một tệp có thể không tồn tại
            result = await client.call_tool("read_file", {"path": "nonexistent.txt"})
            print(result)
        except Exception as e:
            print(f"Gọi công cụ thất bại: {e}")
            # Có thể chọn thử lại, dùng giá trị mặc định hoặc báo lỗi cho người dùng

asyncio.run(safe_tool_call())
```

<strong>(4) Truy cập tài nguyên</strong>

Ngoài công cụ, máy chủ MCP còn có thể cung cấp tài nguyên (Resources):

```python
# Liệt kê tài nguyên khả dụng
resources = client.list_resources()
print(f"Tài nguyên khả dụng: {[r['uri'] for r in resources]}")

# Đọc tài nguyên
resource_content = client.read_resource("file:///path/to/resource")
print(f"Nội dung tài nguyên: {resource_content}")
```

<strong>(5) Sử dụng mẫu prompt</strong>

Máy chủ MCP có thể cung cấp các mẫu prompt (Prompts) định nghĩa trước:

```python
# Liệt kê prompt khả dụng
prompts = client.list_prompts()
print(f"Prompt khả dụng: {[p['name'] for p in prompts]}")

# Lấy nội dung prompt
prompt = client.get_prompt("code_review", {"language": "python"})
print(f"Nội dung prompt: {prompt}")
```

<strong>(6) Ví dụ đầy đủ: sử dụng dịch vụ GitHub MCP</strong>

Hãy xem một ví dụ đầy đủ về cách dùng dịch vụ GitHub MCP do cộng đồng cung cấp; chúng ta sẽ dùng MCP Tools đã được đóng gói sẵn để:

```python
"""
Ví dụ dịch vụ GitHub MCP

Lưu ý: cần đặt biến môi trường
    Windows: $env:GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
    Linux/macOS: export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
"""

from hello_agents.tools import MCPTool

# Tạo công cụ GitHub MCP
github_tool = MCPTool(
    server_command=["npx", "-y", "@modelcontextprotocol/server-github"]
)

# 1. Liệt kê công cụ khả dụng
print("📋 Công cụ khả dụng:")
result = github_tool.run({"action": "list_tools"})
print(result)

# 2. Tìm kiếm kho
print("\n🔍 Tìm kiếm kho:")
result = github_tool.run({
    "action": "call_tool",
    "tool_name": "search_repositories",
    "arguments": {
        "query": "AI agents language:python",
        "page": 1,
        "perPage": 3
    }
})
print(result)

```

### 10.2.3 Tìm hiểu chi tiết các kiểu truyền tải của MCP

Một đặc tính quan trọng của giao thức MCP là <strong>độc lập với tầng truyền tải</strong> (Transport Agnostic). Điều này có nghĩa bản thân giao thức MCP không phụ thuộc vào một kiểu truyền tải cụ thể nào và có thể chạy trên các kênh giao tiếp khác nhau. HelloAgents dựa trên FastMCP 2.0, cung cấp hỗ trợ đầy đủ các kiểu truyền tải để bạn chọn chế độ phù hợp nhất với kịch bản thực tế.

<strong>(1) Tổng quan các kiểu truyền tải</strong>

`MCPClient` của HelloAgents hỗ trợ năm kiểu truyền tải, mỗi kiểu có kịch bản sử dụng khác nhau, như Bảng 10.4 trình bày:

<div align="center">
  <p>Bảng 10.4 So sánh các kiểu truyền tải của MCP</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-4.png" alt="" width="85%"/>
</div>

<strong>(2) Ví dụ sử dụng các kiểu truyền tải</strong>

```python
from hello_agents.tools import MCPTool

# 1. Memory Transport - truyền tải trong bộ nhớ (dùng cho kiểm thử)
# Không chỉ định tham số nào, dùng máy chủ minh họa tích hợp sẵn
mcp_tool = MCPTool()

# 2. Stdio Transport - truyền tải qua đầu vào/đầu ra chuẩn (phát triển cục bộ)
# Dùng danh sách lệnh để khởi động máy chủ cục bộ
mcp_tool = MCPTool(server_command=["python", "examples/mcp_example_server.py"])

# 3. Stdio Transport with Args - truyền tải lệnh có tham số
# Có thể truyền thêm tham số
mcp_tool = MCPTool(server_command=["python", "examples/mcp_example_server.py", "--debug"])

# 4. Stdio Transport - máy chủ cộng đồng (cách dùng npx)
# Dùng npx khởi động máy chủ MCP cộng đồng
mcp_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

# 5. HTTP/SSE/StreamableHTTP Transport
# Lưu ý: MCPTool chủ yếu dùng cho truyền tải Stdio và Memory
# Với truyền tải từ xa như HTTP/SSE, nên dùng trực tiếp MCPClient
```

<strong>(3) Memory Transport - truyền tải trong bộ nhớ</strong>

Kịch bản phù hợp: kiểm thử đơn vị, phát triển nguyên mẫu nhanh

```python
from hello_agents.tools import MCPTool

# Dùng máy chủ minh họa tích hợp sẵn (truyền tải Memory)
mcp_tool = MCPTool()

# Liệt kê công cụ khả dụng
result = mcp_tool.run({"action": "list_tools"})
print(result)

# Gọi công cụ
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "add",
    "arguments": {"a": 10, "b": 20}
})
print(result)
```

<strong>(4) Stdio Transport - truyền tải qua đầu vào/đầu ra chuẩn</strong>

Kịch bản phù hợp: phát triển cục bộ, gỡ lỗi, máy chủ dạng script Python

```python
from hello_agents.tools import MCPTool

# Cách 1: dùng máy chủ Python tùy chỉnh
mcp_tool = MCPTool(server_command=["python", "my_mcp_server.py"])

# Cách 2: dùng máy chủ cộng đồng (hệ thống tệp)
mcp_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

# Liệt kê công cụ
result = mcp_tool.run({"action": "list_tools"})
print(result)

# Gọi công cụ
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "read_file",
    "arguments": {"path": "README.md"}
})
print(result)
```

<strong>(5) HTTP Transport - truyền tải HTTP</strong>

Kịch bản phù hợp: môi trường sản xuất, dịch vụ từ xa, kiến trúc microservice

```python
# Lưu ý: MCPTool chủ yếu dùng cho truyền tải Stdio và Memory
# Với truyền tải từ xa như HTTP/SSE, nên dùng MCPClient ở tầng thấp

import asyncio
from hello_agents.protocols import MCPClient

async def test_http_transport():
    # Kết nối tới máy chủ MCP HTTP từ xa
    client = MCPClient("http://api.example.com/mcp")

    async with client:
        # Lấy thông tin máy chủ
        tools = await client.list_tools()
        print(f"Công cụ của máy chủ từ xa: {len(tools)} công cụ")

        # Gọi công cụ từ xa
        result = await client.call_tool("process_data", {
            "data": "Hello, World!",
            "operation": "uppercase"
        })
        print(f"Kết quả xử lý từ xa: {result}")

# Lưu ý: cần có máy chủ MCP HTTP thực tế
# asyncio.run(test_http_transport())
```

<strong>(6) SSE Transport - truyền tải Server-Sent Events</strong>

Kịch bản phù hợp: giao tiếp thời gian thực, xử lý luồng, kết nối dài

```python
# Lưu ý: MCPTool chủ yếu dùng cho truyền tải Stdio và Memory
# Với truyền tải SSE, nên dùng MCPClient ở tầng thấp

import asyncio
from hello_agents.protocols import MCPClient

async def test_sse_transport():
    # Kết nối tới máy chủ MCP SSE
    client = MCPClient(
        "http://localhost:8080/sse",
        transport_type="sse"
    )

    async with client:
        # SSE đặc biệt phù hợp với xử lý luồng
        result = await client.call_tool("stream_process", {
            "input": "Yêu cầu xử lý lượng dữ liệu lớn",
            "stream": True
        })
        print(f"Kết quả xử lý luồng: {result}")

# Lưu ý: cần máy chủ MCP hỗ trợ SSE
# asyncio.run(test_sse_transport())
```

<strong>(7) StreamableHTTP Transport - truyền tải HTTP dạng luồng</strong>

Kịch bản phù hợp: kịch bản HTTP cần giao tiếp luồng hai chiều

```python
# Lưu ý: MCPTool chủ yếu dùng cho truyền tải Stdio và Memory
# Với truyền tải StreamableHTTP, nên dùng MCPClient ở tầng thấp

import asyncio
from hello_agents.protocols import MCPClient

async def test_streamable_http_transport():
    # Kết nối tới máy chủ MCP StreamableHTTP
    client = MCPClient(
        "http://localhost:8080/mcp",
        transport_type="streamable_http"
    )

    async with client:
        # Hỗ trợ giao tiếp luồng hai chiều
        tools = await client.list_tools()
        print(f"Công cụ của máy chủ StreamableHTTP: {len(tools)} công cụ")

# Lưu ý: cần máy chủ MCP hỗ trợ StreamableHTTP
# asyncio.run(test_streamable_http_transport())
```

### 10.2.4 Sử dụng công cụ MCP trong Agent

Phần trước chúng ta đã học cách dùng trực tiếp MCP client. Nhưng trong ứng dụng thực tế, chúng ta mong muốn Agent <strong>tự động</strong> gọi công cụ MCP hơn là viết mã gọi thủ công. HelloAgents cung cấp bộ bọc `MCPTool`, giúp máy chủ MCP tích hợp liền mạch vào chuỗi công cụ của Agent.

<strong>(1) Cơ chế tự động mở rộng của công cụ MCP</strong>

`MCPTool` của HelloAgents có một đặc tính: <strong>tự động mở rộng</strong>. Khi bạn thêm một công cụ MCP vào Agent, nó sẽ tự động mở rộng mọi công cụ mà máy chủ MCP cung cấp thành các công cụ độc lập, để Agent có thể gọi chúng như công cụ bình thường.

<strong>Cách 1: dùng máy chủ minh họa tích hợp sẵn</strong>

Ở phần trước chúng ta đã hiện thực hàm công cụ cho máy tính; ở đây hãy chuyển nó thành dịch vụ MCP. Đây là cách sử dụng đơn giản nhất.

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

agent = SimpleAgent(name="Trợ lý", llm=HelloAgentsLLM())

# Không cần cấu hình gì, tự động dùng máy chủ minh họa tích hợp sẵn
mcp_tool = MCPTool(name="calculator")
agent.add_tool(mcp_tool)
# ✅ Công cụ MCP 'calculator' đã được mở rộng thành 6 công cụ độc lập

# Agent có thể dùng trực tiếp các công cụ đã mở rộng
response = agent.run("Tính 25 nhân 16")
print(response)  # Đầu ra: kết quả của 25 nhân 16 là 400
```

<strong>Các công cụ sau khi tự động mở rộng</strong>:

- `calculator_add` - máy tính phép cộng
- `calculator_subtract` - máy tính phép trừ
- `calculator_multiply` - máy tính phép nhân

- `calculator_divide` - máy tính phép chia
- `calculator_greet` - lời chào thân thiện
- `calculator_get_system_info` - lấy thông tin hệ thống

Khi Agent gọi, chỉ cần cung cấp tham số, ví dụ: `[TOOL_CALL:calculator_multiply:a=25,b=16]`; hệ thống sẽ tự động xử lý chuyển đổi kiểu và lời gọi MCP.

<strong>Cách 2: kết nối tới máy chủ MCP bên ngoài</strong>

Trong dự án thực tế, bạn cần kết nối tới những máy chủ MCP mạnh mẽ hơn. Những máy chủ này có thể là:
- <strong>máy chủ chính thức do cộng đồng cung cấp</strong> (như hệ thống tệp, GitHub, cơ sở dữ liệu, v.v.)
- <strong>máy chủ tùy chỉnh do bạn tự viết</strong> (đóng gói logic nghiệp vụ)

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

agent = SimpleAgent(name="Trợ lý tệp", llm=HelloAgentsLLM())

# Ví dụ 1: kết nối tới máy chủ hệ thống tệp do cộng đồng cung cấp
fs_tool = MCPTool(
    name="filesystem",  # Chỉ định tên duy nhất
    description="Truy cập hệ thống tệp cục bộ",
    server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
)
agent.add_tool(fs_tool)

# Ví dụ 2: kết nối tới máy chủ MCP Python tùy chỉnh
# Về cách viết máy chủ MCP tùy chỉnh, hãy tham khảo mục 10.5
custom_tool = MCPTool(
    name="custom_server",  # Dùng tên khác
    description="Máy chủ logic nghiệp vụ tùy chỉnh",
    server_command=["python", "my_mcp_server.py"]
)
agent.add_tool(custom_tool)

# Agent giờ có thể tự động sử dụng các công cụ này!
response = agent.run("Hãy đọc tệp my_README.md và tóm tắt nội dung chính trong đó")
print(response)
```

Khi dùng nhiều máy chủ MCP, nhất định phải chỉ định `name` khác nhau cho mỗi MCPTool; `name` này sẽ được thêm làm tiền tố cho tên công cụ đã mở rộng để tránh xung đột. Ví dụ: `name="fs"` sẽ mở rộng thành `fs_read_file`, `fs_write_file`, v.v. Nếu bạn cần viết máy chủ MCP của riêng mình để đóng gói logic nghiệp vụ cụ thể, hãy tham khảo nội dung mục 10.5.

<strong>(2) Nguyên lý hoạt động của việc tự động mở rộng công cụ MCP</strong>

Hiểu cơ chế tự động mở rộng sẽ giúp bạn dùng công cụ MCP tốt hơn. Hãy đi sâu xem nó hoạt động thế nào:

```python
# Mã người dùng
fs_tool = MCPTool(name="fs", server_command=[...])
agent.add_tool(fs_tool)

# Những gì diễn ra bên trong:
# 1. MCPTool kết nối tới máy chủ, phát hiện 14 công cụ
# 2. Tạo bộ bọc cho từng công cụ:
#    - fs_read_text_file (tham số: path, tail, head)
#    - fs_write_file (tham số: path, content)
#    - ...
# 3. Đăng ký vào registry công cụ của Agent

# Agent gọi
response = agent.run("Đọc README.md")

# Bên trong Agent:
# 1. Nhận diện cần gọi fs_read_text_file
# 2. Sinh tham số: path=README.md
# 3. Bộ bọc chuyển sang định dạng MCP:
#    {"action": "call_tool", "tool_name": "read_text_file", "arguments": {"path": "README.md"}}
# 4. Gọi máy chủ MCP
# 5. Trả về nội dung tệp
```

Hệ thống sẽ tự động chuyển đổi kiểu dựa trên định nghĩa tham số của công cụ:

```python
# Agent gọi máy tính
agent.run("Tính 25 nhân 16")

# Agent sinh: a=25,b=16 (chuỗi)
# Hệ thống tự động chuyển thành: {"a": 25.0, "b": 16.0} (số)
# Máy chủ MCP nhận đúng kiểu số
```

<strong>(3) Ca thực hành: trợ lý tài liệu thông minh</strong>

Hãy xây dựng một trợ lý tài liệu thông minh hoàn chỉnh; ở đây chúng ta dùng một ví dụ điều phối đa Agent đơn giản để minh họa:

```python
"""
Trợ lý tài liệu thông minh với nhiều Agent phối hợp

Dùng hai SimpleAgent phân công phối hợp:
- Agent1: chuyên gia tìm kiếm GitHub
- Agent2: chuyên gia sinh tài liệu
"""
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool
from dotenv import load_dotenv

# Tải biến môi trường trong tệp .env
load_dotenv(dotenv_path="../HelloAgents/.env")

print("="*70)
print("Trợ lý tài liệu thông minh với nhiều Agent phối hợp")
print("="*70)

# ============================================================
# Agent 1: chuyên gia tìm kiếm GitHub
# ============================================================
print("\n[Bước 1] Tạo chuyên gia tìm kiếm GitHub...")

github_searcher = SimpleAgent(
    name="Chuyên gia tìm kiếm GitHub",
    llm=HelloAgentsLLM(),
    system_prompt="""Bạn là một chuyên gia tìm kiếm GitHub.
Nhiệm vụ của bạn là tìm kiếm kho GitHub và trả về kết quả.
Hãy trả về kết quả tìm kiếm rõ ràng, có cấu trúc, bao gồm:
- tên kho
- mô tả ngắn

Hãy giữ ngắn gọn, không thêm giải thích dư thừa."""
)

# Thêm công cụ GitHub
github_tool = MCPTool(
    name="gh",
    server_command=["npx", "-y", "@modelcontextprotocol/server-github"]
)
github_searcher.add_tool(github_tool)

# ============================================================
# Agent 2: chuyên gia sinh tài liệu
# ============================================================
print("\n[Bước 2] Tạo chuyên gia sinh tài liệu...")

document_writer = SimpleAgent(
    name="Chuyên gia sinh tài liệu",
    llm=HelloAgentsLLM(),
    system_prompt="""Bạn là một chuyên gia sinh tài liệu.
Nhiệm vụ của bạn là sinh báo cáo Markdown có cấu trúc dựa trên thông tin được cung cấp.

Báo cáo nên bao gồm:
- tiêu đề
- giới thiệu
- nội dung chính (liệt kê theo gạch đầu dòng, bao gồm tên dự án, mô tả, v.v.)
- tóm tắt

Hãy xuất trực tiếp nội dung báo cáo đầy đủ ở định dạng Markdown, không dùng công cụ để lưu."""
)

# Thêm công cụ hệ thống tệp
fs_tool = MCPTool(
    name="fs",
    server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
)
document_writer.add_tool(fs_tool)

# ============================================================
# Thực thi nhiệm vụ
# ============================================================
print("\n" + "="*70)
print("Bắt đầu thực thi nhiệm vụ...")
print("="*70)

try:
    # Bước 1: tìm kiếm GitHub
    print("\n[Bước 3] Agent1 tìm kiếm GitHub...")
    search_task = "Tìm kiếm các kho GitHub về 'AI agent', trả về 5 kết quả liên quan nhất"

    search_results = github_searcher.run(search_task)

    print("\nKết quả tìm kiếm:")
    print("-" * 70)
    print(search_results)
    print("-" * 70)

    # Bước 2: sinh báo cáo
    print("\n[Bước 4] Agent2 sinh báo cáo...")
    report_task = f"""
Dựa trên kết quả tìm kiếm GitHub sau, hãy sinh một báo cáo nghiên cứu ở định dạng Markdown:

{search_results}

Yêu cầu của báo cáo:
1. Tiêu đề: # Báo cáo nghiên cứu framework AI Agent
2. Giới thiệu: nêu rõ đây là khảo sát các dự án GitHub về AI Agent
3. Phát hiện chính: liệt kê các dự án tìm được và đặc điểm của chúng (bao gồm tên, mô tả, v.v.)
4. Tóm tắt: tóm tắt đặc điểm chung của các dự án này

Hãy xuất trực tiếp báo cáo đầy đủ ở định dạng Markdown.
"""

    report_content = document_writer.run(report_task)

    print("\nNội dung báo cáo:")
    print("=" * 70)
    print(report_content)
    print("=" * 70)

    # Bước 3: lưu báo cáo
    print("\n[Bước 5] Lưu báo cáo vào tệp...")
    import os
    try:
        with open("report.md", "w", encoding="utf-8") as f:
            f.write(report_content)
        print("✅ Báo cáo đã được lưu vào report.md")

        # Kiểm tra tệp
        file_size = os.path.getsize("report.md")
        print(f"✅ Kích thước tệp: {file_size} byte")
    except Exception as e:
        print(f"❌ Lưu thất bại: {e}")

    print("\n" + "="*70)
    print("Nhiệm vụ hoàn tất!")
    print("="*70)

except Exception as e:
    print(f"\n❌ Lỗi: {e}")
    import traceback
    traceback.print_exc()

```

Trong quá trình này, `github_searcher` sẽ gọi `gh_search_repositories` để tìm các dự án GitHub. Kết quả nhận được sẽ được trả về cho `document_writer` làm đầu vào, tiếp tục định hướng việc sinh báo cáo, và cuối cùng lưu báo cáo vào report.md.

### 10.2.5 Hệ sinh thái cộng đồng MCP

Một ưu điểm lớn của giao thức MCP là <strong>hệ sinh thái cộng đồng phong phú</strong>. Anthropic và các nhà phát triển cộng đồng đã tạo ra rất nhiều máy chủ MCP sẵn có, bao phủ đủ loại kịch bản như hệ thống tệp, cơ sở dữ liệu, dịch vụ API. Điều này có nghĩa bạn không cần viết adapter công cụ từ đầu mà có thể dùng trực tiếp những máy chủ đã được kiểm chứng này.

Dưới đây là ba kho tài nguyên của cộng đồng MCP:

1. <strong>Awesome MCP Servers</strong> (https://github.com/punkpeye/awesome-mcp-servers)
   - Danh sách tuyển chọn máy chủ MCP do cộng đồng duy trì
   - Bao gồm nhiều máy chủ bên thứ ba
   - Phân loại theo chức năng, dễ tìm kiếm

2. <strong>MCP Servers Website</strong> (https://mcpservers.org/)
   - Trang danh mục máy chủ MCP chính thức
   - Cung cấp chức năng tìm kiếm và lọc
   - Bao gồm hướng dẫn sử dụng và ví dụ

3. <strong>Official MCP Servers</strong> (https://github.com/modelcontextprotocol/servers)
   - Máy chủ do Anthropic duy trì chính thức
   - Chất lượng cao nhất, tài liệu đầy đủ nhất
   - Bao gồm hiện thực của các dịch vụ phổ biến

Bảng 10.5 và 10.6 giới thiệu các máy chủ MCP chính thức thường dùng và các máy chủ MCP phổ biến trong cộng đồng:

<div align="center">
  <p>Bảng 10.5 Các máy chủ MCP chính thức thường dùng</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-5.png" alt="" width="85%"/>
</div>

<div align="center">
  <p>Bảng 10.6 Các máy chủ MCP phổ biến trong cộng đồng</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-6.png" alt="" width="85%"/>
</div>

Dưới đây là một số ca khá thú vị để tham khảo:

1. <strong>Kiểm thử web tự động (Playwright)</strong>

   ```python
   # Agent có thể tự động:
   # - mở trình duyệt truy cập website
   # - điền biểu mẫu và gửi
   # - chụp ảnh màn hình để xác minh kết quả
   # - sinh báo cáo kiểm thử
   playwright_tool = MCPTool(
       name="playwright",
       server_command=["npx", "-y", "@playwright/mcp"]
   )
   ```

2. <strong>Trợ lý ghi chú thông minh (Obsidian + Perplexity)</strong>
   ```python
   # Agent có thể:
   # - tìm tin tức công nghệ mới nhất (Perplexity)
   # - sắp xếp thành ghi chú có cấu trúc
   # - lưu vào kho tri thức Obsidian
   # - tự động tạo liên kết giữa các ghi chú
   ```

3. <strong>Tự động hóa quản lý dự án (Jira + GitHub)</strong>
   ```python
   # Agent có thể:
   # - tạo task Jira từ GitHub Issue
   # - đồng bộ commit mã sang Jira
   # - tự động cập nhật tiến độ Sprint
   # - sinh báo cáo dự án
   ```

5. <strong>Quy trình sáng tạo nội dung (YouTube + Notion + Spotify)</strong>

   ```python
   # Agent có thể:
   # - lấy phụ đề video YouTube
   # - sinh tóm tắt nội dung
   # - lưu vào cơ sở dữ liệu Notion
   # - phát nhạc nền (Spotify)
   ```

Qua nội dung của mục này, hy vọng bạn sẽ khám phá thêm nhiều ca hiện thực MCP khác, và cũng hoan nghênh bạn gửi bài đóng góp cho Helloagents! Tiếp theo, hãy học giao thức A2A.

## 10.3 Thực hành giao thức A2A

A2A (Agent-to-Agent) là một giao thức hỗ trợ giao tiếp và phối hợp trực tiếp giữa các Agent.

### 10.3.1 Động cơ thiết kế giao thức

Giao thức MCP giải quyết tương tác giữa Agent và công cụ, còn giao thức A2A giải quyết vấn đề phối hợp giữa các Agent. Trong một nhiệm vụ cần nhiều Agent (như nhà nghiên cứu, người viết, biên tập viên) phối hợp, chúng cần giao tiếp, ủy thác nhiệm vụ, thương lượng năng lực và đồng bộ trạng thái.

Cách tiếp cận bộ điều phối trung tâm truyền thống (tô-pô hình sao) có ba vấn đề chính:

- <strong>Điểm lỗi đơn</strong>: bộ điều phối hỏng khiến toàn bộ hệ thống tê liệt.
- <strong>Nút thắt hiệu năng</strong>: mọi giao tiếp đều đi qua nút trung tâm, hạn chế khả năng đồng thời.
- <strong>Khó mở rộng</strong>: thêm hoặc sửa Agent đòi hỏi thay đổi logic trung tâm.

Giao thức A2A dùng kiến trúc ngang hàng (P2P) (tô-pô dạng lưới), cho phép Agent giao tiếp trực tiếp, giải quyết tận gốc các vấn đề trên. Cốt lõi của nó là hai khái niệm trừu tượng <strong>tác vụ (Task)</strong> và <strong>sản phẩm (Artifact)</strong>; đây là khác biệt lớn nhất so với MCP, như Bảng 10.7 trình bày.

<div align="center">
  <p>Bảng 10.7 Khái niệm cốt lõi của A2A</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-7.png" alt="" width="85%"/>
</div>

Để quản lý quá trình phối hợp, A2A định nghĩa vòng đời chuẩn hóa cho tác vụ, bao gồm các trạng thái như tạo mới, thương lượng, ủy nhiệm, đang thực thi, hoàn thành, thất bại, như Hình 10.7 minh họa.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-7.png" alt="" width="85%"/>
  <p>Hình 10.7 Vòng đời tác vụ của A2A</p>
</div>


Cơ chế này cho phép Agent thương lượng tác vụ, theo dõi tiến độ và xử lý ngoại lệ.

Vòng đời yêu cầu A2A là một chuỗi, mô tả chi tiết bốn bước chính mà yêu cầu tuân theo: phát hiện đại lý (agent), xác thực danh tính, API gửi tin nhắn và API gửi tin nhắn dạng luồng. Hình 10.8 dưới đây tham khảo lưu đồ từ trang chính thức để trình bày quy trình thao tác, minh họa tương tác giữa client, máy chủ A2A và máy chủ xác thực danh tính.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-8.png" alt="" width="85%"/>
  <p>Hình 10.8 Vòng đời yêu cầu A2A</p>
</div>

### 10.3.2 Thực hành giao thức A2A

Hiện nay phần lớn hiện thực A2A chỉ là `Sample Code`, và ngay cả khi có hiện thực Python thì cũng khá rườm rà; vì vậy ở đây chúng ta chỉ mô phỏng tư tưởng của giao thức, kế thừa một phần chức năng thông qua A2A-SDK.

<strong>(2) Tạo một Agent A2A đơn giản</strong>

Hãy tạo một Agent A2A, vẫn dùng ca máy tính để minh họa:

```python
from hello_agents.protocols.a2a.implementation import A2AServer, A2A_AVAILABLE

def create_calculator_agent():
    """Tạo một Agent máy tính"""
    if not A2A_AVAILABLE:
        print("❌ Chưa cài A2A SDK, hãy chạy: pip install a2a-sdk")
        return None

    print("🧮 Tạo Agent máy tính")

    # Tạo máy chủ A2A
    calculator = A2AServer(
        name="calculator-agent",
        description="Agent tính toán toán học chuyên nghiệp",
        version="1.0.0",
        capabilities={
            "math": ["addition", "subtraction", "multiplication", "division"],
            "advanced": ["power", "sqrt", "factorial"]
        }
    )

    # Thêm kỹ năng tính toán cơ bản
    @calculator.skill("add")
    def add_numbers(query: str) -> str:
        """Tính phép cộng"""
        try:
            # Phân tích đơn giản định dạng "tính 5 + 3"
            parts = query.replace("tính", "").replace("cộng", "+").replace("cộng với", "+")
            if "+" in parts:
                numbers = [float(x.strip()) for x in parts.split("+")]
                result = sum(numbers)
                return f"Kết quả tính toán: {' + '.join(map(str, numbers))} = {result}"
            else:
                return "Hãy dùng định dạng: tính 5 + 3"
        except Exception as e:
            return f"Lỗi tính toán: {e}"

    @calculator.skill("multiply")
    def multiply_numbers(query: str) -> str:
        """Tính phép nhân"""
        try:
            parts = query.replace("tính", "").replace("nhân", "*").replace("×", "*")
            if "*" in parts:
                numbers = [float(x.strip()) for x in parts.split("*")]
                result = 1
                for num in numbers:
                    result *= num
                return f"Kết quả tính toán: {' × '.join(map(str, numbers))} = {result}"
            else:
                return "Hãy dùng định dạng: tính 5 * 3"
        except Exception as e:
            return f"Lỗi tính toán: {e}"

    @calculator.skill("info")
    def get_info(query: str) -> str:
        """Lấy thông tin Agent"""
        return f"Tôi là {calculator.name}, có thể thực hiện tính toán toán học cơ bản. Các kỹ năng được hỗ trợ: {list(calculator.skills.keys())}"

    print(f"✅ Tạo Agent máy tính thành công, các kỹ năng được hỗ trợ: {list(calculator.skills.keys())}")
    return calculator

# Tạo Agent
calc_agent = create_calculator_agent()
if calc_agent:
    # Kiểm thử kỹ năng
    print("\n🧪 Kiểm thử kỹ năng Agent:")
    test_queries = [
        "lấy thông tin",
        "tính 10 + 5",
        "tính 6 * 7"
    ]

    for query in test_queries:
        if "thông tin" in query:
            result = calc_agent.skills["info"](query)
        elif "+" in query:
            result = calc_agent.skills["add"](query)
        elif "*" in query or "×" in query:
            result = calc_agent.skills["multiply"](query)
        else:
            result = "Loại truy vấn không xác định"

        print(f"  📝 Truy vấn: {query}")
        print(f"  🤖 Phản hồi: {result}")
        print()
```

<strong>(2) Agent A2A tùy chỉnh</strong>

Bạn cũng có thể tạo Agent A2A của riêng mình; ở đây chỉ là minh họa đơn giản:

```python
from hello_agents.protocols.a2a.implementation import A2AServer, A2A_AVAILABLE

def create_custom_agent():
    """Tạo Agent tùy chỉnh"""
    if not A2A_AVAILABLE:
        print("Hãy cài A2A SDK trước: pip install a2a-sdk")
        return None

    # Tạo Agent
    agent = A2AServer(
        name="my-custom-agent",
        description="Agent tùy chỉnh của tôi",
        capabilities={"custom": ["skill1", "skill2"]}
    )

    # Thêm kỹ năng
    @agent.skill("greet")
    def greet_user(name: str) -> str:
        """Chào người dùng"""
        return f"Xin chào, {name}! Tôi là Agent tùy chỉnh."

    @agent.skill("calculate")
    def simple_calculate(expression: str) -> str:
        """Tính toán đơn giản"""
        try:
            # Tính toán an toàn (chỉ hỗ trợ phép toán cơ bản)
            allowed_chars = set('0123456789+-*/(). ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return f"Kết quả tính toán: {expression} = {result}"
            else:
                return "Lỗi: chỉ hỗ trợ phép toán cơ bản"
        except Exception as e:
            return f"Lỗi tính toán: {e}"

    return agent

# Tạo và kiểm thử Agent tùy chỉnh
custom_agent = create_custom_agent()
if custom_agent:
    # Kiểm thử kỹ năng
    print("Kiểm thử kỹ năng chào hỏi:")
    result1 = custom_agent.skills["greet"]("Nguyễn Văn A")
    print(result1)

    print("\nKiểm thử kỹ năng tính toán:")
    result2 = custom_agent.skills["calculate"]("10 + 5 * 2")
    print(result2)
```

### 10.3.3 Sử dụng công cụ A2A của HelloAgents

HelloAgents cung cấp giao diện công cụ A2A thống nhất.

<strong>(1) Tạo phía máy chủ A2A Agent</strong>

Trước tiên, hãy tạo một máy chủ Agent:

```python
from hello_agents.protocols import A2AServer
import threading
import time

# Tạo dịch vụ Agent nghiên cứu
researcher = A2AServer(
    name="researcher",
    description="Agent phụ trách tìm kiếm và phân tích tài liệu",
    version="1.0.0"
)

# Định nghĩa kỹ năng
@researcher.skill("research")
def handle_research(text: str) -> str:
    """Xử lý yêu cầu nghiên cứu"""
    import re
    match = re.search(r'research\s+(.+)', text, re.IGNORECASE)
    topic = match.group(1).strip() if match else text

    # Logic nghiên cứu thực tế (đơn giản hóa ở đây)
    result = {
        "topic": topic,
        "findings": f"Kết quả nghiên cứu về {topic}...",
        "sources": ["Nguồn 1", "Nguồn 2", "Nguồn 3"]
    }
    return str(result)

# Khởi động dịch vụ ở chế độ nền
def start_server():
    researcher.run(host="localhost", port=5000)

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("✅ Dịch vụ Agent nghiên cứu đã khởi động tại http://localhost:5000")

    # Giữ chương trình chạy
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDịch vụ đã dừng")
```

<strong>(2) Tạo client A2A Agent</strong>

Bây giờ, hãy tạo một client để giao tiếp với phía máy chủ:

```python
from hello_agents.protocols import A2AClient

# Tạo client kết nối tới Agent nghiên cứu
client = A2AClient("http://localhost:5000")

# Gửi yêu cầu nghiên cứu
response = client.execute_skill("research", "research ứng dụng AI trong lĩnh vực y tế")
print(f"Nhận phản hồi: {response.get('result')}")

# Đầu ra:
# Nhận phản hồi: {'topic': 'ứng dụng AI trong lĩnh vực y tế', 'findings': 'Kết quả nghiên cứu về ứng dụng AI trong lĩnh vực y tế...', 'sources': ['Nguồn 1', 'Nguồn 2', 'Nguồn 3']}
```

<strong>(3) Tạo mạng Agent</strong>

Với phối hợp nhiều Agent, chúng ta có thể cho nhiều Agent kết nối với nhau:

```python
from hello_agents.protocols import A2AServer, A2AClient
import threading
import time

# 1. Tạo nhiều dịch vụ Agent
researcher = A2AServer(
    name="researcher",
    description="Nhà nghiên cứu"
)

@researcher.skill("research")
def do_research(text: str) -> str:
    import re
    match = re.search(r'research\s+(.+)', text, re.IGNORECASE)
    topic = match.group(1).strip() if match else text
    return str({"topic": topic, "findings": f"Kết quả nghiên cứu về {topic}"})

writer = A2AServer(
    name="writer",
    description="Người viết"
)

@writer.skill("write")
def write_article(text: str) -> str:
    import re
    match = re.search(r'write\s+(.+)', text, re.IGNORECASE)
    content = match.group(1).strip() if match else text

    # Thử phân tích dữ liệu nghiên cứu
    try:
        data = eval(content)
        topic = data.get("topic", "Chủ đề không xác định")
        findings = data.get("findings", "Không có kết quả nghiên cứu")
    except:
        topic = "Chủ đề không xác định"
        findings = content

    return f"# {topic}\n\nDựa trên nghiên cứu: {findings}\n\nNội dung bài viết..."

editor = A2AServer(
    name="editor",
    description="Biên tập viên"
)

@editor.skill("edit")
def edit_article(text: str) -> str:
    import re
    match = re.search(r'edit\s+(.+)', text, re.IGNORECASE)
    article = match.group(1).strip() if match else text

    result = {
        "article": article + "\n\n[Đã biên tập tối ưu]",
        "feedback": "Chất lượng bài viết tốt",
        "approved": True
    }
    return str(result)

# 2. Khởi động mọi dịch vụ
threading.Thread(target=lambda: researcher.run(port=5000), daemon=True).start()
threading.Thread(target=lambda: writer.run(port=5001), daemon=True).start()
threading.Thread(target=lambda: editor.run(port=5002), daemon=True).start()
time.sleep(2)  # Chờ dịch vụ khởi động

# 3. Tạo client kết nối tới từng Agent
researcher_client = A2AClient("http://localhost:5000")
writer_client = A2AClient("http://localhost:5001")
editor_client = A2AClient("http://localhost:5002")

# 4. Quy trình phối hợp
def create_content(topic):
    # Bước 1: nghiên cứu
    research = researcher_client.execute_skill("research", f"research {topic}")
    research_data = research.get('result', '')

    # Bước 2: viết
    article = writer_client.execute_skill("write", f"write {research_data}")
    article_content = article.get('result', '')

    # Bước 3: biên tập
    final = editor_client.execute_skill("edit", f"edit {article_content}")
    return final.get('result', '')

# Sử dụng
result = create_content("ứng dụng AI trong lĩnh vực y tế")
print(f"\nKết quả cuối cùng:\n{result}")
```

### 10.3.4 Sử dụng công cụ A2A trong Agent

Bây giờ hãy xem cách tích hợp A2A vào Agent của HelloAgents.

<strong>(1) Sử dụng bộ bọc A2ATool</strong>

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import A2ATool
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

# Giả sử đã có một dịch vụ Agent nghiên cứu chạy tại http://localhost:5000

# Tạo Agent điều phối
coordinator = SimpleAgent(name="Điều phối viên", llm=llm)

# Thêm công cụ A2A, kết nối tới Agent nghiên cứu
researcher_tool = A2ATool(
    name="researcher",
    description="Agent nghiên cứu, có thể tìm kiếm và phân tích tài liệu",
    agent_url="http://localhost:5000"
)
coordinator.add_tool(researcher_tool)

# Điều phối viên có thể gọi Agent nghiên cứu
response = coordinator.run("Hãy nhờ nhà nghiên cứu giúp tôi nghiên cứu ứng dụng AI trong lĩnh vực giáo dục")
print(response)
```

<strong>(2) Ca thực hành: hệ thống chăm sóc khách hàng thông minh</strong>

Hãy xây dựng một hệ thống chăm sóc khách hàng thông minh hoàn chỉnh, gồm ba Agent:
- <strong>Lễ tân</strong>: phân tích loại vấn đề của khách hàng
- <strong>Chuyên gia kỹ thuật</strong>: trả lời câu hỏi kỹ thuật
- <strong>Tư vấn bán hàng</strong>: trả lời câu hỏi về bán hàng

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import A2ATool
from hello_agents.protocols import A2AServer
import threading
import time
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

# 1. Tạo dịch vụ Agent chuyên gia kỹ thuật
tech_expert = A2AServer(
    name="tech_expert",
    description="Chuyên gia kỹ thuật, trả lời câu hỏi kỹ thuật"
)

@tech_expert.skill("answer")
def answer_tech_question(text: str) -> str:
    import re
    match = re.search(r'answer\s+(.+)', text, re.IGNORECASE)
    question = match.group(1).strip() if match else text
    # Trong ứng dụng thực tế, ở đây sẽ gọi LLM hoặc kho tri thức
    return f"Trả lời kỹ thuật: về '{question}', tôi khuyên bạn xem tài liệu kỹ thuật của chúng tôi..."

# 2. Tạo dịch vụ Agent tư vấn bán hàng
sales_advisor = A2AServer(
    name="sales_advisor",
    description="Tư vấn bán hàng, trả lời câu hỏi bán hàng"
)

@sales_advisor.skill("answer")
def answer_sales_question(text: str) -> str:
    import re
    match = re.search(r'answer\s+(.+)', text, re.IGNORECASE)
    question = match.group(1).strip() if match else text
    return f"Trả lời bán hàng: về '{question}', chúng tôi có ưu đãi đặc biệt..."

# 3. Khởi động dịch vụ
threading.Thread(target=lambda: tech_expert.run(port=6000), daemon=True).start()
threading.Thread(target=lambda: sales_advisor.run(port=6001), daemon=True).start()
time.sleep(2)

# 4. Tạo Agent lễ tân (dùng SimpleAgent của HelloAgents)
receptionist = SimpleAgent(
    name="Lễ tân",
    llm=llm,
    system_prompt="""Bạn là lễ tân chăm sóc khách hàng, phụ trách:
1. Phân tích loại vấn đề của khách hàng (vấn đề kỹ thuật hoặc vấn đề bán hàng)
2. Chuyển vấn đề cho chuyên gia tương ứng
3. Tổng hợp câu trả lời của chuyên gia và trả về cho khách hàng

Hãy giữ thái độ lịch sự và chuyên nghiệp."""
)

# Thêm công cụ chuyên gia kỹ thuật
tech_tool = A2ATool(
    agent_url="http://localhost:6000",
    name="tech_expert",
    description="Chuyên gia kỹ thuật, trả lời các câu hỏi liên quan đến kỹ thuật"
)
receptionist.add_tool(tech_tool)

# Thêm công cụ tư vấn bán hàng
sales_tool = A2ATool(
    agent_url="http://localhost:6001",
    name="sales_advisor",
    description="Tư vấn bán hàng, trả lời câu hỏi về giá, mua hàng"
)
receptionist.add_tool(sales_tool)

# 5. Xử lý tư vấn khách hàng
def handle_customer_query(query):
    print(f"\nTư vấn khách hàng: {query}")
    print("=" * 50)
    response = receptionist.run(query)
    print(f"\nPhản hồi chăm sóc khách hàng: {response}")
    print("=" * 50)

# Kiểm thử các loại câu hỏi khác nhau
if __name__ == "__main__":
    handle_customer_query("API của các bạn được gọi như thế nào?")
    handle_customer_query("Giá của phiên bản doanh nghiệp là bao nhiêu?")
    handle_customer_query("Làm sao tích hợp vào dự án Python của tôi?")
```

<strong>(3) Cách dùng nâng cao: thương lượng giữa các Agent</strong>

Giao thức A2A còn hỗ trợ cơ chế thương lượng giữa các Agent:

```python
from hello_agents.protocols import A2AServer, A2AClient
import threading
import time

# Tạo hai Agent cần thương lượng
agent1 = A2AServer(
    name="agent1",
    description="Agent 1"
)

@agent1.skill("propose")
def handle_proposal(text: str) -> str:
    """Xử lý đề xuất thương lượng"""
    import re

    # Phân tích đề xuất
    match = re.search(r'propose\s+(.+)', text, re.IGNORECASE)
    proposal_str = match.group(1).strip() if match else text

    try:
        proposal = eval(proposal_str)
        task = proposal.get("task")
        deadline = proposal.get("deadline")

        # Đánh giá đề xuất
        if deadline >= 7:  # Cần ít nhất 7 ngày
            result = {"accepted": True, "message": "Chấp nhận đề xuất"}
        else:
            result = {
                "accepted": False,
                "message": "Thời gian quá gấp",
                "counter_proposal": {"deadline": 7}
            }
        return str(result)
    except:
        return str({"accepted": False, "message": "Định dạng đề xuất không hợp lệ"})

agent2 = A2AServer(
    name="agent2",
    description="Agent 2"
)

@agent2.skill("negotiate")
def negotiate_task(text: str) -> str:
    """Khởi tạo thương lượng"""
    import re

    # Phân tích nhiệm vụ và hạn chót
    match = re.search(r'negotiate\s+task:(.+?)\s+deadline:(\d+)', text, re.IGNORECASE)
    if match:
        task = match.group(1).strip()
        deadline = int(match.group(2))

        # Gửi đề xuất cho agent1
        proposal = {"task": task, "deadline": deadline}
        return str({"status": "negotiating", "proposal": proposal})
    else:
        return str({"status": "error", "message": "Yêu cầu thương lượng không hợp lệ"})

# Khởi động dịch vụ
threading.Thread(target=lambda: agent1.run(port=7000), daemon=True).start()
threading.Thread(target=lambda: agent2.run(port=7001), daemon=True).start()
```

## 10.4 Thực hành giao thức ANP

Sau khi giao thức MCP đã giải quyết gọi công cụ và giao thức A2A đã giải quyết phối hợp ngang hàng giữa các Agent, giao thức ANP tập trung giải quyết vấn đề quản lý Agent trong môi trường mạng mở, quy mô lớn.

Trong mục 10.2 và 10.3, chúng ta đã học MCP (truy cập công cụ) và A2A (phối hợp Agent). Bây giờ, hãy học giao thức ANP (Agent Network Protocol), vốn tập trung vào việc xây dựng <strong>mạng Agent quy mô lớn và mở</strong>.

### 10.4.1 Mục tiêu của giao thức

Khi trong một mạng tồn tại rất nhiều Agent với chức năng khác nhau (ví dụ xử lý ngôn ngữ tự nhiên, nhận dạng hình ảnh, phân tích dữ liệu, v.v.), hệ thống sẽ đối mặt với một loạt thách thức:

- <strong>Phát hiện dịch vụ</strong>: khi nhiệm vụ mới đến, làm sao nhanh chóng tìm được Agent có thể xử lý nhiệm vụ đó?
- <strong>Định tuyến thông minh</strong>: nếu nhiều Agent đều xử lý được cùng một nhiệm vụ, làm sao chọn Agent phù hợp nhất (ví dụ theo tải, chi phí) và phân công nhiệm vụ cho nó?
- <strong>Mở rộng động</strong>: làm sao để Agent mới gia nhập mạng được các thành viên khác phát hiện và gọi?

Mục tiêu thiết kế của ANP chính là cung cấp một bộ cơ chế chuẩn hóa để giải quyết các vấn đề phát hiện dịch vụ, chọn tuyến và mở rộng mạng nêu trên.

Để hiện thực mục tiêu thiết kế, ANP định nghĩa các khái niệm cốt lõi sau, như Bảng 10.8 trình bày:

<div align="center">
  <p>Bảng 10.8 Khái niệm cốt lõi của ANP</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-8.png" alt="" width="85%"/>
</div>

Chúng ta cũng mượn [hướng dẫn nhập môn](https://github.com/agent-network-protocol/AgentNetworkProtocol/blob/main/docs/chinese/ANP入门指南.md) chính thức để giới thiệu thiết kế kiến trúc của ANP, như Hình 10.9 minh họa

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-9.png" alt="" width="85%"/>
  <p>Hình 10.9 Toàn cảnh quy trình ANP</p>
</div>


Trong lưu đồ này, chủ yếu bao gồm các bước sau:

<strong>1. Phát hiện và khớp dịch vụ:</strong> Trước tiên, Agent A thông qua một dịch vụ phát hiện công khai, truy vấn dựa trên mô tả ngữ nghĩa hoặc chức năng, để định vị Agent B phù hợp với nhu cầu nhiệm vụ của mình. Dịch vụ phát hiện này xây dựng chỉ mục bằng cách thu thập trước các endpoint chuẩn (`.well-known/agent-descriptions`) mà các Agent công bố ra ngoài, từ đó hiện thực khớp động giữa bên cần dịch vụ và bên cung cấp dịch vụ.

<strong>2. Xác thực danh tính dựa trên DID:</strong> Khi bắt đầu tương tác, Agent A dùng khóa riêng của mình để ký yêu cầu chứa DID của bản thân. Sau khi Agent B nhận được, nó phân giải DID này để lấy khóa công khai tương ứng, rồi dùng đó xác minh tính xác thực của chữ ký và tính toàn vẹn của yêu cầu, từ đó thiết lập giao tiếp tin cậy giữa hai bên.

<strong>3. Thực thi dịch vụ chuẩn hóa:</strong> Sau khi xác thực danh tính thành công, Agent B phản hồi yêu cầu; hai bên trao đổi dữ liệu hoặc gọi dịch vụ (như đặt chỗ, truy vấn, v.v.) theo giao diện và định dạng dữ liệu chuẩn đã định nghĩa trước. Quy trình tương tác chuẩn hóa là nền tảng của khả năng tương tác xuyên nền tảng, xuyên hệ thống.

Tóm lại, cốt lõi của cơ chế này là dùng DID để xây dựng nền tảng tin cậy phi tập trung, và nhờ giao thức mô tả chuẩn hóa để hiện thực phát hiện dịch vụ động. Cách tiếp cận này cho phép Agent hình thành mạng phối hợp trên Internet một cách an toàn, hiệu quả mà không cần bộ điều phối trung tâm.

### 10.4.2 Sử dụng phát hiện dịch vụ ANP

<strong>(1) Tạo trung tâm phát hiện dịch vụ</strong>

```python
from hello_agents.protocols import ANPDiscovery, register_service

# Tạo trung tâm phát hiện dịch vụ
discovery = ANPDiscovery()

# Đăng ký dịch vụ Agent
register_service(
    discovery=discovery,
    service_id="nlp_agent_1",
    service_name="Chuyên gia xử lý NLP A",
    service_type="nlp",
    capabilities=["text_analysis", "sentiment_analysis", "ner"],
    endpoint="http://localhost:8001",
    metadata={"load": 0.3, "price": 0.01, "version": "1.0.0"}
)

register_service(
    discovery=discovery,
    service_id="nlp_agent_2",
    service_name="Chuyên gia xử lý NLP B",
    service_type="nlp",
    capabilities=["text_analysis", "translation"],
    endpoint="http://localhost:8002",
    metadata={"load": 0.7, "price": 0.02, "version": "1.1.0"}
)

print("✅ Đăng ký dịch vụ hoàn tất")
```

<strong>(2) Phát hiện dịch vụ</strong>

```python
from hello_agents.protocols import discover_service

# Tìm theo loại
nlp_services = discover_service(discovery, service_type="nlp")
print(f"Tìm thấy {len(nlp_services)} dịch vụ NLP")

# Chọn dịch vụ có tải thấp nhất
best_service = min(nlp_services, key=lambda s: s.metadata.get("load", 1.0))
print(f"Dịch vụ tốt nhất: {best_service.service_name} (tải: {best_service.metadata['load']})")
```

<strong>(3) Xây dựng mạng Agent</strong>

```python
from hello_agents.protocols import ANPNetwork

# Tạo mạng
network = ANPNetwork(network_id="ai_cluster")

# Thêm nút
for service in discovery.list_all_services():
    network.add_node(service.service_id, service.endpoint)

# Thiết lập kết nối (khớp theo năng lực)
network.connect_nodes("nlp_agent_1", "nlp_agent_2")

stats = network.get_network_stats()
print(f"✅ Xây dựng mạng hoàn tất, tổng {stats['total_nodes']} nút")
```

### 10.4.3 Ca thực hành

Hãy xây dựng một hệ thống lập lịch nhiệm vụ phân tán hoàn chỉnh:

```python
from hello_agents.protocols import ANPDiscovery, register_service
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools.builtin import ANPTool
import random
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

# 1. Tạo trung tâm phát hiện dịch vụ
discovery = ANPDiscovery()

# 2. Đăng ký nhiều nút tính toán
for i in range(10):
    register_service(
        discovery=discovery,
        service_id=f"compute_node_{i}",
        service_name=f"Nút tính toán {i}",
        service_type="compute",
        capabilities=["data_processing", "ml_training"],
        endpoint=f"http://node{i}:8000",
        metadata={
            "load": random.uniform(0.1, 0.9),
            "cpu_cores": random.choice([4, 8, 16]),
            "memory_gb": random.choice([16, 32, 64]),
            "gpu": random.choice([True, False])
        }
    )

print(f"✅ Đã đăng ký {len(discovery.list_all_services())} nút tính toán")

# 3. Tạo Agent lập lịch nhiệm vụ
scheduler = SimpleAgent(
    name="Bộ lập lịch nhiệm vụ",
    llm=llm,
    system_prompt="""Bạn là một bộ lập lịch nhiệm vụ thông minh, phụ trách:
1. Phân tích nhu cầu nhiệm vụ
2. Chọn nút tính toán phù hợp nhất
3. Phân công nhiệm vụ

Khi chọn nút, hãy cân nhắc: tải, số lõi CPU, bộ nhớ, GPU và các yếu tố khác."""
)

# Thêm công cụ ANP
anp_tool = ANPTool(
    name="service_discovery",
    description="Công cụ phát hiện dịch vụ, có thể tìm và chọn nút tính toán",
    discovery=discovery
)
scheduler.add_tool(anp_tool)

# 4. Phân công nhiệm vụ thông minh
def assign_task(task_description):
    print(f"\nNhiệm vụ: {task_description}")
    print("=" * 50)

    # Để Agent thông minh chọn nút
    response = scheduler.run(f"""
    Hãy chọn nút tính toán phù hợp nhất cho nhiệm vụ sau:
    {task_description}

    Yêu cầu:
    1. Liệt kê mọi nút khả dụng
    2. Phân tích đặc điểm của từng nút
    3. Chọn nút phù hợp nhất
    4. Giải thích lý do lựa chọn
    """)

    print(response)
    print("=" * 50)

# Kiểm thử các loại nhiệm vụ khác nhau
assign_task("Huấn luyện một mô hình học sâu lớn, cần hỗ trợ GPU")
assign_task("Xử lý lượng lớn dữ liệu văn bản, cần nhiều bộ nhớ")
assign_task("Chạy nhiệm vụ phân tích dữ liệu nhẹ")
```

Đây là một ví dụ cân bằng tải

```python
from hello_agents.protocols import ANPDiscovery, register_service
import random

# Tạo trung tâm phát hiện dịch vụ
discovery = ANPDiscovery()

# Đăng ký nhiều dịch vụ cùng loại
for i in range(5):
    register_service(
        discovery=discovery,
        service_id=f"api_server_{i}",
        service_name=f"Máy chủ API {i}",
        service_type="api",
        capabilities=["rest_api"],
        endpoint=f"http://api{i}:8000",
        metadata={"load": random.uniform(0.1, 0.9)}
    )

# Hàm cân bằng tải
def get_best_server():
    """Chọn máy chủ có tải thấp nhất"""
    servers = discovery.discover_services(service_type="api")
    if not servers:
        return None

    best = min(servers, key=lambda s: s.metadata.get("load", 1.0))
    return best

# Mô phỏng phân bổ yêu cầu
for i in range(10):
    server = get_best_server()
    print(f"Yêu cầu {i+1} -> {server.service_name} (tải: {server.metadata['load']:.2f})")

    # Cập nhật tải (mô phỏng)
    server.metadata["load"] += 0.1
```

## 10.5 Xây dựng máy chủ MCP tùy chỉnh

Ở các phần trước, chúng ta đã học cách dùng dịch vụ MCP có sẵn, đồng thời cũng hiểu đặc điểm của các giao thức khác nhau. Bây giờ, hãy học cách xây dựng máy chủ MCP của riêng mình.

### 10.5.1 Tạo máy chủ MCP đầu tiên của bạn

<strong>(1) Vì sao cần xây dựng máy chủ MCP tùy chỉnh?</strong>

Dù có thể dùng trực tiếp các dịch vụ MCP công khai, trong nhiều kịch bản ứng dụng thực tế vẫn cần xây dựng máy chủ MCP tùy chỉnh để đáp ứng nhu cầu cụ thể.

Các động cơ chính bao gồm:

- <strong>Đóng gói logic nghiệp vụ</strong>: đóng gói những quy trình nghiệp vụ đặc thù hoặc thao tác phức tạp bên trong doanh nghiệp thành công cụ MCP chuẩn hóa để Agent gọi thống nhất.
- <strong>Truy cập dữ liệu riêng tư</strong>: tạo một giao diện hoặc proxy an toàn, có kiểm soát để truy cập cơ sở dữ liệu nội bộ, API hoặc nguồn dữ liệu riêng tư khác không thể công bố ra Internet.
- <strong>Tối ưu hiệu năng chuyên biệt</strong>: tối ưu sâu cho kịch bản gọi tần suất cao hoặc có yêu cầu khắt khe về độ trễ phản hồi.
- <strong>Mở rộng chức năng tùy biến</strong>: hiện thực những chức năng mà dịch vụ MCP tiêu chuẩn không cung cấp, ví dụ tích hợp mô hình thuật toán độc quyền hoặc kết nối thiết bị phần cứng đặc thù.

<strong>(2) Ca giảng dạy: máy chủ MCP tra cứu thời tiết</strong>

Hãy bắt đầu từ một máy chủ tra cứu thời tiết đơn giản, từng bước học phát triển máy chủ MCP:

```python
#!/usr/bin/env python3
"""Máy chủ MCP tra cứu thời tiết"""

import json
import requests
import os
from datetime import datetime
from typing import Dict, Any
from hello_agents.protocols import MCPServer

# Tạo máy chủ MCP
weather_server = MCPServer(name="weather-server", description="Dịch vụ tra cứu thời tiết thực tế")

CITY_MAP = {
    "Bắc Kinh": "Beijing", "Thượng Hải": "Shanghai", "Quảng Châu": "Guangzhou",
    "Thâm Quyến": "Shenzhen", "Hàng Châu": "Hangzhou", "Thành Đô": "Chengdu",
    "Trùng Khánh": "Chongqing", "Vũ Hán": "Wuhan", "Tây An": "Xi'an",
    "Nam Kinh": "Nanjing", "Thiên Tân": "Tianjin", "Tô Châu": "Suzhou"
}


def get_weather_data(city: str) -> Dict[str, Any]:
    """Lấy dữ liệu thời tiết từ wttr.in"""
    city_en = CITY_MAP.get(city, city)
    url = f"https://wttr.in/{city_en}?format=j1"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    current = data["current_condition"][0]

    return {
        "city": city,
        "temperature": float(current["temp_C"]),
        "feels_like": float(current["FeelsLikeC"]),
        "humidity": int(current["humidity"]),
        "condition": current["weatherDesc"][0]["value"],
        "wind_speed": round(float(current["windspeedKmph"]) / 3.6, 1),
        "visibility": float(current["visibility"]),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# Định nghĩa hàm công cụ
def get_weather(city: str) -> str:
    """Lấy thời tiết hiện tại của thành phố chỉ định"""
    try:
        weather_data = get_weather_data(city)
        return json.dumps(weather_data, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "city": city}, ensure_ascii=False)


def list_supported_cities() -> str:
    """Liệt kê mọi thành phố được hỗ trợ"""
    result = {"cities": list(CITY_MAP.keys()), "count": len(CITY_MAP)}
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_server_info() -> str:
    """Lấy thông tin máy chủ"""
    info = {
        "name": "Weather MCP Server",
        "version": "1.0.0",
        "tools": ["get_weather", "list_supported_cities", "get_server_info"]
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


# Đăng ký công cụ vào máy chủ
weather_server.add_tool(get_weather)
weather_server.add_tool(list_supported_cities)
weather_server.add_tool(get_server_info)


if __name__ == "__main__":
    weather_server.run()
```

<strong>(3) Kiểm thử máy chủ MCP tùy chỉnh</strong>

Sau đó tạo script kiểm thử:

```python
#!/usr/bin/env python3
"""Kiểm thử máy chủ MCP tra cứu thời tiết"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'HelloAgents'))
from hello_agents.protocols.mcp.client import MCPClient


async def test_weather_server():
    server_script = os.path.join(os.path.dirname(__file__), "14_weather_mcp_server.py")
    client = MCPClient(["python", server_script])

    try:
        async with client:
            # Kiểm thử 1: lấy thông tin máy chủ
            info = json.loads(await client.call_tool("get_server_info", {}))
            print(f"Máy chủ: {info['name']} v{info['version']}")

            # Kiểm thử 2: liệt kê thành phố được hỗ trợ
            cities = json.loads(await client.call_tool("list_supported_cities", {}))
            print(f"Thành phố được hỗ trợ: {cities['count']}")

            # Kiểm thử 3: tra thời tiết Bắc Kinh
            weather = json.loads(await client.call_tool("get_weather", {"city": "Bắc Kinh"}))
            if "error" not in weather:
                print(f"\nThời tiết Bắc Kinh: {weather['temperature']}°C, {weather['condition']}")

            # Kiểm thử 4: tra thời tiết Thâm Quyến
            weather = json.loads(await client.call_tool("get_weather", {"city": "Thâm Quyến"}))
            if "error" not in weather:
                print(f"Thời tiết Thâm Quyến: {weather['temperature']}°C, {weather['condition']}")

            print("\n✅ Mọi kiểm thử hoàn tất!")

    except Exception as e:
        print(f"❌ Kiểm thử thất bại: {e}")


if __name__ == "__main__":
    asyncio.run(test_weather_server())
```

<strong>(4) Sử dụng máy chủ MCP tùy chỉnh trong Agent</strong>

```python
"""Sử dụng máy chủ MCP thời tiết trong Agent"""

import os
from dotenv import load_dotenv
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

load_dotenv()


def create_weather_assistant():
    """Tạo trợ lý thời tiết"""
    llm = HelloAgentsLLM()

    assistant = SimpleAgent(
        name="Trợ lý thời tiết",
        llm=llm,
        system_prompt="""Bạn là trợ lý thời tiết, có thể tra cứu thời tiết của thành phố.
Dùng công cụ mcp_get_weather để tra cứu thời tiết, hỗ trợ tên thành phố.
"""
    )

    # Thêm công cụ MCP thời tiết
    server_script = os.path.join(os.path.dirname(__file__), "14_weather_mcp_server.py")
    weather_tool = MCPTool(server_command=["python", server_script])

    # Mở rộng và đăng ký tường minh các công cụ con của MCP
    expanded_tools = weather_tool.get_expanded_tools()
    if not expanded_tools:
        raise RuntimeError("Không phát hiện công cụ con MCP thời tiết, hãy kiểm tra script dịch vụ, phụ thuộc và log khởi động.")

    for expanded_tool in expanded_tools:
        assistant.add_tool(expanded_tool)

    return assistant


def demo():
    """Minh họa"""
    assistant = create_weather_assistant()

    print("\nTra cứu thời tiết Bắc Kinh:")
    response = assistant.run("Thời tiết Bắc Kinh hôm nay thế nào?")
    print(f"Trả lời: {response}\n")


def interactive():
    """Chế độ tương tác"""
    assistant = create_weather_assistant()

    while True:
        user_input = input("\nBạn: ").strip()
        if user_input.lower() in ['quit', 'exit']:
            break
        response = assistant.run(user_input)
        print(f"Trợ lý: {response}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        interactive()
```

```
🔗 Đang kết nối tới máy chủ MCP...
✅ Kết nối thành công!
🔌 Kết nối đã ngắt
✅ Công cụ 'mcp_get_weather' đã được đăng ký.
✅ Công cụ 'mcp_list_supported_cities' đã được đăng ký.
✅ Công cụ 'mcp_get_server_info' đã được đăng ký.

Bạn: Tôi muốn tra thời tiết Bắc Kinh
🔗 Đang kết nối tới máy chủ MCP...
✅ Kết nối thành công!
🔌 Kết nối đã ngắt
Trợ lý: Tình hình thời tiết hiện tại ở Bắc Kinh như sau:

- Nhiệt độ: 10.0°C
- Nhiệt độ cảm nhận: 9.0°C
- Độ ẩm: 94%
- Tình trạng thời tiết: mưa nhỏ
- Tốc độ gió: 1.7 m/giây
- Tầm nhìn: 10.0 km
- Dấu thời gian: 09/10/2025 13:46:40

Hãy nhớ mang theo đồ che mưa và điều chỉnh trang phục phù hợp với thay đổi thời tiết.
```

### 10.5.2 Tải máy chủ MCP lên

Chúng ta đã tạo một máy chủ MCP tra cứu thời tiết thực tế. Bây giờ, hãy công bố nó lên nền tảng Smithery để các nhà phát triển trên toàn thế giới có thể dùng dịch vụ của chúng ta.

 (1) Smithery là gì?

[Smithery](https://smithery.ai/) là nền tảng công bố chính thức của máy chủ MCP, tương tự PyPI của Python hay npm của Node.js. Thông qua Smithery, người dùng có thể:

- 🔍 Khám phá và tìm kiếm máy chủ MCP
- 📦 Cài đặt máy chủ MCP chỉ với một cú nhấp
- 📊 Xem thống kê sử dụng và đánh giá của máy chủ
- 🔄 Tự động nhận cập nhật của máy chủ

(2) Chuẩn bị công bố
Trước tiên, chúng ta cần sắp xếp dự án thành định dạng công bố chuẩn; thư mục này đã được sắp xếp sẵn trong thư mục `code` để bạn tham khảo:

```
weather-mcp-server/
├── README.md           # Tài liệu mô tả dự án
├── LICENSE            # Giấy phép mã nguồn mở
├── Dockerfile         # Cấu hình build Docker (khuyến nghị)
├── pyproject.toml     # Cấu hình dự án Python (bắt buộc)
├── requirements.txt   # Phụ thuộc Python
├── smithery.yaml      # Tệp cấu hình Smithery (bắt buộc)
└── server.py          # Tệp chính của máy chủ MCP
```

Cần lưu ý, `smithery.yaml` là tệp cấu hình của nền tảng Smithery:
```yaml
name: weather-mcp-server
displayName: Weather MCP Server
description: Real-time weather query MCP server based on HelloAgents framework
version: 1.0.0
author: HelloAgents Team
homepage: https://github.com/yourusername/weather-mcp-server
license: MIT
categories:
  - weather
  - data
tags:
  - weather
  - real-time
  - helloagents
  - wttr
runtime: container
build:
  dockerfile: Dockerfile
  dockerBuildPath: .
startCommand:
  type: http
tools:
  - name: get_weather
    description: Get current weather for a city
  - name: list_supported_cities
    description: List all supported cities
  - name: get_server_info
    description: Get server information
```

Giải thích cấu hình:

- `name`: định danh duy nhất của máy chủ (chữ thường, phân cách bằng dấu gạch nối)
- `displayName`: tên hiển thị
- `description`: mô tả ngắn
- `version`: số phiên bản (tuân theo phiên bản ngữ nghĩa)
- `runtime`: môi trường chạy (python/node)
- `entrypoint`: tệp đầu vào
- `tools`: danh sách công cụ

`pyproject.toml` là tệp cấu hình chuẩn của dự án Python; Smithery yêu cầu phải có tệp này vì sau đó nó sẽ được đóng gói thành một server:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "weather-mcp-server"
version = "1.0.0"
description = "Real-time weather query MCP server based on HelloAgents framework"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "HelloAgents Team", email = "xxx"}
]
requires-python = ">=3.10"
dependencies = [
    "hello-agents>=0.2.1",
    "requests>=2.31.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/weather-mcp-server"
Repository = "https://github.com/yourusername/weather-mcp-server"
"Bug Tracker" = "https://github.com/yourusername/weather-mcp-server/issues"

[tool.setuptools]
py-modules = ["server"]
```

Giải thích cấu hình:

- `[build-system]`: chỉ định công cụ build (setuptools)
- `[project]`: siêu dữ liệu dự án
  - `name`: tên dự án
  - `version`: số phiên bản (tuân theo phiên bản ngữ nghĩa)
  - `dependencies`: danh sách phụ thuộc của dự án
  - `requires-python`: yêu cầu phiên bản Python
- `[project.urls]`: các liên kết liên quan đến dự án
- `[tool.setuptools]`: cấu hình setuptools

Mặc dù Smithery sẽ tự động sinh Dockerfile, việc cung cấp Dockerfile tùy chỉnh giúp đảm bảo triển khai thành công:

```dockerfile
# Multi-stage build for weather-mcp-server
FROM python:3.12-slim-bookworm as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml requirements.txt ./
COPY server.py ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8081

# Expose port (Smithery uses 8081)
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the MCP server
CMD ["python", "server.py"]
```

Giải thích cấu hình Dockerfile:

- <strong>Image nền</strong>: `python:3.12-slim-bookworm` - image Python nhẹ
- <strong>Thư mục làm việc</strong>: `/app` - thư mục gốc của ứng dụng
- <strong>Cổng</strong>: `8081` - cổng chuẩn của nền tảng Smithery
- <strong>Lệnh khởi động</strong>: `python server.py` - chạy máy chủ MCP

Ở đây, chúng ta cần Fork kho `hello-agents`, lấy mã nguồn trong `code`, rồi dùng GitHub của mình tạo một kho tên `weather-mcp-server`, thay `yourusername` bằng Username GitHub của bạn.

(3) Gửi lên Smithery

Mở trình duyệt và truy cập [https://smithery.ai/](https://smithery.ai/). Đăng nhập Smithery bằng tài khoản GitHub. Nhấp vào nút "Publish Server" trên trang, nhập URL kho GitHub của bạn: `https://github.com/yourusername/weather-mcp-server`, rồi chờ công bố.

Sau khi công bố hoàn tất, bạn sẽ thấy một trang tương tự như Hình 10.10:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-10.png" alt="" width="85%"/>
  <p>Hình 10.10 Trang công bố thành công trên Smithery </p>
</div>



Sau khi máy chủ công bố thành công, người dùng có thể dùng theo các cách sau:

Cách 1: thông qua Smithery CLI

```bash
# Cài đặt Smithery CLI
npm install -g @smithery/cli

# Cài đặt máy chủ của bạn
smithery install weather-mcp-server
```

Cách 2: cấu hình trong Claude Desktop

```json
{
  "mcpServers": {
    "weather": {
      "command": "smithery",
      "args": ["run", "weather-mcp-server"]
    }
  }
}
```

Cách 3: sử dụng trong HelloAgents

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools.builtin.protocol_tools import MCPTool

agent = SimpleAgent(name="Trợ lý thời tiết", llm=HelloAgentsLLM())

# Dùng máy chủ đã cài qua Smithery
weather_tool = MCPTool(
    server_command=["smithery", "run", "weather-mcp-server"]
)
agent.add_tool(weather_tool)

response = agent.run("Thời tiết Bắc Kinh hôm nay thế nào?")
```

Tất nhiên, đây chỉ là ví dụ; còn nhiều cách dùng khác để bạn tự khám phá. Hình 10.11 dưới đây minh họa thông tin hiển thị khi công cụ MCP công bố thành công, gồm tên dịch vụ “thời tiết”, định danh duy nhất `@jjyaoao/weather-mcp-server` và thông tin trạng thái. Khu vực Tools chính là những phương thức chúng ta vừa hiện thực; khu vực Connect cung cấp thông tin kỹ thuật cần thiết để kết nối và sử dụng dịch vụ này, bao gồm <strong>địa chỉ URL truy cập</strong> của dịch vụ và <strong>đoạn mã cấu hình</strong> cho nhiều ngôn ngữ/môi trường. Nếu muốn tìm hiểu sâu hơn, hãy nhấp vào [liên kết](https://smithery.ai/server/@jjyaoao/weather-mcp-server) này.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-11.png" alt="" width="85%"/>
  <p>Hình 10.11 Công cụ MCP công bố thành công trên Smithery </p>
</div>

Đã đến lúc tạo máy chủ MCP của riêng bạn!



## 10.6 Tóm tắt chương

Chương này giới thiệu một cách hệ thống ba giao thức cốt lõi của giao tiếp Agent: MCP, A2A và ANP, đồng thời thảo luận triết lý thiết kế, kịch bản ứng dụng và phương pháp thực hành của chúng.

<strong>Định vị của các giao thức:</strong>

- <strong>MCP (Model Context Protocol)</strong>: là cầu nối giữa Agent và công cụ, cung cấp giao diện truy cập công cụ thống nhất, phù hợp để tăng cường năng lực cho một Agent đơn lẻ.
- <strong>A2A (Agent-to-Agent Protocol)</strong>: là hệ thống đối thoại giữa các Agent, hỗ trợ giao tiếp trực tiếp và thương lượng nhiệm vụ, phù hợp với sự phối hợp chặt chẽ của nhóm nhỏ.
- <strong>ANP (Agent Network Protocol)</strong>: là “Internet” của Agent, cung cấp cơ chế phát hiện dịch vụ, định tuyến và cân bằng tải, phù hợp để xây dựng mạng Agent quy mô lớn, mở.

<strong>Phương án tích hợp của HelloAgents</strong>

Trong framework `HelloAgents`, ba giao thức này được trừu tượng hóa thống nhất thành công cụ (Tool), hiện thực tích hợp liền mạch, cho phép nhà phát triển linh hoạt thêm cho Agent các năng lực giao tiếp ở những tầng khác nhau:

```python
# Giao diện Tool thống nhất
from hello_agents.tools import MCPTool, A2ATool, ANPTool

# Mọi giao thức đều có thể thêm vào Agent như một Tool
agent.add_tool(MCPTool(...))
agent.add_tool(A2ATool(...))
agent.add_tool(ANPTool(...))
```

<strong>Tổng kết kinh nghiệm thực hành</strong>

- Ưu tiên tận dụng các dịch vụ MCP cộng đồng trưởng thành để giảm việc phát triển lặp lại không cần thiết.
- Chọn giao thức phù hợp với quy mô hệ thống: kịch bản phối hợp quy mô nhỏ nên dùng A2A, kịch bản mạng quy mô lớn nên dùng ANP.

Sau khi hoàn thành chương này, chúng tôi khuyến nghị bạn:

1. <strong>Thực hành tay</strong>:
   - Xây dựng máy chủ MCP của riêng bạn
   - Dùng giao thức để tạo hệ thống nhiều Agent phối hợp
   - Chiến lược kết hợp MCP, A2A và ANP
2. <strong>Học sâu</strong>:
   - Đọc tài liệu chính thức của MCP: https://modelcontextprotocol.io
   - Đọc tài liệu chính thức của A2A: https://a2a-protocol.org/latest/
   - Đọc tài liệu chính thức của ANP: https://agent-network-protocol.com/guide/
3. <strong>Tham gia cộng đồng</strong>:
   - Đóng góp dịch vụ MCP mới cho cộng đồng
   - Chia sẻ các ca hiện thực Agent do bạn phát triển
   - Tham gia thảo luận tiêu chuẩn kỹ thuật của các giao thức liên quan, hoặc đặt câu hỏi trong Issue hay trực tiếp giúp Helloagents hỗ trợ ca example mới

<strong>Chúc mừng bạn đã hoàn thành chương 10!</strong>

Bạn đã nắm được kiến thức cốt lõi về giao thức giao tiếp Agent. Hãy tiếp tục cố gắng! 🚀

## Bài tập

> <strong>Gợi ý</strong>: một số bài tập không có đáp án chuẩn; trọng tâm là rèn luyện hiểu biết tổng hợp và năng lực thực hành của người học về giao thức giao tiếp Agent.

1. Chương này giới thiệu ba giao thức giao tiếp Agent: MCP, A2A và ANP. Hãy phân tích:

   - Mục 10.1.2 đã so sánh triết lý thiết kế của ba giao thức. Hãy phân tích sâu: vì sao MCP nhấn mạnh “chia sẻ ngữ cảnh”, A2A nhấn mạnh “phối hợp dạng đối thoại”, còn ANP nhấn mạnh “tô-pô mạng”? Mỗi triết lý thiết kế này giải quyết vấn đề cốt lõi gì?
   - Giả sử bạn cần xây dựng một “hệ thống chăm sóc khách hàng thông minh” với các chức năng sau: (1) truy cập cơ sở dữ liệu khách hàng và hệ thống đơn hàng; (2) nhiều Agent chăm sóc khách hàng chuyên môn phối hợp xử lý vấn đề phức tạp; (3) hỗ trợ yêu cầu đồng thời của người dùng quy mô lớn. Hãy chọn giao thức phù hợp nhất cho từng chức năng và giải thích lý do.
   - Ba giao thức có thể dùng kết hợp không? Hãy thiết kế một kịch bản ứng dụng thực tế, trình bày cách dùng đồng thời MCP, A2A và ANP để xây dựng một hệ thống Agent hoàn chỉnh. Vẽ sơ đồ kiến trúc hệ thống và giải thích trách nhiệm của từng giao thức.

2. MCP (Model Context Protocol) là giao thức chuẩn cho giao tiếp giữa Agent và công cụ. Dựa trên nội dung mục 10.2, hãy suy nghĩ sâu:

   > <strong>Gợi ý</strong>: đây là bài tập thực hành tay, nên thao tác thật

   - Trong phần hiện thực máy chủ MCP ở mục 10.2.3, chúng ta đã định nghĩa các phương thức cốt lõi như `list_tools`, `call_tool`. Hãy mở rộng hiện thực này, thêm một máy chủ MCP mới cung cấp các công cụ sau: (1) công cụ truy vấn cơ sở dữ liệu; (2) công cụ trực quan hóa dữ liệu; (3) công cụ sinh báo cáo. Yêu cầu các công cụ có thể phối hợp hoàn thành nhiệm vụ phân tích dữ liệu phức tạp.
   - Giao thức MCP hỗ trợ hai khái niệm quan trọng là “tài nguyên” (Resources) và “prompt” (Prompts), nhưng chương này chủ yếu tập trung vào “công cụ” (Tools). Hãy tra tài liệu chính thức của MCP để hiểu mục đích thiết kế của Resources và Prompts, rồi thiết kế một kịch bản ứng dụng trình bày cách dùng ba khái niệm cốt lõi này để xây dựng hệ thống Agent mạnh mẽ hơn.
   - MCP dùng JSON-RPC 2.0 làm giao thức giao tiếp tầng dưới, giao tiếp giữa các tiến trình qua stdio. Hãy phân tích: thiết kế này có ưu điểm và hạn chế gì? Nếu cần hỗ trợ máy chủ MCP từ xa (truy cập qua HTTP/WebSocket), nên mở rộng hiện thực hiện tại như thế nào?

3. A2A (Agent-to-Agent Protocol) hỗ trợ phối hợp dạng đối thoại giữa các Agent. Dựa trên nội dung mục 10.3, hãy hoàn thành các bài thực hành mở rộng sau:

   > <strong>Gợi ý</strong>: đây là bài tập thực hành tay, nên thao tác thật

   - Trong ca “nhóm nghiên cứu” ở mục 10.3.4, nhà nghiên cứu và người viết phối hợp qua giao thức A2A để hoàn thành bài viết. Hãy mở rộng ca này, thêm Agent thứ ba là “người phản biện” (Reviewer), có khả năng đánh giá chất lượng bài viết và đề xuất chỉnh sửa. Hãy thiết kế quy trình phối hợp giữa ba Agent và hiện thực mã đầy đủ.
   - Giao thức A2A định nghĩa các loại tin nhắn như `task`, `task_result`. Hãy phân tích: nếu trong quá trình phối hợp xuất hiện xung đột (ví dụ hai Agent có ý kiến khác nhau về cùng một vấn đề), nên thiết kế cơ chế giải quyết xung đột thế nào? Hãy mở rộng giao thức A2A, thêm các loại tin nhắn như “thương lượng” (negotiation) và “bỏ phiếu” (voting).
   - Hãy so sánh giao thức A2A với các framework đa Agent như AutoGen, CAMEL đã giới thiệu ở chương 6: A2A với tư cách giao thức chuẩn có quan hệ thế nào với các framework này? Chúng có thể thay thế nhau không? Hãy thiết kế một phương án để Agent dựa trên giao thức A2A có thể giao tiếp với Agent trong framework AutoGen.

4. ANP (Agent Network Protocol) hỗ trợ mạng Agent quy mô lớn. Dựa trên nội dung mục 10.4, hãy phân tích sâu:

   - Mục 10.4.2 đã giới thiệu thiết kế tô-pô mạng của ANP, bao gồm các cấu trúc hình sao, dạng lưới, phân tầng. Hãy phân tích: trong kịch bản nào nên chọn cấu trúc tô-pô nào? Nếu quy mô mạng từ 10 Agent mở rộng lên 1000 Agent, cấu trúc tô-pô nên tiến hóa ra sao?
   - Giao thức ANP hỗ trợ cơ chế “định tuyến” (routing) và “phát hiện” (discovery), giúp Agent tìm được đối tác phối hợp phù hợp một cách động. Hãy thiết kế một “thuật toán định tuyến thông minh”: dựa trên loại nhiệm vụ, năng lực Agent, tải mạng và các yếu tố khác để tự động chọn đường định tuyến tin nhắn tối ưu.
   - Trong ca “thành phố thông minh” ở mục 10.4.4, nhiều Agent phối hợp quản lý hệ thống thành phố. Hãy suy nghĩ: nếu một Agent then chốt (như Agent quản lý giao thông) gặp sự cố, toàn bộ hệ thống nên ứng phó thế nào? Hãy thiết kế một “cơ chế chịu lỗi”, bao gồm phát hiện sự cố, chuyển sang bản dự phòng, khôi phục trạng thái, v.v.

5. An ninh và bảo vệ quyền riêng tư của giao thức giao tiếp Agent là vấn đề then chốt trong ứng dụng thực tế. Hãy suy nghĩ:

   - Trong phần hiện thực MCP client ở mục 10.2.4, Agent có thể gọi bất kỳ công cụ nào mà máy chủ MCP cung cấp. Hãy phân tích: thiết kế này có rủi ro an ninh gì? Nếu máy chủ MCP cung cấp thao tác nguy hiểm (như xóa tệp, thực thi lệnh hệ thống), nên thiết kế cơ chế kiểm soát quyền như thế nào?
   - Giao thức A2A và ANP liên quan giao tiếp giữa nhiều Agent, có thể chứa thông tin nhạy cảm (như dữ liệu riêng tư của người dùng, bí mật kinh doanh). Hãy thiết kế một phương án “mã hóa đầu cuối”: đảm bảo tin nhắn không bị nghe lén hay sửa đổi trong quá trình truyền, đồng thời hỗ trợ xác thực danh tính Agent và kiểm soát truy cập.
   - Trong mạng Agent quy mô lớn, Agent độc hại có thể gửi thông tin giả, phát động tấn công từ chối dịch vụ hoặc đánh cắp dữ liệu của Agent khác. Hãy thiết kế một “hệ thống đánh giá tin cậy”: dựa trên hành vi lịch sử, chất lượng phối hợp, đánh giá cộng đồng và các yếu tố khác để đánh giá động độ tin cậy của từng Agent, rồi điều chỉnh chiến lược giao tiếp theo đó.

## Tài liệu tham khảo

[1] Anthropic. (2024). *Model Context Protocol*. Retrieved October 7, 2025, from https://modelcontextprotocol.io/

[2] The A2A Project. (2025). *A2A Protocol: An open protocol for agent-to-agent communication*. Retrieved October 7, 2025, from https://a2a-protocol.org/

[3] Chang, G., Lin, E., Yuan, C., Cai, R., Chen, B., Xie, X., & Zhang, Y. (2025). *Agent Network Protocol technical white paper*. arXiv. https://doi.org/10.48550/arXiv.2508.00007

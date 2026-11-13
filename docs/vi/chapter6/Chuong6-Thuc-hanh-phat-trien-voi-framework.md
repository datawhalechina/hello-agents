# Chương 6: Thực hành phát triển với framework

Ở chương 4, chúng ta đã hiện thực các quy trình làm việc cốt lõi của Agent như ReAct, Plan-and-Solve và Reflection bằng cách viết mã gốc. Quá trình này giúp chúng ta hiểu logic thực thi bên trong của Agent. Tiếp đó, ở chương 5, chúng ta chuyển sang góc nhìn “người sử dụng”, trải nghiệm sự thuận tiện và hiệu quả mà nền tảng low-code mang lại.

Mục tiêu của chương này là tìm hiểu cách sử dụng một số <strong>framework Agent</strong> chủ lưu trong ngành để xây dựng ứng dụng Agent đáng tin cậy một cách hiệu quả và chuẩn hóa. Trước tiên, chúng ta sẽ khảo sát tổng quan các framework Agent chủ lưu hiện nay, sau đó với một số framework tiêu biểu, đi qua một ca thực chiến hoàn chỉnh để trải nghiệm mô hình phát triển do framework dẫn dắt.

## 6.1 Từ hiện thực thủ công đến phát triển bằng framework

Từ việc viết script dùng một lần đến việc dùng một framework trưởng thành là một bước chuyển tư duy quan trọng trong lĩnh vực kỹ thuật phần mềm. Mã chúng ta viết ở chương 4 chủ yếu nhằm mục đích giảng dạy và tìm hiểu. Chúng có thể hoàn thành tốt nhiệm vụ cụ thể, nhưng nếu dùng chúng để xây dựng nhiều ứng dụng Agent khác loại, logic phức tạp, sẽ nhanh chóng gặp nút thắt.

Bản chất của một framework là cung cấp một bộ “quy phạm” đã được kiểm chứng. Nó trừu tượng hóa và đóng gói những công việc lặp lại mà mọi Agent đều có (như vòng lặp chính, quản lý trạng thái, gọi công cụ, ghi nhật ký, v.v.), để khi xây dựng Agent mới, chúng ta có thể tập trung vào logic nghiệp vụ độc đáo của nó thay vì hiện thực tầng dưới chung.

### 6.1.1 Vì sao cần framework Agent

Trước khi bắt đầu thực chiến, cần làm rõ vì sao dùng framework. So với việc trực tiếp viết script Agent độc lập, giá trị của framework chủ yếu thể hiện ở các khía cạnh sau:

1. <strong>Tăng khả năng tái sử dụng mã và hiệu quả phát triển</strong>: đây là giá trị trực tiếp nhất. Một framework tốt cung cấp lớp cơ sở `Agent` hoặc bộ thực thi chung, đóng gói vòng lặp cốt lõi khi Agent chạy (Agent Loop). Dù là ReAct hay Plan-and-Solve, đều có thể nhanh chóng dựng dựa trên các thành phần chuẩn của framework, tránh công việc lặp lại.
2. <strong>Hiện thực tách rời và khả năng mở rộng của các thành phần cốt lõi</strong>: một hệ thống Agent vững chắc nên gồm nhiều mô-đun liên kết lỏng. Thiết kế framework buộc chúng ta tách các mối quan tâm khác nhau:
   - <strong>Tầng mô hình (Model Layer)</strong>: chịu trách nhiệm tương tác với mô hình ngôn ngữ lớn, có thể dễ dàng thay thế các mô hình khác nhau (OpenAI, Anthropic, mô hình cục bộ).
   - <strong>Tầng công cụ (Tool Layer)</strong>: cung cấp giao diện định nghĩa, đăng ký và thực thi công cụ được chuẩn hóa; thêm công cụ mới không ảnh hưởng mã khác.
   - <strong>Tầng bộ nhớ (Memory Layer)</strong>: xử lý bộ nhớ ngắn hạn và dài hạn, có thể chuyển đổi chiến lược bộ nhớ khác nhau theo nhu cầu (như cửa sổ trượt, bộ nhớ tóm tắt). Thiết kế mô-đun này khiến toàn bộ hệ thống có khả năng mở rộng cao; thay thế hoặc nâng cấp bất kỳ thành phần nào đều trở nên đơn giản.
3. <strong>Chuẩn hóa quản lý trạng thái phức tạp</strong>: lớp `Memory` chúng ta hiện thực trong `ReflectionAgent` chỉ là khởi đầu đơn giản. Trong ứng dụng Agent thật, chạy lâu dài, quản lý trạng thái là thách thức lớn; cần xử lý giới hạn cửa sổ ngữ cảnh, lưu trữ bền vững thông tin lịch sử, theo dõi trạng thái hội thoại nhiều lượt, v.v. Một framework có thể cung cấp cơ chế quản lý trạng thái mạnh mẽ và tổng quát, nhà phát triển không cần xử lý lại những vấn đề phức tạp này mỗi lần.
4. <strong>Đơn giản hóa khả năng quan sát và gỡ lỗi</strong>: khi hành vi Agent trở nên phức tạp, hiểu quá trình ra quyết định của nó trở nên then chốt. Một framework được thiết kế cẩn thận có thể tích hợp sẵn năng lực quan sát mạnh mẽ. Ví dụ, thông qua cơ chế callback sự kiện (Callbacks), chúng ta có thể tự động kích hoạt ghi nhật ký hoặc báo cáo dữ liệu tại các nút then chốt trong vòng đời Agent (như `on_llm_start`, `on_tool_end`, `on_agent_finish`), từ đó dễ dàng theo dõi và gỡ lỗi toàn bộ quỹ đạo chạy của Agent. Điều này hiệu quả và hệ thống hơn nhiều so với thêm câu lệnh `print` thủ công trong mã.

Vì vậy, đi từ hiện thực thủ công sang phát triển bằng framework không chỉ là thay đổi cách tổ chức mã, mà còn là con đường tất yếu để xây dựng ứng dụng Agent phức tạp, đáng tin cậy, dễ bảo trì.

### 6.1.2 Lựa chọn và so sánh các framework chủ lưu

Hệ sinh thái framework Agent đang phát triển với tốc độ chưa từng có. Nếu LangChain và LlamaIndex đã định nghĩa mô hình của thế hệ framework ứng dụng LLM tổng quát đầu tiên, thì thế hệ framework mới tập trung hơn vào giải quyết những thách thức sâu ở lĩnh vực cụ thể, đặc biệt là <strong>cộng tác đa Agent (Multi-Agent Collaboration)</strong> và <strong>kiểm soát quy trình làm việc phức tạp (Complex Workflow Control)</strong>.

Trong thực chiến tiếp theo của chương này, chúng ta sẽ tập trung vào bốn framework rất tiêu biểu ở những lĩnh vực tiên phong này: AutoGen, AgentScope, CAMEL và LangGraph. Triết lý thiết kế của chúng khác nhau, đại diện cho các con đường kỹ thuật khác nhau để hiện thực hệ thống Agent phức tạp, như trong Bảng 6.1.

<div align="center">
  <p>Bảng 6.1 So sánh bốn framework Agent</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/6-figures/01.png" alt="" width="90%"/>
</div>


- <strong>AutoGen</strong>: tư tưởng cốt lõi của AutoGen là hiện thực cộng tác thông qua hội thoại<sup>[1]</sup>. Nó trừu tượng hóa hệ thống đa Agent thành một nhóm chat gồm nhiều Agent “có thể đối thoại”. Nhà phát triển có thể định nghĩa các vai trò khác nhau (như `Coder`, `ProductManager`, `Tester`) và đặt quy tắc tương tác giữa chúng (ví dụ `Coder` viết xong mã thì `Tester` tự động tiếp nhận). Quá trình giải quyết nhiệm vụ chính là quá trình các Agent này trong nhóm chat, thông qua truyền tin tự động, liên tục đối thoại, cộng tác, lặp cho đến khi đạt mục tiêu cuối cùng.
- <strong>AgentScope</strong>: AgentScope là nền tảng phát triển đầy đủ chức năng được thiết kế riêng cho ứng dụng đa Agent<sup>[2]</sup>. Đặc điểm cốt lõi của nó là <strong>dễ sử dụng</strong> và <strong>kỹ thuật hóa</strong>. Nó cung cấp một bộ giao diện lập trình rất thân thiện, cho phép nhà phát triển dễ dàng định nghĩa Agent, xây dựng mạng giao tiếp và quản lý toàn bộ vòng đời ứng dụng. Cơ chế <strong>truyền tin</strong> tích hợp và hỗ trợ triển khai phân tán khiến nó rất phù hợp để xây dựng và vận hành hệ thống đa Agent phức tạp, quy mô lớn.
- <strong>CAMEL</strong>: CAMEL cung cấp một phương pháp cộng tác mới lạ có tên <strong>nhập vai (Role-Playing)</strong><sup>[3]</sup>. Tư tưởng cốt lõi là chúng ta chỉ cần đặt vai trò và mục tiêu nhiệm vụ chung cho hai Agent (ví dụ `nhà nghiên cứu AI` và `lập trình viên Python`), chúng sẽ dưới sự dẫn dắt của “<strong>prompt khởi đầu (Inception Prompting)</strong>” tự chủ thực hiện hội thoại nhiều lượt, truyền cảm hứng và phối hợp với nhau để cùng hoàn thành nhiệm vụ. Nó giảm rất nhiều độ phức tạp khi thiết kế luồng hội thoại đa Agent.
- <strong>LangGraph</strong>: là phần mở rộng của hệ sinh thái LangChain, LangGraph đi theo con đường khác, mô hình hóa quy trình thực thi của Agent thành <strong>đồ thị (Graph)</strong><sup>[4]</sup>. Trong cấu trúc chuỗi truyền thống, thông tin chỉ có thể chảy một chiều. Còn LangGraph định nghĩa mỗi thao tác (như gọi LLM, thực thi công cụ) là một <strong>nút (Node)</strong> trong đồ thị, và dùng <strong>cạnh (Edge)</strong> để định nghĩa logic chuyển giữa các nút. Thiết kế này tự nhiên hỗ trợ <strong>chu trình (Cycles)</strong>, khiến việc hiện thực các quy trình phức tạp như Reflection – lặp, sửa, tự phản tư – trở nên cực kỳ đơn giản và trực quan.

Trong các mục tiếp theo, với bốn framework này, chúng ta sẽ lần lượt đi qua một ca thực chiến hoàn chỉnh để trải nghiệm sâu mô hình phát triển do framework dẫn dắt. <strong>Xin lưu ý</strong>, tất cả tệp nguồn của dự án trình diễn sẽ đặt trong thư mục `code`; phần nội dung chính chỉ trình bày nguyên lý.

## 6.2 Framework một: AutoGen

Như đã nói ở trên, triết lý thiết kế của AutoGen bắt nguồn từ “lấy hội thoại dẫn dắt cộng tác”. Nó khéo léo ánh xạ quy trình giải quyết nhiệm vụ phức tạp thành một chuỗi hội thoại tự động giữa các Agent với vai trò khác nhau. Dựa trên tư tưởng cốt lõi này, framework AutoGen không ngừng tiến hóa. Chúng ta sẽ lấy phiên bản `0.7.4` làm ví dụ, vì đây là phiên bản mới nhất tính đến nay, đại diện cho một lần tái cấu trúc kiến trúc quan trọng, chuyển từ thiết kế kế thừa lớp sang kiến trúc kết hợp linh hoạt hơn. Để hiểu sâu và áp dụng framework này, trước tiên chúng ta cần trình bày các yếu tố cấu thành cốt lõi và cơ chế tương tác hội thoại tầng dưới.

### 6.2.1 Cơ chế cốt lõi của AutoGen

Việc phát hành phiên bản `0.7.4` là một nút quan trọng trong sự phát triển của AutoGen, đánh dấu một cuộc cách tân căn bản trong thiết kế tầng dưới của framework. Cập nhật này không phải là cộng thêm chức năng đơn giản, mà là suy nghĩ lại toàn bộ kiến trúc, nhằm nâng cao tính mô-đun, hiệu năng đồng thời và trải nghiệm nhà phát triển.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/6-figures/02.png" alt="" width="90%"/>
  <p>Hình 6.1 Kiến trúc AutoGen</p>
</div>

(1) Sự tiến hóa của cấu trúc framework

Như trong Hình 6.1, thay đổi rõ rệt nhất của kiến trúc mới là đưa vào tư tưởng phân tầng rõ ràng và ưu tiên bất đồng bộ.

- <strong>Thiết kế phân tầng:</strong> framework được tách thành hai mô-đun cốt lõi:
  - `autogen-core`: là nền tảng tầng dưới của framework, đóng gói các chức năng cốt lõi như tương tác với mô hình ngôn ngữ, truyền tin. Sự tồn tại của nó đảm bảo tính ổn định và khả năng mở rộng tương lai của framework.
  - `autogen-agentchat`: xây dựng trên `core`, cung cấp giao diện cấp cao để phát triển ứng dụng Agent hội thoại, đơn giản hóa quy trình phát triển ứng dụng đa Agent. Chiến lược phân tầng này khiến trách nhiệm các thành phần rõ ràng, giảm mức liên kết của hệ thống.
- <strong>Ưu tiên bất đồng bộ:</strong> kiến trúc mới chuyển hoàn toàn sang lập trình bất đồng bộ (`async/await`). Trong tình huống cộng tác đa Agent, yêu cầu mạng (như gọi API LLM) là thao tác tốn thời gian chính. Chế độ bất đồng bộ cho phép hệ thống xử lý nhiệm vụ khác trong khi chờ một Agent phản hồi, từ đó tránh chặn luồng và nâng cao rõ rệt năng lực xử lý đồng thời và hiệu quả sử dụng tài nguyên hệ thống.

(2) Các thành phần Agent cốt lõi

Agent là đơn vị cơ bản thực thi nhiệm vụ. Trong phiên bản `0.7.4`, thiết kế Agent tập trung và mô-đun hóa hơn.

- <strong>AssistantAgent (Agent trợ lý):</strong> đây là người giải quyết nhiệm vụ chính, cốt lõi là đóng gói một mô hình ngôn ngữ lớn (LLM). Nhiệm vụ của nó là sinh phản hồi giàu logic và tri thức dựa trên lịch sử hội thoại, ví dụ đề xuất kế hoạch, viết bài hoặc viết mã. Thông qua các system message khác nhau, chúng ta có thể trao cho nó các vai “chuyên gia” khác nhau.
- <strong>UserProxyAgent (Agent đại diện người dùng):</strong> đây là thành phần có chức năng độc đáo trong AutoGen. Nó đóng hai vai: vừa là “người đại diện” của người dùng, chịu trách nhiệm khởi phát nhiệm vụ và truyền đạt ý định; vừa là “bộ thực thi” đáng tin cậy, có thể cấu hình để thực thi mã hoặc gọi công cụ, và phản hồi kết quả cho các Agent khác. Thiết kế này phân biệt rõ ràng “suy nghĩ” (do `AssistantAgent` hoàn thành) và “hành động”.

(3) Từ GroupChatManager đến Team

Khi nhiệm vụ cần nhiều Agent cộng tác, cần một cơ chế điều phối luồng hội thoại. Ở phiên bản đầu, `GroupChatManager` đảm nhận trách nhiệm này. Còn trong kiến trúc mới, khái niệm `Team` hoặc nhóm chat linh hoạt hơn được đưa vào, ví dụ `RoundRobinGroupChat`.

- <strong>Nhóm chat luân phiên (RoundRobinGroupChat):</strong> đây là cơ chế điều phối hội thoại rõ ràng, tuần tự. Nó cho các Agent tham gia phát biểu lần lượt theo thứ tự đặt trước. Chế độ này rất phù hợp với nhiệm vụ có quy trình cố định, ví dụ quy trình phát triển phần mềm điển hình: quản lý sản phẩm nêu yêu cầu trước, kỹ sư viết mã, cuối cùng người kiểm duyệt mã kiểm tra.
- <strong>Quy trình làm việc:</strong>
  1. Trước tiên, tạo một thực thể `RoundRobinGroupChat` và thêm tất cả Agent tham gia cộng tác (như quản lý sản phẩm, kỹ sư, v.v.) vào đó.
  2. Khi nhiệm vụ bắt đầu, nhóm chat sẽ kích hoạt Agent tương ứng lần lượt theo thứ tự đặt trước.
  3. Agent được chọn phản hồi dựa trên ngữ cảnh hội thoại hiện tại.
  4. Nhóm chat thêm phản hồi mới vào lịch sử hội thoại và kích hoạt Agent tiếp theo.
  5. Quá trình này tiếp diễn cho đến khi đạt số lượt hội thoại tối đa hoặc thỏa mãn điều kiện dừng đặt trước.

Bằng cách này, AutoGen đơn giản hóa quan hệ cộng tác phức tạp thành một “cuộc họp bàn tròn” tự động có quy trình rõ ràng, dễ quản lý. Nhà phát triển chỉ cần định nghĩa vai trò và thứ tự phát biểu của từng thành viên nhóm; phần còn lại của quy trình cộng tác có thể do cơ chế nhóm chat tự chủ dẫn dắt.

Trong mục tiếp theo, chúng ta sẽ xây dựng một ca mô phỏng nhóm phát triển phần mềm để tự trải nghiệm cách định nghĩa Agent với các vai trò khác nhau dưới kiến trúc mới, và tổ chức chúng trong một nhóm chat do `RoundRobinGroupChat` điều phối để cộng tác hoàn thành một nhiệm vụ lập trình thực tế.

### 6.2.2 Nhóm phát triển phần mềm

Sau khi hiểu các thành phần cốt lõi và cơ chế hội thoại của AutoGen, mục này sẽ thông qua một ca thực chiến hoàn chỉnh để trình bày cụ thể cách áp dụng các đặc tính mới này. Chúng ta sẽ xây dựng một nhóm phát triển phần mềm mô phỏng, gồm nhiều Agent có kỹ năng chuyên môn khác nhau, cùng cộng tác hoàn thành một nhiệm vụ phát triển phần mềm thực tế.

(1) Mục tiêu nghiệp vụ

Mục tiêu của chúng ta là phát triển một ứng dụng web có chức năng rõ ràng: <strong>hiển thị giá Bitcoin hiện tại theo thời gian thực</strong>. Nhiệm vụ tuy nhỏ nhưng bao phủ đầy đủ các khâu điển hình của phát triển phần mềm: từ phân tích yêu cầu, lựa chọn công nghệ, hiện thực mã đến kiểm duyệt mã và kiểm thử cuối cùng. Điều này khiến nó trở thành cảnh lý tưởng để kiểm chứng quy trình cộng tác tự động của AutoGen.

(2) Vai trò nhóm Agent

Để mô phỏng quy trình phát triển phần mềm thực tế, chúng ta thiết kế bốn vai Agent có trách nhiệm rõ ràng:

- <strong>ProductManager (quản lý sản phẩm):</strong> chịu trách nhiệm chuyển yêu cầu mơ hồ của người dùng thành kế hoạch phát triển rõ ràng, có thể thực thi.
- <strong>Engineer (kỹ sư):</strong> dựa trên kế hoạch phát triển, chịu trách nhiệm viết mã ứng dụng cụ thể.
- <strong>CodeReviewer (người kiểm duyệt mã):</strong> chịu trách nhiệm kiểm duyệt mã kỹ sư gửi, đảm bảo chất lượng, khả năng đọc và độ vững chắc.
- <strong>UserProxy (đại diện người dùng):</strong> đại diện người dùng cuối, khởi phát nhiệm vụ ban đầu, đồng thời chịu trách nhiệm thực thi và xác minh mã bàn giao cuối cùng.

Cách phân chia vai trò này là bước then chốt trong thiết kế hệ thống đa Agent; nó phân rã nhiệm vụ phức tạp thành nhiều nhiệm vụ con do các “chuyên gia” lĩnh vực xử lý.

### 6.2.3 Hiện thực mã nguồn cốt lõi

Dưới đây, chúng ta sẽ phân tích từng bước mã nguồn cốt lõi của nhóm tự động hóa này.

(1) Cấu hình client mô hình

Mọi Agent dựa trên LLM đều cần một client mô hình để tương tác với mô hình ngôn ngữ. AutoGen `0.7.4` cung cấp `OpenAIChatCompletionClient` được chuẩn hóa, có thể dễ dàng kết nối với bất kỳ dịch vụ mô hình nào tương thích quy chuẩn OpenAI API (gồm dịch vụ chính thức OpenAI, Azure OpenAI và dịch vụ mô hình cục bộ như Ollama, v.v.).

Chúng ta tạo và cấu hình client mô hình thông qua một hàm độc lập, và quản lý API Key cùng địa chỉ dịch vụ qua biến môi trường; đây là thực tiễn kỹ thuật tốt, tăng tính linh hoạt và an toàn của mã.

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient

def create_openai_model_client():
    """Tạo và cấu hình client mô hình OpenAI"""
    return OpenAIChatCompletionClient(
        model=os.getenv("LLM_MODEL_ID", "gpt-4o"),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    )
```

(2) Định nghĩa vai trò Agent

Cốt lõi của việc định nghĩa Agent là viết system message chất lượng cao. System message giống như “chuẩn mực hành vi” và “kho kiến thức chuyên môn” đặt cho Agent; nó quy định chính xác vai trò, trách nhiệm, quy trình làm việc, thậm chí cách tương tác với các Agent khác. Một system message được thiết kế cẩn thận là chìa khóa đảm bảo hệ thống đa Agent cộng tác hiệu quả, chính xác. Trong nhóm phát triển phần mềm của chúng ta, mỗi vai trò đều có một hàm độc lập đóng gói định nghĩa của nó.

<strong>Quản lý sản phẩm (ProductManager)</strong>

Quản lý sản phẩm chịu trách nhiệm khởi động toàn bộ quy trình. System message của nó không chỉ định nghĩa trách nhiệm mà còn quy phạm cấu trúc đầu ra, và chứa chỉ thị rõ ràng dẫn dắt hội thoại chuyển sang mắt xích tiếp theo (kỹ sư).

```python
def create_product_manager(model_client):
    """Tạo Agent quản lý sản phẩm"""
    system_message = """Bạn là một quản lý sản phẩm giàu kinh nghiệm, chuyên phụ trách phân tích yêu cầu và lập kế hoạch dự án cho sản phẩm phần mềm.

Trách nhiệm cốt lõi của bạn gồm:
1. **Phân tích yêu cầu**: hiểu sâu nhu cầu người dùng, nhận diện chức năng cốt lõi và điều kiện biên
2. **Lập kế hoạch kỹ thuật**: dựa trên yêu cầu, xây dựng đường hiện thực kỹ thuật rõ ràng
3. **Đánh giá rủi ro**: nhận diện rủi ro kỹ thuật và vấn đề trải nghiệm người dùng tiềm ẩn
4. **Điều phối giao tiếp**: giao tiếp hiệu quả với kỹ sư và các thành viên nhóm khác

Khi nhận nhiệm vụ phát triển, hãy phân tích theo cấu trúc sau:
1. Hiểu và phân tích yêu cầu
2. Phân chia mô-đun chức năng
3. Gợi ý lựa chọn công nghệ
4. Sắp xếp ưu tiên hiện thực
5. Định nghĩa tiêu chí nghiệm thu

Hãy phản hồi ngắn gọn rõ ràng, và sau khi phân tích xong nói "Mời kỹ sư bắt đầu hiện thực"."""

    return AssistantAgent(
        name="ProductManager",
        model_client=model_client,
        system_message=system_message,
    )
```

<strong>Kỹ sư (Engineer)</strong>

System message của kỹ sư tập trung vào hiện thực kỹ thuật. Nó liệt kê chuyên môn kỹ thuật của kỹ sư, quy định các bước hành động cụ thể sau khi nhận nhiệm vụ, đồng thời cũng chứa chỉ thị dẫn dắt quy trình chuyển sang người kiểm duyệt mã.

```python
def create_engineer(model_client):
    """Tạo Agent kỹ sư phần mềm"""
    system_message = """Bạn là một kỹ sư phần mềm lão luyện, giỏi phát triển Python và xây dựng ứng dụng web.

Chuyên môn kỹ thuật của bạn gồm:
1. **Lập trình Python**: thành thạo cú pháp và thực tiễn tốt nhất của Python
2. **Phát triển web**: tinh thông các framework Streamlit, Flask, Django
3. **Tích hợp API**: có kinh nghiệm phong phú tích hợp API bên thứ ba
4. **Xử lý lỗi**: chú trọng độ vững chắc của mã và xử lý ngoại lệ

Khi nhận nhiệm vụ phát triển, hãy:
1. Phân tích kỹ yêu cầu kỹ thuật
2. Chọn phương án kỹ thuật phù hợp
3. Viết mã hiện thực hoàn chỉnh
4. Thêm chú thích và giải thích cần thiết
5. Cân nhắc tình huống biên và xử lý ngoại lệ

Hãy cung cấp mã hoàn chỉnh có thể chạy, và sau khi hoàn thành nói "Mời người kiểm duyệt mã kiểm tra"."""

    return AssistantAgent(
        name="Engineer",
        model_client=model_client,
        system_message=system_message,
    )
```

<strong>Người kiểm duyệt mã (CodeReviewer)</strong>

Định nghĩa người kiểm duyệt mã tập trung vào chất lượng, an toàn và quy phạm của mã. System message của nó liệt kê chi tiết trọng tâm và quy trình kiểm duyệt, đảm bảo cổng chất lượng trước khi bàn giao mã.

```python
def create_code_reviewer(model_client):
    """Tạo Agent người kiểm duyệt mã"""
    system_message = """Bạn là một chuyên gia kiểm duyệt mã giàu kinh nghiệm, tập trung vào chất lượng mã và thực tiễn tốt nhất.

Trọng tâm kiểm duyệt của bạn gồm:
1. **Chất lượng mã**: kiểm tra khả năng đọc, khả năng bảo trì và hiệu năng của mã
2. **Bảo mật**: nhận diện lỗ hổng bảo mật và điểm rủi ro tiềm ẩn
3. **Thực tiễn tốt nhất**: đảm bảo mã tuân thủ chuẩn ngành và thực tiễn tốt nhất
4. **Xử lý lỗi**: xác minh tính đầy đủ và hợp lý của xử lý ngoại lệ

Quy trình kiểm duyệt:
1. Đọc kỹ và hiểu logic mã
2. Kiểm tra quy phạm mã và thực tiễn tốt nhất
3. Nhận diện vấn đề và điểm cải thiện tiềm ẩn
4. Đưa ra gợi ý sửa cụ thể
5. Đánh giá chất lượng tổng thể của mã

Hãy đưa ra ý kiến kiểm duyệt cụ thể, sau khi hoàn thành nói "Kiểm duyệt mã hoàn tất, mời đại diện người dùng kiểm thử"."""

    return AssistantAgent(
        name="CodeReviewer",
        model_client=model_client,
        system_message=system_message,
    )
```

<strong>Đại diện người dùng (UserProxy)</strong>

`UserProxyAgent` là một Agent đặc biệt; nó không dựa vào LLM để phản hồi mà đóng vai đại diện người dùng trong hệ thống. Trường `description` của nó mô tả rõ trách nhiệm; đặc biệt quan trọng là nó chịu trách nhiệm phát chỉ thị `TERMINATE` sau khi nhiệm vụ cuối cùng hoàn thành, để kết thúc bình thường toàn bộ quy trình cộng tác.

```python
def create_user_proxy():
    """Tạo Agent đại diện người dùng"""
    return UserProxyAgent(
        name="UserProxy",
        description="""Đại diện người dùng, chịu trách nhiệm:
1. Đại diện người dùng nêu yêu cầu phát triển
2. Thực thi mã hiện thực cuối cùng
3. Xác minh chức năng có đúng mong đợi hay không
4. Cung cấp phản hồi và gợi ý từ người dùng

Sau khi hoàn thành kiểm thử hãy trả lời TERMINATE.""",
    )
```

Thông qua bốn hàm định nghĩa độc lập này, chúng ta không chỉ xây dựng một “nhóm ảo” đầy đủ chức năng, mà còn cho thấy “kỹ thuật prompt” thông qua system message là mắt xích cốt lõi để thiết kế ứng dụng đa Agent hiệu quả.

(3) Định nghĩa quy trình cộng tác nhóm

Trong ca này, quy trình phát triển phần mềm tương đối cố định (yêu cầu -> viết mã -> kiểm duyệt -> kiểm thử), vì vậy `RoundRobinGroupChat` (nhóm chat luân phiên) là lựa chọn lý tưởng. Chúng ta thêm bốn Agent vào danh sách người tham gia theo thứ tự logic nghiệp vụ.

```python
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

# Định nghĩa quy tắc chat và cộng tác của nhóm
team_chat = RoundRobinGroupChat(
    participants=[
        product_manager,
        engineer,
        code_reviewer,
        user_proxy
    ],
    termination_condition=TextMentionTermination("TERMINATE"),
    max_turns=20,
)
```

- <strong>Thứ tự người tham gia:</strong> thứ tự danh sách `participants` quyết định thứ tự phát biểu của Agent.
- <strong>Điều kiện dừng:</strong> `termination_condition` là then chốt kiểm soát khi nào quy trình cộng tác kết thúc. Ở đây chúng ta đặt khi bất kỳ tin nhắn nào chứa từ khóa "TERMINATE" thì hội thoại kết thúc. Trong thiết kế của chúng ta, chỉ thị này do `UserProxy` phát ra sau khi hoàn thành kiểm thử cuối cùng.
- <strong>Số lượt tối đa:</strong> `max_turns` là van an toàn, ngăn hội thoại rơi vào vòng lặp vô hạn, tránh tiêu hao tài nguyên không cần thiết.

(4) Khởi động và chạy

Do AutoGen `0.7.4` áp dụng kiến trúc bất đồng bộ, việc khởi động và chạy toàn bộ quy trình cộng tác được hoàn thành trong một hàm bất đồng bộ, và cuối cùng thực thi qua `asyncio.run()`.

```python
async def run_software_development_team():
    # ... khởi tạo client và Agent ...

    # Định nghĩa mô tả nhiệm vụ
    task = """Chúng ta cần phát triển một ứng dụng hiển thị giá Bitcoin, yêu cầu cụ thể như sau:
            Chức năng cốt lõi:
            - Hiển thị giá Bitcoin hiện tại theo thời gian thực (USD)
            - Hiển thị xu hướng biến động giá 24 giờ (tỷ lệ và mức tăng/giảm)
            - Cung cấp chức năng làm mới giá

            Yêu cầu kỹ thuật:
            - Dùng framework Streamlit tạo ứng dụng web
            - Giao diện đơn giản đẹp mắt, thân thiện với người dùng
            - Thêm xử lý lỗi và trạng thái tải phù hợp

            Hãy để nhóm cộng tác hoàn thành nhiệm vụ này, từ phân tích yêu cầu đến hiện thực cuối cùng."""

    # Thực thi bất đồng bộ cộng tác nhóm, và xuất luồng quá trình hội thoại
    result = await Console(team_chat.run_stream(task=task))
    return result

# Điểm vào chương trình chính
if __name__ == "__main__":
    result = asyncio.run(run_software_development_team())
```

Khi chương trình chạy, `task` được truyền vào `team_chat` làm tin nhắn ban đầu; quản lý sản phẩm là người tham gia đầu tiên nhận tin nhắn, sau đó toàn bộ quy trình cộng tác tự động bắt đầu.

(5) Hiệu quả cộng tác dự kiến

Khi chạy nhóm phát triển phần mềm này, có thể quan sát một quy trình cộng tác hoàn chỉnh:

```bash
🔧 Đang khởi tạo client mô hình...
👥 Đang tạo nhóm Agent...
🚀 Khởi động cộng tác nhóm phát triển phần mềm AutoGen...
============================================================
---------- TextMessage (user) ----------
Chúng ta cần phát triển một ứng dụng hiển thị giá Bitcoin, yêu cầu cụ thể như sau:
...
Hãy để nhóm cộng tác hoàn thành nhiệm vụ này, từ phân tích yêu cầu đến hiện thực cuối cùng.
---------- TextMessage (ProductManager) ----------
### 1. Hiểu và phân tích yêu cầu
...
Mời kỹ sư bắt đầu hiện thực.
---------- TextMessage (Engineer) ----------
### Triển khai phương án kỹ thuật
...
Mời người kiểm duyệt mã kiểm tra.
---------- TextMessage (CodeReviewer) ----------
### Kiểm duyệt mã
...
Kiểm duyệt mã hoàn tất, mời đại diện người dùng kiểm thử.
---------- TextMessage (UserProxy) ----------
Đã hoàn thành yêu cầu
---------- TextMessage (ProductManager) ----------
Tuyệt vời, cảm ơn phản hồi của bạn! Nếu trong quá trình sử dụng có bất kỳ vấn đề gì, hoặc có nhu cầu chức năng và gợi ý cải thiện khác, hãy thông báo cho chúng tôi bất cứ lúc nào. Chúng tôi sẽ tiếp tục hỗ trợ và cải thiện. Mong bạn có trải nghiệm vui vẻ với ứng dụng của chúng tôi!
---------- TextMessage (Engineer) ----------
Rất vui khi nghe dự án hoàn thành thuận lợi. Nếu bạn hoặc người dùng có bất kỳ vấn đề gì hoặc cần hỗ trợ, hãy liên hệ chúng tôi bất cứ lúc nào. Cảm ơn bạn đã ủng hộ công việc của chúng tôi; hãy cùng nhau đảm bảo ứng dụng chạy ổn định và không ngừng tối ưu trải nghiệm người dùng!
---------- TextMessage (CodeReviewer) ----------
Cảm ơn rất nhiều vì nỗ lực và cộng tác của mọi người, giúp dự án hoàn thành thuận lợi. Nếu tương lai có nhu cầu hỗ trợ kỹ thuật hoặc điểm cần cải thiện, chúng tôi sẵn lòng đóng góp cho việc tối ưu liên tục dự án. Mong người dùng có trải nghiệm mượt mà, đồng thời hoan nghênh thêm phản hồi và gợi ý. Một lần nữa cảm ơn sự cộng tác của nhóm!
---------- TextMessage (UserProxy) ----------
Enter your response: TERMINATE
============================================================
✅ Cộng tác nhóm hoàn thành!

📋 Tóm tắt kết quả cộng tác:
- Số Agent tham gia: 4
- Trạng thái hoàn thành nhiệm vụ: thành công
```

Toàn bộ quá trình cộng tác thể hiện ưu thế của framework AutoGen: <strong>cộng tác do hội thoại tự nhiên dẫn dắt</strong>, <strong>phân công vai trò chuyên môn hóa</strong>, <strong>quản lý quy trình tự động</strong> và <strong>vòng khép kín phát triển hoàn chỉnh</strong>.

### 6.2.4 Phân tích ưu điểm và hạn chế của AutoGen

Mọi framework kỹ thuật đều có tình huống áp dụng và đánh đổi thiết kế riêng. Trong mục này, chúng ta sẽ phân tích khách quan ưu điểm cốt lõi của AutoGen và những hạn chế, thách thức có thể gặp trong ứng dụng thực tế.

(1) Ưu điểm

- Như ca cho thấy, chúng ta không cần thiết kế máy trạng thái hoặc logic điều khiển phức tạp cho nhóm Agent, mà ánh xạ tự nhiên một quy trình phát triển phần mềm hoàn chỉnh thành hội thoại giữa quản lý sản phẩm, kỹ sư và người kiểm duyệt. Cách này gần hơn với mô hình cộng tác của nhóm người, hạ thấp rõ rệt ngưỡng mô hình hóa nhiệm vụ phức tạp. Nhà phát triển có thể tập trung hơn vào định nghĩa “ai (vai trò)” và “làm gì (trách nhiệm)”, thay vì “làm thế nào (điều khiển quy trình)”.
- Framework cho phép trao cho mỗi Agent vai trò chuyên môn hóa cao thông qua system message. Trong ca, `ProductManager` tập trung vào yêu cầu, còn `CodeReviewer` tập trung vào chất lượng. Một Agent được thiết kế cẩn thận có thể được tái sử dụng trong các dự án khác nhau, dễ bảo trì và mở rộng.
- Với nhiệm vụ có quy trình, cơ chế như `RoundRobinGroupChat` cung cấp quy trình cộng tác rõ ràng, có thể dự đoán. Đồng thời, thiết kế `UserProxyAgent` cung cấp giao diện tự nhiên cho “con người trong vòng lặp” (Human-in-the-loop). Nó có thể là người khởi phát nhiệm vụ, cũng có thể là người giám sát quy trình và người nghiệm thu cuối cùng. Thiết kế này đảm bảo hệ thống tự động luôn nằm dưới sự giám sát của con người.

(2) Hạn chế

- Mặc dù `RoundRobinGroupChat` cung cấp quy trình tuần tự, hội thoại dựa trên LLM về bản chất có tính không chắc chắn. Agent có thể sinh phản hồi lệch mong đợi, khiến hội thoại đi vào nhánh bất ngờ, thậm chí rơi vào vòng lặp.
- Khi kết quả làm việc của nhóm Agent không đạt mong đợi, quá trình gỡ lỗi có thể rất khó khăn. Khác với chương trình truyền thống, chúng ta không nhận được ngăn xếp lỗi rõ ràng mà là một chuỗi dài lịch sử hội thoại. Đây được gọi là bài toán “gỡ lỗi hội thoại”.

(3) Bổ sung cấu hình cho mô hình không phải OpenAI

Nếu muốn dùng mô hình không thuộc dòng OpenAI (như DeepSeek, Qwen, v.v.), trong phiên bản 0.7.4 cần truyền từ điển thông tin mô hình vào tham số của `OpenAIChatCompletionClient`. Lấy DeepSeek làm ví dụ:

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    model_info={
        "function_calling": True,
        "max_tokens": 4096,
        "context_length": 32768,
        "vision": False,
        "json_output": True,
        "family": "deepseek",
        "structured_output": True,
    }
)
```

Từ điển `model_info` này giúp AutoGen hiểu ranh giới năng lực của mô hình, từ đó thích ứng tốt hơn với các dịch vụ mô hình khác nhau.



## 6.3 Framework hai: AgentScope

Nếu triết lý thiết kế của AutoGen là “lấy hội thoại dẫn dắt cộng tác”, thì AgentScope đại diện cho một con đường kỹ thuật khác: <strong>nền tảng đa Agent ưu tiên kỹ thuật hóa</strong>. AgentScope do Viện DAMO của Alibaba phát triển, được thiết kế riêng cho việc xây dựng ứng dụng đa Agent quy mô lớn, độ tin cậy cao. Nó không chỉ cung cấp giao diện lập trình trực quan dễ dùng, mà quan trọng hơn là tích hợp sẵn các đặc tính cấp doanh nghiệp như triển khai phân tán, phục hồi sau lỗi, khả năng quan sát, khiến nó đặc biệt phù hợp để xây dựng ứng dụng môi trường sản xuất cần chạy ổn định lâu dài.

### 6.3.1 Thiết kế của AgentScope

So với AutoGen, khác biệt cốt lõi của AgentScope nằm ở <strong>kiến trúc thiết kế hướng tin nhắn</strong> và <strong>thực tiễn kỹ thuật cấp công nghiệp</strong>. Nếu AutoGen giống một “xưởng hội thoại” linh hoạt, thì AgentScope là một “hệ điều hành Agent” hoàn chỉnh, cung cấp cho nhà phát triển hỗ trợ toàn vòng đời từ phát triển, kiểm thử đến triển khai. Khác với thiết kế kế thừa mà nhiều framework áp dụng, AgentScope chọn <strong>kiến trúc kết hợp</strong> và <strong>mô hình hướng tin nhắn</strong>. Thiết kế này không chỉ tăng mức mô-đun hóa của hệ thống mà còn đặt nền tảng cho hiệu năng đồng thời và năng lực phân tán xuất sắc của nó.

(1) Hệ thống kiến trúc phân tầng

Như trong Hình 6.2, AgentScope áp dụng thiết kế mô-đun phân tầng rõ ràng, từ các thành phần nền tảng tầng dưới đến biên soạn ứng dụng tầng trên, tạo thành một hệ sinh thái phát triển Agent hoàn chỉnh.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/6-figures/03.png" alt="" width="90%"/>
  <p>Hình 6.2 Kiến trúc AgentScope</p>
</div>

Trong kiến trúc này, tầng dưới cùng là <strong>tầng thành phần nền tảng (Foundational Components)</strong>, cung cấp các khối xây dựng cốt lõi cho toàn bộ framework. Thành phần `Message` định nghĩa định dạng tin nhắn thống nhất, hỗ trợ từ tương tác văn bản đơn giản đến nội dung đa phương thức phức tạp; thành phần `Memory` cung cấp quản lý bộ nhớ ngắn hạn và dài hạn; tầng `Model API` trừu tượng hóa việc gọi các mô hình ngôn ngữ lớn khác nhau; còn thành phần `Tool` đóng gói năng lực tương tác của Agent với thế giới bên ngoài.

Trên các thành phần nền tảng, <strong>tầng hạ tầng Agent (Agent-level Infrastructure)</strong> cung cấp mức trừu tượng cao hơn. Tầng này không chỉ gồm các Agent dựng sẵn khác nhau (như Agent sử dụng trình duyệt, Agent nghiên cứu chuyên sâu), mà còn hiện thực mô hình ReAct kinh điển, hỗ trợ các đặc tính nâng cao như hook Agent, gọi công cụ song song, quản lý trạng thái. Đặc biệt đáng chú ý là tầng này hỗ trợ native <strong>thực thi bất đồng bộ và điều khiển thời gian thực</strong>, đây là ưu thế quan trọng của AgentScope so với các framework khác.

<strong>Tầng cộng tác đa Agent (Multi-Agent Cooperation)</strong> là nơi đổi mới cốt lõi của AgentScope. `MsgHub` là trung tâm tin nhắn, chịu trách nhiệm định tuyến tin nhắn và quản lý trạng thái giữa các Agent; hệ thống `Pipeline` cung cấp năng lực biên soạn quy trình làm việc linh hoạt, hỗ trợ nhiều chế độ thực thi như tuần tự, đồng thời. Thiết kế này cho phép nhà phát triển dễ dàng xây dựng các tình huống cộng tác đa Agent phức tạp.

Tầng trên cùng là <strong>tầng triển khai và phát triển (Deployment & Development)</strong>, thể hiện sự coi trọng kỹ thuật hóa của AgentScope. `AgentScope Runtime` cung cấp môi trường chạy cấp sản xuất, còn `AgentScope Studio` cung cấp cho nhà phát triển chuỗi công cụ phát triển trực quan hoàn chỉnh.

(2) Hướng tin nhắn

Đổi mới cốt lõi của AgentScope nằm ở <strong>kiến trúc hướng tin nhắn</strong>. Trong kiến trúc này, mọi tương tác của Agent đều được trừu tượng hóa thành việc gửi và nhận <strong>tin nhắn</strong>, thay vì gọi hàm truyền thống.

```python
from agentscope.message import Msg

# Cấu trúc chuẩn của tin nhắn
message = Msg(
    name="Alice",           # Tên người gửi
    content="Hello, Bob!",  # Nội dung tin nhắn
    role="user",           # Loại vai trò
    metadata={             # Thông tin siêu dữ liệu
        "timestamp": "2024-01-15T10:30:00Z",
        "message_type": "text",
        "priority": "normal"
    }
)
```

Lấy tin nhắn làm đơn vị tương tác cơ bản mang lại một số ưu thế then chốt:

- <strong>Tách rời bất đồng bộ</strong>: bên gửi và bên nhận tin nhắn tách rời về thời gian, không cần chờ nhau, tự nhiên hỗ trợ tình huống đồng thời cao.
- <strong>Minh bạch vị trí</strong>: Agent không cần quan tâm Agent khác ở tiến trình cục bộ hay máy chủ từ xa; hệ thống tin nhắn tự động xử lý định tuyến.
- <strong>Khả năng quan sát</strong>: mỗi tin nhắn đều có thể được ghi lại, theo dõi và phân tích, đơn giản hóa rất nhiều việc gỡ lỗi và giám sát hệ thống phức tạp.
- <strong>Độ tin cậy</strong>: tin nhắn có thể được lưu trữ bền vững và thử lại; ngay cả khi hệ thống gặp sự cố vẫn có thể đảm bảo tính nhất quán cuối cùng của tương tác, nâng cao khả năng chịu lỗi.

(3) Quản lý vòng đời Agent

Trong AgentScope, mỗi Agent có vòng đời rõ ràng (khởi tạo, chạy, tạm dừng, hủy, v.v.), được hiện thực dựa trên lớp cơ sở thống nhất `AgentBase`. Nhà phát triển thường chỉ cần quan tâm phương thức cốt lõi `reply`.

```python
from agentscope.agents import AgentBase

class CustomAgent(AgentBase):
    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        # Logic khởi tạo Agent

    def reply(self, x: Msg) -> Msg:
        # Logic phản hồi cốt lõi của Agent
        response = self.model(x.content)
        return Msg(name=self.name, content=response, role="assistant")

    def observe(self, x: Msg) -> None:
        # Logic quan sát của Agent (tùy chọn)
        self.memory.add(x)
```

Mô hình thiết kế này tách logic bên trong của Agent khỏi giao tiếp bên ngoài; nhà phát triển chỉ cần định nghĩa trong phương thức `reply` cách Agent “suy nghĩ và phản hồi”.

(4) Cơ chế truyền tin

AgentScope tích hợp sẵn một <strong>trung tâm tin nhắn (MsgHub)</strong>, là trung tâm của toàn bộ kiến trúc hướng tin nhắn. MsgHub không chỉ chịu trách nhiệm định tuyến và phân phối tin nhắn, mà còn tích hợp các chức năng nâng cao như lưu trữ bền vững và giao tiếp phân tán. Nó có các đặc điểm sau.

- <strong>Định tuyến tin nhắn linh hoạt</strong>: hỗ trợ nhiều chế độ giao tiếp như điểm-điểm, quảng bá, đa hướng, có thể xây dựng mạng tương tác linh hoạt phức tạp.
- <strong>Lưu trữ tin nhắn bền vững</strong>: có thể tự động lưu tất cả tin nhắn vào cơ sở dữ liệu (như SQLite, MongoDB), đảm bảo trạng thái nhiệm vụ chạy dài hạn có thể được phục hồi.
- <strong>Hỗ trợ phân tán native</strong>: đây là đặc tính biểu tượng của AgentScope. Agent có thể được triển khai trên các tiến trình hoặc máy chủ khác nhau; `MsgHub` sẽ tự động xử lý giao tiếp giữa các nút qua RPC (gọi thủ tục từ xa), hoàn toàn minh bạch với nhà phát triển.

Những năng lực kỹ thuật hóa do kiến trúc tầng dưới cung cấp này khiến AgentScope có ưu thế hơn các framework hướng hội thoại truyền thống khi xử lý tình huống ứng dụng phức tạp cần đồng thời cao, độ tin cậy cao. Tất nhiên, điều này cũng đòi hỏi nhà phát triển hiểu và thích nghi với mô hình lập trình bất đồng bộ hướng tin nhắn.

Trong mục tiếp theo, chúng ta sẽ đi qua một ca thực chiến cụ thể – trò chơi ma sói Tam Quốc – để trải nghiệm sâu năng lực của framework AgentScope, đặc biệt là ưu thế của nó khi xử lý tương tác đồng thời.

### 6.3.2 Trò chơi ma sói Tam Quốc

Để hiểu sâu kiến trúc hướng tin nhắn và năng lực cộng tác đa Agent của AgentScope, chúng ta sẽ xây dựng một trò chơi “ma sói Tam Quốc” kết hợp yếu tố văn hóa cổ điển Trung Hoa. Ca này không chỉ thể hiện ưu thế của AgentScope khi xử lý tương tác đa Agent phức tạp, mà quan trọng hơn là trình diễn cách phát huy sức mạnh của kiến trúc hướng tin nhắn trong một tình huống cần <strong>cộng tác thời gian thực</strong>, <strong>nhập vai</strong> và <strong>đấu trí chiến lược</strong>. Khác với ma sói truyền thống, “ma sói Tam Quốc” của chúng ta đưa các nhân vật kinh điển như Lưu Bị, Quan Vũ, Gia Cát Lượng vào trò chơi; mỗi Agent không chỉ hoàn thành nhiệm vụ cơ bản của ma sói (ma sói giết người, tiên tri kiểm tra, dân làng suy luận), mà còn thể hiện đặc điểm tính cách và mô hình hành vi của nhân vật Tam Quốc tương ứng. Thiết kế này cho phép chúng ta quan sát biểu hiện của AgentScope trong <strong>mô hình hóa vai trò đa tầng</strong>.

(1) Thiết kế kiến trúc và thành phần cốt lõi

Thiết kế hệ thống của ca này tuân theo nguyên tắc tách rời phân tầng, chia logic trò chơi thành ba tầng độc lập; mỗi tầng ánh xạ đến một hoặc nhiều thành phần cốt lõi của AgentScope:

- <strong>Tầng điều khiển trò chơi (Game Control Layer)</strong>: lớp `ThreeKingdomsWerewolfGame` làm bộ điều khiển chính, chịu trách nhiệm duy trì trạng thái toàn cục (như danh sách người chơi còn sống, giai đoạn trò chơi hiện tại), đẩy quy trình trò chơi (gọi giai đoạn ban đêm, giai đoạn ban ngày) và phán định thắng thua.
- <strong>Tầng tương tác Agent (Agent Interaction Layer)</strong>: hoàn toàn do `MsgHub` dẫn dắt. Mọi giao tiếp giữa các Agent, dù là thương lượng bí mật giữa ma sói hay tranh luận công khai ban ngày, đều được định tuyến và phân phối qua trung tâm tin nhắn.
- <strong>Tầng mô hình hóa vai trò (Role Modeling Layer)</strong>: mỗi người chơi là một thực thể dựa trên `DialogAgent`. Thông qua system prompt được thiết kế cẩn thận, chúng ta truyền cho mỗi Agent hai thân phận “vai trò trò chơi” và “nhân cách Tam Quốc”.

(2) Quy trình trò chơi hướng tin nhắn

Thiết kế cốt lõi nhất của ca này là dùng <strong>hướng tin nhắn</strong> thay cho <strong>máy trạng thái</strong> để quản lý quy trình trò chơi. Trong hiện thực truyền thống, việc chuyển giai đoạn trò chơi thường do một máy trạng thái tập trung (State Machine) kiểm soát. Còn dưới mô hình AgentScope, quy trình trò chơi được mô hình hóa tự nhiên thành một loạt mô hình tương tác tin nhắn đã định nghĩa.

Ví dụ, việc hiện thực giai đoạn ma sói không phải là một lời gọi hàm đơn giản, mà thông qua `MsgHub` tạo động một kênh giao tiếp riêng tư tạm thời chỉ gồm các người chơi ma sói:

```python
async def werewolf_phase(self, round_num: int):
    """Giai đoạn ma sói - thể hiện mô hình cộng tác hướng tin nhắn"""
    if not self.werewolves:
        return None

    # Thiết lập kênh giao tiếp riêng cho ma sói qua trung tâm tin nhắn
    async with MsgHub(
        self.werewolves,
        enable_auto_broadcast=True,
        announcement=await self.moderator.announce(
            f"Ma sói, hãy thảo luận mục tiêu giết đêm nay. Người chơi còn sống: {format_player_list(self.alive_players)}"
        ),
    ) as werewolves_hub:
        # Giai đoạn thảo luận: ma sói trao đổi chiến lược qua tin nhắn
        for _ in range(MAX_DISCUSSION_ROUND):
            for wolf in self.werewolves:
                await wolf(structured_model=DiscussionModelCN)

        # Giai đoạn bỏ phiếu: thu thập và thống kê quyết định giết của ma sói
        werewolves_hub.set_auto_broadcast(False)
        kill_votes = await fanout_pipeline(
            self.werewolves,
            msg=await self.moderator.announce("Hãy chọn mục tiêu giết"),
            structured_model=WerewolfKillModelCN,
            enable_gather=False,
        )
```

Ưu thế của thiết kế này là logic trò chơi được biểu đạt rõ ràng thành “trong ngữ cảnh cụ thể, trao đổi tin nhắn theo mô hình nào”, thay vì một chuỗi chuyển trạng thái cứng nhắc. Các giai đoạn như thảo luận ban ngày (quảng bá toàn viên), tiên tri kiểm tra (yêu cầu điểm-điểm) cũng tuân theo mô hình thiết kế tương tự.

(3) Dùng đầu ra có cấu trúc ràng buộc quy tắc trò chơi

Một thách thức then chốt của trò chơi ma sói là đảm bảo hành vi của Agent tuân thủ quy tắc trò chơi. <strong>Cơ chế đầu ra có cấu trúc</strong> của AgentScope cung cấp giải pháp cho vấn đề này. Chúng ta định nghĩa mô hình dữ liệu nghiêm ngặt cho các hành vi trò chơi khác nhau:

```python
class DiscussionModelCN(BaseModel):
    """Định dạng đầu ra giai đoạn thảo luận"""
    reach_agreement: bool = Field(
        description="Đã đạt ý kiến thống nhất hay chưa",
        default=False
    )
    confidence_level: int = Field(
        description="Mức độ tự tin với suy luận hiện tại (1-10)",
        ge=1, le=10,
        default=5
    )
    key_evidence: Optional[str] = Field(
        description="Bằng chứng then chốt ủng hộ quan điểm của bạn",
        default=None
    )

class WitchActionModelCN(BaseModel):
    """Định dạng đầu ra hành động của phù thủy"""
    use_antidote: bool = Field(description="Có dùng thuốc giải hay không")
    use_poison: bool = Field(description="Có dùng thuốc độc hay không")
    target_name: Optional[str] = Field(description="Tên người chơi là mục tiêu thuốc độc")
```

Bằng cách này, chúng ta không chỉ đảm bảo <strong>tính nhất quán định dạng</strong> đầu ra của Agent, mà quan trọng hơn là hiện thực <strong>ràng buộc tự động quy tắc trò chơi</strong>. Ví dụ, Agent phù thủy không thể đồng thời dùng thuốc giải và thuốc độc cho cùng một mục tiêu; tiên tri mỗi đêm chỉ có thể kiểm tra một người chơi; những ràng buộc này đều được thực thi tự động thông qua định nghĩa trường và logic xác minh của mô hình dữ liệu.

(4) Thách thức kép của mô hình hóa vai trò

Trong ca này, thách thức kỹ thuật thú vị nhất là làm sao để Agent đồng thời đóng tốt hai tầng vai trò: <strong>vai trò chức năng trò chơi</strong> (ma sói, tiên tri, v.v.) và <strong>vai trò nhân cách văn hóa</strong> (Lưu Bị, Tào Tháo, v.v.). Chúng ta giải quyết vấn đề này bằng kỹ thuật prompt:

```python
def get_role_prompt(role: str, character: str) -> str:
    """Lấy prompt vai trò - kết hợp quy tắc trò chơi và tính cách nhân vật"""
    base_prompt = f"""Bạn là {character}, trong trò chơi ma sói Tam Quốc này bạn đóng vai {role}.

Quy tắc quan trọng:
1. Bạn chỉ có thể tham gia trò chơi thông qua hội thoại và suy luận
2. Không được thử gọi bất kỳ công cụ hoặc hàm bên ngoài nào
3. Trả lời nghiêm ngặt theo định dạng JSON được yêu cầu

Đặc điểm vai trò:
"""

    if role == "狼人":  # ma sói
        return base_prompt + f"""
- Bạn thuộc phe ma sói, mục tiêu là tiêu diệt tất cả người tốt
- Ban đêm có thể thương lượng với ma sói khác về mục tiêu giết
- Ban ngày phải che giấu thân phận, đánh lạc hướng người tốt
- Nói và hành động theo tính cách của {character}
"""
```

Thiết kế này cho chúng ta quan sát một hiện tượng thú vị: các nhân vật Tam Quốc khác nhau khi đóng cùng một vai trò trò chơi sẽ thể hiện chiến lược và phong cách nói chuyện hoàn toàn khác nhau. Ví dụ, “Tào Tháo” đóng ma sói có thể xảo quyệt và giỏi ngụy trang hơn, còn “Trương Phi” đóng ma sói có thể trực tiếp và bốc đồng hơn.

(5) Xử lý đồng thời và cơ chế chịu lỗi

Kiến trúc bất đồng bộ của AgentScope phát huy vai trò quan trọng trong trò chơi đa Agent này. Trò chơi thường có tình huống cần <strong>thu thập quyết định của nhiều Agent cùng lúc</strong>, ví dụ giai đoạn bỏ phiếu:

```python
# Thu thập song song quyết định bỏ phiếu của tất cả người chơi
vote_msgs = await fanout_pipeline(
    self.alive_players,
    await self.moderator.announce("Hãy bỏ phiếu chọn người chơi cần loại bỏ"),
    structured_model=get_vote_model_cn(self.alive_players),
    enable_gather=False,
)
```

`fanout_pipeline` cho phép chúng ta song song gửi cùng một tin nhắn đến tất cả Agent và thu thập phản hồi của chúng một cách bất đồng bộ. Điều này không chỉ nâng cao hiệu quả thực thi trò chơi, mà quan trọng hơn là mô phỏng tình huống “bỏ phiếu đồng thời” trong trò chơi ma sói thật. Đồng thời, chúng ta thêm xử lý chịu lỗi ở các khâu then chốt:

```python
try:
    response = await wolf(
        "Hãy phân tích tình hình hiện tại và nêu quan điểm của bạn.",
        structured_model=DiscussionModelCN
    )
except Exception as e:
    print(f"⚠️ {wolf.name} gặp lỗi khi thảo luận: {e}")
    # Tạo phản hồi mặc định, đảm bảo trò chơi tiếp tục
    default_response = DiscussionModelCN(
        reach_agreement=False,
        confidence_level=5,
        key_evidence="Tạm thời không thể phân tích"
    )
```

Thiết kế này đảm bảo ngay cả khi một Agent gặp bất thường, toàn bộ quy trình trò chơi vẫn tiếp tục.

(6) Đầu ra ca và tổng kết

Để cảm nhận trực quan hơn cơ chế vận hành của AgentScope, dưới đây là một đoạn nhật ký chạy thật trích từ giai đoạn ban đêm của trò chơi, thể hiện quá trình hai Agent ma sói đóng vai “Tôn Quyền” và “Chu Du” thương lượng bí mật và thực hiện giết người.

```
🎮 Chào mừng đến với ma sói Tam Quốc!

=== Khởi tạo trò chơi ===
Quản trò: 📢 【Tôn Quyền】Bạn đóng vai ma sói trong trò chơi ma sói Tam Quốc này; nhân vật của bạn là Tôn Quyền. Ban đêm có thể giết một người chơi
Quản trò: 📢 【Chu Du】Bạn đóng vai ma sói trong trò chơi ma sói Tam Quốc này; nhân vật của bạn là Chu Du. Ban đêm có thể giết một người chơi
...

Quản trò: 📢 Trò chơi ma sói Tam Quốc bắt đầu! Người tham gia: Tôn Quyền, Chu Du, Tào Tháo, Trương Phi, Tư Mã Ý, Triệu Vân
✅ Thiết lập trò chơi hoàn tất, tổng cộng 6 người chơi

=== Vòng chơi thứ 1 ===
🌙 Đêm thứ 1 buông xuống, trời tối xin nhắm mắt...

【Giai đoạn ma sói】
Quản trò: 📢 🐺 Ma sói xin mở mắt, chọn mục tiêu giết đêm nay...
Quản trò: 📢 Ma sói, hãy thảo luận mục tiêu giết đêm nay. Người chơi còn sống: Tôn Quyền, Chu Du, Tào Tháo, Trương Phi, Tư Mã Ý, Triệu Vân

Tôn Quyền: Đêm nay chúng ta nên loại bỏ Chu Du; người này mưu trí hơn người, đe dọa chúng ta rất lớn.
Chu Du: Tôn Quyền, bạn nói có lý. Nhưng Chu Du tuy có trí, chưa chắc là mối đe dọa lớn nhất đêm nay. Thế lực Tào Tháo hùng mạnh, nếu không sớm loại bỏ, e rằng bất lợi cho chúng ta.
Tôn Quyền: Tào Tháo đúng là mối đe dọa, nhưng nếu Chu Du còn sống, hắn có thể nhìn thấu mưu kế của chúng ta. Chi bằng giải quyết mối nguy trước mắt.
Chu Du: Tôn Quyền, lo lắng của bạn không phải không có lý. Nhưng nếu Tào Tháo chống lại chúng ta, hắn có thể liên kết các thế lực khác tạo thành mối đe dọa lớn hơn.
Tôn Quyền: Bạn nói cũng có lý; việc Tào Tháo liên kết quả thật phiền phức. Vậy chúng ta đối phó Tào Tháo trước.
Chu Du: Tốt, Tôn Quyền. Tào Tháo mới là mục tiêu ưu tiên đêm nay của chúng ta.

Quản trò: 📢 Hãy chọn mục tiêu giết
Tôn Quyền: Tôi đồng ý, Tào Tháo phải bị loại bỏ.
Chu Du: Tôi đồng ý, Tào Tháo là mục tiêu chúng ta cần giải quyết đêm nay.

【Giai đoạn tiên tri】
Quản trò: 📢 🔮 Tiên tri xin mở mắt, chọn người chơi cần kiểm tra...
Tào Tháo: Tôi muốn kiểm tra Tôn Quyền.
Quản trò: 📢 Kết quả kiểm tra: Tôn Quyền là ma sói

【Giai đoạn phù thủy】
Quản trò: 📢 🧙‍♀️ Phù thủy xin mở mắt...
Quản trò: 📢 Đêm nay Tào Tháo bị ma sói giết
Trương Phi: Đêm qua tôi dùng thuốc giải cứu Tào Tháo; hiện thuốc giải đã dùng hết.
Quản trò: 📢 Bạn đã dùng thuốc giải cứu Tào Tháo

Quản trò: 📢 Đêm qua bình yên vô sự, không ai chết.

【Giai đoạn thảo luận ban ngày】
Quản trò: 📢 ☀️ Ngày thứ 1 đã sáng, mọi người xin mở mắt...
Quản trò: 📢 Bây giờ bắt đầu thảo luận tự do. Người chơi còn sống: Tôn Quyền, Chu Du, Tào Tháo, Trương Phi, Tư Mã Ý, Triệu Vân

Tôn Quyền: Chư vị, thế lực Tào Tháo hùng mạnh, là mối đe dọa tiềm ẩn với tất cả chúng ta. Đêm nay tôi đề nghị chúng ta tập trung sức lực đối phó hắn.
Chu Du: Tôn Quyền nói rất đúng; Tào Tháo không chỉ mạnh mà còn có thể liên minh với người chơi khác, tạo mối đe dọa lớn hơn.
Tào Tháo: Đêm qua tôi kiểm tra Tôn Quyền, vốn tưởng hắn là người tốt, nhưng kết quả quản trò đưa ra lại là ma sói. Điều này cho thấy có ma sói đang nói dối.
Trương Phi: Đêm qua tôi thật sự đã cứu Tào Tháo, cho thấy hắn bị ma sói tấn công. Nhưng kết quả Tào Tháo kiểm tra Tôn Quyền khiến người ta nghi ngờ.
Tư Mã Ý: Kết quả kiểm tra của Tào Tháo và hành động cứu người của Trương Phi dường như mâu thuẫn; chúng ta cần thêm thông tin để phán đoán ai là ma sói.
Triệu Vân: Tình hình đúng là phức tạp; chúng ta cần phân tích kỹ phát biểu của các bên.

【Giai đoạn bỏ phiếu】
Quản trò: 📢 Hãy bỏ phiếu chọn người chơi cần loại bỏ

Tôn Quyền: Mối đe dọa của Tào Tháo vẫn rất lớn; tôi kiên quyết cho rằng nên bỏ phiếu cho hắn.
Chu Du: Dựa trên tình hình đêm qua, tôi cho rằng chúng ta nên bỏ phiếu cho Tào Tháo trước; hắn là mối đe dọa lớn nhất.
Tào Tháo: Tôi chọn bỏ phiếu cho Tôn Quyền. Theo phản hồi của quản trò, Tôn Quyền đúng là ma sói.
Trương Phi: Tôi kiên trì sự thật đêm qua đã cứu Tào Tháo, nhưng việc Tôn Quyền bị phát hiện là ma sói khiến tôi bối rối.
Tư Mã Ý: Chúng ta cần thêm thông tin để phán đoán ai là ma sói.

[Trò chơi tiếp tục...]
```

### 6.3.3 Phân tích ưu điểm và hạn chế của AgentScope

Qua ca “ma sói Tam Quốc” này, chúng ta đã trải nghiệm sâu ưu thế cốt lõi của framework AgentScope. Lấy kiến trúc hướng tin nhắn làm cốt lõi, framework ánh xạ quy trình trò chơi phức tạp một cách thanh lịch thành một loạt sự kiện truyền tin đồng thời, bất đồng bộ, từ đó tránh sự cứng nhắc và phức tạp của máy trạng thái truyền thống. Kết hợp với năng lực đầu ra có cấu trúc mạnh mẽ, chúng ta chuyển trực tiếp quy tắc trò chơi thành ràng buộc ở tầng mã, nâng cao rõ rệt tính ổn định và khả năng dự đoán của hệ thống. Mô hình thiết kế này không chỉ thể hiện ưu thế đồng thời native về hiệu năng, mà còn đảm bảo trong xử lý chịu lỗi rằng ngay cả khi một Agent gặp bất thường, toàn bộ quy trình vẫn chạy vững chắc.

Tuy nhiên, ưu thế kỹ thuật hóa của AgentScope cũng mang lại chi phí phức tạp nhất định. Kiến trúc hướng tin nhắn tuy mạnh mẽ nhưng yêu cầu kỹ thuật với nhà phát triển cao hơn; cần hiểu các khái niệm như lập trình bất đồng bộ, giao tiếp phân tán. Với tình huống hội thoại đa Agent đơn giản, kiến trúc này có thể tỏ ra quá phức tạp, có rủi ro “kỹ thuật hóa quá mức”. Ngoài ra, là framework tương đối mới, hệ sinh thái và tài nguyên cộng đồng của nó còn cần hoàn thiện thêm. Vì vậy, AgentScope phù hợp hơn với việc xây dựng hệ thống đa Agent cấp sản xuất quy mô lớn, độ tin cậy cao; còn với phát triển nguyên mẫu nhanh hoặc tình huống ứng dụng đơn giản, chọn framework nhẹ hơn có thể phù hợp hơn.



## 6.4 Framework ba: CAMEL

Khác với các framework đầy đủ chức năng như AutoGen và AgentScope, mục tiêu cốt lõi ban đầu của CAMEL là khám phá cách để hai Agent tự chủ cộng tác giải quyết nhiệm vụ phức tạp thông qua “nhập vai” với ít can thiệp của con người nhất.

### 6.4.1 Cộng tác tự chủ của CAMEL

Nền tảng để CAMEL hiện thực cộng tác tự chủ là hai khái niệm cốt lõi: <strong>nhập vai (Role-Playing)</strong> và <strong>prompt dẫn dắt (Inception Prompting)</strong>.

(1) Nhập vai

Trong thiết kế ban đầu của CAMEL, một nhiệm vụ thường do hai Agent cộng tác hoàn thành. Hai Agent này được trao các “vai trò” bổ trợ, được định nghĩa rõ ràng. Một bên đóng <strong>“người dùng AI” (AI User)</strong>, chịu trách nhiệm nêu yêu cầu, ra chỉ thị và xây dựng các bước nhiệm vụ; bên kia đóng <strong>“trợ lý AI” (AI Assistant)</strong>, chịu trách nhiệm thực hiện thao tác cụ thể và cung cấp giải pháp theo chỉ thị.

Ví dụ, trong nhiệm vụ “phát triển công cụ phân tích chiến lược giao dịch chứng khoán”:

- Vai trò <strong>người dùng AI</strong> có thể là một “nhà giao dịch chứng khoán lão luyện”. Nó hiểu thị trường, hiểu chiến lược, nhưng không hiểu lập trình.
- Vai trò <strong>trợ lý AI</strong> là một “lập trình viên Python xuất sắc”. Nó tinh thông lập trình nhưng không biết gì về giao dịch chứng khoán.

Với thiết lập này, quá trình giải quyết nhiệm vụ được chuyển tự nhiên thành cuộc hội thoại giữa hai “chuyên gia liên ngành”. Nhà giao dịch nêu yêu cầu chuyên môn, lập trình viên chuyển nó thành hiện thực mã; hai bên cộng tác hoàn thành nhiệm vụ phức tạp mà bất kỳ bên nào cũng không thể tự làm.

(2) Prompt dẫn dắt

Chỉ đặt vai trò thì chưa đủ; làm sao đảm bảo hai AI, khi không có con người giám sát liên tục, luôn “ở trong vai của mình” và tiến hiệu quả về mục tiêu chung? Đây là nơi kỹ thuật cốt lõi nhất của CAMEL – prompt dẫn dắt – phát huy tác dụng. “Prompt dẫn dắt” là một đoạn chỉ thị khởi đầu có cấu trúc, được thiết kế cẩn thận, được chèn riêng cho hai Agent trước khi hội thoại bắt đầu (System Prompt). Đoạn chỉ thị này giống như “cương lĩnh hành động” cấy vào Agent; nó thường gồm các phần then chốt sau:

- <strong>Xác định rõ vai trò bản thân</strong>: ví dụ “bạn là một nhà giao dịch chứng khoán lão luyện...”
- <strong>Thông báo vai trò của người cộng tác</strong>: ví dụ “bạn đang cộng tác với một lập trình viên Python xuất sắc...”
- <strong>Định nghĩa mục tiêu chung</strong>: ví dụ “mục tiêu chung của các bạn là phát triển một công cụ phân tích chiến lược giao dịch chứng khoán.”
- <strong>Đặt ràng buộc hành vi và giao thức giao tiếp</strong>: đây là mắt xích then chốt nhất. Ví dụ, chỉ thị yêu cầu người dùng AI “mỗi lần chỉ nêu một bước rõ ràng, cụ thể”, yêu cầu trợ lý AI “không hỏi thêm chi tiết trước khi hoàn thành bước trước”, đồng thời quy định hai bên phải dùng dấu hiệu đặc biệt (như `<SOLUTION>`) ở cuối phản hồi để đánh dấu hoàn thành nhiệm vụ.

Những ràng buộc này đảm bảo hội thoại không lệch chủ đề, không rơi vào vòng lặp vô ích, mà tiến lên theo cách có cấu trúc cao, do nhiệm vụ dẫn dắt, như trong Hình 6.3.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/6-figures/04.png" alt="" width="90%"/>
  <p>Hình 6.3 CAMEL tạo bot giao dịch chứng khoán</p>
</div>

Trong mục tiếp theo, chúng ta sẽ trải nghiệm quá trình này qua một ví dụ cụ thể.

### 6.4.2 Sách điện tử phổ cập AI

Để hiểu năng lực nhập vai của framework CAMEL, chúng ta sẽ xây dựng một ca cộng tác có giá trị thực tế: để một nhà tâm lý học AI và một nhà văn AI hợp tác sáng tác một cuốn sách điện tử ngắn về “tâm lý học trì hoãn”. Ca này thể hiện ưu thế cốt lõi của CAMEL: cho hai Agent phát huy sở trường trong lĩnh vực chuyên môn của mình, cộng tác hoàn thành nhiệm vụ sáng tạo phức tạp mà một Agent đơn lẻ khó đảm nhận.

(1) Thiết lập nhiệm vụ

<strong>Thiết lập cảnh</strong>: sáng tác một cuốn sách điện tử phổ cập tâm lý học về trì hoãn dành cho độc giả phổ thông, yêu cầu vừa có tính nghiêm ngặt khoa học vừa có khả năng đọc tốt.

<strong>Vai trò Agent</strong>:

- <strong>Nhà tâm lý học (Psychologist)</strong>: có nền tảng lý thuyết tâm lý học sâu, quen thuộc với khoa học hành vi nhận thức, khoa học thần kinh và các lĩnh vực liên quan, có thể cung cấp kiến giải học thuật chuyên nghiệp và hỗ trợ nghiên cứu thực nghiệm.
- <strong>Nhà văn (Writer)</strong>: có kỹ năng viết và năng lực tự sự xuất sắc, giỏi chuyển khái niệm học thuật phức tạp thành văn bản sinh động dễ hiểu, chú trọng trải nghiệm độc giả và khả năng đọc của nội dung.

(2) Định nghĩa nhiệm vụ cộng tác

Trước tiên, chúng ta cần làm rõ mục tiêu chung của hai chuyên gia AI. Chúng ta định nghĩa nhiệm vụ này bằng một chuỗi `task_prompt` có nội dung chi tiết.

```python
from colorama import Fore
from camel.societies import RolePlaying
from camel.utils import print_text_animated
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from dotenv import load_dotenv
import os

load_dotenv()
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")

# Tạo mô hình; ở đây lấy Qwen làm ví dụ, gọi API của nền tảng mô hình lớn Bailian
model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=LLM_MODEL,
    url=LLM_BASE_URL,
    api_key=LLM_API_KEY
)

# Định nghĩa nhiệm vụ cộng tác
task_prompt = """
Sáng tác một cuốn sách điện tử ngắn về "tâm lý học trì hoãn", độc giả mục tiêu là công chúng phổ thông quan tâm đến tâm lý học.
Yêu cầu:
1. Nội dung khoa học nghiêm ngặt, dựa trên nghiên cứu thực nghiệm
2. Ngôn ngữ phổ thông dễ hiểu, tránh quá nhiều thuật ngữ chuyên môn
3. Gồm gợi ý cải thiện thiết thực và phân tích ca
4. Độ dài kiểm soát trong 8000-10000 từ
5. Cấu trúc rõ ràng, gồm mở đầu, các chương cốt lõi và tổng kết
"""

print(Fore.YELLOW + f"Nhiệm vụ cộng tác:\n{task_prompt}\n")
```

`task_prompt` là “bản mô tả nhiệm vụ” của toàn bộ quá trình cộng tác. Nó không chỉ là mục tiêu chúng ta cần hoàn thành, mà còn được CAMEL dùng ở hậu trường để sinh “prompt dẫn dắt”, đảm bảo hội thoại của hai Agent luôn xoay quanh mục tiêu cốt lõi này.

(3) Khởi tạo “xã hội” nhập vai

Tiếp theo, chúng ta tạo thực thể phiên `RolePlaying`. Đây là thao tác cốt lõi của CAMEL; nó dựa trên vai trò và nhiệm vụ chúng ta cung cấp để nhanh chóng xây dựng một “xã hội” cộng tác hai Agent.

```python
# Khởi tạo phiên nhập vai
# Nhà văn AI đóng "user", chịu trách nhiệm nêu cấu trúc và yêu cầu viết
# Nhà tâm lý học AI đóng "assistant", chịu trách nhiệm cung cấp kiến thức chuyên môn và nội dung
role_play_session = RolePlaying(
    assistant_role_name="nhà tâm lý học",
    user_role_name="nhà văn",
    task_prompt=task_prompt,
    model=model,
    with_task_specify=False, # Trong ví dụ này, chúng ta dùng trực tiếp task_prompt đã cho
)

print(Fore.CYAN + f"Mô tả nhiệm vụ cụ thể:\n{role_play_session.task_prompt}\n")
```

`RolePlaying` là API cấp cao do CAMEL cung cấp, đóng gói kỹ thuật prompt phức tạp. Chúng ta chỉ cần truyền tên hai vai trò và nhiệm vụ. Trong thiết kế của CAMEL, vai `user` là “người thúc đẩy” và “bên nêu nhu cầu” của hội thoại, còn vai `assistant` là “bên thực thi” và “bên cung cấp giải pháp”. Vì vậy, chúng ta gán “nhà văn” – người chịu trách nhiệm lập kế hoạch cấu trúc – cho `user_role_name`, và “nhà tâm lý học” – người chịu trách nhiệm cung cấp kiến thức chuyên môn – cho `assistant_role_name`.

(4) Khởi động và chạy hội thoại tự động

Cuối cùng, chúng ta viết một vòng lặp để dẫn dắt toàn bộ quá trình hội thoại, để hai chuyên gia AI bắt đầu cộng tác tự động.

```python
# Bắt đầu hội thoại cộng tác
chat_turn_limit, n = 30, 0
# Gọi init_chat() để lấy tin nhắn hội thoại khởi đầu do AI sinh
input_msg = role_play_session.init_chat()

while n < chat_turn_limit:
    n += 1
    # Phương thức step() dẫn dắt một vòng hội thoại hoàn chỉnh; người dùng AI và trợ lý AI mỗi bên phát biểu một lần
    assistant_response, user_response = role_play_session.step(input_msg)

    # Kiểm tra xem có tin nhắn trả về không, tránh hội thoại kết thúc sớm
    if assistant_response.msg is None or user_response.msg is None:
        break

    print_text_animated(Fore.BLUE + f"Nhà văn (AI User):\n\n{user_response.msg.content}\n")
    print_text_animated(Fore.GREEN + f"Nhà tâm lý học (AI Assistant):\n\n{assistant_response.msg.content}\n")

    # Kiểm tra dấu hiệu hoàn thành nhiệm vụ
    if "<CAMEL_TASK_DONE>" in user_response.msg.content or "<CAMEL_TASK_DONE>" in assistant_response.msg.content:
        print(Fore.MAGENTA + "✅ Sáng tác sách điện tử hoàn thành!")
        break

    # Dùng phản hồi của trợ lý làm đầu vào cho vòng hội thoại tiếp theo
    input_msg = assistant_response.msg

print(Fore.YELLOW + f"Tổng cộng đã thực hiện {n} vòng hội thoại cộng tác")
```

Vòng `while` này là cốt lõi của cộng tác tự động. Hội thoại được phương thức `init_chat()` tự động mở đầu dựa trên nhiệm vụ và vai trò, không cần viết thủ công lời mở đầu. Mỗi bước của vòng lặp gọi `step()` để dẫn dắt một lượt tương tác hoàn chỉnh (nhà văn nêu yêu cầu, nhà tâm lý học cung cấp nội dung), và dùng đầu ra của nhà tâm lý học ở vòng trước làm đầu vào vòng sau, tạo thành chuỗi sáng tác liên kết. Toàn bộ quá trình tiếp diễn cho đến khi đạt giới hạn số lượt hội thoại đặt trước, hoặc một Agent xuất dấu hiệu hoàn thành nhiệm vụ `<CAMEL_TASK_DONE>` thì tự động kết thúc.

(5) Trình diễn quy trình cộng tác

Sau khi thực thi mã trên, chúng ta không chỉ nhận được một chuỗi hỏi đáp đơn điệu, mà có thể quan sát một quy trình cộng tác có cấu trúc cao, giống như một nhóm chuyên gia con người, đang tự động diễn ra. Toàn bộ quá trình sáng tác chia tự nhiên thành vài giai đoạn:

<strong>Giai đoạn một (khoảng 1-5 vòng): dựng khung và căn chỉnh mục tiêu</strong> Ở đầu hội thoại, Agent “nhà văn” trước tiên đóng vai người dẫn dắt, nêu ý tưởng sơ bộ về cấu trúc tổng thể và sắp xếp chương của sách điện tử. Sau đó, “nhà tâm lý học” xem xét và bổ sung khung này từ góc độ chuyên môn, đảm bảo các mô-đun học thuật cốt lõi (như nền tảng lý thuyết, khái niệm then chốt) không bị bỏ sót, từ đó đạt đồng thuận về sản phẩm cuối ngay từ đầu cộng tác.

<strong>Giai đoạn hai (khoảng 6-20 vòng): sinh nội dung cốt lõi và chuyển dịch tri thức</strong> Đây là giai đoạn sáng tạo nội dung hiệu quả nhất. Mô hình cộng tác chuyển thành vòng “yêu cầu – phản hồi” ổn định:

- <strong>Nhà tâm lý học</strong>: chịu trách nhiệm cung cấp kiến thức chuyên môn “cứng”, như giải thích khoa học các khái niệm cốt lõi “lý thuyết chiết khấu thời gian”, “khiếm khuyết chức năng điều hành”, và trích dẫn nghiên cứu thực nghiệm liên quan để hỗ trợ quan điểm.
- <strong>Nhà văn</strong>: phát huy vai “người phiên dịch”, chuyển các khái niệm học thuật nghiêm ngặt nhưng có thể khó hiểu thành ẩn dụ sinh động, hình tượng và ca gần gũi đời sống. Ví dụ, nó có thể ví khái niệm “‘thiên kiến hiện tại’ trong não” với “một đứa trẻ bướng bỉnh chỉ nghĩ đến kẹo trước mắt, không quan tâm sức khỏe lâu dài”.

<strong>Giai đoạn ba (khoảng 21-25 vòng): tối ưu lặp và đảm bảo chất lượng</strong> Khi nội dung chính của sách hoàn thành, trọng tâm hội thoại chuyển sang mài giũa và hoàn thiện văn bản hiện có. Lúc này, vai trò của hai Agent thay đổi tinh tế:

- <strong>Nhà văn</strong>: tập trung hơn vào việc xem xét tính trôi chảy tổng thể, liên kết logic và phong cách ngôn ngữ của bài, đưa gợi ý sửa từ “trải nghiệm độc giả”.
- <strong>Nhà tâm lý học</strong>: lại đóng vai “người kiểm chứng sự thật”, đảm bảo trong quá trình chuyển dịch và trau chuốt, độ chính xác khoa học của kiến thức cốt lõi không bị mất, đồng thời bổ sung hỗ trợ nghiên cứu thực nghiệm mạnh hơn cho một số quan điểm.

<strong>Giai đoạn bốn (kết thúc): tổng kết và nâng cao</strong> Trong vài vòng hội thoại cuối, hai bên cộng tác hoàn thành tổng kết gợi ý thực dụng và nhìn lại toàn sách, đảm bảo sách điện tử có kết thúc rõ ràng, mạnh mẽ, để lại ấn tượng sâu sắc và mang lại giá trị thực tế cho độc giả.

```
Nhiệm vụ cộng tác:
Sáng tác một cuốn sách điện tử ngắn về "tâm lý học trì hoãn", độc giả mục tiêu là công chúng phổ thông quan tâm đến tâm lý học.
Yêu cầu:
1. Nội dung khoa học nghiêm ngặt, dựa trên nghiên cứu thực nghiệm
2. Ngôn ngữ phổ thông dễ hiểu, tránh quá nhiều thuật ngữ chuyên môn
3. Gồm gợi ý cải thiện thiết thực và phân tích ca
4. Độ dài kiểm soát trong 8000-10000 từ
5. Cấu trúc rõ ràng, gồm mở đầu, các chương cốt lõi và tổng kết

Mô tả nhiệm vụ cụ thể:
Viết cho công chúng phổ thông cuốn sách điện tử ngắn 8000–10000 từ “Tâm lý học trì hoãn”: lấy thực nghiệm làm nền, phổ thông dễ hiểu. Cấu trúc: mở đầu, nguyên nhân (nhận thức/cảm xúc/phần thưởng), động cơ và ra quyết định, hình thành thói quen và can thiệp, chiến lược thực dụng và bài tập, ba ca phân tích, tổng kết và tài nguyên. Mỗi chương gồm trích dẫn nghiên cứu và bước có thể thao tác.

Nhà văn:
Instruction: Hãy viết một bản nháp tiếng Trung 400–600 từ cho chương “Mở đầu” của sách điện tử...
Input: None

Nhà tâm lý học:
Solution:
Bản nháp: Trì hoãn là hành vi và khuynh hướng nội tại của việc biết rõ nên hoàn thành một nhiệm vụ nhưng lặp đi lặp lại việc trì hoãn hoặc né tránh. Nó có thể là vấn đề quản lý thời gian ngẫu phát...

Next request.

Nhà văn:
Instruction: Hãy sửa bản nháp mở đầu dưới đây thành văn bản tiếng Trung 450–550 từ...
Input: Bản nháp: Trì hoãn là hành vi và khuynh hướng nội tại của việc biết rõ nên hoàn thành một nhiệm vụ nhưng lặp đi lặp lại việc trì hoãn hoặc né tránh...
.....
```

### 6.4.3 Phân tích ưu điểm và hạn chế của CAMEL

Qua ca sáng tác sách điện tử ở trên, chúng ta đã trải nghiệm sâu mô hình nhập vai độc đáo của framework CAMEL. Bây giờ hãy phân tích khách quan ưu điểm và hạn chế của triết lý thiết kế này, để có thể lựa chọn công nghệ sáng suốt trong dự án thực tế.

(1) Ưu điểm

Ưu thế lớn nhất của CAMEL nằm ở triết lý thiết kế “kiến trúc nhẹ, prompt nặng”. So với quản lý hội thoại phức tạp của AutoGen và kiến trúc phân tán của AgentScope, CAMEL có thể hiện thực cộng tác Agent chất lượng cao chỉ bằng prompt khởi đầu được thiết kế cẩn thận. Hành vi cộng tác tự nảy sinh này thường linh hoạt và hiệu quả hơn quy trình làm việc mã hóa cứng.

Đáng chú ý là framework CAMEL đang phát triển và tiến hóa nhanh chóng. Từ [kho GitHub](https://github.com/camel-ai/camel) của nó có thể thấy CAMEL đã vượt xa một framework cộng tác hai Agent đơn giản; hiện đã có:

- <strong>Năng lực đa phương thức</strong>: hỗ trợ cộng tác Agent với nhiều phương thức như văn bản, hình ảnh, âm thanh.
- <strong>Tích hợp công cụ</strong>: tích hợp sẵn thư viện công cụ phong phú, gồm tìm kiếm, tính toán, thực thi mã, v.v.
- <strong>Thích ứng mô hình</strong>: hỗ trợ nhiều backend LLM như OpenAI, Anthropic, Google, mô hình mã nguồn mở.
- <strong>Liên kết hệ sinh thái</strong>: hiện thực khả năng tương tác với các framework chủ lưu như LangChain, CrewAI, AutoGen.

(2) Hạn chế chính

1. Phụ thuộc cao vào kỹ thuật prompt

Thành công của CAMEL phụ thuộc lớn vào chất lượng prompt khởi đầu. Điều này mang lại vài thách thức:

- <strong>Ngưỡng thiết kế prompt</strong>: cần hiểu sâu lĩnh vực mục tiêu và đặc tính hành vi của LLM.
- <strong>Độ phức tạp gỡ lỗi</strong>: khi hiệu quả cộng tác không tốt, rất khó xác định vấn đề nằm ở định nghĩa vai trò, mô tả nhiệm vụ hay quy tắc tương tác.
- <strong>Thách thức nhất quán</strong>: các LLM khác nhau có thể hiểu cùng một prompt khác nhau.

2. Hạn chế quy mô cộng tác

Mặc dù CAMEL xuất sắc trong cộng tác hai Agent, nó gặp thách thức khi xử lý tình huống đa Agent quy mô lớn:

- <strong>Quản lý hội thoại</strong>: thiếu cơ chế định tuyến hội thoại phức tạp như AutoGen.
- <strong>Đồng bộ trạng thái</strong>: không có năng lực quản lý trạng thái phân tán như AgentScope.
- <strong>Giải quyết xung đột</strong>: khi nhiều Agent bất đồng ý kiến, thiếu cơ chế trọng tài hiệu quả.

3. Biên giới phù hợp nhiệm vụ

CAMEL đặc biệt phù hợp với nhiệm vụ cần cộng tác sâu và tư duy sáng tạo, nhưng trong một số tình huống có thể không phải lựa chọn tối ưu:

- <strong>Kiểm soát quy trình nghiêm ngặt</strong>: với nhiệm vụ cần kiểm soát bước chính xác, cấu trúc đồ thị của LangGraph phù hợp hơn.
- <strong>Đồng thời quy mô lớn</strong>: kiến trúc hướng tin nhắn của AgentScope có ưu thế hơn trong tình huống đồng thời cao.
- <strong>Cây quyết định phức tạp</strong>: chế độ nhóm chat của AutoGen linh hoạt hơn trong tình huống ra quyết định nhiều bên.

Tổng thể, CAMEL đại diện cho một mô hình cộng tác đa Agent độc đáo và thanh lịch. Thông qua thiết kế nhập vai “lấy con người làm trung tâm”, nó chuyển vấn đề kỹ thuật hệ thống phức tạp thành mô hình cộng tác giữa người với người trực quan. Cùng với hệ sinh thái không ngừng hoàn thiện và chức năng tiếp tục mở rộng, CAMEL đang trở thành một trong những lựa chọn quan trọng để xây dựng hệ thống cộng tác thông minh.

## 6.5 Framework bốn: LangGraph

### 6.5.1 Khảo sát cấu trúc LangGraph

LangGraph, với tư cách phần mở rộng quan trọng của hệ sinh thái LangChain, đại diện cho một hướng hoàn toàn mới trong thiết kế framework Agent. Khác với các framework dựa trên “hội thoại” đã giới thiệu (như AutoGen và CAMEL), LangGraph mô hình hóa quy trình thực thi của Agent thành <strong>máy trạng thái (State Machine)</strong>, và biểu diễn nó thành <strong>đồ thị có hướng (Directed Graph)</strong>. Trong mô hình này, <strong>nút (Nodes)</strong> của đồ thị đại diện cho một bước tính toán cụ thể (như gọi LLM, thực thi công cụ), còn <strong>cạnh (Edges)</strong> định nghĩa logic chuyển từ nút này sang nút khác. Tính cách mạng của thiết kế này nằm ở việc nó hỗ trợ chu trình tự nhiên, khiến việc xây dựng quy trình Agent phức tạp có thể lặp, phản tư và tự sửa trở nên trực quan và đơn giản chưa từng có.

Để hiểu LangGraph, trước tiên cần nắm ba yếu tố cấu thành cơ bản.

<strong>Thứ nhất là trạng thái toàn cục (State)</strong>. Toàn bộ quá trình thực thi của đồ thị xoay quanh một đối tượng trạng thái chia sẻ. Trạng thái này thường được định nghĩa là `TypedDict` của Python, có thể chứa bất kỳ thông tin bạn cần theo dõi, như lịch sử hội thoại, kết quả trung gian, số lần lặp, v.v. Mọi nút đều có thể đọc và cập nhật trạng thái trung tâm này.

```python
from typing import TypedDict, List

# Định nghĩa cấu trúc dữ liệu của trạng thái toàn cục
class AgentState(TypedDict):
    messages: List[str]      # Lịch sử hội thoại
    current_task: str        # Nhiệm vụ hiện tại
    final_answer: str        # Câu trả lời cuối cùng
    # ... bất kỳ trạng thái nào khác cần theo dõi
```

<strong>Thứ hai là nút (Nodes)</strong>. Mỗi nút là một hàm Python nhận trạng thái hiện tại làm đầu vào và trả về trạng thái đã cập nhật làm đầu ra. Nút là đơn vị thực hiện công việc cụ thể.

```python
# Định nghĩa hàm nút “người lập kế hoạch”
def planner_node(state: AgentState) -> AgentState:
    """Lập kế hoạch dựa trên nhiệm vụ hiện tại và cập nhật trạng thái."""
    current_task = state["current_task"]
    # ... gọi LLM sinh kế hoạch ...
    plan = f"Kế hoạch được sinh cho nhiệm vụ '{current_task}'..."

    # Nối tin nhắn mới vào trạng thái
    state["messages"].append(plan)
    return state

# Định nghĩa hàm nút “người thực thi”
def executor_node(state: AgentState) -> AgentState:
    """Thực thi kế hoạch mới nhất và cập nhật trạng thái."""
    latest_plan = state["messages"][-1]
    # ... thực thi kế hoạch và nhận kết quả ...
    result = f"Kết quả thực thi kế hoạch '{latest_plan}'..."

    state["messages"].append(result)
    return state
```

<strong>Cuối cùng là cạnh (Edges)</strong>. Cạnh chịu trách nhiệm kết nối các nút, định nghĩa hướng của quy trình làm việc. Cạnh đơn giản nhất là cạnh thường, chỉ định đầu ra của một nút luôn chảy đến một nút cố định khác. Còn chức năng mạnh nhất của LangGraph nằm ở <strong>cạnh điều kiện (Conditional Edges)</strong>. Nó dùng một hàm để phán đoán trạng thái hiện tại, rồi quyết định động bước tiếp theo nên chuyển đến nút nào. Đây chính là chìa khóa hiện thực chu trình và nhánh logic phức tạp.

```python
def should_continue(state: AgentState) -> str:
    """Hàm điều kiện: quyết định định tuyến bước tiếp theo dựa trên trạng thái."""
    # Giả sử nếu số tin nhắn nhỏ hơn 3 thì cần tiếp tục lập kế hoạch
    if len(state["messages"]) < 3:
        # Chuỗi trả về cần khớp với khóa định nghĩa khi thêm cạnh điều kiện
        return "continue_to_planner"
    else:
        state["final_answer"] = state["messages"][-1]
        return "end_workflow"
```

Sau khi định nghĩa trạng thái, nút và cạnh, chúng ta có thể lắp ghép chúng thành một quy trình làm việc có thể thực thi như lắp khối lego.

```python
from langgraph.graph import StateGraph, END

# Khởi tạo đồ thị trạng thái và gắn cấu trúc trạng thái chúng ta định nghĩa
workflow = StateGraph(AgentState)

# Thêm các hàm nút vào đồ thị
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)

# Đặt điểm vào của đồ thị
workflow.set_entry_point("planner")

# Thêm cạnh thường, kết nối planner và executor
workflow.add_edge("planner", "executor")

# Thêm cạnh điều kiện, hiện thực định tuyến động
workflow.add_conditional_edges(
    # Nút bắt đầu
    "executor",
    # Hàm phán đoán
    should_continue,
    # Ánh xạ định tuyến: ánh xạ giá trị trả về của hàm phán đoán đến nút đích
    {
        "continue_to_planner": "planner", # Nếu trả về "continue_to_planner" thì quay lại nút planner
        "end_workflow": END               # Nếu trả về "end_workflow" thì kết thúc quy trình
    }
)

# Biên dịch đồ thị, sinh ứng dụng có thể thực thi
app = workflow.compile()

# Chạy đồ thị
inputs = {"current_task": "Phân tích tin tức ngành AI gần đây", "messages": []}
for event in app.stream(inputs):
    print(event)
```

### 6.5.2 Trợ lý hỏi đáp ba bước
Sau khi hiểu khái niệm cốt lõi của LangGraph, chúng ta sẽ củng cố kiến thức qua một ca thực chiến. Chúng ta sẽ xây dựng một trợ lý hội thoại hỏi đáp đơn giản, tuân theo quy trình ba bước rõ ràng, cố định để trả lời câu hỏi người dùng:

1. <strong>Hiểu (Understand)</strong>: trước tiên, phân tích ý định truy vấn của người dùng.
2. <strong>Tìm kiếm (Search)</strong>: sau đó, mô phỏng tìm kiếm thông tin liên quan đến ý định.
3. <strong>Trả lời (Answer)</strong>: cuối cùng, dựa trên ý định và thông tin tìm được, sinh câu trả lời cuối cùng.

Ca này sẽ thể hiện rõ cách định nghĩa trạng thái, tạo nút và kết nối chúng tuyến tính thành một quy trình làm việc hoàn chỉnh. Chúng ta chia mã thành bốn bước cốt lõi: định nghĩa trạng thái, tạo nút, xây dựng đồ thị và chạy ứng dụng.

(1) Định nghĩa trạng thái toàn cục

Trước tiên, chúng ta cần định nghĩa một trạng thái toàn cục xuyên suốt toàn bộ quy trình làm việc. <strong>Đây là cấu trúc dữ liệu chia sẻ, được truyền giữa mỗi nút của đồ thị, làm ngữ cảnh bền vững của quy trình làm việc.</strong> Mỗi nút đều có thể đọc dữ liệu trong cấu trúc này và cập nhật nó.

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class SearchState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str      # Tóm tắt nhu cầu người dùng sau khi LLM hiểu
    search_query: str    # Truy vấn tìm kiếm đã tối ưu cho Tavily API
    search_results: str  # Kết quả Tavily trả về
    final_answer: str    # Câu trả lời cuối cùng được sinh
    step: str            # Đánh dấu bước hiện tại
```

Chúng ta tạo `SearchState` là một `TypedDict`, định nghĩa lược đồ dữ liệu (Schema) rõ ràng cho đối tượng trạng thái. Một thiết kế then chốt là đồng thời chứa trường `user_query` và `search_query`. Điều này cho phép Agent trước tiên tối ưu câu hỏi ngôn ngữ tự nhiên của người dùng thành từ khóa tinh gọn phù hợp hơn với công cụ tìm kiếm, từ đó nâng cao rõ rệt chất lượng kết quả tìm kiếm.

(2) Định nghĩa các nút của quy trình làm việc

Sau khi định nghĩa cấu trúc trạng thái, bước tiếp theo là tạo các nút cấu thành quy trình làm việc. Trong LangGraph, mỗi nút là một hàm Python thực hiện nhiệm vụ cụ thể. Các hàm này nhận đối tượng trạng thái hiện tại làm đầu vào và trả về một từ điển chứa các trường đã cập nhật.

Trước khi định nghĩa nút, chúng ta hoàn thành thiết lập khởi tạo dự án, gồm tải biến môi trường và khởi tạo mô hình ngôn ngữ lớn.

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tavily import TavilyClient

# Tải các biến môi trường từ tệp .env
load_dotenv()

# Khởi tạo mô hình
# Chúng ta sẽ dùng thực thể llm này để dẫn dắt trí tuệ của tất cả các nút
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL_ID", "gpt-4o-mini"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
    temperature=0.7
)
# Khởi tạo client Tavily
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
```

Bây giờ, chúng ta lần lượt tạo ba nút cốt lõi.

(1) Nút hiểu và truy vấn

Nút này là bước đầu tiên của quy trình làm việc; trách nhiệm là hiểu ý định người dùng và sinh truy vấn tìm kiếm tối ưu cho nó.

```python
def understand_query_node(state: SearchState) -> dict:
    """Bước 1: hiểu truy vấn người dùng và sinh từ khóa tìm kiếm"""
    user_message = state["messages"][-1].content

    understand_prompt = f"""Phân tích truy vấn của người dùng: "{user_message}"
Hãy hoàn thành hai nhiệm vụ:
1. Tóm tắt ngắn gọn người dùng muốn hiểu điều gì
2. Sinh từ khóa phù hợp nhất với công cụ tìm kiếm (tiếng Trung hoặc tiếng Anh đều được, phải chính xác)

Định dạng:
Hiểu: [tóm tắt nhu cầu người dùng]
Từ khóa tìm kiếm: [từ khóa tìm kiếm tốt nhất]"""

    response = llm.invoke([SystemMessage(content=understand_prompt)])
    response_text = response.content

    # Phân tích đầu ra của LLM, trích xuất từ khóa tìm kiếm
    search_query = user_message # Mặc định dùng truy vấn gốc
    if "Từ khóa tìm kiếm：" in response_text:
        search_query = response_text.split("Từ khóa tìm kiếm：")[1].strip()

    return {
        "user_query": response_text,
        "search_query": search_query,
        "step": "understood",
        "messages": [AIMessage(content=f"Tôi sẽ tìm kiếm cho bạn: {search_query}")]
    }
```

Nút này thông qua một prompt có cấu trúc, yêu cầu LLM đồng thời hoàn thành hai nhiệm vụ “hiểu ý định” và “sinh từ khóa”, và cập nhật từ khóa tìm kiếm chuyên dụng đã phân tích vào trường `search_query` của trạng thái, chuẩn bị cho tìm kiếm chính xác ở bước sau.

(2) Nút tìm kiếm

Nút này chịu trách nhiệm thực hiện năng lực “sử dụng công cụ” của Agent; nó sẽ gọi Tavily API để tìm kiếm internet thật, và có chức năng xử lý lỗi cơ bản.

```python
def tavily_search_node(state: SearchState) -> dict:
    """Bước 2: dùng Tavily API tìm kiếm thật"""
    search_query = state["search_query"]
    try:
        print(f"🔍 Đang tìm kiếm: {search_query}")
        response = tavily_client.search(
            query=search_query, search_depth="basic", max_results=5, include_answer=True
        )
        # ... (xử lý và định dạng kết quả tìm kiếm) ...
        search_results = ... # Chuỗi kết quả đã định dạng

        return {
            "search_results": search_results,
            "step": "searched",
            "messages": [AIMessage(content="✅ Tìm kiếm hoàn tất! Đang sắp xếp câu trả lời...")]
        }
    except Exception as e:
        # ... (xử lý lỗi) ...
        return {
            "search_results": f"Tìm kiếm thất bại: {e}",
            "step": "search_failed",
            "messages": [AIMessage(content="❌ Tìm kiếm gặp vấn đề...")]
        }
```

Nút này gọi API thật thông qua `tavily_client.search`. Nó được bao trong khối `try...except` để bắt ngoại lệ có thể xảy ra. Nếu tìm kiếm thất bại, nó cập nhật trạng thái `step` thành `"search_failed"`; trạng thái này sẽ được nút tiếp theo dùng để kích hoạt phương án dự phòng.

(3) Nút trả lời

Nút trả lời cuối cùng có thể chọn chiến lược trả lời khác nhau dựa trên việc tìm kiếm ở bước trước thành công hay không, có tính linh hoạt nhất định.

```python
def generate_answer_node(state: SearchState) -> dict:
    """Bước 3: sinh câu trả lời cuối cùng dựa trên kết quả tìm kiếm"""
    if state["step"] == "search_failed":
        # Nếu tìm kiếm thất bại, thực hiện chiến lược dự phòng, trả lời dựa trên kiến thức của LLM
        fallback_prompt = f"API tìm kiếm tạm thời không khả dụng, hãy trả lời câu hỏi của người dùng dựa trên kiến thức của bạn:\nCâu hỏi người dùng: {state['user_query']}"
        response = llm.invoke([SystemMessage(content=fallback_prompt)])
    else:
        # Tìm kiếm thành công, sinh câu trả lời dựa trên kết quả tìm kiếm
        answer_prompt = f"""Dựa trên kết quả tìm kiếm sau, cung cấp câu trả lời đầy đủ, chính xác cho người dùng:
Câu hỏi người dùng: {state['user_query']}
Kết quả tìm kiếm:\n{state['search_results']}
Hãy tổng hợp kết quả tìm kiếm, cung cấp câu trả lời chính xác, hữu ích..."""
        response = llm.invoke([SystemMessage(content=answer_prompt)])

    return {
        "final_answer": response.content,
        "step": "completed",
        "messages": [AIMessage(content=response.content)]
    }
```

Nút này thực hiện logic điều kiện bằng cách kiểm tra giá trị `state["step"]`. Nếu tìm kiếm thất bại, nó dùng kiến thức nội bộ của LLM để trả lời và thông báo tình hình cho người dùng. Nếu tìm kiếm thành công, nó dùng prompt chứa kết quả tìm kiếm thời gian thực để sinh câu trả lời có tính thời sự và có căn cứ.

(4) Xây dựng đồ thị

Chúng ta kết nối tất cả các nút.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

def create_search_assistant():
    workflow = StateGraph(SearchState)

    # Thêm nút
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("search", tavily_search_node)
    workflow.add_node("answer", generate_answer_node)

    # Thiết lập luồng tuyến tính
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)

    # Biên dịch đồ thị
    memory = InMemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app
```

(5) Trình diễn ca chạy

Sau khi chạy script này, bạn có thể đặt một số câu hỏi cần thông tin thời gian thực, ví dụ ca ở chương 1 của chúng ta: `Ngày mai tôi đi Bắc Kinh, thời tiết thế nào? Có điểm tham quan phù hợp không`

Bạn sẽ thấy terminal hiển thị rõ quá trình “suy nghĩ” của Agent:

```
🔍 Trợ lý tìm kiếm thông minh khởi động!
Tôi sẽ dùng Tavily API tìm kiếm thông tin mới nhất, chính xác nhất cho bạn
Hỗ trợ nhiều loại câu hỏi: tin tức, công nghệ, hỏi đáp kiến thức, v.v.
(nhập 'quit' để thoát)

🤔 Bạn muốn hiểu điều gì: Ngày mai tôi đi Bắc Kinh, thời tiết thế nào? Có điểm tham quan phù hợp không

============================================================
🧠 Giai đoạn hiểu: Tôi hiểu nhu cầu của bạn: Hiểu: người dùng muốn biết thời tiết Bắc Kinh ngày mai và gợi ý điểm tham quan phù hợp.
Từ khóa tìm kiếm: Bắc Kinh ngày mai thời tiết gợi ý điểm tham quan Beijing weather tomorrow attractions
🔍 Đang tìm kiếm: Bắc Kinh ngày mai thời tiết gợi ý điểm tham quan Beijing weather tomorrow attractions
🔍 Giai đoạn tìm kiếm: ✅ Tìm kiếm hoàn tất! Đã tìm thấy thông tin liên quan, đang sắp xếp câu trả lời cho bạn...

💡 Câu trả lời cuối cùng:
Dự báo thời tiết Bắc Kinh ngày mai (17 tháng 9 năm 2025) cho thấy dự kiến trời nhiều mây, nhiệt độ từ 17°C (62°F) đến 25°C (77°F). Thời tiết ôn hòa này rất phù hợp cho hoạt động ngoài trời.

### Gợi ý điểm tham quan phù hợp:
1. **Vạn Lý Trường Thành**: là một trong những di tích lịch sử nổi tiếng nhất Trung Quốc, Vạn Lý Trường Thành là nơi nhất định phải đến. Bạn có thể chọn các đoạn phổ biến như Bát Đạt Lĩnh hoặc Mộ Điền Dục để tham quan.

2. **Tử Cấm Thành**: Tử Cấm Thành là cung điện của hai triều Minh và Thanh, có lịch sử và văn hóa phong phú, phù hợp với du khách quan tâm lịch sử Trung Quốc.

3. **Quảng trường Thiên An Môn**: đây là một trong những biểu tượng của Trung Quốc; quảng trường có nhiều công trình và đài kỷ niệm quan trọng, phù hợp chụp ảnh lưu niệm.

4. **Di Hòa Viên**: một khu vườn hoàng gia rất đẹp, phù hợp đi dạo và ngắm cảnh tự nhiên, đặc biệt là hồ và kiến trúc cổ.

5. **Khu nghệ thuật 798**: nếu bạn quan tâm nghệ thuật hiện đại, khu nghệ thuật 798 là nơi hội tụ nghệ thuật, văn hóa và sáng tạo, phù hợp khám phá và chụp ảnh.

### Mẹo nhỏ:
- Vì thời tiết ngày mai tốt, khuyến nghị lên kế hoạch lộ trình trước, chuẩn bị nước và đồ ăn nhẹ để giữ sức khi tham quan.
- Vì thời tiết thay đổi có thể ảnh hưởng trải nghiệm tham quan, khuyến nghị xem cập nhật thời tiết thời gian thực.

Hy vọng những thông tin này giúp bạn sắp xếp một chuyến đi Bắc Kinh vui vẻ! Nếu cần thêm thông tin về điểm tham quan hoặc gợi ý du lịch, hãy hỏi bất cứ lúc nào.

============================================================

🤔 Bạn muốn hiểu điều gì:
```

Và nó là một trợ lý có thể tương tác liên tục; bạn cũng có thể tiếp tục đặt câu hỏi.

### 6.5.3 Phân tích ưu điểm và hạn chế của LangGraph

Mọi framework kỹ thuật đều có tình huống áp dụng và đánh đổi thiết kế riêng. Trong mục này, chúng ta sẽ phân tích khách quan ưu điểm cốt lõi của LangGraph và những hạn chế có thể gặp trong ứng dụng thực tế.

(1) Ưu điểm

- Như ca trợ lý tìm kiếm thông minh của chúng ta cho thấy, LangGraph định nghĩa rõ ràng một quy trình hỏi đáp thời gian thực hoàn chỉnh thành một “lưu đồ” gồm trạng thái, nút và cạnh. Ưu thế lớn nhất của thiết kế này là <strong>tính kiểm soát và khả năng dự đoán cao</strong>. Nhà phát triển có thể lập kế hoạch chính xác hành vi từng bước của Agent; điều này rất quan trọng để xây dựng ứng dụng cấp sản xuất cần độ tin cậy và khả năng kiểm toán cao. Đặc tính mạnh nhất của nó là <strong>hỗ trợ native chu trình (Cycles)</strong>. Thông qua cạnh điều kiện, chúng ta có thể dễ dàng xây dựng vòng “phản tư – sửa”, ví dụ trong ca của chúng ta, nếu tìm kiếm thất bại có thể thiết kế đường quay về phương án dự phòng. Đây là chìa khóa để xây dựng Agent có khả năng tự tối ưu và chịu lỗi.

- Ngoài ra, vì mỗi nút là một hàm Python độc lập, nên có <strong>tính mô-đun cao</strong>. Đồng thời, việc chèn một nút chờ con người kiểm duyệt vào quy trình cũng trở nên rất trực tiếp, tạo nền tảng vững chắc cho “cộng tác người – máy” (Human-in-the-loop) đáng tin cậy.

(2) Hạn chế

- So với các framework dựa trên hội thoại, LangGraph yêu cầu nhà phát triển viết nhiều <strong>mã khung (Boilerplate)</strong> hơn. Một loạt thao tác như định nghĩa trạng thái, nút, cạnh khiến quá trình phát triển có vẻ rườm rà hơn với nhiệm vụ đơn giản. Nhà phát triển cần suy nghĩ nhiều hơn về “cách kiểm soát quy trình (how)”, chứ không chỉ “làm gì (what)”. Vì quy trình làm việc được định trước, hành vi của LangGraph tuy có thể kiểm soát nhưng cũng thiếu kiểu tương tác động, <strong>“nảy sinh”</strong> của Agent hội thoại. Điểm mạnh của nó là thực thi một quy trình xác định, đáng tin cậy, không phải mô phỏng cộng tác xã hội mở, không thể dự đoán.

- Quá trình gỡ lỗi cũng có thách thức. Mặc dù quy trình rõ ràng hơn lịch sử hội thoại, vấn đề có thể nằm ở nhiều khâu: lỗi logic bên trong một nút, dữ liệu trạng thái truyền giữa các nút bị biến đổi, hoặc phán đoán điều kiện chuyển cạnh bị sai. Điều này đòi hỏi nhà phát triển có hiểu biết tổng thể về cơ chế vận hành của toàn bộ đồ thị.

## 6.6 Tổng kết chương

Chương này chúng ta đã cảm nhận một số framework Agent tiên tiến nhất hiện nay, và thực hành qua các ca.

Chúng ta thấy mỗi framework có cách riêng để hiện thực việc xây dựng Agent:

- <strong>AutoGen</strong> trừu tượng hóa cộng tác phức tạp thành một “nhóm chat” đa vai trò, có thể tự động diễn ra; cốt lõi là “lấy hội thoại dẫn dắt cộng tác”.
- <strong>AgentScope</strong> tập trung vào độ vững chắc và khả năng mở rộng của ứng dụng cấp công nghiệp, cung cấp nền tảng kỹ thuật vững chắc để xây dựng hệ thống đa Agent phân tán, đồng thời cao.
- <strong>CAMEL</strong> với mô hình “nhập vai” và “prompt dẫn dắt” nhẹ, cho thấy cách dùng ít mã nhất để khơi dậy cộng tác sâu, tự chủ giữa hai Agent chuyên gia.
- <strong>LangGraph</strong> quay về mô hình “máy trạng thái” tầng thấp hơn, thông qua cấu trúc đồ thị tường minh trao cho nhà phát triển kiểm soát chính xác quy trình làm việc, đặc biệt là năng lực chu trình, mở đường cho việc xây dựng Agent có thể phản tư, sửa lỗi.

Qua phân tích sâu các framework này, chúng ta có thể rút ra một đánh đổi thiết kế: <strong>lựa chọn giữa “cộng tác nảy sinh” và “kiểm soát tường minh”</strong>. AutoGen và CAMEL phụ thuộc nhiều hơn vào việc định nghĩa “vai trò” và “mục tiêu” của Agent, để hành vi cộng tác phức tạp “nảy sinh” từ các quy tắc hội thoại đơn giản; cách này gần với mô hình tương tác của con người hơn, nhưng đôi khi khó dự đoán và gỡ lỗi. LangGraph yêu cầu nhà phát triển định nghĩa rõ ràng từng bước và điều kiện chuyển, hy sinh một phần “bất ngờ nảy sinh” để đổi lấy độ tin cậy, tính kiểm soát và khả năng quan sát cao. Đồng thời, AgentScope tiết lộ chiều quan trọng thứ hai: <strong>kỹ thuật hóa</strong>. Dù chọn mô hình cộng tác nào, để đưa nó từ nguyên mẫu thí nghiệm sang ứng dụng sản xuất, đều phải đối mặt thách thức kỹ thuật như đồng thời, chịu lỗi, triển khai phân tán. AgentScope sinh ra để giải quyết những vấn đề này; nó đại diện cho bước chuyển then chốt từ “có thể chạy” sang “có thể phục vụ ổn định”.

Tóm lại, Agent không chỉ có một cách xây dựng. Hiểu sâu triết lý thiết kế của các framework được bàn trong chương này giúp chúng ta không chỉ trở thành “người dùng công cụ” giỏi hơn, mà còn hiểu các ưu nhược điểm và đánh đổi trong thiết kế framework.

Chương tiếp theo, chúng ta sẽ đi vào nội dung cốt lõi của giáo trình: từ con số không, tự tay xây dựng một framework Agent của riêng mình, kết hợp tất cả lý thuyết và thực hành.


## Bài tập

1. Chương này giới thiệu bốn framework Agent có đặc sắc riêng: `AutoGen`, `AgentScope`, `CAMEL` và `LangGraph`. Hãy phân tích:

   - Trong Bảng 6.1 ở mục 6.1.2, nhiều chiều của bốn framework đã được so sánh. Hãy chọn hai framework bạn quen nhất, so sánh sâu thêm theo ba chiều “mô hình cộng tác”, “cách kiểm soát”, “tình huống áp dụng”.
   - Chương này đề cập đánh đổi giữa “cộng tác nảy sinh” và “kiểm soát tường minh”; bạn hiểu ý nghĩa của hai triết lý thiết kế này như thế nào?

2. Trong ca `AutoGen` ở mục 6.2, chúng ta xây dựng một “nhóm phát triển phần mềm”. Hãy mở rộng suy nghĩ dựa trên ca này:

   > <strong>Gợi ý</strong>: đây là bài thực hành tay, khuyến nghị thao tác thực tế

   - Nhóm hiện tại dùng chế độ `RoundRobinGroupChat` (nhóm chat luân phiên), Agent phát biểu theo thứ tự cố định. Nếu yêu cầu thay đổi, mã của kỹ sư cần quay lại quản lý sản phẩm để kiểm duyệt lại, nên sửa quy trình cộng tác thế nào? Hãy thiết kế cơ chế hỗ trợ “quay lui động”.
   - Trong ca, chúng ta định nghĩa vai trò và trách nhiệm cho mỗi Agent qua `System Message`. Hãy thử thêm một vai mới “kỹ sư kiểm thử” (`Quality Assurance`) cho nhóm, thiết kế system message của nó để nó có thể thực thi kiểm thử tự động sau khi kiểm duyệt mã.
   - Cộng tác hội thoại của `AutoGen` có tính không ổn định, có thể khiến hội thoại lệch chủ đề hoặc rơi vào vòng lặp. Hãy suy nghĩ: thiết kế một bộ “giám sát chất lượng hội thoại” thế nào để can thiệp kịp thời khi phát hiện bất thường?

3. Trong ca `AgentScope` ở mục 6.3, chúng ta hiện thực trò chơi “ma sói Tam Quốc”. Hãy phân tích sâu:

   - Ca này dùng `MsgHub` (trung tâm tin nhắn) để quản lý giao tiếp giữa các Agent. Hãy giải thích ưu thế của kiến trúc hướng tin nhắn so với gọi hàm truyền thống? Kiến trúc này đặc biệt có giá trị trong tình huống nào?
   - Trò chơi dùng đầu ra có cấu trúc (như `DiscussionModelCN`, `WitchActionModelCN`) để ràng buộc hành vi Agent. Hãy thiết kế một vai trò trò chơi mới “thợ săn”, định nghĩa mô hình đầu ra có cấu trúc tương ứng, gồm định nghĩa trường và quy tắc xác minh.
   - `AgentScope` hỗ trợ triển khai phân tán, nghĩa là các Agent khác nhau có thể chạy trên máy chủ khác nhau. Hãy suy nghĩ: trong tình huống trò chơi thời gian thực như “ma sói Tam Quốc”, triển khai phân tán mang lại thách thức kỹ thuật nào? Làm sao đảm bảo thứ tự và tính nhất quán của tin nhắn?

4. Trong ca `CAMEL` ở mục 6.4, chúng ta để nhà tâm lý học và nhà văn cộng tác sáng tác sách điện tử.

   - Trong ca, cộng tác bị buộc dừng khi phát hiện dấu hiệu `<CAMEL_TASK_DONE>`. Nhưng nếu hai Agent bất đồng ý kiến (một bên cho rằng có thể dừng, một bên cho rằng không nên), không đạt được nhất trí thì sao? Hãy thiết kế cơ chế tương thích “giải quyết xung đột”.
   - `CAMEL` ban đầu được thiết kế cho cộng tác hai Agent, nhưng hiện đã mở rộng hỗ trợ đa Agent. Hãy tra tài liệu mới nhất của `CAMEL`, tìm hiểu mô-đun cộng tác đa Agent [`workforce`](https://docs.camel-ai.org/key_modules/workforce), và kết hợp sơ đồ kiến trúc để giải thích nó khác gì mô hình nhóm chat của `AutoGen`.

5. Trong ca `LangGraph` ở mục 6.5, chúng ta xây dựng “trợ lý hỏi đáp ba bước”. Hãy phân tích:

   - `LangGraph` mô hình hóa quy trình Agent thành máy trạng thái và đồ thị có hướng. Hãy vẽ cấu trúc đồ thị của quy trình “hiểu – tìm kiếm – trả lời” trong ca, chú thích nút, cạnh và điều kiện chuyển trạng thái.
   - Trợ lý hiện tại là quy trình tuyến tính. Hãy mở rộng ca này, thêm một nút “phản tư”: nếu chất lượng câu trả lời sinh ra thấp (ví dụ quá ngắn hoặc thiếu chi tiết), hệ thống nên tìm kiếm lại hoặc sinh lại câu trả lời. Hãy thiết kế logic cạnh điều kiện cho cơ chế chu trình này.
   - Ưu thế của `LangGraph` nằm ở hỗ trợ native chu trình. Hãy thiết kế một tình huống ứng dụng phức tạp hơn, tận dụng đầy đủ đặc tính này: ví dụ vòng “sinh mã – kiểm thử – sửa”, vòng “viết bài – phản biện – sửa”, v.v. Yêu cầu vẽ cấu trúc đồ thị hoàn chỉnh và giải thích chức năng các nút then chốt.

6. Chọn framework là một trong những quyết định then chốt trong quá trình phát triển sản phẩm Agent. Giả sử bạn là kiến trúc sư kỹ thuật của một công ty `AI`; công ty dự định phát triển ba ứng dụng sản phẩm Agent sau; hãy chọn framework phù hợp nhất cho mỗi ứng dụng (`AutoGen`, `AgentScope`, `CAMEL`, `LangGraph` hoặc tự phát triển từ con số không không dùng framework), và giải thích chi tiết lý do:

   <strong>Ứng dụng A</strong>: hệ thống chăm sóc khách hàng thông minh, cần xử lý lượng lớn yêu cầu người dùng đồng thời (1000+/giây), yêu cầu thời gian phản hồi dưới 2 giây, hệ thống cần chạy ổn định 7×24 giờ và hỗ trợ mở rộng ngang.

   <strong>Ứng dụng B</strong>: nền tảng hỗ trợ viết bài báo nghiên cứu, cần một “Agent nhà nghiên cứu” và một “Agent viết” cộng tác sâu, cùng hoàn thành tổng quan tài liệu, thiết kế thí nghiệm, phân tích dữ liệu và viết bài báo. Yêu cầu Agent có thể thảo luận sâu nhiều vòng, tự chủ đẩy nhiệm vụ.

   <strong>Ứng dụng C</strong>: hệ thống phê duyệt kiểm soát rủi ro tài chính, cần xử lý đơn vay theo quy trình nghiêm ngặt: kiểm duyệt tài liệu → đánh giá rủi ro → tính hạn mức → kiểm tra tuân thủ → kiểm duyệt thủ công → quyết định cuối cùng. Mỗi khâu có tiêu chí phán đoán và logic nhánh rõ ràng; yêu cầu quy trình có thể truy vết, kiểm toán.


## Tài liệu tham khảo

[1] Wu Q, Bansal G, Zhang J, et al. Autogen: Enabling next-gen LLM applications via multi-agent conversations[C]//First Conference on Language Modeling. 2024.

[2] Gao D, Li Z, Pan X, et al. Agentscope: A flexible yet robust multi-agent platform[J]. arXiv preprint arXiv:2402.14034, 2024.

[3] Li G, Hammoud H, Itani H, et al. Camel: Communicative agents for" mind" exploration of large language model society[J]. Advances in Neural Information Processing Systems, 2023, 36: 51991-52008.

[4] LangChain. LangGraph [EB/OL]. (2024). https://github.com/langchain-ai/langgraph.

[5] Microsoft. AutoGen - UserProxyAgent [EB/OL]. (2024). https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.agents.html#autogen_agentchat.agents.UserProxyAgent.

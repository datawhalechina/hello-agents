# Chương 1: Làm quen với Agent

Chào mừng bạn đến với thế giới của Agent! Trong thời đại mà làn sóng trí tuệ nhân tạo đang lan rộng khắp toàn cầu, **Agent (tác tử)** đã trở thành một trong những khái niệm cốt lõi thúc đẩy chuyển đổi công nghệ và đổi mới ứng dụng. Dù mục tiêu của bạn là trở thành nhà nghiên cứu, kỹ sư trong lĩnh vực AI, hay chỉ là một người quan sát mong muốn hiểu sâu về biên giới công nghệ, thì việc nắm bắt bản chất của Agent sẽ là một mắt xích không thể thiếu trong hệ thống tri thức của bạn.

Vì vậy, trong chương này, hãy cùng quay về điểm khởi đầu và thảo luận vài câu hỏi: Agent là gì? Nó có những loại chính nào? Nó tương tác với thế giới mà chúng ta đang sống như thế nào? Qua những thảo luận này, chúng tôi hy vọng sẽ đặt nền tảng vững chắc cho việc học tập và khám phá của bạn trong tương lai.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-0.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 1.1 Vòng lặp tương tác cơ bản giữa Agent và môi trường</p>
</div>

## 1.1 Agent là gì?

Khi khám phá bất kỳ khái niệm phức tạp nào, tốt nhất chúng ta nên bắt đầu từ một định nghĩa ngắn gọn. Trong lĩnh vực trí tuệ nhân tạo, Agent được định nghĩa là bất kỳ thực thể nào có thể cảm nhận **môi trường (Environment)** mà nó đang tồn tại thông qua **cảm biến (Sensors)**, và **tự chủ** thực hiện **hành động (Action)** thông qua **cơ cấu chấp hành (Actuators)** để đạt được một mục tiêu cụ thể.

Định nghĩa này bao hàm bốn yếu tố cơ bản trong sự tồn tại của Agent. Môi trường là thế giới bên ngoài nơi Agent tồn tại. Đối với một xe tự lái, môi trường là giao thông đường bộ luôn biến động; đối với một thuật toán giao dịch, môi trường là thị trường tài chính biến đổi từng giây. Agent không tách rời khỏi môi trường; nó liên tục cảm nhận trạng thái môi trường thông qua các cảm biến của mình. Camera, micro, radar hoặc các luồng dữ liệu do nhiều loại **giao diện lập trình ứng dụng (Application Programming Interface, API)** trả về đều là phần mở rộng cho năng lực cảm nhận của nó.

Sau khi thu thập thông tin, Agent cần thực hiện hành động để gây ảnh hưởng lên môi trường, thay đổi trạng thái môi trường thông qua cơ cấu chấp hành. Cơ cấu chấp hành có thể là thiết bị vật lý (như cánh tay robot, vô lăng) hoặc công cụ ảo (như thực thi một đoạn mã, gọi một dịch vụ).

Tuy nhiên, thứ thực sự mang lại “trí tuệ” cho Agent chính là **tính tự chủ (Autonomy)**. Agent không chỉ là một chương trình phản ứng thụ động với kích thích bên ngoài hay thực thi nghiêm ngặt các chỉ thị được định trước; nó có thể đưa ra quyết định độc lập dựa trên cảm nhận và trạng thái nội tại của mình để đạt được mục tiêu thiết kế. Vòng lặp kín từ cảm nhận đến hành động này tạo nên nền tảng cho mọi hành vi của Agent, như được thể hiện trong Hình 1.1.

### 1.1.1 Agent dưới góc nhìn truyền thống

Trước khi làn sóng **mô hình ngôn ngữ lớn (Large Language Model, LLM)** hiện nay xuất hiện, những người tiên phong của trí tuệ nhân tạo đã dành nhiều thập kỷ để khám phá và xây dựng khái niệm “Agent”. Những mô hình mà ngày nay chúng ta gọi là “Agent truyền thống” không phải là một khái niệm tĩnh duy nhất, mà đã trải qua một con đường tiến hóa rõ ràng từ đơn giản đến phức tạp, từ phản ứng thụ động đến học tập chủ động.

Điểm khởi đầu của sự tiến hóa này là những **Agent phản xạ đơn giản (Simple Reflex Agent)** có cấu trúc đơn giản nhất. Lõi ra quyết định của chúng được tạo thành từ các quy tắc “điều kiện - hành động” do kỹ sư thiết kế rõ ràng, như trong Hình 1.2. Một chiếc máy điều hòa nhiệt độ tự động cổ điển là ví dụ như vậy: nếu cảm biến nhận thấy nhiệt độ phòng cao hơn giá trị đặt, nó sẽ khởi động hệ thống làm mát.

Loại Agent này hoàn toàn phụ thuộc vào đầu vào cảm nhận hiện tại, không có khả năng ghi nhớ hay dự đoán. Nó giống như một bản năng được số hóa, đáng tin cậy và hiệu quả, nhưng vì thế mà không thể xử lý những nhiệm vụ phức tạp cần hiểu ngữ cảnh. Hạn chế của nó đặt ra một câu hỏi then chốt: nếu trạng thái hiện tại của môi trường không đủ làm căn cứ duy nhất cho quyết định, thì Agent nên làm gì?

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-1.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 1.2 Sơ đồ logic ra quyết định của Agent phản xạ đơn giản</p>
</div>

Để trả lời câu hỏi này, các nhà nghiên cứu đã đưa vào khái niệm “trạng thái” và phát triển **Agent phản xạ dựa trên mô hình (Model-Based Reflex Agent)**. Loại Agent này sở hữu một **mô hình thế giới (World Model)** nội tại, dùng để theo dõi và hiểu những khía cạnh của môi trường không thể cảm nhận trực tiếp. Nó cố gắng trả lời: “Thế giới hiện tại trông như thế nào?”. Ví dụ, một chiếc xe tự lái đang chạy trong đường hầm, dù camera tạm thời không thể cảm nhận được chiếc xe phía trước, mô hình nội tại của nó vẫn duy trì phán đoán về sự tồn tại, tốc độ và vị trí ước tính của chiếc xe đó. Mô hình nội tại này mang lại cho Agent một dạng “bộ nhớ” sơ khai, khiến quyết định của nó không còn chỉ dựa vào cảm nhận tức thời mà dựa trên một sự hiểu biết liên tục và đầy đủ hơn về trạng thái thế giới.

Tuy nhiên, chỉ hiểu thế giới vẫn chưa đủ, Agent cần có mục tiêu rõ ràng. Điều này thúc đẩy sự phát triển của **Agent dựa trên mục tiêu (Goal-Based Agent)**. Khác với hai loại trước, hành vi của nó không còn là phản ứng thụ động với môi trường mà là chủ động, có tính dự báo trong việc lựa chọn những hành động có thể dẫn tới một trạng thái tương lai cụ thể. Câu hỏi mà loại Agent này cần trả lời là: “Tôi nên làm gì để đạt được mục tiêu?”. Một ví dụ kinh điển là hệ thống định vị GPS: mục tiêu của bạn là đến công ty, Agent sẽ dựa trên dữ liệu bản đồ (mô hình thế giới) và dùng thuật toán tìm kiếm (như thuật toán A*) để lập kế hoạch (Planning) một lộ trình tối ưu. Năng lực cốt lõi của loại Agent này thể hiện ở việc cân nhắc và lập kế hoạch cho tương lai.

Xa hơn nữa, mục tiêu trong thế giới thực thường không đơn nhất. Chúng ta không chỉ muốn đến công ty, mà còn muốn thời gian ngắn nhất, lộ trình tiết kiệm nhiên liệu nhất và tránh tắc đường. Khi cần cân bằng nhiều mục tiêu, **Agent dựa trên lợi ích (Utility-Based Agent)** xuất hiện. Nó gán cho mỗi trạng thái thế giới có thể xảy ra một giá trị lợi ích, giá trị này biểu thị mức độ hài lòng. Mục tiêu cốt lõi của Agent không còn là đơn giản đạt được một trạng thái cụ thể mà là tối đa hóa lợi ích kỳ vọng. Nó cần trả lời một câu hỏi phức tạp hơn: “Hành vi nào sẽ mang lại cho tôi kết quả hài lòng nhất?”. Kiến trúc này giúp Agent học cách cân bằng giữa các mục tiêu xung đột, khiến quyết định của nó gần với lựa chọn lý tính của con người hơn.

Đến đây, các Agent mà chúng ta thảo luận tuy chức năng ngày càng phức tạp, nhưng logic ra quyết định cốt lõi của chúng, dù là quy tắc, mô hình hay hàm lợi ích, vẫn phụ thuộc vào tri thức tiên nghiệm của nhà thiết kế con người. Nếu Agent có thể không dựa vào thiết lập sẵn mà tự học thông qua tương tác với môi trường thì sao?

Đó chính là tư tưởng cốt lõi của **Agent học (Learning Agent)**, và **học tăng cường (Reinforcement Learning, RL)** là con đường tiêu biểu nhất để hiện thực hóa tư tưởng này. Một Agent học bao gồm một phần tử hiệu năng (tức các loại Agent mà chúng ta đã thảo luận ở trên) và một phần tử học. Phần tử học không ngừng điều chỉnh chiến lược ra quyết định của phần tử hiệu năng bằng cách quan sát kết quả hành động của phần tử hiệu năng trong môi trường.

Hãy tưởng tượng một AI học chơi cờ. Ban đầu nó có thể chỉ đặt quân ngẫu nhiên, khi cuối cùng thắng một ván, hệ thống sẽ trao cho nó một phần thưởng dương. Qua rất nhiều ván tự đấu, phần tử học sẽ dần khám phá những nước đi nào có khả năng dẫn tới chiến thắng cuối cùng cao hơn. AlphaGo Zero là một thành tựu mang tính cột mốc của tư tưởng này. Trong trò chơi phức tạp là cờ vây, thông qua học tăng cường, nó đã khám phá ra nhiều chiến lược hiệu quả vượt xa tri thức hiện có của con người.

Từ chiếc máy điều hòa đơn giản, đến chiếc xe có mô hình nội tại, đến hệ thống định vị biết lập lộ trình, đến người ra quyết định biết cân nhắc lợi hại, và cuối cùng là người học có thể tự tiến hóa qua kinh nghiệm. Con đường tiến hóa này cho thấy quỹ đạo phát triển mà trí tuệ nhân tạo truyền thống đã trải qua trên con đường xây dựng trí tuệ máy. Chúng đã đặt nền tảng vững chắc và cần thiết cho việc chúng ta hiểu những mô hình Agent tiên tiến hơn ngày nay.

### 1.1.2 Mô hình mới do mô hình ngôn ngữ lớn dẫn dắt

Sự xuất hiện của các mô hình ngôn ngữ lớn, tiêu biểu là **GPT (Generative Pre-trained Transformer)**, đang thay đổi rõ rệt cách xây dựng và biên giới năng lực của Agent. Cơ chế ra quyết định cốt lõi của Agent LLM do mô hình ngôn ngữ lớn dẫn dắt có sự khác biệt bản chất so với Agent truyền thống, từ đó mang lại cho nó một loạt đặc tính hoàn toàn mới.

Sự chuyển dịch này có thể thấy rõ qua so sánh giữa hai loại trên nhiều chiều như lõi, nguồn tri thức, cách tương tác, như trong Bảng 1.1. Nói ngắn gọn, năng lực của Agent truyền thống bắt nguồn từ lập trình tường minh và xây dựng tri thức của kỹ sư, mô hình hành vi của nó có tính xác định và có biên giới; còn Agent LLM, thông qua tiền huấn luyện trên khối dữ liệu khổng lồ, đã có được mô hình thế giới ẩn và năng lực nổi sinh mạnh mẽ, giúp nó xử lý nhiệm vụ phức tạp một cách linh hoạt và tổng quát hơn.

<div align="center">
  <p>Bảng 1.1 So sánh cốt lõi giữa Agent truyền thống và Agent do LLM dẫn dắt</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-2.png" alt="Mô tả hình ảnh" width="90%"/>
</div>

Sự khác biệt này cho phép Agent LLM xử lý trực tiếp những chỉ thị ngôn ngữ tự nhiên ở mức cao, mơ hồ và chứa nhiều thông tin ngữ cảnh. Hãy lấy một “trợ lý du lịch thông minh” làm ví dụ để minh họa.

Trước khi Agent LLM xuất hiện, lập kế hoạch du lịch thường có nghĩa là người dùng phải chuyển đổi thủ công giữa nhiều ứng dụng chuyên dụng (như thời tiết, bản đồ, trang đặt vé), và chính người dùng đảm nhận vai trò tích hợp thông tin và ra quyết định. Còn một Agent LLM có thể tích hợp toàn bộ quy trình này. Khi nhận được một chỉ thị mơ hồ như “lập kế hoạch cho một chuyến đi Hạ Môn”, cách nó làm việc thể hiện những điểm sau:

- **Lập kế hoạch và suy luận**: Agent trước hết phân rã mục tiêu cấp cao này thành một chuỗi nhiệm vụ con logic, ví dụ: `[Xác nhận sở thích đi lại] -> [Tra cứu thông tin điểm đến] -> [Soạn lịch trình dự thảo] -> [Đặt vé và chỗ ở]`. Đây là một quá trình lập kế hoạch nội tại, do mô hình dẫn dắt.
- **Sử dụng công cụ**: Khi thực thi kế hoạch, Agent nhận ra lỗ hổng thông tin và chủ động gọi công cụ bên ngoài để bổ sung. Ví dụ, nó sẽ gọi giao diện tra cứu thời tiết để lấy thời tiết thời gian thực, và dựa trên thông tin “dự báo có mưa”, trong lập kế hoạch tiếp theo nó sẽ nghiêng về gợi ý các hoạt động trong nhà.
- **Điều chỉnh linh hoạt**: Trong quá trình tương tác, Agent coi phản hồi của người dùng (như “khách sạn này vượt ngân sách”) là ràng buộc mới, từ đó điều chỉnh các hành động tiếp theo, tìm kiếm lại và gợi ý những lựa chọn đáp ứng yêu cầu mới. Toàn bộ quy trình “**tra thời tiết → điều chỉnh lịch trình → đặt khách sạn**” cho thấy khả năng tự điều chỉnh hành vi theo ngữ cảnh của nó.

Tóm lại, chúng ta đang chuyển từ việc phát triển các công cụ tự động hóa chuyên dụng sang xây dựng những hệ thống có thể tự chủ giải quyết vấn đề. Cốt lõi không còn là viết mã, mà là dẫn dắt một “bộ não” tổng quát biết lập kế hoạch, hành động và học hỏi.

### 1.1.3 Các loại Agent

Tiếp nối phần ôn lại sự tiến hóa của Agent ở trên, mục này sẽ phân loại Agent theo ba chiều bổ trợ lẫn nhau.

(1) **Phân loại dựa trên kiến trúc ra quyết định nội tại**

Chiều phân loại thứ nhất dựa trên mức độ phức tạp của kiến trúc ra quyết định nội tại của Agent, góc nhìn này được trình bày một cách hệ thống trong cuốn *Artificial Intelligence: A Modern Approach*<sup>[1]</sup>. Như đã nêu ở mục 1.1.1, bản thân con đường tiến hóa của Agent truyền thống đã tạo thành bậc thang phân loại kinh điển nhất, bao gồm từ Agent **phản xạ** đơn giản, đến Agent **dựa trên mô hình** có mô hình nội tại, rồi đến Agent **dựa trên mục tiêu** và **dựa trên lợi ích** có tính tiên liệu hơn. Ngoài ra, **khả năng học** là một siêu năng lực có thể gán cho tất cả các loại trên, giúp chúng tự cải thiện qua kinh nghiệm.

(2) **Phân loại dựa trên thời gian và tính phản ứng**

Ngoài mức độ phức tạp của kiến trúc nội tại, còn có thể phân loại Agent theo chiều thời gian xử lý quyết định. Góc nhìn này quan tâm đến việc Agent hành động ngay sau khi nhận thông tin hay hành động sau khi đã suy nghĩ và lập kế hoạch kỹ lưỡng. Điều này cho thấy một đánh đổi cốt lõi trong thiết kế Agent: sự cân bằng giữa **tính phản ứng (Reactivity)** theo đuổi tốc độ và **tính suy xét (Deliberation)** theo đuổi lời giải tối ưu, như trong Hình 1.3.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-3.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 1.3 Đồ thị quan hệ giữa thời gian ra quyết định và chất lượng quyết định của Agent</p>
</div>

- **Agent phản ứng (Reactive Agents)**

Loại Agent này phản ứng gần như tức thời với kích thích từ môi trường, độ trễ quyết định rất thấp. Chúng thường tuân theo ánh xạ trực tiếp từ cảm nhận đến hành động, không lập kế hoạch tương lai hoặc chỉ lập rất ít. Các Agent **phản xạ đơn giản** và **dựa trên mô hình** ở trên đều thuộc nhóm này.

Ưu thế cốt lõi của chúng nằm ở **tốc độ nhanh, chi phí tính toán thấp**, điều này rất quan trọng trong môi trường động cần ra quyết định nhanh. Ví dụ, hệ thống túi khí của xe phải phản ứng trong vài mili giây kể từ khi va chạm, mọi độ trễ đều có thể gây hậu quả nghiêm trọng; tương tự, robot giao dịch tần suất cao cũng phải dựa vào quyết định phản ứng để nắm bắt cơ hội thị trường thoáng qua. Tuy nhiên, cái giá của tốc độ này là sự “thiển cận”: do thiếu lập kế hoạch dài hạn, Agent phản ứng dễ rơi vào tối ưu cục bộ, khó hoàn thành nhiệm vụ phức tạp cần phối hợp nhiều bước.

- **Agent lập kế hoạch (Deliberative Agents)**

Đối lập với Agent phản ứng, Agent lập kế hoạch (hay còn gọi là Agent suy xét) thực hiện tư duy và lập kế hoạch phức tạp trước khi hành động. Chúng không phản ứng ngay với cảm nhận mà trước tiên dùng mô hình thế giới nội tại để khám phá một cách hệ thống các khả năng tương lai, đánh giá hậu quả của những chuỗi hành động khác nhau, nhằm tìm ra một con đường tốt nhất để đạt mục tiêu. Agent **dựa trên mục tiêu** và **dựa trên lợi ích** là những Agent lập kế hoạch điển hình.

Có thể ví quá trình ra quyết định của chúng với một kỳ thủ. Kỳ thủ không chỉ nhìn nước đi trước mắt mà còn dự đoán cách đối thủ có thể ứng phó, rồi vạch ra các nước tiếp theo, thậm chí hàng chục nước. Năng lực suy xét này giúp chúng xử lý những nhiệm vụ phức tạp cần tầm nhìn dài hạn, như xây dựng một kế hoạch kinh doanh hay lập kế hoạch cho một chuyến đi dài. Ưu thế của chúng nằm ở tính chiến lược và tầm nhìn của quyết định. Tuy nhiên, mặt trái của ưu thế này là chi phí thời gian và tính toán cao. Trong môi trường biến đổi từng giây, khi Agent lập kế hoạch vẫn đang suy xét, thời điểm tốt nhất để hành động có thể đã trôi qua từ lâu.

- **Agent lai (Hybrid Agents)**

Các nhiệm vụ phức tạp trong thế giới thực thường cần cả phản ứng tức thời lẫn lập kế hoạch dài hạn. Ví dụ, trợ lý du lịch thông minh mà chúng ta đã nhắc đến cần điều chỉnh gợi ý theo phản hồi tức thời của người dùng (như “khách sạn này quá đắt”) (tính phản ứng), đồng thời phải lập được một phương án du lịch trọn vẹn nhiều ngày (tính suy xét). Vì vậy, Agent lai ra đời, nhằm kết hợp ưu điểm của cả hai và đạt được sự cân bằng giữa phản ứng và lập kế hoạch.

Một kiến trúc lai kinh điển là thiết kế phân tầng: tầng dưới là một mô-đun phản ứng nhanh, xử lý tình huống khẩn cấp và hành động cơ bản; tầng trên là một mô-đun lập kế hoạch thận trọng, chịu trách nhiệm xác lập mục tiêu dài hạn. Còn các Agent LLM hiện đại thể hiện một mô hình lai linh hoạt hơn. Chúng thường vận hành trong một vòng lặp “suy nghĩ - hành động - quan sát”, khéo léo hòa hai chế độ vào nhau:

- **Suy luận (Reasoning)**: Ở giai đoạn “suy nghĩ”, LLM phân tích tình huống hiện tại và lập kế hoạch cho hành động hợp lý tiếp theo. Đây là một quá trình suy xét.
- **Phản ứng (Acting & Observing)**: Ở giai đoạn “hành động” và “quan sát”, Agent tương tác với công cụ bên ngoài hoặc môi trường và nhận phản hồi ngay lập tức. Đây là một quá trình phản ứng.

Bằng cách này, Agent phân rã một nhiệm vụ lớn cần lập kế hoạch dài hạn thành một chuỗi vi vòng lặp “lập kế hoạch - phản ứng”. Điều đó giúp nó vừa linh hoạt ứng phó với thay đổi tức thời của môi trường, vừa cuối cùng hoàn thành được những mục tiêu dài hạn phức tạp qua các bước liên tục.

**(3) Phân loại dựa trên biểu diễn tri thức**

Đây là một chiều phân loại mang tính nền tảng hơn, khảo sát xem tri thức mà Agent dùng để ra quyết định tồn tại dưới hình thức nào trong “tâm trí” của nó. Câu hỏi này là lõi của một cuộc tranh luận kéo dài hơn nửa thế kỷ trong lĩnh vực trí tuệ nhân tạo và đã tạo nên hai nền văn hóa AI khác biệt rõ rệt.

- **AI cận biểu tượng (Sub-symbolic AI)**

Cận biểu tượng, hay còn gọi là thuyết liên kết, cho rằng tri thức không phải là những quy tắc tường minh, mà được phân tán một cách ẩn trong một mạng nơ-ron phức tạp gồm lượng lớn nơ-ron, như những mẫu thống kê học được từ khối dữ liệu khổng lồ. Mạng nơ-ron và học sâu là đại diện của nó.

Như phần bên trái của Hình 1.4, AI cận biểu tượng giống như một đứa trẻ đang tập nói. Đứa trẻ không nhận biết con mèo bằng cách học quy tắc “mèo có bốn chân, có lông, kêu meo meo”, mà sau khi xem hàng nghìn bức ảnh mèo, mạng nơ-ron trong não có thể nhận diện mẫu thị giác của khái niệm “mèo”. Sức mạnh của phương pháp này nằm ở năng lực nhận diện mẫu và độ bền vững với dữ liệu nhiễu. Nó có thể xử lý dễ dàng dữ liệu phi cấu trúc như hình ảnh, âm thanh, những nhiệm vụ thường rất khó với hệ thống phụ thuộc quy tắc tường minh.

Tuy nhiên, năng lực trực giác mạnh mẽ này cũng đi kèm tính không minh bạch. Hệ thống cận biểu tượng thường được xem là một **hộp đen (Black Box)**. Nó có thể nhận diện con mèo trong ảnh với độ chính xác đáng kinh ngạc, nhưng nếu bạn hỏi “vì sao bạn nghĩ đây là mèo?”, nó rất có thể không đưa ra được lời giải thích hợp logic. Ngoài ra, nó hoạt động kém trên các nhiệm vụ suy luận logic thuần túy, đôi khi tạo ra những ảo giác nghe có lý nhưng sai về mặt sự thật.

- **AI biểu tượng (Symbolic AI)**

Khác với cận biểu tượng, biểu tượng thường được gọi là trí tuệ nhân tạo truyền thống, niềm tin cốt lõi là: trí tuệ bắt nguồn từ thao tác logic trên các biểu tượng. Ở đây biểu tượng là những thực thể con người có thể đọc được (như từ ngữ, khái niệm), còn thao tác tuân theo những quy tắc logic chặt chẽ, như phần giữa của Hình 1.4. Điều này giống như một thủ thư tỉ mỉ, sắp xếp tri thức về thế giới thành những cơ sở quy tắc và đồ thị tri thức rõ ràng.

Ưu thế chính của nó là tính minh bạch và khả năng giải thích. Vì các bước suy luận tường minh, quá trình ra quyết định có thể được truy vết đầy đủ, điều này rất quan trọng trong các lĩnh vực rủi ro cao như tài chính, y tế. Tuy nhiên, “gót chân Achilles” của nó là tính dễ tổn thương: nó phụ thuộc vào một hệ thống quy tắc hoàn chỉnh, nhưng trong thế giới thực đầy mơ hồ và ngoại lệ, bất kỳ tình huống mới nào chưa được bao phủ đều có thể khiến hệ thống thất bại, đây chính là cái gọi là “nút cổ chai thu nhận tri thức”.

- **AI thần kinh - biểu tượng (Neuro-Symbolic AI)**

Trong thời gian dài, hai phe cận biểu tượng và biểu tượng như hai đường thẳng song song, phát triển riêng rẽ. Để khắc phục hạn chế của hai mô hình trên, một tư tưởng “hòa giải lớn” bắt đầu xuất hiện, đó là AI thần kinh - biểu tượng, còn gọi là thuyết lai thần kinh - biểu tượng. Mục tiêu của nó là hợp nhất ưu điểm của hai mô hình, tạo ra một Agent lai vừa có thể học từ dữ liệu như mạng nơ-ron, vừa có thể suy luận logic như hệ thống biểu tượng. Nói cách khác, nó cố gắng kết hợp năng lực nhận diện mẫu mà cận biểu tượng giỏi với năng lực suy luận logic mà biểu tượng giỏi. Lý thuyết hai hệ thống do nhà kinh tế học đoạt giải Nobel Daniel Kahneman đề xuất trong cuốn *Thinking, Fast and Slow* (Suy nghĩ nhanh và chậm) mang lại một phép loại suy tuyệt vời để hiểu AI thần kinh - biểu tượng<sup>[2]</sup>. Theo thứ tự trình bày từ trái sang phải của Hình 1.4, sự tương ứng này có thể được khái quát như sau:

- **Hệ thống 1** là chế độ tư duy nhanh, trực giác, song song, tương tự năng lực nhận diện mẫu mạnh mẽ của AI cận biểu tượng.
- **Hệ thống 2** là tư duy chậm rãi, có phương pháp, dựa trên logic và thận trọng, đúng như quá trình suy luận của AI biểu tượng.
- **AI thần kinh - biểu tượng** kết hợp nhận diện mẫu của Hệ thống 1 với suy luận logic của Hệ thống 2, giúp hai bên phối hợp hoạt động.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-4.png" alt="Sơ đồ quan hệ giữa AI cận biểu tượng, AI biểu tượng và AI thần kinh - biểu tượng" width="90%"/>
  <p>Hình 1.4 Các mô hình biểu diễn tri thức của cận biểu tượng, biểu tượng và lai thần kinh - biểu tượng</p>
</div>

Trí tuệ của con người bắt nguồn từ sự phối hợp của hai hệ thống này. Tương tự, một AI thực sự bền vững cũng cần có ưu điểm của cả hai. Agent do mô hình ngôn ngữ lớn dẫn dắt là một ví dụ thực tiễn tuyệt vời của AI thần kinh - biểu tượng: lõi của nó là một mạng nơ-ron khổng lồ, mang lại năng lực nhận diện mẫu và sinh ngôn ngữ; trong quá trình làm việc, nó lại sinh ra một chuỗi bước trung gian có cấu trúc, như suy nghĩ, kế hoạch hoặc lời gọi API, đây đều là những biểu tượng tường minh, có thể thao tác. Bằng cách này, nó kết hợp nhận diện mẫu dựa trên mạng nơ-ron với suy luận logic dựa trên biểu tượng.



## 1.2 Cấu tạo và nguyên lý vận hành của Agent

### 1.2.1 Định nghĩa môi trường nhiệm vụ

Để hiểu cách Agent vận hành, trước tiên chúng ta phải hiểu **môi trường nhiệm vụ** mà nó tồn tại. Trong lĩnh vực trí tuệ nhân tạo, thường dùng **mô hình PEAS** để mô tả chính xác một môi trường nhiệm vụ, tức phân tích **thước đo hiệu năng (Performance), môi trường (Environment), cơ cấu chấp hành (Actuators) và cảm biến (Sensors)**. Lấy trợ lý du lịch thông minh đã nhắc ở trên làm ví dụ, Bảng 1.2 dưới đây cho thấy cách áp dụng mô hình PEAS để đặc tả môi trường nhiệm vụ của nó.

<div align="center">
  <p>Bảng 1.2 Mô tả PEAS của trợ lý du lịch thông minh</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-6.png" alt="Mô tả hình ảnh" width="90%"/>
</div>


Trong thực tiễn, môi trường số mà Agent LLM tồn tại thể hiện một số đặc tính phức tạp, những đặc tính này ảnh hưởng trực tiếp đến thiết kế Agent.

Thứ nhất, môi trường thường **có thể quan sát một phần**. Ví dụ, khi tra cứu chuyến bay, trợ lý du lịch không thể lấy được toàn bộ thông tin chỗ ngồi thời gian thực của tất cả hãng hàng không trong một lần. Nó chỉ có thể thấy một phần dữ liệu do API đặt vé trả về, điều này đòi hỏi Agent phải có năng lực ghi nhớ (nhớ các tuyến đã tra cứu) và khám phá (thử các ngày tra cứu khác nhau).

Thứ hai, kết quả của hành động cũng không phải lúc nào cũng xác định. Dựa trên tính dự đoán được của kết quả, môi trường có thể chia thành **tất định** và **ngẫu nhiên**. Môi trường nhiệm vụ của trợ lý du lịch là môi trường ngẫu nhiên điển hình. Khi nó tìm giá vé, hai lần gọi liên tiếp có thể trả về giá vé và số chỗ còn lại khác nhau, đòi hỏi Agent phải có năng lực xử lý bất định, theo dõi thay đổi và ra quyết định kịp thời.

Ngoài ra, trong môi trường còn có thể tồn tại những tác nhân hành động khác, tạo thành môi trường **đa Agent (Multi-agent)**. Với trợ lý du lịch, hành vi đặt vé của người dùng khác, các script tự động khác, thậm chí hệ thống điều chỉnh giá động của hãng bay, đều là những “Agent” khác trong môi trường. Hành động của chúng (ví dụ đặt tấm vé giảm giá cuối cùng) sẽ thay đổi trực tiếp trạng thái môi trường mà trợ lý du lịch đang tồn tại, đặt ra yêu cầu cao hơn về phản ứng nhanh và lựa chọn chiến lược của Agent.

Cuối cùng, gần như mọi nhiệm vụ đều diễn ra trong môi trường **tuần tự** và **động**. “Tuần tự” nghĩa là hành động hiện tại ảnh hưởng đến tương lai; còn “động” nghĩa là bản thân môi trường có thể thay đổi trong khi Agent ra quyết định. Điều này đòi hỏi vòng lặp “cảm nhận - suy nghĩ - hành động - quan sát” của Agent phải thích ứng nhanh và linh hoạt với một thế giới luôn biến đổi.

### 1.2.2 Cơ chế vận hành của Agent

Sau khi đã định nghĩa môi trường nhiệm vụ mà Agent tồn tại, chúng ta hãy tìm hiểu cơ chế vận hành cốt lõi của nó. Agent không hoàn thành nhiệm vụ trong một lần, mà tương tác với môi trường qua một vòng lặp liên tục, cơ chế cốt lõi này được gọi là **vòng lặp Agent (Agent Loop)**. Như trong Hình 1.5, vòng lặp này mô tả quá trình tương tác động giữa Agent và môi trường, tạo nên nền tảng cho hành vi tự chủ của nó.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-5.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 1.5 Vòng lặp cơ bản của tương tác giữa Agent và môi trường</p>
</div>

Vòng lặp này chủ yếu gồm các giai đoạn liên kết với nhau sau đây:

1. **Cảm nhận (Perception)**: Đây là điểm khởi đầu của vòng lặp. Agent nhận thông tin đầu vào từ môi trường thông qua cảm biến của mình (ví dụ cổng lắng nghe của API, giao diện nhập liệu của người dùng). Thông tin này, tức **quan sát (Observation)**, có thể là chỉ thị ban đầu của người dùng, cũng có thể là phản hồi về thay đổi trạng thái môi trường do hành động ở bước trước gây ra.
2. **Suy nghĩ (Thought)**: Sau khi nhận thông tin quan sát, Agent bước vào giai đoạn ra quyết định cốt lõi. Với Agent LLM, đây thường là quá trình suy luận nội tại do mô hình ngôn ngữ lớn dẫn dắt. Như trong hình, giai đoạn “suy nghĩ” có thể chia nhỏ thành hai khâu then chốt:
   - **Lập kế hoạch (Planning)**: Dựa trên quan sát hiện tại và bộ nhớ nội tại, Agent cập nhật hiểu biết về nhiệm vụ và môi trường, đồng thời xây dựng hoặc điều chỉnh một kế hoạch hành động. Việc này có thể bao gồm phân rã mục tiêu phức tạp thành một chuỗi nhiệm vụ con cụ thể hơn.
   - **Lựa chọn công cụ (Tool Selection)**: Theo kế hoạch hiện tại, Agent chọn từ thư viện công cụ khả dụng công cụ phù hợp nhất để thực hiện bước tiếp theo, và xác định các tham số cụ thể cần thiết để gọi công cụ đó.
3. **Hành động (Action)**: Sau khi hoàn tất quyết định, Agent thực hiện hành động cụ thể thông qua cơ cấu chấp hành. Điều này thường thể hiện ở việc gọi một công cụ đã chọn (như trình thông dịch mã, API công cụ tìm kiếm), từ đó gây ảnh hưởng lên môi trường với ý định thay đổi trạng thái của nó.

Hành động không phải là điểm kết thúc của vòng lặp. Hành động của Agent gây ra **thay đổi trạng thái (State Change)** của **môi trường (Environment)**, môi trường ngay sau đó sinh ra một **quan sát (Observation)** mới như phản hồi kết quả. Quan sát mới này lại được hệ thống cảm nhận của Agent bắt lấy trong vòng lặp tiếp theo, tạo thành một vòng lặp kín “cảm nhận - suy nghĩ - hành động - quan sát” liên tục. Chính nhờ lặp đi lặp lại vòng lặp này, Agent dần đẩy nhiệm vụ tiến lên, tiến hóa từ trạng thái ban đầu tới trạng thái mục tiêu.

### 1.2.3 Cảm nhận và hành động của Agent

Trong thực tiễn kỹ thuật, để LLM có thể dẫn dắt hiệu quả vòng lặp này, chúng ta cần một **giao thức tương tác (Interaction Protocol)** rõ ràng để chuẩn hóa việc trao đổi thông tin giữa nó và môi trường.

Trong nhiều framework Agent hiện đại, giao thức này được thể hiện ở việc định nghĩa có cấu trúc cho mỗi đầu ra của Agent. Đầu ra của Agent không còn là một câu trả lời ngôn ngữ tự nhiên duy nhất, mà là một đoạn văn bản tuân theo định dạng cụ thể, trong đó thể hiện rõ quá trình suy luận nội tại và quyết định cuối cùng của nó.

Cấu trúc này thường gồm hai phần cốt lõi:

- **Thought (Suy nghĩ)**: Đây là “ảnh chụp nhanh” quyết định nội tại của Agent. Nó diễn đạt bằng ngôn ngữ tự nhiên cách Agent phân tích tình huống hiện tại, xem lại kết quả quan sát ở bước trước, tự phản tư và phân rã vấn đề, cuối cùng lập kế hoạch hành động cụ thể tiếp theo.
- **Action (Hành động)**: Đây là thao tác cụ thể mà Agent quyết định áp lên môi trường sau khi suy nghĩ, thường được biểu diễn dưới dạng lời gọi hàm.

Ví dụ, một Agent đang lập kế hoạch du lịch có thể sinh ra đầu ra có định dạng như sau:

```Bash
Thought: Người dùng muốn biết thời tiết ở Bắc Kinh. Tôi cần gọi công cụ tra cứu thời tiết.
Action: get_weather("Bắc Kinh")
```

Trường `Action` ở đây tạo thành chỉ thị gửi tới thế giới bên ngoài. Một **bộ phân tích (Parser)** bên ngoài sẽ bắt lấy chỉ thị này và gọi hàm `get_weather` tương ứng.

Sau khi hành động được thực thi, môi trường trả về một kết quả. Ví dụ, hàm `get_weather` có thể trả về một đối tượng JSON chứa dữ liệu thời tiết chi tiết. Tuy nhiên, dữ liệu thô mà máy có thể đọc (như JSON) thường chứa thông tin dư thừa mà LLM không cần quan tâm, và định dạng không phù hợp với thói quen xử lý ngôn ngữ tự nhiên của nó.

Vì vậy, một trách nhiệm quan trọng của hệ thống cảm nhận là đóng vai trò cảm biến: xử lý và đóng gói đầu ra thô này thành một đoạn văn bản ngôn ngữ tự nhiên ngắn gọn, rõ ràng, tức quan sát.

```Bash
Observation: Thời tiết hiện tại ở Bắc Kinh là nắng, nhiệt độ 25 độ C, gió nhẹ.
```

Đoạn `Observation` này sẽ được phản hồi lại cho Agent, làm thông tin đầu vào chính cho vòng lặp tiếp theo, để nó thực hiện một lượt `Thought` và `Action` mới.

Tóm lại, thông qua vòng lặp chặt chẽ gồm Thought, Action, Observation này, Agent LLM có thể kết hợp hiệu quả năng lực suy luận ngôn ngữ nội tại với thông tin thực tế và năng lực thao tác công cụ của môi trường bên ngoài.

## 1.3 Thực hành: hiện thực Agent đầu tiên trong 5 phút

Ở các mục trước, chúng ta đã học về môi trường nhiệm vụ, cơ chế vận hành cốt lõi và mô hình tương tác `Thought-Action-Observation` của Agent. Tri thức lý thuyết dĩ nhiên quan trọng, nhưng cách học tốt nhất là tự tay thực hành. Trong mục này, chúng tôi sẽ hướng dẫn bạn dùng vài dòng mã Python đơn giản để xây dựng từ con số 0 một trợ lý du lịch thông minh có thể hoạt động. Quá trình này sẽ tuân theo vòng lặp lý thuyết mà chúng ta vừa học, giúp bạn cảm nhận trực quan cách một Agent “suy nghĩ” và tương tác với các “công cụ” bên ngoài. Hãy bắt đầu thôi!

Trong ca này, mục tiêu của chúng ta là xây dựng một trợ lý du lịch thông minh có thể xử lý nhiệm vụ theo từng bước. Nhiệm vụ người dùng cần giải quyết được định nghĩa là: “Xin chào, hãy giúp tôi tra cứu thời tiết Bắc Kinh hôm nay, sau đó dựa trên thời tiết gợi ý một điểm du lịch phù hợp.” Để hoàn thành nhiệm vụ này, Agent phải thể hiện năng lực lập kế hoạch logic rõ ràng. Nó cần gọi công cụ tra cứu thời tiết trước, và dùng kết quả quan sát thu được làm căn cứ cho bước tiếp theo. Trong vòng lặp kế tiếp, nó gọi công cụ gợi ý điểm du lịch, từ đó đưa ra gợi ý cuối cùng.

### 1.3.1 Chuẩn bị

Để truy cập API mạng từ chương trình Python, chúng ta cần một thư viện HTTP. `requests` là lựa chọn phổ biến nhất và dễ dùng nhất trong cộng đồng Python. `tavily-python` là một client API tìm kiếm AI mạnh mẽ, dùng để lấy kết quả tìm kiếm web theo thời gian thực, có thể đăng ký trên [trang chủ](https://www.tavily.com/) để lấy API. `openai` là SDK Python chính thức do OpenAI cung cấp, dùng để gọi các dịch vụ mô hình ngôn ngữ lớn như GPT. Trước tiên hãy cài đặt chúng bằng lệnh sau:

```bash
pip install requests tavily-python openai
```

(1) Mẫu chỉ thị

Chìa khóa để dẫn dắt một LLM thực sự nằm ở **kỹ thuật prompt (Prompt Engineering)**. Chúng ta cần thiết kế một “mẫu chỉ thị”, nói cho LLM biết nó nên đóng vai gì, có những công cụ nào, và định dạng suy nghĩ cùng hành động của nó ra sao. Đây là “bản hướng dẫn sử dụng” của Agent, sẽ được truyền cho LLM dưới dạng `system_prompt`.

```
AGENT_SYSTEM_PROMPT = """
Bạn là một trợ lý du lịch thông minh. Nhiệm vụ của bạn là phân tích yêu cầu của người dùng và dùng các công cụ khả dụng để giải quyết vấn đề từng bước một.

# Công cụ khả dụng:
- `get_weather(city: str)`: Tra cứu thời tiết thời gian thực của thành phố được chỉ định.
- `get_attraction(city: str, weather: str)`: Tìm kiếm và gợi ý điểm du lịch dựa trên thành phố và thời tiết.

# Yêu cầu định dạng đầu ra:
Mỗi lần trả lời phải tuân thủ nghiêm ngặt định dạng sau, gồm một cặp Thought và Action:

Thought: [Quá trình suy nghĩ và kế hoạch bước tiếp theo của bạn]
Action: [Hành động cụ thể bạn muốn thực thi]

Định dạng của Action phải là một trong các dạng sau:
1. Gọi công cụ: function_name(arg_name="arg_value")
2. Kết thúc nhiệm vụ: Finish[câu trả lời cuối cùng]

# Lưu ý quan trọng:
- Mỗi lần chỉ xuất ra một cặp Thought-Action
- Action phải nằm trên cùng một dòng, không xuống dòng
- Khi đã thu thập đủ thông tin để trả lời câu hỏi của người dùng, phải dùng định dạng Action: Finish[câu trả lời cuối cùng] để kết thúc

Hãy bắt đầu!
"""
```

(2) Công cụ 1: tra cứu thời tiết thực tế

Chúng ta sẽ dùng dịch vụ tra cứu thời tiết miễn phí `wttr.in`, dịch vụ này có thể trả về dữ liệu thời tiết của thành phố được chỉ định ở định dạng JSON. Dưới đây là mã hiện thực công cụ này:

```python
import requests

def get_weather(city: str) -> str:
    """
    Tra cứu thông tin thời tiết thực tế bằng cách gọi API wttr.in.
    """
    # Điểm cuối API, chúng ta yêu cầu dữ liệu ở định dạng JSON
    url = f"https://wttr.in/{city}?format=j1"

    try:
        # Gửi yêu cầu mạng
        response = requests.get(url)
        # Kiểm tra mã trạng thái phản hồi có phải 200 (thành công) không
        response.raise_for_status()
        # Phân tích dữ liệu JSON trả về
        data = response.json()

        # Trích xuất điều kiện thời tiết hiện tại
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        # Định dạng thành ngôn ngữ tự nhiên để trả về
        return f"Thời tiết hiện tại ở {city}:{weather_desc}, nhiệt độ {temp_c} độ C"

    except requests.exceptions.RequestException as e:
        # Xử lý lỗi mạng
        return f"Lỗi:truy vấn thời tiết gặp sự cố mạng - {e}"
    except (KeyError, IndexError) as e:
        # Xử lý lỗi phân tích dữ liệu
        return f"Lỗi:phân tích dữ liệu thời tiết thất bại, có thể tên thành phố không hợp lệ - {e}"
```

(3) Công cụ 2: tìm kiếm và gợi ý điểm du lịch

Chúng ta sẽ định nghĩa một công cụ mới `get_attraction`, công cụ này sẽ dựa trên thành phố và điều kiện thời tiết để tìm kiếm điểm du lịch phù hợp trên Internet:

```python
import os
from tavily import TavilyClient

def get_attraction(city: str, weather: str) -> str:
    """
    Dựa trên thành phố và thời tiết, dùng Tavily Search API để tìm kiếm và trả về gợi ý điểm du lịch đã được tối ưu.
    """
    # 1. Đọc khóa API từ biến môi trường
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Lỗi:chưa cấu hình biến môi trường TAVILY_API_KEY."

    # 2. Khởi tạo client Tavily
    tavily = TavilyClient(api_key=api_key)

    # 3. Xây dựng một truy vấn chính xác
    query = f"gợi ý điểm du lịch đáng đi nhất và lý do tại '{city}' khi thời tiết '{weather}'"

    try:
        # 4. Gọi API, include_answer=True sẽ trả về một câu trả lời tổng hợp
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        # 5. Kết quả Tavily trả về đã rất gọn gàng, có thể dùng trực tiếp
        # response['answer'] là một câu trả lời tổng kết dựa trên tất cả kết quả tìm kiếm
        if response.get("answer"):
            return response["answer"]

        # Nếu không có câu trả lời tổng hợp, định dạng lại kết quả thô
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
             return "Xin lỗi, không tìm thấy gợi ý điểm du lịch liên quan."

        return "Dựa trên kết quả tìm kiếm, chúng tôi tìm thấy thông tin sau:\n" + "\n".join(formatted_results)

    except Exception as e:
        return f"Lỗi:gặp sự cố khi thực thi tìm kiếm Tavily - {e}"
```

Cuối cùng, chúng ta đặt tất cả hàm công cụ vào một từ điển để vòng lặp chính gọi tới:

```python
# Đặt tất cả hàm công cụ vào một từ điển để tiện gọi về sau
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}
```



### 1.3.2 Kết nối với mô hình ngôn ngữ lớn

Hiện nay, nhiều nhà cung cấp dịch vụ LLM (bao gồm OpenAI, Azure, và nhiều framework phục vụ mô hình mã nguồn mở như Ollama, vLLM, v.v.) đều tuân theo quy chuẩn giao diện tương tự OpenAI API. Sự chuẩn hóa này mang lại sự tiện lợi to lớn cho nhà phát triển. Năng lực tự chủ ra quyết định của Agent bắt nguồn từ LLM. Chúng ta sẽ hiện thực một client tổng quát `OpenAICompatibleClient`, có thể kết nối tới bất kỳ dịch vụ LLM nào tương thích với quy chuẩn giao diện OpenAI.

```python
from openai import OpenAI

class OpenAICompatibleClient:
    """
    Một client dùng để gọi bất kỳ dịch vụ LLM nào tương thích với giao diện OpenAI.
    """
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """Gọi API LLM để sinh phản hồi."""
        print("Đang gọi mô hình ngôn ngữ lớn...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            answer = response.choices[0].message.content
            print("Mô hình ngôn ngữ lớn phản hồi thành công.")
            return answer
        except Exception as e:
            print(f"Xảy ra lỗi khi gọi API LLM: {e}")
            return "Lỗi:gặp lỗi khi gọi dịch vụ mô hình ngôn ngữ."
```

Để khởi tạo lớp này, bạn cần cung cấp ba thông tin: `API_KEY`, `BASE_URL` và `MODEL_ID`, giá trị cụ thể phụ thuộc vào nhà cung cấp dịch vụ bạn dùng (như OpenAI chính thức, Azure, hoặc mô hình cục bộ như Ollama), nếu tạm thời chưa có kênh để lấy, có thể tham khảo [Cấu hình môi trường](https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra07-环境配置.md).

### 1.3.3 Thực thi vòng lặp hành động

Vòng lặp chính dưới đây sẽ tích hợp tất cả thành phần, và dẫn dắt LLM ra quyết định thông qua Prompt đã được định dạng.

```python
import re

# --- 1. Cấu hình client LLM ---
# Hãy thay thế bằng thông tin xác thực và địa chỉ tương ứng với dịch vụ bạn dùng
API_KEY = "YOUR_API_KEY"
BASE_URL = "YOUR_BASE_URL"
MODEL_ID = "YOUR_MODEL_ID"
TAVILY_API_KEY="YOUR_Tavily_KEY"
os.environ['TAVILY_API_KEY'] = "YOUR_TAVILY_API_KEY"

llm = OpenAICompatibleClient(
    model=MODEL_ID,
    api_key=API_KEY,
    base_url=BASE_URL
)

# --- 2. Khởi tạo ---
user_prompt = "Xin chào, hãy giúp tôi tra cứu thời tiết Bắc Kinh hôm nay, sau đó dựa trên thời tiết gợi ý một điểm du lịch phù hợp."
prompt_history = [f"Yêu cầu của người dùng: {user_prompt}"]

print(f"Người dùng nhập: {user_prompt}\n" + "="*40)

# --- 3. Chạy vòng lặp chính ---
for i in range(5): # Đặt số lần lặp tối đa
    print(f"--- Vòng lặp {i+1} ---\n")

    # 3.1. Xây dựng Prompt
    full_prompt = "\n".join(prompt_history)

    # 3.2. Gọi LLM để suy nghĩ
    llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
    # Mô hình có thể xuất ra cặp Thought-Action dư thừa, cần cắt bớt
    match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("Đã cắt bớt cặp Thought-Action dư thừa")
    print(f"Mô hình xuất ra:\n{llm_output}\n")
    prompt_history.append(llm_output)

    # 3.3. Phân tích và thực thi hành động
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        observation = "Lỗi: không phân tích được trường Action. Hãy đảm bảo phản hồi của bạn tuân thủ nghiêm ngặt định dạng 'Thought: ... Action: ...'."
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "="*40)
        prompt_history.append(observation_str)
        continue
    action_str = action_match.group(1).strip()

    if action_str.startswith("Finish"):
        final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
        print(f"Nhiệm vụ hoàn thành, câu trả lời cuối cùng: {final_answer}")
        break

    tool_name = re.search(r"(\w+)\(", action_str).group(1)
    args_str = re.search(r"\((.*)\)", action_str).group(1)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"Lỗi:công cụ '{tool_name}' chưa được định nghĩa"

    # 3.4. Ghi lại kết quả quan sát
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "="*40)
    prompt_history.append(observation_str)
```

Qua các bước trên, chúng ta đã xây dựng một Agent hoàn chỉnh, được dẫn dắt bởi LLM thực sự. Cốt lõi của nó nằm ở sự kết hợp giữa “công cụ” và “kỹ thuật prompt”, đây chính là tinh túy thiết kế của các framework Agent chủ lưu hiện nay (như LangChain, LlamaIndex, v.v.).

### 1.3.4 Phân tích ca chạy thử

Đầu ra dưới đây thể hiện đầy đủ một quy trình thực thi Agent thành công. Qua phân tích ba vòng lặp này, chúng ta có thể thấy rõ năng lực cốt lõi của Agent trong việc giải quyết vấn đề.

```bash
Người dùng nhập: Xin chào, hãy giúp tôi tra cứu thời tiết Bắc Kinh hôm nay, sau đó dựa trên thời tiết gợi ý một điểm du lịch phù hợp.
========================================
--- Vòng lặp 1 ---

Đang gọi mô hình ngôn ngữ lớn...
Mô hình ngôn ngữ lớn phản hồi thành công.
Mô hình xuất ra:
Thought: Trước tiên cần lấy thông tin thời tiết Bắc Kinh hôm nay, sau đó dựa trên tình hình thời tiết để gợi ý điểm du lịch.
Action: get_weather(city="Bắc Kinh")

Observation: Thời tiết hiện tại ở Bắc Kinh:Sunny, nhiệt độ 26 độ C
========================================
--- Vòng lặp 2 ---

Đang gọi mô hình ngôn ngữ lớn...
Mô hình ngôn ngữ lớn phản hồi thành công.
Mô hình xuất ra:
Thought: Hiện đã biết thời tiết Bắc Kinh hôm nay là nắng và nhiệt độ vừa phải, tiếp theo có thể dựa trên thông tin này để gợi ý một điểm du lịch phù hợp.
Action: get_attraction(city="Bắc Kinh", weather="Sunny")

Observation: Điểm du lịch đáng đi nhất ở Bắc Kinh vào ngày nắng là Di Hòa Viên, nhờ cảnh hồ đẹp và kiến trúc cổ. Một gợi ý khác là Vạn Lý Trường Thành, nhờ phong cảnh hùng vĩ và ý nghĩa lịch sử.
========================================
--- Vòng lặp 3 ---

Đang gọi mô hình ngôn ngữ lớn...
Mô hình ngôn ngữ lớn phản hồi thành công.
Mô hình xuất ra:
Thought: Đã có được hai gợi ý điểm du lịch phù hợp cho ngày nắng, giờ có thể dựa trên thông tin này để đưa ra câu trả lời hài lòng cho người dùng.
Action: Finish[Thời tiết Bắc Kinh hôm nay là nắng, nhiệt độ 26 độ C, rất phù hợp để ra ngoài vui chơi. Tôi gợi ý bạn đến Di Hòa Viên để thưởng ngoạn cảnh hồ đẹp và kiến trúc cổ, hoặc đến Vạn Lý Trường Thành để trải nghiệm phong cảnh hùng vĩ và ý nghĩa lịch sử sâu sắc. Chúc bạn có một chuyến đi vui vẻ!]

Nhiệm vụ hoàn thành, câu trả lời cuối cùng: Thời tiết Bắc Kinh hôm nay là nắng, nhiệt độ 26 độ C, rất phù hợp để ra ngoài vui chơi. Tôi gợi ý bạn đến Di Hòa Viên để thưởng ngoạn cảnh hồ đẹp và kiến trúc cổ, hoặc đến Vạn Lý Trường Thành để trải nghiệm phong cảnh hùng vĩ và ý nghĩa lịch sử sâu sắc. Chúc bạn có một chuyến đi vui vẻ!
```

Ca trợ lý du lịch đơn giản này tập trung minh họa bốn năng lực cơ bản mà một Agent dựa trên mô hình `Thought-Action-Observation` sở hữu: phân rã nhiệm vụ, gọi công cụ, hiểu ngữ cảnh và tổng hợp kết quả. Chính nhờ sự lặp lại không ngừng của vòng lặp này, Agent mới có thể chuyển một ý định mơ hồ của người dùng thành một chuỗi bước cụ thể, có thể thực thi, và cuối cùng đạt được mục tiêu.

## 1.4 Các mô hình cộng tác của ứng dụng Agent

Ở mục trước, qua việc tự tay xây dựng một Agent, chúng ta đã hiểu sâu vòng lặp vận hành bên trong của nó. Tuy nhiên, trong bối cảnh ứng dụng rộng lớn hơn, vai trò của chúng ta đang ngày càng chuyển thành người dùng và người cộng tác. Dựa trên vai trò của Agent trong nhiệm vụ và mức độ tự chủ, mô hình cộng tác của nó chủ yếu chia thành hai loại: một là công cụ hiệu quả, hòa sâu vào quy trình làm việc của chúng ta; hai là người cộng tác tự chủ, phối hợp với các Agent khác để hoàn thành mục tiêu phức tạp.

### 1.4.1 Agent với vai trò công cụ của nhà phát triển

Ở mô hình này, Agent được tích hợp sâu vào quy trình làm việc của nhà phát triển, như một công cụ hỗ trợ mạnh mẽ. Nó tăng cường chứ không thay thế vai trò của nhà phát triển, bằng cách tự động hóa các nhiệm vụ tẻ nhạt, lặp đi lặp lại, giúp nhà phát triển tập trung hơn vào công việc sáng tạo cốt lõi. Cách cộng tác người - máy này nâng cao đáng kể hiệu quả và chất lượng phát triển phần mềm.

Hiện nay, trên thị trường đã xuất hiện nhiều công cụ hỗ trợ lập trình AI xuất sắc, tuy đều có thể nâng cao hiệu quả phát triển nhưng mỗi công cụ có con đường hiện thực và trọng tâm chức năng khác nhau:

- **GitHubCopilot**: Là một trong những sản phẩm có ảnh hưởng nhất trong lĩnh vực này, Copilot do GitHub và OpenAI cùng phát triển. Nó được tích hợp sâu vào các trình soạn thảo chủ lưu như Visual Studio Code, nổi tiếng nhờ năng lực tự động hoàn thiện mã mạnh mẽ. Khi nhà phát triển viết mã, Copilot có thể gợi ý theo thời gian thực cho cả dòng, thậm chí cả khối hàm. Những năm gần đây, nó còn mở rộng năng lực lập trình hội thoại qua Copilot Chat, cho phép nhà phát triển giải quyết vấn đề lập trình ngay trong trình soạn thảo bằng trò chuyện.
- **Claude Code**: Claude Code là trợ lý lập trình AI do Anthropic phát triển, nhằm giúp nhà phát triển hoàn thành hiệu quả các nhiệm vụ viết mã trong terminal thông qua chỉ thị ngôn ngữ tự nhiên. Nó có thể hiểu cấu trúc toàn bộ cơ sở mã, thực thi các thao tác như chỉnh sửa mã, kiểm thử và gỡ lỗi, hỗ trợ toàn bộ quy trình từ mô tả chức năng đến hiện thực mã. Claude Code còn cung cấp chế độ không tương tác (headless), phù hợp cho CI, pre-commit hooks, script build và các kịch bản tự động hóa khác, mang lại cho nhà phát triển trải nghiệm lập trình dòng lệnh mạnh mẽ.
- **Trae**: Là một công cụ lập trình AI mới nổi, Trae tập trung cung cấp dịch vụ sinh và tối ưu mã thông minh cho nhà phát triển. Nó phân tích các mẫu mã bằng công nghệ học sâu, có thể đưa ra gợi ý mã chính xác và phương án tái cấu trúc tự động cho nhà phát triển. Đặc sắc của Trae nằm ở thiết kế nhẹ và khả năng phản hồi nhanh, đặc biệt phù hợp với các kịch bản cần lặp lại thường xuyên và phát triển nguyên mẫu nhanh.
- **Cursor**: Khác với các công cụ trên chủ yếu tồn tại dưới dạng plugin hoặc tính năng tích hợp, Cursor chọn một con đường mang tính tích hợp hơn: bản thân nó là một trình soạn thảo mã AI-native. Nó không thêm chức năng AI vào trình soạn thảo hiện có, mà ngay từ khi thiết kế đã coi tương tác AI là cốt lõi. Ngoài năng lực sinh mã và trò chuyện hàng đầu, nó còn nhấn mạnh việc để AI hiểu ngữ cảnh của toàn bộ cơ sở mã, từ đó thực hiện hỏi đáp, tái cấu trúc và gỡ lỗi ở mức sâu hơn.

Dĩ nhiên còn nhiều công cụ xuất sắc khác chưa được liệt kê, nhưng chúng cùng chỉ về một xu hướng rõ ràng: AI đang hòa sâu vào toàn bộ vòng đời phát triển phần mềm, thông qua việc xây dựng quy trình cộng tác người - máy hiệu quả, đang định hình lại sâu sắc biên giới hiệu quả và mô hình phát triển của kỹ nghệ phần mềm.

### 1.4.2 Agent với vai trò người cộng tác tự chủ

Khác với vai trò công cụ hỗ trợ con người, mô hình tương tác thứ hai nâng mức độ tự động hóa của Agent lên một tầng hoàn toàn mới: người cộng tác tự chủ. Ở mô hình này, chúng ta không còn hướng dẫn AI từng bước một, mà giao phó một mục tiêu cấp cao cho nó. Agent sẽ như một thành viên thực sự của dự án, độc lập lập kế hoạch, suy luận, thực thi và phản tư cho đến khi cuối cùng bàn giao kết quả. Sự chuyển dịch từ trợ lý sang người cộng tác này đưa Agent LLM vào sâu hơn trong tầm nhìn của công chúng. Nó đánh dấu quan hệ giữa chúng ta và AI đã tiến hóa từ “ra lệnh - thực thi” sang “mục tiêu - ủy thác”. Agent không còn là công cụ thụ động, mà là người theo đuổi mục tiêu chủ động.

Hiện nay, các hướng tiếp cận để hiện thực sự cộng tác tự chủ này đang nở rộ, xuất hiện rất nhiều framework và sản phẩm xuất sắc, từ BabyAGI, AutoGPT thời kỳ đầu, đến những framework trưởng thành hơn hiện nay như CrewAI, AutoGen, MetaGPT, LangGraph, cùng nhau thúc đẩy lĩnh vực này phát triển nhanh chóng. Tuy cách hiện thực cụ thể khác nhau rất nhiều, mô hình kiến trúc của chúng có thể khái quát thành vài hướng chủ lưu:

1. **Vòng lặp tự chủ của một Agent đơn**: Đây là mô hình điển hình thời kỳ đầu, như mô hình mà **AgentGPT** đại diện. Cốt lõi của nó là một Agent tổng quát không ngừng tự nhắc và lặp qua vòng lặp kín “suy nghĩ - lập kế hoạch - thực thi - phản tư” để hoàn thành một mục tiêu cấp cao mở.
2. **Cộng tác đa Agent**: Đây là hướng khám phá chủ lưu nhất hiện nay, nhằm giải quyết vấn đề phức tạp bằng cách mô phỏng mô hình cộng tác của đội ngũ con người. Nó có thể chia nhỏ thành các mô hình khác nhau: **Đối thoại nhập vai**: như framework **CAMEL**, đặt vai trò và giao thức giao tiếp rõ ràng cho hai Agent (ví dụ “lập trình viên” và “quản lý sản phẩm”), để chúng phối hợp hoàn thành nhiệm vụ trong một cuộc đối thoại có cấu trúc. **Quy trình làm việc có tổ chức**: như **MetaGPT** và **CrewAI**, chúng mô phỏng một “đội ngũ ảo” có phân công rõ ràng (như một công ty phần mềm hay nhóm tư vấn). Mỗi Agent có trách nhiệm và quy trình làm việc được đặt trước (SOP), phối hợp theo cách phân tầng hoặc tuần tự, tạo ra những kết quả phức tạp chất lượng cao (như một cơ sở mã hoàn chỉnh hay báo cáo nghiên cứu). **AutoGen** và **AgentScope** thì cung cấp mô hình đối thoại linh hoạt hơn, cho phép nhà phát triển tự định nghĩa mạng tương tác phức tạp giữa các Agent.
3. **Kiến trúc luồng điều khiển nâng cao**: Các framework như **LangGraph** tập trung hơn vào việc cung cấp nền tảng kỹ thuật tầng thấp mạnh mẽ hơn cho Agent. Nó mô hình hóa quá trình thực thi của Agent thành đồ thị trạng thái (State Graph), từ đó có thể hiện thực linh hoạt và đáng tin cậy hơn các quy trình phức tạp như vòng lặp, rẽ nhánh, quay lui và can thiệp của con người.

Những mô hình kiến trúc khác nhau này cùng thúc đẩy Agent tự chủ từ ý tưởng lý thuyết tiến tới ứng dụng thực tế rộng rãi hơn, giúp nó có khả năng đối phó với những nhiệm vụ thực tế ngày càng phức tạp. Trong các chương sau, chúng ta cũng sẽ cảm nhận sự khác biệt và ưu thế giữa các loại framework khác nhau.

### 1.4.3 Khác biệt giữa Workflow và Agent

Sau khi đã hiểu hai mô hình Agent với vai trò “công cụ” và “người cộng tác”, chúng ta cần thảo luận về khác biệt giữa Workflow và Agent. Dù cả hai đều nhằm tự động hóa nhiệm vụ, nhưng logic nền tảng, đặc trưng cốt lõi và kịch bản áp dụng của chúng hoàn toàn khác nhau.

Nói đơn giản, **Workflow là để AI thực thi chỉ thị theo từng bước, còn Agent là trao cho AI tự do để tự chủ đạt mục tiêu.**

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/1-figures/1757242319667-18.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 1.6 Khác biệt giữa Workflow và Agent</p>
</div>

Như trong Hình 1.6, workflow là một mô hình tự động hóa truyền thống, cốt lõi là **việc sắp xếp có cấu trúc, được định trước cho một chuỗi nhiệm vụ hoặc bước**. Về bản chất, nó là một lưu đồ chính xác, tĩnh, quy định thao tác nào được thực thi trong điều kiện nào và theo thứ tự nào. Một ca điển hình: quy trình phê duyệt hoàn ứng chi phí của một doanh nghiệp. Nhân viên nộp đơn hoàn ứng (kích hoạt) -> Nếu số tiền nhỏ hơn 500 tệ, trưởng phòng phê duyệt trực tiếp -> Nếu số tiền lớn hơn 500 tệ, trưởng phòng phê duyệt trước, rồi chuyển tới giám đốc tài chính phê duyệt -> Sau khi phê duyệt, thông báo cho phòng tài chính chuyển tiền. Mỗi bước và mỗi điều kiện phán đoán của toàn bộ quá trình đều được đặt trước chính xác.

Khác với workflow, Agent dựa trên mô hình ngôn ngữ lớn là một **hệ thống có tính tự chủ, hướng tới mục tiêu**. Nó không chỉ thực thi chỉ thị đặt trước, mà còn có thể ở một mức độ nhất định hiểu môi trường, suy luận, lập kế hoạch và linh hoạt hành động để đạt mục tiêu cuối cùng. LLM đóng vai “bộ não” trong đó. Một ví dụ điển hình chính là trợ lý du lịch thông minh mà chúng ta đã viết ở mục 1.3. Khi chúng ta đưa cho nó một chỉ thị mới, ví dụ: **“Xin chào, hãy giúp tôi tra cứu thời tiết Bắc Kinh hôm nay, sau đó dựa trên thời tiết gợi ý một điểm du lịch phù hợp.”** Quá trình xử lý của nó thể hiện đầy đủ tính tự chủ:

1. **Lập kế hoạch và gọi công cụ:** Agent trước hết phân rã nhiệm vụ thành hai bước: ① tra cứu thời tiết; ② gợi ý điểm du lịch dựa trên thời tiết. Ngay sau đó, nó tự chọn và gọi “API tra cứu thời tiết”, truyền “Bắc Kinh” làm tham số.
2. **Suy luận và ra quyết định:** Giả sử API trả về “nắng, gió nhẹ”. Bộ não LLM của Agent sẽ dựa trên thông tin này để suy luận: “Ngày nắng phù hợp cho hoạt động ngoài trời”. Tiếp đó, dựa trên phán đoán này, nó sàng lọc từ cơ sở tri thức hoặc qua công cụ tìm kiếm những điểm du lịch ngoài trời ở Bắc Kinh, như Tử Cấm Thành, Di Hòa Viên, Công viên Thiên Đàn, v.v.
3. **Sinh kết quả:** Cuối cùng, Agent tổng hợp thông tin và đưa ra câu trả lời hoàn chỉnh, thân thiện với con người: “Hôm nay thời tiết Bắc Kinh nắng, gió nhẹ, rất phù hợp để vui chơi ngoài trời. Gợi ý bạn đến 【Di Hòa Viên】, nơi bạn có thể chèo thuyền trên hồ Côn Minh và thưởng ngoạn cảnh vườn hoàng gia tuyệt đẹp.”

Trong quá trình này, không có bất kỳ quy tắc cứng nào kiểu `nếu thời tiết = nắng thì gợi ý Di Hòa Viên`. Nếu thời tiết là “mưa”, Agent sẽ tự suy luận và gợi ý những địa điểm trong nhà như Bảo tàng Quốc gia, Bảo tàng Thủ đô. **Năng lực suy luận và ra quyết định linh hoạt dựa trên thông tin thời gian thực này chính là giá trị cốt lõi của Agent.**



## 1.5 Tóm tắt chương

Trong chương này, chúng ta đã cùng bước vào hành trình làm quen và khám phá Agent. Hành trình của chúng ta bắt đầu từ những câu hỏi cơ bản nhất:

- **Agent do mô hình ngôn ngữ lớn dẫn dắt là gì?** Trước tiên chúng ta đã làm rõ định nghĩa của nó, hiểu rằng Agent hiện đại là một thực thể sở hữu năng lực. Nó không còn chỉ là script thực thi chương trình đặt trước, mà là người ra quyết định có thể tự suy luận và sử dụng công cụ.
- **Agent hoạt động như thế nào?** Chúng ta đã đi sâu vào cơ chế vận hành tương tác giữa Agent và môi trường. Chúng ta hiểu rằng vòng lặp kín liên tục này là nền tảng để Agent xử lý thông tin, ra quyết định, gây ảnh hưởng lên môi trường và điều chỉnh hành vi của mình theo phản hồi.
- **Xây dựng Agent như thế nào?** Đây là phần thực hành cốt lõi của chương. Lấy “trợ lý du lịch thông minh” làm ví dụ, chúng ta đã tự tay xây dựng một Agent hoàn chỉnh, được dẫn dắt bởi LLM thực sự.
- **Agent có những mô hình ứng dụng chủ lưu nào?** Cuối cùng, chúng ta hướng tầm nhìn ra lĩnh vực ứng dụng rộng lớn hơn. Chúng ta đã thảo luận hai mô hình tương tác chủ lưu của Agent: một là “công cụ của nhà phát triển” đại diện bởi GitHub Copilot và Cursor, giúp tăng cường quy trình làm việc của con người; hai là “người cộng tác tự chủ” đại diện bởi các framework như CrewAI, MetaGPT và AgentScope, có thể độc lập hoàn thành mục tiêu cấp cao. Đồng thời chúng ta cũng giải thích khác biệt giữa Workflow và Agent.

Qua việc học chương này, chúng ta đã xây dựng một khung nhận thức nền tảng về Agent. Vậy nó đã tiến hóa từng bước từ ý tưởng ban đầu đến ngày nay như thế nào? Trong chương tiếp theo, chúng ta sẽ khám phá lịch sử phát triển của Agent, một hành trình truy nguyên nguồn cội sắp bắt đầu!



## Bài tập

> **Gợi ý**: Một số bài tập dưới đây không có đáp án chuẩn, trọng tâm là bồi dưỡng năng lực tư duy phê phán sâu sắc và thực hành của người học đối với hệ thống Agent.

1. Hãy phân tích xem **chủ thể** trong bốn `case` dưới đây có phải là Agent hay không, nếu có thì thuộc loại Agent nào (có thể phân tích từ nhiều chiều phân loại), và giải thích lý do:

   `case A`: **Một siêu máy tính tuân theo kiến trúc von Neumann**, với năng lực tính toán đỉnh cao lên tới 2EFlop mỗi giây

   `case B`: **Hệ thống tự lái của Tesla** đang chạy trên cao tốc, đột nhiên phát hiện có chướng ngại vật phía trước, cần đưa ra quyết định phanh hoặc chuyển làn trong vài mili giây

   `case C`: **AlphaGo** khi đấu với kỳ thủ con người, cần đánh giá tình thế hiện tại và lập kế hoạch chiến lược tối ưu cho vài chục nước tiếp theo

   `case D`: **Chatbot chăm sóc khách hàng do ChatGPT đóng vai** khi xử lý khiếu nại của người dùng, cần tra cứu thông tin đơn hàng, phân tích nguyên nhân vấn đề, đưa ra giải pháp và trấn an cảm xúc người dùng

2. Giả sử bạn cần thiết kế môi trường nhiệm vụ cho một “huấn luyện viên thể hình thông minh”. Agent này có thể:
   - Giám sát nhịp tim, cường độ vận động và các dữ liệu sinh lý khác của người dùng qua thiết bị đeo
   - Điều chỉnh linh hoạt kế hoạch tập luyện theo mục tiêu thể hình của người dùng (giảm mỡ/tăng cơ/nâng cao sức bền)
   - Cung cấp hướng dẫn bằng giọng nói theo thời gian thực và sửa động tác trong khi người dùng tập
   - Đánh giá hiệu quả tập luyện và đưa ra gợi ý dinh dưỡng

   Hãy dùng mô hình PEAS để mô tả đầy đủ môi trường nhiệm vụ của Agent này, và phân tích môi trường đó có những đặc tính nào (như quan sát một phần, tính ngẫu nhiên, tính động, v.v.).

3. Một công ty thương mại điện tử đang cân nhắc hai phương án để xử lý đơn yêu cầu hoàn tiền sau bán hàng:

   Phương án A (`Workflow`): thiết kế một quy trình cố định, ví dụ:

   A.1 Với hàng hóa thông thường và trong vòng 7 ngày, số tiền `< 100RMB` tự động được duyệt; `100-500RMB` do nhân viên chăm sóc khách hàng xét duyệt; `>500RMB` cần quản lý phê duyệt; còn hàng hóa đặc biệt (như hàng đặt làm) thì nhất loạt từ chối hoàn tiền

   A.2 Với hàng hóa quá 7 ngày, bất kể số tiền, chỉ có thể do nhân viên chăm sóc khách hàng xét duyệt hoặc quản lý phê duyệt;

   Phương án B (`Agent`): xây dựng một hệ thống Agent, để nó hiểu chính sách hoàn tiền, phân tích hành vi lịch sử của người dùng, đánh giá tình trạng hàng hóa và tự chủ quyết định có phê duyệt hoàn tiền hay không

   Hãy phân tích:
   - Ưu nhược điểm của từng phương án là gì?
   - Trong trường hợp nào `Workflow` phù hợp hơn? Trong trường hợp nào `Agent` có ưu thế hơn? Nếu bạn là người phụ trách công ty thương mại điện tử này, bạn nghiêng về phương án nào?
   - Liệu có một phương án C có thể kết hợp cả hai phương án, đạt hiệu quả phát huy ưu điểm và khắc phục nhược điểm?

4. Trên cơ sở trợ lý du lịch thông minh ở mục 1.3, hãy suy nghĩ cách thêm các chức năng sau (có thể chỉ mô tả ý tưởng thiết kế, cũng có thể thử hiện thực bằng mã):

   > **Gợi ý**: Hãy suy nghĩ cách sửa vòng lặp `Thought-Action-Observation` để hiện thực những chức năng này.

   - Thêm chức năng “ghi nhớ”, để Agent ghi nhớ sở thích của người dùng (như thích điểm du lịch văn hóa - lịch sử, phạm vi ngân sách, v.v.)
   - Khi vé vào điểm du lịch được gợi ý đã bán hết, Agent có thể tự động gợi ý phương án thay thế
   - Nếu người dùng liên tiếp từ chối 3 gợi ý, Agent có thể phản tư và điều chỉnh chiến lược gợi ý

5. Lý thuyết “Hệ thống 1” (trực giác nhanh) và “Hệ thống 2” (suy luận chậm) của Kahneman<sup>[2]</sup> mang lại một phép loại suy tốt cho AI thần kinh - biểu tượng. Trước tiên hãy hình dung một kịch bản ứng dụng thực tế cụ thể của Agent, sau đó giải thích trong kịch bản đó:

   > **Gợi ý**: Trợ lý chẩn đoán y tế, robot tư vấn pháp luật, hệ thống kiểm soát rủi ro tài chính, v.v. đều là những kịch bản ứng dụng phổ biến

   - Những nhiệm vụ nào nên do “Hệ thống 1” xử lý?
   - Những nhiệm vụ nào nên do “Hệ thống 2” xử lý?
   - Hai hệ thống này phối hợp với nhau như thế nào để đạt mục tiêu cuối cùng?

6. Dù hệ thống Agent do mô hình ngôn ngữ lớn dẫn dắt đã thể hiện năng lực mạnh mẽ, chúng vẫn còn nhiều hạn chế. Hãy phân tích các vấn đề sau:
   - Vì sao Agent hoặc hệ thống Agent đôi khi sinh ra “ảo giác” (tạo ra thông tin nghe có lý nhưng thực tế sai)?
   - Trong ca ở mục 1.3, chúng ta đặt số lần lặp tối đa là 5. Nếu không có giới hạn này, Agent có thể rơi vào vấn đề gì?
   - Làm thế nào để đánh giá mức độ “thông minh” của một Agent? Chỉ dùng chỉ số độ chính xác liệu có đủ?




## Tài liệu tham khảo

[1] RUSSELL S, NORVIG P. Artificial Intelligence: A Modern Approach[M]. 4th ed. London: Pearson, 2020.

[2] KAHNEMAN D. Thinking, Fast and Slow[M]. New York: Farrar, Straus and Giroux, 2011.

---

## 💬 Thảo luận và trao đổi

Gặp vấn đề trong quá trình học chương này? Muốn trao đổi kinh nghiệm với những người học khác?

**📝 Truy cập khu thảo luận GitHub Discussions:**
- [💬 Thảo luận và hỏi đáp bài tập](https://github.com/datawhalechina/Hello-Agents/discussions)
- Tại đây bạn có thể:
  - ✅ Đặt câu hỏi liên quan đến bài tập
  - ✅ Chia sẻ cách giải của bạn
  - ✅ Trao đổi kinh nghiệm với những người học khác
  - ✅ Nhận sự giúp đỡ và phản hồi từ cộng đồng

**💡 Gợi ý:** Mỗi trang cũng có khu bình luận ở cuối, bạn có thể thảo luận trực tiếp ngay trong trang!

---

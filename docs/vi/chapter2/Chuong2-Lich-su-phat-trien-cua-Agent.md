# Chương 2: Lịch sử phát triển của Agent

Để hiểu sâu vì sao Agent hiện đại lại có hình dạng như ngày nay, và nguồn gốc tư tưởng thiết kế cốt lõi của nó, chương này sẽ nhìn lại lịch sử: bắt đầu từ thời kỳ cổ điển của trí tuệ nhân tạo, tìm hiểu “trí tuệ” sớm nhất đã được định nghĩa như thế nào trong hệ thống quy tắc logic và biểu tượng; tiếp đó chứng kiến bước ngoặt lớn từ mô hình trí tuệ đơn nhất, tập trung sang tư tưởng trí tuệ phân tán, cộng tác; cuối cùng hiểu cách mô hình “học” đã thay đổi hoàn toàn phương thức Agent thu nhận năng lực, và sản sinh ra những Agent hiện đại mà chúng ta thấy ngày nay.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-00.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.1 Bậc thang tiến hóa của Agent AI</p>
</div>

Như trong Hình 2.1, **sự xuất hiện của mỗi mô hình mới đều nhằm giải quyết “nỗi đau” cốt lõi hoặc hạn chế căn bản của mô hình thế hệ trước.** Và giải pháp mới, trong khi mang lại bước nhảy về năng lực, cũng đưa vào những “hạn chế” mới khó vượt qua ở thời điểm đó, và điều này lại đặt nền móng cho sự ra đời của mô hình thế hệ sau. Hiểu được tiến trình lặp “do vấn đề dẫn dắt” này giúp chúng ta nắm bắt sâu sắc hơn những lý do tầng sâu và tính tất yếu lịch sử đằng sau việc lựa chọn công nghệ Agent hiện đại.

## 2.1 Agent sơ khai dựa trên biểu tượng và logic

Những khám phá ban đầu trong lĩnh vực trí tuệ nhân tạo chịu ảnh hưởng sâu sắc từ logic toán học và các nguyên lý cơ bản của khoa học máy tính. Ở thời đại đó, các nhà nghiên cứu thường giữ niềm tin: trí tuệ của con người, đặc biệt là năng lực suy luận logic, có thể được hệ thống biểu tượng hình thức hóa nắm bắt và tái tạo. Tư tưởng cốt lõi này sản sinh ra mô hình quan trọng đầu tiên của trí tuệ nhân tạo — chủ nghĩa biểu tượng (Symbolicism), còn được gọi là “AI logic” hay “AI truyền thống”.

Dưới góc nhìn của chủ nghĩa biểu tượng, cốt lõi của hành vi thông minh là thao tác trên các biểu tượng dựa trên một bộ quy tắc tường minh. Vì vậy, một Agent có thể được coi là một hệ thống biểu tượng vật lý: nó biểu diễn thế giới bên ngoài thông qua các biểu tượng nội tại, và lập kế hoạch hành động thông qua suy luận logic. “Trí tuệ” của Agent thời đại này hoàn toàn bắt nguồn từ cơ sở tri thức và quy tắc suy luận được nhà thiết kế mã hóa trước, chứ không phải từ tự học.

### 2.1.1 Giả thuyết hệ thống biểu tượng vật lý

Cơ sở lý thuyết của thời đại chủ nghĩa biểu tượng là **giả thuyết hệ thống biểu tượng vật lý (Physical Symbol System Hypothesis, PSSH)**<sup>[1]</sup> do **Allen Newell** và **Herbert A. Simon** cùng đề xuất năm 1976. Hai nhà khoa học đoạt giải Turing này, thông qua giả thuyết đó, đã cung cấp định hướng lý thuyết và tiêu chuẩn đánh giá cho việc hiện thực trí tuệ nhân tạo tổng quát trên máy tính.

Giả thuyết này gồm hai luận điểm cốt lõi:

1. **Luận điểm đủ**: bất kỳ hệ thống biểu tượng vật lý nào cũng có đủ phương tiện để tạo ra hành vi thông minh tổng quát.
2. **Luận điểm cần**: bất kỳ hệ thống nào có thể thể hiện hành vi thông minh tổng quát, về bản chất, tất yếu là một hệ thống biểu tượng vật lý.

Hệ thống biểu tượng vật lý ở đây chỉ một hệ thống có thể tồn tại trong thế giới vật lý, được cấu thành từ một tập hợp các biểu tượng có thể phân biệt và một chuỗi quá trình thao tác trên các biểu tượng đó, các yếu tố cấu thành được thể hiện trong Hình 2.2. Những biểu tượng này có thể được kết hợp thành những cấu trúc phức tạp hơn (như biểu thức), còn các quá trình có thể tạo, sửa, sao chép và hủy các cấu trúc biểu tượng này.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-0.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.2 Các yếu tố cấu thành của hệ thống biểu tượng vật lý</p>
</div>

Nói ngắn gọn, PSSH tuyên bố một cách táo bạo: **bản chất của trí tuệ chính là tính toán và xử lý biểu tượng.**

Giả thuyết này có ảnh hưởng sâu rộng. Nó chuyển việc nghiên cứu tâm trí con người — một vấn đề triết học mơ hồ và phức tạp — thành một vấn đề cụ thể có thể hiện thực bằng kỹ thuật trên máy tính. Nó truyền cho các nhà nghiên cứu AI thời kỳ đầu niềm tin mạnh mẽ rằng chỉ cần tìm được cách đúng để biểu diễn tri thức và thiết kế thuật toán suy luận hiệu quả, chúng ta nhất định tạo ra được trí tuệ máy sánh ngang con người. Toàn bộ nghiên cứu của thời đại chủ nghĩa biểu tượng, từ hệ chuyên gia đến lập kế hoạch tự động, gần như đều được triển khai dưới sự dẫn dắt của giả thuyết này.

### 2.1.2 Hệ chuyên gia

Dưới ảnh hưởng trực tiếp của giả thuyết hệ thống biểu tượng vật lý, **hệ chuyên gia (Expert System)** trở thành thành quả ứng dụng quan trọng nhất và thành công nhất của thời đại chủ nghĩa biểu tượng. Mục tiêu cốt lõi của hệ chuyên gia là mô phỏng năng lực giải quyết vấn đề của chuyên gia con người trong một lĩnh vực cụ thể. Bằng cách mã hóa tri thức và kinh nghiệm của chuyên gia thành chương trình máy tính, nó có thể đưa ra kết luận hoặc gợi ý sánh ngang, thậm chí vượt con người, khi đối mặt với những vấn đề tương tự.

Một hệ chuyên gia điển hình thường gồm vài phần cốt lõi như cơ sở tri thức, máy suy luận, giao diện người dùng, kiến trúc tổng quát được thể hiện trong Hình 2.3.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-1.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.3 Kiến trúc tổng quát của hệ chuyên gia</p>
</div>


Kiến trúc này thể hiện rõ tư tưởng thiết kế tách rời tri thức và suy luận, đây là đặc trưng quan trọng của AI biểu tượng.

**Cơ sở tri thức và máy suy luận**

“Trí tuệ” của hệ chuyên gia chủ yếu bắt nguồn từ hai thành phần cốt lõi: cơ sở tri thức và máy suy luận.

- **Cơ sở tri thức (Knowledge Base)**: đây là trung tâm lưu trữ tri thức của hệ chuyên gia, dùng để chứa tri thức và kinh nghiệm của chuyên gia trong lĩnh vực. **Biểu diễn tri thức (Knowledge Representation)** là chìa khóa để xây dựng cơ sở tri thức. Trong hệ chuyên gia, một phương pháp biểu diễn tri thức được dùng phổ biến nhất là **luật sản xuất (Production Rules)**, tức một chuỗi câu điều kiện dạng “IF-THEN”. Ví dụ: IF bệnh nhân có triệu chứng sốt AND ho THEN có thể mắc nhiễm trùng đường hô hấp. Những quy tắc này liên kết một tình huống cụ thể (phần IF, điều kiện) với kết luận hoặc hành động tương ứng (phần THEN, kết luận). Một hệ chuyên gia phức tạp có thể chứa hàng trăm, hàng nghìn quy tắc như vậy, cùng tạo thành một mạng tri thức khổng lồ.
- **Máy suy luận (Inference Engine)**: máy suy luận là bộ máy tính toán cốt lõi của hệ chuyên gia. Đây là một chương trình tổng quát, nhiệm vụ là dựa trên sự kiện do người dùng cung cấp, tìm và áp dụng các quy tắc liên quan trong cơ sở tri thức, từ đó suy ra kết luận mới. Máy suy luận có hai cách làm việc chính:
  - **Suy luận tiến (Forward Chaining)**: xuất phát từ sự kiện đã biết, liên tục khớp phần IF của quy tắc, kích hoạt kết luận ở phần THEN, và thêm kết luận mới vào cơ sở sự kiện, cho đến khi cuối cùng suy ra mục tiêu hoặc không còn quy tắc nào có thể khớp. Đây là cách suy luận “do dữ liệu dẫn dắt”.
  - **Suy luận lùi (Backward Chaining)**: xuất phát từ một mục tiêu giả định (như “bệnh nhân có mắc viêm phổi không”), tìm quy tắc có thể suy ra mục tiêu đó, sau đó lấy phần IF của quy tắc làm mục tiêu con mới, cứ đệ quy như vậy cho đến khi mọi mục tiêu con đều được sự kiện đã biết chứng minh. Đây là cách suy luận “do mục tiêu dẫn dắt”.

**Ca ứng dụng và phân tích: hệ thống MYCIN**

MYCIN là một trong những hệ chuyên gia nổi tiếng nhất và có ảnh hưởng nhất trong lịch sử, do Đại học Stanford phát triển vào những năm 1970<sup>[2]</sup>. Nó được thiết kế để hỗ trợ bác sĩ chẩn đoán nhiễm trùng máu do vi khuẩn và gợi ý phác đồ kháng sinh phù hợp.

- **Nguyên lý hoạt động**: MYCIN thu thập triệu chứng, tiền sử bệnh và kết quả xét nghiệm của bệnh nhân thông qua tương tác hỏi đáp với bác sĩ. Cơ sở tri thức của nó chứa khoảng 600 quy tắc “IF-THEN” do chuyên gia y tế cung cấp. Máy suy luận chủ yếu làm việc theo suy luận lùi: xuất phát từ mục tiêu cao nhất “xác định vi khuẩn gây bệnh”, suy ngược để tìm những bằng chứng và điều kiện cần thiết, sau đó hỏi bác sĩ để lấy thông tin này. Quy trình làm việc được đơn giản hóa trong Hình 2.4.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-2.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.4 Sơ đồ quy trình suy luận lùi của MYCIN</p>
</div>

- **Xử lý bất định**: chẩn đoán y tế đầy bất định. Một cải tiến quan trọng của MYCIN là đưa vào khái niệm **hệ số tin cậy (Certainty Factor, CF)**, dùng một giá trị trong khoảng -1 đến 1 để biểu thị độ tin cậy của một kết luận. Điều này giúp hệ thống xử lý được tri thức y khoa bất định, mơ hồ, và đưa ra kết quả chẩn đoán kèm đánh giá độ tin cậy, gần với thế giới thực hơn logic Boolean đơn giản.
- **Thành tựu và ý nghĩa**: trong một đánh giá, MYCIN thể hiện vượt trội so với bác sĩ không chuyên trong chẩn đoán nhiễm trùng máu, thậm chí đạt trình độ chuyên gia con người. Thành công của nó đã chứng minh hùng hồn tính hiệu lực của giả thuyết hệ thống biểu tượng vật lý: thông qua kỹ nghệ tri thức cẩn thận và suy luận biểu tượng, máy móc thực sự có thể thể hiện “trí tuệ” xuất sắc trong những lĩnh vực chuyên môn phức tạp cao độ. MYCIN không chỉ là một cột mốc trong lịch sử phát triển hệ chuyên gia, mà còn mở đường cho việc thương mại hóa AI ở các lĩnh vực dọc tiếp theo.

### 2.1.3 SHRDLU

Nếu hệ chuyên gia cho thấy “độ sâu” của AI biểu tượng trong các lĩnh vực chuyên môn, thì dự án SHRDLU<sup>[3]</sup> do **Terry Winograd** phát triển từ năm 1968 đến 1970 lại tạo ra bước đột phá mang tính cách mạng về “độ rộng”. Như trong Hình 2.5, SHRDLU nhằm xây dựng một Agent tổng hợp có thể tương tác trôi chảy với con người bằng ngôn ngữ tự nhiên trong một môi trường vi mô là “thế giới khối gỗ”. “Thế giới khối gỗ” là một không gian ba chiều ảo mô phỏng, chứa các khối gỗ với hình dạng, màu sắc và kích thước khác nhau, cùng một cánh tay robot ảo có thể gắp và di chuyển chúng. Người dùng ra chỉ thị hoặc đặt câu hỏi cho SHRDLU bằng ngôn ngữ tự nhiên, SHRDLU thực hiện hành động trong thế giới ảo hoặc đưa ra câu trả lời bằng văn bản.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-3.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.5 Giao diện tương tác “thế giới khối gỗ” của SHRDLU</p>
</div>

SHRDLU gây chú ý rộng rãi vào thời đó, chủ yếu vì nó lần đầu tích hợp nhiều mô-đun trí tuệ nhân tạo độc lập (như phân tích ngôn ngữ, lập kế hoạch, ghi nhớ) vào một hệ thống thống nhất, và khiến chúng phối hợp hoạt động:

- **Hiểu ngôn ngữ tự nhiên**: SHRDLU có thể phân tích những câu tiếng Anh có cấu trúc phức tạp và chứa nhập nhằng. Nó không chỉ hiểu lệnh trực tiếp (như `Pick up a big red block.`), mà còn xử lý được những chỉ thị phức tạp hơn, ví dụ:
  - Phân giải đại từ: `Find a block which is taller than the one you are holding and put it into the box.` Trong chỉ thị này, hệ thống cần hiểu `the one you are holding` chỉ vật mà cánh tay robot đang gắp.
  - Ghi nhớ ngữ cảnh: người dùng có thể nói `Grasp the pyramid.`, sau đó hỏi tiếp `What does the box contain?`, hệ thống có thể liên hệ ngữ cảnh để trả lời.
- **Lập kế hoạch và hành động**: sau khi hiểu chỉ thị, SHRDLU có thể tự lập kế hoạch một chuỗi hành động cần thiết để hoàn thành nhiệm vụ. Ví dụ, nếu chỉ thị là “đặt khối gỗ xanh lên khối gỗ đỏ”, mà trên khối đỏ đã có một khối xanh lá khác, hệ thống sẽ lập kế hoạch chuỗi hành động “trước tiên dời khối xanh lá đi, rồi đặt khối xanh dương lên”.
- **Ghi nhớ và hỏi đáp**: SHRDLU có bộ nhớ về môi trường và hành vi của chính nó. Người dùng có thể đặt câu hỏi về điều đó, ví dụ:
  - Hỏi trạng thái thế giới: `Is there a large block behind a pyramid?`
  - Hỏi lịch sử hành vi: `Did you touch any pyramid before you put the green one on the little cube?`
  - Hỏi động cơ hành vi: `Why did you pick up the red block?` SHRDLU có thể trả lời: `BECAUSE YOU ASKED ME TO.`

Vị thế lịch sử và ảnh hưởng của SHRDLU thể hiện ở ba phương diện:

- **Hình mẫu của trí tuệ tổng hợp**: trước SHRDLU, nghiên cứu AI phần lớn tập trung vào một chức năng đơn lẻ. Nó lần đầu tích hợp nhiều mô-đun AI như hiểu ngôn ngữ, suy luận - lập kế hoạch và ghi nhớ hành động vào một hệ thống thống nhất; thiết kế vòng lặp kín “cảm nhận - suy nghĩ - hành động” của nó đã đặt nền tảng cho nghiên cứu Agent hiện đại.
- **Phổ biến phương pháp nghiên cứu thế giới vi mô**: thành công của nó chứng minh tính khả thi của việc khám phá và kiểm chứng nguyên lý cơ bản của Agent phức tạp trong một môi trường đơn giản, có quy tắc rõ ràng; phương pháp này ảnh hưởng sâu sắc đến nghiên cứu robot học và lập kế hoạch AI sau này.
- **Sự lạc quan và phản tư mà nó gợi ra**: thành công của SHRDLU khơi dậy kỳ vọng lạc quan sớm về AGI, nhưng năng lực của nó lại bị giới hạn nghiêm ngặt trong thế giới khối gỗ. Hạn chế này khơi ra cuộc tranh luận lâu dài trong lĩnh vực AI về khác biệt giữa “xử lý biểu tượng” và “hiểu thực sự”, cho thấy những thách thức sâu xa trên con đường tới trí tuệ tổng quát.

### 2.1.4 Thách thức căn bản mà chủ nghĩa biểu tượng đối mặt

Dù các dự án thời kỳ đầu đạt thành tựu đáng chú ý, từ những năm 1980, khi AI biểu tượng bước từ “thế giới vi mô” ra thế giới thực mở và phức tạp, nó gặp phải những vấn đề căn bản cố hữu trong phương pháp luận của mình. Những vấn đề này chủ yếu quy về hai loại lớn:

**(1) Tri thức thông thường và nút cổ chai thu nhận tri thức**

“Trí tuệ” của Agent biểu tượng hoàn toàn phụ thuộc vào chất lượng và tính hoàn chỉnh của cơ sở tri thức. Tuy nhiên, việc xây dựng một cơ sở tri thức có thể hỗ trợ tương tác trong thế giới thực đã được chứng minh là một nhiệm vụ cực kỳ gian nan, thể hiện ở hai phương diện:

- **Nút cổ chai thu nhận tri thức (Knowledge Acquisition Bottleneck)**: tri thức của hệ chuyên gia cần được chuyên gia con người và kỹ sư tri thức xây dựng thông qua quá trình phỏng vấn, chắt lọc và mã hóa tỉ mỉ. Quá trình này tốn kém, kéo dài và khó mở rộng quy mô. Quan trọng hơn, nhiều tri thức của chuyên gia con người là ẩn, mang tính trực giác, rất khó diễn đạt rõ ràng thành quy tắc “IF-THEN”. Việc cố gắng biểu tượng hóa thủ công toàn bộ tri thức của thế giới được coi là nhiệm vụ gần như bất khả thi.
- **Vấn đề tri thức thông thường (Common-sense Problem)**: hành vi của con người dựa vào một nền tri thức thông thường khổng lồ (ví dụ “nước thì ướt”, “dây thừng có thể kéo chứ không thể đẩy”), nhưng hệ thống biểu tượng không biết gì về điều đó trừ khi được mã hóa tường minh. Xây dựng cơ sở tri thức hoàn chỉnh cho tri thức thông thường rộng lớn, mơ hồ vẫn là thách thức lớn cho đến nay; dự án Cyc<sup>[4]</sup> đã nỗ lực hàng chục năm nhưng thành quả và ứng dụng vẫn rất hạn chế.

**(2) Vấn đề khung và tính dễ tổn thương của hệ thống**

Ngoài thách thức ở tầng tri thức, chủ nghĩa biểu tượng còn gặp khó khăn logic khi xử lý thế giới biến đổi.

- **Vấn đề khung (Frame Problem)**: trong một thế giới động, sau khi Agent thực hiện một hành động, làm thế nào để phán đoán hiệu quả những gì không thay đổi là một bài toán logic<sup>[5]</sup>. Việc khai báo tường minh mọi trạng thái bất biến cho từng hành động là bất khả thi về mặt tính toán, trong khi con người lại bỏ qua những thay đổi không liên quan một cách dễ dàng.
- **Tính dễ tổn thương của hệ thống (Brittleness)**: hệ thống biểu tượng hoàn toàn phụ thuộc quy tắc đặt trước, khiến hành vi của nó rất “dễ tổn thương”. Một khi gặp bất kỳ thay đổi nhỏ hoặc tình huống mới nào ngoài quy tắc, hệ thống có thể thất bại hoàn toàn, không thể linh hoạt ứng biến như con người. Thành công của SHRDLU cũng chính vì nó vận hành trong một thế giới khép kín có quy tắc hoàn chỉnh, còn thế giới thực thì đầy ngoại lệ.

## 2.2 Xây dựng chatbot dựa trên quy tắc

Sau khi đã thảo luận những thách thức lý thuyết của chủ nghĩa biểu tượng, trong mục này chúng ta sẽ thông qua một thực hành lập trình cụ thể để cảm nhận trực quan cách một hệ thống dựa trên quy tắc vận hành. Chúng ta sẽ thử tái tạo một chatbot sơ khai có ảnh hưởng lớn trong lịch sử trí tuệ nhân tạo — ELIZA.

### 2.2.1 Tư tưởng thiết kế của ELIZA

ELIZA là một chương trình máy tính do nhà khoa học máy tính **Joseph Weizenbaum** của MIT công bố năm 1966<sup>[6]</sup>, là một trong những nỗ lực nổi tiếng của lĩnh vực xử lý ngôn ngữ tự nhiên thời kỳ đầu. ELIZA không phải một chương trình đơn nhất mà là một framework có thể thực thi các “script” khác nhau. Trong đó, script được biết đến rộng rãi nhất và thành công nhất là “DOCTOR”, mô phỏng một nhà trị liệu tâm lý theo trường phái Rogers, người không chỉ đạo.

Cách ELIZA làm việc cực kỳ khéo léo: nó không bao giờ trả lời trực diện câu hỏi hay cung cấp thông tin, mà thông qua việc nhận diện từ khóa trong đầu vào của người dùng, rồi áp dụng một bộ quy tắc chuyển đổi đặt trước để biến câu phát biểu của người dùng thành một câu hỏi mở. Ví dụ, khi người dùng nói “Tôi buồn vì bạn trai tôi”, ELIZA có thể nhận diện từ khóa “Tôi buồn vì…” và áp dụng quy tắc để sinh phản hồi: “Vì sao bạn lại buồn vì bạn trai của bạn?”.

Tư tưởng thiết kế của Weizenbaum không phải tạo ra một Agent thực sự có thể “hiểu” cảm xúc con người, mà ngược lại, ông muốn chứng minh rằng bằng vài kỹ thuật chuyển đổi câu đơn giản, máy móc có thể tạo ra ảo giác “thông minh” và “đồng cảm” trong khi hoàn toàn không hiểu nội dung cuộc hội thoại. Tuy nhiên, ngoài dự đoán của ông, nhiều người đã tương tác với ELIZA (kể cả thư ký của ông) lại nảy sinh phụ thuộc cảm xúc với nó, tin chắc rằng nó có thể hiểu mình.

Mục tiêu thực hành của mục này là tái tạo cơ chế cốt lõi của ELIZA, để hiểu sâu ưu điểm và hạn chế căn bản của phương pháp do quy tắc dẫn dắt này.

### 2.2.2 Khớp mẫu và thay thế văn bản

Thuật toán của ELIZA dựa trên **khớp mẫu (Pattern Matching) và thay thế văn bản (Text Substitution)**, có thể được phân tách rõ ràng thành bốn bước sau:

1. **Nhận diện và sắp xếp từ khóa:** cơ sở quy tắc đặt cho mỗi từ khóa (như `mother`, `dreamed`, `depressed`) một độ ưu tiên. Khi đầu vào chứa nhiều từ khóa, chương trình chọn quy tắc tương ứng với từ khóa có độ ưu tiên cao nhất để xử lý.
2. **Quy tắc phân tách:** sau khi tìm được từ khóa, chương trình dùng quy tắc phân tách có ký tự đại diện (`*`) để bắt phần còn lại của câu.
   1. **Ví dụ quy tắc**: `* my *`
   2. **Đầu vào người dùng**: `"My mother is afraid of me"`
   3. **Kết quả bắt được**: `["", "mother is afraid of me"]`
3. **Quy tắc tái tổ hợp:** chương trình chọn từ một nhóm quy tắc tái tổ hợp gắn với quy tắc phân tách để sinh phản hồi (thường chọn ngẫu nhiên để tăng đa dạng), và có thể tùy chọn dùng nội dung bắt được ở bước trên.
   1. **Ví dụ quy tắc**: `"Tell me more about your family."`
   2. **Sinh đầu ra**: `"Tell me more about your family."`
4. **Chuyển đổi đại từ:** trước khi tái tổ hợp, chương trình thực hiện chuyển đổi đại từ đơn giản (như `I` → `you`, `my` → `your`) để duy trì tính liên tục của hội thoại.

Toàn bộ quy trình làm việc có thể được biểu diễn bằng một ý tưởng mã giả đơn giản:

```Python
FUNCTION generate_response(user_input):
    // 1. Tách đầu vào của người dùng thành các từ
    words = SPLIT(user_input)

    // 2. Tìm quy tắc từ khóa có độ ưu tiên cao nhất
    best_rule = FIND_BEST_RULE(words)
    IF best_rule is NULL:
        RETURN a_generic_response() // ví dụ: "Please go on."

    // 3. Dùng quy tắc để phân tách đầu vào của người dùng
    decomposed_parts = DECOMPOSE(user_input, best_rule.decomposition_pattern)
    IF decomposition_failed:
        RETURN a_generic_response()

    // 4. Chuyển đổi đại từ trên các phần đã phân tách
    transformed_parts = TRANSFORM_PRONOUNS(decomposed_parts)

    // 5. Dùng quy tắc tái tổ hợp để sinh phản hồi
    response = REASSEMBLE(transformed_parts, best_rule.reassembly_patterns)

    RETURN response
```

Thông qua cơ chế này, ELIZA đã rút gọn thành công bài toán hiểu ngôn ngữ tự nhiên phức tạp thành một trò chơi khớp mẫu dựa trên quy tắc, có thể thao tác được.

### 2.2.3 Hiện thực logic cốt lõi

Bây giờ, chúng ta sẽ chuyển nguyên lý kỹ thuật mô tả ở mục trước thành một hàm Python đơn giản, có thể chạy được. Đoạn mã dưới đây hiện thực một phiên bản mini của ELIZA, chứa một phần nhỏ quy tắc nhưng đủ để thể hiện cơ chế làm việc cốt lõi của nó.

```Python
import re
import random

# Định nghĩa cơ sở quy tắc: mẫu (biểu thức chính quy) -> danh sách mẫu phản hồi
rules = {
    r'I need (.*)': [
        "Why do you need {0}?",
        "Would it really help you to get {0}?",
        "Are you sure you need {0}?"
    ],
    r'Why don\'t you (.*)\?': [
        "Do you really think I don't {0}?",
        "Perhaps eventually I will {0}.",
        "Do you really want me to {0}?"
    ],
    r'Why can\'t I (.*)\?': [
        "Do you think you should be able to {0}?",
        "If you could {0}, what would you do?",
        "I don't know -- why can't you {0}?"
    ],
    r'I am (.*)': [
        "Did you come to me because you are {0}?",
        "How long have you been {0}?",
        "How do you feel about being {0}?"
    ],
    r'.* mother .*': [
        "Tell me more about your mother.",
        "What was your relationship with your mother like?",
        "How do you feel about your mother?"
    ],
    r'.* father .*': [
        "Tell me more about your father.",
        "How did your father make you feel?",
        "What has your father taught you?"
    ],
    r'.*': [
        "Please tell me more.",
        "Let's change focus a bit... Tell me about your family.",
        "Can you elaborate on that?"
    ]
}

# Định nghĩa quy tắc chuyển đổi đại từ
pronoun_swap = {
    "i": "you", "you": "i", "me": "you", "my": "your",
    "am": "are", "are": "am", "was": "were", "i'd": "you would",
    "i've": "you have", "i'll": "you will", "yours": "mine",
    "mine": "yours"
}

def swap_pronouns(phrase):
    """
    Chuyển đổi đại từ ngôi thứ nhất/ngôi thứ hai trong cụm từ đầu vào
    """
    words = phrase.lower().split()
    swapped_words = [pronoun_swap.get(word, word) for word in words]
    return " ".join(swapped_words)

def respond(user_input):
    """
    Sinh phản hồi dựa trên cơ sở quy tắc
    """
    for pattern, responses in rules.items():
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            # Bắt phần khớp được
            captured_group = match.group(1) if match.groups() else ''
            # Thực hiện chuyển đổi đại từ
            swapped_group = swap_pronouns(captured_group)
            # Chọn ngẫu nhiên một mẫu và định dạng
            response = random.choice(responses).format(swapped_group)
            return response
    # Nếu không khớp quy tắc cụ thể nào, dùng quy tắc đại diện cuối cùng
    return random.choice(rules[r'.*'])

# Vòng lặp trò chuyện chính
if __name__ == '__main__':
    print("Therapist: Hello! How can I help you today?")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Therapist: Goodbye. It was nice talking to you.")
            break
        response = respond(user_input)
        print(f"Therapist: {response}")

>>>
Therapist: Hello! How can I help you today?
You: I am feeling sad today.
Therapist: How long have you been feeling sad today?
You: I need some help with my project.
Therapist: Are you sure you need some help with your project?
You: My mother is not happy with my work.
Therapist: Tell me more about your mother.
You: quit
Therapist: Goodbye. It was nice talking to you.
```

Qua thực hành lập trình trên, chúng ta có thể khái quát trực quan những hạn chế căn bản của hệ thống do quy tắc dẫn dắt, những hạn chế này chính là minh chứng trực tiếp cho thách thức lý thuyết của chủ nghĩa biểu tượng ở mục `2.1.4`:

- **Thiếu hiểu ngữ nghĩa**: hệ thống không hiểu nghĩa của từ. Ví dụ, trước đầu vào “I am **not** happy”, nó vẫn máy móc khớp quy tắc `I am (.*)` và sinh phản hồi vô nghĩa, vì nó không hiểu tác dụng của từ phủ định “not”.
- **Không có bộ nhớ ngữ cảnh**: hệ thống là **phi trạng thái (Stateless)**, mỗi phản hồi chỉ dựa trên câu đầu vào hiện tại, không thể duy trì hội thoại nhiều lượt liền mạch.
- **Vấn đề mở rộng quy tắc**: cố gắng thêm nhiều quy tắc hơn sẽ khiến cơ sở quy tắc bùng nổ về quy mô, việc quản lý xung đột và độ ưu tiên giữa các quy tắc trở nên cực kỳ phức tạp, cuối cùng khiến hệ thống khó bảo trì.

Tuy nhiên, dù tồn tại những khiếm khuyết hiển nhiên này, ELIZA lại tạo ra “**hiệu ứng ELIZA**” nổi tiếng vào thời đó, nhiều người dùng tin rằng nó có thể hiểu mình. Ảo giác về trí tuệ này chủ yếu bắt nguồn từ chiến lược hội thoại khéo léo của nó (như đóng vai người đặt câu hỏi thụ động, dùng mẫu câu mở) và tâm lý phóng chiếu cảm xúc bẩm sinh của con người.

Thực hành với ELIZA cho thấy rõ mâu thuẫn cốt lõi của phương pháp biểu tượng: biểu hiện có vẻ thông minh của hệ thống hoàn toàn phụ thuộc vào quy tắc được nhà thiết kế mã hóa trước. Tuy nhiên, trước vô số khả năng của ngôn ngữ trong thế giới thực, phương pháp liệt kê cạn kiệt này chắc chắn không thể mở rộng. Hệ thống không có sự hiểu thực sự, chỉ đang thực thi thao tác biểu tượng, đây chính là nguồn gốc tính dễ tổn thương của nó.

## 2.3 Xã hội tâm trí của Marvin Minsky

Sự khám phá của chủ nghĩa biểu tượng và thực hành với ELIZA cùng chỉ về một vấn đề: một bộ máy suy luận đơn nhất, tập trung, được xây dựng bằng quy tắc đặt trước, dường như khó dẫn tới trí tuệ thực sự. Dù cơ sở quy tắc lớn đến đâu, khi đối mặt với tính mơ hồ, phức tạp và biến đổi vô tận của thế giới thực, hệ thống luôn tỏ ra cứng nhắc và dễ tổn thương. Bế tắc này khiến một số nhà tư tưởng hàng đầu bắt đầu phản tư về triết lý thiết kế nền tảng nhất của trí tuệ nhân tạo. Trong đó, **Marvin Minsky** không tiếp tục thử thêm quy tắc cho một lõi suy luận đơn nhất, mà trong cuốn ***The Society of Mind* (Xã hội tâm trí)**<sup>[7]</sup> của ông đã đặt một câu hỏi mang tính cách mạng: "What magical trick makes us intelligent? The trick is that there is no trick. The power of intelligence stems from our vast diversity, not from any single, perfect principle." (Mẹo thần kỳ nào khiến chúng ta thông minh? Mẹo đó là không có mẹo nào cả. Sức mạnh của trí tuệ bắt nguồn từ sự đa dạng phong phú của chúng ta, chứ không từ bất kỳ nguyên lý đơn nhất, hoàn hảo nào.)

### 2.3.1 Phản tư về mô hình trí tuệ đơn nhất tổng thể

Những năm 1970-1980, hạn chế của chủ nghĩa biểu tượng ngày càng rõ. Hệ chuyên gia tuy thành công trong các lĩnh vực dọc cao độ, nhưng chúng không có tri thức thông thường như một đứa trẻ; SHRDLU tuy thể hiện xuất sắc trong một thế giới khối gỗ khép kín, nhưng nó không thể hiểu bất cứ điều gì bên ngoài thế giới đó; ELIZA tuy bắt chước được hội thoại, nhưng nó hoàn toàn không biết gì về nội dung cuộc hội thoại. Những hệ thống này đều tuân theo một tư duy thiết kế từ trên xuống (Top-down): một bộ xử lý trung tâm toàn tri toàn năng, xử lý thông tin và ra quyết định theo một bộ quy tắc logic thống nhất.

Trước thất bại phổ biến này, Minsky bắt đầu đặt ra một loạt câu hỏi căn bản:

- **“Hiểu” là gì?** Khi chúng ta nói mình hiểu một câu chuyện, đó có phải là một năng lực đơn nhất? Hay thực ra nó là kết quả phối hợp của hàng chục quá trình tâm trí khác nhau như năng lực hình ảnh hóa, năng lực suy luận logic, năng lực đồng cảm, tri thức thông thường về quan hệ xã hội?
- **“Tri thức thông thường” là gì?** Tri thức thông thường là một cơ sở tri thức khổng lồ chứa hàng triệu quy tắc logic (như nỗ lực của dự án Cyc)? Hay nó là một mạng phân tán, được dệt từ vô số kinh nghiệm cụ thể và những mảnh quy tắc đơn giản?
- **Agent nên được xây dựng như thế nào?** Chúng ta có nên tiếp tục theo đuổi một hệ thống logic hoàn hảo, thống nhất, hay nên thừa nhận rằng bản thân trí tuệ là “không hoàn hảo”, là một mớ hỗn hợp gồm nhiều phần đơn giản với chức năng khác nhau, thậm chí xung đột lẫn nhau?

Những câu hỏi này nhắm trực diện vào nhược điểm cốt lõi của mô hình trí tuệ đơn nhất tổng thể. Loại mô hình này cố gắng dùng một cơ chế biểu diễn và suy luận thống nhất để giải quyết mọi vấn đề, nhưng điều đó cách rất xa cách vận hành của trí tuệ tự nhiên (đặc biệt là trí tuệ con người) mà chúng ta quan sát được. Minsky cho rằng việc cưỡng ép các hoạt động tâm trí đa dạng vào một khung logic cứng nhắc chính là nguồn gốc khiến nghiên cứu AI thời kỳ đầu trì trệ.

Chính dựa trên sự phản tư này, Minsky đề xuất một ý tưởng đảo ngược, ông không còn coi tâm trí là một cấu trúc phân tầng hình kim tự tháp, mà coi nó là một “xã hội” phẳng, đầy tương tác và cộng tác.

### 2.3.2 Trí tuệ như một thể cộng tác

Trong khung lý thuyết của Minsky, định nghĩa Agent có khác so với Agent hiện đại mà chúng ta thảo luận ở chương một. Agent ở đây chỉ một quá trình tâm trí cực kỳ đơn giản, chuyên biệt, bản thân nó là “vô tâm”. Ví dụ, một Agent `LINE-FINDER` chịu trách nhiệm nhận diện đường nét, hoặc một Agent `GRASP` chịu trách nhiệm gắp.

Những Agent đơn giản này được tổ chức lại, tạo thành những **cơ quan (Agency)** mạnh mẽ hơn về chức năng. Một cơ quan là một nhóm Agent phối hợp hoạt động, nhằm hoàn thành một nhiệm vụ phức tạp hơn. Ví dụ, một cơ quan `BUILD` chịu trách nhiệm xếp khối gỗ có thể gồm nhiều Agent hoặc cơ quan cấp dưới như `SEE`, `FIND`, `GET`, `PUT`. Chúng tác động lẫn nhau thông qua các tín hiệu kích hoạt và ức chế phi tập trung, tạo thành dòng điều khiển động.

**Tính nổi sinh (Emergence)** là chìa khóa để hiểu lý thuyết xã hội tâm trí. Hành vi thông minh phức tạp, có mục đích không phải do một Agent cấp cao lập kế hoạch trước, mà tự phát sinh từ tương tác cục bộ giữa lượng lớn Agent đơn giản ở tầng dưới.

Hãy lấy nhiệm vụ kinh điển “xây tháp khối gỗ” làm ví dụ để minh họa quá trình này, như trong Hình 2.6. Khi một mục tiêu cấp cao (như “tôi muốn xây một cái tháp”) xuất hiện, nó kích hoạt một cơ quan cấp cao tên `BUILD-TOWER`.

1. Cơ quan `BUILD-TOWER` không biết cách thực hiện hành động vật lý cụ thể, tác dụng duy nhất của nó là kích hoạt các cơ quan cấp dưới, ví dụ `BUILDER`.
2. Cơ quan `BUILDER` cũng rất đơn giản, nó có thể chỉ chứa một logic lặp: chừng nào tháp chưa xây xong, kích hoạt cơ quan `ADD-BLOCK`.
3. Cơ quan `ADD-BLOCK` chịu trách nhiệm điều phối các nhiệm vụ con cụ thể hơn, nó lần lượt kích hoạt ba cơ quan con `FIND-BLOCK`, `GET-BLOCK` và `PUT-ON-TOP`.
4. Mỗi cơ quan con lại được tạo thành từ những Agent tầng thấp hơn. Ví dụ, cơ quan `GET-BLOCK` kích hoạt Agent `SEE-SHAPE` trong hệ thống thị giác, cùng các Agent `REACH` và `GRASP` trong hệ thống vận động.

Trong quá trình này, không có bất kỳ Agent hay cơ quan nào sở hữu kế hoạch toàn cục cho toàn bộ nhiệm vụ. `GRASP` chỉ chịu trách nhiệm gắp, nó không biết tháp là gì; `BUILDER` chỉ chịu trách nhiệm lặp, nó không biết điều khiển cánh tay thế nào. Tuy nhiên, khi xã hội gồm vô số Agent “vô tâm” này tương tác với nhau qua những quy tắc kích hoạt và ức chế đơn giản, một hành vi có vẻ cực kỳ thông minh — xây tháp khối gỗ — đã tự nhiên nổi sinh.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-4.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.6 Sơ đồ cơ chế nổi sinh của hành vi xây tháp khối gỗ trong “xã hội tâm trí”</p>
</div>

### 2.3.3 Gợi mở lý thuyết cho hệ thống đa Agent

Ảnh hưởng sâu xa nhất của lý thuyết xã hội tâm trí là nó cung cấp nền tảng khái niệm quan trọng cho **trí tuệ nhân tạo phân tán (Distributed Artificial Intelligence, DAI)** và sau đó là **hệ thống đa Agent (Multi-Agent System, MAS)**. Nó gợi ra cho các nhà nghiên cứu suy nghĩ:

**Nếu trí tuệ bên trong một tâm trí được nổi sinh qua sự cộng tác của lượng lớn Agent đơn giản, thì giữa nhiều thực thể tính toán độc lập, tách biệt về mặt vật lý (máy tính, robot), liệu có thể nổi sinh một “trí tuệ bầy đàn” mạnh mẽ hơn nhờ cộng tác?**

Việc đặt ra câu hỏi này đã chuyển trực tiếp trọng tâm nghiên cứu từ “làm thế nào xây dựng một Agent đơn nhất toàn năng” sang “làm thế nào thiết kế một tập thể Agent cộng tác hiệu quả”. Cụ thể, xã hội tâm trí gợi mở trực tiếp cho nghiên cứu hệ thống đa Agent ở các phương diện sau:

- **Điều khiển phi tập trung (Decentralized Control)**: cốt lõi của lý thuyết là không tồn tại bộ điều khiển trung tâm. Tư tưởng này được lĩnh vực MAS kế thừa hoàn toàn; làm thế nào thiết kế cơ chế phối hợp không có nút trung tâm và chiến lược phân công nhiệm vụ đã trở thành một trong những đề tài nghiên cứu cốt lõi của MAS.
- **Tính toán nổi sinh (Emergent Computation)**: lời giải cho vấn đề phức tạp có thể tự phát sinh từ những quy tắc tương tác cục bộ đơn giản. Điều này gợi mở nhiều thuật toán dựa trên tư tưởng nổi sinh trong MAS, như thuật toán đàn kiến, tối ưu bầy đàn, dùng để giải quyết các bài toán tối ưu và tìm kiếm phức tạp.
- **Tính xã hội của Agent (Agent Sociality)**: lý thuyết của Minsky nhấn mạnh tương tác giữa các Agent (kích hoạt, ức chế). Lĩnh vực MAS mở rộng hơn nữa, nghiên cứu một cách hệ thống ngôn ngữ giao tiếp giữa các Agent (như ACL), giao thức tương tác (như mạng hợp đồng), chiến lược thương lượng, mô hình tin cậy, thậm chí cấu trúc tổ chức, từ đó xây dựng một xã hội tính toán thực sự.

Có thể nói, lý thuyết “xã hội tâm trí” của Minsky đã cung cấp cho các nhà nghiên cứu AI một khung phân tích quan trọng để hiểu cấu trúc bên trong của “trí tuệ bầy đàn”. Nó mang lại cho các nhà nghiên cứu sau này một góc nhìn hoàn toàn mới để khám phá những hệ thống phức tạp được tạo thành từ các Agent tính toán độc lập, tự trị, có năng lực xã hội, từ đó chính thức mở ra kỷ nguyên nghiên cứu hệ thống đa Agent.

## 2.4 Sự tiến hóa của mô hình học và Agent hiện đại

Lý thuyết “xã hội tâm trí” đã thảo luận ở trên, ở tầng triết học, chỉ ra hướng đi cho trí tuệ bầy đàn và cộng tác phi tập trung, nhưng con đường hiện thực vẫn chưa rõ ràng. Đồng thời, những thách thức căn bản mà chủ nghĩa biểu tượng bộc lộ khi đối phó với sự phức tạp của thế giới thực cũng cho thấy chỉ dựa vào quy tắc mã hóa trước không thể xây dựng trí tuệ thực sự bền vững.

Hai manh mối này cùng chỉ về một câu hỏi: nếu trí tuệ không thể được thiết kế hoàn toàn, thì liệu nó có thể được học ra không?

Câu hỏi này mở ra “kỷ nguyên học” của trí tuệ nhân tạo. Mục tiêu cốt lõi của nó không còn là mã hóa tri thức thủ công, mà là xây dựng những hệ thống có thể tự động thu nhận tri thức và năng lực từ kinh nghiệm và dữ liệu. Mục này sẽ truy nguyên lịch sử tiến hóa của mô hình này: từ nền tảng học do thuyết liên kết đặt ra, đến học tương tác do học tăng cường hiện thực, cho đến Agent hiện đại do mô hình ngôn ngữ lớn dẫn dắt ngày nay.

### 2.4.1 Từ biểu tượng đến liên kết

Như một phản hồi trực tiếp cho hạn chế của chủ nghĩa biểu tượng, **thuyết liên kết (Connectionism)** hồi sinh vào những năm 1980. Khác với triết lý thiết kế từ trên xuống, phụ thuộc quy tắc logic tường minh của chủ nghĩa biểu tượng, thuyết liên kết là phương pháp từ dưới lên, lấy cảm hứng từ việc mô phỏng cấu trúc mạng nơ-ron của não sinh học<sup>[8]</sup>. Tư tưởng cốt lõi của nó có thể khái quát như sau:

1. **Biểu diễn phân tán của tri thức**: tri thức không được lưu trong một cơ sở tri thức dưới dạng biểu tượng hay quy tắc tường minh, mà được lưu phân tán dưới dạng trọng số kết nối giữa lượng lớn đơn vị xử lý đơn giản (tức nơ-ron nhân tạo). Bản thân mô hình kết nối của toàn mạng đã tạo thành tri thức.
2. **Đơn vị xử lý đơn giản**: mỗi nơ-ron chỉ thực hiện một phép tính rất đơn giản, như nhận đầu vào có trọng số từ các nơ-ron khác, xử lý qua một hàm kích hoạt, rồi xuất kết quả cho nơ-ron tiếp theo.
3. **Điều chỉnh trọng số qua học**: trí tuệ của hệ thống không đến từ chương trình phức tạp do nhà thiết kế viết trước, mà đến từ quá trình “học”. Hệ thống tiếp xúc với lượng lớn mẫu, và theo một thuật toán học nào đó (như thuật toán lan truyền ngược), tự động điều chỉnh lặp đi lặp lại trọng số kết nối giữa các nơ-ron, từ đó khiến đầu ra của toàn mạng dần tiến gần mục tiêu kỳ vọng.

Trong mô hình này, Agent không còn là một bộ máy suy luận logic thực thi quy tắc một cách thụ động, mà là một hệ thống thích nghi có thể tự tối ưu qua kinh nghiệm. Như trong Hình 2.7, điều này thể hiện sự chuyển dịch căn bản trong tư tưởng cốt lõi về xây dựng Agent. Chủ nghĩa biểu tượng cố gắng mã hóa tri thức của con người một cách tường minh cho máy, còn thuyết liên kết cố gắng tạo ra những cỗ máy có thể học tri thức như con người.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-5.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.7 So sánh mô hình chủ nghĩa biểu tượng và thuyết liên kết</p>
</div>

Sự trỗi dậy của thuyết liên kết, đặc biệt là thành công của học sâu trong thế kỷ 21, đã mang lại cho Agent năng lực cảm nhận và nhận diện mẫu mạnh mẽ, giúp nó hiểu thế giới trực tiếp từ dữ liệu thô (như hình ảnh, âm thanh, văn bản), điều khó tưởng tượng ở thời đại chủ nghĩa biểu tượng. Tuy nhiên, làm thế nào để Agent học được cách đưa ra quyết định tuần tự tối ưu trong tương tác động với môi trường lại cần một mô hình học khác bổ sung.

### 2.4.2 Agent dựa trên học tăng cường

Thuyết liên kết chủ yếu giải quyết bài toán cảm nhận (ví dụ “trong bức ảnh này có gì?”), nhưng nhiệm vụ cốt lõi hơn của Agent là ra quyết định (ví dụ “trong tình huống này, tôi nên làm gì?”). **Học tăng cường (Reinforcement Learning, RL)** chính là mô hình học chuyên giải quyết bài toán quyết định tuần tự. Nó không học trực tiếp từ tập dữ liệu tĩnh đã gán nhãn, mà thông qua tương tác trực tiếp giữa Agent và môi trường, học trong “thử và sai” cách tối đa hóa lợi ích dài hạn của mình.

Lấy AlphaGo làm ví dụ, quá trình học tự đấu cốt lõi của nó chính là biểu hiện kinh điển của học tăng cường<sup>[9]</sup>. Trong quá trình này, AlphaGo (Agent) quan sát bố cục hiện tại của bàn cờ (trạng thái môi trường), quyết định vị trí đặt quân tiếp theo (hành động). Sau khi một ván cờ kết thúc, dựa trên kết quả thắng thua, nó nhận được một tín hiệu rõ ràng: thắng là phần thưởng dương, thua là phần thưởng âm. Qua hàng triệu ván tự đấu như vậy, AlphaGo không ngừng điều chỉnh chiến lược nội tại, dần học được trong thế cờ nào nên chọn hành động nào để có khả năng dẫn tới chiến thắng cuối cùng cao nhất. Quá trình này hoàn toàn tự chủ, không phụ thuộc vào hướng dẫn trực tiếp từ kỳ phổ của con người.

Cơ chế học thông qua tương tác với môi trường, tối ưu hành vi của mình theo tín hiệu phản hồi chính là khung cốt lõi của học tăng cường. Dưới đây chúng ta sẽ phân tích chi tiết các yếu tố cấu thành cơ bản và mô hình làm việc của nó.

Khung học tăng cường có thể được mô tả bằng vài yếu tố cốt lõi:

- **Agent**: người học và người ra quyết định. Trong ví dụ AlphaGo, đó là chương trình ra quyết định của nó.
- **Môi trường (Environment)**: mọi thứ bên ngoài Agent, là đối tượng mà Agent tương tác. Với AlphaGo, đó là luật cờ vây và đối thủ.
- **Trạng thái (State, S)**: mô tả cụ thể về môi trường tại một thời điểm, là căn cứ để Agent ra quyết định. Ví dụ, vị trí hiện tại của tất cả quân cờ trên bàn.
- **Hành động (Action, A)**: thao tác mà Agent có thể thực hiện dựa trên trạng thái hiện tại. Ví dụ, đặt một quân vào một vị trí hợp lệ trên bàn cờ.
- **Phần thưởng (Reward, R)**: tín hiệu vô hướng mà môi trường phản hồi cho Agent sau khi nó thực hiện một hành động, dùng để đánh giá hành động đó tốt hay xấu trong trạng thái cụ thể. Ví dụ, sau khi một ván cờ kết thúc, thắng nhận phần thưởng +1, thua nhận -1.

Dựa trên các yếu tố cốt lõi trên, Agent học tăng cường lặp liên tục trong một vòng lặp kín “cảm nhận - hành động - học”, mô hình làm việc được thể hiện trong Hình 2.8.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-6.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.8 Vòng lặp tương tác cốt lõi của học tăng cường</p>
</div>

Các bước cụ thể của vòng lặp này như sau:

1. Tại bước thời gian t, Agent quan sát trạng thái hiện tại của môi trường $S_{t}$.
2. Dựa trên trạng thái $S_{t}$, Agent chọn một hành động $A_{t}$ theo **chiến lược (Policy, π)** nội tại của mình và thực thi nó. Chiến lược về bản chất là một ánh xạ từ trạng thái sang hành động, định nghĩa cách hành xử của Agent.
3. Sau khi nhận hành động $A_{t}$, môi trường chuyển sang trạng thái mới $S_{t+1}$.
4. Đồng thời, môi trường phản hồi cho Agent một phần thưởng tức thời $R_{t+1}$.
5. Agent dùng phản hồi này (trạng thái mới $S_{t+1}$ và phần thưởng $R_{t+1}$) để cập nhật và tối ưu chiến lược nội tại, nhằm ra quyết định tốt hơn trong tương lai. Quá trình cập nhật này chính là học.

Mục tiêu học của Agent không phải tối đa hóa phần thưởng tức thời của một bước thời gian, mà là tối đa hóa **phần thưởng tích lũy (Cumulative Reward)** từ thời điểm hiện tại đến tương lai, còn gọi là **lợi tức (Return)**. Điều này có nghĩa Agent cần có “tầm nhìn xa”, đôi khi phải hy sinh phần thưởng tức thời hiện tại để có phần thưởng lớn hơn trong tương lai (ví dụ chiến lược “bỏ quân” trong cờ vây). Qua việc không ngừng khám phá, thu thập phản hồi và tối ưu chiến lược trong vòng lặp trên, cuối cùng Agent có thể học được cách tự chủ ra quyết định và lập kế hoạch dài hạn trong môi trường động phức tạp.

### 2.4.3 Tiền huấn luyện dựa trên dữ liệu quy mô lớn

Học tăng cường mang lại cho Agent năng lực học chiến lược ra quyết định từ tương tác, nhưng việc này thường cần lượng lớn dữ liệu tương tác dành riêng cho nhiệm vụ cụ thể, khiến Agent thiếu tri thức tiên nghiệm khi bắt đầu học, phải xây dựng hiểu biết về nhiệm vụ từ con số 0. Dù là tri thức thông thường mà chủ nghĩa biểu tượng cố mã hóa thủ công, hay tri thức nền mà con người dựa vào khi ra quyết định, đều thiếu vắng trong Agent RL. Làm thế nào để Agent có được hiểu biết rộng về thế giới trước khi bắt đầu học nhiệm vụ cụ thể? Lời giải cho vấn đề này cuối cùng xuất hiện trong lĩnh vực **xử lý ngôn ngữ tự nhiên (Natural Language Processing, NLP)**, cốt lõi là **tiền huấn luyện (Pre-training)** dựa trên dữ liệu quy mô lớn.

**Từ nhiệm vụ cụ thể đến mô hình tổng quát**

Trước khi mô hình tiền huấn luyện xuất hiện, các mô hình xử lý ngôn ngữ tự nhiên truyền thống thường được huấn luyện độc lập từ con số 0 cho một nhiệm vụ cụ thể duy nhất (như phân tích cảm xúc, dịch máy) trên tập dữ liệu quy mô vừa và nhỏ được gán nhãn chuyên dụng. Mô hình này dẫn tới vài vấn đề: tri thức của mô hình hẹp, khó tổng quát hóa tri thức học được ở một nhiệm vụ sang nhiệm vụ khác, và mỗi nhiệm vụ mới đều cần tiêu tốn nhiều nhân lực để gán nhãn dữ liệu. Việc đề xuất mô hình tiền huấn luyện và tinh chỉnh (Pre-training, Fine-tuning) đã thay đổi hoàn toàn tình trạng này. Tư tưởng cốt lõi gồm hai bước:

1. **Giai đoạn tiền huấn luyện**: trước tiên huấn luyện một mô hình mạng nơ-ron siêu lớn trên một kho ngữ liệu tổng quát chứa dữ liệu văn bản khổng lồ cấp Internet, bằng cách **học tự giám sát (Self-supervised Learning)**. Mục tiêu của giai đoạn này không phải hoàn thành bất kỳ nhiệm vụ cụ thể nào, mà là học quy luật nội tại của bản thân ngôn ngữ, cấu trúc ngữ pháp, tri thức sự thật và logic ngữ cảnh. Mục tiêu phổ biến nhất là “dự đoán từ tiếp theo”.
2. **Giai đoạn tinh chỉnh**: sau khi hoàn thành tiền huấn luyện, mô hình đã học được tri thức phong phú liên quan đến tập dữ liệu. Sau đó, với một nhiệm vụ hạ nguồn cụ thể, chỉ cần dùng một lượng nhỏ dữ liệu gán nhãn của nhiệm vụ đó để tinh chỉnh mô hình, là có thể khiến mô hình thích ứng với nhiệm vụ tương ứng.

Như trong Hình 2.9, quy trình đầy đủ của tiền huấn luyện và tinh chỉnh được thể hiện trực quan: dữ liệu văn bản tổng quát qua học tự giám sát tạo thành mô hình nền, sau đó được tinh chỉnh bằng dữ liệu nhiệm vụ cụ thể, cuối cùng thích ứng với các nhiệm vụ hạ nguồn.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-7.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.9 Sơ đồ mô hình “tiền huấn luyện - tinh chỉnh”</p>
</div>

**Sự ra đời của mô hình ngôn ngữ lớn và năng lực nổi sinh**

Thông qua tiền huấn luyện trên hàng nghìn tỷ văn bản, trọng số mạng nơ-ron của mô hình ngôn ngữ lớn thực tế đã xây dựng một mô hình ẩn, được nén cao độ, về tri thức thế giới. Nó giải quyết vấn đề “nút cổ chai thu nhận tri thức” khó khăn nhất của thời đại chủ nghĩa biểu tượng theo một cách hoàn toàn mới. Điều đáng ngạc nhiên hơn là khi quy mô mô hình (số tham số, lượng dữ liệu, lượng tính toán) vượt qua một ngưỡng nào đó, chúng bắt đầu thể hiện những **năng lực nổi sinh (Emergent Abilities)** không được huấn luyện trực tiếp và nằm ngoài dự đoán, ví dụ:

- **Học trong ngữ cảnh (In-context Learning)**: không cần điều chỉnh trọng số mô hình, chỉ cần cung cấp **một vài ví dụ (Few-shot)** hoặc thậm chí **không ví dụ nào (Zero-shot)** trong đầu vào, mô hình đã có thể hiểu và hoàn thành nhiệm vụ mới.
- **Suy luận chuỗi suy nghĩ (Chain-of-Thought)**: bằng cách dẫn dắt mô hình xuất ra quá trình suy luận từng bước trước khi trả lời câu hỏi phức tạp, có thể nâng cao rõ rệt độ chính xác của nó trên các nhiệm vụ suy luận logic, số học và tri thức thông thường.

Sự xuất hiện của những năng lực này đánh dấu LLM không còn chỉ là một mô hình ngôn ngữ, nó đã tiến hóa thành một thành phần vừa mang vai trò cơ sở tri thức khổng lồ vừa mang vai trò bộ máy suy luận tổng quát.

Đến đây, trong dòng sông dài lịch sử phát triển Agent, vài mảnh ghép công nghệ then chốt đã lần lượt xuất hiện: chủ nghĩa biểu tượng cung cấp khung suy luận logic, thuyết liên kết và học tăng cường cung cấp năng lực học và ra quyết định, còn mô hình ngôn ngữ lớn cung cấp tri thức thế giới và năng lực suy luận tổng quát có được qua tiền huấn luyện, chưa từng có trước đây. Mục tiếp theo, chúng ta sẽ thấy những công nghệ này được hòa vào nhau như thế nào trong thiết kế Agent hiện đại.

### 2.4.4 Agent dựa trên mô hình ngôn ngữ lớn

Với sự phát triển nhanh chóng của công nghệ mô hình ngôn ngữ lớn, Agent lấy LLM làm lõi đã trở thành mô hình mới của lĩnh vực trí tuệ nhân tạo. Nó không chỉ có thể hiểu và sinh ngôn ngữ của con người, quan trọng hơn, có thể thông qua tương tác với môi trường để tự chủ cảm nhận, lập kế hoạch, ra quyết định và thực thi nhiệm vụ.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-8.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.10 Kiến trúc các thành phần cốt lõi của Agent do LLM dẫn dắt</p>
</div>

Như đã nêu ở chương một, tương tác giữa Agent và môi trường có thể được trừu tượng hóa thành một vòng lặp cốt lõi. Agent do LLM dẫn dắt hoàn thành nhiệm vụ thông qua một quy trình vòng lặp kín, lặp liên tục, trong đó nhiều mô-đun phối hợp hoạt động. Quy trình tuân theo kiến trúc trong Hình 2.10, các bước cụ thể như sau:

1. **Cảm nhận (Perception)**: quy trình bắt đầu từ **mô-đun cảm nhận (Perception Module)**. Nó nhận đầu vào thô từ **môi trường bên ngoài (Environment)** thông qua cảm biến, tạo thành **quan sát (Observation)**. Những thông tin quan sát này (như chỉ thị của người dùng, dữ liệu API trả về hoặc thay đổi trạng thái môi trường) là điểm khởi đầu cho quyết định của Agent, sau khi xử lý sẽ được truyền tới giai đoạn suy nghĩ.
2. **Suy nghĩ (Thought)**: đây là lõi nhận thức của Agent, tương ứng với sự phối hợp giữa **mô-đun lập kế hoạch (Planning Module)** và **mô hình ngôn ngữ lớn (LLM)** trong hình.
   - **Lập kế hoạch và phân rã**: trước tiên, mô-đun lập kế hoạch nhận thông tin quan sát và xây dựng chiến lược cấp cao. Thông qua các cơ chế như **phản tư (Reflection)** và **tự phê phán (Self-criticism)**, nó phân rã mục tiêu vĩ mô thành những bước cụ thể hơn, có thể thực thi.
   - **Suy luận và ra quyết định**: sau đó, **LLM** với vai trò trung tâm nhận chỉ thị từ mô-đun lập kế hoạch, và tương tác với **mô-đun bộ nhớ (Memory)** để tích hợp thông tin lịch sử. LLM thực hiện suy luận sâu, cuối cùng quyết định thao tác cụ thể cần thực thi ở bước tiếp theo, thường được thể hiện dưới dạng một **lời gọi công cụ (Tool Call)**.
3. **Hành động (Action)**: sau khi hoàn tất quyết định, bước vào giai đoạn hành động, do **mô-đun thực thi (Execution Module)** phụ trách. Chỉ thị gọi công cụ do LLM sinh ra được gửi tới mô-đun thực thi. Mô-đun này phân tích chỉ thị, chọn và gọi công cụ phù hợp từ **hộp công cụ (Tool Use)** (như trình thực thi mã, công cụ tìm kiếm, API, v.v.) để tương tác với môi trường hoặc thực thi nhiệm vụ. Tương tác thực tế với môi trường này chính là **hành động (Action)** của Agent.
4. **Quan sát (Observation) và vòng lặp**: hành động sẽ thay đổi trạng thái môi trường và sinh ra kết quả.
   - Sau khi công cụ thực thi, nó trả về một **kết quả công cụ (Tool Result)** cho LLM, đây là phản hồi trực tiếp về hiệu quả của hành động. Đồng thời, hành động của Agent thay đổi môi trường, từ đó sinh ra một **trạng thái môi trường** hoàn toàn mới.
   - “Kết quả công cụ” và “trạng thái môi trường mới” cùng tạo thành một **quan sát (Observation)** hoàn toàn mới. Quan sát mới này lại được mô-đun cảm nhận bắt lấy, đồng thời LLM **cập nhật bộ nhớ (Memory Update)** theo kết quả hành động, từ đó khởi động vòng lặp “cảm nhận - suy nghĩ - hành động” tiếp theo.

Cơ chế phối hợp mô-đun hóa và vòng lặp lặp liên tục này tạo thành quy trình làm việc cốt lõi để Agent do LLM dẫn dắt giải quyết vấn đề phức tạp.



### 2.4.5 Tổng quan các mốc phát triển then chốt của Agent

Lịch sử phát triển của Agent AI không phải một con đường thẳng duy nhất, mà là quá trình đan xen, cạnh tranh và hòa hợp giữa vài trường phái tư tưởng cốt lõi kéo dài hơn nửa thế kỷ. Hiểu quá trình này giúp chúng ta thấy được nguồn gốc sâu xa của mô hình kiến trúc Agent hiện nay.

Trong đó, chủ yếu có ba trào lưu tư tưởng dẫn dắt mô hình nghiên cứu ở các thời kỳ khác nhau:

1. **Chủ nghĩa biểu tượng (Symbolism)**: đại diện bởi các nhà tiên phong như **Herbert A. Simon**, **Marvin Minsky**, cho rằng cốt lõi của trí tuệ là thao tác trên biểu tượng và suy luận logic. Tư tưởng này sản sinh ra SHRDLU có thể hiểu chỉ thị ngôn ngữ tự nhiên, các hệ chuyên gia do tri thức dẫn dắt, và máy tính “Deep Blue” thành công lớn trong lĩnh vực cờ vua.
2. **Thuyết liên kết (Connectionism)**: lấy cảm hứng từ việc mô phỏng mạng nơ-ron của não. Dù phát triển ban đầu bị hạn chế, dưới sự thúc đẩy của các nhà nghiên cứu như **Geoffrey Hinton**, thuật toán lan truyền ngược đã đặt nền tảng cho sự phục hưng của mạng nơ-ron. Cuối cùng, khi kỷ nguyên học sâu đến, tư tưởng này trở thành chủ lưu hiện nay qua các mô hình như mạng nơ-ron tích chập, Transformer.
3. **Chủ nghĩa hành vi (Behaviorism)**: nhấn mạnh Agent học chiến lược tối ưu thông qua tương tác và thử sai với môi trường, phiên bản hiện đại của nó là học tăng cường. Từ TD-Gammon thời kỳ đầu đến AlphaGo kết hợp với học sâu và đánh bại các kỳ thủ hàng đầu của con người, trường phái này mang lại cho Agent năng lực học hành vi ra quyết định phức tạp từ kinh nghiệm.

Bước vào những năm 2020, các trường phái tư tưởng này hòa vào nhau sâu sắc theo cách chưa từng có. Các mô hình ngôn ngữ lớn đại diện bởi dòng GPT, bản thân là sản phẩm của thuyết liên kết, lại trở thành “bộ não” cốt lõi thực thi suy luận biểu tượng, gọi công cụ và lập kế hoạch ra quyết định, tạo thành kiến trúc Agent hiện đại kết hợp thần kinh - biểu tượng. Để nhìn lại một cách hệ thống mạch phát triển này, Hình 2.11 dưới đây sắp xếp những lý thuyết, dự án và sự kiện then chốt trong lịch sử phát triển Agent AI từ những năm 1950 đến nay, mang lại cho độc giả một cái nhìn tổng quan rõ ràng, như một sự đọng lại tri thức của chương này.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-9.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.11 Dòng thời gian tiến hóa phát triển của Agent (chưa đầy đủ)</p>
</div>

Nhờ những đột phá của mô hình ngôn ngữ lớn, ngăn xếp công nghệ Agent thể hiện mức độ sôi động và đa dạng chưa từng có. Hình 2.12 thể hiện toàn cảnh một ngăn xếp công nghệ điển hình của lĩnh vực AI Agent hiện nay, bao quát các khâu từ mô hình tầng dưới đến ứng dụng tầng trên.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/2-figures/1757246501849-10.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 2.12 Tổng quan ngăn xếp công nghệ AI Agent</p>
</div>

Sơ đồ ngăn xếp công nghệ này do công ty Letta công bố tháng 11 năm 2024<sup>[10]</sup>, nó phân tầng và phân loại các công cụ, nền tảng và dịch vụ liên quan đến Agent AI, mang lại tài liệu tham khảo quý giá để chúng ta hiểu bố cục thị trường hiện tại và lựa chọn công nghệ.

## 2.5 Tóm tắt chương

Chương này đã nhìn lại mạch lịch sử phát triển của Agent, khám phá quá trình tư tưởng cốt lõi của nó từ khi ra đời đến khi tiến hóa, nội dung bao quát vài cuộc cách mạng mô hình then chốt trong lĩnh vực trí tuệ nhân tạo:

- **Sự khám phá và hạn chế của chủ nghĩa biểu tượng**: xuất phát từ thời kỳ cổ điển của trí tuệ nhân tạo, chương này trình bày cách các Agent sơ khai đại diện bởi hệ chuyên gia cố gắng mô phỏng trí tuệ thông qua “tri thức + suy luận”. Qua việc tự tay xây dựng một chatbot dựa trên quy tắc, chúng ta cảm nhận sâu sắc biên giới năng lực của mô hình này và những thách thức căn bản mà nó đối mặt.
- **Mầm mống của tư tưởng trí tuệ phân tán**: thảo luận lý thuyết “xã hội tâm trí” của Marvin Minsky. Tư tưởng mang tính cách mạng này cho thấy trí tuệ tổng thể phức tạp có thể nổi sinh từ tương tác của những đơn vị cục bộ đơn giản, mang lại gợi mở triết học quan trọng cho nghiên cứu hệ thống đa Agent sau này.
- **Sự tiến hóa của mô hình học**: chứng kiến sự thay đổi căn bản trong cách Agent thu nhận năng lực. Từ việc thuyết liên kết mang lại cho Agent năng lực cảm nhận thế giới, đến học tăng cường giúp nó học cách ra quyết định tối ưu trong tương tác với môi trường, rồi đến mô hình ngôn ngữ lớn (LLM) dựa trên tiền huấn luyện dữ liệu quy mô lớn mang lại tri thức thế giới và năng lực suy luận tổng quát chưa từng có.
- **Sự ra đời của Agent hiện đại**: cuối cùng, chúng ta phân tích Agent do LLM dẫn dắt. Qua phân tích các thành phần cốt lõi (mô hình, bộ nhớ, lập kế hoạch, công cụ, v.v.) và nguyên lý hoạt động, chúng ta hiểu được các tư tưởng công nghệ trong lịch sử đã được hòa hợp về mặt kỹ thuật như thế nào trong kiến trúc Agent hiện đại.

Qua việc học chương này, chúng ta không chỉ hiểu Agent hiện đại được giới thiệu ở chương một đến từ đâu, mà còn xây dựng được một khung nhận thức vĩ mô về tiến hóa công nghệ Agent. Có thể thấy, sự phát triển của Agent không phải là lặp lại kỹ thuật đơn giản, mà là một cuộc cách mạng tư tưởng về cách định nghĩa “trí tuệ”, thu nhận “tri thức”, và “ra quyết định”.

Vì lõi của Agent hiện đại là mô hình ngôn ngữ lớn, nên việc hiểu sâu nguyên lý nền tảng của nó là vô cùng quan trọng. Chương tiếp theo sẽ tập trung vào bản thân mô hình ngôn ngữ lớn, thảo luận các khái niệm cơ bản, đặt nền tảng vững chắc cho những ứng dụng nâng cao trong hệ thống đa Agent sau này.



## Bài tập

> **Gợi ý**: Một số bài tập dưới đây không có đáp án chuẩn, nhằm giúp người học xây dựng hiểu biết hệ thống về lịch sử phát triển Agent, và bồi dưỡng nhãn quan công nghệ “lấy sử làm gương”.

1. Giả thuyết hệ thống biểu tượng vật lý<sup>[1]</sup> là nền tảng lý thuyết của thời đại chủ nghĩa biểu tượng. Hãy phân tích:

   - “Luận điểm đủ” và “luận điểm cần” của giả thuyết này có ý nghĩa gì?
   - Kết hợp nội dung chương này, giải thích những vấn đề nào mà Agent biểu tượng gặp phải trong thực tiễn đã đặt thách thức cho tính “đủ” của giả thuyết?
   - Agent do mô hình ngôn ngữ lớn dẫn dắt có phù hợp với giả thuyết hệ thống biểu tượng vật lý không?

2. Hệ chuyên gia MYCIN<sup>[2]</sup> đạt thành công đáng chú ý trong lĩnh vực chẩn đoán y tế, nhưng cuối cùng không được ứng dụng quy mô lớn trong thực hành lâm sàng. Hãy suy nghĩ:

   > **Gợi ý**: có thể phân tích từ nhiều góc độ như kỹ thuật, đạo đức, pháp lý, mức độ chấp nhận của người dùng

   - Ngoài “nút cổ chai thu nhận tri thức” và “tính dễ tổn thương” đã nêu trong chương, còn yếu tố nào có thể đã cản trở việc áp dụng hệ chuyên gia trong các lĩnh vực rủi ro cao như y tế?
   - Nếu bây giờ bạn thiết kế một Agent chẩn đoán y tế, bạn sẽ thiết kế hệ thống như thế nào để khắc phục hạn chế của MYCIN?
   - Trong những lĩnh vực dọc nào, hệ chuyên gia dựa trên quy tắc đến nay vẫn là lựa chọn tốt hơn học sâu? Hãy nêu ví dụ.

3. Ở mục 2.2, chúng ta đã hiện thực một phiên bản đơn giản của chatbot ELIZA. Hãy tiếp tục mở rộng trên cơ sở đó:

   > **Gợi ý**: đây là bài thực hành, nên thực sự viết mã

   - Thêm 3-5 quy tắc mới cho ELIZA, để nó xử lý được nhiều kịch bản hội thoại đa dạng hơn (như nói về công việc, học tập, sở thích, v.v.)
   - Hiện thực một chức năng “ghi nhớ ngữ cảnh” đơn giản: để ELIZA ghi nhớ những thông tin then chốt người dùng đề cập trong hội thoại (như tên, tuổi, nghề nghiệp), và trích dẫn lại trong các lượt hội thoại sau
   - So sánh ELIZA đã mở rộng của bạn với [ChatGPT](https://chatgpt.com/), liệt kê ít nhất 3 khác biệt bản chất trên các chiều khác nhau
   - Vì sao phương pháp dựa trên quy tắc gặp vấn đề “bùng nổ tổ hợp” khi xử lý hội thoại mở và khó mở rộng, bảo trì? Có thể dùng phương pháp toán học để giải thích không?

4. Marvin Minsky trong lý thuyết “xã hội tâm trí”<sup>[7]</sup> đã đưa ra một quan điểm mang tính cách mạng: trí tuệ bắt nguồn từ sự cộng tác của lượng lớn Agent đơn giản, chứ không từ một hệ thống hoàn hảo đơn nhất.

   - Trong ví dụ “xây tháp khối gỗ” ở Hình 2.6, nếu Agent `GRASP` đột nhiên hỏng, toàn bộ hệ thống sẽ ra sao? Ưu nhược điểm của kiến trúc phi tập trung này là gì?
   - So sánh lý thuyết “xã hội tâm trí” với một số hệ thống đa Agent hiện nay (như [CAMEL-Workforce](https://docs.camel-ai.org/key_modules/workforce), [MetaGPT](https://github.com/FoundationAgents/MetaGPT), [CrewAI](https://github.com/crewAIInc/crewAI)), giữa chúng có những liên hệ và khác biệt nào?
   - Marvin Minsky cho rằng Agent có thể là những quá trình đơn giản “vô tâm”, trong khi mô hình ngôn ngữ lớn và Agent hiện nay thường sở hữu năng lực suy luận mạnh mẽ. Điều này có nghĩa lý thuyết “xã hội tâm trí” không còn phù hợp trong thời đại mô hình ngôn ngữ lớn?

5. Học tăng cường và học có giám sát là hai mô hình học khác nhau. Hãy phân tích:

   - Dùng ví dụ AlphaGo để giải thích cơ chế “học thử sai” của học tăng cường hoạt động như thế nào
   - Vì sao học tăng cường đặc biệt phù hợp với bài toán quyết định tuần tự? Nó khác biệt bản chất gì so với học có giám sát về nhu cầu dữ liệu?
   - Giả sử cần huấn luyện một Agent biết chơi game Super Mario. Nếu lần lượt dùng học có giám sát và học tăng cường, mỗi cách cần dữ liệu gì? Cách nào phù hợp hơn với nhiệm vụ này?
   - Trong quá trình huấn luyện mô hình ngôn ngữ lớn, học tăng cường đóng vai trò then chốt gì?

6. Mô hình tiền huấn luyện - tinh chỉnh là đột phá quan trọng của lĩnh vực trí tuệ nhân tạo hiện đại. Hãy suy nghĩ sâu:

   - Vì sao nói tiền huấn luyện đã giải quyết vấn đề “nút cổ chai thu nhận tri thức” của thời đại chủ nghĩa biểu tượng? Giữa chúng có khác biệt bản chất gì về cách biểu diễn tri thức?
   - Tri thức của mô hình tiền huấn luyện phần lớn đến từ dữ liệu Internet, điều này có thể mang lại những vấn đề gì? Làm thế nào giảm thiểu những vấn đề đó?
   - Bạn nghĩ mô hình “tiền huấn luyện - tinh chỉnh” có thể bị một mô hình mới nào đó thay thế? Hay nó sẽ tồn tại lâu dài?

7. Giả sử bạn cần thiết kế một “trợ lý đánh giá mã thông minh”, có thể tự động đánh giá mã được gửi lên (Pull Request), tóm tắt logic hiện thực của mã, kiểm tra chất lượng mã, phát hiện lỗi tiềm ẩn, đưa ra gợi ý cải tiến.

   - Nếu thiết kế hệ thống này vào thời đại chủ nghĩa biểu tượng (những năm 1980), bạn sẽ hiện thực thế nào? Sẽ gặp khó khăn gì?
   - Nếu thiết kế vào thời đại học sâu chưa có mô hình ngôn ngữ lớn (khoảng năm 2015), bạn sẽ hiện thực thế nào?
   - Trong thời đại mô hình ngôn ngữ lớn và Agent hiện nay, bạn sẽ thiết kế kiến trúc Agent này như thế nào? Nó nên gồm những mô-đun nào (tham khảo Hình 2.10)?
   - So sánh phương án của ba thời đại, giải thích sự tiến hóa của công nghệ Agent đã khiến nhiệm vụ này từ “gần như bất khả thi” trở thành “khả thi” như thế nào



## Tài liệu tham khảo

[1] NEWELL A, SIMON H A. Computer science as empirical inquiry: symbols and search[J]. Communications of the ACM, 1976, 19(3): 113-126.

[2] BUCHANAN B G, SHORTLIFFE E H, ed. Rule-based expert systems: the MYCIN experiments of the Stanford Heuristic Programming Project[M]. Reading, Mass.: Addison-Wesley, 1984.

[3] WINOGRAD T. Understanding natural language[M]. New York: Academic Press, 1972.

[4] LENAT D B, GUHA R V. Cyc: a midterm report[J]. AI magazine, 1990, 11(3): 32.

[5] MCCARTHY J, HAYES P J. Some philosophical problems from the standpoint of artificial intelligence[C]//MELTZER B, MICHIE D, ed. Machine intelligence 4. Edinburgh: Edinburgh University Press, 1969: 463-502.

[6] WEIZENBAUM J. ELIZA: a computer program for the study of natural language communication between man and machine[J]. Communications of the ACM, 1966, 9(1): 36-45.

[7] MINSKY M. The society of mind[M]. New York: Simon & Schuster, 1986.

[8] RUMELHART D E, MCCLELLAND J L, PDP RESEARCH GROUP. Parallel distributed processing: explorations in the microstructure of cognition[M]. Cambridge, MA: MIT Press, 1986.

[9] SILVER D, HUANG A, MADDISON C J, ed. Mastering the game of Go with deep neural networks and tree search[J]. Nature, 2016, 529(7587): 484-489.

[10] LETTA. The AI agents stack[EB/OL]. (2024-11) [2025-09-07]. https://www.letta.com/blog/ai-agents-stack.

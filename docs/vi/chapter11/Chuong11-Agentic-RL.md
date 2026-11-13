# Chương 11: Agentic RL

## 11.1 Từ huấn luyện LLM đến Agentic RL

Trong các chương trước, chúng ta đã hiện thực nhiều mô hình Agent và giao thức giao tiếp khác nhau. Tuy nhiên, khi xử lý những nhiệm vụ phức tạp hơn, Agent thường tỏ ra không đủ tốt, nên tự nhiên sẽ nảy sinh câu hỏi: <strong>làm sao để Agent có năng lực suy luận mạnh hơn? Làm sao để Agent học cách sử dụng công cụ tốt hơn? Làm sao để Agent có thể tự cải thiện?</strong>

Đây chính là vấn đề cốt lõi mà Agentic RL (huấn luyện Agent dựa trên học tăng cường) cần giải quyết. Chương này sẽ đưa năng lực huấn luyện học tăng cường vào framework HelloAgents, giúp bạn huấn luyện được những Agent sở hữu các năng lực nâng cao như suy luận, sử dụng công cụ. Chúng ta sẽ bắt đầu từ kiến thức nền tảng về huấn luyện LLM, dần đi sâu vào các kỹ thuật thực dụng như tinh chỉnh có giám sát (Supervised Fine-Tuning, SFT), tối ưu chính sách tương đối theo nhóm (Group Relative Policy Optimization, GRPO), và cuối cùng xây dựng một pipeline huấn luyện Agent hoàn chỉnh.

### 11.1.1 Từ học tăng cường đến Agentic RL

Trong mục 2.4.2 của chương 2, chúng ta đã giới thiệu Agent dựa trên học tăng cường. Học tăng cường (Reinforcement Learning, RL) là một mô hình học tập trung vào việc giải quyết các bài toán quyết định tuần tự; thông qua tương tác trực tiếp giữa Agent và môi trường, nó học cách tối đa hóa lợi ích dài hạn trong quá trình “thử và sai”.

Bây giờ, hãy áp dụng khung này cho Agent LLM. Xét một Agent giải bài toán, nó cần trả lời câu hỏi sau:

```
Bài toán: Janet's ducks lay 16 eggs per day. She eats three for breakfast
every morning and bakes muffins for her friends every day with four.
She sells the remainder at the farmers' market daily for $2 per fresh
duck egg. How much in dollars does she make every day at the farmers' market?
```

Bài toán này cần suy luận nhiều bước: trước tiên tính số trứng Janet còn lại mỗi ngày (16 - 3 - 4 = 9), sau đó tính thu nhập của cô (9 × 2 = 18). Chúng ta có thể ánh xạ nhiệm vụ này vào khung học tăng cường:

- <strong>Agent</strong>: hệ thống suy luận dựa trên LLM
- <strong>Môi trường</strong>: bài toán và hệ thống kiểm chứng
- <strong>Trạng thái</strong>: mô tả bài toán hiện tại và các bước suy luận đã có
- <strong>Hành động</strong>: sinh bước suy luận tiếp theo hoặc đáp án cuối cùng
- <strong>Phần thưởng</strong>: đáp án có đúng không (đúng +1, sai 0)

Phương pháp học có giám sát truyền thống có ba hạn chế cốt lõi: thứ nhất, chất lượng dữ liệu quyết định hoàn toàn chất lượng huấn luyện, mô hình chỉ có thể bắt chước dữ liệu huấn luyện, khó vượt qua; thứ hai, thiếu năng lực khám phá, chỉ có thể học thụ động các con đường do con người cung cấp; thứ ba, khó tối ưu mục tiêu dài hạn, không thể tối ưu chính xác quá trình trung gian của suy luận nhiều bước.

Học tăng cường mang lại những khả năng mới. Bằng cách để Agent tự chủ sinh nhiều đáp án ứng viên và nhận phần thưởng theo tính đúng đắn, nó có thể học được con đường suy luận nào tốt hơn, bước nào là then chốt, thậm chí phát hiện phương pháp giải tốt hơn cả chú thích của con người<sup>[8]</sup>. Đây chính là tư tưởng cốt lõi của Agentic RL: xem LLM như một chính sách có thể học, nhúng vào vòng lặp tri giác – quyết định – thực thi của Agent, và tối ưu hiệu năng trên nhiệm vụ nhiều bước bằng học tăng cường.

### 11.1.2 Toàn cảnh huấn luyện LLM

Trước khi đi sâu vào Agentic RL, chúng ta cần hiểu trước toàn bộ quy trình huấn luyện LLM. Sự ra đời của một LLM mạnh (như GPT, Claude, Qwen) thường phải trải qua hai giai đoạn chính: tiền huấn luyện (Pretraining) và hậu huấn luyện (Post-training). Như Hình 11.1 cho thấy, hai giai đoạn này tạo nên con đường tiến hóa hoàn chỉnh của LLM từ “mô hình ngôn ngữ” đến “trợ lý hội thoại”.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-1.png" alt="" width="85%"/>
  <p>Hình 11.1 Toàn cảnh huấn luyện LLM</p>
</div>

<strong>Giai đoạn tiền huấn luyện</strong> là giai đoạn đầu tiên của huấn luyện LLM, mục tiêu là để mô hình học các quy luật cơ bản của ngôn ngữ và kiến thức về thế giới. Giai đoạn này sử dụng khối lượng văn bản khổng lồ (thường ở mức vài TB), huấn luyện mô hình theo cách học tự giám sát: tín hiệu huấn luyện đến từ chính văn bản, ví dụ dự đoán từ tiếp theo dựa trên ngữ cảnh phía trước. Nhiệm vụ tiền huấn luyện phổ biến nhất là mô hình ngôn ngữ nhân quả (Causal Language Modeling), còn gọi là dự đoán từ tiếp theo (Next Token Prediction).

Cho một chuỗi văn bản $x_1, x_2, ..., x_t$, mô hình cần dự đoán từ tiếp theo $x_{t+1}$:

$$
\mathcal{L}_{\text{pretrain}} = -\sum_{t=1}^{T} \log P(x_t | x_1, x_2, ..., x_{t-1}; \theta)
$$

Trong đó $\theta$ là tham số mô hình, $P(x_t | x_1, ..., x_{t-1}; \theta)$ là phân phối xác suất của từ tiếp theo do mô hình dự đoán, mục tiêu là tối thiểu hóa log-likelihood âm, tức tối đa hóa xác suất dự đoán đúng từ. Ví dụ, cho văn bản "The cat sat on the", mô hình cần dự đoán từ tiếp theo nhiều khả năng nhất là "mat". Thông qua việc huấn luyện như vậy trên khối lượng văn bản khổng lồ, mô hình dần học được quy tắc ngữ pháp (thứ tự từ nào là hợp lệ), kiến thức ngữ nghĩa (quan hệ giữa các từ), kiến thức về thế giới (thông tin thực tế về thế giới) và năng lực suy luận cơ bản.

Đặc điểm của giai đoạn tiền huấn luyện là lượng dữ liệu khổng lồ, chi phí tính toán cao; thứ được học là năng lực hiểu và sinh ngôn ngữ tổng quát; quá trình huấn luyện thường dùng mục tiêu tự giám sát, tự động xây dựng tín hiệu giám sát từ văn bản chưa gán nhãn.

<strong>Giai đoạn hậu huấn luyện</strong> thì nhằm giải quyết những thiếu sót của mô hình tiền huấn luyện. Mô hình sau tiền huấn luyện tuy đã có năng lực ngôn ngữ mạnh, nhưng nó chỉ là mô hình “dự đoán từ tiếp theo”, chưa biết cách tuân theo chỉ dẫn của con người, sinh ra câu trả lời hữu ích, vô hại, trung thực, từ chối các yêu cầu không phù hợp, và tương tác với con người theo cách hội thoại. Giai đoạn hậu huấn luyện chính là để giải quyết những vấn đề này, giúp mô hình căn chỉnh với sở thích và giá trị của con người.

Hậu huấn luyện thường gồm ba bước. Bước đầu tiên là <strong>tinh chỉnh có giám sát (SFT)</strong><sup>[15]</sup>, mục tiêu là để mô hình học cách tuân theo chỉ dẫn và định dạng hội thoại. Dữ liệu huấn luyện là các cặp (prompt, completion), mục tiêu huấn luyện tương tự tiền huấn luyện, vẫn là tối đa hóa xác suất của đầu ra đúng:

$$
\mathcal{L}_{\text{SFT}} = -\sum_{i=1}^{N} \log P(y_i | x_i; \theta)
$$

Trong đó $x_i$ là prompt đầu vào, $y_i$ là đầu ra mong đợi, $N$ là số mẫu huấn luyện. Đặc điểm của SFT là lượng dữ liệu nhỏ hơn, cần gán nhãn thủ công, hiệu quả nhanh, chủ yếu học định dạng nhiệm vụ và năng lực cơ bản.

Bước thứ hai là <strong>xây dựng mô hình phần thưởng (RM)</strong>. Mô hình sau SFT tuy đã biết tuân theo chỉ dẫn, nhưng chất lượng câu trả lời sinh ra không đồng đều. Chúng ta cần một cách để đánh giá chất lượng câu trả lời, đó chính là vai trò của mô hình phần thưởng<sup>[13,14]</sup>. Dữ liệu huấn luyện của mô hình phần thưởng là dữ liệu so sánh sở thích, gồm hai câu trả lời cho cùng một câu hỏi, một câu tốt hơn (chosen), một câu kém hơn (rejected). Mục tiêu huấn luyện của mô hình phần thưởng là học sở thích của con người:

$$
\mathcal{L}_{\text{RM}} = -\mathbb{E}_{(x, y_w, y_l)} [\log \sigma(r_\phi(x, y_w) - r_\phi(x, y_l))]
$$

Trong đó $r_\phi(x, y)$ là mô hình phần thưởng, đầu vào là cặp (prompt, câu trả lời), đầu ra là điểm chất lượng; $y_w$ là câu trả lời tốt hơn (chosen), $y_l$ là câu trả lời kém hơn (rejected), $\sigma$ là hàm sigmoid, mục tiêu là để mô hình phần thưởng cho câu trả lời tốt hơn điểm cao hơn.

Bước thứ ba là <strong>tinh chỉnh bằng học tăng cường</strong>. Khi đã có mô hình phần thưởng, chúng ta có thể dùng học tăng cường để tối ưu mô hình ngôn ngữ, giúp nó sinh ra câu trả lời chất lượng cao hơn. Thuật toán kinh điển nhất là PPO (Proximal Policy Optimization)<sup>[1]</sup>, mục tiêu huấn luyện là:

$$
J_{\text{PPO}} = \mathbb{E}_{x, y \sim \pi_\theta} [r_\phi(x, y)] - \beta \cdot D_{KL}(\pi_\theta || \pi_{\text{ref}})
$$

Trong đó $\pi_\theta$ là chính sách hiện tại, tức mô hình ngôn ngữ, $\pi_{\text{ref}}$ là chính sách tham chiếu, trong kịch bản này có thể là mô hình SFT, $r_\phi(x, y)$ là điểm của mô hình phần thưởng, $D_{KL}$ là phân kỳ KL, nhằm ngăn mô hình lệch quá xa, $\beta$ là hệ số cân bằng. Ý nghĩa của hàm mục tiêu này là: tối đa hóa phần thưởng, đồng thời không lệch quá xa mô hình gốc.

RLHF (Reinforcement Learning from Human Feedback) truyền thống<sup>[5]</sup> cần lượng lớn dữ liệu sở thích gán nhãn thủ công, chi phí cao. Để giảm chi phí, các nhà nghiên cứu đề xuất RLAIF (Reinforcement Learning from AI Feedback)<sup>[7]</sup>, dùng mô hình AI mạnh (như GPT-4) thay thế người gán nhãn. Quy trình làm việc của RLAIF là: dùng mô hình SFT sinh nhiều câu trả lời ứng viên, dùng mô hình AI mạnh chấm điểm và xếp hạng các câu trả lời, dùng điểm của AI để huấn luyện mô hình phần thưởng, dùng mô hình phần thưởng để học tăng cường. Thí nghiệm cho thấy hiệu quả của RLAIF gần bằng, thậm chí vượt RLHF, đồng thời chi phí giảm mạnh<sup>[11]</sup>.

### 11.1.3 Tư tưởng cốt lõi của Agentic RL

Sau khi hiểu quy trình huấn luyện nền tảng của LLM, hãy xem sự khác biệt giữa Agentic RL và các phương pháp huấn luyện truyền thống. Hậu huấn luyện truyền thống (chúng ta gọi là PBRFT: Preference-Based Reinforcement Fine-Tuning) chủ yếu tập trung tối ưu chất lượng hội thoại một lượt: cho một câu hỏi của người dùng, mô hình sinh một câu trả lời, sau đó nhận phần thưởng theo chất lượng câu trả lời. Cách này phù hợp để tối ưu trợ lý hội thoại, nhưng với các nhiệm vụ Agent cần suy luận nhiều bước, sử dụng công cụ, lập kế hoạch dài hạn thì tỏ ra bất lực.

<strong>Agentic RL</strong> là một mô hình mới, xem LLM như một chính sách có thể học, được nhúng trong một vòng lặp quyết định tuần tự. Trong khung này, Agent cần tương tác với thế giới bên ngoài trong môi trường động, thực thi nhiều bước hành động để hoàn thành nhiệm vụ phức tạp, nhận phản hồi trung gian để dẫn dắt quyết định tiếp theo, tối ưu phần thưởng tích lũy dài hạn thay vì phần thưởng một bước.

Hãy hiểu sự khác biệt này qua một ví dụ cụ thể. Trong kịch bản PBRFT, người dùng hỏi “hãy giải thích học tăng cường là gì”, mô hình sinh câu trả lời hoàn chỉnh, sau đó được cho điểm trực tiếp theo chất lượng câu trả lời. Trong kịch bản Agentic RL, người dùng yêu cầu “giúp tôi phân tích chất lượng mã của kho GitHub này”, Agent cần trải qua nhiều bước: trước tiên gọi API GitHub lấy thông tin kho, thành công lấy được cấu trúc kho và danh sách tệp, nhận phần thưởng +0.1; sau đó đọc các tệp mã chính, thành công lấy được nội dung mã, nhận phần thưởng +0.1; tiếp theo phân tích chất lượng mã hợp lý, nhận phần thưởng +0.2; cuối cùng sinh báo cáo phân tích chất lượng cao, nhận phần thưởng +0.6. Tổng phần thưởng là tích lũy của mọi bước: 1.0.

Có thể thấy, đặc trưng then chốt của Agentic RL là tương tác nhiều bước, hành động ở mỗi bước đều thay đổi trạng thái môi trường, mỗi bước đều có thể nhận phản hồi, tối ưu chất lượng hoàn thành của toàn bộ nhiệm vụ.

Học tăng cường thường dùng khung quá trình quyết định Markov (Markov Decision Process, MDP) để hình thức hóa. MDP được định nghĩa bởi bộ năm $(S, A, P, R, \gamma)$: không gian trạng thái $S$, không gian hành động $A$, hàm chuyển trạng thái $P(s'|s,a)$, hàm phần thưởng $R(s,a)$ và hệ số chiết khấu $\gamma$. Bảng dưới đây so sánh PBRFT và Agentic RL từ góc độ MDP.

<div align="center">
  <p>Bảng 11.1 So sánh PBRFT và Agentic RL</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-1.png" alt="" width="85%"/>
</div>

Về trạng thái, trạng thái $s_0$ của PBRFT chỉ gồm prompt của người dùng, khoảng thời gian $T=1$ (một bước), trạng thái không thay đổi, có thể biểu diễn là $s_0 = \text{prompt}$. Còn trạng thái $s_t$ của Agentic RL bao gồm quan sát lịch sử và ngữ cảnh, khoảng thời gian $T \gg 1$ (nhiều bước), trạng thái tiến hóa theo hành động, có thể biểu diễn là $s_t = (\text{prompt}, o_1, o_2, ..., o_t)$, trong đó $o_t$ là quan sát ở bước $t$ (như kết quả trả về từ công cụ, phản hồi môi trường, v.v.).

Về hành động, không gian hành động của PBRFT chỉ có sinh văn bản, một loại hành động duy nhất, biểu diễn là $a = y \sim \pi_\theta(y|s_0)$. Còn không gian hành động của Agentic RL bao gồm sinh văn bản, gọi công cụ, thao tác môi trường và nhiều loại khác, biểu diễn là $a_t \in \{a_t^{\text{text}}, a_t^{\text{tool}}\}$, ví dụ $a_t^{\text{text}}$ là sinh quá trình suy nghĩ hoặc câu trả lời, $a_t^{\text{tool}}$ là gọi máy tính, công cụ tìm kiếm, v.v.

Về hàm chuyển, PBRFT không có chuyển trạng thái, biểu diễn là $P(s'|s,a) = \delta(s' - s_{\text{terminal}})$. Còn trạng thái của Agentic RL thay đổi động theo hành động và môi trường, biểu diễn là $s_{t+1} \sim P(s_{t+1}|s_t, a_t)$, ví dụ sau khi gọi công cụ tìm kiếm, trạng thái sẽ chứa kết quả tìm kiếm.

Về phần thưởng, PBRFT chỉ có phần thưởng một bước $r(s_0, a)$, chỉ được trao khi nhiệm vụ kết thúc, biểu diễn là $R_{\text{PBRFT}} = r(s_0, y)$, thường do mô hình phần thưởng đưa ra: $r(s_0, y) = r_\phi(s_0, y)$. Còn Agentic RL có phần thưởng nhiều bước $r(s_t, a_t)$, có thể trao phần thưởng bộ phận ở các bước trung gian, biểu diễn là:

$$
R_{\text{Agentic}} = \sum_{t=0}^{T} \gamma^t r(s_t, a_t)
$$

Trong đó $\gamma \in [0,1]$ là hệ số chiết khấu, $r(s_t, a_t)$ có thể là phần thưởng thưa (chỉ trao khi nhiệm vụ hoàn thành, như đáp án đúng +1), phần thưởng dày (trao ở mỗi bước, như gọi công cụ thành công +0.1) hoặc phần thưởng hỗn hợp kết hợp cả hai.

Về hàm mục tiêu, PBRFT tối đa hóa phần thưởng kỳ vọng một bước:

$$
J_{\text{PBRFT}}(\theta) = \mathbb{E}_{s_0, y \sim \pi_\theta} [r(s_0, y)]
$$

Còn Agentic RL tối đa hóa phần thưởng chiết khấu tích lũy:

$$
J_{\text{Agentic}}(\theta) = \mathbb{E}_{\tau \sim \pi_\theta} \left[\sum_{t=0}^{T} \gamma^t r(s_t, a_t)\right]
$$

Trong đó $\tau = (s_0, a_0, s_1, a_1, ..., s_T)$ là quỹ đạo (trajectory) hoàn chỉnh.

Sự chuyển dịch này không chỉ là khác biệt về chi tiết kỹ thuật, mà là sự chuyển dịch căn bản về cách tư duy. Tư duy PBRFT quan tâm “làm sao để mô hình sinh ra một câu trả lời đơn lẻ tốt hơn”, tối ưu chất lượng câu trả lời, chú trọng diễn đạt ngôn ngữ, thực hiện quyết định một bước. Còn tư duy Agentic RL quan tâm “làm sao để Agent hoàn thành nhiệm vụ phức tạp”, tối ưu mức độ hoàn thành nhiệm vụ, chú trọng chiến lược hành động, thực hiện lập kế hoạch nhiều bước. Sự chuyển dịch này khiến LLM tiến hóa từ “trợ lý hội thoại” thành “Agent tự chủ”, có thể chủ động tìm kiếm thông tin, biết khi nào và sử dụng công cụ bên ngoài như thế nào, vì mục tiêu cuối cùng mà sẵn sàng thực thi những bước trung gian trông có vẻ “vòng vèo”, và học từ sai lầm.

Mục tiêu của Agentic RL là trao cho Agent LLM sáu năng lực cốt lõi, như Hình 11.2 cho thấy.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-2.png" alt="" width="85%"/>
  <p>Hình 11.2 Sáu năng lực cốt lõi của Agentic RL</p>
</div>

<strong>Suy luận (Reasoning)</strong> là quá trình rút ra kết luận một cách logic từ thông tin đã cho, là năng lực cốt lõi của Agent. Phương pháp prompt CoT truyền thống dựa vào ví dụ ít mẫu, năng lực tổng quát hóa hạn chế; SFT chỉ có thể bắt chước các mẫu suy luận trong dữ liệu huấn luyện, khó đổi mới. Ưu điểm của học tăng cường là học được chiến lược suy luận hiệu quả qua thử và sai, phát hiện những con đường suy luận không có trong dữ liệu huấn luyện, học được khi nào cần suy nghĩ sâu, khi nào có thể trả lời nhanh. Nhiệm vụ suy luận có thể được mô hình hóa như bài toán quyết định tuần tự: cho bài toán $q$, Agent cần sinh chuỗi suy luận $c = (c_1, c_2, ..., c_n)$ và đáp án cuối cùng $a$. Hàm phần thưởng thường được thiết kế là $r(q, c, a) = 1$ if $a = a^*$ else $0$, mục tiêu huấn luyện là $\max_\theta \mathbb{E}_{q, (c,a) \sim \pi_\theta} [r(q, c, a)]$. Bằng cách này, mô hình học được cách sinh chuỗi suy luận chất lượng cao, chứ không chỉ ghi nhớ đáp án.

<strong>Sử dụng công cụ (Tool Use)</strong> là năng lực Agent gọi công cụ bên ngoài để hoàn thành nhiệm vụ. Trong nhiệm vụ sử dụng công cụ, không gian hành động mở rộng thành $a_t \in \{a_t^{\text{think}}, a_t^{\text{tool}}\}$, trong đó $a_t^{\text{think}}$ là sinh quá trình suy nghĩ, $a_t^{\text{tool}} = (\text{tool\_name}, \text{arguments})$ là gọi công cụ. Học tăng cường giúp Agent học được khi nào cần dùng công cụ, chọn công cụ nào, kết hợp nhiều công cụ ra sao. Ví dụ, khi giải bài toán, Agent cần học khi nào dùng máy tính, khi nào dùng trình thông dịch mã, khi nào suy luận trực tiếp.

<strong>Bộ nhớ (Memory)</strong> là năng lực Agent giữ lại và tái sử dụng thông tin quá khứ, rất quan trọng với nhiệm vụ dài hạn. Cửa sổ ngữ cảnh của LLM có hạn, chiến lược truy xuất tĩnh (như RAG) không thể tối ưu theo nhiệm vụ. Học tăng cường giúp Agent học chiến lược quản lý bộ nhớ: quyết định thông tin nào đáng nhớ, khi nào cập nhật bộ nhớ, khi nào xóa thông tin lỗi thời. Điều này tương tự bộ nhớ làm việc của con người, chúng ta chủ động quản lý thông tin trong não, giữ lại cái quan trọng, quên cái không liên quan.

<strong>Lập kế hoạch (Planning)</strong> là năng lực xây dựng chuỗi hành động để đạt mục tiêu. CoT truyền thống là tư duy tuyến tính, không thể quay lui; kỹ thuật prompt dùng mẫu kế hoạch tĩnh, khó thích ứng tình huống mới. Học tăng cường giúp Agent học lập kế hoạch động: phát hiện chuỗi hành động hiệu quả qua thử và sai, học cân nhắc lợi ích ngắn hạn và dài hạn. Ví dụ, trong nhiệm vụ nhiều bước, Agent có thể cần thực thi trước một số bước trông có vẻ “vòng vèo”, chẳng hạn thu thập thông tin, rồi mới hoàn thành nhiệm vụ cuối cùng.

<strong>Tự cải thiện (Self-Improvement)</strong> là năng lực Agent xem lại đầu ra của chính mình, sửa lỗi và tối ưu chính sách. Học tăng cường giúp Agent học tự phản tư: nhận diện lỗi của mình, phân tích nguyên nhân thất bại, điều chỉnh chính sách. Năng lực này cho phép Agent liên tục cải thiện mà không cần can thiệp thủ công, tương tự “học từ sai lầm” của con người.

<strong>Tri giác (Perception)</strong> là năng lực hiểu thông tin đa phương thức. Ví dụ, học tăng cường có thể nâng cao năng lực suy luận thị giác, giúp mô hình học sử dụng công cụ thị giác, học lập kế hoạch thị giác. Điều này khiến Agent không chỉ hiểu văn bản mà còn hiểu và thao tác thế giới thị giác.

### 11.1.4 Thiết kế Agentic RL của HelloAgents

Sau khi hiểu tư tưởng cốt lõi của Agentic RL, hãy xem cách hiện thực những năng lực này trong framework HelloAgents.

Về lựa chọn công nghệ, chúng ta tích hợp framework TRL (Transformer Reinforcement Learning)<sup>[9]</sup>, mô hình chọn Qwen3-0.6B<sup>[10]</sup>. TRL là thư viện học tăng cường của Hugging Face, trưởng thành ổn định, chức năng đầy đủ, dễ tích hợp. Qwen3-0.6B là mô hình ngôn ngữ nhỏ của Alibaba Cloud, với 0.6B tham số phù hợp huấn luyện trên GPU thông thường, hiệu năng tốt, mã nguồn mở và miễn phí.

Mô-đun Agentic RL của HelloAgents dùng thiết kế kiến trúc bốn tầng, như Hình 11.3 cho thấy.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-3.png" alt="" width="85%"/>
  <p>Hình 11.3 Kiến trúc Agentic RL của HelloAgents</p>
</div>

Tầng dưới cùng là <strong>tầng tập dữ liệu</strong>, gồm lớp <code>GSM8KDataset</code>, hàm <code>create_sft_dataset()</code> và hàm <code>create_rl_dataset()</code>, phụ trách tải dữ liệu và chuyển đổi định dạng. Tầng thứ hai là <strong>tầng hàm phần thưởng</strong>, gồm lớp cơ sở <code>MathRewardFunction</code>, phần thưởng độ chính xác <code>AccuracyReward</code>, phạt độ dài <code>LengthPenaltyReward</code>, phần thưởng bước <code>StepReward</code>, cùng hàm tạo tiện lợi <code>create_*_reward()</code>, phụ trách định nghĩa thế nào là hành vi tốt. Tầng thứ ba là <strong>tầng trainer</strong>, gồm <code>SFTTrainerWrapper</code> và <code>GRPOTrainerWrapper</code>, phụ trách logic huấn luyện cụ thể và hỗ trợ LoRA. Tầng trên cùng là <strong>tầng giao diện thống nhất</strong>, cung cấp công cụ huấn luyện thống nhất <code>RLTrainingTool</code>, hỗ trợ bốn thao tác: <code>action="train"</code> (huấn luyện mô hình), <code>action="load_dataset"</code> (tải tập dữ liệu), <code>action="create_reward"</code> (tạo hàm phần thưởng), <code>action="evaluate"</code> (đánh giá mô hình).

### 11.1.5 Ví dụ khởi động nhanh

Trước khi đi sâu, hãy nhanh chóng trải nghiệm toàn bộ quy trình huấn luyện. Vì phần lý thuyết của chương này khá nhiều, phần thực hành cần gỡ lỗi cũng rất phiền phức, nên chúng ta không tập trung vào việc xây dựng công cụ mà là học cách ứng dụng. Trước tiên cài đặt framework HelloAgents:

```bash
# Cài đặt framework HelloAgents (phiên bản chương 11)
pip install "hello-agents[rl]==0.2.5"

# Hoặc cài từ mã nguồn
cd HelloAgents
pip install -e ".[rl]"
```

Sau đó chạy ví dụ huấn luyện nhanh:

```python
import sys
import json

from hello_agents.tools import RLTrainingTool

# Tạo công cụ huấn luyện RL
rl_tool = RLTrainingTool()

# 1. Kiểm tra nhanh: huấn luyện SFT (10 mẫu, 1 epoch)
sft_result_str = rl_tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/quick_test_sft",
    "max_samples": 10,      # Chỉ dùng 10 mẫu để kiểm tra nhanh
    "num_epochs": 1,        # Chỉ huấn luyện 1 vòng
    "batch_size": 2,
    "use_lora": True        # Dùng LoRA để tăng tốc huấn luyện
})

sft_result = json.loads(sft_result_str)
print(f"\n✓ Huấn luyện SFT hoàn tất, mô hình được lưu tại: {sft_result['output_dir']}")

# 2. Huấn luyện GRPO (5 mẫu, 1 epoch)
grpo_result_str = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",  # Dùng mô hình nền
    "output_dir": "./models/quick_test_grpo",
    "max_samples": 5,       # Chỉ dùng 5 mẫu để kiểm tra nhanh
    "num_epochs": 1,
    "batch_size": 2,        # Phải chia hết cho num_generations (8), dùng 2
    "use_lora": True
})

grpo_result = json.loads(grpo_result_str)
print(f"\n✓ Huấn luyện GRPO hoàn tất, mô hình được lưu tại: {grpo_result['output_dir']}")

# 3. Đánh giá mô hình
eval_result_str = rl_tool.run({
    "action": "evaluate",
    "model_path": "./models/quick_test_grpo",
    "max_samples": 10,      # Đánh giá trên 10 mẫu kiểm tra
    "use_lora": True
})

eval_result = json.loads(eval_result_str)
print(f"\n✓ Đánh giá hoàn tất:")
print(f"  - Độ chính xác: {eval_result['accuracy']}")
print(f"  - Phần thưởng trung bình: {eval_result['average_reward']}")
print(f"  - Số mẫu kiểm tra: {eval_result['num_samples']}")

print("\n" + "=" * 50)
print("🎉 Chúc mừng! Bạn đã hoàn thành huấn luyện mô hình Agentic RL đầu tiên!")
print("=" * 50)
print(f"\nĐường dẫn mô hình:")
print(f"  Mô hình SFT: {sft_result['output_dir']}")
print(f"  Mô hình GRPO: {grpo_result['output_dir']}")
```

Ví dụ nhanh này trình bày toàn bộ quy trình huấn luyện: huấn luyện SFT giúp mô hình học định dạng suy luận cơ bản và mẫu hội thoại, huấn luyện GRPO tối ưu chiến lược suy luận bằng học tăng cường để nâng cao độ chính xác, đánh giá mô hình đo hiệu quả huấn luyện trên tập kiểm tra. Ngoài ra, sau khi chạy xong, độ chính xác thấp là hiện tượng bình thường, vì hiện tại mô hình chỉ thấy 0.7% số mẫu huấn luyện và chỉ chạy một vòng.
## 11.2 Tập dữ liệu và hàm phần thưởng

Tập dữ liệu và hàm phần thưởng là hai nền tảng của huấn luyện học tăng cường. Tập dữ liệu định nghĩa nhiệm vụ Agent cần học, hàm phần thưởng định nghĩa thế nào là hành vi tốt. Trong mục này, chúng ta sẽ học cách chuẩn bị dữ liệu huấn luyện và thiết kế hàm phần thưởng.

### 11.2.1 Tập dữ liệu suy luận toán học GSM8K

Suy luận toán học là nhiệm vụ lý tưởng để đánh giá năng lực suy luận của LLM. Thứ nhất, bài toán có đáp án đúng rõ ràng, có thể đánh giá tự động, không cần gán nhãn thủ công hay mô hình phần thưởng phức tạp. Thứ hai, giải bài toán cần phân rã bài toán, suy diễn từng bước, đây chính là kịch bản điển hình của suy luận nhiều bước. Cuối cùng, năng lực suy luận học được có thể chuyển sang lĩnh vực khác, có tính tổng quát hóa mạnh. So sánh ra, chất lượng câu trả lời của nhiệm vụ hỏi đáp mở (như “làm sao để học lập trình?”) khó đánh giá khách quan, cần lượng lớn gán nhãn thủ công.

GSM8K (Grade School Math 8K)<sup>[4]</sup> là một tập dữ liệu bài toán ứng dụng tiểu học chất lượng cao. Như Bảng 11.2 cho thấy, tập dữ liệu gồm 7,473 mẫu huấn luyện và 1,319 mẫu kiểm tra, độ khó trình độ tiểu học (lớp 2-8), dạng bài là toán ứng dụng, cần 2-8 bước suy luận mới ra đáp án.

<div align="center">
  <p>Bảng 11.2 Thống kê tập dữ liệu GSM8K</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-2.png" alt="" width="85%"/>
</div>
Hãy xem một bài toán GSM8K điển hình:

```
Bài toán: Natalia sold clips to 48 of her friends in April, and then she sold half
      as many clips in May. How many clips did Natalia sell altogether in April
      and May?

Lời giải: Natalia sold 48/2 = <<48/2=24>>24 clips in May.
      Natalia sold 48+24 = <<48+24=72>>72 clips altogether in April and May.
      #### 72

Đáp án cuối cùng: 72
```

Bài toán này cần suy luận hai bước: trước tiên tính số lượng bán được trong tháng 5 (một nửa của 48), sau đó tính tổng (tháng 4 + tháng 5). Trong lời giải, `<<48/2=24>>` là dấu đánh dấu bước tính trung gian, `#### 72` đánh dấu đáp án cuối cùng.

Tập dữ liệu GSM8K cần được chuyển đổi thành các định dạng khác nhau để phù hợp với các phương pháp huấn luyện khác nhau, như Hình 11.4 cho thấy.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-4.png" alt="" width="85%"/>
  <p>Hình 11.4 Chuyển đổi định dạng dữ liệu GSM8K</p>
</div>


Định dạng gốc trực tiếp đến từ tập dữ liệu, gồm bài toán (question) và lời giải (answer, có các bước giải), phù hợp để con người đọc. Định dạng SFT dùng cho tinh chỉnh có giám sát, chuyển bài toán thành prompt định dạng hội thoại, lấy toàn bộ lời giải làm completion. Ví dụ:

```python
{
    "prompt": "<|im_start|>user\nNatalia sold clips to 48 of her friends...<|im_end|>\n<|im_start|>assistant\n",
    "completion": "Let me solve this step by step.\n\nStep 1: ...\n\nFinal Answer: 72<|im_end|>"
}
```

Điểm then chốt là dùng mẫu hội thoại của mô hình (như token `<|im_start|>` của Qwen), prompt chứa câu hỏi của người dùng, completion chứa toàn bộ quá trình giải và đáp án. Như vậy mô hình có thể học cách định dạng đầu ra, cách suy luận từng bước.

Định dạng RL dùng cho học tăng cường, chỉ cung cấp bài toán và đáp án đúng, không cung cấp quá trình giải. Ví dụ:

```python
{
    "prompt": "<|im_start|>user\nNatalia sold clips to 48 of her friends...<|im_end|>\n<|im_start|>assistant\n",
    "ground_truth": "72"
}
```

Điểm then chốt là prompt giống với SFT, nhưng ground_truth chỉ chứa đáp án cuối cùng (dùng để tính phần thưởng), mô hình cần tự sinh toàn bộ quá trình suy luận. Thiết kế này buộc mô hình học suy luận tự chủ, thay vì đơn giản ghi nhớ đáp án.

Như Bảng 11.3 cho thấy, ba định dạng có mục đích sử dụng khác nhau.

<div align="center">
  <p>Bảng 11.3 So sánh các định dạng dữ liệu</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-3.png" alt="" width="85%"/>
</div>
HelloAgents cung cấp hàm tải tập dữ liệu tiện lợi. Hãy dùng mã để tải và xem tập dữ liệu:

```python
from hello_agents.tools import RLTrainingTool
import json

# Tạo công cụ
rl_tool = RLTrainingTool()

# 1. Tải tập dữ liệu định dạng SFT
sft_result = rl_tool.run({
    "action": "load_dataset",
    "format": "sft",
    "max_samples": 5  # Chỉ tải 5 mẫu để xem
})
sft_data = json.loads(sft_result)

print(f"Kích thước tập dữ liệu: {sft_data['dataset_size']}")
print(f"Định dạng dữ liệu: {sft_data['format']}")
print(f"Trường của mẫu: {sft_data['sample_keys']}")

# 2. Tải tập dữ liệu định dạng RL
rl_result = rl_tool.run({
    "action": "load_dataset",
    "format": "rl",
    "max_samples": 5
})
rl_data = json.loads(rl_result)

print(f"Kích thước tập dữ liệu: {rl_data['dataset_size']}")
print(f"Định dạng dữ liệu: {rl_data['format']}")
print(f"Trường của mẫu: {rl_data['sample_keys']}")
```

Có thể thấy, định dạng SFT chứa toàn bộ quá trình giải, dùng cho học có giám sát; định dạng RL chỉ chứa đáp án cuối cùng, mô hình cần tự sinh quá trình suy luận. Tham số `max_samples` điều khiển số mẫu được tải, thuận tiện cho kiểm tra nhanh.

### 11.2.2 Thiết kế hàm phần thưởng

Hàm phần thưởng là cốt lõi của học tăng cường, nó định nghĩa thế nào là “hành vi tốt”. Một hàm phần thưởng tốt có thể dẫn dắt Agent học được chính sách đúng, còn một hàm phần thưởng tồi có thể khiến huấn luyện thất bại hoặc học được hành vi sai.

Trong học tăng cường, hàm phần thưởng $r(s, a)$ hoặc $r(s, a, s')$ gán cho mỗi hành động của Agent một phần thưởng số. Mục tiêu của Agent là tối đa hóa phần thưởng tích lũy:

$$
J(\theta) = \mathbb{E}_{\tau \sim \pi_\theta} \left[\sum_{t=0}^{T} \gamma^t r(s_t, a_t)\right]
$$

Với nhiệm vụ suy luận toán học, chúng ta có thể đơn giản hóa thành:

$$
r(q, a) = f(a, a^*)
$$

Trong đó $q$ là bài toán, $a$ là đáp án mô hình sinh ra, $a^*$ là đáp án đúng, $f$ là hàm đánh giá.

Thiết kế hàm phần thưởng ảnh hưởng trực tiếp đến hiệu quả huấn luyện. Một hàm phần thưởng tốt nên định nghĩa rõ ràng thế nào là thành công, cung cấp được tín hiệu gradient, không tạo ra phương sai quá lớn, dễ điều chỉnh và kết hợp. Một hàm phần thưởng tồi có thể chỉ trao phần thưởng khi nhiệm vụ kết thúc, không có phản hồi ở các bước trung gian, tồn tại hiện tượng đánh lừa phần thưởng khiến Agent tìm ra cách “gian lận” để nhận phần thưởng cao, nhiều mục tiêu mâu thuẫn nhau, phương sai quá lớn, huấn luyện không hội tụ.

HelloAgents cung cấp ba loại hàm phần thưởng tích hợp, có thể dùng riêng hoặc kết hợp, như Hình 11.5 cho thấy.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-5.png" alt="" width="85%"/>
  <p>Hình 11.5 Thiết kế hàm phần thưởng</p>
</div>
<strong>(1) Phần thưởng độ chính xác</strong>

Phần thưởng độ chính xác (AccuracyReward) là hàm phần thưởng cơ bản nhất, nó chỉ quan tâm đáp án có đúng hay không. Định nghĩa toán học là:

$$
r_{\text{acc}}(a, a^*) = \begin{cases}
1 & \text{if } a = a^* \\
0 & \text{otherwise}
\end{cases}
$$

Trong đó $a$ là đáp án mô hình sinh ra, $a^*$ là đáp án đúng. Đây là hàm phần thưởng nhị phân, đáp án đúng được 1 điểm, sai được 0 điểm.

Khi hiện thực cần xử lý việc trích xuất và so sánh đáp án. Đầu ra của mô hình có thể chứa lượng lớn văn bản, chúng ta cần trích xuất đáp án cuối cùng. Các phương pháp trích xuất phổ biến gồm: tìm số sau “Final Answer:”, tìm số sau dấu `####`, dùng biểu thức chính quy để trích xuất số cuối cùng. Khi so sánh đáp án cần xử lý độ chính xác số (như 72.0 và 72 nên được coi là giống nhau), chuyển đổi đơn vị (như 1000 và 1k), khác biệt định dạng (như “72” và “seventy-two”).

Ví dụ sử dụng:

```python
from hello_agents.tools import RLTrainingTool
import json
rl_tool = RLTrainingTool()

# Tạo hàm phần thưởng độ chính xác
reward_result = rl_tool.run({
    "action": "create_reward",
    "reward_type": "accuracy"
})
reward_data = json.loads(reward_result)

print(f"Loại phần thưởng: {reward_data['reward_type']}")
print(f"Mô tả: {reward_data['description']}")

# Lưu ý: thao tác create_reward của RLTrainingTool trả về thông tin cấu hình,
# hàm phần thưởng thực tế sẽ được tạo và sử dụng tự động khi huấn luyện
```

Đầu ra:

```json
Dự đoán: 72, Thực tế: 72, Phần thưởng: 1.0
Dự đoán: 72.0, Thực tế: 72, Phần thưởng: 1.0
Dự đoán: 73, Thực tế: 72, Phần thưởng: 0.0
```

Ưu điểm của phần thưởng độ chính xác là đơn giản trực tiếp, dễ hiểu và dễ hiện thực, phù hợp với nhiệm vụ có đáp án đúng rõ ràng. Nhược điểm là phần thưởng thưa, chỉ khi đáp án hoàn toàn đúng mới có phần thưởng, không phân biệt được “gần đúng” và “hoàn toàn sai”, có thể khiến giai đoạn đầu huấn luyện thiếu phản hồi hiệu quả.

<strong>(2) Phạt độ dài</strong>

Phạt độ dài (LengthPenaltyReward) khuyến khích mô hình sinh câu trả lời súc tích, tránh dài dòng lan man. Định nghĩa toán học là:

$$
r_{\text{length}}(a, a^*, l) = r_{\text{acc}}(a, a^*) - \alpha \cdot \max(0, l - l_{\text{target}})
$$

Trong đó $l$ là độ dài văn bản sinh ra (số ký tự hoặc số token), $l_{\text{target}}$ là độ dài mục tiêu, $\alpha$ là hệ số phạt (mặc định 0.001). Chỉ áp dụng phạt độ dài khi đáp án đúng, tránh việc mô hình vì giảm phạt mà sinh ra đáp án ngắn nhưng sai.

Ý tưởng thiết kế là: nếu đáp án sai, phần thưởng là 0 (bất kể độ dài); nếu đáp án đúng và độ dài hợp lý, phần thưởng là 1; nếu đáp án đúng nhưng quá dài, phần thưởng là $1 - \alpha \cdot (l - l_{\text{target}})$. Ví dụ, độ dài mục tiêu 200 ký tự, độ dài thực tế 500 ký tự, hệ số phạt 0.001, thì phần thưởng là $1 - 0.001 \times (500 - 200) = 0.7$.

Ví dụ sử dụng:

```python
# Tạo hàm phần thưởng phạt độ dài
reward_result = rl_tool.run({
    "action": "create_reward",
    "reward_type": "length_penalty",
    "max_length": 1024,      # Độ dài tối đa
    "penalty_weight": 0.001  # Trọng số phạt
})
reward_data = json.loads(reward_result)

print(f"Loại phần thưởng: {reward_data['reward_type']}")
print(f"Mô tả: {reward_data['description']}")
print(f"Độ dài tối đa: {reward_data['max_length']}")
print(f"Trọng số phạt: {reward_data['penalty_weight']}")
```

Đầu ra:

```
Dự đoán: 72, Thực tế: 72, Độ dài: 50, Phần thưởng: 1.000
Dự đoán: 72, Thực tế: 72, Độ dài: 200, Phần thưởng: 1.000
Dự đoán: 72, Thực tế: 72, Độ dài: 500, Phần thưởng: 0.700
Dự đoán: 73, Thực tế: 72, Độ dài: 50, Phần thưởng: 0.000
```

Ưu điểm của phạt độ dài là khuyến khích diễn đạt súc tích, tránh mô hình sinh nội dung dư thừa, có thể kiểm soát chi phí suy luận (đầu ra ngắn hơn nghĩa là tiêu thụ ít token hơn). Nhược điểm là có thể kìm hãm suy luận chi tiết, cần điều chỉnh cẩn thận hệ số phạt, độ dài tối ưu của các nhiệm vụ khác nhau rất khác nhau.

<strong>(3) Phần thưởng bước</strong>

Phần thưởng bước (StepReward) khuyến khích mô hình sinh các bước suy luận rõ ràng, nâng cao khả năng giải thích. Định nghĩa toán học là:

$$
r_{\text{step}}(a, a^*, s) = r_{\text{acc}}(a, a^*) + \beta \cdot s
$$

Trong đó $s$ là số bước suy luận phát hiện được, $\beta$ là hệ số phần thưởng bước (mặc định 0.1). Tương tự, chỉ trao phần thưởng bước khi đáp án đúng.

Phương pháp phát hiện bước gồm: tìm các dấu như “Step 1:”, “Step 2:”, tìm số ký tự xuống dòng, dùng biểu thức chính quy khớp mẫu suy luận. Ví dụ, một đáp án đúng chứa 3 bước rõ ràng, phần thưởng là $1 + 0.1 \times 3 = 1.3$.

Ví dụ sử dụng:

```python
# Tạo hàm phần thưởng bước
reward_result = rl_tool.run({
    "action": "create_reward",
    "reward_type": "step",
    "step_bonus": 0.1  # Thưởng 0.1 cho mỗi bước
})
reward_data = json.loads(reward_result)

print(f"Loại phần thưởng: {reward_data['reward_type']}")
print(f"Mô tả: {reward_data['description']}")
print(f"Phần thưởng bước: {reward_data['step_bonus']}")
```

Đầu ra:

```
Dự đoán: 72, Thực tế: 72, Số bước: 0, Phần thưởng: 1.00
Dự đoán: 72, Thực tế: 72, Số bước: 2, Phần thưởng: 1.20
Dự đoán: 72, Thực tế: 72, Số bước: 5, Phần thưởng: 1.50
Dự đoán: 73, Thực tế: 72, Số bước: 5, Phần thưởng: 0.00
```

Ưu điểm của phần thưởng bước là khuyến khích suy luận có thể giải thích, câu trả lời sinh ra dễ kiểm chứng và gỡ lỗi hơn, giúp mô hình học cách tư duy có hệ thống. Nhược điểm là có thể khiến mô hình sinh thêm bước dư thừa để nhận nhiều phần thưởng hơn, cần cân bằng giữa số bước và chất lượng đáp án, việc phát hiện bước có thể không chính xác.

Trong ứng dụng thực tế, chúng ta thường kết hợp nhiều hàm phần thưởng để cân bằng các mục tiêu khác nhau. Các chiến lược kết hợp phổ biến gồm:

<strong>Độ chính xác + phạt độ dài</strong>: khuyến khích câu trả lời súc tích và đúng, phù hợp hệ thống hội thoại, hệ thống hỏi đáp. Công thức là:

$$
r = r_{\text{acc}} - \alpha \cdot \max(0, l - l_{\text{target}})
$$

<strong>Độ chính xác + phần thưởng bước</strong>: khuyến khích quá trình suy luận chi tiết, phù hợp kịch bản giáo dục, AI có thể giải thích. Công thức là:

$$
r = r_{\text{acc}} + \beta \cdot s
$$

<strong>Cân bằng cả ba</strong>: tối ưu toàn diện chất lượng đáp án, tính súc tích và khả năng giải thích. Công thức là:
$$
r = r_{\text{acc}} - \alpha \cdot \max(0, l - l_{\text{target}}) + \beta \cdot s
$$

Cần điều chỉnh cẩn thận trọng số $\alpha$ và $\beta$, tránh một mục tiêu nào đó chi phối quá mức.

Ví dụ sử dụng:

```python
# Hàm phần thưởng kết hợp: độ chính xác + phạt độ dài + phần thưởng bước
# Lưu ý: RLTrainingTool hiện chỉ hỗ trợ một loại phần thưởng
# Phần thưởng kết hợp cần được chỉ định qua tham số reward_fn trong cấu hình huấn luyện
# Ở đây minh họa cách cấu hình các loại hàm phần thưởng khác nhau

# Phần thưởng độ chính xác
accuracy_result = rl_tool.run({
    "action": "create_reward",
    "reward_type": "accuracy"
})
print("Phần thưởng độ chính xác:", json.loads(accuracy_result)['description'])

# Phần thưởng phạt độ dài
length_result = rl_tool.run({
    "action": "create_reward",
    "reward_type": "length_penalty",
    "max_length": 1024,
    "penalty_weight": 0.001
})
print("Phần thưởng phạt độ dài:", json.loads(length_result)['description'])

# Phần thưởng bước
step_result = rl_tool.run({
    "action": "create_reward",
    "reward_type": "step",
    "step_bonus": 0.1
})
print("Phần thưởng bước:", json.loads(step_result)['description'])
```

Đầu ra:

```
Phần thưởng kết hợp: 1.200
  - Độ chính xác: 1.0
  - Phạt độ dài: -0.100
  - Phần thưởng bước: +0.3
```

Như Bảng 11.4 cho thấy, các hàm phần thưởng khác nhau phù hợp với các kịch bản ứng dụng khác nhau.

<div align="center">
  <p>Bảng 11.4 So sánh các hàm phần thưởng</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-4.png" alt="" width="85%"/>
</div>

### 11.2.3 Tùy biến tập dữ liệu và hàm phần thưởng

Tuy HelloAgents cung cấp tập dữ liệu GSM8K và các hàm phần thưởng thông dụng, trong ứng dụng thực tế bạn có thể cần dùng tập dữ liệu riêng hoặc thiết kế hàm phần thưởng riêng. Mục này sẽ giới thiệu cách mở rộng framework.

Trước khi dùng tập dữ liệu tùy biến, cần hiểu yêu cầu dữ liệu của hai định dạng huấn luyện:

<strong>Định dạng SFT</strong>: dùng cho tinh chỉnh có giám sát, cần chứa các trường sau:
- `prompt`: prompt đầu vào (gồm thông điệp system và user)
- `completion`: đầu ra mong đợi
- `text`: toàn bộ văn bản hội thoại (tùy chọn)

<strong>Định dạng RL</strong>: dùng cho học tăng cường, cần chứa các trường sau:
- `question`: bài toán gốc
- `prompt`: prompt đầu vào (gồm thông điệp system và user)
- `ground_truth`: đáp án đúng
- `full_answer`: đáp án đầy đủ (gồm quá trình suy luận)

<strong>(1) Chuyển đổi bằng format_math_dataset</strong>

Cách đơn giản nhất là chuẩn bị dữ liệu gốc chứa trường `question` và `answer`, sau đó dùng hàm `format_math_dataset()` để chuyển đổi tự động:

```python
from datasets import Dataset
from hello_agents.rl import format_math_dataset

# 1. Chuẩn bị dữ liệu gốc
custom_data = [
    {
        "question": "What is 2+2?",
        "answer": "2+2=4. #### 4"
    },
    {
        "question": "What is 5*3?",
        "answer": "5*3=15. #### 15"
    },
    {
        "question": "What is 10+7?",
        "answer": "10+7=17. #### 17"
    }
]

# 2. Chuyển thành đối tượng Dataset
raw_dataset = Dataset.from_list(custom_data)

# 3. Chuyển thành định dạng SFT
sft_dataset = format_math_dataset(
    dataset=raw_dataset,
    format_type="sft",
    model_name="Qwen/Qwen3-0.6B"
)
print(f"Tập dữ liệu SFT: {len(sft_dataset)} mẫu")
print(f"Các trường: {sft_dataset.column_names}")

# 4. Chuyển thành định dạng RL
rl_dataset = format_math_dataset(
    dataset=raw_dataset,
    format_type="rl",
    model_name="Qwen/Qwen3-0.6B"
)
print(f"Tập dữ liệu RL: {len(rl_dataset)} mẫu")
print(f"Các trường: {rl_dataset.column_names}")
```

<strong>(2) Truyền trực tiếp tập dữ liệu tùy biến</strong>

Khi dùng RLTrainingTool, có thể truyền trực tiếp tập dữ liệu tùy biến qua tham số `custom_dataset`:

```python
from hello_agents.tools import RLTrainingTool

rl_tool = RLTrainingTool()

# Huấn luyện SFT
result = rl_tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/custom_sft",
    "num_epochs": 3,
    "batch_size": 4,
    "use_lora": True,
    "custom_dataset": sft_dataset  # Truyền trực tiếp tập dữ liệu tùy biến
})

# Huấn luyện GRPO
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/custom_grpo",
    "num_epochs": 2,
    "batch_size": 2,
    "use_lora": True,
    "custom_dataset": rl_dataset  # Truyền trực tiếp tập dữ liệu tùy biến
})
```

(3) Đăng ký tập dữ liệu tùy biến (khuyến nghị)

Với tập dữ liệu cần dùng nhiều lần, khuyến nghị dùng cách đăng ký:

```python
# 1. Đăng ký tập dữ liệu
rl_tool.register_dataset("my_math_dataset", rl_dataset)

# 2. Dùng tập dữ liệu đã đăng ký
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "dataset": "my_math_dataset",  # Dùng tên tập dữ liệu đã đăng ký
    "output_dir": "./models/custom_grpo",
    "num_epochs": 2,
    "use_lora": True
})
```

Hàm phần thưởng dùng để đánh giá chất lượng đáp án mô hình sinh ra. Hàm phần thưởng tùy biến cần tuân theo chữ ký sau:

```python
from typing import List
import re

def custom_reward_function(
    completions: List[str],
    **kwargs
) -> List[float]:
    """
    Hàm phần thưởng tùy biến

    Args:
        completions: Danh sách văn bản hoàn thành do mô hình sinh
        **kwargs: Các tham số khác, thường gồm:
            - ground_truth: Danh sách đáp án đúng
            - Các trường khác của tập dữ liệu

    Returns:
        Danh sách giá trị phần thưởng (mỗi giá trị trong khoảng 0.0-1.0)
    """
    ground_truths = kwargs.get("ground_truth", [])
    rewards = []

    for completion, truth in zip(completions, ground_truths):
        reward = 0.0

        # Trích xuất đáp án
        numbers = re.findall(r'-?\d+\.?\d*', completion)
        if numbers:
            try:
                pred = float(numbers[-1])
                truth_num = float(truth)
                error = abs(pred - truth_num)

                # Trao phần thưởng khác nhau theo sai số
                if error < 0.01:
                    reward = 1.0  # Hoàn toàn đúng
                elif error < 1.0:
                    reward = 0.8  # Rất gần
                elif error < 5.0:
                    reward = 0.5  # Gần đúng

                # Thưởng thêm: khuyến khích trình bày các bước suy luận
                if "step" in completion.lower() or "=" in completion:
                    reward += 0.1

            except ValueError:
                reward = 0.0

        rewards.append(min(reward, 1.0))  # Giới hạn giá trị lớn nhất là 1.0

    return rewards
```

Có hai cách dùng hàm phần thưởng tùy biến:

<strong>(1) Truyền trực tiếp</strong>

```python
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/custom_grpo",
    "custom_dataset": rl_dataset,
    "custom_reward": custom_reward_function  # Truyền trực tiếp hàm phần thưởng
})
```

<strong>(2) Đăng ký rồi dùng (khuyến nghị)</strong>

```python
# 1. Đăng ký hàm phần thưởng
rl_tool.register_reward_function("my_reward", custom_reward_function)

# 2. Dùng hàm phần thưởng đã đăng ký
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "dataset": "my_math_dataset",
    "output_dir": "./models/custom_grpo"
    # Hàm phần thưởng sẽ tự động dùng hàm đã đăng ký cùng tên với dataset
})
```

Dưới đây là một ví dụ hoàn chỉnh về tập dữ liệu và hàm phần thưởng tùy biến:

```python
from datasets import Dataset
from hello_agents.tools import RLTrainingTool
from hello_agents.rl import format_math_dataset
import re
from typing import List

# 1. Chuẩn bị dữ liệu tùy biến
custom_data = [
    {"question": "What is 2+2?", "answer": "2+2=4. #### 4"},
    {"question": "What is 5+3?", "answer": "5+3=8. #### 8"},
    {"question": "What is 10+7?", "answer": "10+7=17. #### 17"}
]

# 2. Chuyển thành định dạng huấn luyện
raw_dataset = Dataset.from_list(custom_data)
rl_dataset = format_math_dataset(raw_dataset, format_type="rl")

# 3. Định nghĩa hàm phần thưởng tùy biến
def tolerant_reward(completions: List[str], **kwargs) -> List[float]:
    """Hàm phần thưởng có dung sai"""
    ground_truths = kwargs.get("ground_truth", [])
    rewards = []

    for completion, truth in zip(completions, ground_truths):
        numbers = re.findall(r'-?\d+\.?\d*', completion)
        if numbers:
            try:
                pred = float(numbers[-1])
                truth_num = float(truth)
                error = abs(pred - truth_num)

                if error < 0.01:
                    reward = 1.0
                elif error < 5.0:
                    reward = 0.5
                else:
                    reward = 0.0
            except ValueError:
                reward = 0.0
        else:
            reward = 0.0

        rewards.append(reward)

    return rewards

# 4. Tạo công cụ và đăng ký
rl_tool = RLTrainingTool()
rl_tool.register_dataset("my_dataset", rl_dataset)
rl_tool.register_reward_function("my_dataset", tolerant_reward)

# 5. Huấn luyện
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "dataset": "my_dataset",
    "output_dir": "./models/custom_grpo",
    "num_epochs": 2,
    "batch_size": 2,
    "use_lora": True
})
```

## 11.3 Huấn luyện SFT

Tinh chỉnh có giám sát (Supervised Fine-Tuning, SFT) là bước đầu tiên của huấn luyện học tăng cường, cũng là nền tảng quan trọng nhất. SFT giúp mô hình học định dạng cơ bản của nhiệm vụ, mẫu hội thoại và năng lực suy luận ban đầu. Không có nền tảng SFT, học tăng cường trực tiếp thường sẽ thất bại, vì mô hình thậm chí không biết định dạng đầu ra cơ bản.

### 11.3.1 Vì sao cần SFT

Trước khi bắt đầu học tăng cường, chúng ta cần huấn luyện SFT trước. Đó là vì mô hình tiền huấn luyện tuy có năng lực ngôn ngữ mạnh, nhưng nó không biết cách hoàn thành nhiệm vụ cụ thể. Mục tiêu huấn luyện của mô hình tiền huấn luyện là dự đoán từ tiếp theo, chứ không phải giải bài toán hay sử dụng công cụ. Định dạng đầu ra của mô hình tiền huấn luyện là văn bản tự do, còn chúng ta cần đầu ra có cấu trúc (như “Step 1: ..., Step 2: ..., Final Answer: ...”). Mô hình tiền huấn luyện chưa thấy dữ liệu liên quan đến nhiệm vụ, không biết thế nào là quá trình suy luận “tốt”.

Vai trò của SFT là dạy mô hình các quy tắc cơ bản của nhiệm vụ. Thứ nhất, học định dạng đầu ra, giúp mô hình biết cách tổ chức câu trả lời (như dùng các dấu “Step 1”, “Final Answer”). Thứ hai, học mẫu suy luận, qua ví dụ học cách phân rã bài toán, suy diễn từng bước. Thứ ba, xây dựng năng lực nền, cung cấp điểm khởi đầu hợp lý cho học tăng cường tiếp theo. Cuối cùng, giảm không gian khám phá, học tăng cường không cần bắt đầu từ con số không mà có thể tối ưu trên nền SFT.

Hãy hiểu tầm quan trọng của SFT qua một thí nghiệm so sánh. Giả sử chúng ta dùng trực tiếp mô hình tiền huấn luyện để giải bài toán GSM8K:

```python
from transformers import AutoTokenizer, AutoModelForCausalLM

# Tải mô hình tiền huấn luyện
model_name = "Qwen/Qwen3-0.6B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Bài toán kiểm tra
question = """Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?"""

# Xây dựng đầu vào
prompt = f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"
inputs = tokenizer(prompt, return_tensors="pt")

# Sinh câu trả lời
outputs = model.generate(**inputs, max_new_tokens=200)
response = tokenizer.decode(outputs[0], skip_special_tokens=False)

print("Câu trả lời của mô hình tiền huấn luyện:")
print(response)
```

Đầu ra của mô hình tiền huấn luyện có thể là:

```bash
<|im_start|>user
Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?<|im_end|>
<|im_start|>assistant
I can help you with that. Let me think about this problem. Natalia sold clips to her friends. In April she sold 48 clips. In May she sold half as many. So we need to find out how many she sold in May and then add them together. But I'm not sure how to calculate half of 48. Maybe I should use a calculator? Or maybe I can just estimate...
```

Có thể thấy, mô hình tiền huấn luyện tuy hiểu bài toán, nhưng đầu ra rất dài dòng, thiếu cấu trúc, không có đáp án rõ ràng, quá trình suy luận hỗn loạn. Đầu ra như vậy không thể dùng cho học tăng cường, vì chúng ta không thể trích xuất đáp án, không thể đánh giá chất lượng, không thể cung cấp tín hiệu phần thưởng hiệu quả.

Bây giờ hãy xem mô hình sau SFT:

```python
# Tải mô hình SFT (giả sử đã huấn luyện xong)
sft_model_path = "./models/sft_model"
sft_model = AutoModelForCausalLM.from_pretrained(sft_model_path)

# Dùng cùng bài toán
outputs = sft_model.generate(**inputs, max_new_tokens=200)
response = tokenizer.decode(outputs[0], skip_special_tokens=False)

print("Câu trả lời của mô hình SFT:")
print(response)
```

Đầu ra của mô hình SFT:

```bash
<|im_start|>user
Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?<|im_end|>
<|im_start|>assistant
Let me solve this step by step.

Step 1: Calculate clips sold in May
Natalia sold half as many clips in May as in April.
Clips in May = 48 / 2 = 24

Step 2: Calculate total clips
Total = April + May = 48 + 24 = 72

Final Answer: 72<|im_end|>
```

Có thể thấy, đầu ra của mô hình SFT có cấu trúc rõ ràng (dùng các dấu “Step 1”, “Step 2”, “Final Answer”), suy luận đúng, đáp án rõ ràng, định dạng thống nhất. Đầu ra như vậy có thể dùng cho học tăng cường, vì chúng ta có thể trích xuất đáp án, tính phần thưởng, tối ưu chính sách.

Như Hình 11.6 cho thấy, SFT là cầu nối từ mô hình tiền huấn luyện đến học tăng cường.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-6.png" alt="" width="85%"/>
  <p>Hình 11.6 Vai trò của SFT trong quy trình huấn luyện</p>
</div>

### 11.3.2 LoRA: Tinh chỉnh hiệu quả tham số

Tinh chỉnh trực tiếp toàn bộ mô hình cần lượng lớn tài nguyên tính toán và bộ nhớ GPU. Với Qwen3-0.6B (0.6B tham số), tinh chỉnh toàn bộ cần khoảng 12GB bộ nhớ GPU (FP16) hoặc 24GB (FP32). Với mô hình lớn hơn (như 7B, 13B), tinh chỉnh toàn bộ gần như không thể thực hiện trên GPU tiêu dùng.

LoRA (Low-Rank Adaptation)<sup>[3]</sup> là một phương pháp tinh chỉnh hiệu quả tham số, chỉ huấn luyện một lượng nhỏ tham số bổ sung trong khi giữ đóng băng tham số mô hình gốc. Tư tưởng cốt lõi của LoRA là: thay đổi tham số khi tinh chỉnh mô hình có thể được biểu diễn bằng ma trận hạng thấp.

Giả sử ma trận trọng số của mô hình gốc là $W \in \mathbb{R}^{d \times k}$, trọng số sau tinh chỉnh là $W' = W + \Delta W$. LoRA giả định $\Delta W$ có thể phân rã thành tích của hai ma trận hạng thấp:

$$
\Delta W = BA
$$

Trong đó $B \in \mathbb{R}^{d \times r}$, $A \in \mathbb{R}^{r \times k}$, $r \ll \min(d, k)$ là hạng (rank).

Khi lan truyền xuôi, đầu ra là:


$$
h = Wx + \Delta Wx = Wx + BAx
$$

Tham số mô hình gốc $W$ được giữ đóng băng, chỉ huấn luyện $B$ và $A$.

So sánh lượng tham số: lượng tham số mô hình gốc là $d \times k$, lượng tham số LoRA là $d \times r + r \times k = r(d + k)$. Khi $r \ll \min(d, k)$, lượng tham số LoRA nhỏ hơn nhiều so với mô hình gốc. Ví dụ, với $d=4096, k=4096, r=8$, lượng tham số mô hình gốc là $4096 \times 4096 = 16,777,216$, lượng tham số LoRA là $8 \times (4096 + 4096) = 65,536$, lượng tham số giảm 256 lần!

Vì vậy có thể tóm tắt ưu điểm của LoRA: mức chiếm bộ nhớ GPU giảm mạnh, huấn luyện nhanh hơn, dễ triển khai, chống quá khớp. Tuy nhiên hiệu quả huấn luyện thường kém hơn một chút so với tinh chỉnh toàn bộ tham số.

Như Bảng 11.5 cho thấy, so sánh hiệu quả của LoRA ở các quy mô mô hình khác nhau.

<div align="center">
  <p>Bảng 11.5 So sánh LoRA với tinh chỉnh toàn bộ</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-5.png" alt="" width="85%"/>
</div>

Các siêu tham số then chốt của LoRA gồm: hạng (rank, r), điều khiển hạng của ma trận LoRA, càng lớn thì năng lực biểu diễn càng mạnh nhưng lượng tham số cũng nhiều hơn, giá trị điển hình 4-64, mặc định 8; Alpha ($\alpha$), hệ số co giãn của LoRA, cập nhật thực tế là $\Delta W = \frac{\alpha}{r} BA$, điều khiển cường độ ảnh hưởng của LoRA, giá trị điển hình bằng rank; mô-đun mục tiêu (target_modules), chỉ định tầng nào áp dụng LoRA, thường chọn tầng chú ý (q_proj, k_proj, v_proj, o_proj), cũng có thể gồm tầng MLP (gate_proj, up_proj, down_proj).

### 11.3.3 Thực hành huấn luyện SFT

Bây giờ hãy dùng HelloAgents để huấn luyện SFT. Quy trình huấn luyện hoàn chỉnh gồm: chuẩn bị tập dữ liệu, cấu hình LoRA, thiết lập tham số huấn luyện, bắt đầu huấn luyện, lưu mô hình.

Ví dụ huấn luyện cơ bản:

```python
from hello_agents.tools import RLTrainingTool

# Tạo công cụ huấn luyện
rl_tool = RLTrainingTool()

# Huấn luyện SFT
result = rl_tool.run({
    # Cấu hình huấn luyện
    "action": "train",
    "algorithm": "sft",

    # Cấu hình mô hình
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/sft_model",

    # Cấu hình dữ liệu
    "max_samples": 100,     # Dùng 100 mẫu để kiểm tra nhanh

    # Tham số huấn luyện
    "num_epochs": 3,        # Huấn luyện 3 vòng
    "batch_size": 4,        # Kích thước batch
    "learning_rate": 5e-5,  # Tốc độ học

    # Cấu hình LoRA
    "use_lora": True,       # Dùng LoRA
    "lora_rank": 8,         # Hạng LoRA
    "lora_alpha": 16,       # Alpha của LoRA
})

print(f"\n✓ Huấn luyện hoàn tất!")
print(f"  - Đường dẫn lưu mô hình: {result['model_path']}")
print(f"  - Số mẫu huấn luyện: {result['num_samples']}")
print(f"  - Số vòng huấn luyện: {result['num_epochs']}")
print(f"  - Loss cuối cùng: {result['final_loss']:.4f}")
```

Nếu loss giảm dần trong quá trình huấn luyện, điều đó cho thấy mô hình đang học.

<strong>(1) Chi tiết các tham số huấn luyện</strong>

Hãy tìm hiểu chi tiết ý nghĩa của từng tham số huấn luyện và khuyến nghị tinh chỉnh.

<strong>Tham số dữ liệu</strong>:

- `max_samples`: số mẫu huấn luyện sử dụng. Khi kiểm tra nhanh có thể dùng 100-1000 mẫu, huấn luyện đầy đủ nên dùng toàn bộ dữ liệu (7473 mẫu). Nhiều dữ liệu hơn thường mang lại hiệu quả tốt hơn, nhưng thời gian huấn luyện cũng dài hơn.
- `split`: chia tập dữ liệu, mặc định là "train". Có thể đặt là "train[:1000]" để chỉ dùng 1000 mẫu đầu tiên.

<strong>Tham số huấn luyện</strong>:

- `num_epochs`: số vòng huấn luyện. 1 vòng nghĩa là duyệt toàn bộ tập dữ liệu một lần. Quá ít (1-2 vòng) có thể dưới khớp, quá nhiều (>10 vòng) có thể quá khớp. Khuyến nghị bắt đầu từ 3 vòng, quan sát đường cong loss để điều chỉnh.
- `batch_size`: số mẫu dùng cho mỗi lần cập nhật. Càng lớn huấn luyện càng ổn định, nhưng mức chiếm bộ nhớ GPU càng cao. Khuyến nghị điều chỉnh theo bộ nhớ GPU: GPU 4GB dùng batch_size=1-2, GPU 8GB dùng batch_size=4-8, GPU 16GB dùng batch_size=8-16.
- `learning_rate`: tốc độ học, điều khiển bước cập nhật tham số. Quá nhỏ (1e-6) hội tụ chậm, quá lớn (1e-3) có thể không hội tụ. SFT khuyến nghị 5e-5, LoRA có thể lớn hơn một chút (1e-4).

<strong>Tham số LoRA</strong>:

- `use_lora`: có dùng LoRA hay không. Khuyến nghị luôn bật, trừ khi có đủ bộ nhớ GPU.
- `lora_rank`: hạng LoRA, điều khiển năng lực biểu diễn. 4-8 phù hợp nhiệm vụ nhỏ, 16-32 phù hợp nhiệm vụ phức tạp, 64 phù hợp tinh chỉnh quy mô lớn.
- `lora_alpha`: hệ số co giãn của LoRA, thường đặt bằng 2 lần rank. Khi rank=8 thì alpha=16; khi rank=16 thì alpha=32.

<strong>Tham số optimizer</strong>:

- `optimizer`: loại optimizer, mặc định là "adamw". AdamW là lựa chọn phổ biến nhất, cũng có thể thử "sgd" hoặc "adafactor", v.v.
- `weight_decay`: suy giảm trọng số, chống quá khớp. Mặc định 0.01, có thể thử 0.001-0.1.
- `warmup_ratio`: tỷ lệ khởi động tốc độ học. Trong warmup_ratio số bước đầu, tốc độ học tăng tuyến tính, sau đó giảm tuyến tính. Mặc định 0.1 (khởi động 10% số bước đầu).

<strong>(2) Ví dụ huấn luyện đầy đủ</strong>

Hãy thực hiện một lần huấn luyện SFT đầy đủ, dùng toàn bộ dữ liệu và thực hành tốt nhất:

```python
from hello_agents.tools import RLTrainingTool

rl_tool = RLTrainingTool()

# Huấn luyện SFT đầy đủ
result = rl_tool.run({
    "action": "train",
    "algorithm": "sft",

    # Cấu hình mô hình
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/sft_full",

    # Cấu hình dữ liệu
    "max_samples": None,    # Dùng toàn bộ dữ liệu (7473 mẫu)

    # Tham số huấn luyện
    "num_epochs": 3,
    "batch_size": 8,
    "learning_rate": 5e-5,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,

    # Cấu hình LoRA
    "use_lora": True,
    "lora_rank": 16,        # Dùng rank lớn hơn
    "lora_alpha": 32,
    "lora_target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],

    # Cấu hình khác
    "save_steps": 500,      # Lưu mỗi 500 bước
    "logging_steps": 100,   # Ghi log mỗi 100 bước
    "eval_steps": 500,      # Đánh giá mỗi 500 bước
})

print(f"Huấn luyện hoàn tất! Mô hình được lưu tại: {result['model_path']}")
```

Cấu hình này phù hợp huấn luyện trên GPU 8GB, dự kiến mất 30-60 phút.

<strong>(3) Giám sát và gỡ lỗi huấn luyện</strong>

Trong quá trình huấn luyện, chúng ta cần giám sát ba chỉ số then chốt. Loss nên giảm dần; nếu không giảm có thể do tốc độ học quá nhỏ hoặc dữ liệu có vấn đề, nếu giảm rồi lại tăng thì có thể do tốc độ học quá lớn hoặc đã quá khớp. Chuẩn gradient (Gradient Norm) nên nằm trong khoảng hợp lý 0.1-10; quá lớn (>100) cho thấy gradient bùng nổ cần giảm tốc độ học, quá nhỏ (<0.01) cho thấy gradient biến mất cần kiểm tra cấu hình mô hình. Tốc độ học (Learning Rate) nên thay đổi theo chiến lược warmup, tăng tuyến tính trong 10% số bước đầu, sau đó giảm tuyến tính về 0.

Các vấn đề thường gặp trong huấn luyện và cách giải quyết: khi thiếu bộ nhớ GPU có thể giảm batch_size hoặc max_length, dùng tích lũy gradient hoặc mô hình nhỏ hơn; khi huấn luyện chậm có thể tăng batch_size, giảm tần suất ghi log, hoặc dùng huấn luyện độ chính xác hỗn hợp; khi loss không giảm có thể tăng tốc độ học, kiểm tra định dạng dữ liệu, hoặc tăng số vòng huấn luyện; khi quá khớp có thể tăng weight_decay, giảm số vòng huấn luyện, hoặc dùng nhiều dữ liệu hơn.
### 11.3.4 Đánh giá mô hình

Sau khi huấn luyện xong, chúng ta cần đánh giá hiệu quả của mô hình. Các chỉ số đánh giá gồm:

- <strong>Độ chính xác (Accuracy)</strong>: tỷ lệ đáp án hoàn toàn đúng, chỉ số trực tiếp nhất, phạm vi 0-1, càng cao càng tốt.

- <strong>Phần thưởng trung bình (Average Reward)</strong>: phần thưởng trung bình của tất cả mẫu, tổng hợp các yếu tố độ chính xác, độ dài, số bước, phạm vi phụ thuộc thiết kế hàm phần thưởng.

- <strong>Chất lượng suy luận (Reasoning Quality)</strong>: độ rõ ràng và tính logic của quá trình suy luận, cần đánh giá thủ công hoặc dùng mô hình đánh giá chuyên dụng.

Dùng HelloAgents để đánh giá mô hình:

```python
from hello_agents.tools import RLTrainingTool

rl_tool = RLTrainingTool()

# Đánh giá mô hình SFT
eval_result = rl_tool.run({
    "action": "evaluate",
    "model_path": "./models/sft_full",
    "max_samples": 100,     # Đánh giá trên 100 mẫu kiểm tra
    "use_lora": True,
})

eval_data = json.loads(eval_result)
print(f"\nKết quả đánh giá:")
print(f"  - Độ chính xác: {eval_data['accuracy']}")
print(f"  - Phần thưởng trung bình: {eval_data['average_reward']}")
print(f"  - Số mẫu kiểm tra: {eval_data['num_samples']}")
```

Với mô hình nhỏ như Qwen3-0.6B, đạt độ chính xác 40-50% trên GSM8K sau SFT là bình thường. Qua học tăng cường, chúng ta có thể nâng tiếp lên 60-70%.

Để hiểu rõ hơn hiệu quả của SFT, chúng ta có thể so sánh mô hình ở các giai đoạn khác nhau:

```python
# Đánh giá mô hình tiền huấn luyện (chưa qua SFT)
base_result = rl_tool.run({
    "action": "evaluate",
    "model_path": "Qwen/Qwen3-0.6B",
    "max_samples": 100,
    "use_lora": False,
})
base_data = json.loads(base_result)

# Đánh giá mô hình SFT
sft_result = rl_tool.run({
    "action": "evaluate",
    "model_path": "./models/sft_full",
    "max_samples": 100,
    "use_lora": True,
})
sft_data = json.loads(sft_result)

# So sánh kết quả
print("So sánh mô hình:")
print(f"Độ chính xác mô hình tiền huấn luyện: {base_data['accuracy']}")
print(f"Độ chính xác mô hình SFT: {sft_data['accuracy']}")
```

Trong mục này, chúng ta đã học tầm quan trọng của SFT (học định dạng, xây dựng baseline), nguyên lý LoRA (phân rã hạng thấp, hiệu quả tham số), thực hành huấn luyện SFT (cấu hình tham số, giám sát huấn luyện), đánh giá mô hình (độ chính xác, phân tích so sánh).

## 11.4 Huấn luyện GRPO

Sau khi hoàn thành huấn luyện SFT, chúng ta đã có một mô hình có thể sinh đáp án có cấu trúc. Tuy nhiên, mô hình SFT chỉ học “bắt chước” quá trình suy luận trong dữ liệu huấn luyện, chưa thực sự học “tư duy”. Học tăng cường có thể giúp mô hình tối ưu chiến lược suy luận qua thử và sai, từ đó vượt qua chất lượng của dữ liệu huấn luyện.

### 11.4.1 Từ PPO đến GRPO

Trong lĩnh vực học tăng cường, PPO (Proximal Policy Optimization)<sup>[1]</sup> là một trong những thuật toán kinh điển nhất. PPO đảm bảo tính ổn định của huấn luyện bằng cách giới hạn biên độ cập nhật chính sách. Tuy nhiên, PPO trong huấn luyện LLM có một số vấn đề: cần huấn luyện Value Model (mô hình giá trị), làm tăng độ phức tạp huấn luyện và mức chiếm bộ nhớ GPU; cần duy trì đồng thời bốn mô hình (Policy Model, Reference Model, Value Model, Reward Model), hiện thực kỹ thuật phức tạp; huấn luyện không ổn định, dễ xảy ra sụp đổ phần thưởng hoặc thoái hóa chính sách.

GRPO (Group Relative Policy Optimization)<sup>[2]</sup> là một biến thể PPO được đơn giản hóa, thiết kế riêng cho LLM. Tư tưởng cốt lõi của GRPO là: không cần Value Model, dùng phần thưởng tương đối trong nhóm thay cho phần thưởng tuyệt đối; đơn giản hóa quy trình huấn luyện, chỉ cần Policy Model và Reference Model; nâng cao tính ổn định huấn luyện, giảm nguy cơ sụp đổ phần thưởng.

Hãy hiểu nguyên lý GRPO qua các công thức toán học. Hàm mục tiêu của PPO là:

$$
J_{\text{PPO}}(\theta) = \mathbb{E}_{s,a \sim \pi_\theta} \left[ \min\left( \frac{\pi_\theta(a|s)}{\pi_{\text{old}}(a|s)} A(s,a), \text{clip}\left(\frac{\pi_\theta(a|s)}{\pi_{\text{old}}(a|s)}, 1-\epsilon, 1+\epsilon\right) A(s,a) \right) \right]
$$

Trong đó $A(s,a)$ là hàm lợi thế (Advantage), cần Value Model để ước lượng:

$$
A(s,a) = Q(s,a) - V(s) = r(s,a) + \gamma V(s') - V(s)
$$

Hàm mục tiêu của GRPO được đơn giản hóa thành:

$$
J_{\text{GRPO}}(\theta) = \mathbb{E}_{s,a \sim \pi_\theta} \left[ \frac{\pi_\theta(a|s)}{\pi_{\text{ref}}(a|s)} \cdot (r(s,a) - \bar{r}_{\text{group}}) \right] - \beta \cdot D_{KL}(\pi_\theta || \pi_{\text{ref}})
$$

Trong đó $\bar{r}_{\text{group}}$ là phần thưởng trung bình trong nhóm, $\beta$ là hệ số phạt phân kỳ KL. Khác biệt then chốt là: GRPO dùng $r(s,a) - \bar{r}_{\text{group}}$ thay cho hàm lợi thế $A(s,a)$, không cần Value Model; GRPO dùng phần thưởng tương đối trong nhóm, giảm phương sai phần thưởng; GRPO thêm phạt phân kỳ KL, ngăn chính sách lệch quá xa.

Như Hình 11.7 cho thấy, so sánh quy trình huấn luyện của PPO và GRPO.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-7.png" alt="" width="85%"/>
  <p>Hình 11.7 Quy trình huấn luyện PPO vs GRPO</p>
</div>

Có thể thấy, GRPO bỏ đi việc huấn luyện Value Model, đơn giản hóa quy trình rất nhiều.

Như Bảng 11.6 cho thấy, so sánh chi tiết PPO và GRPO.

<div align="center">
  <p>Bảng 11.6 So sánh PPO vs GRPO</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-6.png" alt="" width="85%"/>
</div>



Với huấn luyện LLM, GRPO là lựa chọn tốt hơn, vì nó đơn giản hơn, ổn định hơn, mức chiếm bộ nhớ GPU thấp hơn.

### 11.4.2 Thực hành huấn luyện GRPO

Bây giờ hãy dùng HelloAgents để huấn luyện GRPO. Điều kiện tiên quyết của huấn luyện GRPO là đã hoàn thành huấn luyện SFT, vì GRPO cần một chính sách khởi đầu hợp lý.

Ví dụ huấn luyện GRPO cơ bản:

```python
from hello_agents.tools import RLTrainingTool

# Tạo công cụ huấn luyện
rl_tool = RLTrainingTool()

# Huấn luyện GRPO
result = rl_tool.run({
    # Cấu hình huấn luyện
    "action": "train",
    "algorithm": "grpo",

    # Cấu hình mô hình
    "model_name": "./models/sft_full",  # Bắt đầu từ mô hình SFT
    "output_dir": "./models/grpo_model",

    # Cấu hình dữ liệu
    "max_samples": 100,     # Dùng 100 mẫu để kiểm tra nhanh

    # Tham số huấn luyện
    "num_epochs": 3,
    "batch_size": 4,
    "learning_rate": 1e-5,  # Tốc độ học GRPO thường nhỏ hơn SFT

    # Tham số riêng của GRPO
    "num_generations": 4,   # Sinh 4 đáp án cho mỗi bài toán
    "kl_coef": 0.05,        # Hệ số phạt phân kỳ KL

    # Cấu hình LoRA
    "use_lora": True,
    "lora_rank": 16,
    "lora_alpha": 32,

    # Cấu hình hàm phần thưởng
    "reward_type": "accuracy",  # Dùng phần thưởng độ chính xác
})

print(f"\n✓ Huấn luyện hoàn tất!")
print(f"  - Đường dẫn lưu mô hình: {result['model_path']}")
print(f"  - Số mẫu huấn luyện: {result['num_samples']}")
print(f"  - Số vòng huấn luyện: {result['num_epochs']}")
print(f"  - Phần thưởng trung bình: {result['average_reward']:.4f}")
```

Nếu trong quá trình huấn luyện GRPO, phần thưởng trung bình tăng dần và phân kỳ KL giữ trong phạm vi hợp lý, điều đó cho thấy huấn luyện diễn ra bình thường.

GRPO có một số tham số riêng cần hiểu và tinh chỉnh.

<strong>Tham số sinh</strong>:

- `num_generations`: mỗi bài toán sinh bao nhiêu đáp án. Càng nhiều càng tốt, nhưng chi phí tính toán cũng cao hơn. Giá trị điển hình 4-8. Mục đích sinh nhiều đáp án là tính phần thưởng tương đối trong nhóm, tăng tính đa dạng của tín hiệu huấn luyện.
- `max_new_tokens`: mỗi đáp án sinh tối đa bao nhiêu token. Quá ít có thể cắt cụt đáp án, quá nhiều lãng phí tính toán. Khuyến nghị 256-512.
- `temperature`: nhiệt độ sinh, điều khiển tính ngẫu nhiên. 0 nghĩa là giải mã tham lam, 1 là lấy mẫu chuẩn. GRPO khuyến nghị 0.7-1.0, giữ một mức khám phá nhất định.

<strong>Tham số tối ưu</strong>:

- `learning_rate`: tốc độ học của GRPO thường nhỏ hơn SFT, vì chúng ta không muốn lệch quá xa mô hình SFT. Khuyến nghị 1e-6 đến 1e-5; trên mô hình nhỏ, tốc độ học quá lớn (như 5e-5) có thể khiến chính sách sụp đổ.
- `kl_coef`: hệ số phạt phân kỳ KL, điều khiển biên độ cập nhật chính sách. Quá nhỏ (0.01) có thể khiến chính sách lệch quá xa, quá lớn (0.5) có thể hạn chế học tập. Khuyến nghị 0.05-0.1.
- `clip_range`: phạm vi cắt tỷ lệ chính sách, tương tự epsilon của PPO. Khuyến nghị 0.2.

<strong>Tham số phần thưởng</strong>:

- `reward_type`: loại hàm phần thưởng, có thể là "accuracy", "length_penalty", "step" hoặc "combined".
- `reward_config`: cấu hình bổ sung của hàm phần thưởng, như độ dài mục tiêu của phạt độ dài, hệ số của phần thưởng bước, v.v.

Hãy thực hiện một lần huấn luyện GRPO đầy đủ, dùng toàn bộ dữ liệu và thực hành tốt nhất:

```python
from hello_agents.tools import RLTrainingTool

rl_tool = RLTrainingTool()

# Huấn luyện GRPO đầy đủ
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",

    # Cấu hình mô hình
    "model_name": "./models/sft_full",
    "output_dir": "./models/grpo_full",

    # Cấu hình dữ liệu
    "max_samples": None,    # Dùng toàn bộ dữ liệu

    # Tham số huấn luyện
    "num_epochs": 3,
    "batch_size": 4,
    "learning_rate": 1e-5,
    "warmup_ratio": 0.1,

    # Tham số riêng của GRPO
    "num_generations": 4,
    "max_new_tokens": 512,
    "temperature": 0.8,
    "kl_coef": 0.05,
    "clip_range": 0.2,

    # Cấu hình LoRA
    "use_lora": True,
    "lora_rank": 16,
    "lora_alpha": 32,

    # Cấu hình hàm phần thưởng
    "reward_type": "combined",
    "reward_config": {
        "components": [
            {"type": "accuracy", "weight": 1.0},
            {"type": "length_penalty", "weight": 0.5, "target_length": 200},
            {"type": "step", "weight": 0.3, "step_bonus": 0.1}
        ]
    },

    # Cấu hình khác
    "save_steps": 500,
    "logging_steps": 100,
})

print(f"Huấn luyện hoàn tất! Mô hình được lưu tại: {result['model_path']}")
```

### 11.4.3 Phân tích quá trình huấn luyện GRPO

Hãy hiểu sâu quá trình huấn luyện GRPO, xem mỗi bước diễn ra điều gì.

<strong>(1) Vòng lặp huấn luyện</strong>

Vòng lặp huấn luyện GRPO gồm các bước sau:

1. <strong>Giai đoạn lấy mẫu</strong>: với mỗi bài toán, dùng chính sách hiện tại sinh nhiều đáp án (`num_generations` đáp án). Các đáp án này tạo thành một “nhóm”, dùng để tính phần thưởng tương đối.

2. <strong>Tính phần thưởng</strong>: tính phần thưởng $r_i$ cho mỗi đáp án sinh ra. Phần thưởng có thể là độ chính xác, phạt độ dài, phần thưởng bước hoặc kết hợp của chúng.

3. <strong>Phần thưởng tương đối</strong>: tính phần thưởng trung bình trong nhóm $\bar{r} = \frac{1}{N}\sum_{i=1}^{N} r_i$, sau đó tính phần thưởng tương đối $\hat{r}_i = r_i - \bar{r}$. Lợi ích của cách này là giảm phương sai phần thưởng, khiến huấn luyện ổn định hơn.

4. <strong>Cập nhật chính sách</strong>: dùng phần thưởng tương đối để cập nhật chính sách, đồng thời thêm phạt phân kỳ KL để ngăn chính sách lệch quá xa mô hình tham chiếu.

5. <strong>Lặp lại</strong>: lặp lại các bước trên cho đến khi hoàn thành tất cả vòng huấn luyện.

Hãy hiểu qua một ví dụ cụ thể:

```python
# Giả sử chúng ta có một bài toán
question = "What is 48 + 24?"

# Sinh 4 đáp án
answers = [
    "48 + 24 = 72. Final Answer: 72",      # Đúng
    "48 + 24 = 72. Final Answer: 72",      # Đúng
    "48 + 24 = 70. Final Answer: 70",      # Sai
    "Let me think... 72. Final Answer: 72" # Đúng nhưng dài dòng
]

# Tính phần thưởng (giả sử dùng độ chính xác + phạt độ dài)
rewards = [1.0, 1.0, 0.0, 0.8]  # Đáp án thứ 4 bị phạt vì dài dòng

# Tính phần thưởng trung bình trong nhóm
avg_reward = (1.0 + 1.0 + 0.0 + 0.8) / 4 = 0.7

# Tính phần thưởng tương đối
relative_rewards = [
    1.0 - 0.7 = 0.3,   # Đúng và súc tích, phần thưởng tương đối dương
    1.0 - 0.7 = 0.3,   # Đúng và súc tích, phần thưởng tương đối dương
    0.0 - 0.7 = -0.7,  # Sai, phần thưởng tương đối âm
    0.8 - 0.7 = 0.1    # Đúng nhưng dài dòng, phần thưởng tương đối nhỏ
]

# Cập nhật chính sách: tăng xác suất của hai đáp án đầu, giảm xác suất của đáp án thứ ba
```

Có thể thấy, cơ chế phần thưởng tương đối khuyến khích mô hình sinh ra những đáp án “tốt hơn mức trung bình”, thay vì đơn giản theo đuổi phần thưởng cao. Như vậy có thể giảm phương sai phần thưởng, nâng cao tính ổn định của huấn luyện.

<strong>(2) Phạt phân kỳ KL</strong>

Phạt phân kỳ KL là thành phần then chốt của GRPO, nó ngăn chính sách lệch quá xa mô hình tham chiếu. Phân kỳ KL được định nghĩa là:

$$
D_{KL}(\pi_\theta || \pi_{\text{ref}}) = \mathbb{E}_{s,a \sim \pi_\theta} \left[ \log \frac{\pi_\theta(a|s)}{\pi_{\text{ref}}(a|s)} \right]
$$

Trong thực tế, chúng ta tính phân kỳ KL của từng token rồi cộng lại:

$$
D_{KL} = \sum_{t=1}^{T} \log \frac{\pi_\theta(a_t|s, a_{<t})}{\pi_{\text{ref}}(a_t|s, a_{<t})}
$$

Phân kỳ KL càng lớn cho thấy chính sách hiện tại khác biệt càng nhiều so với mô hình tham chiếu. Bằng cách thêm số hạng phạt phân kỳ KL $-\beta \cdot D_{KL}$, chúng ta giới hạn biên độ cập nhật chính sách, tránh “quên” kiến thức đã học ở giai đoạn SFT.

Việc chọn `kl_coef` ($\beta$) rất quan trọng:

- Quá nhỏ (0.01): chính sách có thể lệch quá xa, khiến định dạng đầu ra hỗn loạn hoặc chất lượng giảm
- Quá lớn (0.5): cập nhật chính sách bị hạn chế, học chậm, khó vượt qua mô hình SFT
- Khuyến nghị (0.05-0.1): cân bằng giữa khám phá và ổn định

<strong>(3) Giám sát huấn luyện</strong>

Trong quá trình huấn luyện GRPO, chúng ta cần giám sát các chỉ số sau:

- <strong>Phần thưởng trung bình (Average Reward)</strong>: nên tăng dần. Nếu phần thưởng không tăng, có thể do tốc độ học quá nhỏ, phạt KL quá lớn, thiết kế hàm phần thưởng không hợp lý. Nếu phần thưởng tăng rồi giảm, có thể do quá khớp hoặc sụp đổ phần thưởng.

- <strong>Phân kỳ KL (KL Divergence)</strong>: nên giữ trong phạm vi hợp lý (0.01-0.1). Nếu phân kỳ KL quá lớn (>0.5), chính sách lệch quá xa, cần tăng kl_coef hoặc giảm tốc độ học. Nếu phân kỳ KL quá nhỏ (<0.001), chính sách gần như không cập nhật, cần giảm kl_coef hoặc tăng tốc độ học.

- <strong>Độ chính xác (Accuracy)</strong>: nên tăng dần. Đây là chỉ số trực quan nhất, phản ánh năng lực thực tế của mô hình.

- <strong>Chất lượng sinh (Generation Quality)</strong>: cần kiểm tra thủ công đáp án sinh ra, đảm bảo định dạng đúng, suy luận rõ ràng.

HelloAgents tích hợp hai công cụ giám sát huấn luyện phổ biến: Weights & Biases (wandb) và TensorBoard.

<strong>Cách 1: Dùng Weights & Biases (khuyến nghị)</strong>

Weights & Biases là nền tảng theo dõi thí nghiệm học máy phổ biến nhất hiện nay, cung cấp khả năng trực quan hóa và quản lý thí nghiệm mạnh mẽ.

```python
import os

# 1. Cấu hình wandb (cần đăng ký tài khoản trước: https://wandb.ai)
os.environ["WANDB_PROJECT"] = "hello-agents-grpo"  # Tên dự án
os.environ["WANDB_LOG_MODEL"] = "false"            # Không tải lên tệp mô hình

# 2. Bật wandb trong cấu hình huấn luyện
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/grpo_monitored",
    "num_epochs": 2,
    "batch_size": 2,
    "use_lora": True,
    # wandb sẽ tự động ghi lại mọi chỉ số huấn luyện
})

# Sau khi huấn luyện xong, truy cập https://wandb.ai để xem đường cong huấn luyện
```

wandb sẽ tự động ghi lại các chỉ số sau:
- `train/reward`: phần thưởng trung bình
- `train/kl`: phân kỳ KL
- `train/loss`: loss huấn luyện
- `train/learning_rate`: tốc độ học
- `train/epoch`: số vòng huấn luyện

<strong>Cách 2: Dùng TensorBoard</strong>

TensorBoard là công cụ trực quan hóa do TensorFlow cung cấp, cũng hỗ trợ huấn luyện PyTorch.

```python
# 1. Khi huấn luyện sẽ tự động tạo log tensorboard trong output_dir
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/grpo_tb",
    "num_epochs": 2,
    "batch_size": 2,
    "use_lora": True,
})

# 2. Khởi động TensorBoard để xem đường cong huấn luyện
# Chạy trong dòng lệnh:
# tensorboard --logdir=./models/grpo_tb
# Sau đó truy cập http://localhost:6006
```

<strong>Cách 3: Giám sát ngoại tuyến (không cần công cụ bên ngoài)</strong>

Nếu không muốn dùng wandb hoặc TensorBoard, cũng có thể giám sát qua log huấn luyện:

```python
# Quá trình huấn luyện sẽ in log chi tiết
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/grpo_simple",
    "num_epochs": 2,
    "batch_size": 2,
    "use_lora": True,
})

# Ví dụ log:
# Epoch 1/2 | Step 100/500 | Reward: 0.45 | KL: 0.023 | Loss: 1.234
# Epoch 1/2 | Step 200/500 | Reward: 0.52 | KL: 0.031 | Loss: 1.156
# ...
```

Trong huấn luyện GRPO, có thể gặp một số vấn đề. Khi phần thưởng không tăng, có thể do tốc độ học quá nhỏ hoặc phạt KL quá lớn hạn chế cập nhật chính sách, cũng có thể do thiết kế hàm phần thưởng không hợp lý hoặc chất lượng mô hình SFT quá kém; khi đó có thể tăng tốc độ học (từ 1e-5 lên 5e-5), giảm kl_coef (từ 0.1 xuống 0.05), kiểm tra hàm phần thưởng hoặc huấn luyện lại mô hình SFT.

Khi phân kỳ KL bùng nổ (vượt 0.5 thậm chí 1.0) khiến định dạng đáp án sinh ra hỗn loạn, thường là do tốc độ học quá lớn hoặc phạt KL quá nhỏ, hoặc hàm phần thưởng quá mạnh tay; có thể giảm tốc độ học (từ 5e-5 xuống 1e-5), tăng kl_coef (từ 0.05 lên 0.1), điều chỉnh hàm phần thưởng hoặc dùng cắt gradient.

Khi chất lượng sinh giảm (độ chính xác tăng nhưng định dạng hỗn loạn, suy luận không rõ ràng), có thể do hàm phần thưởng chỉ quan tâm độ chính xác mà bỏ qua các chỉ số chất lượng khác, hoặc phạt KL quá nhỏ khiến mô hình lệch quá xa SFT, hoặc đã quá khớp; khi đó nên dùng hàm phần thưởng kết hợp để tối ưu đồng thời nhiều chỉ số, tăng kl_coef để giữ nhất quán, giảm số vòng huấn luyện hoặc tăng dữ liệu huấn luyện.

Mức chiếm bộ nhớ GPU của huấn luyện GRPO cao hơn SFT, vì cần đồng thời sinh nhiều đáp án và lưu đầu ra của mô hình tham chiếu, dễ xảy ra OOM. Có thể giảm num_generations (từ 8 xuống 4), batch_size (từ 4 xuống 2) hoặc max_new_tokens (từ 512 xuống 256), hoặc dùng checkpoint gradient và huấn luyện độ chính xác hỗn hợp để giảm nhẹ.

## 11.5 Đánh giá và phân tích mô hình

Sau khi huấn luyện xong, chúng ta cần đánh giá toàn diện hiệu năng của mô hình, không chỉ nhìn vào một chỉ số độ chính xác mà còn phân tích sâu chất lượng suy luận, mô thức lỗi, năng lực tổng quát hóa, v.v. Mục này sẽ giới thiệu cách đánh giá và phân tích mô hình Agentic RL một cách hệ thống.

### 11.5.1 Hệ thống chỉ số đánh giá

Một hệ thống đánh giá tốt nên đa chiều, đo lường năng lực mô hình từ nhiều góc độ. Chúng ta chia chỉ số đánh giá thành ba loại: chỉ số độ chính xác, chỉ số hiệu quả, chỉ số chất lượng.


<strong>(1) Chỉ số độ chính xác</strong>

Chỉ số độ chính xác đo lường liệu mô hình có đưa ra được đáp án đúng hay không.

<strong>Độ chính xác (Accuracy)</strong>: chỉ số cơ bản nhất, tỷ lệ đáp án hoàn toàn đúng. Công thức tính là:
$$
\text{Accuracy} = \frac{\text{Số đáp án đúng}}{\text{Tổng số bài toán}}
$$

Ưu điểm là đơn giản trực quan, dễ hiểu và dễ so sánh. Nhược điểm là không phân biệt được “gần đúng” và “hoàn toàn sai”, với nhiệm vụ phức tạp có thể quá thô.

<strong>Độ chính xác Top-K</strong>: sinh K đáp án, chỉ cần một đáp án đúng là tính đúng. Công thức tính là:
$$
\text{Accuracy@K} = \frac{\text{Số bài toán có ít nhất một đáp án đúng}}{\text{Tổng số bài toán}}
$$

Chỉ số này phản ánh “tiềm năng” của mô hình, tức liệu qua nhiều lần lấy mẫu có thể tìm ra đáp án đúng hay không.

<strong>Sai số số học (Numerical Error)</strong>: với bài toán, có thể tính sai số giữa giá trị dự đoán và giá trị thực. Công thức tính là:

$$
\text{Error} = \frac{1}{N} \sum_{i=1}^{N} |y_i - \hat{y}_i|
$$

Chỉ số này có thể phân biệt “gần đúng” (như dự đoán 72.5, thực tế 72) và “hoàn toàn sai” (như dự đoán 100, thực tế 72).

<strong>(2) Chỉ số hiệu quả</strong>

Chỉ số hiệu quả đo lường chi phí sinh đáp án của mô hình.

<strong>Độ dài trung bình (Average Length)</strong>: số token trung bình của đáp án sinh ra. Công thức tính là:

$$
\text{Avg Length} = \frac{1}{N} \sum_{i=1}^{N} |y_i|
$$

Đáp án ngắn hơn nghĩa là chi phí suy luận thấp hơn và tốc độ phản hồi nhanh hơn.

<strong>Số bước suy luận (Reasoning Steps)</strong>: số bước suy luận chứa trong đáp án. Công thức tính là:

$$
\text{Avg Steps} = \frac{1}{N} \sum_{i=1}^{N} s_i
$$

Số bước hợp lý (2-5 bước) cho thấy mô hình có thể phân rã bài toán một cách hệ thống, quá nhiều bước có thể cho thấy suy luận dư thừa.

<strong>Thời gian suy luận (Inference Time)</strong>: thời gian cần để sinh một đáp án. Chỉ số này quan trọng trong triển khai thực tế, ảnh hưởng đến trải nghiệm người dùng.

<strong>(3) Chỉ số chất lượng</strong>

Chỉ số chất lượng đo lường tính dễ đọc và khả năng giải thích của đáp án.

<strong>Tỷ lệ đúng định dạng (Format Correctness)</strong>: đáp án có tuân theo định dạng mong đợi hay không (như có chứa các dấu “Step 1”, “Final Answer”). Công thức tính là:
$$
\text{Format Correctness} = \frac{\text{Số đáp án đúng định dạng}}{\text{Tổng số đáp án}}
$$

Đúng định dạng là yêu cầu cơ bản, đáp án có định dạng hỗn loạn dù kết quả đúng cũng khó sử dụng.

<strong>Tính mạch lạc của suy luận (Reasoning Coherence)</strong>: các bước suy luận có logic mạch lạc hay không. Chỉ số này thường cần đánh giá thủ công hoặc dùng mô hình đánh giá chuyên dụng.

<strong>Khả năng giải thích (Explainability)</strong>: đáp án có dễ hiểu và dễ kiểm chứng hay không. Đáp án chứa các bước rõ ràng có khả năng giải thích cao hơn đáp án đưa ra kết quả trực tiếp.

Như Bảng 11.7 cho thấy, so sánh các chỉ số khác nhau.

<div align="center">
  <p>Bảng 11.7 So sánh các chỉ số đánh giá</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-7.png" alt="" width="85%"/>
</div>


### 11.5.2 Thực hành đánh giá

HelloAgents cung cấp chức năng đánh giá toàn diện, có thể tính nhiều chỉ số cùng lúc.

```python
from hello_agents.tools import RLTrainingTool

rl_tool = RLTrainingTool()

# Đánh giá toàn diện
print("=" * 50)
print("Đánh giá toàn diện mô hình GRPO")
print("=" * 50)

result = rl_tool.run({
    "action": "evaluate",
    "model_path": "./models/grpo_full",
    "max_samples": 200,
    "use_lora": True,

    # Cấu hình đánh giá
    "metrics": [
        "accuracy",           # Độ chính xác
        "accuracy_at_k",      # Độ chính xác Top-K
        "average_length",     # Độ dài trung bình
        "average_steps",      # Số bước trung bình
        "format_correctness", # Tỷ lệ đúng định dạng
    ],
    "k": 3,  # Độ chính xác Top-3
})

# Phân tích kết quả
eval_data = json.loads(result)

# In kết quả
print(f"\nKết quả đánh giá:")
print(f"  Độ chính xác: {eval_data['accuracy']}")
print(f"  Phần thưởng trung bình: {eval_data['average_reward']}")
print(f"  Số mẫu kiểm tra: {eval_data['num_samples']}")
```

Chúng ta có thể so sánh hiệu năng của mô hình tiền huấn luyện, mô hình SFT, mô hình GRPO:

```python
# Đánh giá ba mô hình
models = [
    ("Mô hình tiền huấn luyện", "Qwen/Qwen3-0.6B", False),
    ("Mô hình SFT", "./models/sft_full", True),
    ("Mô hình GRPO", "./models/grpo_full", True),
]

results = []
for name, path, use_lora in models:
    print(f"\nĐánh giá {name}...")
    result = rl_tool.run({
        "action": "evaluate",
        "model_path": path,
        "max_samples": 200,
        "use_lora": use_lora,
        "metrics": ["accuracy", "average_length", "format_correctness"],
    })
    results.append((name, result))

# In bảng so sánh
print("\n" + "=" * 70)
print(f"{'Mô hình':<15} {'Độ chính xác':<12} {'Độ dài TB':<15} {'Đúng định dạng':<12}")
print("=" * 70)
for name, result in results:
    print(f"{name:<15} {result['accuracy']:<12.2%} {result['average_length']:<15.1f} {result['format_correctness']:<12.2%}")
print("=" * 70)
```

### 11.5.3 Phân tích lỗi

Chỉ biết độ chính xác là chưa đủ, chúng ta cần phân tích sâu mô hình dễ mắc lỗi ở loại bài toán nào, từ đó định hướng cải thiện tiếp theo. Lỗi của mô hình có thể chia thành bốn loại: lỗi tính toán (bước suy luận đúng nhưng tính sai, như “48/2=25”, cho thấy năng lực tính số chưa đủ), lỗi suy luận (lô-gíc suy luận sai dẫn đến hướng giải sai, như cộng trước rồi chia thay vì chia trước rồi cộng, cho thấy năng lực suy luận logic chưa đủ), lỗi hiểu đề (không hiểu đúng bài toán, như bài hỏi “tổng cộng” nhưng chỉ tính một phần, cho thấy năng lực hiểu ngôn ngữ chưa đủ), lỗi định dạng (đáp án đúng nhưng định dạng không đạt yêu cầu, như thiếu dấu “Final Answer:”, cho thấy học định dạng chưa đủ).

Ví dụ phân tích lỗi:

```python
from hello_agents.tools import RLTrainingTool

rl_tool = RLTrainingTool()

# Đánh giá và thu thập mẫu lỗi
result = rl_tool.run({
    "action": "evaluate",
    "model_path": "./models/grpo_full",
    "max_samples": 200,
    "use_lora": True,
    "return_details": True,  # Trả về kết quả chi tiết
})

# Phân tích mẫu lỗi
errors = result['errors']  # Danh sách mẫu lỗi
print(f"Tổng số lỗi: {len(errors)}")

# Phân loại theo loại lỗi
error_types = {
    "Lỗi tính toán": 0,
    "Lỗi suy luận": 0,
    "Lỗi hiểu đề": 0,
    "Lỗi định dạng": 0,
}

for error in errors:
    question = error['question']
    prediction = error['prediction']
    ground_truth = error['ground_truth']

    # Logic phân loại lỗi đơn giản (ứng dụng thực tế có thể cần phân tích phức tạp hơn)
    if "Final Answer:" not in prediction:
        error_types["Lỗi định dạng"] += 1
    elif "Step" in prediction:
        # Có bước suy luận, có thể là lỗi tính toán hoặc suy luận
        # Ở đây cần phân tích chi tiết hơn
        error_types["Lỗi tính toán"] += 1
    else:
        error_types["Lỗi hiểu đề"] += 1

# In phân bố lỗi
print("\nPhân bố loại lỗi:")
for error_type, count in error_types.items():
    percentage = count / len(errors) * 100
    print(f"  {error_type}: {count} ({percentage:.1f}%)")
```

Ví dụ đầu ra:

```bash
Tổng số lỗi: 76

Phân bố loại lỗi:
  Lỗi tính toán: 32 (42.1%)
  Lỗi suy luận: 18 (23.7%)
  Lỗi hiểu đề: 22 (28.9%)
  Lỗi định dạng: 4 (5.3%)
```

Có thể thấy, lỗi tính toán là loại lỗi chính (42.1%), cho thấy năng lực tính số của mô hình cần được tăng cường. Lỗi định dạng rất ít (5.3%), cho thấy huấn luyện SFT có hiệu quả tốt. Chúng ta cũng có thể phân tích hiệu năng của mô hình trên các bài toán có độ khó khác nhau:

```python
# Nhóm theo số bước suy luận
step_groups = {
    "Dễ (1-2 bước)": [],
    "Trung bình (3-4 bước)": [],
    "Khó (5+ bước)": [],
}

for sample in result['details']:
    steps = sample['ground_truth_steps']  # Số bước của đáp án thực
    correct = sample['correct']

    if steps <= 2:
        step_groups["Dễ (1-2 bước)"].append(correct)
    elif steps <= 4:
        step_groups["Trung bình (3-4 bước)"].append(correct)
    else:
        step_groups["Khó (5+ bước)"].append(correct)

# Tính độ chính xác của từng nhóm
print("\nĐộ chính xác theo độ khó:")
for group_name, results in step_groups.items():
    if len(results) > 0:
        accuracy = sum(results) / len(results)
        print(f"  {group_name}: {accuracy:.2%} ({len(results)} mẫu)")
```

Ví dụ đầu ra:

```bash
Độ chính xác theo độ khó:
  Dễ (1-2 bước): 78.50% (85 mẫu)
  Trung bình (3-4 bước): 58.30% (96 mẫu)
  Khó (5+ bước): 31.60% (19 mẫu)
```

Có thể thấy, mô hình thể hiện tốt trên bài toán dễ (78.5%), nhưng kém hơn trên bài toán khó (31.6%). Điều này cho thấy năng lực suy luận nhiều bước của mô hình vẫn cần được nâng cao

### 11.5.4 Hướng cải thiện

Dựa trên kết quả đánh giá và phân tích, chúng ta có thể xác định hướng cải thiện mô hình, như Hình 11.8 cho thấy.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-8.png" alt="" width="85%"/>
  <p>Hình 11.8 Quy trình lặp cải thiện mô hình</p>
</div>

Đây là một quá trình lặp liên tục: huấn luyện mô hình → đánh giá hiệu năng → phân tích lỗi → xác định vấn đề → chọn hướng cải thiện → huấn luyện lại. Qua nhiều lần lặp, hiệu năng mô hình sẽ không ngừng được nâng cao.

## 11.6 Thực hành quy trình huấn luyện hoàn chỉnh

Trong các mục trước, chúng ta đã lần lượt học chuẩn bị dữ liệu, huấn luyện SFT, huấn luyện GRPO và đánh giá mô hình. Bây giờ, hãy tích hợp những kiến thức này để hoàn thành một quy trình huấn luyện Agentic RL đầu-cuối.

### 11.6.1 Quy trình huấn luyện đầu-cuối

Một quy trình huấn luyện Agentic RL hoàn chỉnh gồm các giai đoạn sau: chuẩn bị dữ liệu, huấn luyện SFT, đánh giá SFT, huấn luyện GRPO, đánh giá GRPO, triển khai mô hình. Như Hình 11.9 cho thấy.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-9.png" alt="" width="85%"/>
  <p>Hình 11.9 Quy trình huấn luyện đầu-cuối</p>
</div>

Hãy hiện thực quy trình này qua một script hoàn chỉnh:

```python
"""
Quy trình huấn luyện Agentic RL hoàn chỉnh
Ví dụ đầu-cuối từ chuẩn bị dữ liệu đến triển khai mô hình
"""

from hello_agents.tools import RLTrainingTool
import json
from datetime import datetime

class AgenticRLPipeline:
    """Pipeline huấn luyện Agentic RL"""

    def __init__(self, config_path="config.json"):
        """
        Khởi tạo pipeline huấn luyện

        Args:
            config_path: Đường dẫn tệp cấu hình
        """
        self.rl_tool = RLTrainingTool()
        self.config = self.load_config(config_path)
        self.results = {}

    def load_config(self, config_path):
        """Tải tệp cấu hình"""
        with open(config_path, 'r') as f:
            return json.load(f)

    def log(self, message):
        """Ghi log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def stage1_prepare_data(self):
        """Giai đoạn 1: Chuẩn bị dữ liệu"""
        self.log("=" * 50)
        self.log("Giai đoạn 1: Chuẩn bị dữ liệu")
        self.log("=" * 50)

        # Tải và kiểm tra tập dữ liệu
        result = self.rl_tool.run({
            "action": "load_dataset",
            "format": "sft",
            "max_samples": self.config["data"]["max_samples"],
        })

        # Phân tích kết quả JSON
        dataset_info = json.loads(result)

        self.log(f"✓ Tải tập dữ liệu hoàn tất")
        self.log(f"  - Số mẫu: {dataset_info['dataset_size']}")
        self.log(f"  - Định dạng: {dataset_info['format']}")
        self.log(f"  - Cột dữ liệu: {', '.join(dataset_info['sample_keys'])}")

        self.results["data"] = dataset_info

        return dataset_info

    def stage2_sft_training(self):
        """Giai đoạn 2: Huấn luyện SFT"""
        self.log("\n" + "=" * 50)
        self.log("Giai đoạn 2: Huấn luyện SFT")
        self.log("=" * 50)

        sft_config = self.config["sft"]

        result = self.rl_tool.run({
            "action": "train",
            "algorithm": "sft",
            "model_name": self.config["model"]["base_model"],
            "output_dir": sft_config["output_dir"],
            "max_samples": self.config["data"]["max_samples"],
            "num_epochs": sft_config["num_epochs"],
            "batch_size": sft_config["batch_size"],
            "use_lora": True,
            # Cấu hình giám sát huấn luyện
            "use_wandb": self.config.get("monitoring", {}).get("use_wandb", False),
            "use_tensorboard": self.config.get("monitoring", {}).get("use_tensorboard", True),
            "wandb_project": self.config.get("monitoring", {}).get("wandb_project", None),
        })

        # Phân tích kết quả JSON
        result_data = json.loads(result)

        self.log(f"✓ Huấn luyện SFT hoàn tất")
        self.log(f"  - Đường dẫn mô hình: {result_data['output_dir']}")
        self.log(f"  - Trạng thái: {result_data['status']}")

        self.results["sft_training"] = result_data

        return result_data["output_dir"]

    def stage3_sft_evaluation(self, model_path):
        """Giai đoạn 3: Đánh giá SFT"""
        self.log("\n" + "=" * 50)
        self.log("Giai đoạn 3: Đánh giá SFT")
        self.log("=" * 50)

        result = self.rl_tool.run({
            "action": "evaluate",
            "model_path": model_path,
            "max_samples": self.config["eval"]["max_samples"],
            "use_lora": True,
        })
        eval_data = json.loads(result)

        self.log(f"✓ Đánh giá SFT hoàn tất")
        self.log(f"  - Độ chính xác: {eval_data['accuracy']}")
        self.log(f"  - Phần thưởng trung bình: {eval_data['average_reward']}")

        self.results["sft_evaluation"] = eval_data

        return eval_data

    def stage4_grpo_training(self, sft_model_path):
        """Giai đoạn 4: Huấn luyện GRPO"""
        self.log("\n" + "=" * 50)
        self.log("Giai đoạn 4: Huấn luyện GRPO")
        self.log("=" * 50)

        grpo_config = self.config["grpo"]

        result = self.rl_tool.run({
            "action": "train",
            "algorithm": "grpo",
            "model_name": sft_model_path,
            "output_dir": grpo_config["output_dir"],
            "max_samples": self.config["data"]["max_samples"],
            "num_epochs": grpo_config["num_epochs"],
            "batch_size": grpo_config["batch_size"],
            "use_lora": True,
            # Cấu hình giám sát huấn luyện
            "use_wandb": self.config.get("monitoring", {}).get("use_wandb", False),
            "use_tensorboard": self.config.get("monitoring", {}).get("use_tensorboard", True),
            "wandb_project": self.config.get("monitoring", {}).get("wandb_project", None),
        })

        # Phân tích kết quả JSON
        result_data = json.loads(result)

        self.log(f"✓ Huấn luyện GRPO hoàn tất")
        self.log(f"  - Đường dẫn mô hình: {result_data['output_dir']}")
        self.log(f"  - Trạng thái: {result_data['status']}")

        self.results["grpo_training"] = result_data

        return result_data["output_dir"]

    def stage5_grpo_evaluation(self, model_path):
        """Giai đoạn 5: Đánh giá GRPO"""
        self.log("\n" + "=" * 50)
        self.log("Giai đoạn 5: Đánh giá GRPO")
        self.log("=" * 50)

        result = self.rl_tool.run({
            "action": "evaluate",
            "model_path": model_path,
            "max_samples": self.config["eval"]["max_samples"],
            "use_lora": True,
        })
        eval_data = json.loads(result)

        self.log(f"✓ Đánh giá GRPO hoàn tất")
        self.log(f"  - Độ chính xác: {eval_data['accuracy']}")
        self.log(f"  - Phần thưởng trung bình: {eval_data['average_reward']}")

        self.results["grpo_evaluation"] = eval_data

        return eval_data

    def stage6_save_results(self):
        """Giai đoạn 6: Lưu kết quả"""
        self.log("\n" + "=" * 50)
        self.log("Giai đoạn 6: Lưu kết quả")
        self.log("=" * 50)

        # Lưu kết quả huấn luyện
        results_path = "training_results.json"
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        self.log(f"✓ Kết quả đã được lưu vào: {results_path}")

    def run(self):
        """Chạy toàn bộ quy trình"""
        try:
            # Giai đoạn 1: Chuẩn bị dữ liệu
            self.stage1_prepare_data()

            # Giai đoạn 2: Huấn luyện SFT
            sft_model_path = self.stage2_sft_training()

            # Giai đoạn 3: Đánh giá SFT
            self.stage3_sft_evaluation(sft_model_path)

            # Giai đoạn 4: Huấn luyện GRPO
            grpo_model_path = self.stage4_grpo_training(sft_model_path)

            # Giai đoạn 5: Đánh giá GRPO
            self.stage5_grpo_evaluation(grpo_model_path)

            # Giai đoạn 6: Lưu kết quả
            self.stage6_save_results()

            self.log("\n" + "=" * 50)
            self.log("✓ Quy trình huấn luyện hoàn tất!")
            self.log("=" * 50)

        except Exception as e:
            self.log(f"\n✗ Huấn luyện thất bại: {str(e)}")
            raise

# Ví dụ sử dụng
if __name__ == "__main__":
    # Tạo tệp cấu hình
    config = {
        "model": {
            "base_model": "Qwen/Qwen3-0.6B"
        },
        "data": {
            "max_samples": 1000  # Dùng 1000 mẫu
        },
        "sft": {
            "output_dir": "./models/sft_model",
            "num_epochs": 3,
            "batch_size": 8,
        },
        "grpo": {
            "output_dir": "./models/grpo_model",
            "num_epochs": 3,
            "batch_size": 4,
        },
        "eval": {
            "max_samples": 200,
            "sft_accuracy_threshold": 0.40  # Ngưỡng độ chính xác SFT
        },
        "monitoring": {
            "use_wandb": False,  # Có dùng Wandb hay không
            "use_tensorboard": True,  # Có dùng TensorBoard hay không
            "wandb_project": "agentic-rl-pipeline"  # Tên dự án Wandb
        }
    }

    # Lưu cấu hình
    with open("config.json", 'w') as f:
        json.dump(config, f, indent=2)

    # Chạy quy trình huấn luyện
    pipeline = AgenticRLPipeline("config.json")
    pipeline.run()
```

Chạy script này, bạn sẽ thấy toàn bộ quá trình huấn luyện.

Một vài khuyến nghị khi chạy:

<strong>Bắt đầu từ quy mô nhỏ</strong>: đừng dùng toàn bộ dữ liệu để huấn luyện ngay từ đầu. Trước tiên dùng 100-1000 mẫu để lặp nhanh, kiểm chứng quy trình và tham số, xác nhận hiệu quả rồi mới mở rộng quy mô. Như vậy có thể tiết kiệm lượng lớn thời gian và tài nguyên tính toán.

<strong>Kiểm tra chất lượng dữ liệu</strong>: trước khi huấn luyện, hãy kiểm tra chất lượng dữ liệu, đảm bảo định dạng đúng, đáp án chính xác, không có mẫu trùng lặp. Có thể dùng đoạn mã sau:

```python
def check_data_quality(dataset):
    """Kiểm tra chất lượng dữ liệu"""
    issues = []

    # Kiểm tra trường bắt buộc
    required_fields = ["prompt", "completion"]
    for field in required_fields:
        if field not in dataset.column_names:
            issues.append(f"Thiếu trường: {field}")

    # Kiểm tra giá trị rỗng
    for i, sample in enumerate(dataset):
        if not sample["prompt"] or not sample["completion"]:
            issues.append(f"Mẫu {i} chứa giá trị rỗng")

    # Kiểm tra trùng lặp
    prompts = [s["prompt"] for s in dataset]
    duplicates = len(prompts) - len(set(prompts))
    if duplicates > 0:
        issues.append(f"Phát hiện {duplicates} mẫu trùng lặp")

    return issues

# Sử dụng
issues = check_data_quality(dataset)
if issues:
    print("Vấn đề chất lượng dữ liệu:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("✓ Kiểm tra chất lượng dữ liệu đạt")
```

<strong>Tăng cường dữ liệu</strong>: nếu lượng dữ liệu không đủ, có thể cân nhắc tăng cường dữ liệu, như viết lại bài toán (giữ nguyên đáp án), sinh bài toán tương tự, dịch ngược (translate back). Tuy nhiên cần chú ý giữ chất lượng dữ liệu, tránh đưa vào nhiễu.

### 11.6.2 Tinh chỉnh siêu tham số

Tinh chỉnh siêu tham số là chìa khóa để nâng cao hiệu năng mô hình. Dưới đây là một số chiến lược tinh chỉnh thông dụng.

<strong>(1) Tìm kiếm lưới</strong>

Tìm kiếm lưới (Grid Search) là phương pháp tinh chỉnh đơn giản nhất, duyệt qua mọi tổ hợp tham số, chọn tổ hợp tốt nhất.

```python
# Định nghĩa lưới tham số
param_grid = {
    "learning_rate": [1e-5, 5e-5, 1e-4],
    "lora_rank": [8, 16, 32],
    "kl_coef": [0.05, 0.1, 0.2],
}

best_accuracy = 0
best_params = None

# Duyệt mọi tổ hợp
for lr in param_grid["learning_rate"]:
    for rank in param_grid["lora_rank"]:
        for kl in param_grid["kl_coef"]:
            print(f"Tham số thử: lr={lr}, rank={rank}, kl={kl}")

            # Huấn luyện mô hình
            result = rl_tool.run({
                "action": "train",
                "algorithm": "grpo",
                "learning_rate": lr,
                "lora_rank": rank,
                "kl_coef": kl,
                # Các tham số khác...
            })

            # Đánh giá mô hình
            eval_result = rl_tool.run({
                "action": "evaluate",
                "model_path": result["model_path"],
            })

            # Cập nhật tham số tốt nhất
            if eval_result["accuracy"] > best_accuracy:
                best_accuracy = eval_result["accuracy"]
                best_params = {"lr": lr, "rank": rank, "kl": kl}

print(f"Tham số tốt nhất: {best_params}")
print(f"Độ chính xác tốt nhất: {best_accuracy:.2%}")
```

Ưu điểm của tìm kiếm lưới là đơn giản trực tiếp, có thể tìm được tối ưu toàn cục. Nhược điểm là chi phí tính toán cao, không khả thi khi nhiều tham số.

<strong>(2) Tìm kiếm ngẫu nhiên</strong>

Tìm kiếm ngẫu nhiên (Random Search) lấy mẫu ngẫu nhiên các tổ hợp tham số, hiệu quả hơn tìm kiếm lưới.

```python
import random

# Định nghĩa phạm vi tham số
param_ranges = {
    "learning_rate": (1e-6, 1e-4),  # Phân phối log-uniform
    "lora_rank": [4, 8, 16, 32, 64],
    "kl_coef": (0.01, 0.5),
}

best_accuracy = 0
best_params = None

# Lấy mẫu ngẫu nhiên N lần
N = 10
for i in range(N):
    # Lấy mẫu tham số ngẫu nhiên
    lr = 10 ** random.uniform(-6, -4)  # Log-uniform
    rank = random.choice(param_ranges["lora_rank"])
    kl = random.uniform(0.01, 0.5)

    print(f"[{i+1}/{N}] Tham số thử: lr={lr:.2e}, rank={rank}, kl={kl:.3f}")

    # Huấn luyện và đánh giá (như trên)
    # ...

print(f"Tham số tốt nhất: {best_params}")
print(f"Độ chính xác tốt nhất: {best_accuracy:.2%}")
```

Ưu điểm của tìm kiếm ngẫu nhiên là hiệu quả cao, phù hợp khi không gian tham số lớn. Nhược điểm là có thể bỏ lỡ nghiệm tối ưu.

<strong>(3) Tối ưu Bayes</strong>

Tối ưu Bayes (Bayesian Optimization) dùng mô hình xác suất dẫn dắt tìm kiếm, thông minh hơn. Có thể dùng các thư viện như Optuna:

```python
import optuna

def objective(trial):
    """Hàm mục tiêu tối ưu"""
    # Lấy mẫu tham số
    lr = trial.suggest_loguniform("learning_rate", 1e-6, 1e-4)
    rank = trial.suggest_categorical("lora_rank", [8, 16, 32])
    kl = trial.suggest_uniform("kl_coef", 0.01, 0.5)

    # Huấn luyện mô hình
    result = rl_tool.run({
        "action": "train",
        "algorithm": "grpo",
        "learning_rate": lr,
        "lora_rank": rank,
        "kl_coef": kl,
        # Các tham số khác...
    })

    # Đánh giá mô hình
    eval_result = rl_tool.run({
        "action": "evaluate",
        "model_path": result["model_path"],
    })

    return eval_result["accuracy"]

# Tạo study
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=20)

# In tham số tốt nhất
print(f"Tham số tốt nhất: {study.best_params}")
print(f"Độ chính xác tốt nhất: {study.best_value:.2%}")
```

Ưu điểm của tối ưu Bayes là hiệu quả mẫu cao, có thể nhanh chóng tìm được tham số tốt. Nhược điểm là hiện thực phức tạp, cần thư viện bổ sung.

Như Bảng 11.8 cho thấy, so sánh các phương pháp tinh chỉnh khác nhau.

<div align="center">
  <p>Bảng 11.8 So sánh các phương pháp tinh chỉnh siêu tham số</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-8.png" alt="" width="85%"/>
</div>

### 11.6.3 Huấn luyện phân tán

Khi lượng dữ liệu và quy mô mô hình tăng lên, huấn luyện trên một GPU sẽ trở nên rất chậm. Lúc này chúng ta cần dùng huấn luyện phân tán để tăng tốc quá trình huấn luyện. HelloAgents dựa trên TRL và Hugging Face Accelerate, hỗ trợ tự nhiên huấn luyện phân tán đa GPU và đa nút

<strong>Khuyến nghị chọn phương án</strong>:

- <strong>Một máy nhiều card (2-8 card)</strong>: dùng DDP, đơn giản hiệu quả
- <strong>Mô hình lớn (>7B)</strong>: dùng DeepSpeed ZeRO-2 hoặc ZeRO-3
- <strong>Cụm đa nút</strong>: dùng DeepSpeed ZeRO-3 + Offload

<strong>(1) Cấu hình Accelerate</strong>

Trước tiên cần tạo tệp cấu hình Accelerate. Chạy lệnh sau:

```bash
accelerate config
```

Chọn cấu hình theo gợi ý:

```
In which compute environment are you running?
> This machine

Which type of machine are you using?
> multi-GPU

How many different machines will you use?
> 1

Do you wish to optimize your script with torch dynamo?
> NO

Do you want to use DeepSpeed?
> YES

Which DeepSpeed config file do you want to use?
> ZeRO-2

How many GPU(s) should be used for distributed training?
> 4
```

Lệnh này sẽ tạo tệp cấu hình tại `~/.cache/huggingface/accelerate/default_config.yaml`.

<strong>(2) Huấn luyện với DDP</strong>

<strong>Song song dữ liệu (DDP)</strong> là phương án phân tán đơn giản nhất, mỗi GPU giữ một bản sao đầy đủ của mô hình, dữ liệu được chia cho các GPU.

<strong>Tệp cấu hình Accelerate</strong> (`multi_gpu_ddp.yaml`):

```yaml
compute_environment: LOCAL_MACHINE
distributed_type: MULTI_GPU
num_processes: 4  # Số GPU
machine_rank: 0
num_machines: 1
gpu_ids: all
mixed_precision: fp16
```

<strong>Script huấn luyện</strong> (không cần sửa đổi):

```python
from hello_agents.tools import RLTrainingTool

rl_tool = RLTrainingTool()

# Mã huấn luyện hoàn toàn không đổi
result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./models/grpo_ddp",
    "num_epochs": 3,
    "batch_size": 4,  # Batch size của mỗi GPU
    "use_lora": True,
})
```

<strong>Khởi chạy huấn luyện</strong>:

```bash
# Dùng tệp cấu hình
accelerate launch --config_file multi_gpu_ddp.yaml train_script.py

# Hoặc chỉ định tham số trực tiếp
accelerate launch --num_processes 4 --mixed_precision fp16 train_script.py
```

<strong>(3) Huấn luyện với DeepSpeed ZeRO</strong>

<strong>DeepSpeed ZeRO</strong> giảm mạnh mức chiếm bộ nhớ GPU bằng cách phân mảnh trạng thái optimizer, gradient và tham số mô hình, hỗ trợ mô hình lớn hơn và batch size lớn hơn.

<strong>Tệp cấu hình ZeRO-2</strong> (`deepspeed_zero2.yaml`):

```yaml
compute_environment: LOCAL_MACHINE
distributed_type: DEEPSPEED
num_processes: 4
machine_rank: 0
num_machines: 1
gpu_ids: all
mixed_precision: fp16
deepspeed_config:
  gradient_accumulation_steps: 4
  gradient_clipping: 1.0
  offload_optimizer_device: none
  offload_param_device: none
  zero3_init_flag: false
  zero_stage: 2  # ZeRO-2
```

<strong>Tệp cấu hình ZeRO-3</strong> (`deepspeed_zero3.yaml`):

```yaml
compute_environment: LOCAL_MACHINE
distributed_type: DEEPSPEED
num_processes: 4
machine_rank: 0
num_machines: 1
gpu_ids: all
mixed_precision: fp16
deepspeed_config:
  gradient_accumulation_steps: 4
  gradient_clipping: 1.0
  offload_optimizer_device: cpu  # Chuyển trạng thái optimizer sang CPU
  offload_param_device: cpu      # Chuyển tham số sang CPU
  zero3_init_flag: true
  zero_stage: 3  # ZeRO-3
```

<strong>Khởi chạy huấn luyện</strong>:

```bash
# ZeRO-2
accelerate launch --config_file deepspeed_zero2.yaml train_script.py

# ZeRO-3
accelerate launch --config_file deepspeed_zero3.yaml train_script.py
```

Như Bảng 11.9 cho thấy, đây là so sánh mức chiếm bộ nhớ GPU khi huấn luyện mô hình Qwen3-0.6B bằng các cách khác nhau:

<div align="center">
  <p>Bảng 11.9 So sánh mức chiếm bộ nhớ GPU (mô hình Qwen3-0.6B)</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/11-figures/11-table-9.png" alt="" width="85%"/>
</div>

<strong>(4) Huấn luyện đa nút</strong>

Với huấn luyện quy mô cực lớn, có thể dùng nhiều nút (máy).

<strong>Cấu hình nút chính</strong> (`multi_node_main.yaml`):

```yaml
compute_environment: LOCAL_MACHINE
distributed_type: DEEPSPEED
num_processes: 16  # 4 nút x 4 GPU
machine_rank: 0    # Nút chính
num_machines: 4
main_process_ip: 192.168.1.100  # IP nút chính
main_process_port: 29500
gpu_ids: all
mixed_precision: fp16
deepspeed_config:
  zero_stage: 3
  offload_optimizer_device: cpu
  offload_param_device: cpu
```

<strong>Cấu hình nút làm việc</strong> (sửa `machine_rank` thành 1, 2, 3):

```yaml
machine_rank: 1  # Nút làm việc 1
# Các cấu hình khác giữ nguyên
```

<strong>Khởi chạy huấn luyện</strong>:

```bash
# Trên nút chính
accelerate launch --config_file multi_node_main.yaml train_script.py

# Trên nút làm việc 1
accelerate launch --config_file multi_node_worker1.yaml train_script.py

# Trên nút làm việc 2
accelerate launch --config_file multi_node_worker2.yaml train_script.py

# Trên nút làm việc 3
accelerate launch --config_file multi_node_worker3.yaml train_script.py
```

<strong>(5) Thực hành tốt nhất cho huấn luyện phân tán</strong>

<strong>1. Điều chỉnh Batch Size</strong>

Khi huấn luyện phân tán, tổng batch size = `per_device_batch_size × num_gpus × gradient_accumulation_steps`

```python
# Một GPU: batch_size=4, gradient_accumulation=4, tổng batch=16
# 4 GPU DDP: batch_size=4, gradient_accumulation=1, tổng batch=16 (giữ nhất quán)
```

<strong>2. Co giãn tốc độ học</strong>

Dùng quy tắc co giãn tuyến tính: `lr_new = lr_base × sqrt(total_batch_size_new / total_batch_size_base)`

```python
# Chuẩn: một GPU, batch=16, lr=5e-5
# 4 GPU: batch=64, lr=5e-5 × sqrt(64/16) = 1e-4
```

<strong>3. Giám sát và gỡ lỗi</strong>

```python
# Bật log chi tiết
export ACCELERATE_LOG_LEVEL=INFO

# Bật gỡ lỗi NCCL (đa nút)
export NCCL_DEBUG=INFO

# Kiểm tra mức sử dụng GPU
watch -n 1 nvidia-smi
```

### 11.6.4 Triển khai sản xuất

Sau khi huấn luyện xong, chúng ta cần triển khai mô hình vào môi trường sản xuất. Dưới đây là một số khuyến nghị triển khai.

<strong>(1) Xuất mô hình</strong>

Hợp nhất trọng số LoRA vào mô hình nền để thuận tiện triển khai:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Tải mô hình nền
base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B")

# Tải trọng số LoRA
model = PeftModel.from_pretrained(base_model, "./models/grpo_model")

# Hợp nhất trọng số
merged_model = model.merge_and_unload()

# Lưu mô hình đã hợp nhất
merged_model.save_pretrained("./models/merged_model")

# Lưu tokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
tokenizer.save_pretrained("./models/merged_model")

print("✓ Mô hình đã được xuất vào: ./models/merged_model")
```

<strong>(2) Tối ưu suy luận</strong>

Dùng kỹ thuật lượng tử hóa và tối ưu để tăng tốc suy luận:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Tải mô hình (dùng lượng tử hóa 8-bit)
model = AutoModelForCausalLM.from_pretrained(
    "./models/merged_model",
    load_in_8bit=True,  # Lượng tử hóa 8-bit
    device_map="auto",  # Tự động phân bổ thiết bị
)

tokenizer = AutoTokenizer.from_pretrained("./models/merged_model")

# Suy luận
def generate_answer(question):
    prompt = f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.7,
        do_sample=True,
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=False)
    return response

# Kiểm tra
question = "What is 48 + 24?"
answer = generate_answer(question)
print(answer)
```

<strong>(3) Dịch vụ API</strong>

Dùng FastAPI để tạo dịch vụ suy luận:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

app = FastAPI()

# Tải mô hình
model = AutoModelForCausalLM.from_pretrained("./models/merged_model")
tokenizer = AutoTokenizer.from_pretrained("./models/merged_model")

class Question(BaseModel):
    text: str
    max_tokens: int = 512

class Answer(BaseModel):
    text: str
    confidence: float

@app.post("/generate", response_model=Answer)
def generate(question: Question):
    """Sinh câu trả lời"""
    prompt = f"<|im_start|>user\n{question.text}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(prompt, return_tensors="pt")

    outputs = model.generate(
        **inputs,
        max_new_tokens=question.max_tokens,
        temperature=0.7,
        return_dict_in_generate=True,
        output_scores=True,
    )

    response = tokenizer.decode(outputs.sequences[0], skip_special_tokens=False)

    # Tính độ tin cậy (phiên bản đơn giản hóa)
    confidence = 0.8  # Thực tế nên tính dựa trên xác suất đầu ra

    return Answer(text=response, confidence=confidence)

# Chạy: uvicorn api:app --host 0.0.0.0 --port 8000
```



## 11.8 Tóm tắt chương

Trong chương này, chúng ta đã học một cách hệ thống lý thuyết và thực hành của Agentic RL, từ khái niệm nền tảng đến quy trình huấn luyện hoàn chỉnh, từ chuẩn bị dữ liệu đến triển khai mô hình. Hãy cùng ôn lại nội dung chính của chương này.

<strong>(1) Bản chất của Agentic RL</strong>

Agentic RL xem LLM như một chính sách có thể học, nhúng vào vòng lặp tri giác – quyết định – thực thi của Agent, và tối ưu hiệu năng của Agent trên nhiệm vụ nhiều bước bằng học tăng cường. Khác biệt cốt lõi của nó so với PBRFT (Preference-Based Reinforcement Fine-Tuning) truyền thống là:

- <strong>Tính chất nhiệm vụ</strong>: từ tối ưu hội thoại một lượt mở rộng thành quyết định tuần tự nhiều bước
- <strong>Không gian trạng thái</strong>: từ prompt tĩnh mở rộng thành trạng thái môi trường tiến hóa động
- <strong>Không gian hành động</strong>: từ sinh văn bản thuần túy mở rộng thành văn bản + công cụ + thao tác môi trường
- <strong>Thiết kế phần thưởng</strong>: từ đánh giá chất lượng một bước mở rộng thành lợi ích tích lũy dài hạn
- <strong>Mục tiêu tối ưu</strong>: từ chất lượng phản hồi ngắn hạn mở rộng thành thành công nhiệm vụ dài hạn

<strong>(2) Sáu năng lực cốt lõi</strong>

Agentic RL nhằm nâng cao sáu năng lực cốt lõi của Agent:

1. <strong>Suy luận (Reasoning)</strong>: suy diễn logic nhiều bước, học chiến lược suy luận
2. <strong>Sử dụng công cụ (Tool Use)</strong>: gọi API/công cụ, học khi nào dùng, dùng thế nào
3. <strong>Bộ nhớ (Memory)</strong>: giữ thông tin dài hạn, học quản lý bộ nhớ
4. <strong>Lập kế hoạch (Planning)</strong>: lập kế hoạch chuỗi hành động, học lập kế hoạch động
5. <strong>Tự cải thiện (Self-Improvement)</strong>: tự phản tư để tối ưu, học từ sai lầm
6. <strong>Tri giác (Perception)</strong>: hiểu đa phương thức, suy luận thị giác và sử dụng công cụ

<strong>(3) Quy trình huấn luyện</strong>

Quy trình huấn luyện Agentic RL hoàn chỉnh gồm:

1. <strong>Tiền huấn luyện (Pretraining)</strong>: học kiến thức ngôn ngữ trên văn bản quy mô lớn (thường dùng mô hình tiền huấn luyện có sẵn)
2. <strong>Tinh chỉnh có giám sát (SFT)</strong>: học định dạng nhiệm vụ và năng lực suy luận cơ bản
3. <strong>Học tăng cường (RL)</strong>: tối ưu chiến lược suy luận qua thử và sai, vượt qua chất lượng dữ liệu huấn luyện

Trong đó, SFT là nền tảng, RL là nâng cao. Không có nền tảng SFT, RL rất khó thành công; không có tối ưu RL, mô hình chỉ có thể bắt chước dữ liệu huấn luyện.

Nếu bạn muốn học sâu Agentic RL, khuyến nghị đi theo lộ trình sau:

Giai đoạn nền tảng

1. <strong>Nền tảng học tăng cường</strong>: học các khái niệm cơ bản như MDP, policy gradient, PPO
2. <strong>Nền tảng LLM</strong>: tìm hiểu Transformer, tiền huấn luyện, tinh chỉnh và các kỹ thuật khác
3. <strong>Thực hành HelloAgents</strong>: chạy mã ví dụ của chương này, hiểu quy trình hoàn chỉnh

Giai đoạn nâng cao

1. <strong>Đi sâu vào TRL</strong>: học hiện thực của thư viện TRL, hiểu chi tiết các thuật toán như SFT và GRPO
2. <strong>Tập dữ liệu tùy biến</strong>: dùng tập dữ liệu riêng để huấn luyện mô hình
3. <strong>Hàm phần thưởng tùy biến</strong>: thiết kế hàm phần thưởng phù hợp nhiệm vụ của bạn
4. <strong>Tinh chỉnh tham số</strong>: tinh chỉnh siêu tham số một cách hệ thống, nâng cao hiệu năng mô hình

Giai đoạn chuyên sâu

1. <strong>Suy luận nhiều bước</strong>: nghiên cứu nhiệm vụ suy luận chuỗi dài
2. <strong>Học sử dụng công cụ</strong>: giúp Agent học cách sử dụng công cụ
3. <strong>Đa Agent</strong>: nghiên cứu hợp tác giữa nhiều Agent
4. <strong>Bài báo tiên tiến</strong>: đọc các bài báo nghiên cứu mới nhất, theo dõi tiến bộ tiên tiến



Hy vọng chương này có thể giúp bạn hiểu và nắm vững kỹ thuật Agentic RL, áp dụng những kiến thức này trong dự án của mình, xây dựng hệ thống Agent thông minh hơn!



## Tài liệu tham khảo

[1] Schulman, J., Wolski, F., Dhariwal, P., Radford, A., & Klimov, O. (2017). Proximal Policy Optimization Algorithms. *arXiv preprint arXiv:1707.06347*.

[2] Shao, Z., Wang, P., Zhu, Q., Xu, R., Song, J., Zhang, M., ... & Guo, D. (2024). DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models. *arXiv preprint arXiv:2402.03300*.

[3] Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., ... & Chen, W. (2021). LoRA: Low-Rank Adaptation of Large Language Models. *arXiv preprint arXiv:2106.09685*.

[4] Cobbe, K., Kosaraju, V., Bavarian, M., Chen, M., Jun, H., Kaiser, L., ... & Schulman, J. (2021). Training Verifiers to Solve Math Word Problems. *arXiv preprint arXiv:2110.14168*.

[5] Ouyang, L., Wu, J., Jiang, X., Almeida, D., Wainwright, C., Mishkin, P., ... & Lowe, R. (2022). Training language models to follow instructions with human feedback. *Advances in Neural Information Processing Systems*, 35, 27730-27744.

[6] Rafailov, R., Sharma, A., Mitchell, E., Ermon, S., Manning, C. D., & Finn, C. (2023). Direct Preference Optimization: Your Language Model is Secretly a Reward Model. *arXiv preprint arXiv:2305.18290*.

[7] Lee, H., Phatale, S., Mansoor, H., Lu, K., Mesnard, T., Bishop, C., ... & Rastogi, A. (2023). RLAIF: Scaling Reinforcement Learning from Human Feedback with AI Feedback. *arXiv preprint arXiv:2309.00267*.

[8] Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., ... & Zhou, D. (2022). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. *Advances in Neural Information Processing Systems*, 35, 24824-24837.

[9] von Werra, L., Belkada, Y., Tunstall, L., Beeching, E., Thrush, T., Lambert, N., & Huang, S. (2020). TRL: Transformer Reinforcement Learning. *GitHub repository*. https://github.com/huggingface/trl

[10] Qwen Team. (2025). Qwen3 Technical Report. *arXiv preprint arXiv:2505.09388*.

[11] Bai, Y., Jones, A., Ndousse, K., Askell, A., Chen, A., DasSarma, N., ... & Kaplan, J. (2022). Training a Helpful and Harmless Assistant with Reinforcement Learning from Human Feedback. *arXiv preprint arXiv:2204.05862*.

[12] Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., ... & Zhou, D. (2022). Self-Consistency Improves Chain of Thought Reasoning in Language Models. *arXiv preprint arXiv:2203.11171*.

[13] Christiano, P. F., Leike, J., Brown, T., Martic, M., Legg, S., & Amodei, D. (2017). Deep Reinforcement Learning from Human Preferences. *Advances in Neural Information Processing Systems*, 30.

[14] Stiennon, N., Ouyang, L., Wu, J., Ziegler, D., Lowe, R., Voss, C., ... & Christiano, P. F. (2020). Learning to summarize with human feedback. *Advances in Neural Information Processing Systems*, 33, 3008-3021.

[15] Ziegler, D. M., Stiennon, N., Wu, J., Brown, T. B., Radford, A., Amodei, D., ... & Irving, G. (2019). Fine-Tuning Language Models from Human Preferences. *arXiv preprint arXiv:1909.08593*.

## Bài tập

> <strong>Gợi ý</strong>: Một số bài tập không có đáp án chuẩn, trọng điểm là rèn luyện năng lực hiểu và thực hành tổng hợp của người học về Agentic RL và huấn luyện Agent.

1. Chương này giới thiệu quá trình tiến hóa từ huấn luyện LLM đến Agentic RL. Hãy phân tích:

   - Trong Bảng 11.1 ở mục 11.1.3, đã so sánh khác biệt giữa PBRFT (tinh chỉnh học tăng cường dựa trên sở thích) và Agentic RL trong khung MDP. Hãy giải thích sâu: vì sao không gian trạng thái của Agentic RL $s_t = (\text{prompt}, o_1, o_2, ..., o_t)$ chứa quan sát lịch sử, còn trạng thái $s_0 = \text{prompt}$ của PBRFT chỉ chứa prompt ban đầu? Khác biệt này ảnh hưởng thế nào đến quá trình huấn luyện và kết quả cuối cùng?
   - Giả sử bạn cần huấn luyện một “trợ lý gỡ lỗi mã thông minh”, nó cần: (1) phân tích mã để tìm bug; (2) tra cứu tài liệu để hiểu cách dùng API; (3) sửa mã; (4) chạy kiểm tra để xác nhận hiệu quả sửa lỗi. Hãy ánh xạ nhiệm vụ này vào khung học tăng cường, định nghĩa rõ không gian trạng thái, không gian hành động, hàm phần thưởng và hàm chuyển trạng thái.
   - Trong mục 11.1.1 có nêu hạn chế “khó tối ưu mục tiêu dài hạn” của học có giám sát truyền thống. Hãy thiết kế một nhiệm vụ suy luận nhiều bước cụ thể (như chứng minh toán học, giải bài toán phức tạp), trình bày vì sao học có giám sát khó tối ưu các bước trung gian, còn học tăng cường có thể giải quyết vấn đề này nhờ phần thưởng trễ.

2. SFT (tinh chỉnh có giám sát) và GRPO (tối ưu chính sách tương đối theo nhóm) là hai phương pháp huấn luyện cốt lõi của chương này. Dựa trên nội dung mục 11.2 và 11.3, hãy suy nghĩ sâu:

   > <strong>Gợi ý</strong>: Đây là bài thực hành, khuyến nghị thao tác thực tế

   - Trong mã huấn luyện SFT ở mục 11.2.4, chúng ta dùng kỹ thuật LoRA (thích ứng hạng thấp) để giảm tham số huấn luyện. Hãy phân tích: tư tưởng cốt lõi của LoRA là gì? Vì sao nó có thể dùng lượng tham số nhỏ (như 0.16%) để đạt hiệu quả gần với tinh chỉnh toàn bộ tham số? Trong trường hợp nào nên chọn LoRA thay vì tinh chỉnh toàn bộ tham số?
   - Thuật toán GRPO (mục 11.3) có ưu điểm gì so với thuật toán PPO truyền thống? Hãy so sánh quy trình huấn luyện của hai thuật toán, phân tích cách GRPO đơn giản hóa quá trình huấn luyện và nâng cao tính ổn định bằng “phần thưởng tương đối trong nhóm”. Nếu muốn áp dụng GRPO cho nhiệm vụ khác (như sinh mã, tối ưu hội thoại), cần điều chỉnh những gì?
   - Dựa trên mã ở mục 11.2.5, hãy mở rộng quy trình huấn luyện SFT, thêm các chức năng sau: (1) hỗ trợ huấn luyện trên dữ liệu hội thoại nhiều lượt; (2) thêm chiến lược tăng cường dữ liệu (như viết lại đồng nghĩa, điều chỉnh độ khó); (3) hiện thực giám sát trực quan quá trình huấn luyện (như đường cong loss, đánh giá chất lượng mẫu).

3. Thiết kế hàm phần thưởng là thách thức cốt lõi của Agentic RL. Dựa trên nội dung mục 11.3.3, hãy hoàn thành các thực hành mở rộng sau:

   > <strong>Gợi ý</strong>: Đây là bài thực hành, khuyến nghị thao tác thực tế

   - Trong mục 11.3.3, chúng ta thiết kế phần thưởng nhị phân đơn giản cho bài toán GSM8K (đúng +1, sai 0). Hãy thiết kế một hàm phần thưởng tinh tế hơn, có thể: (1) trao phần thưởng bộ phận cho đáp án đúng một phần; (2) chấm điểm tính hợp lý của quá trình suy luận; (3) phạt những con đường giải quá dài dòng hoặc kém hiệu quả. Hàm phần thưởng này nên được hiện thực như thế nào?
   - Thiết kế hàm phần thưởng thường cần kiến thức lĩnh vực. Hãy thiết kế hàm phần thưởng cho ba nhiệm vụ Agent khác nhau: (1) trợ lý sinh mã (cần xét tính đúng đắn, khả năng đọc, hiệu quả của mã); (2) Agent hội thoại chăm sóc khách hàng (cần xét tỷ lệ giải quyết vấn đề, mức hài lòng của người dùng, thời gian phản hồi); (3) AI trò chơi (cần xét tỷ lệ thắng, tính đa dạng chiến lược, độ bền vững đối kháng).
   - Trong ứng dụng thực tế, hàm phần thưởng có thể tồn tại vấn đề “hack phần thưởng” (reward hacking): Agent tìm ra đường tắt để nhận phần thưởng cao nhưng không thực sự hoàn thành nhiệm vụ. Hãy nêu ví dụ về hiện tượng này và thiết kế cơ chế phòng vệ để tránh hack phần thưởng.

4. Trong trường hợp “huấn luyện Agent suy luận toán học” ở mục 11.4, chúng ta đã thấy quy trình huấn luyện hoàn chỉnh. Hãy phân tích sâu:

   - Trường hợp này dùng tập dữ liệu GSM8K để huấn luyện và đánh giá. Hãy phân tích: đặc điểm của tập dữ liệu này là gì? Nó phù hợp huấn luyện loại năng lực suy luận nào? Nếu muốn huấn luyện một Agent có thể xử lý bài toán phức tạp hơn (như toán cao cấp, chứng minh toán học), nên mở rộng tập dữ liệu và phương pháp huấn luyện như thế nào?
   - Trong kết quả huấn luyện ở mục 11.4.3, chúng ta quan sát độ chính xác trên tập huấn luyện tăng lên, nhưng có thể tồn tại nguy cơ quá khớp. Hãy thiết kế một phương án “đánh giá năng lực tổng quát hóa”: làm sao kiểm tra mô hình thực sự học được suy luận toán học thay vì ghi nhớ dữ liệu huấn luyện? Làm sao nâng cao năng lực tổng quát hóa bằng các kỹ thuật như chính quy hóa, tăng cường dữ liệu?
   - Huấn luyện trong trường hợp này là ngoại tuyến (dùng tập dữ liệu thu thập trước). Hãy thiết kế một phương án “học trực tuyến”: Agent liên tục thu thập phản hồi người dùng trong quá trình sử dụng thực tế và tự động cập nhật mô hình. Phương án này cần xét những thách thức kỹ thuật nào (như kiểm soát chất lượng dữ liệu, quên thảm khốc, bảo đảm an toàn)?

5. Một ứng dụng quan trọng của Agentic RL là giúp Agent học cách sử dụng công cụ. Hãy suy nghĩ:

   - Trong mục 11.1.3 có nêu Agentic RL phù hợp tối ưu các nhiệm vụ “cần suy luận nhiều bước, sử dụng công cụ, lập kế hoạch dài hạn”. Hãy thiết kế một phương án huấn luyện “học sử dụng công cụ”: cho một nhóm công cụ (như công cụ tìm kiếm, máy tính, trình thực thi mã), làm sao huấn luyện Agent học được thời điểm thích hợp để chọn công cụ phù hợp? Hàm phần thưởng nên được thiết kế như thế nào?
   - Sử dụng công cụ thường liên quan đến quan hệ phụ thuộc phức tạp (như “phải gọi công cụ A để lấy thông tin trước, mới có thể gọi công cụ B”). Hãy thiết kế một phương án “học tăng cường phân tầng”: chính sách tầng cao phụ trách lập kế hoạch nhiệm vụ, chính sách tầng thấp phụ trách gọi công cụ. Cấu trúc phân tầng này được huấn luyện như thế nào? Làm sao phối hợp mục tiêu tối ưu của tầng cao và tầng thấp?
   - Trong ứng dụng thực tế, số lượng công cụ có thể rất nhiều (như 50+ API), huấn luyện trực tiếp có thể gặp vấn đề “hiệu quả khám phá thấp”. Hãy thiết kế một phương án “học theo chương trình” (curriculum learning): bắt đầu huấn luyện từ nhiệm vụ đơn giản (dùng ít công cụ), dần tăng độ khó nhiệm vụ và số lượng công cụ. Phương án này nên thiết kế thứ tự chương trình như thế nào? Làm sao đánh giá Agent đã sẵn sàng bước sang giai đoạn tiếp theo chưa?

# Chương 3: Cơ sở mô hình ngôn ngữ lớn

Hai chương trước lần lượt giới thiệu định nghĩa và lịch sử phát triển của Agent, chương này sẽ hoàn toàn tập trung vào bản thân mô hình ngôn ngữ lớn để trả lời một câu hỏi then chốt: Agent hiện đại vận hành như thế nào? Chúng ta sẽ xuất phát từ định nghĩa cơ bản của mô hình ngôn ngữ, qua việc học các nguyên lý này, đặt nền tảng vững chắc cho việc hiểu cách LLM có được kho tri thức và năng lực suy luận mạnh mẽ.

## 3.1 Mô hình ngôn ngữ và kiến trúc Transformer

### 3.1.1 Từ N-gram đến RNN

**Mô hình ngôn ngữ (Language Model, LM)** là lõi của xử lý ngôn ngữ tự nhiên, nhiệm vụ căn bản của nó là tính xác suất xuất hiện của một chuỗi từ (tức một câu). Một mô hình ngôn ngữ tốt có thể cho chúng ta biết câu nào là trôi chảy, tự nhiên. Trong hệ thống đa Agent, mô hình ngôn ngữ là nền tảng để Agent hiểu chỉ thị của con người và sinh phản hồi. Mục này sẽ nhìn lại quá trình tiến hóa từ phương pháp thống kê kinh điển đến mô hình học sâu hiện đại, đặt nền tảng vững chắc cho việc hiểu kiến trúc Transformer tiếp theo.

**(1) Mô hình ngôn ngữ thống kê và tư tưởng N-gram**

Trước khi học sâu trỗi dậy, phương pháp thống kê là chủ lưu của mô hình ngôn ngữ. Tư tưởng cốt lõi là: xác suất xuất hiện của một câu bằng tích liên tiếp xác suất có điều kiện của từng từ trong câu đó. Với một câu S được tạo thành từ các từ $w_1,w_2,\cdots,w_m$, xác suất P(S) của nó có thể biểu diễn là:

$$P(S)=P(w_1,w_2,…,w_m)=P(w_1)⋅P(w_2∣w_1)⋅P(w_3∣w_1,w_2)⋯P(w_m∣w_1,…,w_{m−1})$$

Công thức này được gọi là quy tắc chuỗi của xác suất. Tuy nhiên, tính trực tiếp công thức này gần như bất khả thi, vì những xác suất có điều kiện như $P(w_m∣w_1,\cdots,w_{m−1})$ quá khó ước lượng từ kho ngữ liệu, chuỗi từ $w_1,\cdots,w_{m−1}$ có thể chưa từng xuất hiện trong dữ liệu huấn luyện.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/3-figures/1757249275674-0.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 3.1 Sơ đồ giả thuyết Markov</p>
</div>

Để giải quyết vấn đề này, các nhà nghiên cứu đưa vào **giả thuyết Markov (Markov Assumption)**. Tư tưởng cốt lõi là: chúng ta không cần truy hồi toàn bộ lịch sử của một từ, có thể xấp xỉ rằng xác suất xuất hiện của một từ chỉ phụ thuộc vào $n−1$ từ hữu hạn đứng trước nó, như trong Hình 3.1. Mô hình ngôn ngữ được xây dựng dựa trên giả thuyết này được gọi là **mô hình N-gram**. “N” ở đây đại diện cho kích thước cửa sổ ngữ cảnh mà chúng ta xét. Hãy xem vài ví dụ phổ biến nhất để hiểu khái niệm này:

- **Bigram (khi N=2)**: đây là trường hợp đơn giản nhất, chúng ta giả định xác suất xuất hiện của một từ chỉ phụ thuộc vào một từ đứng trước nó. Vì vậy, xác suất có điều kiện phức tạp $P(w_i∣w_1,\cdots,w_{i−1})$ trong quy tắc chuỗi có thể được xấp xỉ bằng dạng dễ tính hơn:

$$P(w_{i}∣w_{1},…,w_{i−1})≈P(w_{i}∣w_{i−1})$$

- **Trigram (khi N=3)**: tương tự, chúng ta giả định xác suất xuất hiện của một từ chỉ phụ thuộc vào hai từ đứng trước nó:

$$P(w_i∣w_1,…,w_{i−1})≈P(w_i∣w_{i−2},w_{i−1})$$

Những xác suất này có thể được tính bằng **ước lượng hợp lý cực đại (Maximum Likelihood Estimation, MLE)** trên kho ngữ liệu lớn. Thuật ngữ này nghe có vẻ phức tạp, nhưng tư tưởng của nó rất trực quan: thứ có khả năng xuất hiện nhất chính là thứ chúng ta thấy nhiều lần nhất trong dữ liệu. Ví dụ, với mô hình Bigram, chúng ta muốn tính xác suất $P(w_i∣w_{i−1})$ rằng sau khi từ $w_{i−1}$ xuất hiện, từ tiếp theo là $w_i$. Theo ước lượng hợp lý cực đại, xác suất này có thể được ước lượng bằng cách đếm đơn giản:

$$P(w_i∣w_{i−1})=\frac{Count(w_{i−1},w_i)}{Count(w_{i−1})}$$

Hàm `Count()` ở đây đại diện cho “đếm”:

- $Count(w_{i−1},w_i)$: tổng số lần cặp từ $(w_{i−1},w_i)$ xuất hiện liên tiếp trong kho ngữ liệu.
- $Count(w_{i−1})$: tổng số lần từ đơn $w_{i−1}$ xuất hiện trong kho ngữ liệu.

Ý nghĩa của công thức là: chúng ta lấy “số lần cặp từ $Count(w_{i−1},w_i)$ xuất hiện” chia cho “tổng số lần từ $Count(w_{i−1})$ xuất hiện”, làm một ước lượng xấp xỉ cho $P(w_i∣w_{i−1})$.

Để quá trình này cụ thể hơn, hãy thực hiện tính tay một lần. Giả sử chúng ta có một kho ngữ liệu mini chỉ gồm hai câu sau: `datawhale agent learns`, `datawhale agent works`. Mục tiêu của chúng ta là: dùng mô hình Bigram (N=2), ước lượng xác suất xuất hiện của câu `datawhale agent learns`. Theo giả định Bigram, mỗi lần chúng ta xét hai từ liên tiếp (tức một cặp từ).

**Bước một: tính xác suất của từ đầu tiên** $P(datawhale)$ Đây là số lần `datawhale` xuất hiện chia cho tổng số từ. `datawhale` xuất hiện 2 lần, tổng số từ là 6.

$$P(\text{datawhale}) = \frac{\text{số lượng "datawhale" trong toàn kho ngữ liệu}}{\text{số từ của toàn kho ngữ liệu}} = \frac{2}{6} \approx 0.333$$

**Bước hai: tính xác suất có điều kiện** $P(agent∣datawhale)$ Đây là số lần cặp từ `datawhale agent` xuất hiện chia cho tổng số lần `datawhale` xuất hiện. `datawhale agent` xuất hiện 2 lần, `datawhale` xuất hiện 2 lần.

$$P(\text{agent}|\text{datawhale}) =  \frac{\text{Count}(\text{datawhale agent})}{\text{Count}(\text{datawhale})} =  \frac{2}{2} = 1$$

**Bước ba: tính xác suất có điều kiện** $P(learns∣agent)$ Đây là số lần cặp từ `agent learns` xuất hiện chia cho tổng số lần `agent` xuất hiện. `agent learns` xuất hiện 1 lần, `agent` xuất hiện 2 lần.

$$P(\text{learns}|\text{agent}) =  \frac{\text{Count(agent learns)}}{\text{Count(agent)}} =  \frac{1}{2} = 0.5$$

**Cuối cùng: nhân liên tiếp các xác suất** Vậy xác suất xấp xỉ của toàn bộ câu là:

$$P(\text{datawhale agent learns}) \approx  P(\text{datawhale}) \cdot  P(\text{agent}|\text{datawhale}) \cdot  P(\text{learns}|\text{agent}) \approx  0.333 \cdot 1 \cdot 0.5 \approx 0.167$$

```Python
import collections

# Kho ngữ liệu ví dụ, giữ đồng nhất với kho ngữ liệu trong phần giải thích ca ở trên
corpus = "datawhale agent learns datawhale agent works"
tokens = corpus.split()
total_tokens = len(tokens)

# --- Bước một: tính P(datawhale) ---
count_datawhale = tokens.count('datawhale')
p_datawhale = count_datawhale / total_tokens
print(f"Bước một: P(datawhale) = {count_datawhale}/{total_tokens} = {p_datawhale:.3f}")

# --- Bước hai: tính P(agent|datawhale) ---
# Trước tiên tính bigrams cho các bước sau
bigrams = zip(tokens, tokens[1:])
bigram_counts = collections.Counter(bigrams)
count_datawhale_agent = bigram_counts[('datawhale', 'agent')]
# count_datawhale đã được tính ở bước một
p_agent_given_datawhale = count_datawhale_agent / count_datawhale
print(f"Bước hai: P(agent|datawhale) = {count_datawhale_agent}/{count_datawhale} = {p_agent_given_datawhale:.3f}")

# --- Bước ba: tính P(learns|agent) ---
count_agent_learns = bigram_counts[('agent', 'learns')]
count_agent = tokens.count('agent')
p_learns_given_agent = count_agent_learns / count_agent
print(f"Bước ba: P(learns|agent) = {count_agent_learns}/{count_agent} = {p_learns_given_agent:.3f}")

# --- Cuối cùng: nhân liên tiếp các xác suất ---
p_sentence = p_datawhale * p_agent_given_datawhale * p_learns_given_agent
print(f"Cuối cùng: P('datawhale agent learns') ≈ {p_datawhale:.3f} * {p_agent_given_datawhale:.3f} * {p_learns_given_agent:.3f} = {p_sentence:.3f}")

>>>
Bước một: P(datawhale) = 2/6 = 0.333
Bước hai: P(agent|datawhale) = 2/2 = 1.000
Bước ba: P(learns|agent) = 1/2 = 0.500
Cuối cùng: P('datawhale agent learns') ≈ 0.333 * 1.000 * 0.500 = 0.167
```

Mô hình N-gram tuy đơn giản và hiệu quả, nhưng có hai khiếm khuyết chí mạng:

1. **Thưa thớt dữ liệu (Sparsity)**: nếu một chuỗi từ chưa từng xuất hiện trong kho ngữ liệu, ước lượng xác suất của nó sẽ là 0, điều này rõ ràng không hợp lý. Dù có thể giảm nhẹ bằng kỹ thuật làm mượt (Smoothing), nhưng không thể loại trừ tận gốc.
2. **Khả năng tổng quát hóa kém:** mô hình không thể hiểu sự tương đồng ngữ nghĩa giữa các từ. Ví dụ, dù mô hình đã thấy `agent learns` nhiều lần trong kho ngữ liệu, nó cũng không thể tổng quát hóa tri thức này sang những từ tương đồng ngữ nghĩa. Khi chúng ta tính xác suất của `robot learns`, nếu từ `robot` chưa từng xuất hiện, hoặc tổ hợp `robot learns` chưa từng xuất hiện, xác suất mô hình tính được cũng sẽ bằng không. Mô hình không thể hiểu sự tương đồng ngữ nghĩa giữa `agent` và `robot`.

**(2) Mô hình ngôn ngữ mạng nơ-ron và nhúng từ**

Khiếm khuyết căn bản của mô hình N-gram là nó coi từ như những biểu tượng rời rạc, độc lập. Để khắc phục vấn đề này, các nhà nghiên cứu chuyển sang mạng nơ-ron, và đề xuất một tư tưởng: dùng vector liên tục để biểu diễn từ. Năm 2003, **mô hình ngôn ngữ mạng nơ-ron truyền thẳng (Feedforward Neural Network Language Model)** do Bengio và cộng sự đề xuất là cột mốc của lĩnh vực này<sup>[1]</sup>.

Tư tưởng cốt lõi có thể chia thành hai bước:

1. **Xây dựng một không gian ngữ nghĩa**: tạo một không gian vector liên tục nhiều chiều, sau đó ánh xạ mỗi từ trong từ vựng thành một điểm trong không gian đó. Điểm này (tức vector) được gọi là **nhúng từ (Word Embedding)** hay vector từ. Trong không gian này, những từ gần nhau về ngữ nghĩa có vị trí vector tương ứng cũng gần nhau. Ví dụ, vector của `agent` và `robot` sẽ ở gần nhau, còn vector của `agent` và `apple` sẽ cách xa nhau.
2. **Học ánh xạ từ ngữ cảnh đến từ tiếp theo**: tận dụng năng lực khớp mạnh mẽ của mạng nơ-ron để học một hàm. Đầu vào của hàm là vector từ của $n−1$ từ trước, đầu ra là phân bố xác suất của mỗi từ trong từ vựng xuất hiện sau ngữ cảnh hiện tại.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/3-figures/1757249275674-1.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 3.2 Sơ đồ kiến trúc mô hình ngôn ngữ mạng nơ-ron</p>
</div>

Như trong Hình 3.2, trong kiến trúc này, nhúng từ được học tự động trong quá trình huấn luyện mô hình. Để hoàn thành nhiệm vụ “dự đoán từ tiếp theo”, mô hình không ngừng điều chỉnh vị trí vector của mỗi từ, cuối cùng khiến những vector này chứa đựng thông tin ngữ nghĩa phong phú. Khi đã chuyển từ thành vector, chúng ta có thể dùng công cụ toán học để đo quan hệ giữa chúng. Phương pháp phổ biến nhất là **độ tương đồng cosin (Cosine Similarity)**, đo mức tương đồng bằng cách tính cosin của góc giữa hai vector.

$$\text{similarity}(\vec{a}, \vec{b}) = \cos(\theta) = \frac{\vec{a} \cdot \vec{b}}{|\vec{a}| |\vec{b}|}$$

Ý nghĩa của công thức này là:

- Nếu hai vector cùng hướng hoàn toàn, góc là 0°, cosin bằng 1, biểu thị tương quan hoàn toàn.
- Nếu hai vector vuông góc, góc là 90°, cosin bằng 0, biểu thị không có quan hệ.
- Nếu hai vector ngược hướng hoàn toàn, góc là 180°, cosin bằng -1, biểu thị tương quan âm hoàn toàn.

Bằng cách này, vector từ không chỉ nắm bắt được những quan hệ đơn giản như “từ đồng nghĩa”, mà còn nắm bắt được những quan hệ loại suy phức tạp hơn.

Một ví dụ nổi tiếng cho thấy quan hệ ngữ nghĩa mà vector từ nắm bắt được: `vector('King') - vector('Man') + vector('Woman')` kết quả của phép tính vector này, trong không gian vector, lại ở gần vị trí của `vector('Queen')` một cách đáng kinh ngạc. Điều này giống như thực hiện một phép dịch chuyển ngữ nghĩa: từ điểm “vua”, trừ vector “nam giới”, cộng vector “nữ giới”, cuối cùng ta đến vị trí của “nữ hoàng”. Điều này chứng minh nhúng từ có thể học được những khái niệm trừu tượng như “giới tính”, “hoàng gia”.

```Python
import numpy as np

# Giả sử chúng ta đã học được các vector từ hai chiều được đơn giản hóa
embeddings = {
    "king": np.array([0.9, 0.8]),
    "queen": np.array([0.9, 0.2]),
    "man": np.array([0.7, 0.9]),
    "woman": np.array([0.7, 0.3])
}

def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    return dot_product / norm_product

# king - man + woman
result_vec = embeddings["king"] - embeddings["man"] + embeddings["woman"]

# Tính độ tương đồng giữa vector kết quả và "queen"
sim = cosine_similarity(result_vec, embeddings["queen"])

print(f"Vector kết quả của king - man + woman: {result_vec}")
print(f"Độ tương đồng của kết quả với 'queen': {sim:.4f}")

>>>
Vector kết quả của king - man + woman: [0.9 0.2]
Độ tương đồng của kết quả với 'queen': 1.0000
```

Mô hình ngôn ngữ mạng nơ-ron, thông qua nhúng từ, đã giải quyết thành công vấn đề tổng quát hóa kém của mô hình N-gram. Tuy nhiên, nó vẫn có một hạn chế tương tự N-gram: cửa sổ ngữ cảnh là cố định. Nó chỉ có thể xét một số lượng từ phía trước cố định, điều này đặt nền móng cho mạng nơ-ron hồi tiếp, vốn có thể xử lý chuỗi dài tùy ý.

**(3) Mạng nơ-ron hồi tiếp (RNN) và mạng bộ nhớ dài - ngắn hạn (LSTM)**

Mô hình ngôn ngữ mạng nơ-ron ở mục trước tuy đưa vào nhúng từ để giải quyết vấn đề tổng quát hóa, nhưng giống mô hình N-gram, cửa sổ ngữ cảnh của nó có kích thước cố định. Để dự đoán từ tiếp theo, nó chỉ có thể thấy n−1 từ trước, thông tin lịch sử sớm hơn đã bị loại bỏ. Điều này rõ ràng không phù hợp với cách con người chúng ta hiểu ngôn ngữ. Để phá vỡ giới hạn cửa sổ cố định, **mạng nơ-ron hồi tiếp (Recurrent Neural Network, RNN)** ra đời, tư tưởng cốt lõi rất trực quan: thêm năng lực “ghi nhớ” cho mạng<sup>[2]</sup>.

Như trong Hình 3.3, thiết kế RNN đưa vào một vector **trạng thái ẩn (hidden state)**, có thể hiểu là bộ nhớ ngắn hạn của mạng. Ở mỗi bước xử lý chuỗi, mạng đọc từ đầu vào hiện tại, kết hợp với ký ức của thời điểm trước (tức trạng thái ẩn của bước thời gian trước), rồi sinh ra ký ức mới (tức trạng thái ẩn của bước thời gian hiện tại) truyền cho thời điểm tiếp theo. Quá trình lặp đi lặp lại này cho phép thông tin được truyền dần về phía sau trong chuỗi.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/3-figures/1757249275674-2.png" alt="Mô tả hình ảnh" width="90%"/>
  <p>Hình 3.3 Sơ đồ cấu trúc RNN</p>
</div>

Tuy nhiên, RNN chuẩn trong thực tiễn có một vấn đề nghiêm trọng: **vấn đề phụ thuộc dài hạn (Long-term Dependency Problem)**. Trong quá trình huấn luyện, mô hình cần điều chỉnh trọng số ở sâu trong mạng thông qua thuật toán lan truyền ngược dựa trên sai số ở đầu ra. Với RNN, độ dài chuỗi chính là độ sâu của mạng. Khi chuỗi rất dài, gradient trong quá trình lan truyền từ sau ra trước sẽ trải qua nhiều lần nhân liên tiếp, khiến giá trị gradient nhanh chóng tiến về 0 (**gradient biến mất**) hoặc trở nên cực lớn (**gradient bùng nổ**). Gradient biến mất khiến mô hình không thể học hiệu quả ảnh hưởng của thông tin sớm trong chuỗi tới đầu ra về sau, tức khó nắm bắt quan hệ phụ thuộc khoảng cách xa.

Để giải quyết vấn đề phụ thuộc dài hạn, **mạng bộ nhớ dài - ngắn hạn (Long Short-Term Memory, LSTM)** được thiết kế<sup>[3]</sup>. LSTM là một loại RNN đặc biệt, cải tiến cốt lõi của nó là đưa vào **trạng thái tế bào (Cell State)** và một bộ **cơ chế cổng (Gating Mechanism)** tinh vi. Trạng thái tế bào có thể được xem như một kênh thông tin độc lập với trạng thái ẩn, cho phép thông tin truyền giữa các bước thời gian trôi chảy hơn. Cơ chế cổng được tạo thành từ vài mạng nơ-ron nhỏ, chúng có thể học cách chọn lọc cho thông tin đi qua, từ đó kiểm soát việc thêm và loại bỏ thông tin trong trạng thái tế bào. Các cổng này gồm:

- **Cổng quên (Forget Gate)**: quyết định loại bỏ những thông tin nào khỏi trạng thái tế bào ở thời điểm trước.
- **Cổng vào (Input Gate)**: quyết định lưu những thông tin mới nào từ đầu vào hiện tại vào trạng thái tế bào.
- **Cổng ra (Output Gate)**: quyết định, dựa trên trạng thái tế bào hiện tại, xuất những thông tin nào ra trạng thái ẩn.

### 3.1.2 Phân tích kiến trúc Transformer

Ở mục trước, chúng ta thấy RNN và LSTM xử lý dữ liệu chuỗi bằng cách đưa vào cấu trúc hồi tiếp, điều này ở một mức độ nhất định đã giải quyết vấn đề nắm bắt phụ thuộc khoảng cách xa. Tuy nhiên, cách tính hồi tiếp này cũng mang lại nút cổ chai mới: nó phải xử lý dữ liệu theo thứ tự. Phép tính ở bước thời gian thứ t phải đợi bước thời gian thứ t−1 hoàn thành mới có thể bắt đầu. Điều này có nghĩa RNN không thể tính toán song song quy mô lớn, hiệu quả thấp khi xử lý chuỗi dài, hạn chế rất lớn việc nâng cao quy mô mô hình và tốc độ huấn luyện. Transformer được nhóm Google đề xuất năm 2017<sup>[4]</sup>. Nó hoàn toàn loại bỏ cấu trúc hồi tiếp, thay vào đó dựa hoàn toàn vào một cơ chế tên là **chú ý (Attention)** để nắm bắt quan hệ phụ thuộc trong chuỗi, từ đó hiện thực tính toán song song thực sự.

**(1) Cấu trúc tổng thể Encoder-Decoder**

Mô hình Transformer ban đầu được thiết kế cho nhiệm vụ đầu-cuối là dịch máy. Như trong Hình 3.4, ở tầng vĩ mô nó tuân theo một kiến trúc kinh điển **bộ mã hóa - bộ giải mã (Encoder-Decoder)**.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/3-figures/1757249275674-3.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 3.4 Sơ đồ kiến trúc tổng thể Transformer</p>
</div>


Chúng ta có thể hiểu cấu trúc này như một đội ngũ có phân công rõ ràng:

1. **Bộ mã hóa (Encoder)**: nhiệm vụ là “**hiểu**” toàn bộ câu đầu vào. Nó đọc tất cả token đầu vào (khái niệm này sẽ được giới thiệu ở mục 3.2.2), cuối cùng sinh ra cho mỗi token một biểu diễn vector giàu thông tin ngữ cảnh.
2. **Bộ giải mã (Decoder)**: nhiệm vụ là “**sinh**” câu mục tiêu. Nó tham khảo phần văn bản đã sinh trước đó của mình, và “hỏi ý kiến” kết quả hiểu của bộ mã hóa, để sinh từ tiếp theo.

Để thực sự hiểu nguyên lý làm việc của Transformer, cách tốt nhất không gì bằng tự tay hiện thực nó. Trong mục này, chúng ta sẽ áp dụng phương pháp “từ trên xuống”: trước tiên dựng khung mã hoàn chỉnh của Transformer, định nghĩa tất cả lớp và phương thức cần thiết. Sau đó, chúng ta sẽ như hoàn thành một bức tranh ghép, lần lượt hiện thực chức năng cụ thể của các lớp này.

```Python
import torch
import torch.nn as nn
import math

# --- Mô-đun giữ chỗ, sẽ được hiện thực ở các mục sau ---

class PositionalEncoding(nn.Module):
    """
    Mô-đun mã hóa vị trí
    """
    def forward(self, x):
        pass

class MultiHeadAttention(nn.Module):
    """
    Mô-đun cơ chế chú ý đa đầu
    """
    def forward(self, query, key, value, mask):
        pass

class PositionWiseFeedForward(nn.Module):
    """
    Mô-đun mạng truyền thẳng theo vị trí
    """
    def forward(self, x):
        pass

# --- Lớp lõi của bộ mã hóa ---

class EncoderLayer(nn.Module):
    def __init__(self, d_model, num_heads, d_ff, dropout):
        super(EncoderLayer, self).__init__()
        self.self_attn = MultiHeadAttention() # chờ hiện thực
        self.feed_forward = PositionWiseFeedForward() # chờ hiện thực
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask):
        # Kết nối dư và chuẩn hóa lớp sẽ được giải thích chi tiết ở mục 3.1.2.4
        # 1. Tự chú ý đa đầu
        attn_output = self.self_attn(x, x, x, mask)
        x = self.norm1(x + self.dropout(attn_output))

        # 2. Mạng truyền thẳng
        ff_output = self.feed_forward(x)
        x = self.norm2(x + self.dropout(ff_output))

        return x

# --- Lớp lõi của bộ giải mã ---

class DecoderLayer(nn.Module):
    def __init__(self, d_model, num_heads, d_ff, dropout):
        super(DecoderLayer, self).__init__()
        self.self_attn = MultiHeadAttention() # chờ hiện thực
        self.cross_attn = MultiHeadAttention() # chờ hiện thực
        self.feed_forward = PositionWiseFeedForward() # chờ hiện thực
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, encoder_output, src_mask, tgt_mask):
        # 1. Tự chú ý đa đầu có mặt nạ (với chính mình)
        attn_output = self.self_attn(x, x, x, tgt_mask)
        x = self.norm1(x + self.dropout(attn_output))

        # 2. Chú ý chéo (với đầu ra của bộ mã hóa)
        cross_attn_output = self.cross_attn(x, encoder_output, encoder_output, src_mask)
        x = self.norm2(x + self.dropout(cross_attn_output))

        # 3. Mạng truyền thẳng
        ff_output = self.feed_forward(x)
        x = self.norm3(x + self.dropout(ff_output))

        return x
```

**(2) Từ tự chú ý đến chú ý đa đầu**

Bây giờ, chúng ta hãy lấp đầy mô-đun then chốt nhất trong khung: cơ chế chú ý.

Hãy tưởng tượng chúng ta đọc câu này: “The agent learns because **it** is intelligent.”. Khi đọc tới “**it**” được in đậm, để hiểu nó chỉ cái gì, não chúng ta sẽ không tự giác dồn nhiều chú ý hơn vào từ “agent” phía trước. Cơ chế **tự chú ý (Self-Attention)** chính là mô hình hóa toán học cho hiện tượng này. Nó cho phép mô hình, khi xử lý mỗi từ trong chuỗi, đều có thể quan tâm tới tất cả các từ khác trong câu, và phân bổ cho những từ này những “trọng số chú ý” khác nhau. Từ có trọng số càng cao thể hiện mức liên quan với từ hiện tại càng mạnh, thông tin của nó cũng nên chiếm tỷ trọng lớn hơn trong biểu diễn của từ hiện tại.

Để hiện thực quá trình trên, cơ chế tự chú ý đưa vào cho mỗi vector token đầu vào ba vai trò có thể học:

- **Truy vấn (Query, Q)**: đại diện cho token hiện tại, nó đang chủ động “truy vấn” các token khác để lấy thông tin.
- **Khóa (Key, K)**: đại diện cho “nhãn” hoặc “chỉ mục” của các token có thể bị truy vấn trong câu.
- **Giá trị (Value, V)**: đại diện cho “nội dung” hoặc “thông tin” mà bản thân token mang theo.

Ba vector này đều được tạo ra bằng cách nhân vector nhúng từ gốc với ba ma trận trọng số khác nhau, có thể học ($W^Q,W^K,W^V$). Toàn bộ quá trình tính toán có thể chia thành các bước sau, có thể hình dung như một kỳ thi mở sách hiệu quả:

- Chuẩn bị “đề thi” và “tài liệu”: với mỗi từ trong câu, sinh vector $Q,K,V$ của nó thông qua ma trận trọng số.
- Tính điểm liên quan: để tính biểu diễn mới của từ $A$, dùng vector $Q$ của từ $A$ nhân vô hướng với vector $K$ của tất cả các từ trong câu (kể cả $A$). Điểm này phản ánh mức quan trọng của các từ khác đối với việc hiểu từ $A$.
- Ổn định hóa và chuẩn hóa: chia tất cả điểm thu được cho một hệ số tỉ lệ $\sqrt{d_{k}}$ ($d_{k}$ là số chiều của vector $K$) để tránh gradient quá nhỏ, sau đó dùng hàm Softmax chuyển điểm thành trọng số có tổng bằng 1, tức quá trình chuẩn hóa.
- Tổng có trọng số: nhân trọng số thu được ở bước trên với vector $V$ tương ứng của từng từ, rồi cộng tất cả kết quả lại. Vector cuối cùng thu được chính là biểu diễn mới của từ $A$ sau khi dung hợp thông tin ngữ cảnh toàn cục.

Quá trình này có thể được khái quát bằng một công thức ngắn gọn:

$$\text{Attention}(Q,K,V)=\text{softmax}\left(\frac{QK^{T}}{\sqrt{d_{k}}}\right)V$$

Nếu chỉ thực hiện một lần tính chú ý như trên (tức một đầu), mô hình có thể chỉ học được cách chú ý tới một loại liên quan. Ví dụ, khi xử lý “it”, nó có thể chỉ học được cách chú ý tới chủ ngữ. Nhưng quan hệ trong ngôn ngữ rất phức tạp, chúng ta muốn mô hình có thể đồng thời chú ý tới nhiều quan hệ (như quan hệ đại từ, quan hệ thì, quan hệ phụ thuộc, v.v.). Cơ chế chú ý đa đầu ra đời. Tư tưởng của nó rất đơn giản: biến việc làm một lần thành chia thành vài nhóm, làm riêng rồi hợp lại.

Nó chia các vector Q, K, V gốc theo chiều thành h phần (h chính là số “đầu”), mỗi phần độc lập thực hiện một lần tính chú ý một đầu. Điều này giống như để h “chuyên gia” khác nhau nhìn nhận câu từ những góc độ khác nhau, mỗi chuyên gia có thể nắm bắt một loại quan hệ đặc trưng khác nhau. Cuối cùng, “ý kiến” của h chuyên gia này (tức các vector đầu ra) được nối lại, rồi tích hợp qua một phép biến đổi tuyến tính, ta có đầu ra cuối cùng.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/3-figures/1757249275674-4.png" alt="Mô tả hình ảnh" width="50%"/>
  <p>Hình 3.5 Cơ chế chú ý đa đầu</p>
</div>


Như trong Hình 3.5, thiết kế này cho phép mô hình cùng chú ý tới thông tin từ các vị trí khác nhau, các không gian biểu diễn con khác nhau, nâng cao rất lớn năng lực biểu diễn của mô hình. Dưới đây là một hiện thực đơn giản của chú ý đa đầu để tham khảo.

```Python
class MultiHeadAttention(nn.Module):
    """
    Mô-đun cơ chế chú ý đa đầu
    """
    def __init__(self, d_model, num_heads):
        super(MultiHeadAttention, self).__init__()
        assert d_model % num_heads == 0, "d_model phải chia hết cho num_heads"

        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        # Định nghĩa các lớp biến đổi tuyến tính cho Q, K, V và đầu ra
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)

    def scaled_dot_product_attention(self, Q, K, V, mask=None):
        # 1. Tính điểm chú ý (QK^T)
        attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)

        # 2. Áp dụng mặt nạ (nếu có)
        if mask is not None:
            # Đặt vị trí bằng 0 trong mặt nạ thành một số âm rất lớn, để sau softmax sẽ gần 0
            attn_scores = attn_scores.masked_fill(mask == 0, -1e9)

        # 3. Tính trọng số chú ý (Softmax)
        attn_probs = torch.softmax(attn_scores, dim=-1)

        # 4. Tổng có trọng số (trọng số * V)
        output = torch.matmul(attn_probs, V)
        return output

    def split_heads(self, x):
        # Biến đổi kích thước của đầu vào x từ (batch_size, seq_length, d_model)
        # thành (batch_size, num_heads, seq_length, d_k)
        batch_size, seq_length, d_model = x.size()
        return x.view(batch_size, seq_length, self.num_heads, self.d_k).transpose(1, 2)

    def combine_heads(self, x):
        # Biến đổi kích thước của đầu vào x từ (batch_size, num_heads, seq_length, d_k)
        # trở lại (batch_size, seq_length, d_model)
        batch_size, num_heads, seq_length, d_k = x.size()
        return x.transpose(1, 2).contiguous().view(batch_size, seq_length, self.d_model)

    def forward(self, Q, K, V, mask=None):
        # 1. Thực hiện biến đổi tuyến tính trên Q, K, V
        Q = self.split_heads(self.W_q(Q))
        K = self.split_heads(self.W_k(K))
        V = self.split_heads(self.W_v(V))

        # 2. Tính chú ý tích vô hướng có tỉ lệ
        attn_output = self.scaled_dot_product_attention(Q, K, V, mask)

        # 3. Hợp nhất đầu ra nhiều đầu và thực hiện biến đổi tuyến tính cuối cùng
        output = self.W_o(self.combine_heads(attn_output))
        return output
```

**(3) Mạng nơ-ron truyền thẳng**

Trong mỗi lớp Encoder và Decoder, sau lớp con chú ý đa đầu đều có một **mạng truyền thẳng theo vị trí (Position-wise Feed-Forward Network, FFN)**. Nếu nói vai trò của lớp chú ý là “tổng hợp động” thông tin liên quan từ toàn bộ chuỗi, thì vai trò của mạng truyền thẳng là trích xuất đặc trưng bậc cao hơn từ những thông tin đã tổng hợp này.

Điểm then chốt của cái tên nằm ở “theo vị trí”. Nó có nghĩa mạng truyền thẳng này tác động độc lập lên từng vector token trong chuỗi. Nói cách khác, với một chuỗi có độ dài `seq_len`, FFN này thực tế được gọi `seq_len` lần, mỗi lần xử lý một token. Điều quan trọng là tất cả các vị trí chia sẻ cùng một bộ trọng số mạng. Thiết kế này vừa giữ được năng lực xử lý độc lập cho từng vị trí, vừa giảm mạnh số tham số của mô hình. Cấu trúc của mạng này rất đơn giản, gồm hai phép biến đổi tuyến tính và một hàm kích hoạt ReLU:

$$\mathrm{FFN}(x)=\max\left(0, xW_{1}+b_{1}\right) W_{2}+b_{2}$$

Trong đó, $x$ là đầu ra của lớp con chú ý. $W_1,b_1,W_2,b_2$ là các tham số có thể học. Thông thường, số chiều đầu ra `d_ff` của lớp tuyến tính thứ nhất lớn hơn nhiều so với số chiều đầu vào `d_model` (ví dụ `d_ff = 4 * d_model`), sau khi qua kích hoạt ReLU lại được ánh xạ về số chiều `d_model` qua lớp tuyến tính thứ hai. Mô hình “mở rộng trước rồi thu nhỏ” này được cho là giúp mô hình học được biểu diễn đặc trưng phong phú hơn.

Trong khung PyTorch của chúng ta, có thể dùng đoạn mã sau để hiện thực mô-đun này:

```Python
class PositionWiseFeedForward(nn.Module):
    """
    Mô-đun mạng truyền thẳng theo vị trí
    """
    def __init__(self, d_model, d_ff, dropout=0.1):
        super(PositionWiseFeedForward, self).__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.dropout = nn.Dropout(dropout)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.relu = nn.ReLU()

    def forward(self, x):
        # Kích thước x: (batch_size, seq_len, d_model)
        x = self.linear1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.linear2(x)
        # Kích thước đầu ra cuối cùng: (batch_size, seq_len, d_model)
        return x
```

**(4) Kết nối dư và chuẩn hóa lớp**

Trong mỗi lớp bộ mã hóa và bộ giải mã của Transformer, tất cả mô-đun con (như chú ý đa đầu và mạng truyền thẳng) đều được bao bọc bởi một thao tác `Add & Norm`. Sự kết hợp này nhằm bảo đảm Transformer có thể huấn luyện ổn định.

Thao tác này gồm hai phần:

- **Kết nối dư (Add)**: thao tác này cộng trực tiếp đầu vào `x` của mô-đun con với đầu ra `Sublayer(x)` của mô-đun con đó. Cấu trúc này giải quyết vấn đề **gradient biến mất (Vanishing Gradients)** trong mạng nơ-ron sâu. Khi lan truyền ngược, gradient có thể đi vòng qua mô-đun con để truyền thẳng về trước, từ đó bảo đảm dù số lớp mạng rất sâu, mô hình vẫn được huấn luyện hiệu quả. Công thức của nó có thể biểu diễn là: $\text{Output} = x + \text{Sublayer}(x)$.
- **Chuẩn hóa lớp (Norm)**: thao tác này chuẩn hóa tất cả đặc trưng của một mẫu đơn lẻ, đưa giá trị trung bình về 0, phương sai về 1. Điều này giải quyết vấn đề **dịch chuyển hiệp biến nội tại (Internal Covariate Shift)** trong quá trình huấn luyện mô hình, giữ phân bố đầu vào của mỗi lớp ổn định, từ đó tăng tốc hội tụ và nâng cao độ ổn định huấn luyện.

**3.1.2.5 Mã hóa vị trí**

Chúng ta đã biết lõi của Transformer là cơ chế tự chú ý, nó nắm bắt phụ thuộc bằng cách tính quan hệ giữa hai token bất kỳ trong chuỗi. Tuy nhiên, cách tính này có một vấn đề cố hữu: bản thân nó không chứa bất kỳ thông tin nào về thứ tự hay vị trí của token. Với tự chú ý, hai chuỗi “agent learns” và “learns agent” là hoàn toàn tương đương, vì nó chỉ quan tâm quan hệ giữa các token mà bỏ qua thứ tự sắp xếp của chúng. Để giải quyết vấn đề này, Transformer đưa vào **mã hóa vị trí (Positional Encoding)**.

Tư tưởng cốt lõi của mã hóa vị trí là: với mỗi vector nhúng của token trong chuỗi đầu vào, cộng thêm một “vector vị trí” có thể đại diện cho thông tin vị trí tuyệt đối và tương đối của nó. Vector vị trí này không được học mà được tính trực tiếp bằng một công thức toán học cố định. Nhờ vậy, dù hai token (ví dụ hai token đều là `agent`) có nhúng giống nhau, do vị trí của chúng trong câu khác nhau, vector cuối cùng đưa vào mô hình Transformer của chúng sẽ trở nên duy nhất nhờ cộng thêm mã hóa vị trí khác nhau. Mã hóa vị trí đề xuất trong bài báo gốc dùng hàm sin và cosin để sinh, công thức như sau:

$$PE_{(pos,2i)}=\sin\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)，$$

$$PE_{(pos,2i+1)}=\cos\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)$$

Trong đó:

- $pos$ là vị trí của token trong chuỗi (ví dụ $0$, $1$, $2$, ...)
- $i$ là chỉ số chiều trong vector vị trí (từ $0$ đến $d_{\text{model}}/2$)
- $d_{\text{model}}$ là số chiều của vector nhúng từ (đồng nhất với định nghĩa trong mô hình của chúng ta)

Bây giờ, chúng ta hãy hiện thực mô-đun `PositionalEncoding`, và hoàn thành phần cuối cùng của mã khung Transformer.

```Python
class PositionalEncoding(nn.Module):
    """
    Thêm mã hóa vị trí cho vector nhúng của chuỗi đầu vào.
    """
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        # Tạo một ma trận mã hóa vị trí đủ dài
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))

        # Kích thước của pe (positional encoding) là (max_len, d_model)
        pe = torch.zeros(max_len, d_model)

        # Chiều chẵn dùng sin, chiều lẻ dùng cos
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        # Đăng ký pe như buffer, để nó không bị coi là tham số mô hình nhưng vẫn di chuyển theo mô hình (ví dụ to(device))
        self.register_buffer('pe', pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x.size(1) là độ dài chuỗi của đầu vào hiện tại
        # Cộng mã hóa vị trí vào vector đầu vào
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)
```

Mục nhỏ này chủ yếu giúp hiểu cấu trúc vĩ mô của Transformer và chi tiết vận hành của từng mô-đun bên trong. Vì đây là phần bổ sung kiến thức về mô hình lớn trong việc học Agent, nên chúng ta không đi sâu hiện thực tiếp. Đến đây, chúng ta đã đặt nền tảng kiến trúc vững chắc cho việc hiểu mô hình ngôn ngữ lớn hiện đại. Ở mục tiếp theo, chúng ta sẽ thảo luận kiến trúc Decoder-Only, xem nó tiến hóa từ tư tưởng Transformer như thế nào.

### 3.1.3 Kiến trúc Decoder-Only

Ở mục trước, chúng ta đã tự tay xây dựng một mô hình Transformer hoàn chỉnh, nó thể hiện xuất sắc trong nhiều kịch bản đầu-cuối. Nhưng khi nhiệm vụ chuyển thành xây dựng một mô hình tổng quát để trò chuyện với con người, sáng tác, làm bộ não của Agent, có lẽ chúng ta không cần cấu trúc phức tạp đến vậy.

Triết lý thiết kế của Transformer là “hiểu trước, sinh sau”. Bộ mã hóa chịu trách nhiệm hiểu sâu toàn bộ câu đầu vào, tạo thành bộ nhớ ngữ cảnh chứa thông tin toàn cục, sau đó bộ giải mã dựa trên bộ nhớ đó để sinh bản dịch. Nhưng khi phát triển **GPT (Generative Pre-trained Transformer)**, OpenAI đã đề xuất một tư tưởng đơn giản hơn<sup>[5]</sup>: **nhiệm vụ cốt lõi của ngôn ngữ chẳng phải là dự đoán từ có khả năng xuất hiện cao nhất tiếp theo sao?**

Dù là trả lời câu hỏi, viết câu chuyện hay sinh mã, về bản chất đều là thêm từng từ một nội dung hợp lý nhất vào sau một chuỗi văn bản đã có. Dựa trên tư tưởng này, GPT đã thực hiện một sự đơn giản hóa táo bạo: **nó hoàn toàn loại bỏ bộ mã hóa, chỉ giữ lại phần bộ giải mã.** Đây là nguồn gốc của kiến trúc **Decoder-Only**.

Mô hình làm việc của kiến trúc Decoder-Only được gọi là **tự hồi quy (Autoregressive)**. Thuật ngữ nghe có vẻ chuyên nghiệp này thực ra mô tả một quá trình rất đơn giản:

1. Cho mô hình một văn bản khởi đầu (ví dụ “Datawhale Agent is”).
2. Mô hình dự đoán từ có khả năng xuất hiện cao nhất tiếp theo (ví dụ “a”).
3. Mô hình thêm từ “a” vừa sinh vào cuối văn bản đầu vào, tạo thành đầu vào mới (“Datawhale Agent is a”).
4. Mô hình dựa trên đầu vào mới này lại dự đoán từ tiếp theo (ví dụ “powerful”).
5. Lặp đi lặp lại quá trình này cho đến khi sinh xong câu hoàn chỉnh hoặc đạt điều kiện dừng.

Mô hình giống như đang chơi trò “nối chữ”, nó không ngừng “nhìn lại” nội dung mình đã viết, rồi nghĩ xem chữ tiếp theo nên viết gì.

Bạn có thể hỏi, khi huấn luyện mô hình thường nhận được toàn bộ văn bản trong một lần, vậy làm sao nó bảo đảm khi học dự đoán từ thứ `t+1` không “nhìn trộm” đáp án phía sau?

Câu trả lời chính là **tự chú ý có mặt nạ (Masked Self-Attention)**. Trong kiến trúc Decoder-Only, cơ chế này trở nên cực kỳ quan trọng. Nguyên lý của nó rất khéo léo:

Ở giai đoạn huấn luyện, dù một đoạn văn bản có thể được đưa song song vào mô hình, nhưng sau khi cơ chế tự chú ý tính ra ma trận điểm chú ý (tức điểm mức quan tâm của mỗi từ với tất cả các từ khác), và trước khi chuẩn hóa Softmax, mô hình sẽ áp dụng một “mặt nạ nhân quả”. Mặt nạ này thay tất cả điểm tương ứng với các token nằm sau vị trí hiện tại bằng một số âm rất lớn. Khi ma trận chứa điểm âm vô cực này đi qua hàm Softmax, xác suất của những vị trí đó sẽ trở thành 0. Nhờ vậy, khi tính biểu diễn cho bất kỳ vị trí nào, mô hình đều bị ngăn cản về mặt toán học không được chú ý tới thông tin phía sau nó.

Ở giai đoạn sinh thì trực tiếp hơn: token tương lai chưa được sinh ra, mô hình chỉ có thể lấy nội dung đã sinh làm ngữ cảnh đầu vào, và từng bước dự đoán từ tiếp theo. Tự chú ý có mặt nạ bảo đảm cách học khi huấn luyện nhất quán với cách dùng tự hồi quy khi sinh, từ đó khiến mô hình luôn chỉ dựa vào thông tin trước vị trí hiện tại.

**Ưu thế của kiến trúc Decoder-Only**

Kiến trúc có vẻ đơn giản này lại mang lại thành công to lớn, ưu thế của nó nằm ở:

- **Mục tiêu huấn luyện thống nhất**: nhiệm vụ duy nhất của mô hình là “dự đoán từ tiếp theo”, mục tiêu đơn giản này rất phù hợp để tiền huấn luyện trên khối dữ liệu văn bản không gán nhãn khổng lồ.
- **Cấu trúc đơn giản, dễ mở rộng**: ít thành phần hơn nghĩa là dễ mở rộng quy mô hơn. Những mô hình khổng lồ ngày nay như GPT-4, Llama với hàng trăm tỷ thậm chí hàng nghìn tỷ tham số, đều dựa trên kiến trúc gọn gàng này.
- **Phù hợp tự nhiên với nhiệm vụ sinh**: mô hình làm việc tự hồi quy của nó khớp hoàn hảo với mọi nhiệm vụ sinh (hội thoại, viết lách, sinh mã, v.v.), đây cũng là lý do cốt lõi khiến nó trở thành nền tảng xây dựng Agent tổng quát.

Tóm lại, kiến trúc Decoder-Only tiến hóa từ bộ giải mã của Transformer, thông qua mô hình đơn giản “dự đoán từ tiếp theo”, đã mở ra thời đại mô hình ngôn ngữ lớn mà chúng ta đang sống.

## 3.2 Tương tác với mô hình ngôn ngữ lớn

### 3.2.1 Kỹ thuật prompt

Nếu ví mô hình ngôn ngữ lớn như một “bộ não” năng lực cực mạnh, thì **prompt** chính là ngôn ngữ để chúng ta giao tiếp với “bộ não” đó. Kỹ thuật prompt là việc nghiên cứu cách thiết kế prompt chính xác, từ đó dẫn dắt mô hình sinh ra phản hồi mà chúng ta kỳ vọng. Với việc xây dựng Agent, một prompt được thiết kế cẩn thận có thể khiến sự phân công cộng tác giữa các Agent trở nên hiệu quả.


**(1) Tham số lấy mẫu của mô hình**

Khi dùng mô hình lớn, bạn sẽ thường thấy những tham số có thể cấu hình như `Temperature`; bản chất của chúng là điều chỉnh chiến lược lấy mẫu của mô hình trên “phân bố xác suất”, để đầu ra khớp với nhu cầu của kịch bản cụ thể. Cấu hình tham số phù hợp có thể nâng cao hiệu năng của Agent trong kịch bản cụ thể.

Phân bố xác suất truyền thống được tính bằng công thức Softmax: $p_i = \frac{e^{z_i}}{\sum_{j=1}^k e^{z_j}}$, bản chất của tham số lấy mẫu là trên cơ sở đó, “điều chỉnh lại” hoặc “cắt ngắn” phân bố theo các chiến lược khác nhau, từ đó thay đổi token tiếp theo mà mô hình lớn xuất ra.

`Temperature`: nhiệt độ là tham số then chốt kiểm soát “tính ngẫu nhiên” và “tính xác định” của đầu ra mô hình. Nguyên lý là đưa vào hệ số nhiệt độ $T\gt0$, viết lại Softmax thành $p_i^{(T)} = \frac{e^{z_i / T}}{\sum_{j=1}^k e^{z_j / T}}$.

Khi T nhỏ đi, phân bố “dốc hơn”, trọng số của các mục xác suất cao được khuếch đại thêm, sinh ra văn bản “bảo thủ” hơn và có tỷ lệ lặp cao hơn. Khi T lớn lên, phân bố “phẳng hơn”, trọng số của các mục xác suất thấp được nâng lên, sinh ra nội dung “đa dạng” hơn nhưng có thể mất liên kết.

- Ở nhiệt độ thấp (0 $\leqslant$ Temperature $\lt$ 0.3), đầu ra “chính xác, xác định” hơn. Kịch bản áp dụng: nhiệm vụ sự thật: như hỏi đáp, tính toán dữ liệu, sinh mã; kịch bản đòi hỏi nghiêm ngặt: giải thích điều luật, viết tài liệu kỹ thuật, giải thích khái niệm học thuật, v.v.

- Ở nhiệt độ trung bình (0.3 $\leqslant$ Temperature $\lt$ 0.7): đầu ra “cân bằng, tự nhiên”. Kịch bản áp dụng: hội thoại hằng ngày: như tương tác chăm sóc khách hàng, chatbot; sáng tạo thông thường: như soạn email, viết nội dung sản phẩm, sáng tác truyện đơn giản.

- Ở nhiệt độ cao (0.7 $\leqslant$ Temperature $\lt$ 2): đầu ra “sáng tạo, phân kỳ”. Kịch bản áp dụng: nhiệm vụ sáng tạo: như sáng tác thơ, hình dung truyện khoa học viễn tưởng, brainstorm slogan quảng cáo, gợi cảm hứng nghệ thuật; tư duy phân kỳ.

`Top-k`: nguyên lý là sắp xếp tất cả token theo xác suất từ cao xuống thấp, lấy k token đứng đầu tạo thành “tập ứng viên”, sau đó “chuẩn hóa” xác suất của k token đã lọc: $ \hat{p}_i = \frac{p_i}{\sum_{j \in \text{tập ứng viên}} p_j}$

- Khác biệt và liên hệ với lấy mẫu nhiệt độ: lấy mẫu nhiệt độ điều chỉnh phân bố xác suất của tất cả token thông qua nhiệt độ T (làm mượt hoặc làm dốc), không thay đổi số lượng token ứng viên (vẫn xét toàn bộ N). Lấy mẫu Top-k giới hạn số lượng token ứng viên thông qua giá trị k (chỉ giữ k token xác suất cao nhất), rồi lấy mẫu từ đó. Khi k=1 đầu ra hoàn toàn xác định, thoái hóa thành “lấy mẫu tham lam”.

`Top-p`: nguyên lý là sắp xếp tất cả token theo xác suất từ cao xuống thấp, bắt đầu từ token đầu tiên sau khi sắp xếp, cộng dồn xác suất dần, cho đến khi tổng tích lũy lần đầu đạt hoặc vượt ngưỡng p: $\sum_{i \in S} p_{(i)} \geq p$, khi đó tất cả token được bao gồm trong quá trình cộng dồn tạo thành “tập hạt nhân”, cuối cùng chuẩn hóa tập hạt nhân.

- Khác biệt và liên hệ với Top-k: so với Top-k có kích thước cắt cố định, Top-p có thể thích ứng động với đặc tính “đuôi dài” của các phân bố khác nhau, thích ứng tốt hơn với những trường hợp cực đoan khi phân bố xác suất không đồng đều.


Trong sinh văn bản, khi đồng thời đặt Top-p, Top-k và hệ số nhiệt độ, các tham số này sẽ phối hợp theo cách lọc phân tầng, thứ tự ưu tiên là: điều chỉnh nhiệt độ → Top-k → Top-p. Điều chỉnh nhiệt độ thay đổi độ dốc của toàn bộ phân bố, Top-k trước tiên giữ k ứng viên có xác suất cao nhất, sau đó Top-p chọn từ kết quả của Top-k tập nhỏ nhất có xác suất tích lũy ≥ p làm tập ứng viên cuối cùng. Tuy nhiên, thông thường chỉ cần chọn một trong hai là Top-k hoặc Top-p; nếu đặt đồng thời, tập ứng viên thực tế là giao của cả hai.
Cần lưu ý, nếu đặt nhiệt độ bằng 0, thì Top-k và Top-p sẽ trở nên không quan trọng, vì token có khả năng xuất hiện cao nhất sẽ trở thành token được dự đoán tiếp theo; nếu đặt Top-k bằng 1, nhiệt độ và Top-p cũng trở nên không quan trọng, vì chỉ có một token đáp ứng tiêu chuẩn Top-k, nó sẽ là token được dự đoán tiếp theo.



**(2) Prompt zero-shot, one-shot và few-shot**

Dựa trên số lượng ví dụ (Exemplar) mà chúng ta cung cấp cho mô hình, prompt có thể chia thành ba loại. Để hiểu rõ hơn, hãy lấy nhiệm vụ phân loại cảm xúc làm ví dụ, mục tiêu là để mô hình phán đoán sắc thái cảm xúc của một đoạn văn bản (như tích cực, tiêu cực hoặc trung tính).

**Prompt zero-shot (Zero-shot Prompting)** Điều này có nghĩa chúng ta không đưa cho mô hình bất kỳ ví dụ nào, trực tiếp để nó hoàn thành nhiệm vụ theo chỉ thị. Điều này nhờ năng lực tổng quát hóa mạnh mẽ mà mô hình có được sau khi tiền huấn luyện trên khối dữ liệu khổng lồ.

Ca ví dụ: chúng ta trực tiếp ra chỉ thị cho mô hình, yêu cầu nó hoàn thành nhiệm vụ phân loại cảm xúc.

```Python
Văn bản: Khóa học AI Agent của Datawhale rất tuyệt!
Cảm xúc: Tích cực
```

**Prompt one-shot (One-shot Prompting)** Chúng ta cung cấp cho mô hình một ví dụ hoàn chỉnh, cho nó thấy định dạng nhiệm vụ và phong cách đầu ra kỳ vọng.

Ca ví dụ: trước tiên chúng ta đưa cho mô hình một cặp “câu hỏi - đáp án” hoàn chỉnh làm mẫu, sau đó đặt câu hỏi mới.

```Python
Văn bản: Dịch vụ của nhà hàng này quá chậm.
Cảm xúc: Tiêu cực

Văn bản: Khóa học AI Agent của Datawhale rất tuyệt!
Cảm xúc:
```

Mô hình sẽ bắt chước định dạng ví dụ được đưa, điền “Tích cực” cho đoạn văn bản thứ hai.

**Prompt few-shot (Few-shot Prompting)** Chúng ta cung cấp nhiều ví dụ, điều này giúp mô hình hiểu chính xác hơn chi tiết, ranh giới và sắc thái tinh tế của nhiệm vụ, từ đó đạt hiệu năng tốt hơn.

Ca ví dụ: chúng ta cung cấp nhiều ví dụ bao quát các tình huống khác nhau, để mô hình hiểu nhiệm vụ toàn diện hơn.

```Python
Văn bản: Dịch vụ của nhà hàng này quá chậm.
Cảm xúc: Tiêu cực

Văn bản: Tình tiết của bộ phim này rất nhạt nhòa.
Cảm xúc: Trung tính

Văn bản: Khóa học AI Agent của Datawhale rất tuyệt!
Cảm xúc:
```

Mô hình sẽ tổng hợp tất cả ví dụ, phân loại cảm xúc của câu cuối cùng thành “Tích cực” chính xác hơn.

**(3) Ảnh hưởng của tinh chỉnh chỉ thị**

Các mô hình GPT thời kỳ đầu (như GPT-3) chủ yếu là mô hình “hoàn thiện văn bản”, chúng giỏi viết tiếp theo đoạn văn phía trước, nhưng không nhất thiết hiểu và thực thi tốt chỉ thị của con người.

**Tinh chỉnh chỉ thị (Instruction Tuning)** là một kỹ thuật tinh chỉnh, dùng lượng lớn dữ liệu định dạng “chỉ thị - trả lời” để huấn luyện thêm cho mô hình đã tiền huấn luyện. Sau khi tinh chỉnh chỉ thị, mô hình có thể hiểu và tuân theo chỉ thị của người dùng tốt hơn. Tất cả mô hình mà chúng ta dùng hằng ngày trong công việc và học tập (như `ChatGPT`, `DeepSeek`, `Qwen`) đều là mô hình đã được tinh chỉnh chỉ thị trong dòng mô hình của chúng.

- **Prompt cho mô hình “hoàn thiện văn bản” (bạn cần dùng prompt few-shot để “dạy” mô hình làm gì):**

```Plain
Đây là một chương trình dịch tiếng Anh sang tiếng Trung.
Tiếng Anh: Hello
Tiếng Trung: 你好
Tiếng Anh: How are you?
Tiếng Trung:
```

- **Prompt cho mô hình “tinh chỉnh chỉ thị” (bạn có thể ra chỉ thị trực tiếp):**

```Plain
Hãy dịch đoạn tiếng Anh sau sang tiếng Trung:
How are you?
```

Sự xuất hiện của tinh chỉnh chỉ thị đã đơn giản hóa rất lớn cách chúng ta tương tác với mô hình, khiến chỉ thị ngôn ngữ tự nhiên trực tiếp, rõ ràng trở nên khả thi.

**(4) Kỹ thuật prompt cơ bản**

**Nhập vai (Role-playing)** Bằng cách gán cho mô hình một vai trò cụ thể, chúng ta có thể dẫn dắt phong cách trả lời, giọng điệu và phạm vi tri thức của nó, khiến đầu ra phù hợp hơn với nhu cầu của kịch bản cụ thể.

```Plain
# Ca ví dụ
Bây giờ bạn là một chuyên gia lập trình Python kỳ cựu. Hãy giải thích GIL (Global Interpreter Lock) trong Python là gì, theo cách mà người mới học cũng hiểu được.
```

**Ví dụ trong ngữ cảnh (In-context Example)** Điều này nhất quán với tư tưởng prompt few-shot, thông qua việc cung cấp ví dụ đầu vào - đầu ra rõ ràng trong prompt, để “dạy” mô hình cách xử lý yêu cầu của chúng ta, đặc biệt hiệu quả khi xử lý nhiệm vụ có định dạng phức tạp hoặc phong cách đặc thù.

```Plain
# Ca ví dụ
Tôi cần bạn trích xuất tên sản phẩm và cảm xúc người dùng từ đánh giá sản phẩm. Hãy xuất đúng theo định dạng JSON dưới đây.

Đánh giá: Màn hình của chiếc laptop "Stardust" này hiển thị đẹp đến kinh ngạc, nhưng tôi không thích cảm giác gõ bàn phím của nó lắm.
Đầu ra: {"product_name": "Stardust laptop", "sentiment": "Hỗn hợp"}

Đánh giá: Tai nghe "SoundWave" tôi vừa mua có chất âm rất tốt, thời lượng pin cũng vượt kỳ vọng của tôi!
Đầu ra:
```

**(5) Chuỗi suy nghĩ**

Với những vấn đề phức tạp cần suy luận logic, tính toán hoặc tư duy nhiều bước, để mô hình trả lời trực tiếp thường dễ sai. **Chuỗi suy nghĩ (Chain-of-Thought, CoT)** là một kỹ thuật prompt mạnh mẽ, nó nâng cao năng lực suy luận của mô hình trên các nhiệm vụ phức tạp bằng cách dẫn dắt mô hình “suy nghĩ từng bước một”.

Chìa khóa để hiện thực CoT là thêm vào prompt một câu dẫn đơn giản, như “Hãy suy nghĩ từng bước” hoặc “Let's think step by step”.

```Plain
# Prompt chuỗi suy nghĩ
Một đội bóng rổ thắng 60% trong 80 trận của một mùa giải. Ở mùa giải tiếp theo, họ chơi 15 trận và thắng 12 trận. Tỷ lệ thắng của cả hai mùa giải là bao nhiêu?
Hãy suy nghĩ từng bước và giải.

>>>
(mô hình có thể xuất ra)
Được, chúng ta hãy tính từng bước.
Bước một: tính số trận thắng của mùa giải đầu tiên.
80 trận * 60% = 48 trận.
Bước hai: tính tổng số trận và tổng số trận thắng của hai mùa giải.
Tổng số trận = 80 + 15 = 95 trận.
Tổng số trận thắng = 48 + 12 = 60 trận.
Bước ba: tính tỷ lệ thắng tổng.
Tỷ lệ thắng tổng = (tổng số trận thắng / tổng số trận) * 100% = (60 / 95) * 100% ≈ 63.16%.
Vậy tỷ lệ thắng của cả hai mùa giải khoảng 63.16%.
```

Bằng cách thể hiện rõ quá trình suy luận của mình, mô hình không chỉ dễ đạt câu trả lời đúng hơn, mà còn khiến câu trả lời trở nên đáng tin cậy hơn, dễ để chúng ta kiểm tra và sửa chữa.

### 3.2.2 Phân tách văn bản

Chúng ta biết máy tính về bản chất chỉ hiểu được con số. Vì vậy, trước khi đưa văn bản ngôn ngữ tự nhiên vào mô hình ngôn ngữ lớn, phải chuyển nó thành định dạng số mà mô hình có thể xử lý. Quá trình chuyển chuỗi văn bản thành chuỗi số này được gọi là **phân tách (Tokenization)**. Vai trò của **bộ phân tách (Tokenizer)** là định nghĩa một bộ quy tắc, chia văn bản gốc thành từng đơn vị nhỏ nhất, chúng ta gọi đó là **token**.

**3.2.2.1 Vì sao cần phân tách**

Các nhiệm vụ xử lý ngôn ngữ tự nhiên thời kỳ đầu có thể dùng chiến lược phân tách đơn giản:

- **Phân tách theo từ (Word-based)**: dùng trực tiếp dấu cách hoặc dấu câu để chia câu thành các từ. Phương pháp này rất trực quan, nhưng cũng gặp thách thức:
  - Bùng nổ từ vựng và từ chưa đăng ký: vốn từ của một ngôn ngữ là khổng lồ, nếu mỗi từ là một token độc lập, từ vựng sẽ trở nên khó quản lý. Tệ hơn, mô hình sẽ không thể xử lý bất kỳ từ nào chưa xuất hiện trong từ vựng (như “DatawhaleAgent”), hiện tượng này được gọi là “từ chưa đăng ký” (Out-Of-Vocabulary, OOV).
  - Thiếu liên hệ ngữ nghĩa: mô hình khó nắm bắt quan hệ ngữ nghĩa giữa các từ có hình thái gần nhau. Ví dụ, "look", "looks" và "looking" sẽ bị coi là ba token hoàn toàn khác nhau, dù chúng có chung ý nghĩa cốt lõi. Tương tự, các từ tần suất thấp trong dữ liệu huấn luyện do xuất hiện ít nên ngữ nghĩa cũng khó được mô hình học đầy đủ.
- **Phân tách theo ký tự (Character-based)**: chia văn bản thành từng ký tự đơn lẻ. Phương pháp này có từ vựng rất nhỏ (như chữ cái tiếng Anh, chữ số và dấu câu), không có vấn đề OOV. Nhưng nhược điểm là phần lớn ký tự đơn lẻ không có ngữ nghĩa độc lập, mô hình phải tốn nhiều công sức hơn để học cách kết hợp ký tự thành từ có nghĩa, khiến hiệu quả học thấp.

Để cân bằng giữa kích thước từ vựng và khả năng biểu đạt ngữ nghĩa, các mô hình ngôn ngữ lớn hiện đại thường áp dụng thuật toán **phân tách dưới từ (Subword Tokenization)**. Tư tưởng cốt lõi là: giữ những từ phổ biến (như "agent") là token hoàn chỉnh, đồng thời chia những từ ít phổ biến (như "Tokenization") thành nhiều mảnh dưới từ có nghĩa (như "Token" và "ization"). Như vậy vừa kiểm soát được kích thước từ vựng, vừa giúp mô hình hiểu và sinh từ mới bằng cách kết hợp các mảnh dưới từ.

**3.2.2.2 Phân tích thuật toán mã hóa cặp byte**

Mã hóa cặp byte (Byte-Pair Encoding, BPE) là một trong những thuật toán phân tách dưới từ chủ lưu nhất<sup>[6]</sup>, dòng mô hình GPT đã áp dụng thuật toán này. Tư tưởng cốt lõi của nó rất gọn gàng, có thể hiểu là một quá trình hợp nhất “tham lam”:

1. **Khởi tạo**: khởi tạo từ vựng bằng tất cả ký tự cơ bản đã xuất hiện trong kho ngữ liệu.
2. **Hợp nhất lặp**: trên kho ngữ liệu, thống kê tần suất xuất hiện của tất cả cặp token liền kề, tìm cặp có tần suất cao nhất, hợp nhất chúng thành một token mới và thêm vào từ vựng.
3. **Lặp lại**: lặp bước 2 cho đến khi kích thước từ vựng đạt ngưỡng đặt trước.

**Minh họa ca ví dụ:** giả sử kho ngữ liệu mini của chúng ta là `{"hug": 1, "pug": 1, "pun": 1, "bun": 1}`, và chúng ta muốn xây dựng một từ vựng có kích thước 10. Quá trình huấn luyện BPE có thể được biểu diễn trong Bảng 3.1 dưới đây:

<div align="center">
  <p>Bảng 3.1 Ví dụ quá trình hợp nhất của thuật toán BPE</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/3-figures/1757249275674-5.png" alt="Mô tả hình ảnh" width="90%"/>
</div>

Sau khi huấn luyện xong, kích thước từ vựng đạt 10, chúng ta có quy tắc phân tách mới. Bây giờ, với một từ chưa từng thấy "bug", bộ phân tách sẽ trước tiên tìm xem "bug" có trong từ vựng không, thấy không có; sau đó tìm "bu", thấy không có; cuối cùng tìm "b" và "ug", thấy đều có, nên chia nó thành `['b', 'ug']`.

Dưới đây chúng ta dùng một đoạn mã Python đơn giản để mô phỏng quá trình trên:

```Python
import re, collections

def get_stats(vocab):
    """Thống kê tần suất cặp token"""
    pairs = collections.defaultdict(int)
    for word, freq in vocab.items():
        symbols = word.split()
        for i in range(len(symbols)-1):
            pairs[symbols[i],symbols[i+1]] += freq
    return pairs

def merge_vocab(pair, v_in):
    """Hợp nhất cặp token"""
    v_out = {}
    bigram = re.escape(' '.join(pair))
    p = re.compile(r'(?<!\S)' + bigram + r'(?!\S)')
    for word in v_in:
        w_out = p.sub(''.join(pair), word)
        v_out[w_out] = v_in[word]
    return v_out

# Chuẩn bị kho ngữ liệu, thêm </w> vào cuối mỗi từ để biểu thị kết thúc, và đã tách sẵn ký tự
vocab = {'h u g </w>': 1, 'p u g </w>': 1, 'p u n </w>': 1, 'b u n </w>': 1}
num_merges = 4 # Đặt số lần hợp nhất

for i in range(num_merges):
    pairs = get_stats(vocab)
    if not pairs:
        break
    best = max(pairs, key=pairs.get)
    vocab = merge_vocab(best, vocab)
    print(f"Hợp nhất lần {i+1}: {best} -> {''.join(best)}")
    print(f"Từ vựng mới (một phần): {list(vocab.keys())}")
    print("-" * 20)

>>>
Hợp nhất lần 1: ('u', 'g') -> ug
Từ vựng mới (một phần): ['h ug </w>', 'p ug </w>', 'p u n </w>', 'b u n </w>']
--------------------
Hợp nhất lần 2: ('ug', '</w>') -> ug</w>
Từ vựng mới (một phần): ['h ug</w>', 'p ug</w>', 'p u n </w>', 'b u n </w>']
--------------------
Hợp nhất lần 3: ('u', 'n') -> un
Từ vựng mới (một phần): ['h ug</w>', 'p ug</w>', 'p un </w>', 'b un </w>']
--------------------
Hợp nhất lần 4: ('un', '</w>') -> un</w>
Từ vựng mới (một phần): ['h ug</w>', 'p ug</w>', 'p un</w>', 'b un</w>']
--------------------
```

Đoạn mã này thể hiện rõ cách thuật toán BPE dần xây dựng và mở rộng từ vựng thông qua việc lặp hợp nhất cặp token liền kề có tần suất cao nhất.

Nhiều thuật toán sau này đều được tối ưu hóa trên cơ sở BPE. Trong đó, WordPiece và SentencePiece do Google phát triển là hai thuật toán có ảnh hưởng lớn nhất.

- **WordPiece**: thuật toán được mô hình Google BERT áp dụng<sup>[7]</sup>. Nó rất giống BPE, nhưng tiêu chí hợp nhất token không phải “tần suất cao nhất”, mà là “có thể tối đa hóa xác suất mô hình ngôn ngữ của kho ngữ liệu”. Nói đơn giản, nó sẽ ưu tiên hợp nhất những cặp token giúp “độ trôi chảy” của toàn bộ kho ngữ liệu tăng nhiều nhất.
- **SentencePiece**: một công cụ phân tách do Google mã nguồn mở<sup>[8]</sup>, dòng mô hình Llama áp dụng thuật toán này. Đặc điểm lớn nhất của nó là coi dấu cách cũng như một ký tự bình thường (thường biểu diễn bằng dấu gạch dưới `_`). Điều này khiến quá trình phân tách và giải mã hoàn toàn khả nghịch, và không phụ thuộc vào một ngôn ngữ cụ thể (ví dụ, nó không cần biết tiếng Trung không dùng dấu cách để phân tách từ).

**3.2.2.3 Ý nghĩa của bộ phân tách đối với nhà phát triển**

Hiểu chi tiết thuật toán phân tách không phải là mục đích, nhưng với vai trò nhà phát triển Agent, hiểu tác động thực tế của bộ phân tách là rất quan trọng, nó liên quan trực tiếp đến hiệu năng, chi phí và độ ổn định của Agent:

- **Giới hạn cửa sổ ngữ cảnh**: cửa sổ ngữ cảnh của mô hình (như 8K, 128K) được tính bằng **số lượng token**, chứ không phải số ký tự hay số từ. Cùng một đoạn văn, ở các ngôn ngữ khác nhau (như tiếng Trung và tiếng Anh) hoặc các bộ phân tách khác nhau, số token có thể chênh lệch rất lớn. Quản lý chính xác độ dài đầu vào, tránh vượt giới hạn ngữ cảnh là nền tảng để xây dựng Agent có bộ nhớ dài hạn.
- **Chi phí API**: phần lớn API mô hình tính phí theo số lượng token. Hiểu văn bản của bạn sẽ được phân tách như thế nào là bước then chốt để ước lượng và kiểm soát chi phí vận hành Agent.
- **Biểu hiện bất thường của mô hình**: đôi khi biểu hiện kỳ lạ của mô hình bắt nguồn từ phân tách. Ví dụ, mô hình có thể rất giỏi tính `2 + 2`, nhưng với `2+2` (không có dấu cách) lại có thể sai, vì chuỗi sau có thể bị bộ phân tách coi là một token độc lập, ít phổ biến. Tương tự, một từ do chữ cái đầu viết hoa khác nhau cũng có thể bị chia thành chuỗi token hoàn toàn khác, từ đó ảnh hưởng đến việc hiểu của mô hình. Khi thiết kế prompt và phân tích đầu ra của mô hình, việc tính đến những “cái bẫy” này giúp nâng cao độ bền vững của Agent.

### 3.2.3 Gọi mô hình ngôn ngữ lớn mã nguồn mở

Ở chương một của cuốn sách, chúng ta tương tác với mô hình ngôn ngữ lớn qua API để dẫn dắt Agent. Đây là cách nhanh chóng, tiện lợi, nhưng không phải cách duy nhất. Với nhiều kịch bản cần xử lý dữ liệu nhạy cảm, muốn chạy ngoại tuyến hoặc muốn kiểm soát chi phí tinh tế, việc triển khai mô hình ngôn ngữ lớn trực tiếp tại cục bộ trở nên rất quan trọng.

**Hugging Face Transformers** là một thư viện mã nguồn mở mạnh mẽ, cung cấp giao diện chuẩn hóa để tải và sử dụng hàng chục nghìn mô hình đã tiền huấn luyện. Chúng ta sẽ dùng nó để hoàn thành bài thực hành này.

**Cấu hình môi trường và chọn mô hình**: để phần lớn độc giả có thể chạy thuận lợi trên máy tính cá nhân, chúng tôi cố ý chọn một mô hình quy mô nhỏ nhưng mạnh mẽ: `Qwen/Qwen1.5-0.5B-Chat`. Đây là mô hình hội thoại với khoảng 500 triệu tham số do Alibaba DAMO Academy mã nguồn mở, kích thước nhỏ, hiệu năng xuất sắc, rất phù hợp cho học nhập môn và triển khai cục bộ.

Trước tiên, hãy bảo đảm bạn đã cài đặt các thư viện cần thiết:

```Plain
pip install transformers torch
```

Trong thư viện `transformers`, chúng ta thường dùng hai lớp `AutoModelForCausalLM` và `AutoTokenizer` để tự động tải trọng số và bộ phân tách khớp với mô hình. Đoạn mã dưới đây sẽ tự động tải các tệp mô hình và cấu hình bộ phân tách cần thiết từ Hugging Face Hub, việc này có thể mất một chút thời gian, tùy thuộc vào tốc độ mạng của bạn.

```Python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Chỉ định ID mô hình
model_id = "Qwen/Qwen1.5-0.5B-Chat"

# Thiết lập thiết bị, ưu tiên dùng GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Tải bộ phân tách
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Tải mô hình và chuyển nó tới thiết bị được chỉ định
model = AutoModelForCausalLM.from_pretrained(model_id).to(device)

print("Tải mô hình và bộ phân tách hoàn tất!")
```

Chúng ta hãy tạo một prompt hội thoại, mô hình Qwen1.5-Chat tuân theo một mẫu hội thoại cụ thể. Sau đó, có thể dùng `tokenizer` đã tải ở bước trước để chuyển prompt văn bản thành ID số (tức Token ID) mà mô hình hiểu được.

```Python
# Chuẩn bị đầu vào hội thoại
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Xin chào, hãy giới thiệu về bạn."}
]

# Dùng mẫu của bộ phân tách để định dạng đầu vào
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

# Mã hóa văn bản đầu vào
model_inputs = tokenizer([text], return_tensors="pt").to(device)

print("Văn bản đầu vào sau khi mã hóa:")
print(model_inputs)

>>>
{'input_ids': tensor([[151644, 8948, 198, 2610, 525, 264,  10950, 17847, 13,151645, 198, 151644, 872, 198, 108386, 37945, 100157, 107828,1773, 151645, 198, 151644, 77091, 198]], device='cuda:0'), 'attention_mask': tensor([[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]],
       device='cuda:0')}
```

Bây giờ có thể gọi phương thức `generate()` của mô hình để sinh câu trả lời. Mô hình sẽ xuất ra một chuỗi Token ID, đại diện cho câu trả lời của nó.

Cuối cùng, chúng ta cần dùng phương thức `decode()` của bộ phân tách để dịch những ID số này trở lại thành văn bản con người có thể đọc.

```Python
# Dùng mô hình để sinh câu trả lời
# max_new_tokens kiểm soát số token mới tối đa mà mô hình có thể sinh
generated_ids = model.generate(
    model_inputs.input_ids,
    max_new_tokens=512
)

# Cắt bỏ phần đầu vào khỏi Token ID đã sinh
# Như vậy chúng ta chỉ giải mã phần mô hình mới sinh
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

# Giải mã Token ID đã sinh
response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

print("\nCâu trả lời của mô hình:")
print(response)

>>>
Tôi tên là Tongyi Qianwen, một mô hình ngôn ngữ đã được tiền huấn luyện do Alibaba Cloud phát triển, có thể trả lời câu hỏi, sáng tác văn bản, bày tỏ quan điểm và viết mã. Chức năng chính của tôi là cung cấp trợ giúp trong nhiều lĩnh vực, bao gồm nhưng không giới hạn ở: hiểu ngôn ngữ, sinh văn bản, dịch máy, hệ thống hỏi đáp, v.v. Tôi có thể giúp gì cho bạn không?
```

Sau khi chạy xong tất cả mã, bạn sẽ thấy trên máy tính cục bộ phần giới thiệu về mô hình Qwen do mô hình sinh ra. Chúc mừng bạn, bạn đã triển khai và chạy thành công một mô hình ngôn ngữ lớn mã nguồn mở tại cục bộ!

### 3.2.4 Lựa chọn mô hình

Ở mục trước, chúng ta đã chạy thành công một mô hình ngôn ngữ mã nguồn mở nhỏ tại cục bộ. Điều này tự nhiên dẫn tới một câu hỏi then chốt với nhà phát triển Agent: trong bối cảnh hàng trăm mô hình đang nở rộ hiện nay, chúng ta nên chọn mô hình phù hợp nhất cho nhiệm vụ cụ thể như thế nào?

Chọn mô hình ngôn ngữ không đơn giản là theo đuổi “lớn nhất, mạnh nhất”, mà là quá trình ra quyết định cân bằng giữa hiệu năng, chi phí, tốc độ và cách triển khai. Mục này trước tiên sẽ sắp xếp vài yếu tố cân nhắc then chốt khi chọn mô hình, sau đó tổng quan các mô hình đóng và mở chủ lưu hiện nay.

Vì công nghệ mô hình ngôn ngữ lớn đang ở giai đoạn phát triển nhanh, mô hình và phiên bản mới xuất hiện liên tục, tốc độ lặp rất nhanh. Mục này khi biên soạn cố gắng cung cấp tổng quan các mô hình chủ lưu hiện nay và các cân nhắc chọn lựa, nhưng xin độc giả lưu ý phiên bản mô hình và dữ liệu hiệu năng cụ thể được nêu có thể thay đổi theo thời gian, và chỉ liệt kê một phần công trình chứ không đầy đủ. Chúng tôi tập trung hơn vào việc giới thiệu đặc điểm kỹ thuật cốt lõi, xu hướng phát triển và nguyên tắc chọn lựa tổng quát trong phát triển Agent.

**3.2.4.1 Các cân nhắc then chốt khi chọn mô hình**

Khi chọn mô hình ngôn ngữ lớn cho Agent của bạn, có thể đánh giá tổng hợp từ các chiều sau:

- **Hiệu năng và năng lực**: đây là cân nhắc cốt lõi nhất. Các mô hình khác nhau giỏi những nhiệm vụ khác nhau, có mô hình mạnh về suy luận logic và sinh mã, có mô hình lại vượt trội hơn ở sáng tác sáng tạo hoặc dịch đa ngôn ngữ. Bạn có thể tham khảo một số bảng xếp hạng benchmark công khai (như LMSys Chatbot Arena Leaderboard) để đánh giá năng lực tổng hợp của mô hình.
- **Chi phí**: với mô hình đóng, chi phí chủ yếu thể hiện ở phí gọi API, thường tính theo số lượng token. Với mô hình mã nguồn mở, chi phí thể hiện ở phần cứng (GPU, bộ nhớ) và vận hành cần cho triển khai cục bộ. Cần lựa chọn dựa trên khối lượng sử dụng dự kiến và ngân sách của ứng dụng.
- **Tốc độ (độ trễ)**: với Agent cần tương tác thời gian thực (như chăm sóc khách hàng, NPC trong game), tốc độ phản hồi của mô hình rất quan trọng. Một số mô hình nhẹ hoặc đã được tối ưu (như GPT-3.5 Turbo, Claude 3.5 Sonnet) thể hiện tốt hơn về độ trễ.
- **Cửa sổ ngữ cảnh**: giới hạn số token mô hình có thể xử lý trong một lần. Với Agent cần hiểu tài liệu dài, phân tích cơ sở mã hoặc duy trì bộ nhớ hội thoại dài hạn, việc chọn mô hình có cửa sổ ngữ cảnh lớn (như 128K token hoặc cao hơn) là cần thiết.
- **Cách triển khai**: dùng API là cách đơn giản, tiện lợi nhất, nhưng dữ liệu cần gửi cho bên thứ ba, và bị ràng buộc bởi điều khoản của nhà cung cấp. Triển khai cục bộ bảo đảm quyền riêng tư dữ liệu và mức tự chủ kiểm soát cao nhất, nhưng yêu cầu kỹ thuật và phần cứng cao hơn.
- **Hệ sinh thái và chuỗi công cụ**: mức độ phổ biến của một mô hình cũng quyết định độ trưởng thành của hệ sinh thái xung quanh. Mô hình chủ lưu thường có hỗ trợ cộng đồng, hướng dẫn, mô hình tiền huấn luyện, công cụ tinh chỉnh và framework phát triển tương thích (như LangChain, LlamaIndex, Hugging Face Transformers) phong phú hơn, điều này có thể tăng tốc đáng kể quá trình phát triển và giảm độ khó. Chọn một mô hình có cộng đồng năng động và chuỗi công cụ hoàn thiện giúp dễ tìm được giải pháp và tài nguyên khi gặp vấn đề.
- **Khả năng tinh chỉnh và tùy biến**: với Agent cần xử lý dữ liệu lĩnh vực cụ thể hoặc thực thi nhiệm vụ cụ thể, năng lực tinh chỉnh mô hình rất quan trọng. Một số mô hình cung cấp giao diện và công cụ tinh chỉnh tiện lợi, cho phép nhà phát triển dùng tập dữ liệu của mình để huấn luyện tùy biến mô hình, từ đó nâng cao rõ rệt hiệu năng và độ chính xác của mô hình trong kịch bản cụ thể. Mô hình mã nguồn mở thường mang lại sự linh hoạt lớn hơn ở phương diện này.
- **An toàn và đạo đức**: cùng với việc mô hình ngôn ngữ lớn được ứng dụng rộng rãi, rủi ro an toàn và vấn đề đạo đức tiềm ẩn của nó cũng ngày càng rõ. Khi chọn mô hình, cần xét biểu hiện của nó về thiên lệch, độc hại, ảo giác, cũng như mức đầu tư của nhà cung cấp hoặc cộng đồng mã nguồn mở vào an toàn mô hình và AI có trách nhiệm. Với ứng dụng hướng tới công chúng hoặc liên quan thông tin nhạy cảm, tính an toàn và tuân thủ đạo đức của mô hình là cân nhắc không thể bỏ qua.

**3.2.4.2 Tổng quan mô hình đóng**

Mô hình đóng thường đại diện cho biên giới tiên tiến nhất của công nghệ AI hiện nay, và cung cấp dịch vụ API ổn định, dễ dùng, là lựa chọn hàng đầu để xây dựng Agent hiệu năng cao.

1. **Dòng OpenAI GPT**: từ GPT-3 mở ra thời đại mô hình lớn, đến ChatGPT đưa vào RLHF (học tăng cường từ phản hồi con người), hiện thực căn chỉnh với ý định con người, rồi đến GPT-4 mở ra thời đại đa phương thức, OpenAI liên tục dẫn dắt ngành. GPT-5 mới nhất còn nâng năng lực đa phương thức và mức trí tuệ tổng quát lên tầm cao mới, có thể xử lý liền mạch đầu vào văn bản, âm thanh và hình ảnh, đồng thời sinh đầu ra tương ứng, tốc độ phản hồi và độ tự nhiên cũng được nâng cao đáng kể, đặc biệt xuất sắc trong hội thoại giọng nói thời gian thực.
2. **Dòng Google Gemini**: dòng mô hình Gemini do Google DeepMind ra mắt là đại diện của đa phương thức nguyên bản, đặc điểm cốt lõi là có thể xử lý thống nhất dữ liệu nhiều phương thức như văn bản, mã, âm thanh - video và hình ảnh, và có ưu thế trong xử lý khối thông tin khổng lồ nhờ cửa sổ ngữ cảnh siêu dài. Gemini Ultra là mô hình mạnh nhất của dòng này, phù hợp cho nhiệm vụ phức tạp cao độ; Gemini Pro phù hợp cho nhiều nhiệm vụ, mang lại hiệu năng và hiệu quả cao; Gemini Nano được tối ưu cho triển khai trên thiết bị. Dòng Gemini 2.5 mới nhất, như Gemini 2.5 Pro và Gemini 2.5 Flash, tiếp tục nâng cao năng lực suy luận và cửa sổ ngữ cảnh, đặc biệt Gemini 2.5 Flash với tốc độ suy luận nhanh hơn và hiệu quả chi phí, phù hợp cho kịch bản cần phản hồi nhanh.
3. **Dòng Anthropic Claude**: Anthropic là công ty tập trung vào an toàn AI và AI có trách nhiệm, dòng mô hình Claude của họ ngay từ thiết kế đã đặt an toàn AI lên hàng đầu, nổi tiếng về độ tin cậy trong xử lý tài liệu dài, giảm đầu ra độc hại và tuân theo chỉ thị, được các ứng dụng cấp doanh nghiệp ưa chuộng. Dòng Claude 3 gồm Claude 3 Opus (thông minh nhất, hiệu năng mạnh nhất), Claude 3 Sonnet (lựa chọn cân bằng giữa hiệu năng và tốc độ) và Claude 3 Haiku (mô hình nhanh nhất, gọn nhất, phù hợp tương tác gần như thời gian thực). Dòng Claude 4 mới nhất, như Claude 4 Opus, đạt tiến bộ đáng kể về trí tuệ tổng quát, suy luận phức tạp và sinh mã, nâng cao hơn nữa năng lực xử lý ngữ cảnh dài và nhiệm vụ đa phương thức.
4. **Các mô hình chủ lưu trong nước**: Trung Quốc đã xuất hiện nhiều mô hình đóng có sức cạnh tranh trong lĩnh vực mô hình ngôn ngữ lớn, với các đại diện như ERNIE Bot (Văn Tâm Nhất Ngôn) của Baidu, Hunyuan (Hỗn Nguyên) của Tencent, Pangu-α (Bàn Cổ) của Huawei, SparkDesk (Tinh Hỏa) của iFlytek và Moonshot AI, các mô hình nội địa này có ưu thế tự nhiên trong xử lý tiếng Trung và hỗ trợ sâu cho ngành công nghiệp bản địa.

**3.2.4.3 Tổng quan mô hình mã nguồn mở**

Mô hình mã nguồn mở mang lại cho nhà phát triển mức linh hoạt, minh bạch và tự chủ cao nhất, thúc đẩy một hệ sinh thái cộng đồng phồn thịnh. Chúng cho phép nhà phát triển triển khai cục bộ, tinh chỉnh tùy biến và có toàn quyền kiểm soát mô hình.

- **Dòng Meta Llama**: dòng Llama do Meta ra mắt là cột mốc quan trọng của mô hình ngôn ngữ lớn mã nguồn mở. Nhờ hiệu năng tổng hợp xuất sắc, giấy phép mở và hỗ trợ cộng đồng mạnh mẽ, dòng này trở thành nền tảng cho nhiều dự án phái sinh và nghiên cứu. Dòng Llama 4 ra mắt tháng 4 năm 2025, là những mô hình đầu tiên của Meta áp dụng kiến trúc hỗn hợp chuyên gia (MoE), kiến trúc này nâng cao đáng kể hiệu quả tính toán bằng cách chỉ kích hoạt phần mô hình cần thiết để xử lý nhiệm vụ cụ thể. Dòng này gồm ba mô hình có định vị rõ ràng: LLama 4 Scout hỗ trợ cửa sổ ngữ cảnh 10 triệu token, được thiết kế cho phân tích tài liệu dài và triển khai trên thiết bị di động. Llama 4 Maverick tập trung vào năng lực đa phương thức, xuất sắc trong viết mã, suy luận phức tạp và hỗ trợ đa ngôn ngữ. Llama 4 Behemoth thể hiện vượt trội so với đối thủ trong nhiều benchmark STEM. Đây là mô hình mạnh nhất hiện nay của Meta
- **Dòng Mistral AI**: Mistral AI đến từ Pháp nổi tiếng với thiết kế mô hình “kích thước nhỏ, hiệu năng cao”. Mô hình mới nhất của họ Mistral Medium 3.1 ra mắt tháng 8 năm 2025, độ chính xác và tốc độ phản hồi đều được nâng cao đáng kể trên các nhiệm vụ như sinh mã, suy luận STEM và hỏi đáp liên lĩnh vực, biểu hiện benchmark vượt trội so với các mô hình cùng cấp như Claude Sonnet 3.7 và Llama 4 Maverick. Nó có năng lực đa phương thức nguyên bản, có thể xử lý đồng thời đầu vào hỗn hợp hình ảnh và văn bản, và tích hợp sẵn “lớp thích ứng giọng điệu”, giúp doanh nghiệp dễ dàng hơn trong việc tạo đầu ra phù hợp với bản sắc thương hiệu.
- **Lực lượng mã nguồn mở trong nước**: các nhà sản xuất và cơ sở nghiên cứu trong nước cũng tích cực đón nhận mã nguồn mở, ví dụ dòng **Qwen (Tongyi Qianwen)** của Alibaba và dòng **ChatGLM** do Đại học Thanh Hoa hợp tác với Zhipu AI, chúng cung cấp năng lực tiếng Trung mạnh mẽ và xây dựng cộng đồng năng động xung quanh mình.

Với nhà phát triển Agent, mô hình đóng mang lại sự tiện lợi “dùng ngay”, còn mô hình mã nguồn mở trao cho chúng ta tự do tùy biến “theo ý muốn”. Hiểu đặc điểm và mô hình đại diện của hai phe này là bước đầu tiên để đưa ra lựa chọn công nghệ sáng suốt cho dự án Agent của chúng ta.

## 3.3 Quy luật tỉ lệ và hạn chế của mô hình ngôn ngữ lớn

Mô hình ngôn ngữ lớn (LLM) đã đạt tiến bộ đáng chú ý trong những năm gần đây, biên giới năng lực không ngừng mở rộng, kịch bản ứng dụng ngày càng phong phú. Tuy nhiên, đằng sau những thành tựu này là sự hiểu biết sâu sắc về quan hệ giữa quy mô mô hình, lượng dữ liệu và tài nguyên tính toán, tức **quy luật tỉ lệ (Scaling Laws)**. Đồng thời, là công nghệ mới nổi, LLM cũng đối mặt với nhiều thách thức và hạn chế. Mục này sẽ đi sâu vào những khái niệm cốt lõi này, nhằm giúp độc giả hiểu toàn diện biên giới năng lực của LLM, từ đó phát huy ưu điểm và tránh nhược điểm khi xây dựng Agent.

### 3.3.1 Quy luật tỉ lệ

**Quy luật tỉ lệ (Scaling Laws)** là một trong những phát hiện quan trọng nhất của lĩnh vực mô hình ngôn ngữ lớn trong những năm gần đây. Nó cho thấy hiệu năng mô hình có quan hệ lũy thừa có thể dự đoán được với số tham số mô hình, lượng dữ liệu huấn luyện và tài nguyên tính toán. Phát hiện này cung cấp định hướng lý thuyết cho sự phát triển liên tục của mô hình ngôn ngữ lớn, làm rõ logic nền tảng rằng tăng đầu tư tài nguyên có thể nâng cao hiệu năng mô hình một cách hệ thống.

Nghiên cứu phát hiện, trong hệ tọa độ log-log, hiệu năng mô hình (thường đo bằng Loss) có quan hệ lũy thừa trơn với cả ba yếu tố số tham số, lượng dữ liệu và lượng tính toán<sup>[9]</sup>. Nói đơn giản, chỉ cần chúng ta liên tục tăng ba yếu tố này theo tỷ lệ, hiệu năng mô hình sẽ được nâng cao một cách có thể dự đoán, trơn tru, mà không xuất hiện nút cổ chai rõ rệt. Phát hiện này cung cấp hướng dẫn rõ ràng cho thiết kế và huấn luyện mô hình lớn: trong phạm vi tài nguyên cho phép, mở rộng quy mô mô hình và lượng dữ liệu huấn luyện càng nhiều càng tốt.

Nghiên cứu thời kỳ đầu thiên về tăng số tham số mô hình, nhưng “định luật Chinchilla” do DeepMind đề xuất năm 2022 đã sửa đổi quan trọng điều này<sup>[10]</sup>. Định luật chỉ ra rằng, với ngân sách tính toán cho trước, để đạt hiệu năng tối ưu, **giữa số tham số mô hình và lượng dữ liệu huấn luyện tồn tại một tỷ lệ tối ưu**. Cụ thể, mô hình tối ưu nên nhỏ hơn so với nhận định phổ biến trước đó, nhưng cần được huấn luyện với nhiều dữ liệu hơn hẳn. Ví dụ, một mô hình Chinchilla 70 tỷ tham số, nhờ dùng lượng dữ liệu gấp 4 lần GPT-3 (175 tỷ tham số) để huấn luyện, lại vượt trội về hiệu năng so với mô hình sau. Phát hiện này đã chỉnh lại nhận thức phiến diện “càng lớn càng tốt”, nhấn mạnh tầm quan trọng của hiệu quả dữ liệu, và định hướng thiết kế của nhiều mô hình lớn hiệu quả sau này (như dòng Llama).

Sản phẩm đáng ngạc nhiên nhất của quy luật tỉ lệ là “năng lực nổi sinh”. Năng lực nổi sinh nghĩa là khi quy mô mô hình đạt một ngưỡng nhất định, nó đột nhiên thể hiện những năng lực hoàn toàn mới mà mô hình quy mô nhỏ không có hoặc thể hiện kém. Ví dụ, các năng lực như **chuỗi suy nghĩ (Chain-of-Thought)**, **tuân theo chỉ thị (Instruction Following)**, suy luận nhiều bước, sinh mã, đều chỉ xuất hiện rõ rệt sau khi số tham số mô hình đạt hàng chục tỷ thậm chí hàng trăm tỷ. Hiện tượng này cho thấy mô hình ngôn ngữ lớn không chỉ đơn thuần ghi nhớ và kể lại, mà trong quá trình học có thể đã hình thành một năng lực trừu tượng và suy luận ở tầng sâu hơn. Với nhà phát triển Agent, năng lực nổi sinh có nghĩa việc chọn một mô hình đủ quy mô lớn là tiền đề để hiện thực năng lực tự chủ ra quyết định và lập kế hoạch phức tạp.

### 3.3.2 Ảo giác của mô hình

**Ảo giác của mô hình (Hallucination)** thường chỉ việc nội dung do mô hình ngôn ngữ lớn sinh ra mâu thuẫn với sự thật khách quan, đầu vào của người dùng hoặc thông tin ngữ cảnh, hoặc sinh ra những sự thật, thực thể hay sự kiện không tồn tại. Bản chất của ảo giác là trong quá trình sinh, mô hình đã quá tự tin “bịa” ra thông tin, thay vì truy xuất hoặc suy luận chính xác. Theo biểu hiện, ảo giác có thể chia thành nhiều loại<sup>[11]</sup>, ví dụ:

- **Ảo giác sự thật (Factual Hallucinations)**: mô hình sinh ra thông tin không khớp với sự thật của thế giới thực.
- **Ảo giác trung thành (Faithfulness Hallucinations)**: trong các nhiệm vụ như tóm tắt văn bản, dịch, nội dung sinh ra không phản ánh trung thành ý nghĩa của văn bản nguồn.
- **Ảo giác nội tại (Intrinsic Hallucinations)**: nội dung mô hình sinh ra mâu thuẫn trực tiếp với thông tin đầu vào.

Ảo giác là kết quả tác động tổng hợp của nhiều yếu tố. Thứ nhất, dữ liệu huấn luyện có thể chứa thông tin sai hoặc mâu thuẫn. Thứ hai, cơ chế sinh tự hồi quy của mô hình quyết định nó chỉ đang dự đoán token có khả năng xuất hiện cao nhất tiếp theo, mà không có mô-đun kiểm chứng sự thật tích hợp sẵn. Cuối cùng, khi đối mặt với nhiệm vụ cần suy luận phức tạp, mô hình có thể sai trong chuỗi logic, từ đó “bịa” ra kết luận sai. Ví dụ: một Agent lập kế hoạch du lịch có thể gợi ý cho bạn một điểm du lịch không tồn tại trong thực tế, hoặc đặt một vé máy bay với số hiệu chuyến sai.

Ngoài ra, mô hình ngôn ngữ lớn còn đối mặt với thách thức về tính thời sự của tri thức không đủ và thiên lệch tồn tại trong dữ liệu huấn luyện. Năng lực của mô hình ngôn ngữ lớn bắt nguồn từ dữ liệu huấn luyện của nó. Điều này có nghĩa tri thức mà mô hình nắm được là tư liệu mới nhất tại thời điểm thu thập dữ liệu huấn luyện. Với những sự kiện xảy ra sau ngày đó, khái niệm mới xuất hiện hoặc sự thật mới nhất, mô hình sẽ không thể cảm nhận hoặc trả lời đúng. Đồng thời, dữ liệu huấn luyện thường chứa các thiên lệch và định kiến khác nhau của xã hội loài người. Khi mô hình học trên những dữ liệu này, nó không tránh khỏi việc hấp thụ và phản ánh những thiên lệch đó<sup>[12]</sup>.

Để nâng cao độ tin cậy của mô hình ngôn ngữ lớn, các nhà nghiên cứu và nhà phát triển đang tích cực khám phá nhiều phương pháp phát hiện và giảm thiểu ảo giác:

1. **Ở tầng dữ liệu**: thông qua làm sạch dữ liệu chất lượng cao, đưa vào tri thức sự thật và học tăng cường từ phản hồi con người (RLHF)<sup>[13]</sup>, giảm ảo giác từ nguồn.
2. **Ở tầng mô hình**: khám phá kiến trúc mô hình mới, hoặc để mô hình có thể bày tỏ mức không chắc chắn về nội dung sinh ra.
3. **Ở tầng suy luận và sinh**:
   1. **Sinh tăng cường truy xuất (Retrieval-Augmented Generation, RAG)**<sup>[14]</sup>: đây là một trong những phương pháp hiệu quả hiện nay để giảm thiểu ảo giác. Hệ thống RAG truy xuất thông tin liên quan từ cơ sở tri thức bên ngoài (như cơ sở dữ liệu tài liệu, trang web) trước khi sinh, sau đó dùng thông tin truy xuất được làm ngữ cảnh, dẫn dắt mô hình sinh câu trả lời dựa trên sự thật.
   2. **Suy luận nhiều bước và kiểm chứng**: dẫn dắt mô hình suy luận nhiều bước, và tự kiểm tra hoặc kiểm chứng bên ngoài ở mỗi bước.
   3. **Đưa vào công cụ bên ngoài**: cho phép mô hình gọi công cụ bên ngoài (như công cụ tìm kiếm, máy tính, trình thông dịch mã) để lấy thông tin thời gian thực hoặc thực hiện tính toán chính xác.

Dù vấn đề ảo giác khó có thể loại trừ hoàn toàn trong ngắn hạn, thông qua các chiến lược trên, có thể giảm đáng kể tần suất và tác động của nó, nâng cao độ tin cậy và tính hữu dụng của mô hình ngôn ngữ lớn trong ứng dụng thực tế.

## 3.4 Tóm tắt chương

Chương này giới thiệu kiến thức nền tảng cần thiết để xây dựng Agent, tập trung vào mô hình ngôn ngữ lớn (LLM) với vai trò thành phần cốt lõi của nó. Nội dung bắt đầu từ sự phát triển sớm của mô hình ngôn ngữ, trình bày chi tiết kiến trúc Transformer, và giới thiệu các phương pháp tương tác với LLM. Cuối cùng, chương này tổng quan hệ sinh thái mô hình chủ lưu hiện nay, quy luật phát triển và những hạn chế cố hữu của nó.

**Ôn tập các điểm kiến thức cốt lõi:**

- **Tiến hóa mô hình và kiến trúc cốt lõi**: chương này truy nguyên từ mô hình ngôn ngữ thống kê (N-gram) đến mô hình mạng nơ-ron (RNN, LSTM), rồi đến kiến trúc Transformer đặt nền tảng cho LLM hiện đại. Thông qua hiện thực mã “từ trên xuống”, chương này phân tích các thành phần cốt lõi của Transformer, và trình bày vai trò then chốt của cơ chế tự chú ý trong tính toán song song và nắm bắt phụ thuộc khoảng cách xa.
- **Cách tương tác với mô hình**: chương này giới thiệu hai khâu cốt lõi khi tương tác với LLM: kỹ thuật prompt (Prompt Engineering) và phân tách văn bản (Tokenization). Khâu trước dùng để dẫn dắt hành vi của mô hình, khâu sau là nền tảng để hiểu cách mô hình xử lý đầu vào. Thông qua thực hành triển khai và chạy mô hình mã nguồn mở tại cục bộ, kiến thức lý thuyết được áp dụng vào thao tác thực tế.
- **Hệ sinh thái mô hình và chọn lựa**: chương này sắp xếp một cách hệ thống các yếu tố then chốt cần cân bằng khi chọn mô hình cho Agent, và tổng quan đặc điểm, định vị của các mô hình đóng đại diện bởi OpenAI GPT, Google Gemini và các mô hình mã nguồn mở đại diện bởi Llama, Mistral.
- **Quy luật và hạn chế**: chương này thảo luận quy luật tỉ lệ thúc đẩy nâng cao năng lực LLM, trình bày nguyên lý cơ bản đằng sau nó. Đồng thời, chương này cũng phân tích những hạn chế cố hữu của mô hình như ảo giác sự thật, tri thức lỗi thời, điều này rất quan trọng để xây dựng Agent đáng tin cậy, bền vững.

**Từ nền tảng LLM đến xây dựng Agent:**

Phần nền tảng LLM của chương này chủ yếu giúp mọi người hiểu rõ hơn sự ra đời và quá trình phát triển của mô hình lớn, trong đó cũng chứa đựng một phần tư duy về thiết kế Agent. Ví dụ, làm thế nào thiết kế prompt hiệu quả để dẫn dắt lập kế hoạch và ra quyết định của Agent, làm thế nào chọn mô hình phù hợp theo nhu cầu nhiệm vụ, và làm thế nào thêm cơ chế kiểm chứng vào quy trình làm việc của Agent để tránh ảo giác của mô hình, v.v., lời giải của những vấn đề này đều được xây dựng trên nền tảng của chương này. Hiện chúng ta đã sẵn sàng chuyển từ lý thuyết sang thực hành. Ở chương tiếp theo, chúng ta sẽ bắt đầu khám phá việc xây dựng các mô hình Agent kinh điển, áp dụng kiến thức học được ở chương này vào thiết kế Agent thực tế.



## Bài tập

1. Trong xử lý ngôn ngữ tự nhiên, mô hình ngôn ngữ đã trải qua quá trình tiến hóa từ thống kê đến mạng nơ-ron.

   - Hãy dùng kho ngữ liệu mini được cung cấp trong chương này (`datawhale agent learns`, `datawhale agent works`), tính xác suất của câu `agent works` dưới mô hình Bigram
   - Giả thuyết cốt lõi của mô hình N-gram là giả thuyết Markov. Hãy giải thích ý nghĩa của giả thuyết này, và mô hình N-gram có những hạn chế căn bản nào?
   - Mô hình ngôn ngữ mạng nơ-ron (RNN/LSTM) và Transformer lần lượt khắc phục hạn chế của mô hình N-gram như thế nào? Ưu thế của mỗi loại là gì?

2. Kiến trúc Transformer<sup>[4]</sup> là nền tảng của mô hình ngôn ngữ lớn hiện đại. Trong đó:

   > **Gợi ý**: có thể kết hợp hiện thực mã ở mục 3.1.2 của chương này để hỗ trợ hiểu

   - Tư tưởng cốt lõi của cơ chế tự chú ý (Self-Attention) là gì?
   - Vì sao Transformer có thể xử lý chuỗi song song, còn RNN phải xử lý tuần tự? Mã hóa vị trí (Positional Encoding) đóng vai trò gì trong đó?
   - Kiến trúc Decoder-Only khác gì so với kiến trúc Encoder-Decoder đầy đủ? Vì sao các mô hình ngôn ngữ lớn chủ lưu hiện nay đều dùng kiến trúc Decoder-Only?

3. Thuật toán phân tách dưới từ của văn bản là một công nghệ then chốt của mô hình ngôn ngữ lớn, chịu trách nhiệm chuyển văn bản thành chuỗi token mà mô hình có thể xử lý. Vậy vì sao không thể trực tiếp lấy “ký tự” hoặc “từ” làm đơn vị đầu vào của mô hình? Thuật toán BPE (Byte Pair Encoding) đã giải quyết vấn đề gì?

4. Mục 3.2.3 của chương này giới thiệu cách triển khai mô hình ngôn ngữ lớn mã nguồn mở tại cục bộ. Hãy hoàn thành thực hành và phân tích sau:

   > **Gợi ý**: đây là bài thực hành, nên thao tác thực tế

   - Theo hướng dẫn của chương này, triển khai một mô hình mã nguồn mở nhẹ tại cục bộ (khuyến nghị [Qwen3-0.6B](https://modelscope.cn/models/Qwen/Qwen3-0.6B)), và thử điều chỉnh tham số lấy mẫu, quan sát tác động của chúng lên đầu ra
   - Chọn một nhiệm vụ cụ thể (như phân loại văn bản, trích xuất thông tin, sinh mã, v.v.), thiết kế và so sánh hiệu quả của các chiến lược prompt khác nhau (như Zero-shot, Few-shot, Chain-of-Thought) lên kết quả đầu ra
   - So sánh mô hình đóng và mô hình mã nguồn mở trên các chiều hiệu năng, chi phí, khả năng kiểm soát, quyền riêng tư
   - Nếu bạn xây dựng một Agent chăm sóc khách hàng cấp doanh nghiệp, bạn sẽ chọn loại mô hình nào? Cần xét những yếu tố nào?

5. Ảo giác của mô hình (Hallucination)<sup>[11]</sup> là một trong những hạn chế then chốt hiện nay của mô hình ngôn ngữ lớn. Chương này giới thiệu các phương pháp giảm thiểu ảo giác (như sinh tăng cường truy xuất, suy luận nhiều bước, gọi công cụ bên ngoài)

   - Hãy chọn một trong số đó, giải thích nguyên lý làm việc và kịch bản áp dụng
   - Tìm hiểu các nghiên cứu và bài báo tiên tiến, liệu còn phương pháp nào khác giảm thiểu ảo giác của mô hình, chúng có cải tiến và ưu thế gì?

6. Giả sử bạn cần thiết kế một Agent hỗ trợ đọc bài báo, có thể giúp nhà nghiên cứu nhanh chóng đọc và hiểu bài báo học thuật, bao gồm: tóm tắt nội dung cốt lõi của nghiên cứu, trả lời câu hỏi về bài báo, trích xuất thông tin then chốt, so sánh quan điểm của nhiều bài báo khác nhau, v.v. Hãy trả lời:

   - Bạn sẽ chọn mô hình nào làm mô hình nền khi thiết kế Agent? Khi chọn cần xét những yếu tố nào?
   - Làm thế nào thiết kế prompt để dẫn dắt mô hình hiểu bài báo học thuật tốt hơn? Bài báo học thuật thường rất dài, có thể vượt giới hạn cửa sổ ngữ cảnh của mô hình, bạn sẽ giải quyết vấn đề này như thế nào?
   - Nghiên cứu học thuật đòi hỏi sự nghiêm ngặt, nghĩa là chúng ta cần bảo đảm thông tin do Agent sinh ra là chính xác, khách quan, trung thành với văn bản gốc. Bạn nghĩ nên thêm những thiết kế nào vào hệ thống để hiện thực tốt hơn nhu cầu này?



## Tài liệu tham khảo

[1] Bengio, Y., Ducharme, R., Vincent, P., & Jauvin, C. (2003). A neural probabilistic language model. *Journal of Machine Learning Research*, 3, 1137-1155.

[2] Elman, J. L. (1990). Finding structure in time. *Cognitive Science*, 14(2), 179-211.

[3] Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*, 9(8), 1735-1780.

[4] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017). Attention is all you need. In *Advances in neural information processing systems* (pp. 5998-6008).

[5] Radford, A., Narasimhan, K., Salimans, T., & Sutskever, I. (2018). Improving language understanding by generative pre-training. OpenAI.

[6] Gage, P. (1994). A new algorithm for data compression. *C Users Journal*, *12*(2), 23-38.

[7] Schuster, M., & Nakajima, K. (2012, March). Japanese and korean voice search. In *2012 IEEE international conference on acoustics, speech and signal processing (ICASSP)* (pp. 5149-5152). IEEE.

[8] Kudo, T., & Richardson, J. (2018). SentencePiece: A simple and language independent subword tokenizer and detokenizer for neural text processing. *arXiv preprint arXiv:1808.06226*.

[9] Kaplan, J., McCandlish, S., Henighan, T., Brown, T. B., Chess, B., Child, R., ... & Amodei, D. (2020). Scaling Laws for Neural Language Models. arXiv preprint arXiv:2001.08361.

[10] Hoffmann, J., Borgeaud, E., Mensch, A., Buchatskaya, E., Cai, T., Rutherford, R., ... & Sifre, L. (2022). Training Compute-Optimal Large Language Models. arXiv preprint arXiv:2203.07678.

[11] Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., ... & Liu, T. (2023). A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions. *arXiv preprint arXiv:2311.05232*.

[12] Bender, E. M., Gebru, T., McMillan-Major, A., & Mitchell, M. (2021). On the Dangers of Stochastic Parrots: Can Language Models Be Too Big? .

[13] Christiano, P., Leike, J., Brown, T. B., Martic, M., Legg, S., & Amodei, D. (2017). Deep reinforcement learning from human preferences. *arXiv preprint arXiv:1706.03741*.

[14] Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goswami, N., ... & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances in neural information processing systems* (pp. 9459-9474).

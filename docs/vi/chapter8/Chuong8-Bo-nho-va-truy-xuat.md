# Chương 8: Bộ nhớ và truy xuất

Ở các chương trước, chúng ta đã xây dựng kiến trúc nền tảng của framework HelloAgents, hiện thực nhiều mẫu hình Agent khác nhau và hệ thống công cụ. Tuy nhiên, framework của chúng ta vẫn còn thiếu một năng lực then chốt: <strong>bộ nhớ</strong>. Nếu Agent không thể ghi nhớ nội dung các tương tác trước đó, cũng không thể học từ kinh nghiệm lịch sử, thì trong các cuộc hội thoại liên tục hoặc nhiệm vụ phức tạp, hiệu năng của nó sẽ bị hạn chế rất lớn.

Chương này sẽ dựa trên nền framework đã xây dựng ở chương 7, bổ sung cho HelloAgents hai năng lực cốt lõi: <strong>hệ thống bộ nhớ (Memory System)</strong> và <strong>sinh tăng cường truy xuất (Retrieval-Augmented Generation, RAG)</strong>. Chúng ta sẽ áp dụng cách tiếp cận "mở rộng framework + phổ biến kiến thức", trong quá trình xây dựng đồng thời hiểu sâu cơ sở lý thuyết của Memory và RAG, cuối cùng hiện thực một hệ thống Agent có năng lực ghi nhớ và truy xuất tri thức hoàn chỉnh.


## 8.1 Từ khoa học nhận thức đến bộ nhớ của Agent

### 8.1.1 Gợi mở từ hệ thống bộ nhớ của con người

Trước khi xây dựng hệ thống bộ nhớ cho Agent, chúng ta hãy bắt đầu từ góc nhìn khoa học nhận thức để hiểu con người xử lý và lưu trữ thông tin như thế nào. Bộ nhớ của con người là một hệ thống nhận thức nhiều tầng, không chỉ lưu trữ thông tin mà còn có thể phân loại và sắp xếp thông tin theo mức độ quan trọng, thời gian và ngữ cảnh. Tâm lý học nhận thức cung cấp cho chúng ta một khung lý thuyết kinh điển để hiểu cấu trúc và quá trình của bộ nhớ<sup>[1]</sup>, như minh họa trong Hình 8.1.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-1.png" alt="Sơ đồ cấu trúc hệ thống bộ nhớ của con người" width="85%"/>
  <p>Hình 8.1 Cấu trúc phân tầng của hệ thống bộ nhớ con người</p>
</div>

Theo các nghiên cứu trong tâm lý học nhận thức, bộ nhớ của con người có thể được chia thành các tầng sau:

1. <strong>Bộ nhớ cảm giác (Sensory Memory)</strong>: thời gian tồn tại cực ngắn (0.5-3 giây), dung lượng khổng lồ, chịu trách nhiệm lưu giữ tạm thời mọi thông tin mà các giác quan tiếp nhận
2. <strong>Bộ nhớ làm việc (Working Memory)</strong>: thời gian tồn tại ngắn (15-30 giây), dung lượng hạn chế (7±2 mục), chịu trách nhiệm xử lý thông tin của nhiệm vụ hiện tại
3. <strong>Bộ nhớ dài hạn (Long-term Memory)</strong>: thời gian tồn tại dài (có thể đến trọn đời), dung lượng gần như vô hạn, được chia tiếp thành:
   - <strong>Bộ nhớ thủ tục</strong>: kỹ năng và thói quen (ví dụ: đi xe đạp)
   - <strong>Bộ nhớ khai báo</strong>: tri thức có thể diễn đạt bằng ngôn ngữ, lại được chia thành:
     - <strong>Bộ nhớ ngữ nghĩa</strong>: tri thức chung và khái niệm (ví dụ: "Paris là thủ đô của Pháp")
     - <strong>Bộ nhớ tình huống</strong>: trải nghiệm cá nhân và sự kiện (ví dụ: "nội dung cuộc họp hôm qua")

### 8.1.2 Vì sao Agent cần bộ nhớ và RAG

Học hỏi từ thiết kế hệ thống bộ nhớ của con người, chúng ta có thể hiểu vì sao Agent cũng cần năng lực ghi nhớ tương tự. Một đặc trưng quan trọng của trí tuệ con người là có thể ghi nhớ những trải nghiệm đã qua, học hỏi từ đó và áp dụng những kinh nghiệm này vào tình huống mới. Tương tự, một Agent thực sự thông minh cũng cần có năng lực ghi nhớ. Với Agent dựa trên LLM, thường tồn tại hai hạn chế căn bản: <strong>sự quên lãng trạng thái hội thoại</strong> và <strong>hạn chế của tri thức tích hợp sẵn</strong>.

(1) Hạn chế thứ nhất: quên hội thoại do không lưu trạng thái

Các mô hình ngôn ngữ lớn hiện nay tuy mạnh mẽ, nhưng về thiết kế là <strong>không lưu trạng thái (stateless)</strong>. Điều này có nghĩa mỗi yêu cầu của người dùng (hoặc mỗi lần gọi API) là một phép tính độc lập, không liên quan đến lần trước. Bản thân mô hình không tự động "ghi nhớ" nội dung của cuộc hội thoại trước đó. Điều này mang lại một số vấn đề:

1. <strong>Mất ngữ cảnh</strong>: trong hội thoại dài, thông tin quan trọng ở giai đoạn đầu có thể bị mất do giới hạn của cửa sổ ngữ cảnh
2. <strong>Thiếu cá nhân hóa</strong>: Agent không thể ghi nhớ sở thích, thói quen hoặc nhu cầu cụ thể của người dùng
3. <strong>Năng lực học bị hạn chế</strong>: không thể học hỏi, cải thiện từ những kinh nghiệm thành công hay thất bại trong quá khứ
4. <strong>Vấn đề nhất quán</strong>: trong hội thoại nhiều lượt có thể xuất hiện những câu trả lời mâu thuẫn trước sau

Hãy cùng hiểu vấn đề này qua một ví dụ cụ thể:

```python
# Cách dùng Agent ở chương 7
from hello_agents import SimpleAgent, HelloAgentsLLM

agent = SimpleAgent(name="Trợ lý học tập", llm=HelloAgentsLLM())

# Lượt hội thoại thứ nhất
response1 = agent.run("Tôi tên là Trương Tam, đang học Python, hiện đã nắm được cú pháp cơ bản")
print(response1)  # "Rất tốt! Cú pháp cơ bản của Python là nền tảng quan trọng của lập trình..."

# Lượt hội thoại thứ hai (phiên mới, ví dụ sau khi khởi động lại chương trình và tạo lại Agent)
agent = SimpleAgent(name="Trợ lý học tập", llm=HelloAgentsLLM())
response2 = agent.run("Bạn còn nhớ tiến độ học của tôi không?")
print(response2)  # "Xin lỗi, tôi không biết tiến độ học của bạn..."
```

Cần lưu ý rằng `SimpleAgent` ở chương 7 sẽ lưu tạm cuộc hội thoại hiện tại trong `_history` của cùng một thực thể, nên các hội thoại liên tục trong cùng một tiến trình, cùng một thực thể có thể mang theo ngữ cảnh gần nhất. Nhưng lịch sử này chỉ là danh sách tin nhắn tạm thời, không được lưu trữ bền vững qua các phiên, cũng không thể truy xuất dài hạn, quên đi và tích hợp.

Để giải quyết vấn đề này, framework của chúng ta cần đưa vào hệ thống bộ nhớ.

(2) Hạn chế thứ hai: giới hạn của tri thức tích hợp trong mô hình

Ngoài việc quên lịch sử hội thoại, một hạn chế cốt lõi khác của LLM nằm ở chỗ tri thức của nó là <strong>tĩnh và hữu hạn</strong>. Những tri thức này hoàn toàn đến từ dữ liệu huấn luyện của nó, và do đó kéo theo một loạt vấn đề:

1. <strong>Tính thời sự của tri thức</strong>: dữ liệu huấn luyện của mô hình lớn có điểm cắt thời gian, không thể tiếp cận thông tin mới nhất
2. <strong>Tri thức chuyên ngành</strong>: mô hình tổng quát có thể thiếu tri thức chuyên sâu trong một lĩnh vực cụ thể
3. <strong>Độ chính xác của sự kiện</strong>: thông qua truy xuất để kiểm chứng, giảm vấn đề ảo giác của mô hình
4. <strong>Khả năng giải thích</strong>: cung cấp nguồn thông tin, tăng độ tin cậy của câu trả lời

Để khắc phục hạn chế này, kỹ thuật RAG ra đời. Tư tưởng cốt lõi của nó là trước khi mô hình sinh câu trả lời, trước tiên truy xuất từ một kho tri thức bên ngoài (như tài liệu, cơ sở dữ liệu, API) những thông tin liên quan nhất, rồi cung cấp những thông tin này cho mô hình cùng với ngữ cảnh.

### 8.1.3 Thiết kế kiến trúc hệ thống bộ nhớ và RAG

Dựa trên nền framework đã xây dựng ở chương 7 và những gợi mở từ khoa học nhận thức, chúng ta thiết kế một kiến trúc hệ thống bộ nhớ và RAG phân tầng, như minh họa trong Hình 8.2. Kiến trúc này không chỉ tham khảo cấu trúc phân tầng của hệ thống bộ nhớ con người mà còn tính đầy đủ đến khả năng mở rộng trong hiện thực kỹ thuật. Về hiện thực, chúng ta thiết kế bộ nhớ và RAG thành hai công cụ độc lập: `memory_tool` chịu trách nhiệm lưu trữ và bảo trì thông tin tương tác trong quá trình hội thoại, còn `rag_tool` chịu trách nhiệm truy xuất thông tin liên quan từ kho tri thức do người dùng cung cấp làm ngữ cảnh, đồng thời có thể tự động lưu những kết quả truy xuất quan trọng vào hệ thống bộ nhớ.
<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-2.png" alt="Sơ đồ kiến trúc hệ thống bộ nhớ và RAG của HelloAgents" width="95%"/>
  <p>Hình 8.2 Kiến trúc tổng thể hệ thống bộ nhớ và RAG của HelloAgents</p>
</div>

Hệ thống bộ nhớ áp dụng thiết kế kiến trúc bốn tầng:

```
Hệ thống bộ nhớ HelloAgents
├── Tầng hạ tầng (Infrastructure Layer)
│   ├── MemoryManager - Trình quản lý bộ nhớ (điều phối và phối hợp thống nhất)
│   ├── MemoryItem - Cấu trúc dữ liệu bộ nhớ (mục bộ nhớ được chuẩn hóa)
│   ├── MemoryConfig - Quản lý cấu hình (thiết lập tham số hệ thống)
│   └── BaseMemory - Lớp cơ sở bộ nhớ (định nghĩa giao diện chung)
├── Tầng loại bộ nhớ (Memory Types Layer)
│   ├── WorkingMemory - Bộ nhớ làm việc (thông tin tạm thời, quản lý TTL)
│   ├── EpisodicMemory - Bộ nhớ tình huống (sự kiện cụ thể, chuỗi thời gian)
│   ├── SemanticMemory - Bộ nhớ ngữ nghĩa (tri thức trừu tượng, quan hệ đồ thị)
│   └── PerceptualMemory - Bộ nhớ tri giác (dữ liệu đa phương thức)
├── Tầng backend lưu trữ (Storage Backend Layer)
│   ├── QdrantVectorStore - Lưu trữ vector (truy xuất ngữ nghĩa hiệu năng cao)
│   ├── Neo4jGraphStore - Lưu trữ đồ thị (quản lý đồ thị tri thức)
│   └── SQLiteDocumentStore - Lưu trữ tài liệu (lưu trữ bền vững có cấu trúc)
└── Tầng dịch vụ embedding (Embedding Service Layer)
    ├── DashScopeEmbedding - Embedding Tongyi Qianwen (API đám mây)
    ├── LocalTransformerEmbedding - Embedding cục bộ (triển khai ngoại tuyến)
    └── TFIDFEmbedding - Embedding TFIDF (phương án dự phòng nhẹ)
```

Hệ thống RAG tập trung vào việc tiếp nhận và sử dụng tri thức bên ngoài:

```
Hệ thống RAG HelloAgents
├── Tầng xử lý tài liệu (Document Processing Layer)
│   ├── DocumentProcessor - Bộ xử lý tài liệu (phân tích đa định dạng)
│   ├── Document - Đối tượng tài liệu (quản lý siêu dữ liệu)
│   └── Pipeline - Đường ống RAG (xử lý đầu-cuối)
├── Tầng biểu diễn embedding (Embedding Layer)
│   └── Giao diện embedding thống nhất - Tái sử dụng dịch vụ embedding của hệ thống bộ nhớ
├── Tầng lưu trữ vector (Vector Storage Layer)
│   └── QdrantVectorStore - Cơ sở dữ liệu vector (cách ly theo không gian tên)
└── Tầng hỏi đáp thông minh (Intelligent Q&A Layer)
    ├── Truy xuất đa chiến lược - Truy xuất vector + MQE + HyDE
    ├── Xây dựng ngữ cảnh - Hợp nhất và cắt tỉa đoạn thông minh
    └── Sinh tăng cường bằng LLM - Hỏi đáp chính xác dựa trên ngữ cảnh
```

### 8.1.4 Mục tiêu học tập và trải nghiệm nhanh của chương này

Trước tiên hãy xem nội dung học tập cốt lõi của chương 8:

```
hello-agents/
├── hello_agents/
│   ├── memory/                   # Mô-đun hệ thống bộ nhớ
│   │   ├── base.py               # Cấu trúc dữ liệu cơ sở (MemoryItem, MemoryConfig, BaseMemory)
│   │   ├── manager.py            # Trình quản lý bộ nhớ (điều phối thống nhất)
│   │   ├── embedding.py          # Dịch vụ embedding thống nhất (DashScope/Local/TFIDF)
│   │   ├── types/                # Hiện thực các loại bộ nhớ
│   │   │   ├── working.py        # Bộ nhớ làm việc (quản lý TTL, thuần bộ nhớ trong)
│   │   │   ├── episodic.py       # Bộ nhớ tình huống (chuỗi sự kiện, SQLite+Qdrant)
│   │   │   ├── semantic.py       # Bộ nhớ ngữ nghĩa (đồ thị tri thức, Qdrant+Neo4j)
│   │   │   └── perceptual.py     # Bộ nhớ tri giác (đa phương thức, SQLite+Qdrant)
│   │   ├── storage/              # Hiện thực backend lưu trữ
│   │   │   ├── qdrant_store.py   # Lưu trữ vector Qdrant (truy xuất vector hiệu năng cao)
│   │   │   ├── neo4j_store.py    # Lưu trữ đồ thị Neo4j (quản lý đồ thị tri thức)
│   │   │   └── document_store.py # Lưu trữ tài liệu SQLite (lưu trữ bền vững có cấu trúc)
│   │   └── rag/                  # Hệ thống RAG
│   │       ├── pipeline.py       # Đường ống RAG (xử lý đầu-cuối)
│   │       └── document.py       # Bộ xử lý tài liệu (phân tích đa định dạng)
│   └── tools/builtin/            # Mở rộng công cụ tích hợp
│       ├── memory_tool.py        # Công cụ bộ nhớ (năng lực ghi nhớ của Agent)
│       └── rag_tool.py           # Công cụ RAG (năng lực hỏi đáp thông minh)
└──
```

<strong>Bắt đầu nhanh: cài đặt framework HelloAgents</strong>

Để người đọc nhanh chóng trải nghiệm đầy đủ chức năng của chương này, chúng ta cung cấp gói Python có thể cài trực tiếp. Bạn có thể cài phiên bản tương ứng của chương này bằng lệnh sau:

```bash
# Nếu phiên bản 0.2.0 gặp tình trạng mô hình không khả dụng, hãy xem issue#320 hoặc chuyển sang phiên bản 0.2.9 để kiểm thử
pip install "hello-agents[all]==0.2.0"
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm
```

Ngoài ra, cần cấu hình API cho cơ sở dữ liệu đồ thị, cơ sở dữ liệu vector, LLM và phương án Embedding trong `.env`. Trong giáo trình, cơ sở dữ liệu vector dùng Qdrant, cơ sở dữ liệu đồ thị dùng Neo4J, Embedding ưu tiên nền tảng Bailian; nếu không có API có thể chuyển sang phương án mô hình triển khai cục bộ.

```bash
# ================================
# Cấu hình cơ sở dữ liệu vector Qdrant - Lấy API key tại: https://cloud.qdrant.io/
# ================================
# Dùng dịch vụ đám mây Qdrant (khuyến nghị)
QDRANT_URL=https://your-cluster.qdrant.tech:6333
QDRANT_API_KEY=your_qdrant_api_key_here

# Hoặc dùng Qdrant cục bộ (cần Docker)
# QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=

# Cấu hình collection Qdrant
QDRANT_COLLECTION=hello_agents_vectors
QDRANT_VECTOR_SIZE=384
QDRANT_DISTANCE=cosine
QDRANT_TIMEOUT=30

# ================================
# Cấu hình cơ sở dữ liệu đồ thị Neo4j - Lấy API key tại: https://neo4j.com/cloud/aura/
# ================================
# Dùng dịch vụ đám mây Neo4j Aura (khuyến nghị)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here

# Hoặc dùng Neo4j cục bộ (cần Docker)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=hello-agents-password

# Cấu hình kết nối Neo4j
NEO4J_DATABASE=neo4j
NEO4J_MAX_CONNECTION_LIFETIME=3600
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=60

# ==========================
# Ví dụ cấu hình Embedding - Có thể lấy từ bảng điều khiển Alibaba Cloud: https://dashscope.aliyun.com/
# ==========================
# - Nếu để trống, dashscope mặc định dùng text-embedding-v3; local mặc định dùng sentence-transformers/all-MiniLM-L6-v2
EMBED_MODEL_TYPE=dashscope
EMBED_MODEL_NAME=
EMBED_API_KEY=
EMBED_BASE_URL=
```

Việc học chương này có thể theo hai cách:

1. <strong>Học qua trải nghiệm</strong>: cài framework trực tiếp bằng `pip`, chạy mã ví dụ, nhanh chóng trải nghiệm các chức năng
2. <strong>Học sâu</strong>: theo nội dung chương này, tự hiện thực từng thành phần từ con số không, hiểu sâu tư tưởng thiết kế và chi tiết hiện thực của framework

Chúng ta khuyến nghị lộ trình "trải nghiệm trước, hiện thực sau". Trong chương này, chúng ta cung cấp tệp kiểm thử hoàn chỉnh; bạn có thể viết lại hàm cốt lõi và chạy kiểm thử để kiểm tra hiện thực của mình có đúng hay không.

Tuân theo các nguyên tắc thiết kế đã xác lập ở chương 7, chúng ta đóng gói năng lực bộ nhớ và RAG thành công cụ chuẩn, thay vì tạo lớp Agent mới. Trước khi bắt đầu, hãy dùng 30 giây trải nghiệm xây Agent có năng lực bộ nhớ và RAG với Hello-agents!

```python
# Cấu hình API mô hình lớn trong .env ở thư mục cùng cấp
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import MemoryTool, RAGTool

# Tạo thực thể LLM
llm = HelloAgentsLLM()

# Tạo registry công cụ
tool_registry = ToolRegistry()

# Thêm công cụ bộ nhớ
memory_tool = MemoryTool(user_id="user123")
tool_registry.register_tool(memory_tool)

# Thêm công cụ RAG
rag_tool = RAGTool(knowledge_base_path="./knowledge_base")
tool_registry.register_tool(rag_tool)

# Tạo Agent và cấu hình công cụ
agent = SimpleAgent(
    name="Trợ lý thông minh",
    llm=llm,
    system_prompt="Bạn là một trợ lý AI có năng lực ghi nhớ và truy xuất tri thức",
    tool_registry=tool_registry
)

# Bắt đầu hội thoại
response = agent.run("Xin chào! Hãy nhớ tôi tên là Trương Tam, tôi là một lập trình viên Python")
print(response)
```

Nếu mọi thứ đã được cấu hình xong, bạn có thể thấy nội dung sau.

```bash
[OK] Đã tạo xong bảng và chỉ mục của cơ sở dữ liệu SQLite
[OK] Khởi tạo xong lưu trữ tài liệu SQLite: ./memory_data\memory.db
INFO:hello_agents.memory.storage.qdrant_store:✅ Kết nối thành công dịch vụ đám mây Qdrant: https://0c517275-2ad0-4442-8309-11c36dc7e811.us-east-1-1.aws.cloud.qdrant.io:6333
INFO:hello_agents.memory.storage.qdrant_store:✅ Dùng collection Qdrant hiện có: hello_agents_vectors
INFO:hello_agents.memory.types.semantic:✅ Mô hình embedding sẵn sàng, số chiều: 1024
INFO:hello_agents.memory.types.semantic:✅ Khởi tạo xong cơ sở dữ liệu vector Qdrant
INFO:hello_agents.memory.storage.neo4j_store:✅ Kết nối thành công dịch vụ đám mây Neo4j: neo4j+s://851b3a28.databases.neo4j.io      NFO:hello_agents.memory.types.semantic:✅ Khởi tạo xong cơ sở dữ liệu đồ thị Neo4j
INFO:hello_agents.memory.storage.neo4j_store:✅ Tạo xong chỉ mục Neo4j
INFO:hello_agents.memory.types.semantic:✅ Khởi tạo xong cơ sở dữ liệu đồ thị Neo4j
INFO:hello_agents.memory.types.semantic:🏥 Trạng thái sức khỏe cơ sở dữ liệu: Qdrant=✅, Neo4j=✅
INFO:hello_agents.memory.types.semantic:✅ Tải mô hình spaCy tiếng Trung: zh_core_web_sm
INFO:hello_agents.memory.types.semantic:✅ Tải mô hình spaCy tiếng Anh: en_core_web_sm
INFO:hello_agents.memory.types.semantic:📚 Mô hình ngôn ngữ khả dụng: tiếng Trung, tiếng Anh
INFO:hello_agents.memory.types.semantic:Khởi tạo xong bộ nhớ ngữ nghĩa tăng cường (dùng cơ sở dữ liệu chuyên dụng Qdrant+Neo4j)
INFO:hello_agents.memory.manager:Khởi tạo xong MemoryManager, loại bộ nhớ được bật: ['working', 'episodic', 'semantic']
✅ Công cụ 'memory' đã được đăng ký.
INFO:hello_agents.memory.storage.qdrant_store:✅ Kết nối thành công dịch vụ đám mây Qdrant: https://0c517275-2ad0-4442-8309-11c36dc7eNFO:hello_agents.memory.storage.qdrant_store:✅ Dùng collection Qdrant hiện có: rag_knowledge_base
811.us-east-1-1.aws.cloud.qdrant.io:6333
INFO:hello_agents.memory.storage.qdrant_store:✅ Dùng collection Qdrant hiện có: rag_knowledge_base
✅ Khởi tạo thành công công cụ RAG: namespace=default, collection=rag_knowledge_base
✅ Công cụ 'rag' đã được đăng ký.
Xin chào Trương Tam! Rất vui được gặp bạn. Là một lập trình viên Python, chắc hẳn bạn rất đam mê lập trình. Nếu bạn có bất kỳ câu hỏi kỹ thuật nào hoặc cần trao đổi về các chủ đề liên quan đến Python,
hãy tìm tôi bất cứ lúc nào. Tôi sẽ cố gắng hết sức để giúp bạn. Có điều gì tôi có thể giúp bạn ngay bây giờ không?
```

## 8.2 Hệ thống bộ nhớ: cho Agent có khả năng ghi nhớ

### 8.2.1 Quy trình làm việc của hệ thống bộ nhớ

Trước khi bước vào giai đoạn hiện thực mã, chúng ta cần định nghĩa quy trình làm việc của hệ thống bộ nhớ. Quy trình này tham khảo mô hình bộ nhớ trong khoa học nhận thức, đồng thời ánh xạ mỗi giai đoạn nhận thức thành thành phần kỹ thuật và thao tác cụ thể. Hiểu mối quan hệ ánh xạ này sẽ giúp ích cho việc hiện thực mã về sau.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-3.png" alt="Quá trình hình thành bộ nhớ" width="90%"/>
  <p>Hình 8.3 Quá trình nhận thức hình thành bộ nhớ</p>
</div>

Như minh họa trong Hình 8.3, theo các nghiên cứu khoa học nhận thức, quá trình hình thành bộ nhớ của con người trải qua các giai đoạn sau:


1. <strong>Mã hóa (Encoding)</strong>: chuyển thông tin được tri giác thành dạng có thể lưu trữ
2. <strong>Lưu trữ (Storage)</strong>: giữ thông tin đã mã hóa trong hệ thống bộ nhớ
3. <strong>Truy xuất (Retrieval)</strong>: trích xuất thông tin liên quan từ bộ nhớ theo nhu cầu
4. <strong>Tích hợp (Consolidation)</strong>: chuyển bộ nhớ ngắn hạn thành bộ nhớ dài hạn
5. <strong>Quên (Forgetting)</strong>: xóa những thông tin không quan trọng hoặc đã lỗi thời

Dựa trên gợi mở này, chúng ta thiết kế cho HelloAgents một hệ thống bộ nhớ hoàn chỉnh. Tư tưởng cốt lõi là mô phỏng cách bộ não con người xử lý các loại thông tin khác nhau, chia bộ nhớ thành nhiều mô-đun chuyên biệt, và xây dựng một cơ chế quản lý thông minh. Hình 8.4 trình bày chi tiết quy trình làm việc của hệ thống này, bao gồm các khâu then chốt như thêm, truy xuất, tích hợp và quên bộ nhớ.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-4.png" alt="Quy trình làm việc của hệ thống bộ nhớ" width="95%"/>
  <p>Hình 8.4 Quy trình làm việc đầy đủ của hệ thống bộ nhớ HelloAgents</p>
</div>

Hệ thống bộ nhớ của chúng ta được cấu thành từ bốn loại mô-đun bộ nhớ khác nhau, mỗi mô-đun đều được tối ưu cho một kịch bản ứng dụng và vòng đời cụ thể:

Đầu tiên là <strong>bộ nhớ làm việc (Working Memory)</strong>, đóng vai trò "bộ nhớ ngắn hạn" của Agent, chủ yếu dùng để lưu thông tin ngữ cảnh của cuộc hội thoại hiện tại. Để đảm bảo truy cập và phản hồi tốc độ cao, dung lượng của nó được cố ý giới hạn (ví dụ, mặc định 50 mục), và vòng đời gắn với một phiên duy nhất; sau khi phiên kết thúc, nó sẽ tự động được dọn sạch.

Tiếp theo là <strong>bộ nhớ tình huống (Episodic Memory)</strong>, chịu trách nhiệm lưu trữ dài hạn các sự kiện tương tác cụ thể và trải nghiệm học tập của Agent. Khác với bộ nhớ làm việc, bộ nhớ tình huống chứa thông tin ngữ cảnh phong phú, hỗ trợ truy xuất hồi cố theo chuỗi thời gian hoặc theo chủ đề; đây là nền tảng để Agent "nhìn lại" và học hỏi từ kinh nghiệm quá khứ.

Tương ứng với các sự kiện cụ thể là <strong>bộ nhớ ngữ nghĩa (Semantic Memory)</strong>, lưu trữ những tri thức, khái niệm và quy tắc trừu tượng hơn. Ví dụ, sở thích người dùng biết được qua hội thoại, những chỉ thị cần tuân thủ lâu dài hoặc các điểm tri thức chuyên ngành đều phù hợp để lưu ở đây. Phần bộ nhớ này có tính bền vững và tầm quan trọng cao, là hạt nhân để Agent hình thành "hệ thống tri thức" và suy luận liên kết.

Cuối cùng, để tương thích với các tương tác đa phương tiện ngày càng phong phú, chúng ta đưa vào <strong>bộ nhớ tri giác (Perceptual Memory)</strong>. Mô-đun này chuyên xử lý thông tin đa phương thức như hình ảnh, âm thanh, và hỗ trợ truy xuất xuyên phương thức. Vòng đời của nó được quản lý động theo mức độ quan trọng của thông tin và dung lượng lưu trữ khả dụng.

### 8.2.2 Trải nghiệm nhanh: nắm bắt chức năng bộ nhớ trong 30 giây

Trước khi đi sâu vào chi tiết hiện thực, chúng ta hãy nhanh chóng trải nghiệm các chức năng cơ bản của hệ thống bộ nhớ:

```python
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import MemoryTool

# Tạo thực thể LLM
llm = HelloAgentsLLM()

# Tạo công cụ bộ nhớ
memory_tool = MemoryTool(user_id="user123")
tool_registry = ToolRegistry()
tool_registry.register_tool(memory_tool)

# Tạo Agent có năng lực ghi nhớ
agent = SimpleAgent(name="Trợ lý ghi nhớ", llm=llm, tool_registry=tool_registry)

# Trải nghiệm chức năng bộ nhớ
print("=== Thêm nhiều bộ nhớ ===")

# Thêm bộ nhớ thứ nhất
result1 = memory_tool.run("add", content="Người dùng Trương Tam là lập trình viên Python, tập trung vào học máy và phân tích dữ liệu", memory_type="semantic", importance=0.8)
print(f"Bộ nhớ 1: {result1}")

# Thêm bộ nhớ thứ hai
result2 = memory_tool.run("add", content="Lý Tứ là kỹ sư frontend, thành thạo phát triển React và Vue.js", memory_type="semantic", importance=0.7)
print(f"Bộ nhớ 2: {result2}")

# Thêm bộ nhớ thứ ba
result3 = memory_tool.run("add", content="Vương Ngũ là quản lý sản phẩm, phụ trách thiết kế trải nghiệm người dùng và phân tích yêu cầu", memory_type="semantic", importance=0.6)
print(f"Bộ nhớ 3: {result3}")

print("\n=== Tìm kiếm bộ nhớ cụ thể ===")
# Tìm kiếm bộ nhớ liên quan đến frontend
print("🔍 Tìm kiếm 'kỹ sư frontend':")
result = memory_tool.run("search", query="kỹ sư frontend", limit=3)
print(result)

print("\n=== Tóm tắt bộ nhớ ===")
result = memory_tool.run("summary")
print(result)
```

### 8.2.3 Chi tiết MemoryTool

Bây giờ chúng ta hãy áp dụng cách tiếp cận từ trên xuống, bắt đầu từ các thao tác cụ thể mà MemoryTool hỗ trợ, rồi dần đi sâu vào hiện thực tầng dưới. MemoryTool là giao diện thống nhất của hệ thống bộ nhớ, thiết kế của nó tuân theo mẫu kiến trúc "một cửa vào, phân phối xử lý":

````python
def execute(self, action: str, **kwargs) -> str:
    """Thực thi thao tác bộ nhớ

    Các thao tác được hỗ trợ:
    - add: thêm bộ nhớ (hỗ trợ 4 loại: working/episodic/semantic/perceptual)
    - search: tìm kiếm bộ nhớ
    - summary: lấy tóm tắt bộ nhớ
    - stats: lấy thông tin thống kê
    - update: cập nhật bộ nhớ
    - remove: xóa bộ nhớ
    - forget: quên bộ nhớ (nhiều chiến lược)
    - consolidate: tích hợp bộ nhớ (ngắn hạn→dài hạn)
    - clear_all: xóa toàn bộ bộ nhớ
    """

    if action == "add":
        return self._add_memory(**kwargs)
    elif action == "search":
        return self._search_memory(**kwargs)
    elif action == "summary":
        return self._get_summary(**kwargs)
    # ... các thao tác khác
````

Thiết kế giao diện `execute` thống nhất này đơn giản hóa cách Agent gọi công cụ: tham số `action` chỉ định thao tác cụ thể, còn `**kwargs` cho phép mỗi thao tác có nhu cầu tham số khác nhau. Dưới đây chúng ta sẽ liệt kê một số thao tác quan trọng hơn:

(1) Thao tác 1: add

Thao tác `add` là nền tảng của hệ thống bộ nhớ, nó mô phỏng quá trình bộ não con người mã hóa thông tin tri giác thành bộ nhớ. Trong hiện thực, chúng ta không chỉ lưu nội dung bộ nhớ mà còn thêm thông tin ngữ cảnh phong phú cho mỗi bộ nhớ; những thông tin này sẽ phát huy vai trò quan trọng trong truy xuất và quản lý về sau.

````python
def _add_memory(
    self,
    content: str = "",
    memory_type: str = "working",
    importance: float = 0.5,
    file_path: str = None,
    modality: str = None,
    **metadata
) -> str:
    """Thêm bộ nhớ"""
    try:
        # Đảm bảo ID phiên tồn tại
        if self.current_session_id is None:
            self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Hỗ trợ tệp cho bộ nhớ tri giác
        if memory_type == "perceptual" and file_path:
            inferred = modality or self._infer_modality(file_path)
            metadata.setdefault("modality", inferred)
            metadata.setdefault("raw_data", file_path)

        # Thêm thông tin phiên vào siêu dữ liệu
        metadata.update({
            "session_id": self.current_session_id,
            "timestamp": datetime.now().isoformat()
        })

        memory_id = self.memory_manager.add_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata,
            auto_classify=False
        )

        return f"✅ Đã thêm bộ nhớ (ID: {memory_id[:8]}...)"

    except Exception as e:
        return f"❌ Thêm bộ nhớ thất bại: {str(e)}"
````

Ở đây chủ yếu hiện thực ba nhiệm vụ then chốt: quản lý tự động ID phiên (đảm bảo mỗi bộ nhớ có quy thuộc phiên rõ ràng), xử lý thông minh dữ liệu đa phương thức (tự động suy luận loại tệp và lưu siêu dữ liệu liên quan), và tự động bổ sung thông tin ngữ cảnh (thêm dấu thời gian và thông tin phiên cho mỗi bộ nhớ). Trong đó, tham số `importance` (mặc định 0.5) dùng để đánh dấu mức độ quan trọng của bộ nhớ, phạm vi giá trị 0.0-1.0; cơ chế này mô phỏng việc bộ não con người đánh giá mức quan trọng của các thông tin khác nhau. Thiết kế này cho phép Agent tự động phân biệt hội thoại ở các khoảng thời gian khác nhau, đồng thời cung cấp thông tin ngữ cảnh phong phú cho truy xuất và quản lý về sau.

Trong đó, với mỗi loại bộ nhớ, chúng ta cung cấp các ví dụ sử dụng khác nhau:

```python
# 1. Bộ nhớ làm việc - thông tin tạm thời, dung lượng hạn chế
memory_tool.run("add",
    content="Người dùng vừa hỏi về hàm Python",
    memory_type="working",
    importance=0.6
)

# 2. Bộ nhớ tình huống - sự kiện và trải nghiệm cụ thể
memory_tool.run("add",
    content="Ngày 15 tháng 3 năm 2024, người dùng Trương Tam hoàn thành dự án Python đầu tiên",
    memory_type="episodic",
    importance=0.8,
    event_type="milestone",
    location="Nền tảng học trực tuyến"
)

# 3. Bộ nhớ ngữ nghĩa - tri thức và khái niệm trừu tượng
memory_tool.run("add",
    content="Python là một ngôn ngữ lập trình thông dịch, hướng đối tượng",
    memory_type="semantic",
    importance=0.9,
    knowledge_type="factual"
)

# 4. Bộ nhớ tri giác - thông tin đa phương thức
memory_tool.run("add",
    content="Người dùng đã tải lên một ảnh chụp mã Python, chứa định nghĩa hàm",
    memory_type="perceptual",
    importance=0.7,
    modality="image",
    file_path="./uploads/code_screenshot.png"
)
```

(2) Thao tác 2: search

Thao tác `search` là chức năng cốt lõi của hệ thống bộ nhớ, nó cần nhanh chóng tìm ra trong lượng lớn bộ nhớ những nội dung liên quan nhất đến truy vấn. Nó liên quan đến nhiều khâu như hiểu ngữ nghĩa, tính toán độ tương đồng và xếp hạng kết quả.

````python
def _search_memory(
    self,
    query: str,
    limit: int = 5,
    memory_types: List[str] = None,
    memory_type: str = None,
    min_importance: float = 0.1
) -> str:
    """Tìm kiếm bộ nhớ"""
    try:
        # Chuẩn hóa tham số
        if memory_type and not memory_types:
            memory_types = [memory_type]

        results = self.memory_manager.retrieve_memories(
            query=query,
            limit=limit,
            memory_types=memory_types,
            min_importance=min_importance
        )

        if not results:
            return f"🔍 Không tìm thấy bộ nhớ nào liên quan đến '{query}'"

        # Định dạng kết quả
        formatted_results = []
        formatted_results.append(f"🔍 Tìm thấy {len(results)} bộ nhớ liên quan:")

        for i, memory in enumerate(results, 1):
            memory_type_label = {
                "working": "bộ nhớ làm việc",
                "episodic": "bộ nhớ tình huống",
                "semantic": "bộ nhớ ngữ nghĩa",
                "perceptual": "bộ nhớ tri giác"
            }.get(memory.memory_type, memory.memory_type)

            content_preview = memory.content[:80] + "..." if len(memory.content) > 80 else memory.content
            formatted_results.append(
                f"{i}. [{memory_type_label}] {content_preview} (độ quan trọng: {memory.importance:.2f})"
            )

        return "\n".join(formatted_results)

    except Exception as e:
        return f"❌ Tìm kiếm bộ nhớ thất bại: {str(e)}"
````

Về thiết kế, thao tác tìm kiếm hỗ trợ cả hai dạng tham số số ít và số nhiều (`memory_type` và `memory_types`), cho phép người dùng diễn đạt nhu cầu theo cách tự nhiên nhất. Trong đó, tham số `min_importance` (mặc định 0.1) dùng để lọc bỏ những bộ nhớ chất lượng thấp. Về cách sử dụng chức năng tìm kiếm, có thể tham khảo ví dụ sau.

```python
# Tìm kiếm cơ bản
result = memory_tool.execute("search", query="lập trình Python", limit=5)

# Tìm kiếm chỉ định loại bộ nhớ
result = memory_tool.execute("search",
    query="tiến độ học",
    memory_type="episodic",
    limit=3
)

# Tìm kiếm nhiều loại
result = memory_tool.execute("search",
    query="định nghĩa hàm",
    memory_types=["semantic", "episodic"],
    min_importance=0.5
)
```

(3) Thao tác 3: forget

Cơ chế quên là chức năng mang đậm màu sắc khoa học nhận thức nhất, nó mô phỏng quá trình quên có chọn lọc của bộ não con người, hỗ trợ ba chiến lược: dựa trên độ quan trọng (xóa những bộ nhớ không quan trọng), dựa trên thời gian (xóa những bộ nhớ lỗi thời) và dựa trên dung lượng (khi lưu trữ gần đạt giới hạn thì xóa những bộ nhớ kém quan trọng nhất).

````python
def _forget(self, strategy: str = "importance_based", threshold: float = 0.1, max_age_days: int = 30) -> str:
    """Quên bộ nhớ (hỗ trợ nhiều chiến lược)"""
    try:
        count = self.memory_manager.forget_memories(
            strategy=strategy,
            threshold=threshold,
            max_age_days=max_age_days
        )
        return f"🧹 Đã quên {count} bộ nhớ (chiến lược: {strategy})"
    except Exception as e:
        return f"❌ Quên bộ nhớ thất bại: {str(e)}"
````

<strong>Cách sử dụng ba chiến lược quên:</strong>

```python
# 1. Quên dựa trên độ quan trọng - xóa bộ nhớ có độ quan trọng dưới ngưỡng
memory_tool.execute("forget",
    strategy="importance_based",
    threshold=0.2
)

# 2. Quên dựa trên thời gian - xóa bộ nhớ vượt quá số ngày chỉ định
memory_tool.execute("forget",
    strategy="time_based",
    max_age_days=30
)

# 3. Quên dựa trên dung lượng - xóa những bộ nhớ kém quan trọng nhất khi số lượng vượt giới hạn
memory_tool.execute("forget",
    strategy="capacity_based",
    threshold=0.3
)
```

(4) Thao tác 4: consolidate

````python
def _consolidate(self, from_type: str = "working", to_type: str = "episodic", importance_threshold: float = 0.7) -> str:
    """Tích hợp bộ nhớ (nâng bộ nhớ ngắn hạn quan trọng thành bộ nhớ dài hạn)"""
    try:
        count = self.memory_manager.consolidate_memories(
            from_type=from_type,
            to_type=to_type,
            importance_threshold=importance_threshold,
        )
        return f"🔄 Đã tích hợp {count} bộ nhớ thành bộ nhớ dài hạn ({from_type} → {to_type}, ngưỡng={importance_threshold})"
    except Exception as e:
        return f"❌ Tích hợp bộ nhớ thất bại: {str(e)}"
````

Thao tác consolidate vay mượn khái niệm cố định hóa bộ nhớ trong khoa học thần kinh, mô phỏng quá trình bộ não con người chuyển bộ nhớ ngắn hạn thành bộ nhớ dài hạn. Thiết lập mặc định là chuyển những bộ nhớ làm việc có độ quan trọng trên 0.7 thành bộ nhớ tình huống; ngưỡng này đảm bảo chỉ những thông tin thực sự quan trọng mới được lưu giữ dài hạn. Toàn bộ quá trình là tự động, người dùng không cần chọn thủ công bộ nhớ cụ thể; hệ thống sẽ thông minh nhận diện những bộ nhớ thỏa mãn điều kiện và thực thi chuyển đổi loại.

<strong>Ví dụ sử dụng tích hợp bộ nhớ:</strong>

```python
# Chuyển bộ nhớ làm việc quan trọng thành bộ nhớ tình huống
memory_tool.execute("consolidate",
    from_type="working",
    to_type="episodic",
    importance_threshold=0.7
)

# Chuyển bộ nhớ tình huống quan trọng thành bộ nhớ ngữ nghĩa
memory_tool.execute("consolidate",
    from_type="episodic",
    to_type="semantic",
    importance_threshold=0.8
)
```

Thông qua sự phối hợp của một số thao tác cốt lõi trên, MemoryTool xây dựng một hệ thống quản lý vòng đời bộ nhớ hoàn chỉnh. Từ việc tạo, truy xuất, tóm tắt đến quên, tích hợp và quản lý bộ nhớ, tất cả tạo thành một hệ thống quản lý bộ nhớ thông minh khép kín, giúp Agent thực sự có năng lực ghi nhớ giống con người.

### 8.2.4 Chi tiết MemoryManager

Sau khi đã hiểu thiết kế giao diện của MemoryTool, chúng ta hãy đi sâu vào hiện thực tầng dưới để xem MemoryTool phối hợp với MemoryManager như thế nào. Thiết kế phân tầng này thể hiện nguyên tắc tách biệt mối quan tâm trong kỹ thuật phần mềm: MemoryTool tập trung vào giao diện người dùng và xử lý tham số, còn MemoryManager chịu trách nhiệm logic quản lý bộ nhớ cốt lõi.

Khi khởi tạo, MemoryTool sẽ tạo một thực thể MemoryManager và bật các mô-đun bộ nhớ khác nhau theo cấu hình. Thiết kế này cho phép người dùng chọn bật những loại bộ nhớ nào theo nhu cầu cụ thể, vừa đảm bảo đầy đủ chức năng, vừa tránh tiêu tốn tài nguyên không cần thiết.
````python
class MemoryTool(Tool):
    """Công cụ bộ nhớ - cung cấp chức năng ghi nhớ cho Agent"""

    def __init__(
        self,
        user_id: str = "default_user",
        memory_config: MemoryConfig = None,
        memory_types: List[str] = None
    ):
        super().__init__(
            name="memory",
            description="Công cụ bộ nhớ - có thể lưu trữ và truy xuất lịch sử hội thoại, tri thức và kinh nghiệm"
        )

        # Khởi tạo trình quản lý bộ nhớ
        self.memory_config = memory_config or MemoryConfig()
        self.memory_types = memory_types or ["working", "episodic", "semantic"]

        self.memory_manager = MemoryManager(
            config=self.memory_config,
            user_id=user_id,
            enable_working="working" in self.memory_types,
            enable_episodic="episodic" in self.memory_types,
            enable_semantic="semantic" in self.memory_types,
            enable_perceptual="perceptual" in self.memory_types
        )
````
MemoryManager với vai trò người điều phối cốt lõi của hệ thống bộ nhớ, chịu trách nhiệm quản lý các mô-đun bộ nhớ khác nhau và cung cấp giao diện thao tác thống nhất. Năng lực lưu trữ và truy xuất cụ thể do từng loại bộ nhớ hiện thực ở bên trong.

````python
class MemoryManager:
    """Trình quản lý bộ nhớ - giao diện thao tác bộ nhớ thống nhất"""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        user_id: str = "default_user",
        enable_working: bool = True,
        enable_episodic: bool = True,
        enable_semantic: bool = True,
        enable_perceptual: bool = False
    ):
        self.config = config or MemoryConfig()
        self.user_id = user_id

        # Chức năng lưu trữ và truy xuất do từng loại bộ nhớ hiện thực ở bên trong

        # Khởi tạo các loại bộ nhớ
        self.memory_types = {}

        if enable_working:
            self.memory_types['working'] = WorkingMemory(self.config)

        if enable_episodic:
            self.memory_types['episodic'] = EpisodicMemory(self.config)

        if enable_semantic:
            self.memory_types['semantic'] = SemanticMemory(self.config)

        if enable_perceptual:
            self.memory_types['perceptual'] = PerceptualMemory(self.config)
````

### 8.2.5 Bốn loại bộ nhớ

Bây giờ chúng ta hãy tìm hiểu sâu hiện thực cụ thể của bốn loại bộ nhớ; mỗi loại bộ nhớ đều có đặc điểm và kịch bản ứng dụng riêng:

(1) Bộ nhớ làm việc (WorkingMemory)

Bộ nhớ làm việc là phần hoạt động tích cực nhất trong hệ thống bộ nhớ, chịu trách nhiệm lưu thông tin tạm thời trong phiên hội thoại hiện tại. Trọng tâm thiết kế của bộ nhớ làm việc là truy cập nhanh và tự động dọn sạch; thiết kế này đảm bảo tốc độ phản hồi và hiệu quả tài nguyên của hệ thống.

Bộ nhớ làm việc áp dụng phương án lưu trữ thuần bộ nhớ trong, kết hợp cơ chế TTL (Time To Live) để tự động dọn sạch. Ưu điểm của thiết kế này là tốc độ truy cập cực nhanh, nhưng cũng có nghĩa nội dung của bộ nhớ làm việc sẽ mất đi sau khi hệ thống khởi động lại. Đặc tính này hoàn toàn phù hợp với định vị của bộ nhớ làm việc: lưu trữ thông tin tạm thời, dễ biến đổi.


````python
class WorkingMemory:
    """Hiện thực bộ nhớ làm việc
    Đặc điểm:
    - Dung lượng hạn chế (mặc định 50 mục) + tự động dọn sạch theo TTL
    - Lưu trữ thuần bộ nhớ trong, tốc độ truy cập cực nhanh
    - Truy xuất từ vựng kết hợp: độ tương đồng trọng số từ TF-IDF + khớp từ khóa
    """

    def __init__(self, config: MemoryConfig):
        self.max_capacity = config.working_memory_capacity or 50
        self.max_age_minutes = config.working_memory_ttl or 60
        self.memories = []

    def add(self, memory_item: MemoryItem) -> str:
        """Thêm bộ nhớ làm việc"""
        self._expire_old_memories()  # Dọn sạch mục hết hạn

        if len(self.memories) >= self.max_capacity:
            self._remove_lowest_priority_memory()  # Quản lý dung lượng

        self.memories.append(memory_item)
        return memory_item.id

    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """Truy xuất từ vựng kết hợp: độ tương đồng trọng số từ TF-IDF + khớp từ khóa"""
        self._expire_old_memories()

        # Tính độ tương đồng trọng số từ TF-IDF
        vector_scores = self._try_tfidf_search(query)

        # Tính điểm tổng hợp
        scored_memories = []
        for memory in self.memories:
            vector_score = vector_scores.get(memory.id, 0.0)
            keyword_score = self._calculate_keyword_score(query, memory.content)

            # Điểm pha trộn
            base_relevance = vector_score * 0.7 + keyword_score * 0.3 if vector_score > 0 else keyword_score
            time_decay = self._calculate_time_decay(memory.timestamp)
            importance_weight = 0.8 + (memory.importance * 0.4)

            final_score = base_relevance * time_decay * importance_weight
            if final_score > 0:
                scored_memories.append((final_score, memory))

        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored_memories[:limit]]
````
Bộ nhớ làm việc áp dụng chiến lược truy xuất từ vựng kết hợp: dùng TF-IDF biểu diễn văn bản thành vector từ vựng thưa và tính độ tương đồng từ vựng, đồng thời kết hợp khớp từ khóa; khi TF-IDF không khả dụng hoặc không tạo ra điểm hợp lệ thì dùng điểm từ khóa. Biểu diễn vector hóa của TF-IDF đến từ tần suất từ và tần suất nghịch đảo tài liệu, không tương đương với truy xuất ngữ nghĩa dựa trên embedding dày đặc. Thuật toán chấm điểm kết hợp độ liên quan từ vựng, suy giảm theo thời gian và trọng số độ quan trọng; công thức điểm cuối cùng là: `(độ liên quan × suy giảm thời gian) × (0.8 + độ quan trọng × 0.4)`.

(2) Bộ nhớ tình huống (EpisodicMemory)

Bộ nhớ tình huống chịu trách nhiệm lưu trữ các sự kiện và trải nghiệm cụ thể; trọng tâm thiết kế của nó là giữ tính đầy đủ của sự kiện và quan hệ chuỗi thời gian. Bộ nhớ tình huống áp dụng phương án lưu trữ kết hợp SQLite+Qdrant: SQLite chịu trách nhiệm lưu trữ dữ liệu có cấu trúc và truy vấn phức tạp, Qdrant chịu trách nhiệm truy xuất vector hiệu quả.

````python
class EpisodicMemory:
    """Hiện thực bộ nhớ tình huống
    Đặc điểm:
    - Kiến trúc lưu trữ kết hợp SQLite+Qdrant
    - Hỗ trợ truy xuất theo chuỗi thời gian và theo phiên
    - Lọc có cấu trúc + truy xuất vector ngữ nghĩa
    """

    def __init__(self, config: MemoryConfig):
        self.doc_store = SQLiteDocumentStore(config.database_path)
        self.vector_store = QdrantVectorStore(config.qdrant_url, config.qdrant_api_key)
        self.embedder = create_embedding_model_with_fallback()
        self.sessions = {}  # Chỉ mục phiên

    def add(self, memory_item: MemoryItem) -> str:
        """Thêm bộ nhớ tình huống"""
        # Tạo đối tượng tình huống
        episode = Episode(
            episode_id=memory_item.id,
            session_id=memory_item.metadata.get("session_id", "default"),
            timestamp=memory_item.timestamp,
            content=memory_item.content,
            context=memory_item.metadata
        )

        # Cập nhật chỉ mục phiên
        session_id = episode.session_id
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(episode.episode_id)

        # Lưu trữ bền vững (SQLite + Qdrant)
        self._persist_episode(episode)
        return memory_item.id

    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """Truy xuất kết hợp: lọc có cấu trúc + truy xuất vector ngữ nghĩa"""
        # 1. Tiền lọc có cấu trúc (khoảng thời gian, độ quan trọng, v.v.)
        candidate_ids = self._structured_filter(**kwargs)

        # 2. Truy xuất ngữ nghĩa bằng vector
        hits = self._vector_search(query, limit * 5, kwargs.get("user_id"))

        # 3. Chấm điểm và xếp hạng tổng hợp
        results = []
        for hit in hits:
            if self._should_include(hit, candidate_ids, kwargs):
                score = self._calculate_episode_score(hit)
                memory_item = self._create_memory_item(hit)
                results.append((score, memory_item))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:limit]]

    def _calculate_episode_score(self, hit) -> float:
        """Thuật toán chấm điểm bộ nhớ tình huống"""
        vec_score = float(hit.get("score", 0.0))
        recency_score = self._calculate_recency(hit["metadata"]["timestamp"])
        importance = hit["metadata"].get("importance", 0.5)

        # Công thức chấm điểm: (độ tương đồng vector × 0.8 + độ gần thời gian × 0.2) × trọng số độ quan trọng
        base_relevance = vec_score * 0.8 + recency_score * 0.2
        importance_weight = 0.8 + (importance * 0.4)

        return base_relevance * importance_weight
````
Hiện thực truy xuất của bộ nhớ tình huống thể hiện cơ chế chấm điểm đa yếu tố phức tạp. Nó không chỉ xem xét độ tương đồng ngữ nghĩa mà còn thêm yếu tố độ gần thời gian, cuối cùng điều chỉnh bằng trọng số độ quan trọng. Công thức chấm điểm là: `(độ tương đồng vector × 0.8 + độ gần thời gian × 0.2) × (0.8 + độ quan trọng × 0.4)`, đảm bảo kết quả truy xuất vừa liên quan ngữ nghĩa vừa liên quan thời gian.

(3) Bộ nhớ ngữ nghĩa (SemanticMemory)

Bộ nhớ ngữ nghĩa là phần phức tạp nhất trong hệ thống bộ nhớ, chịu trách nhiệm lưu trữ các khái niệm, quy tắc và tri thức trừu tượng. Trọng tâm thiết kế của bộ nhớ ngữ nghĩa là biểu diễn có cấu trúc tri thức và năng lực suy luận thông minh. Bộ nhớ ngữ nghĩa áp dụng kiến trúc kết hợp cơ sở dữ liệu đồ thị Neo4j và cơ sở dữ liệu vector Qdrant; thiết kế này cho phép hệ thống vừa truy xuất ngữ nghĩa nhanh, vừa tận dụng đồ thị tri thức để suy luận quan hệ phức tạp.

````python
class SemanticMemory(BaseMemory):
    """Hiện thực bộ nhớ ngữ nghĩa

    Đặc điểm:
    - Dùng mô hình tiền huấn luyện tiếng Trung của HuggingFace để embedding văn bản
    - Truy xuất vector để khớp độ tương đồng nhanh
    - Đồ thị tri thức lưu trữ thực thể và quan hệ
    - Chiến lược truy xuất kết hợp: vector + đồ thị + suy luận ngữ nghĩa
    """

    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)

        # Mô hình embedding (cung cấp thống nhất)
        self.embedding_model = get_text_embedder()

        # Lưu trữ bằng cơ sở dữ liệu chuyên dụng
        self.vector_store = QdrantConnectionManager.get_instance(**qdrant_config)
        self.graph_store = Neo4jGraphStore(**neo4j_config)

        # Bộ đệm thực thể và quan hệ
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []

        # Bộ xử lý NLP (hỗ trợ tiếng Trung và tiếng Anh)
        self.nlp = self._init_nlp()
````
Quá trình thêm bộ nhớ ngữ nghĩa thể hiện quy trình hoàn chỉnh của việc xây dựng đồ thị tri thức. Hệ thống không chỉ lưu nội dung bộ nhớ mà còn tự động trích xuất thực thể và quan hệ, xây dựng biểu diễn tri thức có cấu trúc:

```python
def add(self, memory_item: MemoryItem) -> str:
    """Thêm bộ nhớ ngữ nghĩa"""
    # 1. Sinh embedding văn bản
    embedding = self.embedding_model.encode(memory_item.content)

    # 2. Trích xuất thực thể và quan hệ
    entities = self._extract_entities(memory_item.content)
    relations = self._extract_relations(memory_item.content, entities)

    # 3. Lưu vào cơ sở dữ liệu đồ thị Neo4j
    for entity in entities:
        self._add_entity_to_graph(entity, memory_item)

    for relation in relations:
        self._add_relation_to_graph(relation, memory_item)

    # 4. Lưu vào cơ sở dữ liệu vector Qdrant
    metadata = {
        "memory_id": memory_item.id,
        "entities": [e.entity_id for e in entities],
        "entity_count": len(entities),
        "relation_count": len(relations)
    }

    self.vector_store.add_vectors(
        vectors=[embedding.tolist()],
        metadata=[metadata],
        ids=[memory_item.id]
    )
```

Truy xuất của bộ nhớ ngữ nghĩa hiện thực chiến lược tìm kiếm kết hợp, kết hợp năng lực hiểu ngữ nghĩa của truy xuất vector với năng lực suy luận quan hệ của truy xuất đồ thị:

```python
def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
    """Truy xuất bộ nhớ ngữ nghĩa"""
    # 1. Truy xuất vector
    vector_results = self._vector_search(query, limit * 2, user_id)

    # 2. Truy xuất đồ thị
    graph_results = self._graph_search(query, limit * 2, user_id)

    # 3. Xếp hạng kết hợp
    combined_results = self._combine_and_rank_results(
        vector_results, graph_results, query, limit
    )

    return combined_results[:limit]
```

Thuật toán xếp hạng kết hợp áp dụng cơ chế chấm điểm đa yếu tố:

```python
def _combine_and_rank_results(self, vector_results, graph_results, query, limit):
    """Xếp hạng kết quả kết hợp"""
    combined = {}

    # Hợp nhất kết quả truy xuất vector và đồ thị
    for result in vector_results:
        combined[result["memory_id"]] = {
            **result,
            "vector_score": result.get("score", 0.0),
            "graph_score": 0.0
        }

    for result in graph_results:
        memory_id = result["memory_id"]
        if memory_id in combined:
            combined[memory_id]["graph_score"] = result.get("similarity", 0.0)
        else:
            combined[memory_id] = {
                **result,
                "vector_score": 0.0,
                "graph_score": result.get("similarity", 0.0)
            }

    # Tính điểm kết hợp
    for memory_id, result in combined.items():
        vector_score = result["vector_score"]
        graph_score = result["graph_score"]
        importance = result.get("importance", 0.5)

        # Điểm tương đồng cơ sở
        base_relevance = vector_score * 0.7 + graph_score * 0.3

        # Trọng số độ quan trọng [0.8, 1.2]
        importance_weight = 0.8 + (importance * 0.4)

        # Điểm cuối cùng: độ tương đồng * trọng số độ quan trọng
        combined_score = base_relevance * importance_weight
        result["combined_score"] = combined_score

    # Sắp xếp và trả về
    sorted_results = sorted(
        combined.values(),
        key=lambda x: x["combined_score"],
        reverse=True
    )

    return sorted_results[:limit]
```

Công thức chấm điểm của bộ nhớ ngữ nghĩa là: `(độ tương đồng vector × 0.7 + độ tương đồng đồ thị × 0.3) × (0.8 + độ quan trọng × 0.4)`. Tư tưởng cốt lõi của thiết kế này là:

- <strong>Trọng số truy xuất vector (0.7)</strong>: độ tương đồng ngữ nghĩa là yếu tố chính, đảm bảo kết quả truy xuất liên quan ngữ nghĩa đến truy vấn
- <strong>Trọng số truy xuất đồ thị (0.3)</strong>: suy luận quan hệ đóng vai trò bổ sung, phát hiện liên kết ẩn giữa các khái niệm
- <strong>Phạm vi trọng số độ quan trọng [0.8, 1.2]</strong>: tránh để độ quan trọng ảnh hưởng quá mức đến xếp hạng độ tương đồng, giữ độ chính xác của truy xuất

(4) Bộ nhớ tri giác (PerceptualMemory)

Bộ nhớ tri giác hỗ trợ lưu trữ và truy xuất dữ liệu nhiều phương thức như văn bản, hình ảnh, âm thanh. Nó áp dụng chiến lược lưu trữ tách biệt theo phương thức, tạo các collection vector độc lập cho dữ liệu của từng phương thức; thiết kế này tránh vấn đề không khớp số chiều, đồng thời đảm bảo độ chính xác của truy xuất:

````python
class PerceptualMemory(BaseMemory):
    """Hiện thực bộ nhớ tri giác

    Đặc điểm:
    - Hỗ trợ dữ liệu đa phương thức (văn bản, hình ảnh, âm thanh, v.v.)
    - Tìm kiếm độ tương đồng xuyên phương thức
    - Hiểu ngữ nghĩa dữ liệu tri giác
    - Hỗ trợ sinh nội dung và truy xuất
    """

    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)

        # Bộ mã hóa đa phương thức
        self.text_embedder = get_text_embedder()
        self._clip_model = self._init_clip_model()  # Mã hóa hình ảnh
        self._clap_model = self._init_clap_model()  # Mã hóa âm thanh

        # Lưu trữ vector tách biệt theo phương thức
        self.vector_stores = {
            "text": QdrantConnectionManager.get_instance(
                collection_name="perceptual_text",
                vector_size=self.vector_dim
            ),
            "image": QdrantConnectionManager.get_instance(
                collection_name="perceptual_image",
                vector_size=self._image_dim
            ),
            "audio": QdrantConnectionManager.get_instance(
                collection_name="perceptual_audio",
                vector_size=self._audio_dim
            )
        }
````
Truy xuất của bộ nhớ tri giác hỗ trợ hai chế độ: cùng phương thức và xuyên phương thức. Truy xuất cùng phương thức tận dụng bộ mã hóa chuyên dụng để khớp chính xác, còn truy xuất xuyên phương thức cần cơ chế căn chỉnh ngữ nghĩa phức tạp hơn:

```python
def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
    """Truy xuất bộ nhớ tri giác (có thể lọc phương thức; truy xuất vector cùng phương thức + kết hợp thời gian/độ quan trọng)"""
    user_id = kwargs.get("user_id")
    target_modality = kwargs.get("target_modality")
    query_modality = kwargs.get("query_modality", target_modality or "text")

    # Truy xuất vector cùng phương thức
    try:
        query_vector = self._encode_data(query, query_modality)
        store = self._get_vector_store_for_modality(target_modality or query_modality)

        where = {"memory_type": "perceptual"}
        if user_id:
            where["user_id"] = user_id
        if target_modality:
            where["modality"] = target_modality

        hits = store.search_similar(
            query_vector=query_vector,
            limit=max(limit * 5, 20),
            where=where
        )
    except Exception:
        hits = []

    # Xếp hạng kết hợp (độ tương đồng vector + độ gần thời gian + trọng số độ quan trọng)
    results = []
    for hit in hits:
        vector_score = float(hit.get("score", 0.0))
        recency_score = self._calculate_recency_score(hit["metadata"]["timestamp"])
        importance = hit["metadata"].get("importance", 0.5)

        # Thuật toán chấm điểm
        base_relevance = vector_score * 0.8 + recency_score * 0.2
        importance_weight = 0.8 + (importance * 0.4)
        combined_score = base_relevance * importance_weight

        results.append((combined_score, self._create_memory_item(hit)))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in results[:limit]]
```

Công thức chấm điểm của bộ nhớ tri giác là: `(độ tương đồng vector × 0.8 + độ gần thời gian × 0.2) × (0.8 + độ quan trọng × 0.4)`. Cơ chế chấm điểm của bộ nhớ tri giác còn hỗ trợ truy xuất xuyên phương thức, thông qua không gian vector thống nhất để căn chỉnh ngữ nghĩa dữ liệu của các phương thức khác nhau như văn bản, hình ảnh, âm thanh. Khi thực hiện truy xuất xuyên phương thức, hệ thống sẽ tự động điều chỉnh trọng số chấm điểm, đảm bảo tính đa dạng và độ chính xác của kết quả truy xuất. Ngoài ra, việc tính độ gần thời gian trong bộ nhớ tri giác áp dụng mô hình suy giảm theo hàm mũ:

```python
def _calculate_recency_score(self, timestamp: str) -> float:
    """Tính điểm độ gần thời gian"""
    try:
        memory_time = datetime.fromisoformat(timestamp)
        current_time = datetime.now()
        age_hours = (current_time - memory_time).total_seconds() / 3600

        # Suy giảm hàm mũ: giữ điểm cao trong 24 giờ, sau đó suy giảm dần
        decay_factor = 0.1  # Hệ số suy giảm
        recency_score = math.exp(-decay_factor * age_hours / 24)

        return max(0.1, recency_score)  # Giữ tối thiểu điểm cơ sở 0.1
    except Exception:
        return 0.5  # Điểm trung bình mặc định
```

Mô hình suy giảm theo thời gian này mô phỏng đường cong quên trong bộ nhớ con người, đảm bảo hệ thống bộ nhớ tri giác có thể ưu tiên truy xuất những nội dung bộ nhớ liên quan hơn về thời gian.

## 8.3 Hệ thống RAG: tăng cường truy xuất tri thức

### 8.3.1 Kiến thức cơ bản về RAG

Trước khi đi sâu vào hiện thực hệ thống RAG của HelloAgents, chúng ta hãy tìm hiểu các khái niệm cơ bản, quá trình phát triển và nguyên lý cốt lõi của kỹ thuật RAG. Vì nội dung bài viết này không được sáng tác lấy RAG làm nền tảng, nên ở đây chỉ giúp người đọc nhanh chóng sắp xếp lại các khái niệm liên quan, để hiểu rõ hơn các lựa chọn kỹ thuật và điểm đổi mới trong thiết kế hệ thống.

(1) RAG là gì?

Sinh tăng cường truy xuất (Retrieval-Augmented Generation, RAG) là một kỹ thuật kết hợp truy xuất thông tin và sinh văn bản. Tư tưởng cốt lõi của nó là: trước khi sinh câu trả lời, trước tiên truy xuất thông tin liên quan từ kho tri thức bên ngoài, rồi cung cấp thông tin đã truy xuất cho mô hình ngôn ngữ lớn làm ngữ cảnh, từ đó sinh ra câu trả lời chính xác và đáng tin cậy hơn.

Do đó, sinh tăng cường truy xuất có thể được tách thành ba từ. <strong>Truy xuất</strong> là tra cứu nội dung liên quan từ kho tri thức; <strong>tăng cường</strong> là đưa kết quả truy xuất vào prompt để hỗ trợ mô hình sinh; <strong>sinh</strong> là xuất ra câu trả lời vừa chính xác vừa minh bạch.

(2) Quy trình làm việc cơ bản

Một quy trình ứng dụng RAG hoàn chỉnh chủ yếu được chia thành hai khâu cốt lõi. Ở <strong>giai đoạn chuẩn bị dữ liệu</strong>, hệ thống thông qua <strong>trích xuất dữ liệu</strong>, <strong>phân tách văn bản</strong> và <strong>vector hóa</strong> để xây dựng tri thức bên ngoài thành một cơ sở dữ liệu có thể truy xuất. Sau đó ở <strong>giai đoạn ứng dụng</strong>, hệ thống phản hồi <strong>câu hỏi</strong> của người dùng, <strong>truy xuất</strong> thông tin liên quan từ cơ sở dữ liệu, <strong>đưa vào Prompt</strong>, và cuối cùng dẫn dắt mô hình ngôn ngữ lớn <strong>sinh câu trả lời</strong>.

(3) Quá trình phát triển

Giai đoạn thứ nhất: RAG ngây thơ (Naive RAG, 2020-2021). Đây là giai đoạn mầm mống của kỹ thuật RAG, quy trình trực tiếp và đơn giản, thường được gọi là mô hình "truy xuất - đọc" (Retrieve-Read). <strong>Cách truy xuất</strong>: chủ yếu dựa vào các thuật toán khớp từ khóa truyền thống như `TF-IDF` hoặc `BM25`. Những phương pháp này tính tần suất từ và tần suất tài liệu để đánh giá độ liên quan, hiệu quả tốt với khớp chữ nghĩa nhưng khó hiểu sự tương đồng về ngữ nghĩa. <strong>Cách sinh</strong>: ghép trực tiếp nội dung tài liệu đã truy xuất vào ngữ cảnh của prompt mà không xử lý gì thêm, rồi đưa cho mô hình sinh.

Giai đoạn thứ hai: RAG nâng cao (Advanced RAG, 2022-2023). Cùng với sự trưởng thành của cơ sở dữ liệu vector và kỹ thuật embedding văn bản, RAG bước vào giai đoạn phát triển nhanh. Các nhà nghiên cứu và nhà phát triển đã đưa vào một lượng lớn kỹ thuật tối ưu ở từng khâu của "truy xuất" và "sinh". <strong>Cách truy xuất</strong>: chuyển sang truy xuất ngữ nghĩa dựa trên <strong>embedding dày đặc (Dense Embedding)</strong>. Bằng cách chuyển văn bản thành vector nhiều chiều, mô hình có thể hiểu và khớp sự tương đồng về ngữ nghĩa, không chỉ là từ khóa. <strong>Cách sinh</strong>: đưa vào nhiều kỹ thuật tối ưu, ví dụ viết lại truy vấn, chia khối tài liệu, xếp hạng lại, v.v.

Giai đoạn thứ ba: RAG mô-đun hóa (Modular RAG, 2023 đến nay). Trên nền RAG nâng cao, các hệ thống RAG hiện đại tiếp tục phát triển theo hướng mô-đun hóa, tự động hóa và thông minh hóa. Các phần của hệ thống được thiết kế thành các mô-đun độc lập có thể cắm vào và kết hợp, để thích ứng với nhiều kịch bản ứng dụng đa dạng và phức tạp hơn. <strong>Cách truy xuất</strong>: như truy xuất kết hợp, mở rộng đa truy vấn, embedding tài liệu giả định, v.v. <strong>Cách sinh</strong>: suy luận chuỗi tư duy, tự phản tư và tự sửa lỗi, v.v.



### 8.3.2 Nguyên lý làm việc của hệ thống RAG

Trước khi đi sâu vào chi tiết hiện thực, có thể dùng lưu đồ để sắp xếp quy trình làm việc hoàn chỉnh của hệ thống RAG trong Helloagents:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-5.png" alt="Nguyên lý cốt lõi của hệ thống RAG" width="85%"/>
  <p>Hình 8.5 Nguyên lý làm việc cốt lõi của hệ thống RAG</p>
</div>

Như minh họa trong Hình 8.5, hai chế độ làm việc chính của hệ thống RAG được trình bày:
1. <strong>Quy trình xử lý dữ liệu</strong>: xử lý và lưu trữ tài liệu tri thức; ở đây chúng ta dùng công cụ `Markitdown` với tư tưởng thiết kế là chuyển mọi nguồn tri thức bên ngoài được truyền vào thành định dạng Markdown thống nhất để xử lý.
2. <strong>Quy trình truy vấn và sinh</strong>: truy xuất thông tin liên quan theo truy vấn và sinh câu trả lời.

### 8.3.3 Trải nghiệm nhanh: nắm bắt chức năng RAG trong 30 giây

Chúng ta hãy nhanh chóng trải nghiệm các chức năng cơ bản của hệ thống RAG:

```python
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import RAGTool

# Tạo thực thể LLM
llm = HelloAgentsLLM()

# Tạo công cụ RAG
rag_tool = RAGTool(
    knowledge_base_path="./knowledge_base",
    collection_name="test_collection",
    rag_namespace="test"
)

tool_registry = ToolRegistry()
tool_registry.register_tool(rag_tool)

# Tạo Agent có năng lực RAG
agent = SimpleAgent(name="Trợ lý tri thức", llm=llm, tool_registry=tool_registry)

# Trải nghiệm chức năng RAG
# Thêm tri thức thứ nhất
result1 = rag_tool.execute("add_text",
    text="Python là một ngôn ngữ lập trình bậc cao, được Guido van Rossum công bố lần đầu vào năm 1991. Triết lý thiết kế của Python nhấn mạnh tính dễ đọc và cú pháp súc tích của mã.",
    document_id="python_intro")
print(f"Tri thức 1: {result1}")

# Thêm tri thức thứ hai
result2 = rag_tool.execute("add_text",
    text="Học máy là một nhánh của trí tuệ nhân tạo, thông qua thuật toán cho phép máy tính học các mẫu từ dữ liệu. Chủ yếu gồm ba loại: học có giám sát, học không giám sát và học tăng cường.",
    document_id="ml_basics")
print(f"Tri thức 2: {result2}")

# Thêm tri thức thứ ba
result3 = rag_tool.execute("add_text",
    text="RAG (sinh tăng cường truy xuất) là một kỹ thuật AI kết hợp truy xuất thông tin và sinh văn bản. Nó tăng cường năng lực sinh của mô hình ngôn ngữ lớn bằng cách truy xuất tri thức liên quan.",
    document_id="rag_concept")
print(f"Tri thức 3: {result3}")


print("\n=== Tìm kiếm tri thức ===")
result = rag_tool.execute("search",
    query="lịch sử ngôn ngữ lập trình Python",
    limit=3,
    min_score=0.1
)
print(result)

print("\n=== Thống kê kho tri thức ===")
result = rag_tool.execute("stats")
print(result)
```

Tiếp theo, chúng ta sẽ đi sâu thảo luận hiện thực cụ thể của hệ thống RAG trong HelloAgents.

### 8.3.4 Thiết kế kiến trúc hệ thống RAG

Trong phần này, chúng ta trình bày theo cách khác với hệ thống bộ nhớ. Bởi vì `Memory_tool` là một hiện thực mang tính hệ thống, còn RAG trong thiết kế của chúng ta được định nghĩa là một loại công cụ, có thể sắp xếp thành một pipeline. Kiến trúc cốt lõi của hệ thống RAG có thể khái quát thành mẫu thiết kế "năm tầng bảy bước":

```
Tầng người dùng: giao diện thống nhất RAGTool
  ↓
Tầng ứng dụng: hỏi đáp thông minh, tìm kiếm, quản lý
  ↓
Tầng xử lý: phân tích tài liệu, chia khối, vector hóa
  ↓
Tầng lưu trữ: cơ sở dữ liệu vector, lưu trữ tài liệu
  ↓
Tầng nền tảng: mô hình embedding, LLM, cơ sở dữ liệu
```

Ưu điểm của thiết kế phân tầng này là mỗi tầng đều có thể được tối ưu và thay thế độc lập, đồng thời giữ ổn định toàn hệ thống. Ví dụ, có thể dễ dàng chuyển mô hình embedding từ sentence-transformers sang API Bailian mà không ảnh hưởng đến logic nghiệp vụ của tầng trên. Tương tự, mã của các quy trình xử lý này hoàn toàn có thể tái sử dụng, bạn cũng có thể chọn những phần mình cần đưa vào dự án của mình. RAGTool là cửa vào thống nhất của hệ thống RAG, cung cấp giao diện API súc tích.

````python
class RAGTool(Tool):
    """Công cụ RAG

    Cung cấp năng lực RAG đầy đủ:
    - Thêm tài liệu đa định dạng (PDF, Office, hình ảnh, âm thanh, v.v.)
    - Truy xuất và gợi nhớ thông minh
    - Hỏi đáp tăng cường bằng LLM
    - Quản lý kho tri thức
    """

    def __init__(
        self,
        knowledge_base_path: str = "./knowledge_base",
        qdrant_url: str = None,
        qdrant_api_key: str = None,
        collection_name: str = "rag_knowledge_base",
        rag_namespace: str = "default"
    ):
        # Khởi tạo đường ống RAG
        self._pipelines: Dict[str, Dict[str, Any]] = {}
        self.llm = HelloAgentsLLM()

        # Tạo đường ống mặc định
        default_pipeline = create_rag_pipeline(
            qdrant_url=self.qdrant_url,
            qdrant_api_key=self.qdrant_api_key,
            collection_name=self.collection_name,
            rag_namespace=self.rag_namespace
        )
        self._pipelines[self.rag_namespace] = default_pipeline
````
Toàn bộ quy trình xử lý như sau:
```
Tài liệu định dạng bất kỳ → Chuyển đổi MarkItDown → Văn bản Markdown → Chia khối thông minh → Vector hóa → Lưu trữ và truy xuất
```

(1) Nạp tài liệu đa phương thức

Một trong những ưu thế cốt lõi của hệ thống RAG là năng lực xử lý tài liệu đa phương thức mạnh mẽ. Hệ thống dùng MarkItDown làm công cụ chuyển đổi tài liệu thống nhất, hỗ trợ gần như mọi định dạng tài liệu phổ biến. MarkItDown là công cụ chuyển đổi tài liệu đa năng mã nguồn mở của Microsoft, là thành phần cốt lõi của hệ thống RAG HelloAgents, chịu trách nhiệm chuyển tài liệu định dạng bất kỳ thành văn bản Markdown có cấu trúc thống nhất. Dù đầu vào là PDF, Word, Excel, hình ảnh hay âm thanh, cuối cùng đều được chuyển thành định dạng Markdown chuẩn, rồi đi vào quy trình chia khối, vector hóa và lưu trữ thống nhất.

```python
def _convert_to_markdown(path: str) -> str:
    """
    Bộ đọc tài liệu đa năng dùng MarkItDown với xử lý PDF tăng cường.
    Chức năng cốt lõi: chuyển tài liệu định dạng bất kỳ thành văn bản Markdown

    Định dạng được hỗ trợ:
    - Tài liệu: PDF, Word, Excel, PowerPoint
    - Hình ảnh: JPG, PNG, GIF (qua OCR)
    - Âm thanh: MP3, WAV, M4A (qua chuyển thành văn bản)
    - Văn bản: TXT, CSV, JSON, XML, HTML
    - Mã: Python, JavaScript, Java, v.v.
    """
    if not os.path.exists(path):
        return ""

    # Dùng xử lý tăng cường cho tệp PDF
    ext = (os.path.splitext(path)[1] or '').lower()
    if ext == '.pdf':
        return _enhanced_pdf_processing(path)

    # Các định dạng khác dùng MarkItDown để chuyển đổi thống nhất
    md_instance = _get_markitdown_instance()
    if md_instance is None:
        return _fallback_text_reader(path)

    try:
        result = md_instance.convert(path)
        markdown_text = getattr(result, "text_content", None)
        if isinstance(markdown_text, str) and markdown_text.strip():
            print(f"[RAG] Chuyển đổi MarkItDown thành công: {path} -> {len(markdown_text)} chars Markdown")
            return markdown_text
        return ""
    except Exception as e:
        print(f"[WARNING] Chuyển đổi MarkItDown thất bại {path}: {e}")
        return _fallback_text_reader(path)
```

(2) Chiến lược chia khối thông minh

Sau khi qua MarkItDown chuyển đổi, mọi tài liệu đều thống nhất về định dạng Markdown chuẩn. Điều này tạo nền tảng có cấu trúc cho việc chia khối thông minh tiếp theo. HelloAgents hiện thực chiến lược chia khối thông minh dành riêng cho định dạng Markdown, tận dụng đầy đủ đặc tính cấu trúc của Markdown để phân tách chính xác.

Quy trình chia khối nhận thức cấu trúc Markdown:

```
Văn bản Markdown chuẩn → Phân tích cấp tiêu đề → Phân tách ngữ nghĩa đoạn → Tính token để chia khối → Tối ưu chiến lược chồng lấp → Chuẩn bị vector hóa
       ↓                      ↓                    ↓                  ↓                    ↓                    ↓
   Định dạng thống nhất   #/##/###          Ranh giới ngữ nghĩa  Kiểm soát kích thước  Liên tục thông tin   Vector embedding
   Cấu trúc rõ ràng      Nhận diện cấp     Đảm bảo đầy đủ      Tối ưu truy xuất      Giữ ngữ cảnh         Khớp độ tương đồng
```

Vì mọi tài liệu đã được chuyển sang định dạng Markdown, hệ thống có thể tận dụng cấu trúc tiêu đề của Markdown (#, ##, ###, v.v.) để phân tách ngữ nghĩa chính xác:

```python
def _split_paragraphs_with_headings(text: str) -> List[Dict]:
    """Chia đoạn theo cấp tiêu đề, giữ tính đầy đủ ngữ nghĩa"""
    lines = text.splitlines()
    heading_stack: List[str] = []
    paragraphs: List[Dict] = []
    buf: List[str] = []
    char_pos = 0

    def flush_buf(end_pos: int):
        if not buf:
            return
        content = "\n".join(buf).strip()
        if not content:
            return
        paragraphs.append({
            "content": content,
            "heading_path": " > ".join(heading_stack) if heading_stack else None,
            "start": max(0, end_pos - len(content)),
            "end": end_pos,
        })

    for ln in lines:
        raw = ln
        if raw.strip().startswith("#"):
            # Xử lý dòng tiêu đề
            flush_buf(char_pos)
            level = len(raw) - len(raw.lstrip('#'))
            title = raw.lstrip('#').strip()

            if level <= 0:
                level = 1
            if level <= len(heading_stack):
                heading_stack = heading_stack[:level-1]
            heading_stack.append(title)

            char_pos += len(raw) + 1
            continue

        # Tích lũy nội dung đoạn
        if raw.strip() == "":
            flush_buf(char_pos)
            buf = []
        else:
            buf.append(raw)
        char_pos += len(raw) + 1

    flush_buf(char_pos)

    if not paragraphs:
        paragraphs = [{"content": text, "heading_path": None, "start": 0, "end": len(text)}]

    return paragraphs
```

Trên cơ sở phân tách đoạn Markdown, hệ thống tiếp tục chia khối thông minh theo số lượng Token. Vì đầu vào đã là văn bản Markdown có cấu trúc, hệ thống có thể kiểm soát ranh giới khối chính xác hơn, đảm bảo mỗi khối vừa phù hợp cho xử lý vector hóa, vừa giữ tính đầy đủ của cấu trúc Markdown:

```python
def _chunk_paragraphs(paragraphs: List[Dict], chunk_tokens: int, overlap_tokens: int) -> List[Dict]:
    """Chia khối thông minh dựa trên số lượng Token"""
    chunks: List[Dict] = []
    cur: List[Dict] = []
    cur_tokens = 0
    i = 0

    while i < len(paragraphs):
        p = paragraphs[i]
        p_tokens = _approx_token_len(p["content"]) or 1

        if cur_tokens + p_tokens <= chunk_tokens or not cur:
            cur.append(p)
            cur_tokens += p_tokens
            i += 1
        else:
            # Sinh khối hiện tại
            content = "\n\n".join(x["content"] for x in cur)
            start = cur[0]["start"]
            end = cur[-1]["end"]
            heading_path = next((x["heading_path"] for x in reversed(cur) if x.get("heading_path")), None)

            chunks.append({
                "content": content,
                "start": start,
                "end": end,
                "heading_path": heading_path,
            })

            # Xây dựng phần chồng lấp
            if overlap_tokens > 0 and cur:
                kept: List[Dict] = []
                kept_tokens = 0
                for x in reversed(cur):
                    t = _approx_token_len(x["content"]) or 1
                    if kept_tokens + t > overlap_tokens:
                        break
                    kept.append(x)
                    kept_tokens += t
                cur = list(reversed(kept))
                cur_tokens = kept_tokens
            else:
                cur = []
                cur_tokens = 0

    # Xử lý khối cuối cùng
    if cur:
        content = "\n\n".join(x["content"] for x in cur)
        start = cur[0]["start"]
        end = cur[-1]["end"]
        heading_path = next((x["heading_path"] for x in reversed(cur) if x.get("heading_path")), None)

        chunks.append({
            "content": content,
            "start": start,
            "end": end,
            "heading_path": heading_path,
        })

    return chunks
```

Đồng thời, để tương thích với các ngôn ngữ khác nhau, hệ thống hiện thực thuật toán ước lượng Token cho văn bản hỗn hợp Trung-Anh; điều này rất quan trọng để kiểm soát chính xác kích thước khối:

```python
def _approx_token_len(text: str) -> int:
    """Ước lượng gần đúng độ dài Token, hỗ trợ hỗn hợp Trung-Anh"""
    # Ký tự CJK tính 1 token
    cjk = sum(1 for ch in text if _is_cjk(ch))
    # Các ký tự khác tính theo tách từ bằng khoảng trắng
    non_cjk_tokens = len([t for t in text.split() if t])
    return cjk + non_cjk_tokens

def _is_cjk(ch: str) -> bool:
    """Kiểm tra có phải ký tự CJK hay không"""
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF or  # CJK thống nhất Hán tự
        0x3400 <= code <= 0x4DBF or  # CJK mở rộng A
        0x20000 <= code <= 0x2A6DF or # CJK mở rộng B
        0x2A700 <= code <= 0x2B73F or # CJK mở rộng C
        0x2B740 <= code <= 0x2B81F or # CJK mở rộng D
        0x2B820 <= code <= 0x2CEAF or # CJK mở rộng E
        0xF900 <= code <= 0xFAFF      # CJK Hán tự tương thích
    )
```

(3) Embedding thống nhất và lưu trữ vector

Mô hình embedding là hạt nhân của hệ thống RAG, chịu trách nhiệm chuyển văn bản thành vector nhiều chiều, giúp máy tính có thể hiểu và so sánh độ tương đồng ngữ nghĩa của văn bản. Năng lực truy xuất của hệ thống RAG phụ thuộc rất lớn vào chất lượng mô hình embedding và hiệu quả lưu trữ vector. HelloAgents hiện thực giao diện embedding thống nhất. Ở đây để minh họa, chúng ta dùng API Bailian; nếu chưa cấu hình có thể chuyển sang mô hình cục bộ `all-MiniLM-L6-v2`; nếu cả hai phương án đều không được hỗ trợ, cũng đã cấu hình thuật toán TF-IDF để dự phòng. Khi dùng thực tế, bạn có thể thay bằng mô hình hoặc API mình muốn, cũng có thể thử mở rộng nội dung framework~

```python
def index_chunks(
    store = None,
    chunks: List[Dict] = None,
    cache_db: Optional[str] = None,
    batch_size: int = 64,
    rag_namespace: str = "default"
) -> None:
    """
    Đánh chỉ mục các khối markdown bằng embedding thống nhất và lưu trữ Qdrant.
    Dùng API Bailian, dự phòng bằng sentence-transformers.
    """
    if not chunks:
        print("[RAG] No chunks to index")
        return

    # Dùng mô hình embedding thống nhất
    embedder = get_text_embedder()
    dimension = get_dimension(384)

    # Tạo lưu trữ Qdrant mặc định
    if store is None:
        store = _create_default_vector_store(dimension)
        print(f"[RAG] Created default Qdrant store with dimension {dimension}")

    # Tiền xử lý văn bản Markdown để có chất lượng embedding tốt hơn
    processed_texts = []
    for c in chunks:
        raw_content = c["content"]
        processed_content = _preprocess_markdown_for_embedding(raw_content)
        processed_texts.append(processed_content)

    print(f"[RAG] Embedding start: total_texts={len(processed_texts)} batch_size={batch_size}")

    # Mã hóa theo lô
    vecs: List[List[float]] = []
    for i in range(0, len(processed_texts), batch_size):
        part = processed_texts[i:i+batch_size]
        try:
            # Dùng bộ embedding thống nhất (tự xử lý bộ đệm bên trong)
            part_vecs = embedder.encode(part)

            # Chuẩn hóa về định dạng List[List[float]]
            if not isinstance(part_vecs, list):
                if hasattr(part_vecs, "tolist"):
                    part_vecs = [part_vecs.tolist()]
                else:
                    part_vecs = [list(part_vecs)]

            # Xử lý định dạng và số chiều vector
            for v in part_vecs:
                try:
                    if hasattr(v, "tolist"):
                        v = v.tolist()
                    v_norm = [float(x) for x in v]

                    # Kiểm tra và điều chỉnh số chiều
                    if len(v_norm) != dimension:
                        print(f"[WARNING] Số chiều vector bất thường: mong đợi {dimension}, thực tế {len(v_norm)}")
                        if len(v_norm) < dimension:
                            v_norm.extend([0.0] * (dimension - len(v_norm)))
                        else:
                            v_norm = v_norm[:dimension]

                    vecs.append(v_norm)
                except Exception as e:
                    print(f"[WARNING] Chuyển đổi vector thất bại: {e}, dùng vector không")
                    vecs.append([0.0] * dimension)

        except Exception as e:
            print(f"[WARNING] Batch {i} encoding failed: {e}")
            # Hiện thực cơ chế thử lại
            # ... logic thử lại ...

        print(f"[RAG] Embedding progress: {min(i+batch_size, len(processed_texts))}/{len(processed_texts)}")
```

### 8.3.5 Chiến lược truy xuất nâng cao

Năng lực truy xuất của hệ thống RAG là năng lực cạnh tranh cốt lõi của nó. Trong ứng dụng thực tế, cách diễn đạt truy vấn của người dùng và nội dung thực tế trong tài liệu có thể có khác biệt về từ ngữ, khiến tài liệu liên quan không được truy xuất. Để giải quyết vấn đề này, HelloAgents hiện thực ba chiến lược truy xuất nâng cao bổ sung lẫn nhau: mở rộng đa truy vấn (MQE), embedding tài liệu giả định (HyDE) và khung truy xuất mở rộng thống nhất.

(1) Mở rộng đa truy vấn (MQE)

Mở rộng đa truy vấn (Multi-Query Expansion) là một kỹ thuật nâng cao độ gợi nhớ truy xuất bằng cách sinh các truy vấn đa dạng tương đương ngữ nghĩa. Nhận định cốt lõi của phương pháp này là: cùng một câu hỏi có thể có nhiều cách diễn đạt khác nhau, và các cách diễn đạt khác nhau có thể khớp với các tài liệu liên quan khác nhau. Ví dụ, "làm sao để học Python" có thể được mở rộng thành nhiều truy vấn như "hướng dẫn nhập môn Python", "phương pháp học Python", "cẩm nang lập trình Python". Bằng cách thực thi song song các truy vấn mở rộng này và hợp nhất kết quả, hệ thống có thể bao phủ tài liệu liên quan rộng hơn, tránh bỏ sót thông tin quan trọng do khác biệt từ ngữ.

Ưu thế của MQE nằm ở chỗ nó có thể tự động hiểu nhiều ý nghĩa khả dĩ của truy vấn người dùng, đặc biệt hiệu quả với truy vấn mơ hồ hoặc truy vấn thuật ngữ chuyên ngành. Hệ thống dùng LLM sinh truy vấn mở rộng, đảm bảo tính đa dạng và liên quan ngữ nghĩa của phần mở rộng:

```python
def _prompt_mqe(query: str, n: int) -> List[str]:
    """Dùng LLM sinh các truy vấn mở rộng đa dạng"""
    try:
        from ...core.llm import HelloAgentsLLM
        llm = HelloAgentsLLM()
        prompt = [
            {"role": "system", "content": "Bạn là trợ lý mở rộng truy vấn tìm kiếm. Hãy sinh các truy vấn đa dạng tương đương hoặc bổ sung về ngữ nghĩa. Dùng tiếng Trung, ngắn gọn, tránh dấu câu."},
            {"role": "user", "content": f"Truy vấn gốc: {query}\nHãy đưa ra {n} truy vấn với cách diễn đạt khác nhau, mỗi dòng một truy vấn."}
        ]
        text = llm.invoke(prompt)
        lines = [ln.strip("- \t") for ln in (text or "").splitlines()]
        outs = [ln for ln in lines if ln]
        return outs[:n] or [query]
    except Exception:
        return [query]
```

(2) Embedding tài liệu giả định (HyDE)

Embedding tài liệu giả định (Hypothetical Document Embeddings, HyDE) là một kỹ thuật truy xuất đổi mới; tư tưởng cốt lõi của nó là "dùng câu trả lời để tìm câu trả lời". Phương pháp truy xuất truyền thống dùng câu hỏi để khớp tài liệu, nhưng phân bố của câu hỏi và câu trả lời trong không gian ngữ nghĩa thường có khác biệt — câu hỏi thường là câu nghi vấn, còn nội dung tài liệu là câu trần thuật. HyDE cho LLM trước tiên sinh một đoạn trả lời giả định, rồi dùng đoạn trả lời này để truy xuất tài liệu thật, từ đó thu hẹp khoảng cách ngữ nghĩa giữa truy vấn và tài liệu.

Ưu thế của phương pháp này nằm ở chỗ câu trả lời giả định gần với câu trả lời thật hơn trong không gian ngữ nghĩa, do đó có thể khớp tài liệu liên quan chính xác hơn. Kể cả khi nội dung câu trả lời giả định không hoàn toàn đúng, các thuật ngữ then chốt, khái niệm và phong cách diễn đạt mà nó chứa cũng có thể dẫn dắt hiệu quả hệ thống truy xuất tìm đến tài liệu đúng. Đặc biệt với truy vấn trong lĩnh vực chuyên ngành, HyDE có thể sinh tài liệu giả định chứa thuật ngữ chuyên ngành, nâng cao rõ rệt độ chính xác truy xuất:

```python
def _prompt_hyde(query: str) -> Optional[str]:
    """Sinh tài liệu giả định để cải thiện truy xuất"""
    try:
        from ...core.llm import HelloAgentsLLM
        llm = HelloAgentsLLM()
        prompt = [
            {"role": "system", "content": "Dựa trên câu hỏi của người dùng, trước tiên viết một đoạn có thể là câu trả lời, dùng làm tài liệu truy vấn cho truy xuất vector (không phân tích quá trình)."},
            {"role": "user", "content": f"Câu hỏi: {query}\nHãy viết trực tiếp một đoạn có độ dài trung bình, khách quan, chứa các thuật ngữ then chốt."}
        ]
        return llm.invoke(prompt)
    except Exception:
        return None
```

(3) Khung truy xuất mở rộng

HelloAgents tích hợp hai chiến lược MQE và HyDE vào một khung truy xuất mở rộng thống nhất. Hệ thống thông qua hai tham số `enable_mqe` và `enable_hyde` cho phép người dùng chọn bật những chiến lược nào theo kịch bản cụ thể: với kịch bản cần độ gợi nhớ cao có thể bật đồng thời cả hai chiến lược, với kịch bản nhạy cảm về hiệu năng có thể chỉ dùng truy xuất cơ bản.

Cơ chế cốt lõi của truy xuất mở rộng là quy trình ba bước "mở rộng - truy xuất - hợp nhất". Đầu tiên, hệ thống sinh nhiều truy vấn mở rộng theo truy vấn gốc (bao gồm các truy vấn đa dạng do MQE sinh và tài liệu giả định do HyDE sinh); sau đó, với mỗi truy vấn mở rộng, thực thi song song truy xuất vector để thu được pool tài liệu ứng viên; cuối cùng, hợp nhất mọi kết quả thông qua khử trùng lặp và sắp xếp theo điểm, trả về top-k tài liệu liên quan nhất. Điểm khéo léo của thiết kế này là nó mở rộng pool ứng viên thông qua tham số `candidate_pool_multiplier` (mặc định là 4), đảm bảo có đủ tài liệu ứng viên để sàng lọc, đồng thời tránh trả về nội dung trùng lặp nhờ khử trùng lặp thông minh.

```python
def search_vectors_expanded(
    store = None,
    query: str = "",
    top_k: int = 8,
    rag_namespace: Optional[str] = None,
    only_rag_data: bool = True,
    score_threshold: Optional[float] = None,
    enable_mqe: bool = False,
    mqe_expansions: int = 2,
    enable_hyde: bool = False,
    candidate_pool_multiplier: int = 4,
) -> List[Dict]:
    """
    Tìm kiếm có mở rộng truy vấn dùng embedding thống nhất và Qdrant.
    """
    if not query:
        return []

    # Tạo lưu trữ mặc định
    if store is None:
        store = _create_default_vector_store()

    # Mở rộng truy vấn
    expansions: List[str] = [query]

    if enable_mqe and mqe_expansions > 0:
        expansions.extend(_prompt_mqe(query, mqe_expansions))
    if enable_hyde:
        hyde_text = _prompt_hyde(query)
        if hyde_text:
            expansions.append(hyde_text)

    # Khử trùng lặp và cắt tỉa
    uniq: List[str] = []
    for e in expansions:
        if e and e not in uniq:
            uniq.append(e)
    expansions = uniq[: max(1, len(uniq))]

    # Phân bổ pool ứng viên
    pool = max(top_k * candidate_pool_multiplier, 20)
    per = max(1, pool // max(1, len(expansions)))

    # Xây dựng bộ lọc dữ liệu RAG
    where = {"memory_type": "rag_chunk"}
    if only_rag_data:
        where["is_rag_data"] = True
        where["data_source"] = "rag_pipeline"
    if rag_namespace:
        where["rag_namespace"] = rag_namespace

    # Thu thập kết quả của mọi truy vấn mở rộng
    agg: Dict[str, Dict] = {}
    for q in expansions:
        qv = embed_query(q)
        hits = store.search_similar(
            query_vector=qv,
            limit=per,
            score_threshold=score_threshold,
            where=where
        )
        for h in hits:
            mid = h.get("metadata", {}).get("memory_id", h.get("id"))
            s = float(h.get("score", 0.0))
            if mid not in agg or s > float(agg[mid].get("score", 0.0)):
                agg[mid] = h

    # Sắp xếp theo điểm và trả về
    merged = list(agg.values())
    merged.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    return merged[:top_k]
```

Trong ứng dụng thực tế, việc kết hợp ba chiến lược này cho hiệu quả tốt nhất. MQE giỏi xử lý vấn đề đa dạng từ ngữ, HyDE giỏi xử lý vấn đề khoảng cách ngữ nghĩa, còn khung thống nhất đảm bảo chất lượng và tính đa dạng của kết quả. Với truy vấn thông thường, khuyến nghị bật MQE; với truy vấn chuyên ngành, khuyến nghị bật đồng thời MQE và HyDE; với kịch bản nhạy cảm về hiệu năng, có thể chỉ dùng truy xuất cơ bản hoặc chỉ bật MQE.

Tất nhiên còn rất nhiều phương pháp thú vị khác; ở đây chỉ giới thiệu mở rộng phù hợp cho bạn đọc, trong kịch bản sử dụng thực tế cũng cần thử tìm giải pháp phù hợp với vấn đề.



## 8.4 Xây dựng trợ lý hỏi đáp tài liệu thông minh

Ở các phần trước, chúng ta đã giới thiệu chi tiết thiết kế và hiện thực hệ thống bộ nhớ và hệ thống RAG của HelloAgents. Bây giờ, hãy cùng thông qua một ca thực chiến hoàn chỉnh để trình bày cách kết hợp hữu cơ hai hệ thống này, xây dựng một trợ lý hỏi đáp tài liệu thông minh.

### 8.4.1 Bối cảnh và mục tiêu của ca

Trong công việc thực tế, chúng ta thường xuyên phải xử lý lượng lớn tệp PDF như tài liệu kỹ thuật, bài báo nghiên cứu, sổ tay sản phẩm. Cách đọc tài liệu truyền thống hiệu quả thấp, khó nhanh chóng định vị thông tin then chốt, càng không thể thiết lập liên kết giữa các tri thức.

Ca này sẽ lấy tài liệu PDF công khai `Happy-LLM-0727.pdf` của một khóa học thực hành mô hình lớn khác của Datawhale là Happy-LLM làm ví dụ, xây dựng một <strong>ứng dụng Web dựa trên Gradio</strong>, trình bày cách dùng RAGTool và MemoryTool để xây dựng một trợ lý học tập tương tác hoàn chỉnh. PDF có thể tải tại [liên kết](https://github.com/datawhalechina/happy-llm/releases/download/v1.0.1/Happy-LLM-0727.pdf) này.

Chúng ta mong muốn hiện thực các chức năng sau:

1. <strong>Xử lý tài liệu thông minh</strong>: dùng MarkItDown để chuyển đổi thống nhất PDF sang Markdown, chiến lược chia khối thông minh dựa trên cấu trúc Markdown, vector hóa và xây dựng chỉ mục hiệu quả

2. <strong>Hỏi đáp truy xuất nâng cao</strong>: mở rộng đa truy vấn (MQE) nâng cao độ gợi nhớ, embedding tài liệu giả định (HyDE) cải thiện độ chính xác truy xuất, hỏi đáp thông minh nhận biết ngữ cảnh

3. <strong>Quản lý bộ nhớ nhiều tầng</strong>: bộ nhớ làm việc quản lý nhiệm vụ học tập và ngữ cảnh hiện tại, bộ nhớ tình huống ghi lại sự kiện học tập và lịch sử truy vấn, bộ nhớ ngữ nghĩa lưu trữ tri thức khái niệm và sự hiểu biết, bộ nhớ tri giác xử lý đặc trưng tài liệu và thông tin đa phương thức

4. <strong>Hỗ trợ học tập cá nhân hóa</strong>: khuyến nghị cá nhân hóa dựa trên lịch sử học tập, tích hợp và quên có chọn lọc bộ nhớ, sinh báo cáo học tập và theo dõi tiến độ

Để trình bày rõ hơn quy trình làm việc của toàn hệ thống, Hình 8.6 minh họa quan hệ giữa năm bước và dòng chảy dữ liệu. Năm bước tạo thành một vòng khép kín hoàn chỉnh: bước 1 ghi thông tin sau khi xử lý tài liệu PDF vào hệ thống bộ nhớ, kết quả truy xuất của bước 2 cũng được ghi vào hệ thống bộ nhớ, bước 3 trình bày đầy đủ chức năng của hệ thống bộ nhớ (thêm, truy xuất, tích hợp, quên), bước 4 tích hợp RAG và Memory để cung cấp định tuyến thông minh, bước 5 thu thập mọi thông tin thống kê để sinh báo cáo học tập.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-6.png" alt="" width="85%"/>
  <p>Hình 8.6 Quy trình thực thi năm bước của trợ lý hỏi đáp thông minh</p>
</div>

Tiếp theo, chúng ta sẽ trình bày cách hiện thực ứng dụng Web này. Toàn bộ ứng dụng được chia thành ba phần cốt lõi:

1. <strong>Lớp trợ lý cốt lõi (PDFLearningAssistant)</strong>: đóng gói logic gọi RAGTool và MemoryTool
2. <strong>Giao diện Web Gradio</strong>: cung cấp giao diện tương tác thân thiện với người dùng; phần này có thể tham khảo mã ví dụ để học
3. <strong>Các chức năng cốt lõi khác</strong>: ghi chú, ôn tập học tập, xem thống kê và sinh báo cáo

### 8.4.2 Hiện thực lớp trợ lý cốt lõi

Đầu tiên, chúng ta hiện thực lớp trợ lý cốt lõi `PDFLearningAssistant`, lớp này đóng gói logic gọi RAGTool và MemoryTool.

(1) Khởi tạo lớp

```python
class PDFLearningAssistant:
    """Trợ lý hỏi đáp tài liệu thông minh"""

    def __init__(self, user_id: str = "default_user"):
        """Khởi tạo trợ lý học tập

        Args:
            user_id: ID người dùng, dùng để cách ly dữ liệu của các người dùng khác nhau
        """
        self.user_id = user_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Khởi tạo công cụ
        self.memory_tool = MemoryTool(user_id=user_id)
        self.rag_tool = RAGTool(rag_namespace=f"pdf_{user_id}")

        # Thống kê học tập
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "concepts_learned": 0
        }

        # Tài liệu hiện đang được nạp
        self.current_document = None
```

Trong quá trình khởi tạo này, chúng ta đưa ra một số quyết định thiết kế then chốt:

<strong>Khởi tạo MemoryTool</strong>: thông qua tham số `user_id` để cách ly bộ nhớ ở cấp người dùng. Bộ nhớ học tập của các người dùng khác nhau hoàn toàn độc lập; mỗi người dùng có không gian bộ nhớ làm việc, bộ nhớ tình huống, bộ nhớ ngữ nghĩa và bộ nhớ tri giác riêng.

<strong>Khởi tạo RAGTool</strong>: thông qua tham số `rag_namespace` để cách ly không gian tên của kho tri thức. Dùng `f"pdf_{user_id}"` làm không gian tên, mỗi người dùng có kho tri thức PDF độc lập riêng.

<strong>Quản lý phiên</strong>: `session_id` dùng để theo dõi toàn bộ quá trình của một phiên học tập, thuận tiện cho việc ôn tập và phân tích hành trình học tập về sau.

<strong>Thông tin thống kê</strong>: từ điển `stats` ghi lại các chỉ số học tập then chốt, dùng để sinh báo cáo học tập.

(2) Nạp tài liệu PDF

```python
def load_document(self, pdf_path: str) -> Dict[str, Any]:
    """Nạp tài liệu PDF vào kho tri thức

    Args:
        pdf_path: Đường dẫn tệp PDF

    Returns:
        Dict: Kết quả chứa success và message
    """
    if not os.path.exists(pdf_path):
        return {"success": False, "message": f"Tệp không tồn tại: {pdf_path}"}

    start_time = time.time()

    # [RAGTool]Xử lý PDF: chuyển đổi MarkItDown → chia khối thông minh → vector hóa
    result = self.rag_tool.execute(
        "add_document",
        file_path=pdf_path,
        chunk_size=1000,
        chunk_overlap=200
    )

    process_time = time.time() - start_time

    if result.get("success", False):
        self.current_document = os.path.basename(pdf_path)
        self.stats["documents_loaded"] += 1

        # [MemoryTool]Ghi vào bộ nhớ học tập
        self.memory_tool.execute(
            "add",
            content=f"Đã nạp tài liệu \"{self.current_document}\"",
            memory_type="episodic",
            importance=0.9,
            event_type="document_loaded",
            session_id=self.session_id
        )

        return {
            "success": True,
            "message": f"Nạp thành công! (thời gian: {process_time:.1f} giây)",
            "document": self.current_document
        }
    else:
        return {
            "success": False,
            "message": f"Nạp thất bại: {result.get('error', 'lỗi không xác định')}"
        }
```

Chúng ta có thể hoàn thành xử lý PDF chỉ với một dòng mã:

```python
result = self.rag_tool.execute(
    "add_document",
    file_path=pdf_path,
    chunk_size=1000,
    chunk_overlap=200
)
```

Lời gọi này sẽ kích hoạt quy trình xử lý đầy đủ của RAGTool (chuyển đổi MarkItDown, xử lý tăng cường, chia khối thông minh, lưu trữ vector); những chi tiết bên trong này đã được giới thiệu chi tiết ở mục 8.3. Chúng ta chỉ cần quan tâm:

- <strong>Loại thao tác</strong>: `"add_document"` - thêm tài liệu vào kho tri thức
- <strong>Đường dẫn tệp</strong>: `file_path` - đường dẫn của tệp PDF
- <strong>Tham số chia khối</strong>: `chunk_size=1000, chunk_overlap=200` - kiểm soát việc chia khối văn bản
- <strong>Kết quả trả về</strong>: từ điển chứa trạng thái xử lý và thông tin thống kê

Sau khi nạp tài liệu thành công, chúng ta dùng MemoryTool ghi vào bộ nhớ tình huống:

```python
self.memory_tool.execute(
    "add",
    content=f"Đã nạp tài liệu \"{self.current_document}\"",
    memory_type="episodic",
    importance=0.9,
    event_type="document_loaded",
    session_id=self.session_id
)
```

<strong>Vì sao dùng bộ nhớ tình huống?</strong> Vì đây là một sự kiện cụ thể, có dấu thời gian, phù hợp để ghi bằng bộ nhớ tình huống. Tham số `session_id` liên kết sự kiện này với phiên học tập hiện tại, thuận tiện cho việc ôn lại hành trình học tập về sau.

Bản ghi bộ nhớ này đặt nền tảng cho các dịch vụ cá nhân hóa về sau:

- Người dùng hỏi "Trước đây tôi đã nạp những tài liệu nào?" → truy xuất từ bộ nhớ tình huống
- Hệ thống có thể theo dõi hành trình học tập và tình hình sử dụng tài liệu của người dùng

### 8.4.3 Chức năng hỏi đáp thông minh

Sau khi tài liệu được nạp xong, người dùng có thể đặt câu hỏi cho tài liệu. Chúng ta hiện thực phương thức `ask` để xử lý câu hỏi của người dùng:

```python
def ask(self, question: str, use_advanced_search: bool = True) -> str:
    """Đặt câu hỏi cho tài liệu

    Args:
        question: Câu hỏi của người dùng
        use_advanced_search: Có dùng truy xuất nâng cao (MQE + HyDE) hay không

    Returns:
        str: Câu trả lời
    """
    if not self.current_document:
        return "⚠️ Vui lòng nạp tài liệu trước!"

    # [MemoryTool]Ghi câu hỏi vào bộ nhớ làm việc
    self.memory_tool.execute(
        "add",
        content=f"Đặt câu hỏi: {question}",
        memory_type="working",
        importance=0.6,
        session_id=self.session_id
    )

    # [RAGTool]Dùng truy xuất nâng cao để lấy câu trả lời
    answer = self.rag_tool.execute(
        "ask",
        question=question,
        limit=5,
        enable_advanced_search=use_advanced_search,
        enable_mqe=use_advanced_search,
        enable_hyde=use_advanced_search
    )

    # [MemoryTool]Ghi vào bộ nhớ tình huống
    self.memory_tool.execute(
        "add",
        content=f"Học tập về '{question}'",
        memory_type="episodic",
        importance=0.7,
        event_type="qa_interaction",
        session_id=self.session_id
    )

    self.stats["questions_asked"] += 1

    return answer
```

Khi chúng ta gọi `self.rag_tool.execute("ask", ...)`, bên trong RAGTool thực thi quy trình truy xuất nâng cao sau:

1. <strong>Mở rộng đa truy vấn (MQE)</strong>:

   ```python
   # Sinh các truy vấn đa dạng
   expanded_queries = self._generate_multi_queries(question)
   # Ví dụ, với "Mô hình ngôn ngữ lớn là gì?", có thể sinh:
   # - "Định nghĩa của mô hình ngôn ngữ lớn là gì?"
   # - "Hãy giải thích về mô hình ngôn ngữ lớn"
   # - "LLM có nghĩa là gì?"
   ```

   MQE thông qua LLM sinh các truy vấn tương đương ngữ nghĩa nhưng khác cách diễn đạt, hiểu ý định người dùng từ nhiều góc độ, nâng cao độ gợi nhớ 30%-50%.

2. <strong>Embedding tài liệu giả định (HyDE)</strong>:

   - Sinh tài liệu câu trả lời giả định, bắc cầu khoảng cách ngữ nghĩa giữa truy vấn và tài liệu
   - Dùng vector của câu trả lời giả định để truy xuất

Hiện thực bên trong của các kỹ thuật truy xuất nâng cao này đã được giới thiệu chi tiết ở mục 8.3.5.

### 8.4.4 Các chức năng cốt lõi khác

Ngoài việc nạp tài liệu và hỏi đáp thông minh, chúng ta còn cần hiện thực các chức năng ghi chú, ôn tập học tập, xem thống kê và sinh báo cáo:

```python
def add_note(self, content: str, concept: Optional[str] = None):
    """Thêm ghi chú học tập"""
    self.memory_tool.execute(
        "add",
        content=content,
        memory_type="semantic",
        importance=0.8,
        concept=concept or "general",
        session_id=self.session_id
    )
    self.stats["concepts_learned"] += 1

def recall(self, query: str, limit: int = 5) -> str:
    """Ôn lại hành trình học tập"""
    result = self.memory_tool.execute(
        "search",
        query=query,
        limit=limit
    )
    return result

def get_stats(self) -> Dict[str, Any]:
    """Lấy thống kê học tập"""
    duration = (datetime.now() - self.stats["session_start"]).total_seconds()
    return {
        "Thời lượng phiên": f"{duration:.0f} giây",
        "Tài liệu đã nạp": self.stats["documents_loaded"],
        "Số lần đặt câu hỏi": self.stats["questions_asked"],
        "Ghi chú học tập": self.stats["concepts_learned"],
        "Tài liệu hiện tại": self.current_document or "Chưa nạp"
    }

def generate_report(self, save_to_file: bool = True) -> Dict[str, Any]:
    """Sinh báo cáo học tập"""
    memory_summary = self.memory_tool.execute("summary", limit=10)
    rag_stats = self.rag_tool.execute("stats")

    duration = (datetime.now() - self.stats["session_start"]).total_seconds()
    report = {
        "session_info": {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.stats["session_start"].isoformat(),
            "duration_seconds": duration
        },
        "learning_metrics": {
            "documents_loaded": self.stats["documents_loaded"],
            "questions_asked": self.stats["questions_asked"],
            "concepts_learned": self.stats["concepts_learned"]
        },
        "memory_summary": memory_summary,
        "rag_status": rag_stats
    }

    if save_to_file:
        report_file = f"learning_report_{self.session_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        report["report_file"] = report_file

    return report
```

Các phương thức này lần lượt hiện thực:

- <strong>add_note</strong>: lưu ghi chú học tập vào bộ nhớ ngữ nghĩa
- <strong>recall</strong>: truy xuất hành trình học tập từ hệ thống bộ nhớ
- <strong>get_stats</strong>: lấy thông tin thống kê của phiên hiện tại
- <strong>generate_report</strong>: sinh báo cáo học tập chi tiết và lưu thành tệp JSON

### 8.4.5 Trình diễn hiệu quả chạy

Tiếp theo là phần trình diễn hiệu quả chạy; như minh họa trong Hình 8.7, sau khi vào trang chính cần khởi tạo trợ lý trước, tức là thực hiện các thao tác nạp cơ sở dữ liệu, mô hình, API, v.v. Sau đó truyền vào tài liệu PDF và nhấn nạp tài liệu.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-7.png" alt="" width="85%"/>
  <p>Hình 8.7 Trang chính của trợ lý hỏi đáp</p>
</div>

Chức năng đầu tiên là hỏi đáp thông minh, có thể truy xuất dựa trên tài liệu đã tải lên, và trả về nguồn tham khảo cùng tính toán độ tương đồng của tài liệu liên quan; đây là biểu hiện năng lực của RAG tool, như minh họa trong Hình 8.8.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-8.png" alt="" width="85%"/>
  <p>Hình 8.8 Trang chính của trợ lý hỏi đáp</p>
</div>

Chức năng thứ hai là ghi chú học tập, như minh họa trong Hình 8.9, có thể đánh dấu các khái niệm liên quan và viết nội dung ghi chú; phần này sử dụng Memory tool, sẽ lưu ghi chú cá nhân của bạn trong cơ sở dữ liệu, thuận tiện cho việc thống kê và trả về báo cáo học tập tổng thể về sau.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-9.png" alt="" width="85%"/>
  <p>Hình 8.9 Trang chính của trợ lý hỏi đáp</p>
</div>

Cuối cùng là thống kê tiến độ học tập và sinh báo cáo, như minh họa trong Hình 8.10, chúng ta có thể thấy số lượng tài liệu đã nạp, số lần đặt câu hỏi và số lượng ghi chú trong thời gian sử dụng trợ lý; cuối cùng hệ thống sắp xếp kết quả hỏi đáp và ghi chú của chúng ta thành một tài liệu JSON và trả về.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-10.png" alt="" width="85%"/>
  <p>Hình 8.10 Trang chính của trợ lý hỏi đáp</p>
</div>

Thông qua ca trợ lý hỏi đáp này, chúng ta đã trình bày cách dùng RAGTool và MemoryTool để xây dựng một <strong>hệ thống hỏi đáp tài liệu thông minh dựa trên Web</strong> hoàn chỉnh. Mã đầy đủ có thể tìm thấy trong `code/chapter8/11_Q&A_Assistant.py`. Sau khi khởi động, truy cập `http://localhost:7860` là có thể sử dụng trợ lý học tập thông minh này.

Khuyến nghị bạn đọc tự chạy ca này, trải nghiệm năng lực của RAG và Memory, rồi mở rộng và tùy biến trên cơ sở đó để xây dựng ứng dụng thông minh phù hợp với nhu cầu của mình!

## 8.5 Tóm tắt chương và triển vọng

Trong chương này, chúng ta đã bổ sung thành công hai năng lực cốt lõi cho framework HelloAgents: hệ thống bộ nhớ và hệ thống RAG.

Với những bạn đọc mong muốn học sâu và ứng dụng nội dung chương này, chúng ta đưa ra các khuyến nghị sau:

1. Từ con số không, tự tay thiết kế một mô-đun bộ nhớ cơ bản, rồi lặp dần, bổ sung cho nó những đặc tính phức tạp hơn.

2. Thử nghiệm và đánh giá các mô hình embedding và chiến lược truy xuất khác nhau trong dự án, tìm giải pháp tối ưu cho nhiệm vụ cụ thể.

3. Áp dụng hệ thống bộ nhớ và RAG đã học vào một dự án cá nhân thực tế, kiểm chứng và nâng cao năng lực trong thực chiến.

Khám phá nâng cao

1. Theo dõi và nghiên cứu các kho memory, rag tiên tiến, học hỏi những hiện thực xuất sắc.
2. Khám phá khả năng áp dụng kiến trúc RAG vào kịch bản đa phương thức (văn bản + hình ảnh) hoặc xuyên phương thức.
3. Tham gia dự án mã nguồn mở HelloAgents, đóng góp ý tưởng và mã của bạn

Qua việc học chương này, bạn không chỉ nắm được kỹ thuật hiện thực hệ thống Memory và RAG, mà quan trọng hơn là hiểu cách chuyển hóa lý thuyết khoa học nhận thức thành giải pháp kỹ thuật thực tế. Cách tư duy liên ngành này sẽ đặt nền tảng vững chắc cho sự phát triển tiếp theo của bạn trong lĩnh vực AI.

Cuối cùng, hãy cùng tóm tắt hệ thống tri thức hoàn chỉnh của chương này bằng một sơ đồ tư duy, như minh họa trong Hình 8.11:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/8-figures/8-11.png" alt="" width="85%"/>
  <p>Hình 8.11 Tóm tắt tri thức chương 8 của Hello-agents</p>
</div>

Chương này đã trình bày năng lực của hệ thống bộ nhớ và kỹ thuật RAG trong framework HelloAgents; chúng ta đã xây dựng thành công một trợ lý học tập có "trí tuệ" thực sự. Kiến trúc này có thể dễ dàng mở rộng sang các kịch bản ứng dụng khác như dịch vụ khách hàng, hỗ trợ kỹ thuật, trợ lý cá nhân, v.v.

Ở chương tiếp theo, chúng ta sẽ tiếp tục khám phá cách nâng cao hơn nữa chất lượng hội thoại và trải nghiệm người dùng của Agent thông qua kỹ thuật ngữ cảnh; hãy đón chờ!

## Bài tập

> <strong>Gợi ý</strong>: một số bài tập không có đáp án chuẩn; trọng tâm là rèn luyện khả năng hiểu tổng hợp và thực hành của người học đối với hệ thống bộ nhớ và kỹ thuật RAG.

1. Chương này giới thiệu bốn loại bộ nhớ: bộ nhớ làm việc, bộ nhớ tình huống, bộ nhớ ngữ nghĩa và bộ nhớ tri giác. Hãy phân tích:

   - Trong mục 8.2.5, mỗi loại bộ nhớ đều có công thức chấm điểm riêng. Hãy so sánh cơ chế chấm điểm của bộ nhớ tình huống và bộ nhớ ngữ nghĩa, giải thích vì sao bộ nhớ tình huống nhấn mạnh hơn "độ gần thời gian" (trọng số 0.2), còn bộ nhớ ngữ nghĩa nhấn mạnh hơn "truy xuất đồ thị" (trọng số 0.3)?
   - Nếu phải thiết kế một "trợ lý quản lý sức khỏe cá nhân" (cần ghi lại dữ liệu ăn uống, vận động, giấc ngủ của người dùng và đưa ra khuyến nghị sức khỏe), bạn sẽ kết hợp bốn loại bộ nhớ này như thế nào? Hãy thiết kế kịch bản ứng dụng cụ thể cho từng loại bộ nhớ.
   - Bộ nhớ làm việc áp dụng cơ chế TTL (Time To Live) để tự động dọn dữ liệu hết hạn. Hãy suy nghĩ: trong trường hợp nào, bộ nhớ làm việc quan trọng nên được "tích hợp" (consolidate) thành bộ nhớ dài hạn? Làm sao thiết kế một điều kiện kích hoạt tích hợp tự động?

2. Trong hệ thống RAG ở mục 8.3, chúng ta dùng MarkItDown để chuyển đổi thống nhất tài liệu các định dạng sang Markdown. Hãy suy nghĩ sâu:

   > <strong>Gợi ý</strong>: đây là một bài thực hành, khuyến nghị thao tác thực tế

   - Chiến lược chia khối thông minh hiện tại dựa trên cấp tiêu đề của Markdown (#, ##, ###) để phân tách. Nếu xử lý tài liệu không có cấu trúc tiêu đề rõ ràng (như tiểu thuyết, điều khoản pháp luật), nên tối ưu chiến lược chia khối như thế nào? Hãy thử hiện thực một thuật toán chia khối dựa trên "ranh giới ngữ nghĩa".
   - Mục 8.3.5 giới thiệu hai chiến lược truy xuất nâng cao MQE (mở rộng đa truy vấn) và HyDE (embedding tài liệu giả định). Hãy chọn một kịch bản thực tế (như hỏi đáp tài liệu kỹ thuật, truy xuất tri thức y tế), so sánh khác biệt hiệu quả của ba phương pháp truy xuất cơ bản, MQE và HyDE, đồng thời phân tích kịch bản phù hợp của từng phương pháp.
   - Chất lượng truy xuất của hệ thống RAG phụ thuộc rất lớn vào việc lựa chọn mô hình embedding. Hãy so sánh ba phương án embedding được nhắc trong chương này (API Bailian, Transformer cục bộ, TF-IDF), đánh giá theo các chiều như độ chính xác, tốc độ, chi phí, triển khai ngoại tuyến, và đưa ra khuyến nghị lựa chọn.

3. Cơ chế "quên" của hệ thống bộ nhớ là thiết kế quan trọng mô phỏng nhận thức con người. Dựa trên MemoryTool ở mục 8.2.3, hãy hoàn thành bài thực hành mở rộng sau:

   > <strong>Gợi ý</strong>: đây là một bài thực hành, khuyến nghị thao tác thực tế

   - Hiện có ba chiến lược quên: dựa trên độ quan trọng, dựa trên thời gian, dựa trên dung lượng. Hãy thiết kế và hiện thực một chiến lược "quên thông minh", tổng hợp nhiều yếu tố như độ quan trọng, tần suất truy cập, suy giảm theo thời gian, dùng chấm điểm có trọng số để quyết định những bộ nhớ nào nên bị quên.
   - Trong hệ thống Agent chạy lâu dài, cơ sở dữ liệu bộ nhớ có thể tích lũy lượng lớn dữ liệu. Hãy thiết kế một cơ chế "lưu trữ bộ nhớ": chuyển những bộ nhớ lâu không dùng nhưng có thể có giá trị sang lưu trữ lạnh, khôi phục khi cần. Cơ chế này nên tích hợp với bốn loại bộ nhớ hiện có như thế nào?
   - Suy nghĩ: nếu Agent cần "quên" một số thông tin nhạy cảm (như dữ liệu riêng tư của người dùng), chỉ xóa khỏi cơ sở dữ liệu có đủ không? Trong trường hợp dùng cơ sở dữ liệu vector và cơ sở dữ liệu đồ thị, làm sao đảm bảo dữ liệu được xóa triệt để?

4. Trong ca "trợ lý học tập thông minh" ở mục 8.4, chúng ta kết hợp MemoryTool và RAGTool. Hãy phân tích sâu:

   - Phương thức `ask_question()` trong ca đồng thời dùng truy xuất RAG và truy xuất bộ nhớ. Hãy phân tích: trong trường hợp nào nên ưu tiên dùng RAG? Trong trường hợp nào nên ưu tiên dùng Memory? Làm sao thiết kế cơ chế "định tuyến thông minh" để tự động chọn cách truy xuất phù hợp nhất?
   - Báo cáo học tập hiện tại (`generate_report()`) chỉ chứa thông tin thống kê. Hãy mở rộng chức năng này, thiết kế một bộ sinh báo cáo học tập thông minh hơn: có thể phân tích quỹ đạo học tập của người dùng, nhận diện điểm mù tri thức, khuyến nghị nội dung học tập tiếp theo. Việc này cần dùng những loại bộ nhớ và chiến lược truy xuất nào?
   - Giả sử bạn cần triển khai trợ lý học tập này thành dịch vụ Web đa người dùng, mỗi người dùng có bộ nhớ và kho tri thức độc lập. Hãy thiết kế phương án cách ly dữ liệu: làm sao hiện thực cách ly dữ liệu ở cấp người dùng trong Qdrant và Neo4j? Làm sao tối ưu hiệu năng truy xuất trong kịch bản đa người dùng?

5. Bộ nhớ ngữ nghĩa dùng cơ sở dữ liệu đồ thị Neo4j để lưu đồ thị tri thức. Hãy suy nghĩ:

   - Trong hiện thực bộ nhớ ngữ nghĩa ở mục 8.2.5, hệ thống tự động trích xuất thực thể và quan hệ để xây dựng đồ thị tri thức. Hãy phân tích: độ chính xác của việc trích xuất tự động này như thế nào? Trong trường hợp nào có thể trích xuất sai thực thể hoặc quan hệ? Làm sao thiết kế cơ chế "đánh giá chất lượng đồ thị tri thức"?
   - Một ưu thế quan trọng của đồ thị tri thức là hỗ trợ suy luận quan hệ phức tạp. Hãy thiết kế một kịch bản truy vấn, tận dụng đầy đủ năng lực truy vấn đồ thị của Neo4j (như quan hệ nhiều bước, tìm đường đi), hiện thực nhiệm vụ mà truy xuất vector thuần túy không thể hoàn thành.
   - So sánh chiến lược kết hợp "truy xuất vector + truy xuất đồ thị" của bộ nhớ ngữ nghĩa với truy xuất vector thuần túy: trong loại truy vấn nào, truy xuất đồ thị có thể mang lại cải thiện hiệu năng rõ rệt? Hãy giải thích bằng ví dụ cụ thể.

## Tài liệu tham khảo

[1] Atkinson, R. C., & Shiffrin, R. M. (1968). Human memory: A proposed system and its control processes. In *Psychology of learning and motivation* (Vol. 2, pp. 89-195). Academic press.

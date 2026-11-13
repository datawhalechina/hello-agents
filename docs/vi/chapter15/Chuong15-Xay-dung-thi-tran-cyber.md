# Chương 15: Xây dựng thị trấn cyber

Chương này, chúng ta sẽ khám phá một hướng đi hoàn toàn mới: <strong>kết hợp công nghệ Agent với game engine để xây dựng một thị trấn AI tràn đầy sức sống</strong>.

Bạn còn nhớ những NPC sống động trong “The Sims” hay “Animal Crossing” không? Họ có tính cách, ký ức và các mối quan hệ xã hội riêng. Thị trấn Cyber trong chương này sẽ là một dự án tương tự, nhưng khác với game truyền thống, NPC của chúng ta sở hữu “trí thông minh” thực sự — họ có thể hiểu cuộc trò chuyện của người chơi, ghi nhớ những tương tác trong quá khứ và có phản ứng khác nhau dựa trên độ thiện cảm. Thị trấn Cyber trong chương này bao gồm các chức năng cốt lõi sau:

<strong>(1) Hệ thống hội thoại NPC thông minh</strong>: Người chơi có thể trò chuyện bằng ngôn ngữ tự nhiên với NPC, NPC sẽ phản hồi dựa trên thiết lập nhân vật và ký ức của mình.

<strong>(2) Hệ thống bộ nhớ</strong>: NPC có bộ nhớ ngắn hạn và bộ nhớ dài hạn, có thể ghi nhớ lịch sử tương tác với người chơi.

<strong>(3) Hệ thống độ thiện cảm</strong>: Thái độ của NPC với người chơi sẽ thay đổi theo tương tác, từ xa lạ đến quen thuộc, từ thân thiện đến thân mật.

<strong>(4) Tương tác trò chơi hóa</strong>: Người chơi có thể tự do di chuyển trong scene văn phòng phong cách pixel 2D, tương tác với các NPC khác nhau.

<strong>(5) Hệ thống log thời gian thực</strong>: Mọi cuộc hội thoại và tương tác đều được ghi lại, thuận tiện cho gỡ lỗi và phân tích.

## 15.1 Tổng quan dự án và thiết kế kiến trúc

### 15.1.1 Vì sao cần xây dựng thị trấn AI

NPC trong game truyền thống thường chỉ có thể nói những câu thoại cố định, hoặc tương tác hạn chế thông qua cây hội thoại được thiết kế sẵn. Ngay cả những game RPG phức tạp nhất, hội thoại của NPC cũng do biên kịch viết trước. Cách làm này tuy có thể kiểm soát được, nhưng thiếu đi “trí thông minh” và “sức sống” thực sự.

Hãy tưởng tượng, nếu NPC trong game có thể hiểu bất cứ điều gì bạn nói, không còn giới hạn trong các lựa chọn định sẵn, bạn có thể giao tiếp với NPC bằng ngôn ngữ tự nhiên. NPC sẽ nhớ lần trước bạn đã nói gì, quan hệ giữa hai người ra sao, thậm chí cả sở thích của bạn. Mỗi NPC đều có nghề nghiệp, tính cách và phong cách nói chuyện riêng. Thái độ của NPC với bạn sẽ thay đổi theo tương tác, từ người xa lạ thành bạn bè, thậm chí thành bạn thân.

Đây chính là khả năng mới mà công nghệ AI mang đến cho game. Bằng cách kết hợp mô hình ngôn ngữ lớn với game engine, chúng ta có thể tạo ra những NPC thực sự “sống”. Đây không chỉ là một bản demo kỹ thuật, mà còn là sự khám phá hình thái game của tương lai. Trong game giáo dục, NPC có thể đóng vai nhân vật lịch sử, nhà khoa học, dạy học tương tác với học sinh. Trong văn phòng ảo, NPC có thể đóng vai đồng nghiệp, người hướng dẫn, đưa ra trợ giúp và lời khuyên. NPC còn có thể là người đồng hành, giao tiếp cảm xúc với người dùng, được ứng dụng trong lĩnh vực sức khỏe tinh thần. Tất nhiên, ứng dụng trực tiếp nhất là thêm NPC AI cho game truyền thống, nâng cao trải nghiệm của người chơi.

### 15.1.2 Tổng quan kiến trúc kỹ thuật

Thị trấn Cyber áp dụng kiến trúc tách biệt <strong>game engine + dịch vụ backend</strong>, chia thành bốn tầng, như Hình 15.1.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-1.png" alt="" width="85%"/>
  <p>Hình 15.1 Kiến trúc kỹ thuật của Thị trấn Cyber</p>
</div>

Tầng frontend sử dụng game engine Godot 4.5, phụ trách render game, điều khiển người chơi, hiển thị NPC và UI hội thoại. Godot là một game engine 2D/3D mã nguồn mở, rất phù hợp để phát triển nhanh các game phong cách pixel. Tầng backend sử dụng framework FastAPI, phụ trách định tuyến API, quản lý trạng thái NPC, xử lý hội thoại và ghi log. FastAPI là một framework web Python hiện đại, hiệu năng tốt và dễ phát triển. Tầng Agent sử dụng framework HelloAgents do chính chúng ta xây dựng, phụ trách trí tuệ của NPC, quản lý bộ nhớ và tính độ thiện cảm. Mỗi NPC đều là một instance SimpleAgent, có bộ nhớ và trạng thái độc lập. Tầng dịch vụ bên ngoài cung cấp năng lực LLM, lưu trữ vector và lưu trữ dữ liệu, bao gồm LLM API, cơ sở dữ liệu vector Qdrant và cơ sở dữ liệu quan hệ SQLite.

Quá trình luân chuyển dữ liệu được minh họa như Hình 15.2:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-2.png" alt="" width="85%"/>
  <p>Hình 15.2 Quá trình luân chuyển dữ liệu</p>
</div>


Người chơi nhấn phím E trong Godot để tương tác với NPC, Godot gửi yêu cầu hội thoại tới backend FastAPI thông qua HTTP API. Backend gọi SimpleAgent của HelloAgents để xử lý hội thoại, Agent truy xuất lịch sử liên quan từ hệ thống bộ nhớ, sau đó gọi LLM để sinh phản hồi. Backend cập nhật trạng thái và độ thiện cảm của NPC, ghi log ra console và tệp, cuối cùng trả phản hồi về cho frontend Godot. Godot hiển thị phản hồi của NPC và cập nhật UI, hoàn thành một vòng tương tác đầy đủ.

Cấu trúc dự án như sau, giúp bạn định vị mã nguồn:

```
Helloagents-AI-Town/
├── helloagents-ai-town/           # Dự án game Godot
│   ├── project.godot              # Cấu hình dự án Godot
│   ├── scenes/                    # Scene game
│   │   ├── main.tscn              # Scene chính (văn phòng)
│   │   ├── player.tscn            # Nhân vật người chơi
│   │   ├── npc.tscn               # Nhân vật NPC
│   │   └── dialogue_ui.tscn       # UI hội thoại
│   ├── scripts/                   # Script GDScript
│   │   ├── main.gd                # Logic scene chính
│   │   ├── player.gd              # Điều khiển người chơi
│   │   ├── npc.gd                 # Hành vi NPC
│   │   ├── dialogue_ui.gd         # Logic UI hội thoại
│   │   ├── api_client.gd          # API client
│   │   └── config.gd              # Quản lý cấu hình
│   └── assets/                    # Tài nguyên game
│       ├── characters/            # Sprite nhân vật
│       ├── interiors/             # Scene trong nhà
│       ├── ui/                    # Tư liệu UI
│       └── audio/                 # Âm thanh và nhạc
│
└── backend/                       # Backend Python
    ├── main.py                    # Chương trình chính FastAPI
    ├── agents.py                  # Hệ thống NPC Agent
    ├── relationship_manager.py    # Quản lý độ thiện cảm
    ├── state_manager.py           # Quản lý trạng thái
    ├── logger.py                  # Hệ thống log
    ├── config.py                  # Quản lý cấu hình
    ├── models.py                  # Mô hình dữ liệu
    ├── requirements.txt           # Phụ thuộc Python
    └── .env.example               # Mẫu biến môi trường
```

Thiết kế kiến trúc chi tiết và luồng dữ liệu sẽ được giới thiệu trong các phần sau.

### 15.1.3 Trải nghiệm nhanh: chạy dự án trong 5 phút

Trước khi đi sâu tìm hiểu chi tiết hiện thực, hãy chạy dự án trước để xem hiệu quả cuối cùng. Như vậy bạn sẽ có nhận thức trực quan về toàn bộ hệ thống.

<strong>Yêu cầu môi trường:</strong>

- Godot 4.2 trở lên
- Python 3.10 trở lên
- Khóa LLM API (OpenAI, DeepSeek, Zhipu, v.v.)

<strong>Tải dự án:</strong>

Bạn có thể xem tại `code/chapter15/Helloagents-AI-Town`, hoặc clone toàn bộ kho hello-agents từ GitHub.

<strong>Khởi động backend:</strong>

```bash
# 1. Di chuyển vào thư mục backend
cd Helloagents-AI-Town/backend

# 2. Cài đặt phụ thuộc
pip install -r requirements.txt

# 3. Cấu hình biến môi trường
cp .env.example .env
# Chỉnh sửa tệp .env, điền khóa API của bạn

# 4. Khởi động dịch vụ backend
python main.py
```

Sau khi khởi động thành công, bạn sẽ thấy output như sau:

```
============================================================
🎮 Dịch vụ backend Thị trấn Cyber đang khởi động...
============================================================
✅ Tất cả dịch vụ đã khởi động!
📡 Địa chỉ API: http://0.0.0.0:8000
📚 Tài liệu API: http://0.0.0.0:8000/docs
============================================================
```

<strong>Khởi động Godot:</strong>

Việc cài đặt Godot rất đơn giản, Windows cung cấp tệp `.exe` mở trực tiếp, Mac cũng cung cấp tệp `.dmg`. Bạn có thể tải trực tiếp từ trang chủ ([Windows](https://godotengine.org/download/windows/) / [Mac](https://godotengine.org/download/macos/))

Mở Godot engine, nhấn nút “Import”, duyệt đến `Helloagents-AI-Town/helloagents-ai-town/scenes/main.tscn`, nhấn “Import & Edit”. Sau khi Godot import tài nguyên xong, nhấn `F5` hoặc nhấn nút “Run” để khởi động game.

<strong>Trải nghiệm các chức năng cốt lõi:</strong>

Sau khi game khởi động, bạn sẽ thấy một scene văn phòng Datawhale theo phong cách pixel, như Hình 15.3.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-3.png" alt="" width="85%"/>
  <p>Hình 15.3 Scene game của Thị trấn Cyber</p>
</div>

Dùng phím WASD để di chuyển nhân vật người chơi; khi đi đến gần NPC, trên màn hình sẽ hiện gợi ý “Nhấn E để tương tác”. Sau khi nhấn phím E, hộp thoại sẽ bật lên, bạn có thể nhập bất cứ điều gì muốn nói, như Hình 15.4.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-4.png" alt="" width="85%"/>
  <p>Hình 15.4 Giao diện trò chuyện với NPC</p>
</div>

NPC sẽ phản hồi dựa trên thiết lập nhân vật của mình (kỹ sư Python, quản lý sản phẩm, nhà thiết kế UI) và lịch sử tương tác giữa hai bạn. Khi cuộc hội thoại tiếp diễn, độ thiện cảm của NPC với bạn sẽ dần tăng lên, từ “Xa lạ” đến “Quen thuộc”, rồi “Thân thiện”, “Thân mật” và thậm chí “Bạn thân”.

<strong>Hệ thống độ thiện cảm được hiện thực ở backend</strong>, mỗi cuộc hội thoại đều điều chỉnh giá trị độ thiện cảm dựa trên nội dung tin nhắn của người chơi và phân tích cảm xúc. Mặc dù giao diện game ở frontend không hiển thị trực tiếp giá trị độ thiện cảm, nhưng mọi thay đổi của độ thiện cảm đều được ghi lại chi tiết trong log của backend. Bạn có thể xem thay đổi độ thiện cảm của từng cuộc hội thoại trong tệp `backend/logs/dialogue_YYYY-MM-DD.log`. Tệp log sẽ ghi lại thông tin chi tiết của mỗi cuộc hội thoại, bao gồm: giá trị độ thiện cảm hiện tại, ký ức liên quan được truy xuất, phản hồi của NPC, mức thay đổi độ thiện cảm (+2.0, +3.0, v.v.), lý do thay đổi (lời chào thân thiện, giao tiếp bình thường, v.v.) và kết quả phân tích cảm xúc (positive, neutral, v.v.). Thiết kế này cho phép nhà phát triển theo dõi rõ ràng quá trình phát triển quan hệ giữa NPC và người chơi, đồng thời cung cấp nền tảng dữ liệu cho việc bổ sung UI độ thiện cảm ở frontend sau này.

Tất cả các cuộc hội thoại đều được ghi vào tệp log của backend, bạn có thể xem thời gian thực bằng lệnh sau:

```bash
# Trong thư mục backend
python view_logs.py
```

Trải nghiệm đơn giản này đã trình bày các chức năng cốt lõi của thị trấn AI. Tiếp theo, chúng ta sẽ đi sâu tìm hiểu cách hiện thực các chức năng này.




## 15.2 Hệ thống Agent NPC

### 15.2.1 SimpleAgent dựa trên HelloAgents

Trong Thị trấn Cyber, mỗi NPC là một Agent độc lập. Chúng ta sử dụng SimpleAgent trong framework HelloAgents để hiện thực trí tuệ của NPC. SimpleAgent là một hiện thực Agent nhẹ, đóng gói các chức năng cốt lõi như gọi LLM, quản lý tin nhắn và gọi công cụ.

Nhớ lại SimpleAgent mà chúng ta đã học ở chương 7, cốt lõi của nó là một vòng hội thoại đơn giản: nhận tin nhắn người dùng, gọi LLM sinh phản hồi, trả kết quả. Trong Thị trấn Cyber, chúng ta cần tạo một instance SimpleAgent cho mỗi NPC, và cấu hình system prompt riêng cho nó, để mỗi NPC có tính cách và thiết lập nhân vật khác nhau.

Hãy xem cách tạo một NPC Agent. Trước tiên, chúng ta cần định nghĩa thông tin cơ bản của NPC, bao gồm ID, tên, nghề nghiệp và tính cách. Sau đó, chúng ta xây dựng system prompt dựa trên những thông tin này, để LLM nhập vai NPC đó. Cuối cùng, chúng ta tạo instance SimpleAgent và cấu hình hệ thống bộ nhớ.

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.memory import MemoryManager, WorkingMemory, EpisodicMemory

def create_npc_agent(npc_id: str, name: str, role: str, personality: str):
    """Tạo NPC Agent"""
    # Xây dựng system prompt
    system_prompt = f"""Bạn là {name}, một {role}.
Đặc điểm tính cách của bạn: {personality}

Bạn làm việc tại văn phòng Datawhale, cùng đồng nghiệp thúc đẩy sự phát triển của cộng đồng mã nguồn mở.
Hãy trò chuyện tự nhiên với người chơi theo vai trò và tính cách của bạn.
Ghi nhớ nội dung trò chuyện trước đó của hai người, giữ cho cuộc hội thoại được mạch lạc.
"""

    # Tạo instance LLM
    llm = HelloAgentsLLM()

    # Tạo trình quản lý bộ nhớ
    memory_manager = MemoryManager(
        working_memory=WorkingMemory(capacity=10, ttl_minutes=120),
        episodic_memory=EpisodicMemory(
            db_path=f"memory_data/{npc_id}_episodic.db",
            collection_name=f"{npc_id}_memories"
        )
    )

    # Tạo Agent
    agent = SimpleAgent(
        name=name,
        llm=llm,
        system_prompt=system_prompt,
        memory_manager=memory_manager
    )

    return agent
```

Đoạn mã này trình bày cách tạo một NPC Agent. System prompt định nghĩa danh tính và tính cách của NPC, trình quản lý bộ nhớ giúp NPC ghi nhớ lịch sử hội thoại với người chơi. WorkingMemory là bộ nhớ ngắn hạn, dung lượng 10 tin nhắn, thời gian lưu giữ 120 phút. EpisodicMemory là bộ nhớ dài hạn, sử dụng cơ sở dữ liệu SQLite và cơ sở dữ liệu vector Qdrant để lưu trữ, có thể truy xuất các cuộc hội thoại lịch sử liên quan.

Quy trình làm việc của NPC Agent được minh họa như Hình 15.5:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-5.png" alt="" width="85%"/>
  <p>Hình 15.5 Quy trình làm việc của NPC Agent</p>
</div>


### 15.2.2 Thiết lập nhân vật NPC và thiết kế prompt

Một NPC tốt cần có tính cách và thiết lập nhân vật rõ nét. Trong Thị trấn Cyber, chúng ta thiết kế ba NPC, đại diện cho các nghề nghiệp và tính cách khác nhau.

<strong>Trương Tam – Kỹ sư Python</strong>

Trương Tam là một kỹ sư Python kỳ cựu, phụ trách phát triển cốt lõi của framework HelloAgents. Anh có tính cách nghiêm túc, nói chuyện thẳng thắn, thích dùng thuật ngữ kỹ thuật. Anh có yêu cầu cao về chất lượng mã nguồn, thường chia sẻ các mẹo lập trình và thực hành tốt nhất.

```python
npc_zhang = {
    "npc_id": "zhang_san",
    "name": "张三",
    "role": "Kỹ sư Python",
    "personality": "Nghiêm túc, chuyên nghiệp, thích chia sẻ kiến thức kỹ thuật. Nói thẳng, coi trọng chất lượng mã nguồn."
}
```

<strong>Lý Tứ – Quản lý sản phẩm</strong>

Lý Tứ là một quản lý sản phẩm giàu kinh nghiệm, phụ trách quy hoạch sản phẩm và thiết kế trải nghiệm người dùng của framework HelloAgents. Anh có tính cách hướng ngoại, giỏi giao tiếp, luôn suy nghĩ từ góc độ người dùng. Anh thích thảo luận về thiết kế sản phẩm và nhu cầu người dùng, thường hỏi “tại sao”.

```python
npc_li = {
    "npc_id": "li_si",
    "name": "李四",
    "role": "Quản lý sản phẩm",
    "personality": "Hướng ngoại, giỏi giao tiếp, coi trọng trải nghiệm người dùng. Thích suy nghĩ từ góc độ người dùng."
}
```

<strong>Vương Ngũ – Nhà thiết kế UI</strong>

Vương Ngũ là một nhà thiết kế UI giàu sáng tạo, phụ trách thiết kế giao diện và thể hiện thị giác của framework HelloAgents. Anh có tính cách điềm đạm, thẩm mỹ độc đáo, có cảm nhận nhạy bén với màu sắc và bố cục. Anh thích thảo luận về ý tưởng thiết kế và mỹ học, thường chia sẻ một số nguồn cảm hứng thiết kế.

```python
npc_wang = {
    "npc_id": "wang_wu",
    "name": "王五",
    "role": "Nhà thiết kế UI",
    "personality": "Điềm đạm, giàu sáng tạo, thẩm mỹ độc đáo. Coi trọng thể hiện thị giác và trải nghiệm người dùng."
}
```

Thiết lập của ba NPC này đều có nét riêng, người chơi có thể chọn tương tác với NPC khác nhau theo sở thích của mình. Trương Tam có thể dạy bạn mẹo lập trình, Lý Tứ có thể cùng bạn thảo luận thiết kế sản phẩm, Vương Ngũ có thể chia sẻ cảm hứng thiết kế.

### 15.2.3 Tích hợp hệ thống bộ nhớ

Hệ thống bộ nhớ là chìa khóa cho trí tuệ của NPC. Một NPC có thể nhớ các cuộc hội thoại trước đây sẽ khiến người chơi cảm thấy chân thực và thú vị hơn. Chúng ta sử dụng `WorkingMemory` và `EpisodicMemory` của helloagents để xây dựng bộ nhớ ngắn hạn và bộ nhớ dài hạn.

Bộ nhớ ngắn hạn lưu trữ nội dung hội thoại gần nhất, dung lượng có hạn, sẽ tự động được dọn dẹp theo thời gian. Vai trò của nó là duy trì tính mạch lạc của cuộc hội thoại, giúp NPC hiểu ngữ cảnh. Ví dụ, khi người chơi nói “Nó màu gì?”, NPC cần tìm trong bộ nhớ ngắn hạn xem “nó” đang chỉ điều gì.

Bộ nhớ dài hạn lưu trữ toàn bộ lịch sử hội thoại, sử dụng cơ sở dữ liệu vector để truy xuất ngữ nghĩa. Khi người chơi nhắc đến một chủ đề nào đó, NPC có thể truy xuất các cuộc hội thoại lịch sử liên quan từ bộ nhớ dài hạn, nhớ lại nội dung đã thảo luận trước đó. Ví dụ, khi người chơi nói “Còn nhớ dự án chúng ta thảo luận lần trước không?”, NPC có thể tìm thấy bản ghi hội thoại liên quan trong bộ nhớ dài hạn.

Kiến trúc của hệ thống bộ nhớ được minh họa như Hình 15.6:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-6.png" alt="" width="85%"/>
  <p>Hình 15.6 Kiến trúc hệ thống bộ nhớ</p>
</div>


Trong sử dụng thực tế, Agent sẽ lấy các cuộc hội thoại gần nhất từ bộ nhớ ngắn hạn trước, sau đó truy xuất các cuộc hội thoại lịch sử liên quan từ bộ nhớ dài hạn, gửi cùng những thông tin này cho LLM để sinh phản hồi chính xác và cá nhân hóa hơn.

```python
# Quy trình Agent xử lý hội thoại
def process_dialogue(agent, player_message):
    # 1. Lấy hội thoại gần nhất từ bộ nhớ ngắn hạn
    recent_messages = agent.memory_manager.working_memory.get_recent_messages(5)

    # 2. Truy xuất lịch sử liên quan từ bộ nhớ dài hạn
    relevant_memories = agent.memory_manager.episodic_memory.search(
        query=player_message,
        top_k=3
    )

    # 3. Xây dựng ngữ cảnh
    context = {
        "recent": recent_messages,
        "relevant": relevant_memories
    }

    # 4. Gọi Agent sinh phản hồi
    reply = agent.run(player_message, context=context)

    # 5. Lưu vào hệ thống bộ nhớ
    agent.memory_manager.add_interaction(player_message, reply)

    return reply
```

Quy trình này đảm bảo NPC có thể ghi nhớ lịch sử tương tác với người chơi và thể hiện điều đó trong cuộc hội thoại.

### 15.2.4 Sinh hội thoại hàng loạt: chế độ tải nhẹ

Trong vận hành thực tế, sẽ sớm phát hiện một vấn đề: khi nhiều người chơi đồng thời trò chuyện với các NPC khác nhau, backend cần xử lý đồng thời nhiều yêu cầu LLM. Mỗi yêu cầu đều cần gọi API, điều này không chỉ làm tăng chi phí mà còn có thể khiến yêu cầu thất bại hoặc bị trễ do giới hạn đồng thời.

Để giải quyết vấn đề này, chúng ta thiết kế một <strong>hệ thống sinh hội thoại hàng loạt</strong>. Ý tưởng cốt lõi là: gộp yêu cầu hội thoại của nhiều NPC thành một lần gọi LLM, để LLM sinh phản hồi cho tất cả NPC trong một lượt. Điều này giống như “món ăn chuẩn bị sẵn” của nhà hàng, chuẩn bị hàng loạt trước, dùng ngay khi cần, giảm đáng kể chi phí và độ trễ.

Quy trình làm việc của sinh hàng loạt được minh họa như Hình 15.7:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-7.png" alt="" width="85%"/>
  <p>Hình 15.7 Sinh hàng loạt so với chế độ truyền thống</p>
</div>


Cách hiện thực bộ sinh hàng loạt rất khéo léo. Chúng ta xây dựng một prompt đặc biệt, yêu cầu LLM sinh hội thoại của tất cả NPC trong một lượt và trả về dưới định dạng JSON. Như vậy, một lần gọi API có thể thu được phản hồi của tất cả NPC, chi phí giảm xuống còn 1/3 so với ban đầu, độ trễ cũng giảm mạnh.

```python
class NPCBatchGenerator:
    """Bộ sinh hội thoại NPC hàng loạt"""

    def __init__(self):
        self.llm = HelloAgentsLLM()
        self.npc_configs = NPC_ROLES  # Cấu hình của tất cả NPC

    def generate_batch_dialogues(self, context: Optional[str] = None) -> Dict[str, str]:
        """Sinh hội thoại của tất cả NPC theo lô

        Args:
            context: Ngữ cảnh của cảnh (như "giờ làm việc buổi sáng", "giờ ăn trưa", v.v.)

        Returns:
            Dict[str, str]: Ánh xạ từ tên NPC sang nội dung hội thoại
        """
        # Xây dựng prompt sinh hàng loạt
        prompt = self._build_batch_prompt(context)

        # Một lần gọi LLM sinh tất cả hội thoại
        response = self.llm.invoke([
            {"role": "system", "content": "Bạn là bộ sinh hội thoại NPC trong game, giỏi sáng tác những cuộc hội thoại văn phòng tự nhiên và chân thực."},
            {"role": "user", "content": prompt}
        ])

        # Phân tích phản hồi JSON
        dialogues = json.loads(response)
        # Định dạng trả về: {"张三": "...", "李四": "...", "王五": "..."}

        return dialogues

    def _build_batch_prompt(self, context: Optional[str] = None) -> str:
        """Xây dựng prompt sinh hàng loạt"""
        # Tự động suy luận bối cảnh theo thời gian
        if context is None:
            context = self._get_current_context()

        # Xây dựng mô tả NPC
        npc_descriptions = []
        for name, cfg in self.npc_configs.items():
            desc = f"- {name}({cfg['title']}): tại {cfg['location']}, {cfg['activity']}, tính cách {cfg['personality']}"
            npc_descriptions.append(desc)

        npc_desc_text = "\n".join(npc_descriptions)

        prompt = f"""Hãy sinh hội thoại hoặc mô tả hành vi hiện tại cho 3 NPC trong văn phòng Datawhale.

【Bối cảnh】{context}

【Thông tin NPC】
{npc_desc_text}

【Yêu cầu sinh】
1. Mỗi NPC sinh 1 câu (20-40 chữ)
2. Nội dung phải phù hợp với thiết lập nhân vật, hoạt động hiện tại và không khí của cảnh
3. Có thể là độc thoại, mô tả trạng thái công việc, hoặc một suy nghĩ đơn giản
4. Phải tự nhiên chân thực, giống những đồng nghiệp văn phòng thật
5. **Bắt buộc trả về đúng định dạng JSON**

【Định dạng đầu ra】(tuân thủ nghiêm ngặt)
{{"张三": "...", "李四": "...", "王五": "..."}}

【Ví dụ đầu ra】
{{"张三": "Cái bug này đúng là quái đản, đã debug hai tiếng rồi...", "李四": "Ừm, độ ưu tiên của tính năng này cần đánh giá lại.", "王五": "Ly cà phê này vẽ latte đẹp thật, cảm hứng đến rồi!"}}

Hãy sinh (chỉ trả về JSON, không kèm nội dung khác):
"""
        return prompt
```

Điểm then chốt của thiết kế này nằm ở việc xây dựng prompt. Chúng ta yêu cầu rõ ràng LLM trả về định dạng JSON và cung cấp ví dụ đầu ra. LLM sẽ sinh phản hồi theo đúng định dạng này, chúng ta chỉ cần phân tích JSON là có thể thu được hội thoại của tất cả NPC.

Sinh hàng loạt còn có một lợi ích bổ sung: hội thoại của tất cả NPC được sinh trong cùng một ngữ cảnh, nên giữa chúng sẽ có mối liên hệ nhất định. Ví dụ, nếu Trương Tam đang gỡ lỗi, Lý Tứ có thể nhắc đến việc sẽ giúp xem qua; nếu Vương Ngũ đang thiết kế giao diện, Trương Tam có thể nói sẽ xem bản thiết kế sau. Điều này khiến không khí của cả văn phòng trở nên chân thực và mạch lạc hơn.

Tất nhiên, sinh hàng loạt cũng có một số giới hạn. Nó phù hợp hơn để sinh “hội thoại nền” hoặc “độc thoại” của NPC, chứ không phải tương tác trực tiếp với người chơi. Với các cuộc hội thoại do người chơi khởi xướng, chúng ta vẫn sử dụng Agent riêng để xử lý, nhằm đảm bảo tính cá nhân hóa và độ chính xác của phản hồi. Sinh hàng loạt chủ yếu dùng trong các tình huống sau:

1. <strong>Hội thoại nền của NPC</strong>: Khi người chơi bước vào cảnh, NPC đang làm gì, nói gì
2. <strong>Cập nhật định kỳ</strong>: Cập nhật trạng thái và hội thoại của NPC theo từng khoảng thời gian
3. <strong>Không khí của cảnh</strong>: Sinh hội thoại khác nhau theo thời gian (sáng, trưa, tối)
4. <strong>Giảm chi phí</strong>: Trong tình huống đồng thời cao, dùng sinh hàng loạt để giảm số lần gọi API

<strong>Chế độ hỗn hợp: sinh hàng loạt + phản hồi tức thời</strong>

Trong triển khai thực tế, chúng ta áp dụng một chế độ hỗn hợp, kết hợp sinh hàng loạt với phản hồi tức thời. Thiết kế này rất khéo léo, vừa đảm bảo hiệu suất, vừa đảm bảo chất lượng tương tác.

Cụ thể, hệ thống sẽ chạy sinh hàng loạt định kỳ ở background, sinh “hội thoại nền” trong cảnh hiện tại cho tất cả NPC. Những hội thoại này được cache lại; khi người chơi đến gần NPC nhưng chưa khởi xướng tương tác, NPC sẽ hiển thị những hội thoại nền này, như “Đang gỡ lỗi...”, “Đang xem tài liệu sản phẩm...”, v.v. Điều này khiến NPC trông như đang “sống”, thay vì là một mô hình tĩnh.

Nhưng khi người chơi nhấn phím E để khởi xướng tương tác, hệ thống sẽ lập tức chuyển sang chế độ phản hồi tức thời. Lúc này, backend sẽ gọi Agent riêng của NPC đó, sinh phản hồi cá nhân hóa dựa trên tin nhắn cụ thể của người chơi, ký ức lịch sử và độ thiện cảm. Quá trình này diễn ra theo thời gian thực, đảm bảo phản hồi của NPC có liên quan chặt chẽ với đầu vào của người chơi.

```python
# Hiện thực chế độ hỗn hợp trong main.py
@app.post("/dialogue")
async def dialogue(request: DialogueRequest):
    """Xử lý hội thoại giữa người chơi và NPC (chế độ phản hồi tức thời)"""
    npc_id = request.npc_id
    player_message = request.player_message
    player_name = request.player_name

    # Lấy NPC Agent (mỗi NPC có Agent độc lập)
    agent = npc_agents.get(npc_id)
    if not agent:
        raise HTTPException(status_code=404, detail="NPC not found")

    # Sinh phản hồi cá nhân hóa tức thời
    # Ở đây không dùng sinh hàng loạt, mà gọi phương thức run của Agent
    reply = agent.run(player_message)

    # Cập nhật độ thiện cảm
    affinity_change = relationship_manager.update_affinity(
        npc_id, player_name, player_message, reply
    )

    return {
        "npc_reply": reply,
        "affinity_score": affinity_change["score"],
        "affinity_level": affinity_change["level"]
    }

# Tác vụ nền: sinh hội thoại nền hàng loạt định kỳ
async def background_dialogue_update():
    """Tác vụ nền: cập nhật hội thoại nền của NPC mỗi 5 phút"""
    while True:
        try:
            # Dùng bộ sinh hàng loạt để sinh hội thoại nền cho tất cả NPC
            batch_generator = get_batch_generator()
            dialogues = batch_generator.generate_batch_dialogues()

            # Cập nhật vào trình quản lý trạng thái
            for npc_name, dialogue in dialogues.items():
                state_manager.update_npc_background_dialogue(npc_name, dialogue)

            print(f"✅ Cập nhật hội thoại nền hoàn tất: {len(dialogues)} NPC")
        except Exception as e:
            print(f"❌ Cập nhật hội thoại nền thất bại: {e}")

        # Chờ 5 phút
        await asyncio.sleep(300)
```

Ưu điểm của chế độ hỗn hợp này rất rõ ràng:

1. <strong>Giảm chi phí</strong>: Hội thoại nền dùng sinh hàng loạt, một lần gọi sinh hội thoại của tất cả NPC, chi phí thấp
2. <strong>Đảm bảo chất lượng</strong>: Tương tác với người chơi dùng phản hồi tức thời, mỗi phản hồi đều được cá nhân hóa, chất lượng cao
3. <strong>Nâng cao trải nghiệm</strong>: NPC luôn có “hội thoại nền”, trông rất sống động; khi người chơi tương tác, phản hồi chính xác, trải nghiệm tốt
4. <strong>Điều chỉnh linh hoạt</strong>: Có thể điều chỉnh động tần suất sinh hàng loạt theo tải của máy chủ

Thông qua việc kết hợp sinh hàng loạt và phản hồi tức thời, chúng ta hiện thực được một hệ thống NPC vừa hiệu quả vừa thông minh. Trong điều kiện bình thường, người chơi không cảm nhận được sự khác biệt nào, nhưng chi phí và hiệu năng của backend đã được tối ưu đáng kể. Cách thiết kế này cũng có thể áp dụng cho các tình huống khác cần lượng lớn lệnh gọi AI.




## 15.3 Thiết kế hệ thống độ thiện cảm

### 15.3.1 Phân cấp độ thiện cảm

Trong Thị trấn Cyber, thái độ của NPC với người chơi sẽ thay đổi theo tương tác. Chúng ta thiết kế một hệ thống độ thiện cảm năm cấp, từ xa lạ đến bạn thân, mỗi cấp có phạm vi điểm số khác nhau và biểu hiện hành vi tương ứng.

Ý tưởng cốt lõi của hệ thống độ thiện cảm là: lượng hóa quan hệ giữa NPC và người chơi, để phản hồi của NPC trở nên chân thực và có nhiều tầng lớp hơn. Khi người chơi mới vào game, tất cả NPC đều có thái độ xa lạ với người chơi, phản hồi khá lịch sự nhưng giữ khoảng cách. Khi cuộc hội thoại tiếp diễn, nếu người chơi thể hiện thân thiện, độ thiện cảm của NPC sẽ dần tăng lên, phản hồi cũng trở nên gần gũi và chi tiết hơn.

Chúng ta chia độ thiện cảm thành năm cấp, mỗi cấp tương ứng một phạm vi điểm số, như Hình 15.8:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-8.png" alt="" width="85%"/>
  <p>Hình 15.8 Phân cấp độ thiện cảm</p>
</div>

- <strong>Xa lạ (0-20 điểm)</strong>: NPC vừa quen người chơi, thái độ lịch sự nhưng giữ khoảng cách. Phản hồi ngắn gọn, không chủ động chia sẻ thông tin cá nhân.

- <strong>Quen thuộc (21-40 điểm)</strong>: NPC bắt đầu nhớ người chơi, sẵn sàng giao tiếp đơn giản. Phản hồi trở nên tự nhiên hơn, thỉnh thoảng chia sẻ một số thông tin liên quan đến công việc.

- <strong>Thân thiện (41-60 điểm)</strong>: NPC coi người chơi là bạn, sẵn sàng chia sẻ nhiều thông tin hơn. Phản hồi chi tiết hơn, chủ động hỏi thăm tình hình của người chơi.

- <strong>Thân mật (61-80 điểm)</strong>: NPC rất tin tưởng người chơi, sẵn sàng chia sẻ chủ đề riêng tư. Phản hồi tràn đầy nhiệt huyết, đưa ra trợ giúp và lời khuyên cho người chơi.

- <strong>Bạn thân (81-100 điểm)</strong>: NPC coi người chơi là bạn tốt nhất, không điều gì không thể nói. Phản hồi rất gần gũi, chia sẻ những suy nghĩ và cảm xúc trong lòng.

Thiết kế này giúp người chơi cảm nhận rõ ràng sự thay đổi trong quan hệ với NPC, đồng thời cung cấp nền tảng cho các lối chơi tiếp theo. Ví dụ, chỉ khi đạt đến một mức độ thiện cảm nhất định, NPC mới chia sẻ một số thông tin đặc biệt hoặc cung cấp nhiệm vụ đặc biệt.

### 15.3.2 Logic tính độ thiện cảm

Việc tính độ thiện cảm cần xem xét nhiều yếu tố. Chúng ta không thể đơn giản để mỗi cuộc hội thoại đều tăng điểm cố định, như vậy hệ thống sẽ trở nên máy móc và thiếu chân thực. Một hệ thống độ thiện cảm tốt cần nhận diện được thái độ của người chơi và điều chỉnh điểm số linh hoạt theo nội dung hội thoại.

Trong Thị trấn Cyber, chúng ta sử dụng LLM để phân tích nội dung hội thoại, phán đoán thái độ của người chơi là thân thiện, trung lập hay không thân thiện. Sau đó điều chỉnh điểm độ thiện cảm theo kết quả phán đoán. Quá trình này diễn ra tự động, người chơi không cần cố ý chọn lựa chọn, khiến tương tác trở nên tự nhiên hơn.

Quy trình tính độ thiện cảm được minh họa như Hình 15.9:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-9.png" alt="" width="85%"/>
  <p>Hình 15.9 Quy trình tính độ thiện cảm</p>
</div>


```python
class RelationshipManager:
    """Trình quản lý độ thiện cảm"""

    def __init__(self):
        self.affinity_data = {}  # Lưu dữ liệu độ thiện cảm
        self.llm = HelloAgentsLLM()  # Dùng để phân tích hội thoại

    def analyze_sentiment(self, player_message: str, npc_reply: str) -> int:
        """Phân tích cảm xúc của hội thoại, trả về mức thay đổi độ thiện cảm"""
        prompt = f"""Phân tích thái độ của người chơi trong cuộc hội thoại sau:
Người chơi: {player_message}
NPC: {npc_reply}

Hãy phán đoán thái độ của người chơi là:
1. Thân thiện (+5 điểm): lịch sự, nhiệt tình, bày tỏ cảm ơn hoặc đồng tình
2. Trung lập (+2 điểm): câu hỏi hoặc câu trần thuật thông thường
3. Không thân thiện (-3 điểm): thô lỗ, lạnh nhạt, chỉ trích hoặc phủ định

Chỉ trả về số, không kèm nội dung khác."""

        response = self.llm.think([{"role": "user", "content": prompt}])
        try:
            score_change = int(response.strip())
            return max(-3, min(5, score_change))  # Giới hạn trong khoảng -3 đến 5
        except:
            return 2  # Mặc định trung lập

    def update_affinity(self, npc_id: str, player_name: str,
                       player_message: str, npc_reply: str) -> dict:
        """Cập nhật độ thiện cảm"""
        key = f"{npc_id}_{player_name}"

        # Lấy độ thiện cảm hiện tại
        if key not in self.affinity_data:
            self.affinity_data[key] = {
                "score": 0,
                "level": "Xa lạ",
                "interaction_count": 0
            }

        # Phân tích cảm xúc của hội thoại
        score_change = self.analyze_sentiment(player_message, npc_reply)

        # Cập nhật điểm số
        current_score = self.affinity_data[key]["score"]
        new_score = max(0, min(100, current_score + score_change))

        # Cập nhật cấp độ
        level = self.get_affinity_level(new_score)

        # Cập nhật dữ liệu
        self.affinity_data[key].update({
            "score": new_score,
            "level": level,
            "interaction_count": self.affinity_data[key]["interaction_count"] + 1
        })

        return self.affinity_data[key]

    def get_affinity_level(self, score: int) -> str:
        """Lấy cấp độ thiện cảm theo điểm số"""
        if score <= 20:
            return "Xa lạ"
        elif score <= 40:
            return "Quen thuộc"
        elif score <= 60:
            return "Thân thiện"
        elif score <= 80:
            return "Thân mật"
        else:
            return "Bạn thân"
```

Cách hiện thực này sử dụng LLM để phân tích nội dung hội thoại, tự động phán đoán thái độ của người chơi và điều chỉnh độ thiện cảm. Thiết kế như vậy khiến hệ thống độ thiện cảm trở nên thông minh và tự nhiên hơn, người chơi không cần cố ý lấy lòng NPC, chỉ cần giao tiếp bình thường là đủ.

### 15.3.3 Độ thiện cảm ảnh hưởng đến hội thoại

Độ thiện cảm không chỉ là một con số, nó cần thực sự ảnh hưởng đến hành vi của NPC. Trong Thị trấn Cyber, chúng ta thay đổi system prompt của NPC, để NPC điều chỉnh phong cách phản hồi theo cấp độ thiện cảm hiện tại.

Khi độ thiện cảm thấp, NPC sẽ giữ thái độ lịch sự nhưng xa cách. Khi độ thiện cảm tăng lên, NPC sẽ trở nên nhiệt tình và cởi mở hơn. Sự thay đổi này được hiện thực thông qua việc điều chỉnh động system prompt.

```python
def create_npc_agent_with_affinity(npc_id: str, name: str, role: str,
                                   personality: str, affinity_level: str):
    """Tạo NPC Agent có kèm độ thiện cảm"""

    # Điều chỉnh prompt theo cấp độ thiện cảm
    affinity_prompts = {
        "Xa lạ": "Bạn vừa quen người chơi này, giữ thái độ lịch sự nhưng đừng quá nhiệt tình. Phản hồi ngắn gọn và chuyên nghiệp.",
        "Quen thuộc": "Bạn đã quen người chơi này, có thể giao tiếp bình thường. Phản hồi tự nhiên và thân thiện.",
        "Thân thiện": "Bạn coi người chơi này là bạn, sẵn sàng chia sẻ nhiều thông tin hơn. Phản hồi chi tiết và nhiệt tình.",
        "Thân mật": "Bạn rất tin tưởng người chơi này, có thể chia sẻ chủ đề riêng tư. Phản hồi tràn đầy sự quan tâm.",
        "Bạn thân": "Bạn coi người chơi này là bạn tốt nhất, không điều gì không thể nói. Phản hồi gần gũi và chân thành."
    }

    system_prompt = f"""Bạn là {name}, một {role}.
Đặc điểm tính cách của bạn: {personality}

Quan hệ hiện tại với người chơi: {affinity_level}
{affinity_prompts.get(affinity_level, affinity_prompts["Xa lạ"])}

Bạn làm việc tại văn phòng Datawhale, cùng đồng nghiệp thúc đẩy sự phát triển của cộng đồng mã nguồn mở.
Hãy phản hồi tự nhiên theo vai trò, tính cách của bạn và quan hệ với người chơi.
"""

    # Tạo Agent
    llm = HelloAgentsLLM()
    agent = SimpleAgent(
        name=name,
        llm=llm,
        system_prompt=system_prompt
    )

    return agent
```

Thiết kế này khiến hành vi của NPC thay đổi linh hoạt theo độ thiện cảm. Người chơi có thể cảm nhận rõ ràng rằng, khi tương tác tăng lên, thái độ của NPC với mình đang dần thay đổi, điều này làm tăng đáng kể tính nhập vai và thú vị của game.


## 15.4 Hiện thực dịch vụ backend


### 15.4.1 Cấu trúc ứng dụng FastAPI

Backend của Thị trấn Cyber được xây dựng bằng framework FastAPI, phụ trách xử lý yêu cầu từ frontend Godot, gọi NPC Agent của HelloAgents, quản lý trạng thái và độ thiện cảm của NPC, cũng như ghi log. Một cấu trúc ứng dụng rõ ràng giúp mã nguồn dễ bảo trì và mở rộng hơn.

Ứng dụng FastAPI của chúng ta áp dụng thiết kế mô-đun, tách các chức năng khác nhau vào các tệp khác nhau, như Hình 15.10:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-10.png" alt="" width="85%"/>
  <p>Hình 15.10 Cấu trúc ứng dụng backend</p>
</div>


Hãy bắt đầu từ `main.py`, đây là tệp đầu vào của ứng dụng FastAPI:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from agents import NPCAgentManager
from relationship_manager import RelationshipManager
from state_manager import StateManager
from logger import DialogueLogger
from config import settings

# Tạo ứng dụng FastAPI
app = FastAPI(
    title="Dịch vụ backend Thị trấn Cyber",
    description="Hệ thống hội thoại NPC AI dựa trên HelloAgents",
    version="1.0.0"
)

# Cấu hình CORS, cho phép frontend Godot truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Môi trường sản xuất nên giới hạn tên miền cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo các trình quản lý
agent_manager = NPCAgentManager()
relationship_manager = RelationshipManager()
state_manager = StateManager()
dialogue_logger = DialogueLogger()

@app.on_event("startup")
async def startup_event():
    """Khởi tạo khi ứng dụng khởi động"""
    print("=" * 60)
    print("🎮 Dịch vụ backend Thị trấn Cyber đang khởi động...")
    print("=" * 60)

    # Khởi tạo NPC Agents
    agent_manager.initialize_npcs()
    print("✅ NPC Agents đã được khởi tạo")

    # Khởi tạo trình quản lý trạng thái
    state_manager.initialize_npcs()
    print("✅ Trình quản lý trạng thái đã được khởi tạo")

@app.get("/")
async def root():
    """Kiểm tra tình trạng hoạt động"""
    return {
        "status": "running",
        "message": "Dịch vụ backend Thị trấn Cyber đang chạy",
        "version": "1.0.0",
        "npcs": state_manager.get_npc_count()
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
```

Tệp chương trình chính này định nghĩa cấu trúc cơ bản của ứng dụng FastAPI, cấu hình middleware CORS để cho phép yêu cầu cross-origin, và khởi tạo các trình quản lý khi khởi động. Tiếp theo chúng ta sẽ hiện thực các tuyến API cụ thể.

### 15.4.2 Thiết kế tuyến API

Backend của Thị trấn Cyber cần cung cấp một số endpoint API cốt lõi để xử lý yêu cầu từ frontend Godot. Chúng ta thêm các tuyến này vào `main.py`.

<strong>Lấy trạng thái NPC</strong>

API này trả về trạng thái hiện tại của tất cả NPC, bao gồm vị trí, có đang bận hay không, v.v.:

```python
from models import NPCStatusResponse

@app.get("/npcs/status", response_model=NPCStatusResponse)
async def get_npc_status():
    """Lấy trạng thái của tất cả NPC"""
    npcs = state_manager.get_all_npc_states()
    return {"npcs": npcs}

@app.get("/npcs/{npc_id}/status")
async def get_single_npc_status(npc_id: str):
    """Lấy trạng thái của một NPC"""
    npc = state_manager.get_npc_state(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC {npc_id} không tồn tại")
    return npc
```

<strong>Endpoint hội thoại</strong>

Đây là API cốt lõi nhất, xử lý hội thoại giữa người chơi và NPC:

```python
from models import DialogueRequest, DialogueResponse

@app.post("/dialogue", response_model=DialogueResponse)
async def dialogue(request: DialogueRequest):
    """Xử lý hội thoại giữa người chơi và NPC"""
    # 1. Kiểm tra NPC có tồn tại hay không
    if not agent_manager.has_npc(request.npc_id):
        raise HTTPException(status_code=404, detail=f"NPC {request.npc_id} không tồn tại")

    # 2. Kiểm tra NPC có đang bận hay không
    if state_manager.is_npc_busy(request.npc_id):
        raise HTTPException(status_code=409, detail=f"NPC {request.npc_id} đang trò chuyện với người chơi khác")

    # 3. Đánh dấu NPC ở trạng thái bận
    state_manager.set_npc_busy(request.npc_id, True)

    try:
        # 4. Lấy độ thiện cảm hiện tại
        affinity_info = relationship_manager.get_affinity(
            request.npc_id,
            request.player_name
        )

        # 5. Gọi Agent sinh phản hồi
        agent = agent_manager.get_agent(request.npc_id, affinity_info["level"])
        reply = agent.run(request.player_message)

        # 6. Cập nhật độ thiện cảm
        new_affinity = relationship_manager.update_affinity(
            request.npc_id,
            request.player_name,
            request.player_message,
            reply
        )

        # 7. Ghi log
        dialogue_logger.log_dialogue(
            npc_id=request.npc_id,
            player_name=request.player_name,
            player_message=request.player_message,
            npc_reply=reply,
            affinity_info=new_affinity
        )

        # 8. Trả về phản hồi
        return DialogueResponse(
            npc_reply=reply,
            affinity_level=new_affinity["level"],
            affinity_score=new_affinity["score"]
        )

    except Exception as e:
        dialogue_logger.log_error(f"Xử lý hội thoại thất bại: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Xử lý hội thoại thất bại: {str(e)}")

    finally:
        # 9. Giải phóng trạng thái NPC
        state_manager.set_npc_busy(request.npc_id, False)
```

<strong>Truy vấn độ thiện cảm</strong>

API này cho phép truy vấn độ thiện cảm giữa người chơi và NPC:

```python
from models import AffinityInfo

@app.get("/affinity/{npc_id}/{player_name}", response_model=AffinityInfo)
async def get_affinity(npc_id: str, player_name: str):
    """Lấy độ thiện cảm giữa người chơi và NPC"""
    if not agent_manager.has_npc(npc_id):
        raise HTTPException(status_code=404, detail=f"NPC {npc_id} không tồn tại")

    affinity = relationship_manager.get_affinity(npc_id, player_name)
    return affinity
```

Quy trình gọi tuyến API được minh họa như Hình 15.11:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-11.png" alt="" width="85%"/>
  <p>Hình 15.11 Quy trình gọi API</p>
</div>


### 15.4.3 Quản lý trạng thái và hệ thống log

<strong>Trình quản lý trạng thái</strong>

Trình quản lý trạng thái phụ trách theo dõi trạng thái hiện tại của mỗi NPC, bao gồm vị trí, có đang bận hay không, hành động hiện tại, v.v. Điều này rất quan trọng để ngăn ngừa vấn đề đồng thời, ví dụ tránh việc một NPC đồng thời trò chuyện với nhiều người chơi.

```python
# state_manager.py
from typing import Dict, List, Optional
from datetime import datetime

class StateManager:
    """Trình quản lý trạng thái NPC"""

    def __init__(self):
        self.npc_states: Dict[str, dict] = {}

    def initialize_npcs(self):
        """Khởi tạo trạng thái NPC"""
        npcs = [
            {
                "npc_id": "zhang_san",
                "name": "张三",
                "role": "Kỹ sư Python",
                "position": {"x": 300, "y": 200}
            },
            {
                "npc_id": "li_si",
                "name": "李四",
                "role": "Quản lý sản phẩm",
                "position": {"x": 500, "y": 200}
            },
            {
                "npc_id": "wang_wu",
                "name": "王五",
                "role": "Nhà thiết kế UI",
                "position": {"x": 700, "y": 200}
            }
        ]

        for npc in npcs:
            self.npc_states[npc["npc_id"]] = {
                **npc,
                "is_busy": False,
                "current_action": "idle",
                "last_interaction": None
            }

    def get_npc_state(self, npc_id: str) -> Optional[dict]:
        """Lấy trạng thái NPC"""
        return self.npc_states.get(npc_id)

    def get_all_npc_states(self) -> List[dict]:
        """Lấy trạng thái của tất cả NPC"""
        return list(self.npc_states.values())

    def is_npc_busy(self, npc_id: str) -> bool:
        """Kiểm tra NPC có đang bận hay không"""
        npc = self.npc_states.get(npc_id)
        return npc["is_busy"] if npc else False

    def set_npc_busy(self, npc_id: str, busy: bool):
        """Đặt trạng thái bận cho NPC"""
        if npc_id in self.npc_states:
            self.npc_states[npc_id]["is_busy"] = busy
            if busy:
                self.npc_states[npc_id]["last_interaction"] = datetime.now().isoformat()

    def get_npc_count(self) -> int:
        """Lấy số lượng NPC"""
        return len(self.npc_states)
```

<strong>Hệ thống log</strong>

Hệ thống log hiện thực hai đầu ra: console và tệp. Như vậy vừa thuận tiện xem thời gian thực, vừa lưu được lịch sử.

```python
# logger.py
import logging
from datetime import datetime
from pathlib import Path

class DialogueLogger:
    """Bộ ghi log hội thoại"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Tạo tên tệp log (theo ngày)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"dialogue_{today}.log"

        # Cấu hình log
        self.logger = logging.getLogger("DialogueLogger")
        self.logger.setLevel(logging.INFO)

        # Bộ xử lý console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # Bộ xử lý tệp
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Thêm các bộ xử lý
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def log_dialogue(self, npc_id: str, player_name: str,
                    player_message: str, npc_reply: str,
                    affinity_info: dict):
        """Ghi log hội thoại"""
        log_message = f"""
{'='*60}
NPC: {npc_id}
Người chơi: {player_name}
Tin nhắn người chơi: {player_message}
Phản hồi NPC: {npc_reply}
Độ thiện cảm: {affinity_info['level']} ({affinity_info['score']}/100)
Số lần tương tác: {affinity_info['interaction_count']}
{'='*60}
"""
        self.logger.info(log_message)

    def log_error(self, error_message: str):
        """Ghi log lỗi"""
        self.logger.error(error_message)
```

Hệ thống log này sẽ hiển thị nội dung hội thoại theo thời gian thực trên console, đồng thời lưu vào tệp. Log của mỗi ngày được lưu trong một tệp riêng, thuận tiện cho việc phân tích sau này.

### 15.4.4 Hiểu hệ thống scene của Godot

Trước khi bắt đầu xây dựng scene game, chúng ta cần hiểu khái niệm cốt lõi của Godot — scene và node. Đây là điểm khác biệt lớn nhất giữa Godot và các game engine khác, cũng là một trong những đặc tính mạnh mẽ nhất của nó.

<strong>Node là gì?</strong>

Node là khối xây dựng cơ bản nhất trong Godot. Bạn có thể hình dung node như những viên gạch Lego, mỗi node đều có chức năng riêng. Ví dụ, node Sprite2D dùng để hiển thị hình ảnh, node AudioStreamPlayer dùng để phát âm thanh, node CharacterBody2D dùng để xử lý chuyển động vật lý của nhân vật. Godot cung cấp hàng trăm loại node khác nhau, mỗi loại đều tập trung làm tốt một việc.

Giữa các node có thể hình thành quan hệ cha-con, tạo nên cấu trúc cây. Node cha có thể ảnh hưởng đến node con, ví dụ di chuyển node cha sẽ đồng thời di chuyển tất cả node con, ẩn node cha sẽ đồng thời ẩn tất cả node con. Quan hệ phân cấp này giúp chúng ta dễ dàng tổ chức và quản lý các đối tượng game phức tạp.

<strong>Scene là gì?</strong>

Scene là một tập hợp các node, được lưu trong một tệp `.tscn`. Bạn có thể hiểu scene như một “prefab”. Ví dụ, chúng ta có thể tạo một scene “Player”, bao gồm sprite của nhân vật, collider, âm thanh và tất cả các node liên quan. Sau đó sử dụng scene này nhiều lần trong game, mỗi lần sử dụng sẽ tạo một instance độc lập.

Sức mạnh của scene nằm ở tính tái sử dụng và tính mô-đun. Chúng ta có thể khởi tạo instance của scene này trong một scene khác, tạo thành cấu trúc lồng nhau. Ví dụ, scene chính có thể chứa scene người chơi, nhiều scene NPC và scene UI. Sửa đổi scene NPC sẽ tự động ảnh hưởng đến tất cả instance NPC, điều này đơn giản hóa đáng kể việc phát triển và bảo trì.

<strong>Một ví dụ đơn giản</strong>

Hãy dùng một ví dụ đơn giản để hiểu scene và node. Giả sử chúng ta muốn tạo một scene “Player”:

```
Player (CharacterBody2D)  ← Node gốc, phụ trách di chuyển vật lý
├─ AnimatedSprite2D       ← Node con, hiển thị hoạt ảnh nhân vật
├─ CollisionShape2D       ← Node con, định nghĩa hình dạng va chạm
└─ Camera2D               ← Node con, camera bám theo người chơi
```

Scene này chứa 4 node, tạo thành cấu trúc cây. CharacterBody2D là node gốc, ba node còn lại là node con của nó. Chúng ta có thể thêm script cho mỗi node để điều khiển hành vi của nó, cũng có thể thêm script cho node gốc để điều phối tất cả node con.

Khi chúng ta khởi tạo instance của scene Player này trong scene chính, Godot sẽ tạo một bản sao của toàn bộ cây node. Chúng ta có thể tạo nhiều instance người chơi, mỗi instance đều độc lập, có vị trí, trạng thái và hành vi riêng.

<strong>Ưu điểm của việc khởi tạo instance scene</strong>

Trong Thị trấn Cyber, chúng ta có ba NPC: Trương Tam, Lý Tứ và Vương Ngũ. Nếu không sử dụng hệ thống scene, chúng ta cần tạo node, thiết lập thuộc tính và viết script riêng cho từng NPC, điều này dẫn đến lượng lớn công việc lặp lại. Còn khi dùng hệ thống scene, chúng ta chỉ cần tạo một scene NPC chung, sau đó khởi tạo instance ba lần, đặt tên và thông tin vai trò khác nhau thông qua tham số script.

Lợi ích của thiết kế này là: nếu chúng ta muốn thêm một chức năng mới cho tất cả NPC (như hiển thị bong bóng hội thoại trên đầu), chỉ cần sửa scene NPC, tất cả instance sẽ tự động có chức năng này.

## 15.5 Xây dựng scene game Godot

<strong>Vì sao chọn Godot làm game engine?</strong>

Trong nhiều game engine, chúng ta chọn Godot 4.5 làm engine frontend, chủ yếu dựa trên các cân nhắc sau:

<strong>(1) Godot có lợi thế tự nhiên trong phát triển game 2D</strong>. Thị trấn Cyber là một game pixel 2D góc nhìn từ trên xuống, engine 2D của Godot rất trưởng thành, cung cấp các loại node được thiết kế riêng cho game 2D như TileMap, AnimatedSprite2D, CharacterBody2D, hiệu quả phát triển cao hơn hẳn các engine như Unity. Hệ thống scene của Godot cho phép chúng ta đóng gói người chơi, NPC, UI thành các scene độc lập, sau đó khởi tạo instance trong scene chính; thiết kế dạng component này rất phù hợp với nhu cầu của chúng ta.

<strong>(2) Godot hoàn toàn mã nguồn mở và miễn phí</strong>. Godot sử dụng giấy phép MIT, không có bất kỳ chi phí bản quyền hay chia sẻ doanh thu nào, rất thân thiện với dự án giảng dạy và dự án mã nguồn mở. Bạn có thể tự do sửa đổi mã nguồn engine, cũng có thể thương mại hóa game mà không lo vấn đề cấp phép. Trong khi đó, Unity tuy mạnh mẽ về tính năng nhưng đã đưa ra chính sách phí theo thời gian chạy vào năm 2024, gây ra tranh cãi rộng rãi trong cộng đồng nhà phát triển.

<strong>(3) Chi phí học Godot cực thấp</strong>. Godot sử dụng GDScript làm ngôn ngữ script chính, đây là ngôn ngữ kiểu động tương tự Python, cú pháp ngắn gọn dễ hiểu, đường cong học tập rất thoải mái. Với những độc giả đã quen Python, học GDScript gần như không có rào cản — khai báo biến, định nghĩa hàm, luồng điều khiển và các cú pháp khác đều rất giống Python, bạn thậm chí có thể bắt đầu viết script game trong vài giờ. Cấu trúc cây node của Godot cũng rất trực quan, bạn có thể thấy rõ quan hệ phân cấp của scene trong editor, điều này rất thân thiện với người mới.

<strong>(4) Tích hợp Godot với backend Python rất đơn giản</strong>. Godot tích hợp sẵn node HTTPRequest, có thể dễ dàng giao tiếp HTTP với backend FastAPI. Chúng ta chỉ cần tạo một script API client, đóng gói tất cả lệnh gọi API, là có thể gọi năng lực AI của backend trong game. Kiến trúc tách biệt frontend-backend này cho phép chúng ta phát triển và kiểm thử độc lập logic game và logic AI, nâng cao đáng kể hiệu quả phát triển.

Tất nhiên, Godot cũng có một số hạn chế. Ví dụ, năng lực 3D của Godot còn khoảng cách so với Unreal Engine và Unity, nếu bạn muốn phát triển game 3D quy mô lớn, có thể cần cân nhắc engine khác. Nhưng với game 2D, game độc lập và dự án giảng dạy, Godot là một lựa chọn rất xuất sắc.

### 15.5.1 Thiết kế scene và tổ chức tài nguyên

Sau khi đã hiểu hệ thống scene của Godot, hãy xem thiết kế scene của Thị trấn Cyber. Toàn bộ game gồm bốn scene cốt lõi: Main (scene chính), Player (người chơi), NPC (nhân vật không phải người chơi) và DialogueUI (giao diện hội thoại). Mỗi scene là một mô-đun độc lập, có thể chỉnh sửa và kiểm thử riêng, sau đó kết hợp lại thành game hoàn chỉnh.

Việc tổ chức scene của Thị trấn Cyber áp dụng thiết kế mô-đun. Trước tiên chúng ta tạo ba scene cơ bản: Player (người chơi), NPC (nhân vật không phải người chơi) và DialogueUI (giao diện hội thoại). Sau đó trong Main (scene chính), chúng ta khởi tạo instance và kết hợp các scene này. Điều đặc biệt đáng chú ý là ba NPC (Trương Tam, Lý Tứ, Vương Ngũ) đều là instance của cùng một scene NPC, chỉ khác nhau ở thông tin nhân vật được đặt qua tham số script.

Trước tiên hãy xem cấu trúc của bốn scene cốt lõi, như Hình 15.12:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-12.png" alt="" width="85%"/>
  <p>Hình 15.12 Bốn scene cốt lõi của Thị trấn Cyber</p>
</div>


Hình này trình bày bốn scene độc lập và cấu trúc bên trong của chúng. <strong>Scene 1 (Main)</strong> là scene chính, nó chứa hình nền (Sprite2D), instance người chơi, node tổ chức NPCs (bên dưới có ba instance NPC), instance giao diện hội thoại, node tổ chức tường và nhạc nền. Lưu ý, Player, NPC_Zhang, NPC_Li, NPC_Wang và DialogueUI ở đây đều là instance scene, không phải node thông thường. <strong>Scene 2 (Player)</strong> định nghĩa cấu trúc nhân vật người chơi, bao gồm hoạt ảnh, va chạm, camera và hai node âm thanh. <strong>Scene 3 (NPC)</strong> là một mẫu chung, Trương Tam, Lý Tứ, Vương Ngũ đều là instance của scene này, bao gồm va chạm, hoạt ảnh, vùng tương tác và hai nhãn. <strong>Scene 4 (DialogueUI)</strong> là một node CanvasLayer, bao gồm Panel và các phần tử UI khác nhau.

Quá trình khởi tạo instance scene có thể hiểu như sau: chúng ta tạo tệp scene NPC.tscn trong editor Godot, định nghĩa cấu trúc node của NPC. Sau đó trong scene Main, chúng ta “khởi tạo instance” scene NPC này ba lần, tạo ra ba bản sao độc lập, lần lượt đặt tên NPC_Zhang, NPC_Li và NPC_Wang. Mỗi bản sao có vị trí và trạng thái riêng, nhưng chúng chia sẻ cùng cấu trúc node. Nếu chúng ta sửa NPC.tscn, ví dụ thêm một node âm thanh mới cho NPC, thì cả ba instance đều tự động có âm thanh này.

Các bước tạo những scene này trong Godot như sau:

1. <strong>Tạo scene Player</strong>: Tạo scene mới, chọn CharacterBody2D làm node gốc, thêm các node con AnimatedSprite2D, CollisionShape2D, Camera2D, InteractSound và RunningSound, lưu thành Player.tscn.

2. <strong>Tạo scene NPC</strong>: Tạo scene mới, chọn CharacterBody2D làm node gốc, thêm các node con CollisionShape2D, AnimatedSprite2D, InteractionArea (Area2D, bên dưới có CollisionShape2D), NameLabel và DialogueLabel, lưu thành NPC.tscn.

3. <strong>Tạo scene DialogueUI</strong>: Tạo scene mới, chọn CanvasLayer làm node gốc, thêm node con Panel, dưới Panel thêm NPCName, NPCTitle, DialogueText (RichTextLabel), PlayerInput (LineEdit), SendButton và CloseButton, lưu thành DialogueUI.tscn.

4. <strong>Tạo scene Main</strong>: Tạo scene mới, chọn Node2D làm node gốc, thêm Background (Sprite2D) làm hình nền, dưới Background thêm trang trí cá voi nhỏ, sau đó khởi tạo instance scene Player, tạo node NPCs và khởi tạo instance scene NPC ba lần bên dưới nó, khởi tạo instance scene DialogueUI, tạo node Walls để tổ chức va chạm tường, cuối cùng thêm AudioStreamPlayer phát nhạc nền.

Ưu điểm của cách tổ chức scene này là: mỗi scene đều độc lập, có thể kiểm thử riêng; NPC dùng instance của cùng một scene, sửa một lần là ảnh hưởng đến tất cả NPC; các scene giao tiếp qua signal, độ ghép nối thấp, dễ bảo trì và mở rộng.

### 15.5.2 Hiện thực điều khiển người chơi

Nhân vật người chơi là một trong những yếu tố quan trọng nhất trong game. Chúng ta cần hiện thực điều khiển di chuyển bằng WASD, chuyển đổi hoạt ảnh, phát hiện va chạm, tương tác với NPC và hệ thống âm thanh.

Cấu trúc scene người chơi bao gồm: một CharacterBody2D làm node gốc, phụ trách di chuyển vật lý và va chạm; một AnimatedSprite2D hiển thị hoạt ảnh nhân vật; một CollisionShape2D định nghĩa hình dạng va chạm; một Camera2D bám theo người chơi; hai AudioStreamPlayer lần lượt phát âm thanh tương tác và âm thanh bước chân.

Script điều khiển người chơi `player.gd` hiện thực logic di chuyển, tương tác và âm thanh:

```python
extends CharacterBody2D

# Tốc độ di chuyển
@export var speed: float = 200.0

# NPC hiện có thể tương tác
var nearby_npc: Node = null

# Trạng thái tương tác (vô hiệu hóa di chuyển khi tương tác)
var is_interacting: bool = false

# Tham chiếu node
@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var camera: Camera2D = $Camera2D

# Tham chiếu âm thanh
@onready var interact_sound: AudioStreamPlayer = null
@onready var running_sound: AudioStreamPlayer = null

# Trạng thái âm thanh bước chân
var is_playing_running_sound: bool = false

func _ready():
    # Thêm vào nhóm player (quan trọng! NPC cần nhận diện người chơi qua nhóm này)
    add_to_group("player")

    # Lấy các node âm thanh (tùy chọn, nếu không tồn tại cũng không báo lỗi)
    interact_sound = get_node_or_null("InteractSound")
    running_sound = get_node_or_null("RunningSound")

    # Bật camera
    camera.enabled = true

    # Phát hoạt ảnh mặc định
    if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
        animated_sprite.play("idle")

func _physics_process(_delta: float):
    # Nếu đang tương tác, vô hiệu hóa di chuyển
    if is_interacting:
        velocity = Vector2.ZERO
        move_and_slide()
        # Phát hoạt ảnh idle
        if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")
        # Dừng âm thanh bước chân
        stop_running_sound()
        return

    # Lấy hướng đầu vào
    var input_direction = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")

    # Đặt vận tốc
    velocity = input_direction * speed

    # Di chuyển
    move_and_slide()

    # Cập nhật hoạt ảnh và hướng nhìn
    update_animation(input_direction)

    # Cập nhật âm thanh bước chân
    update_running_sound(input_direction)

func update_animation(direction: Vector2):
    """Cập nhật hoạt ảnh nhân vật (hỗ trợ 4 hướng)"""
    if animated_sprite.sprite_frames == null:
        return

    # Phát hoạt ảnh theo hướng di chuyển
    if direction.length() > 0:
        # Đang di chuyển - xác định hướng chính
        if abs(direction.x) > abs(direction.y):
            # Di chuyển trái phải
            if direction.x > 0:
                # Sang phải
                if animated_sprite.sprite_frames.has_animation("walk_right"):
                    animated_sprite.play("walk_right")
                    animated_sprite.flip_h = false
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
                    animated_sprite.flip_h = false
            else:
                # Sang trái
                if animated_sprite.sprite_frames.has_animation("walk_left"):
                    animated_sprite.play("walk_left")
                    animated_sprite.flip_h = false
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
                    animated_sprite.flip_h = true
        else:
            # Di chuyển lên xuống
            if direction.y > 0:
                # Đi xuống
                if animated_sprite.sprite_frames.has_animation("walk_down"):
                    animated_sprite.play("walk_down")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
            else:
                # Đi lên
                if animated_sprite.sprite_frames.has_animation("walk_up"):
                    animated_sprite.play("walk_up")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
    else:
        # Đứng yên
        if animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")

func _input(event: InputEvent):
    # Nhấn phím E để tương tác với NPC
    if event is InputEventKey:
        if event.pressed and not event.echo:
            if event.keycode == KEY_E or event.keycode == KEY_ENTER:
                if nearby_npc != null:
                    interact_with_npc()

func interact_with_npc():
    """Tương tác với NPC gần đó"""
    if nearby_npc != null:
        # Phát âm thanh tương tác
        if interact_sound:
            interact_sound.play()

        # Gửi signal cho hệ thống hội thoại
        get_tree().call_group("dialogue_system", "start_dialogue", nearby_npc.npc_name)

func set_nearby_npc(npc: Node):
    """Đặt NPC gần đó"""
    nearby_npc = npc

func set_interacting(interacting: bool):
    """Đặt trạng thái tương tác"""
    is_interacting = interacting
    if interacting:
        # Dừng âm thanh bước chân
        stop_running_sound()

func update_running_sound(direction: Vector2):
    """Cập nhật âm thanh bước chân"""
    if running_sound == null:
        return

    # Nếu đang di chuyển
    if direction.length() > 0:
        # Nếu âm thanh chưa phát, bắt đầu phát
        if not is_playing_running_sound:
            running_sound.play()
            is_playing_running_sound = true
    else:
        # Nếu dừng di chuyển, dừng âm thanh
        stop_running_sound()

func stop_running_sound():
    """Dừng âm thanh bước chân"""
    if running_sound and is_playing_running_sound:
        running_sound.stop()
        is_playing_running_sound = false
```

Script này hiện thực đầy đủ việc điều khiển người chơi. Người chơi dùng phím WASD (hoặc phím mũi tên) để di chuyển, nhân vật sẽ phát hoạt ảnh 4 hướng tương ứng theo hướng di chuyển (walk_up/down/left/right). Khi người chơi đến gần NPC, NPC sẽ gọi `set_nearby_npc()` để đặt mình làm đối tượng có thể tương tác, người chơi chỉ cần nhấn phím E là có thể kích hoạt tương tác. Khi tương tác sẽ phát âm thanh, và thông qua `call_group()` thông báo cho hệ thống hội thoại bắt đầu trò chuyện. Trong thời gian hội thoại, `set_interacting(true)` sẽ vô hiệu hóa di chuyển của người chơi, sau khi hội thoại kết thúc sẽ khôi phục di chuyển. Âm thanh bước chân sẽ tự động phát khi người chơi di chuyển, tự động dừng khi dừng lại.

### 15.5.3 Hành vi và tương tác của NPC

NPC cần hiện thực ba chức năng cốt lõi: tuần tra ngẫu nhiên trong scene, phản hồi tương tác của người chơi, hiển thị bong bóng hội thoại. Chúng ta sử dụng Area2D để phát hiện người chơi có đến gần NPC hay không, khi người chơi bước vào vùng tương tác sẽ thông báo cho người chơi, người chơi nhấn phím E là có thể bắt đầu hội thoại.

Cấu trúc scene NPC bao gồm: CharacterBody2D làm node gốc; CollisionShape2D định nghĩa hình dạng va chạm của NPC; AnimatedSprite2D hiển thị hoạt ảnh NPC; InteractionArea (Area2D) phát hiện người chơi bước vào vùng tương tác, bên dưới có CollisionShape2D định nghĩa vùng tương tác; NameLabel hiển thị tên NPC; DialogueLabel hiển thị bong bóng hội thoại.

Script NPC `npc.gd` hiện thực logic tuần tra, tương tác và bong bóng hội thoại:

```python
extends CharacterBody2D

# Thông tin NPC
@export var npc_name: String = "张三"
@export var npc_title: String = "Kỹ sư Python"

# Cấu hình ngoại hình NPC
@export var sprite_frames: SpriteFrames = null  # Tài nguyên sprite frame tùy chỉnh

# Cấu hình di chuyển NPC
@export var move_speed: float = 50.0  # Tốc độ di chuyển
@export var wander_enabled: bool = true  # Có bật tuần tra hay không
@export var wander_range: float = 200.0  # Phạm vi tuần tra
@export var wander_interval_min: float = 3.0  # Khoảng tuần tra tối thiểu (giây)
@export var wander_interval_max: float = 8.0  # Khoảng tuần tra tối đa (giây)

# Nội dung hội thoại hiện tại (lấy từ backend)
var current_dialogue: String = ""

# Tham chiếu node
@onready var animated_sprite: AnimatedSprite2D = $AnimatedSprite2D
@onready var interaction_area: Area2D = $InteractionArea
@onready var name_label: Label = $NameLabel
@onready var dialogue_label: Label = $DialogueLabel

# Tham chiếu người chơi
var player: Node = null

# Biến liên quan đến tuần tra
var wander_target: Vector2 = Vector2.ZERO  # Vị trí mục tiêu tuần tra
var wander_timer: float = 0.0  # Bộ đếm thời gian tuần tra
var is_wandering: bool = false  # Có đang tuần tra hay không
var is_interacting: bool = false  # Có đang tương tác với người chơi hay không
var spawn_position: Vector2 = Vector2.ZERO  # Vị trí xuất phát

func _ready():
    # Thêm vào nhóm npcs
    add_to_group("npcs")

    # Đặt tên NPC
    name_label.text = npc_name

    # Kết nối signal của vùng tương tác
    interaction_area.body_entered.connect(_on_body_entered)
    interaction_area.body_exited.connect(_on_body_exited)

    # Khởi tạo nhãn hội thoại
    dialogue_label.text = ""
    dialogue_label.visible = false

    # Đặt sprite frame tùy chỉnh (nếu có)
    if sprite_frames != null:
        animated_sprite.sprite_frames = sprite_frames

    # Phát hoạt ảnh mặc định
    if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
        animated_sprite.play("idle")

    # Ghi lại vị trí xuất phát
    spawn_position = global_position

    # Khởi tạo bộ đếm thời gian tuần tra
    if wander_enabled:
        wander_timer = randf_range(wander_interval_min, wander_interval_max)
        choose_new_wander_target()

func _on_body_entered(body: Node2D):
    """Người chơi bước vào vùng tương tác"""
    if body.is_in_group("player"):
        player = body

        if player.has_method("set_nearby_npc"):
            player.set_nearby_npc(self)

func _on_body_exited(body: Node2D):
    """Người chơi rời khỏi vùng tương tác"""
    if body.is_in_group("player"):
        if player != null and player.has_method("set_nearby_npc"):
            player.set_nearby_npc(null)
        player = null

func update_dialogue(dialogue: String):
    """Cập nhật nội dung hội thoại của NPC"""
    current_dialogue = dialogue
    dialogue_label.text = dialogue
    dialogue_label.visible = true

    # Ẩn hội thoại sau 10 giây
    await get_tree().create_timer(10.0).timeout
    dialogue_label.visible = false

func _physics_process(delta: float):
    """Cập nhật vật lý - xử lý di chuyển"""
    # Nếu đang tương tác với người chơi, dừng di chuyển
    if is_interacting:
        velocity = Vector2.ZERO
        move_and_slide()
        # Phát hoạt ảnh idle
        if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")
        return

    # Nếu không bật tuần tra, không di chuyển
    if not wander_enabled:
        return

    # Cập nhật bộ đếm thời gian tuần tra
    wander_timer -= delta

    # Nếu bộ đếm kết thúc, chọn mục tiêu mới và bắt đầu di chuyển
    if wander_timer <= 0:
        choose_new_wander_target()
        wander_timer = randf_range(wander_interval_min, wander_interval_max)

    # Nếu đang tuần tra, di chuyển đến mục tiêu
    if is_wandering:
        # Kiểm tra đã đến mục tiêu chưa
        if global_position.distance_to(wander_target) < 10:
            # Đã đến mục tiêu, dừng di chuyển
            is_wandering = false
            velocity = Vector2.ZERO
            move_and_slide()
            # Phát hoạt ảnh idle
            if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
                animated_sprite.play("idle")
        else:
            # Tiếp tục di chuyển đến mục tiêu
            var direction = (wander_target - global_position).normalized()
            velocity = direction * move_speed
            move_and_slide()
            # Cập nhật hoạt ảnh
            update_animation(direction)
    else:
        # Dừng di chuyển
        velocity = Vector2.ZERO
        move_and_slide()
        # Phát hoạt ảnh idle
        if animated_sprite.sprite_frames != null and animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")

func choose_new_wander_target():
    """Chọn mục tiêu tuần tra mới"""
    # Chọn ngẫu nhiên một điểm gần vị trí xuất phát
    var offset = Vector2(
        randf_range(-wander_range, wander_range),
        randf_range(-wander_range, wander_range)
    )
    wander_target = spawn_position + offset
    is_wandering = true

func update_animation(direction: Vector2):
    """Cập nhật hoạt ảnh"""
    if animated_sprite.sprite_frames == null:
        return

    if direction.length() > 0:
        # Hoạt ảnh di chuyển
        if abs(direction.x) > abs(direction.y):
            # Di chuyển trái phải
            if direction.x > 0:
                if animated_sprite.sprite_frames.has_animation("walk_right"):
                    animated_sprite.play("walk_right")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
                    animated_sprite.flip_h = false
            else:
                if animated_sprite.sprite_frames.has_animation("walk_left"):
                    animated_sprite.play("walk_left")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
                    animated_sprite.flip_h = true
        else:
            # Di chuyển lên xuống
            if direction.y > 0:
                if animated_sprite.sprite_frames.has_animation("walk_down"):
                    animated_sprite.play("walk_down")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
            else:
                if animated_sprite.sprite_frames.has_animation("walk_up"):
                    animated_sprite.play("walk_up")
                elif animated_sprite.sprite_frames.has_animation("walk"):
                    animated_sprite.play("walk")
    else:
        # Hoạt ảnh đứng yên
        if animated_sprite.sprite_frames.has_animation("idle"):
            animated_sprite.play("idle")

func set_interacting(interacting: bool):
    """Đặt trạng thái tương tác"""
    is_interacting = interacting
```

Script này hiện thực đầy đủ hành vi của NPC. NPC sẽ tuần tra ngẫu nhiên trong phạm vi `wander_range` quanh vị trí xuất phát, cứ mỗi khoảng từ `wander_interval_min` đến `wander_interval_max` giây lại chọn một điểm mục tiêu mới và di chuyển đến đó. Khi di chuyển sẽ phát hoạt ảnh 4 hướng (walk_up/down/left/right), khi đến mục tiêu sẽ dừng lại và phát hoạt ảnh idle. Khi người chơi bước vào InteractionArea, NPC sẽ gọi phương thức `set_nearby_npc(self)` của người chơi, đặt mình làm đối tượng có thể tương tác. Sau khi người chơi nhấn phím E, hệ thống hội thoại sẽ gọi phương thức `set_interacting(true)` của NPC, NPC dừng di chuyển. Sau khi hội thoại kết thúc sẽ gọi `set_interacting(false)`, NPC tiếp tục tuần tra. Scene chính sẽ định kỳ gọi phương thức `update_dialogue()` để cập nhật bong bóng hội thoại của NPC, hiển thị nội dung hội thoại tự chủ giữa các NPC.

## 15.6 Hiện thực giao tiếp frontend-backend

### 15.6.1 Đóng gói API client

Frontend Godot cần giao tiếp HTTP với backend FastAPI. Chúng ta tạo một script API client `api_client.gd`, đóng gói tất cả lệnh gọi API, và đặt nó thành AutoLoad (tự động tải) singleton, để các script khác có thể sử dụng thuận tiện.

API client sử dụng node HTTPRequest của Godot để gửi yêu cầu HTTP. HTTPRequest là một node bất đồng bộ, sau khi gửi yêu cầu sẽ không chặn game, mà thông báo hoàn thành yêu cầu qua signal. Như vậy có thể đảm bảo độ mượt của game, ngay cả khi độ trễ mạng cao cũng không bị giật. Chúng ta sử dụng cơ chế signal để thông báo phản hồi API cho các script khác, thay vì dùng await, như vậy nhiều script có thể cùng lắng nghe một phản hồi API.

```python
# api_client.gd
extends Node

# Định nghĩa signal
signal chat_response_received(npc_name: String, message: String)
signal chat_error(error_message: String)
signal npc_status_received(dialogues: Dictionary)
signal npc_list_received(npcs: Array)

# Node yêu cầu HTTP
var http_chat: HTTPRequest
var http_status: HTTPRequest
var http_npcs: HTTPRequest

func _ready():
    # Tạo các node yêu cầu HTTP
    http_chat = HTTPRequest.new()
    http_status = HTTPRequest.new()
    http_npcs = HTTPRequest.new()

    add_child(http_chat)
    add_child(http_status)
    add_child(http_npcs)

    # Kết nối signal
    http_chat.request_completed.connect(_on_chat_request_completed)
    http_status.request_completed.connect(_on_status_request_completed)
    http_npcs.request_completed.connect(_on_npcs_request_completed)

# ==================== API hội thoại ====================
func send_chat(npc_name: String, message: String) -> void:
    """Gửi yêu cầu hội thoại"""
    var data = {
        "npc_name": npc_name,
        "message": message
    }

    var json_string = JSON.stringify(data)
    var headers = ["Content-Type: application/json"]

    var error = http_chat.request(
        Config.API_CHAT,
        headers,
        HTTPClient.METHOD_POST,
        json_string
    )

    if error != OK:
        print("[ERROR] Gửi yêu cầu hội thoại thất bại: ", error)
        chat_error.emit("Yêu cầu mạng thất bại")

func _on_chat_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    """Xử lý phản hồi hội thoại"""
    if response_code != 200:
        print("[ERROR] Yêu cầu hội thoại thất bại: HTTP ", response_code)
        chat_error.emit("Lỗi máy chủ: " + str(response_code))
        return

    var json = JSON.new()
    var parse_result = json.parse(body.get_string_from_utf8())

    if parse_result != OK:
        print("[ERROR] Phân tích phản hồi thất bại")
        chat_error.emit("Phân tích phản hồi thất bại")
        return

    var response = json.data

    if response.has("success") and response["success"]:
        var npc_name = response["npc_name"]
        var msg = response["message"]
        print("[INFO] Đã nhận phản hồi NPC: ", npc_name, " -> ", msg)
        chat_response_received.emit(npc_name, msg)
    else:
        chat_error.emit("Hội thoại thất bại")

# ==================== API trạng thái NPC ====================
func get_npc_status() -> void:
    """Lấy trạng thái NPC"""
    # Kiểm tra xem có đang xử lý yêu cầu hay không
    if http_status.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
        print("[WARN] Yêu cầu trạng thái NPC đang được xử lý, bỏ qua yêu cầu này")
        return

    var error = http_status.request(Config.API_NPC_STATUS)

    if error != OK:
        print("[ERROR] Lấy trạng thái NPC thất bại: ", error)

func _on_status_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    """Xử lý phản hồi trạng thái NPC"""
    if response_code != 200:
        print("[ERROR] Yêu cầu trạng thái NPC thất bại: HTTP ", response_code)
        return

    var json = JSON.new()
    var parse_result = json.parse(body.get_string_from_utf8())

    if parse_result != OK:
        print("[ERROR] Phân tích trạng thái NPC thất bại")
        return

    var response = json.data

    if response.has("dialogues"):
        var dialogues = response["dialogues"]
        print("[INFO] Đã nhận cập nhật trạng thái NPC: ", dialogues.size(), " NPC")
        npc_status_received.emit(dialogues)

# ==================== API danh sách NPC ====================
func get_npc_list() -> void:
    """Lấy danh sách NPC"""
    var error = http_npcs.request(Config.API_NPCS)

    if error != OK:
        print("[ERROR] Lấy danh sách NPC thất bại: ", error)

func _on_npcs_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
    """Xử lý phản hồi danh sách NPC"""
    if response_code != 200:
        print("[ERROR] Yêu cầu danh sách NPC thất bại: HTTP ", response_code)
        return

    var json = JSON.new()
    var parse_result = json.parse(body.get_string_from_utf8())

    if parse_result != OK:
        print("[ERROR] Phân tích danh sách NPC thất bại")
        return

    var response = json.data

    if response.has("npcs"):
        var npcs = response["npcs"]
        print("[INFO] Đã nhận danh sách NPC: ", npcs.size(), " NPC")
        npc_list_received.emit(npcs)
```

API client này đóng gói ba chức năng cốt lõi: gửi yêu cầu hội thoại (`send_chat`), lấy trạng thái NPC (`get_npc_status`) và lấy danh sách NPC (`get_npc_list`). Tất cả các yêu cầu HTTP đều bất đồng bộ, thông báo kết quả phản hồi qua signal. Chúng ta tạo node HTTPRequest độc lập cho mỗi API, như vậy có thể gửi đồng thời nhiều yêu cầu mà không ảnh hưởng lẫn nhau. URL của API được lấy từ singleton Config, thuận tiện quản lý tập trung. Hệ thống hội thoại lắng nghe signal `chat_response_received` để nhận phản hồi NPC, scene chính lắng nghe signal `npc_status_received` để cập nhật bong bóng hội thoại của NPC.

### 15.6.2 Hiện thực UI hội thoại

UI hội thoại là giao diện để người chơi tương tác với NPC. Chúng ta cần thiết kế một hộp thoại đơn giản và đẹp mắt, bao gồm tên NPC, chức vụ, hiển thị nội dung hội thoại, ô nhập liệu và các nút.

Cấu trúc của UI hội thoại được minh họa như Hình 15.13:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-13.png" alt="" width="85%"/>
  <p>Hình 15.13 Cấu trúc UI hội thoại</p>
</div>


Thiết kế của UI hội thoại rất đơn giản. DialogueUI là một node CanvasLayer, nghĩa là nó sẽ luôn hiển thị ở lớp trên cùng của màn hình game, không bị các đối tượng game khác che khuất. Panel là nền của hộp thoại, được neo ở cuối màn hình. Dưới Panel đặt trực tiếp 6 phần tử UI: NPCName hiển thị tên NPC, NPCTitle hiển thị chức vụ, DialogueText sử dụng RichTextLabel để hiển thị nội dung hội thoại (hỗ trợ định dạng văn bản phong phú), PlayerInput là LineEdit dùng cho người chơi nhập liệu, SendButton và CloseButton lần lượt dùng để gửi tin nhắn và đóng hộp thoại.

Script UI hội thoại `dialogue_ui.gd` hiện thực logic của giao diện hội thoại:

```python
# dialogue_ui.gd
extends CanvasLayer

# Tham chiếu node UI
@onready var panel = $Panel
@onready var npc_name_label = $Panel/NPCName
@onready var npc_title_label = $Panel/NPCTitle
@onready var dialogue_text = $Panel/DialogueText
@onready var input_field = $Panel/PlayerInput
@onready var send_button = $Panel/SendButton
@onready var close_button = $Panel/CloseButton

# API client
var api_client: Node = null

# NPC của cuộc hội thoại hiện tại
var current_npc_name: String = ""

func _ready():
    # Ẩn hộp thoại khi khởi tạo
    visible = false

    # Kết nối signal của các nút
    send_button.pressed.connect(_on_send_button_pressed)
    close_button.pressed.connect(_on_close_button_pressed)
    input_field.text_submitted.connect(_on_text_submitted)

    # Lấy API client
    api_client = get_node_or_null("/root/APIClient")

func start_dialogue(npc_name: String):
    """Bắt đầu hội thoại với NPC"""
    current_npc_name = npc_name

    # Đặt thông tin NPC
    npc_name_label.text = npc_name
    npc_title_label.text = get_npc_title(npc_name)

    # Xóa nội dung hội thoại
    dialogue_text.clear()
    dialogue_text.append_text("[color=gray]Bắt đầu hội thoại với " + npc_name + "...[/color]\n")

    # Xóa ô nhập liệu
    input_field.text = ""

    # Hiển thị hộp thoại
    show_dialogue()

    # Đưa focus vào ô nhập liệu
    input_field.grab_focus()

func show_dialogue():
    """Hiển thị hộp thoại"""
    visible = true

    # Thông báo người chơi vào trạng thái tương tác (vô hiệu hóa di chuyển)
    var player = get_tree().get_first_node_in_group("player")
    if player and player.has_method("set_interacting"):
        player.set_interacting(true)

func hide_dialogue():
    """Ẩn hộp thoại"""
    visible = false
    current_npc_name = ""

    # Thông báo người chơi thoát trạng thái tương tác (bật di chuyển)
    var player = get_tree().get_first_node_in_group("player")
    if player and player.has_method("set_interacting"):
        player.set_interacting(false)

func _on_send_button_pressed():
    """Nhấn nút gửi"""
    send_message()

func _on_close_button_pressed():
    """Nhấn nút đóng"""
    hide_dialogue()

func _on_text_submitted(_text: String):
    """Nhấn Enter trong ô nhập liệu"""
    send_message()

func send_message():
    """Gửi tin nhắn"""
    var message = input_field.text.strip_edges()

    if message.is_empty():
        return

    if current_npc_name.is_empty():
        return

    # Hiển thị tin nhắn của người chơi
    dialogue_text.append_text("\n[color=cyan]Người chơi:[/color] " + message + "\n")

    # Xóa ô nhập liệu
    input_field.text = ""

    # Vô hiệu hóa nhập liệu
    input_field.editable = false
    send_button.disabled = true

    # Gửi yêu cầu API
    if api_client:
        api_client.send_chat_request(current_npc_name, message)

func on_chat_response_received(npc_name: String, response: String):
    """Nhận phản hồi NPC"""
    if npc_name == current_npc_name:
        # Hiển thị phản hồi NPC
        dialogue_text.append_text("[color=yellow]" + npc_name + ":[/color] " + response + "\n")

        # Bật nhập liệu
        input_field.editable = true
        send_button.disabled = false
        input_field.grab_focus()

func get_npc_title(npc_name: String) -> String:
    """Lấy chức vụ NPC"""
    var titles = {
        "张三": "Kỹ sư Python",
        "李四": "Quản lý sản phẩm",
        "王五": "Nhà thiết kế UI"
    }
    return titles.get(npc_name, "")
```

UI hội thoại này hiện thực đầy đủ chức năng hội thoại. Người chơi có thể nhập tin nhắn và gửi, UI sử dụng phương thức append_text của RichTextLabel để hiển thị nội dung hội thoại, hỗ trợ định dạng văn bản phong phú (màu sắc, in đậm, v.v.). Tất cả các lệnh gọi API đều bất đồng bộ, trong lúc chờ phản hồi sẽ vô hiệu hóa ô nhập liệu, ngăn gửi trùng lặp. Khi hộp thoại hiển thị sẽ thông báo người chơi vào trạng thái tương tác, vô hiệu hóa di chuyển; khi đóng sẽ khôi phục di chuyển.

### 15.6.3 Tích hợp scene chính

Cuối cùng, chúng ta cần tích hợp tất cả các chức năng trong scene chính: điều khiển người chơi, tương tác NPC, UI hội thoại và cập nhật trạng thái NPC. Script scene chính `main.gd` phụ trách điều phối các component này, và định kỳ lấy trạng thái NPC từ backend, cập nhật bong bóng hội thoại của NPC.

```python
# main.gd
extends Node2D

# Tham chiếu node NPC
@onready var npc_zhang: Node2D = $NPCs/NPC_Zhang
@onready var npc_li: Node2D = $NPCs/NPC_Li
@onready var npc_wang: Node2D = $NPCs/NPC_Wang

# API client
var api_client: Node = null

# Bộ đếm thời gian cập nhật trạng thái NPC
var status_update_timer: float = 0.0

func _ready():
    print("[INFO] Khởi tạo scene chính")

    # Lấy API client
    api_client = get_node_or_null("/root/APIClient")
    if api_client:
        api_client.npc_status_received.connect(_on_npc_status_received)

        # Lấy trạng thái NPC một lần ngay lập tức
        api_client.get_npc_status()
    else:
        print("[ERROR] Không tìm thấy API client")

func _process(delta: float):
    # Cập nhật trạng thái NPC định kỳ
    status_update_timer += delta
    if status_update_timer >= Config.NPC_STATUS_UPDATE_INTERVAL:
        status_update_timer = 0.0
        if api_client:
            api_client.get_npc_status()

func _on_npc_status_received(dialogues: Dictionary):
    """Nhận cập nhật trạng thái NPC"""
    print("[INFO] Cập nhật trạng thái NPC: ", dialogues)

    # Cập nhật hội thoại của từng NPC
    for npc_name in dialogues:
        var dialogue = dialogues[npc_name]
        update_npc_dialogue(npc_name, dialogue)

func update_npc_dialogue(npc_name: String, dialogue: String):
    """Cập nhật hội thoại của NPC được chỉ định"""
    var npc_node = get_npc_node(npc_name)
    if npc_node and npc_node.has_method("update_dialogue"):
        npc_node.update_dialogue(dialogue)

func get_npc_node(npc_name: String) -> Node2D:
    """Lấy node NPC theo tên"""
    match npc_name:
        "张三":
            return npc_zhang
        "李四":
            return npc_li
        "王五":
            return npc_wang
        _:
            return null
```

Chức năng cốt lõi của script scene chính là định kỳ lấy trạng thái NPC từ backend. Trong `_ready()`, chúng ta lấy tham chiếu đến singleton APIClient và kết nối signal `npc_status_received`. Sau đó gọi ngay `get_npc_status()` để lấy trạng thái NPC một lần. Trong `_process()`, chúng ta dùng bộ đếm thời gian để gọi `get_npc_status()` mỗi `Config.NPC_STATUS_UPDATE_INTERVAL` giây (mặc định 30 giây). Khi nhận được cập nhật trạng thái NPC, hàm callback `_on_npc_status_received()` sẽ duyệt qua tất cả NPC, gọi phương thức `update_dialogue()` của chúng để cập nhật bong bóng hội thoại. Như vậy, ngay cả khi người chơi không tương tác với NPC, vẫn có thể thấy hội thoại tự chủ giữa các NPC.

Toàn bộ quy trình giao tiếp frontend-backend được minh họa như Hình 15.14:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-14.png" alt="" width="85%"/>
  <p>Hình 15.14 Toàn bộ quy trình giao tiếp frontend-backend</p>
</div>


Đến đây, tất cả các chức năng giao tiếp frontend-backend đã được hiện thực. Người chơi có thể tự do di chuyển trong game, tương tác với NPC, trò chuyện bằng ngôn ngữ tự nhiên. Đồng thời, scene chính sẽ định kỳ lấy trạng thái NPC từ backend, cập nhật bong bóng hội thoại của NPC, hiển thị hội thoại tự chủ giữa các NPC. Toàn bộ hệ thống sử dụng cơ chế signal để giao tiếp, các component được ghép nối lỏng, dễ bảo trì và mở rộng.

## 15.7 Tổng kết và triển vọng

### 15.7.1 Nhìn lại chương này

Trong chương này, chúng ta đã hoàn thành một dự án thị trấn AI hoàn chỉnh — Thị trấn Cyber. Dự án này kết hợp framework HelloAgents với game engine Godot, tạo ra một thế giới ảo tràn đầy sức sống. Hãy cùng nhìn lại những nội dung cốt lõi chúng ta đã học.

<strong>Thiết kế kiến trúc kỹ thuật</strong>

Chúng ta áp dụng kiến trúc tách biệt game engine + dịch vụ backend, tách render frontend, logic backend và trí tuệ AI thành các tầng khác nhau. Godot phụ trách hình ảnh game và tương tác người chơi, FastAPI phụ trách dịch vụ API và quản lý trạng thái, HelloAgents phụ trách trí tuệ NPC và hệ thống bộ nhớ. Thiết kế phân tầng này cho phép mỗi phần được phát triển và kiểm thử độc lập, đồng thời cung cấp nền tảng tốt cho việc mở rộng sau này.

<strong>Hệ thống Agent NPC</strong>

Chúng ta sử dụng SimpleAgent của HelloAgents để tạo Agent độc lập cho mỗi NPC. Mỗi NPC đều có thiết lập nhân vật, đặc điểm tính cách và hệ thống bộ nhớ riêng. Thông qua system prompt được thiết kế tỉ mỉ, chúng ta biến Trương Tam thành một kỹ sư Python nghiêm túc, Lý Tứ thành một quản lý sản phẩm giỏi giao tiếp, Vương Ngũ thành một nhà thiết kế UI giàu sáng tạo. Những NPC này không chỉ hiểu cuộc trò chuyện của người chơi, mà còn có thể đưa ra phản hồi phù hợp với đặc điểm vai trò của mình.

<strong>Hệ thống bộ nhớ và độ thiện cảm</strong>

Chúng ta hiện thực hệ thống bộ nhớ hai tầng: bộ nhớ ngắn hạn duy trì tính mạch lạc của hội thoại, bộ nhớ dài hạn lưu trữ toàn bộ lịch sử tương tác. Thông qua truy xuất ngữ nghĩa của cơ sở dữ liệu vector, NPC có thể nhớ lại các chủ đề đã thảo luận trước đó. Hệ thống độ thiện cảm khiến thái độ của NPC với người chơi thay đổi theo tương tác, từ xa lạ đến bạn thân, mỗi cấp có biểu hiện hành vi khác nhau. Những thiết kế này khiến NPC trở nên chân thực và thú vị hơn.

<strong>Xây dựng scene game</strong>

Chúng ta sử dụng Godot để tạo một scene văn phòng phong cách pixel, hiện thực điều khiển người chơi, NPC tuần tra, phát hiện tương tác và UI hội thoại. Thông qua thiết kế mô-đun của hệ thống scene, chúng ta có thể dễ dàng thêm NPC mới, scene mới và chức năng mới. Cú pháp ngắn gọn của GDScript khiến việc hiện thực logic game trở nên trực quan và hiệu quả.

<strong>Giao tiếp frontend-backend</strong>

Chúng ta sử dụng HTTP REST API để hiện thực giao tiếp giữa frontend Godot và backend FastAPI. Thông qua yêu cầu bất đồng bộ và hệ thống signal, chúng ta đảm bảo độ mượt của game, ngay cả khi độ trễ mạng cao cũng không ảnh hưởng đến trải nghiệm người chơi. Việc đóng gói API client giúp các script khác dễ dàng gọi dịch vụ backend, việc hiện thực UI hội thoại giúp người chơi giao tiếp tự nhiên với NPC.

Toàn bộ tech stack của dự án được minh họa như Hình 15.15:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/15-figures/15-15.png" alt="" width="85%"/>
  <p>Hình 15.15 Tech stack của Thị trấn Cyber</p>
</div>


### 15.7.2 Các hướng mở rộng

Thị trấn Cyber mới chỉ là điểm khởi đầu, vẫn còn nhiều hướng có thể mở rộng. Những mở rộng này không chỉ nâng cao tính thú vị của game, mà còn khám phá thêm nhiều khả năng của công nghệ AI trong game.

<strong>(1) Hỗ trợ nhiều người chơi trực tuyến</strong>

Thị trấn Cyber hiện tại là game một người chơi, nhưng chúng ta có thể mở rộng thành game nhiều người chơi trực tuyến. Nhiều người chơi có thể đồng thời bước vào cùng một văn phòng, tương tác với NPC và những người chơi khác. Điều này đòi hỏi phải đưa vào WebSocket để giao tiếp thời gian thực, cũng như cơ sở dữ liệu để lưu trữ bền vững dữ liệu người chơi và trạng thái NPC. NPC có thể ghi nhớ tương tác với những người chơi khác nhau, duy trì độ thiện cảm độc lập với mỗi người chơi.

<strong>(2) Hệ thống nhiệm vụ</strong>

Chúng ta có thể thiết kế hệ thống nhiệm vụ cho NPC. Khi độ thiện cảm giữa người chơi và NPC đạt đến một mức nhất định, NPC sẽ cung cấp nhiệm vụ đặc biệt. Ví dụ, Trương Tam có thể nhờ người chơi giúp gỡ lỗi một đoạn mã, Lý Tứ có thể nhờ người chơi thu thập phản hồi người dùng, Vương Ngũ có thể nhờ người chơi đánh giá phương án thiết kế. Hoàn thành nhiệm vụ có thể nhận phần thưởng, đồng thời nâng cao hơn nữa độ thiện cảm.

<strong>(3) Tương tác giữa các NPC</strong>

Hiện tại NPC chỉ tương tác với người chơi, nhưng chúng ta có thể để NPC tương tác với nhau. Trương Tam có thể thảo luận nhu cầu sản phẩm với Lý Tứ, Lý Tứ có thể thảo luận thiết kế giao diện với Vương Ngũ, Vương Ngũ có thể thảo luận hiện thực kỹ thuật với Trương Tam. Những tương tác này có thể diễn ra tự động ở background, người chơi có thể quan sát hội thoại giữa các NPC, khiến cả thế giới trở nên sinh động hơn.

<strong>(4) Hệ thống cảm xúc</strong>

Ngoài độ thiện cảm, chúng ta còn có thể thêm hệ thống cảm xúc phức tạp hơn cho NPC. NPC có thể có các trạng thái cảm xúc khác nhau như vui vẻ, buồn bã, tức giận, phấn khích, những cảm xúc này sẽ ảnh hưởng đến phong cách phản hồi và hành vi của NPC. Ví dụ, khi NPC có tâm trạng tốt sẽ sẵn sàng chia sẻ thông tin hơn; khi NPC có tâm trạng không tốt có thể khá lạnh nhạt.

<strong>(5) Hệ thống sự kiện động</strong>

Chúng ta có thể thiết kế một số sự kiện động để thế giới game phong phú hơn. Ví dụ, định kỳ tổ chức họp nhóm, tất cả NPC và người chơi cùng nhau thảo luận tiến độ dự án; hoặc tổ chức tiệc sinh nhật, chúc mừng sinh nhật của một NPC nào đó; hoặc nhiệm vụ khẩn cấp đột xuất, yêu cầu mọi người hợp tác hoàn thành. Những sự kiện này có thể tăng tính biến đổi và thú vị của game.

<strong>(6) Thế giới lớn hơn</strong>

Thị trấn Cyber hiện tại chỉ có một scene văn phòng, nhưng chúng ta có thể mở rộng ra một thế giới lớn hơn. Có thể thêm các scene khác nhau như quán cà phê, thư viện, công viên, mỗi scene có NPC và cách tương tác khác nhau. Người chơi có thể di chuyển giữa các scene, khám phá thế giới ảo rộng lớn hơn.

<strong>(7) Học cá nhân hóa</strong>

NPC có thể học sở thích và thói quen của từng người chơi. Ví dụ, nếu người chơi thường xuyên thảo luận Python với Trương Tam, NPC sẽ ghi nhớ người chơi quan tâm đến lập trình, sau này sẽ chủ động chia sẻ nội dung liên quan. Nếu người chơi thích chơi game vào buổi tối, NPC sẽ ghi nhớ thói quen thời gian này, trở nên hoạt bát hơn vào buổi tối.

### 15.7.3 Suy ngẫm và triển vọng

Thị trấn Cyber đã cho thấy tiềm năng to lớn của công nghệ AI trong game. NPC trong game truyền thống bị giới hạn bởi cây hội thoại và script có sẵn, còn NPC AI có thể hiểu và sinh ngôn ngữ tự nhiên, trò chuyện thực sự với người chơi. Điều này không chỉ nâng cao tính nhập vai của game, mà còn mang đến những khả năng mới cho thiết kế game.

Nhưng NPC AI cũng đối mặt với một số thách thức. Đầu tiên là vấn đề chi phí, mỗi cuộc hội thoại đều cần gọi LLM API, điều này sẽ phát sinh một khoản chi phí nhất định. Với game nhiều người chơi trực tuyến quy mô lớn, chi phí này có thể rất cao. Tiếp theo là vấn đề độ trễ, suy luận của LLM cần thời gian, nếu độ trễ mạng cao, người chơi có thể phải chờ vài giây mới thấy phản hồi của NPC. Cuối cùng là vấn đề kiểm soát nội dung, nội dung do LLM sinh ra có thể không hoàn toàn kiểm soát được, cần thiết kế prompt tốt và cơ chế lọc nội dung.

Dù còn những thách thức này, tương lai của NPC AI vẫn đầy hy vọng. Với sự phát triển của công nghệ LLM, tốc độ suy luận sẽ ngày càng nhanh, chi phí sẽ ngày càng thấp. Các LLM nhỏ gọn chạy cục bộ cũng đang phát triển nhanh chóng, trong tương lai có thể chạy trực tiếp trên thiết bị của người chơi, hoàn toàn không cần yêu cầu mạng. Sự kết hợp giữa công nghệ AI và game sẽ mang đến cho người chơi trải nghiệm chưa từng có.

Trong chương đồ án tốt nghiệp của Phần Năm, chúng ta sẽ học cách dùng single-agent và multi-agent để xây dựng một Agent tổng quát, đó sẽ là thời gian sáng tạo của bạn, hãy đón chờ nhé!

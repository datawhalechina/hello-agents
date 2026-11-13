# Chương 13: Trợ lý du lịch thông minh

Trong những chương trước, chúng ta đã xây dựng framework HelloAgents từ con số không, hiện thực nhiều mẫu hình agent, hệ thống công cụ, cơ chế bộ nhớ, giao thức truyền thông và đánh giá hiệu năng,... Từ chương này, chúng ta bước vào một giai đoạn hoàn toàn mới: <strong>vận dụng tổng hợp những kiến thức đã học để xây dựng một ứng dụng hoàn chỉnh, thực dụng.</strong>

Bạn còn nhớ agent đầu tiên chúng ta xây dựng ở chương 1 không? Đó là một trợ lý du lịch thông minh đơn giản, minh hoạ nguyên lý cơ bản của vòng lặp `Thought-Action-Observation`. Trợ lý du lịch thông minh trong chương này sẽ là một dự án hoàn chỉnh, bao gồm các chức năng cốt lõi sau:

<strong>(1) Lập kế hoạch hành trình thông minh</strong>: người dùng nhập điểm đến, ngày tháng, sở thích và các thông tin khác, hệ thống tự động sinh ra kế hoạch hành trình đầy đủ bao gồm điểm tham quan, ăn uống và khách sạn.

<strong>(2) Trực quan hoá bản đồ</strong>: đánh dấu vị trí các điểm tham quan trên bản đồ, vẽ tuyến tham quan, giúp hành trình rõ ràng trong nháy mắt.

<strong>(3) Tính ngân sách</strong>: tự động tính chi phí vé vào cửa, khách sạn, ăn uống và giao thông, hiển thị chi tiết ngân sách.

<strong>(4) Chỉnh sửa hành trình</strong>: hỗ trợ thêm, xoá, điều chỉnh điểm tham quan, cập nhật bản đồ theo thời gian thực.

<strong>(5) Chức năng xuất</strong>: hỗ trợ xuất sang PDF hoặc ảnh, thuận tiện lưu trữ và chia sẻ.



## 13.1 Tổng quan dự án và thiết kế kiến trúc

### 13.1.1 Vì sao cần trợ lý du lịch thông minh

Lập kế hoạch cho một chuyến đi là việc vừa thú vị vừa đau đầu. Bạn cần tìm kiếm thông tin điểm tham quan trên mạng, so sánh các cẩm nang khác nhau, xem dự báo thời tiết, đặt khách sạn, tính ngân sách, quy hoạch tuyến đường. Quá trình này có thể tốn vài giờ, thậm chí vài ngày. Và dù đã bỏ ra ngần ấy thời gian, bạn vẫn không chắc hành trình đã hợp lý chưa, có bỏ sót điểm tham quan quan trọng nào không, ngân sách có chính xác không.

Cách lập kế hoạch du lịch truyền thống có vài điểm đau. Thứ nhất là <strong>thông tin phân tán</strong>. Thông tin điểm tham quan ở trên các trang du lịch, thông tin thời tiết ở trên các trang thời tiết, thông tin khách sạn ở trên các trang đặt phòng; bạn phải chuyển qua lại giữa nhiều trang và tự tay tổng hợp những thông tin này. Thứ hai là <strong>thiếu cá nhân hoá</strong>. Phần lớn cẩm nang đều chung chung, không xét đến sở thích cá nhân, giới hạn ngân sách, thời gian đi lại của bạn. Cuối cùng là <strong>khó điều chỉnh</strong>. Khi muốn sửa hành trình, có thể bạn phải quy hoạch lại toàn bộ, vì thứ tự điểm tham quan, lịch trình thời gian và ngân sách đều liên quan chặt chẽ với nhau.

Công nghệ AI mang đến khả năng mới để giải quyết những vấn đề này. Hãy tưởng tượng bạn chỉ cần nói với hệ thống "Tôi muốn đi Bắc Kinh 3 ngày, thích lịch sử và văn hoá, ngân sách trung bình", hệ thống có thể tự động tạo cho bạn một kế hoạch hành trình hoàn chỉnh, gồm mỗi ngày đi những điểm tham quan nào, ăn ở đâu, ở khách sạn nào, cần bao nhiêu ngân sách. Hơn nữa kế hoạch này có thể điều chỉnh: bạn có thể xoá những điểm không thích, điều chỉnh thứ tự tham quan, hệ thống sẽ tự động cập nhật bản đồ và ngân sách.

Đó chính là trợ lý du lịch thông minh mà chúng ta sẽ xây dựng. Nó không chỉ là một bản demo kỹ thuật, mà là một ứng dụng thực sự hữu ích. Qua dự án này, bạn sẽ học được cách đưa công nghệ AI vào giải quyết vấn đề thực tế, cách thiết kế hệ thống đa agent, cách xây dựng một ứng dụng Web hoàn chỉnh.

### 13.1.2 Tổng quan kiến trúc kỹ thuật

Hệ thống áp dụng <strong>kiến trúc tách biệt frontend/backend</strong> kinh điển, chia thành bốn tầng, như Hình 13.1:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-1.png" alt="" width="85%"/>
  <p>Hình 13.1 Kiến trúc kỹ thuật của trợ lý du lịch thông minh</p>
</div>

<strong>(1) Tầng frontend (Vue3+TypeScript)</strong>: chịu trách nhiệm tương tác người dùng và hiển thị dữ liệu, bao gồm nhập biểu mẫu, hiển thị kết quả, trực quan hoá bản đồ.

<strong>(2) Tầng backend (FastAPI)</strong>: chịu trách nhiệm định tuyến API, kiểm tra dữ liệu, logic nghiệp vụ.

<strong>(3) Tầng agent (HelloAgents)</strong>: chịu trách nhiệm phân rã nhiệm vụ, gọi công cụ, tích hợp kết quả. Bao gồm 4 Agent chuyên biệt.

<strong>(4) Tầng dịch vụ bên ngoài</strong>: cung cấp dữ liệu và năng lực, bao gồm API Amap (bản đồ cao Đức), API Unsplash, API LLM.

Luồng dữ liệu diễn ra như sau: người dùng điền biểu mẫu ở frontend → backend kiểm tra dữ liệu → gọi hệ thống agent → agent lần lượt gọi các Agent tìm kiếm điểm tham quan, truy vấn thời tiết, gợi ý khách sạn, lập kế hoạch hành trình → mỗi Agent gọi API bên ngoài thông qua giao thức MCP → tích hợp kết quả trả về frontend → frontend render hiển thị.

Cấu trúc dự án tham khảo như sau, giúp bạn dễ định vị mã nguồn:

```
helloagents-trip-planner/
├── backend/                    # Mã nguồn backend
│   ├── app/
│   │   ├── agents/            # Hiện thực agent
│   │   ├── api/               # Định tuyến API
│   │   ├── models/            # Mô hình dữ liệu
│   │   ├── services/          # Tầng dịch vụ
│   │   └── config.py          # Tệp cấu hình
│   └── requirements.txt       # Phụ thuộc Python
│
└── frontend/                   # Mã nguồn frontend
    ├── src/
    │   ├── views/             # Component trang
    │   ├── services/          # Dịch vụ API
    │   ├── types/             # Định nghĩa kiểu
    │   └── router/            # Cấu hình định tuyến
    └── package.json           # Phụ thuộc npm
```

Thiết kế kiến trúc chi tiết và luồng dữ liệu sẽ được giới thiệu trong các mục tiếp theo.

### 13.1.3 Trải nghiệm nhanh: chạy dự án trong 5 phút

Trước khi đi sâu vào chi tiết hiện thực, hãy chạy dự án trước để xem hiệu quả cuối cùng. Như vậy bạn sẽ có nhận thức trực quan về toàn bộ hệ thống.

<strong>Yêu cầu môi trường:</strong>

- Python 3.10 trở lên
- Node.js 16.0 trở lên
- npm 8.0 trở lên

<strong>Lấy API key:</strong>

Bạn cần chuẩn bị các API key sau:

- API của LLM (OpenAI, DeepSeek,...)
- Web Service Key của Amap: truy cập https://console.amap.com/ để đăng ký và tạo ứng dụng
- Unsplash Access Key: truy cập https://unsplash.com/developers để đăng ký và tạo ứng dụng

Đặt tất cả API key vào tệp `.env`.

Khởi động backend:

```bash
# 1. Vào thư mục backend
cd helloagents-trip-planner/backend

# 2. Cài đặt phụ thuộc
pip install -r requirements.txt

# 3. Cấu hình biến môi trường
cp .env.example .env
# Sửa tệp .env, điền API key của bạn

# 4. Khởi động dịch vụ backend
uvicorn app.api.main:app --reload
# hoặc
python run.py
```

Sau khi khởi động thành công, truy cập http://localhost:8000/docs để xem tài liệu API.

Mở một cửa sổ terminal mới:

```bash
# 1. Vào thư mục frontend
cd helloagents-trip-planner/frontend

# 2. Cài đặt phụ thuộc
npm install

# 3. Khởi động dịch vụ frontend
npm run dev
```

Sau khi khởi động thành công, truy cập http://localhost:5173 để sử dụng ứng dụng.

Trải nghiệm các chức năng cốt lõi:

Trước hết, điền vào biểu mẫu ở trang chủ các thông tin như thành phố điểm đến, ngày đi, sở thích, ngân sách, loại phương tiện và loại chỗ ở. Sau khi nhấn nút "Bắt đầu lập kế hoạch", hệ thống sẽ hiển thị thanh tiến trình tải và nhanh chóng tạo trang kết quả, như Hình 13.2.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-2.png" alt="" width="85%"/>
  <p>Hình 13.2 Trang đang lập kế hoạch của trợ lý du lịch</p>
</div>

Sau đó tải thành công, trang sẽ hiển thị rõ ràng tổng quan hành trình, chi tiết ngân sách, bản đồ điểm tham quan, chi tiết hành trình từng ngày và thông tin thời tiết, như Hình 13.3 và 13.4.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-3.png" alt="" width="85%"/>
  <p>Hình 13.3 Trang hoàn tất lập kế hoạch của trợ lý du lịch</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-4.png" alt="" width="85%"/>
  <p>Hình 13.4 Trang hoàn tất lập kế hoạch của trợ lý du lịch</p>
</div>

Nếu người dùng cần điều chỉnh cá nhân hoá, có thể nhấn nút "Chỉnh sửa hành trình" để tự do điều chỉnh thứ tự điểm tham quan hoặc xoá một điểm tham quan, như Hình 13.5. Sau khi hoàn tất quy hoạch, thông qua menu thả xuống "Xuất hành trình", có thể dễ dàng lưu phương án cuối cùng thành tệp ảnh hoặc PDF, thuận tiện tra cứu bất cứ lúc nào.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-5.png" alt="" width="85%"/>
  <p>Hình 13.5 Trang hoàn tất lập kế hoạch của trợ lý du lịch</p>
</div>

## 13.2 Thiết kế mô hình dữ liệu

### 13.2.1 Luồng dữ liệu trong ứng dụng Web

Khi xây dựng trợ lý du lịch thông minh, chúng ta cần giải quyết một vấn đề cốt lõi: <strong>làm sao biểu diễn và truyền tải dữ liệu kế hoạch du lịch?</strong>

Chúng ta cần hiểu dữ liệu luân chuyển như thế nào trong một ứng dụng Web hoàn chỉnh. Hãy tưởng tượng khi người dùng nhấn nút "Bắt đầu lập kế hoạch" trong trình duyệt, điều gì sẽ xảy ra?

Dữ liệu biểu mẫu người dùng điền ở frontend (điểm đến, ngày tháng, ngân sách,...) cần được gửi đến máy chủ backend thông qua yêu cầu HTTP. Sau khi backend nhận dữ liệu, nó gọi hệ thống agent để xử lý. Agent lại gọi API Amap, API Unsplash và các dịch vụ bên ngoài khác để lấy dữ liệu. Định dạng dữ liệu các API bên ngoài trả về rất khác nhau, có nơi dùng `lng`, có nơi dùng `lon`, có nơi dùng `longitude`. Cuối cùng, backend cần trả dữ liệu đã xử lý về frontend, frontend render thành trang mà người dùng nhìn thấy.

Trong quá trình này, dữ liệu trải qua nhiều lần chuyển đổi: biểu mẫu frontend → yêu cầu HTTP → đối tượng Python ở backend → phản hồi API bên ngoài → đối tượng Python ở backend → phản hồi HTTP → đối tượng TypeScript ở frontend → hiển thị trên trang. Nếu không có định dạng dữ liệu thống nhất, mỗi bước chuyển đổi đều có thể phát sinh lỗi. Đó là lý do chúng ta cần <strong>mô hình dữ liệu</strong>.

### 13.2.2 Từ dictionary đến mô hình Pydantic

Hãy bắt đầu từ nguyên mẫu đơn giản ở chương 1. Trong nguyên mẫu đó, chúng ta dùng dictionary của Python để biểu diễn dữ liệu điểm tham quan:

```python
# Cách làm ở chương 1: dùng dictionary
attraction = {
    "name": "Tử Cấm Thành",
    "location": {"lng": 116.397128,"lat": 39.916527},
    "price": 60
}

# Truy cập dữ liệu
lng = attraction["location"]["lng"]
```

Cách này rất tiện ở giai đoạn nguyên mẫu, nhưng trong dự án thực tế sẽ gặp nhiều vấn đề. Thứ nhất là vấn đề <strong>tên trường không thống nhất</strong>. Dữ liệu vị trí API Amap trả về là chuỗi dạng `"116.397128,39.916527"`, cần tự tay tách thành kinh độ và vĩ độ. Trong khi API Unsplash có thể dùng `longitude` và `latitude`. Nếu chúng ta dùng dictionary ở khắp nơi trong mã, thì mỗi nơi đều phải xử lý những khác biệt này.

Thứ hai là vấn đề <strong>an toàn kiểu</strong>. Giả sử chúng ta vô tình viết `price` thành chuỗi `"60"`, trong Python điều này không báo lỗi ngay, nhưng khi tính tổng ngân sách sẽ phát sinh vấn đề. Tệ hơn, loại lỗi này chỉ có thể phát hiện khi chạy, và thông tin lỗi có thể rất khó định vị.

Cuối cùng là vấn đề <strong>khả năng bảo trì</strong>. Khi cần thêm trường mới cho điểm tham quan (ví dụ `rating` - điểm đánh giá), phải sửa nhiều nơi trong mã. Nếu bỏ sót một chỗ nào đó, dữ liệu sẽ không nhất quán.

Pydantic cung cấp một giải pháp. Đây là thư viện kiểm tra dữ liệu của Python, cho phép chúng ta dùng lớp để định nghĩa cấu trúc dữ liệu, và tự động xử lý kiểm tra, chuyển đổi, tuần tự hoá. Hãy xem một ví dụ đơn giản:

```python
from pydantic import BaseModel,Field

class Location(BaseModel):
    longitude: float = Field(...,description="kinh độ")
    latitude: float = Field(...,description="vĩ độ")

class Attraction(BaseModel):
    name: str
    location: Location
    ticket_price: int = 0

# Tạo đối tượng
attraction = Attraction(
    name="Tử Cấm Thành",
    location=Location(longitude=116.397128,latitude=39.916527),
    ticket_price=60
)

# Truy cập an toàn kiểu
lng = attraction.location.longitude  # IDE sẽ cung cấp gợi ý mã
```

Cách làm này có vài lợi ích. Thứ nhất, nếu chúng ta truyền sai kiểu (ví dụ đặt `ticket_price` là chuỗi), Pydantic sẽ lập tức ném ngoại lệ, cho biết chỗ nào sai. Thứ hai, IDE có thể dựa trên định nghĩa kiểu để gợi ý mã và kiểm tra kiểu, giảm mạnh lỗi chính tả. Cuối cùng, khi cần sửa cấu trúc dữ liệu, chỉ cần sửa định nghĩa lớp, mọi nơi dùng lớp này đều tự động cập nhật.

### 13.2.3 Các khái niệm cốt lõi của Pydantic

Trước khi đi sâu thiết kế mô hình dữ liệu của chúng ta, hãy tìm hiểu vài khái niệm cốt lõi của Pydantic. Nền tảng của Pydantic là lớp `BaseModel`, mọi mô hình dữ liệu đều cần kế thừa lớp này. Mỗi trường đều có thể chỉ định kiểu, Pydantic sẽ tự động kiểm tra và chuyển đổi kiểu.

Định nghĩa trường dùng hàm `Field`, có thể chỉ định giá trị mặc định, mô tả, quy tắc kiểm tra,... `...` biểu thị trường này là bắt buộc; nếu tạo đối tượng mà không cung cấp trường này, Pydantic sẽ ném ngoại lệ. Chúng ta cũng có thể dùng `Optional` để biểu thị trường tuỳ chọn, hoặc trực tiếp cung cấp giá trị mặc định.

```python
from pydantic import BaseModel,Field
from typing import Optional,List

class Attraction(BaseModel):
    name: str = Field(...,description="tên điểm tham quan")  # bắt buộc
    rating: float = Field(default=0.0,ge=0,le=5)  # giá trị mặc định, kiểm tra phạm vi
    visit_duration: int = Field(default=60,gt=0)  # lớn hơn 0
    description: Optional[str] = None  # trường tuỳ chọn
```

Pydantic còn hỗ trợ mô hình lồng nhau và danh sách. Chúng ta có thể dùng một mô hình làm kiểu trường trong mô hình khác, từ đó xây dựng cấu trúc dữ liệu phức tạp. Ví dụ, một điểm tham quan chứa thông tin vị trí, một hành trình chứa nhiều điểm tham quan.

```python
class DayPlan(BaseModel):
    date: str
    attractions: List[Attraction]  # danh sách điểm tham quan
    hotel: Optional[Hotel] = None  # thông tin khách sạn tuỳ chọn
```

Một trong những tính năng mạnh mẽ nhất là <strong>validator tuỳ chỉnh</strong>. Đôi khi định dạng dữ liệu API bên ngoài trả về không đáp ứng yêu cầu của chúng ta; chúng ta có thể dùng decorator `field_validator` để tuỳ chỉnh logic kiểm tra và chuyển đổi. Ví dụ, nhiệt độ Amap trả về là chuỗi dạng `"16°C"`, chúng ta cần chuyển thành số:

```python
from pydantic import field_validator

class WeatherInfo(BaseModel):
    temperature: int

    @field_validator('temperature',mode='before')
    def parse_temperature(cls,v):
        """Phân tích chuỗi nhiệt độ: "16°C" -> 16"""
        if isinstance(v,str):
            v = v.replace('°C','').replace('℃','').strip()
            return int(v)
        return v
```

Validator này sẽ tự động chạy trước khi tạo đối tượng, chuyển chuỗi thành số nguyên. Như vậy chúng ta không cần tự tay xử lý định dạng nhiệt độ ở mọi nơi trong mã.

### 13.2.4 Thiết kế mô hình từ dưới lên

Bây giờ hãy bắt đầu thiết kế mô hình dữ liệu cho trợ lý du lịch thông minh. Một nguyên tắc thiết kế tốt là <strong>từ dưới lên</strong>: định nghĩa mô hình cơ bản nhất trước, rồi dần dần tổ hợp thành cấu trúc phức tạp. Lợi ích của cách làm này là mỗi mô hình đều rất đơn giản, dễ hiểu và dễ bảo trì.

Mô hình cơ bản nhất là <strong>thông tin vị trí</strong>. Dù là điểm tham quan, khách sạn hay nhà hàng, đều cần thông tin vị trí. Chúng ta định nghĩa lớp `Location` để biểu diễn toạ độ kinh độ, vĩ độ:

```python
class Location(BaseModel):
    """Thông tin vị trí (toạ độ kinh độ, vĩ độ)"""
    longitude: float = Field(...,description="kinh độ",ge=-180,le=180)
    latitude: float = Field(...,description="vĩ độ",ge=-90,le=90)
```

Ở đây chúng ta dùng kiểm tra phạm vi (`ge` nghĩa là lớn hơn hoặc bằng, `le` nghĩa là nhỏ hơn hoặc bằng), đảm bảo giá trị kinh độ, vĩ độ nằm trong phạm vi hợp lý.

Tiếp theo là <strong>thông tin điểm tham quan</strong>. Một điểm tham quan bao gồm tên, địa chỉ, vị trí, thời gian tham quan, mô tả, đánh giá, ảnh và giá vé. Lưu ý chúng ta dùng `Location` làm kiểu trường, đây chính là mô hình lồng nhau:

```python
class Attraction(BaseModel):
    """Thông tin điểm tham quan"""
    name: str = Field(...,description="tên điểm tham quan")
    address: str = Field(...,description="địa chỉ")
    location: Location = Field(...,description="toạ độ kinh độ, vĩ độ")
    visit_duration: int = Field(...,description="thời gian tham quan gợi ý (phút)",gt=0)
    description: str = Field(...,description="mô tả điểm tham quan")
    category: Optional[str] = Field(default="điểm tham quan",description="phân loại điểm tham quan")
    rating: Optional[float] = Field(default=None,ge=0,le=5,description="điểm đánh giá")
    image_url: Optional[str] = Field(default=None,description="URL ảnh")
    ticket_price: int = Field(default=0,ge=0,description="giá vé (nhân dân tệ)")
```

Tương tự, chúng ta định nghĩa <strong>thông tin ăn uống</strong> và <strong>thông tin khách sạn</strong>. Cấu trúc của các mô hình này khá giống nhau, đều chứa thông tin cơ bản như tên, địa chỉ, vị trí và chi phí:

```python
class Meal(BaseModel):
    """Thông tin ăn uống"""
    type: str = Field(...,description="loại bữa ăn: breakfast/lunch/dinner/snack")
    name: str = Field(...,description="tên quán ăn")
    address: Optional[str] = Field(default=None,description="địa chỉ")
    location: Optional[Location] = Field(default=None,description="toạ độ kinh độ, vĩ độ")
    description: Optional[str] = Field(default=None,description="mô tả")
    estimated_cost: int = Field(default=0,description="chi phí ước tính (nhân dân tệ)")

class Hotel(BaseModel):
    """Thông tin khách sạn"""
    name: str = Field(...,description="tên khách sạn")
    address: str = Field(default="",description="địa chỉ khách sạn")
    location: Optional[Location] = Field(default=None,description="vị trí khách sạn")
    price_range: str = Field(default="",description="khoảng giá")
    rating: str = Field(default="",description="điểm đánh giá")
    distance: str = Field(default="",description="khoảng cách đến điểm tham quan")
    type: str = Field(default="",description="loại khách sạn")
    estimated_cost: int = Field(default=0,description="chi phí ước tính (nhân dân tệ/đêm)")
```

<strong>Thông tin ngân sách</strong> là một mô hình đặc biệt, nó không chứa thông tin vị trí mà chứa tổng hợp các khoản chi phí:

```python
class Budget(BaseModel):
    """Thông tin ngân sách"""
    total_attractions: int = Field(default=0,description="tổng chi phí vé điểm tham quan")
    total_hotels: int = Field(default=0,description="tổng chi phí khách sạn")
    total_meals: int = Field(default=0,description="tổng chi phí ăn uống")
    total_transportation: int = Field(default=0,description="tổng chi phí giao thông")
    total: int = Field(default=0,description="tổng chi phí")
```

Bây giờ chúng ta có thể tổ hợp các mô hình cơ bản này để xây dựng <strong>hành trình một ngày</strong>. Một hành trình một ngày bao gồm ngày, mô tả, phương tiện di chuyển, sắp xếp chỗ ở, khách sạn, danh sách điểm tham quan và danh sách bữa ăn:

```python
class DayPlan(BaseModel):
    """Hành trình một ngày"""
    date: str = Field(...,description="ngày")
    day_index: int = Field(...,description="ngày thứ mấy (bắt đầu từ 0)")
    description: str = Field(...,description="mô tả hành trình trong ngày")
    transportation: str = Field(...,description="phương tiện di chuyển")
    accommodation: str = Field(...,description="sắp xếp chỗ ở")
    hotel: Optional[Hotel] = Field(default=None,description="thông tin khách sạn")
    attractions: List[Attraction] = Field(default_factory=list,description="danh sách điểm tham quan")
    meals: List[Meal] = Field(default_factory=list,description="sắp xếp ăn uống")
```

Lưu ý ở đây dùng `List[Attraction]` để biểu thị danh sách điểm tham quan, `default_factory=list` biểu thị giá trị mặc định là danh sách rỗng.

<strong>Thông tin thời tiết</strong> cần xử lý đặc biệt, vì định dạng nhiệt độ Amap trả về không chuẩn. Chúng ta dùng validator tuỳ chỉnh để xử lý:

```python
class WeatherInfo(BaseModel):
    """Thông tin thời tiết"""
    date: str = Field(...,description="ngày")
    day_weather: str = Field(...,description="thời tiết ban ngày")
    night_weather: str = Field(...,description="thời tiết ban đêm")
    day_temp: int = Field(...,description="nhiệt độ ban ngày (°C)")
    night_temp: int = Field(...,description="nhiệt độ ban đêm (°C)")
    wind_direction: str = Field(...,description="hướng gió")
    wind_power: str = Field(...,description="sức gió")

    @field_validator('day_temp','night_temp',mode='before')
    def parse_temperature(cls,v):
        """Phân tích chuỗi nhiệt độ: "16°C" -> 16"""
        if isinstance(v,str):
            v = v.replace('°C','').replace('℃','').replace('°','').strip()
            try:
                return int(v)
            except ValueError:
                return 0  # xử lý chịu lỗi
        return v
```

Cuối cùng, chúng ta định nghĩa <strong>kế hoạch du lịch đầy đủ</strong>. Đây là mô hình cấp cao nhất, chứa toàn bộ thông tin:

```python
class TripPlan(BaseModel):
    """Kế hoạch du lịch"""
    city: str = Field(...,description="thành phố điểm đến")
    start_date: str = Field(...,description="ngày bắt đầu")
    end_date: str = Field(...,description="ngày kết thúc")
    days: List[DayPlan] = Field(default_factory=list,description="hành trình từng ngày")
    weather_info: List[WeatherInfo] = Field(default_factory=list,description="thông tin thời tiết")
    overall_suggestions: str = Field(...,description="gợi ý tổng thể")
    budget: Optional[Budget] = Field(default=None,description="thông tin ngân sách")
```

Như vậy chúng ta đã hoàn thành thiết kế toàn bộ mô hình dữ liệu. Từ `Location` cơ bản nhất, đến `Attraction`, `Meal`, `Hotel`, rồi `DayPlan`, cuối cùng là `TripPlan`, tạo thành một cấu trúc phân tầng rõ ràng.

### 13.2.5 Ứng dụng của mô hình dữ liệu trong ứng dụng Web

Bây giờ hãy xem những mô hình dữ liệu này được dùng thế nào trong ứng dụng Web thực tế. Trong FastAPI, mô hình Pydantic có thể trực tiếp dùng làm định nghĩa kiểu cho request và response. FastAPI sẽ tự động kiểm tra dữ liệu, tuần tự hoá và sinh tài liệu.

```python
from fastapi import FastAPI
from app.models.schemas import TripPlanRequest,TripPlan

app = FastAPI()

@app.post("/api/trip/plan",response_model=TripPlan)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    """
    Tạo kế hoạch du lịch

    FastAPI tự động:
    1. Kiểm tra dữ liệu request (TripPlanRequest)
    2. Kiểm tra dữ liệu response (TripPlan)
    3. Sinh tài liệu OpenAPI
    """
    trip_plan = await generate_trip_plan(request)
    return trip_plan
```

Khi người dùng gửi yêu cầu POST đến `/api/trip/plan`, FastAPI sẽ tự động chuyển dữ liệu JSON thành đối tượng `TripPlanRequest`. Nếu định dạng dữ liệu không đúng (ví dụ thiếu trường bắt buộc, hoặc kiểu không khớp), FastAPI sẽ tự động trả lỗi 400 và cho người dùng biết chỗ nào sai.

Ở frontend, chúng ta cũng cần định nghĩa kiểu TypeScript tương ứng. Tuy TypeScript và Python là hai ngôn ngữ khác nhau, nhưng cấu trúc dữ liệu là như nhau:

```typescript
interface Location {
  longitude: number;
  latitude: number;
}

interface Attraction {
  name: string;
  address: string;
  location: Location;
  visit_duration: number;
  ticket_price: number;
}

interface TripPlan {
  city: string;
  start_date: string;
  end_date: string;
  days: DayPlan[];
}
```

Như vậy frontend và backend dùng chung một định dạng dữ liệu. Khi backend trả về đối tượng `TripPlan`, frontend có thể dùng trực tiếp, không cần chuyển đổi nào. Kiểm tra kiểu của TypeScript cũng giúp chúng ta tránh nhiều lỗi.

## 13.3 Thiết kế cộng tác đa agent

### 13.3.1 Vì sao cần nhiều agent

Trong chương 7, chúng ta đã học cách dùng SimpleAgent để xây dựng agent. Triết lý thiết kế của SimpleAgent là đơn giản, trực tiếp: mỗi lần gọi phương thức `run()`, Agent sẽ phân tích câu hỏi của người dùng, quyết định có cần gọi công cụ không, rồi trả kết quả. Thiết kế này rất hiệu quả khi xử lý nhiệm vụ đơn giản, nhưng khi đối diện nhiệm vụ như lập kế hoạch du lịch sẽ gặp vài vấn đề.

Nếu dùng một Agent duy nhất để hoàn thành lập kế hoạch du lịch. Agent này cần làm gì? Thứ nhất, nó phải tìm kiếm thông tin điểm tham quan, việc này cần gọi công cụ tìm kiếm POI của Amap. Sau đó, nó phải truy vấn thông tin thời tiết, việc này cần gọi công cụ truy vấn thời tiết. Tiếp theo, nó phải tìm kiếm thông tin khách sạn, lại cần gọi công cụ tìm kiếm POI. Cuối cùng, nó phải tích hợp tất cả thông tin này để sinh ra một kế hoạch du lịch hoàn chỉnh.

Nghe có vẻ đơn giản, nhưng khi thực hiện sẽ gặp vấn đề đầu tiên: <strong>giới hạn gọi công cụ</strong>. Mỗi lần gọi `run()` của SimpleAgent chỉ có thể thực hiện một công cụ. Điều này có nghĩa là chúng ta cần gọi phương thức `run()` nhiều lần, mỗi lần xử lý một nhiệm vụ. Nhưng làm vậy lại nảy sinh vấn đề mới: làm sao truyền thông tin giữa các lần gọi? Thông tin điểm tham quan có được ở lần gọi đầu tiên truyền sang lần gọi thứ hai như thế nào? Chúng ta phải tự tay quản lý các kết quả trung gian này, mã sẽ trở nên rất phức tạp.

Tất nhiên, chúng ta có thể dùng ReactAgent để giải quyết vấn đề này. ReactAgent có thể thực hiện nhiều công cụ trong một lần gọi, nó tự động thực hiện nhiều vòng suy nghĩ và hành động. Nhưng điều này lại mang đến vấn đề mới: <strong>chi phí thời gian</strong>. Mỗi vòng suy nghĩ của ReactAgent đều cần gọi LLM; nếu cần gọi ba công cụ thì cần ít nhất ba vòng suy nghĩ, nghĩa là ít nhất ba lần gọi LLM. Hơn nữa các lần gọi này là tuần tự, phải đợi lần trước hoàn thành mới bắt đầu lần sau, tổng thời gian sẽ rất dài.

Vấn đề thứ hai là <strong>độ phức tạp của prompt</strong>. Nếu muốn một Agent hoàn thành mọi nhiệm vụ, cần mô tả chi tiết logic thực hiện của từng nhiệm vụ trong prompt. Ví dụ:

```python
COMPLEX_PROMPT = """Bạn là trợ lý lập kế hoạch du lịch. Bạn cần:
1. Dùng maps_text_search tìm kiếm điểm tham quan, từ khoá xác định theo sở thích người dùng
2. Dùng maps_weather truy vấn thời tiết, lấy dự báo thời tiết những ngày tới
3. Dùng maps_text_search tìm kiếm khách sạn, loại hình xác định theo nhu cầu người dùng
4. Tích hợp mọi thông tin để sinh kế hoạch du lịch, gồm sắp xếp điểm tham quan, ăn uống, chỗ ở từng ngày
Lưu ý: phải thực hiện theo thứ tự, mỗi công cụ chỉ được gọi một lần, đầu ra phải ở định dạng JSON...
"""
```

Prompt như vậy có vài vấn đề. Thứ nhất là <strong>khó bảo trì</strong>. Nếu muốn sửa logic tìm kiếm điểm tham quan (ví dụ thêm lọc theo đánh giá), phải sửa toàn bộ prompt, rất dễ ảnh hưởng đến các phần khác. Thứ hai là <strong>dễ sai</strong>. LLM cần đồng thời hiểu yêu cầu của nhiều nhiệm vụ, rất dễ nhầm lẫn định dạng và tham số giữa các nhiệm vụ. Cuối cùng là <strong>khó gỡ lỗi</strong>. Khi kế hoạch sinh ra không như kỳ vọng, rất khó biết mắt xích nào có vấn đề: tìm kiếm điểm tham quan không chính xác, truy vấn thời tiết thất bại, hay logic tích hợp có vấn đề?

Đối diện những vấn đề này, một ý tưởng tự nhiên là: có thể phân rã nhiệm vụ phức tạp thành nhiều nhiệm vụ đơn giản, để các Agent khác nhau đảm nhận phần việc của mình? Đó chính là tư tưởng cốt lõi của cộng tác đa agent.

Hãy tưởng tượng một công ty du lịch trong thế giới thực. Khi bạn đến công ty du lịch để tư vấn kế hoạch du lịch, sẽ không chỉ có một người phục vụ bạn. Thường sẽ có chuyên viên tư vấn điểm tham quan, chịu trách nhiệm gợi ý điểm tham quan; có chuyên viên khách sạn, chịu trách nhiệm đặt phòng; và có nhà quy hoạch hành trình, chịu trách nhiệm tích hợp mọi thông tin thành hành trình hoàn chỉnh. Mỗi người tập trung vào lĩnh vực mình giỏi, cuối cùng nhà quy hoạch hành trình tổng hợp mọi thông tin. Cách phân công hợp tác này hiệu quả hơn nhiều so với để một người làm tất cả.

### 13.3.2 Thiết kế vai trò Agent

Dựa trên nguyên tắc phân rã nhiệm vụ, chúng ta thiết kế bốn Agent chuyên biệt, như Hình 13.6:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-6.png" alt="" width="85%"/>
  <p>Hình 13.6 Luồng cộng tác đa agent</p>
</div>

- <strong>AttractionSearchAgent (chuyên gia tìm kiếm điểm tham quan)</strong> tập trung tìm kiếm thông tin điểm tham quan. Nó chỉ cần hiểu sở thích người dùng (ví dụ "lịch sử văn hoá", "phong cảnh tự nhiên"), rồi gọi công cụ tìm kiếm POI của Amap, trả về danh sách điểm tham quan liên quan. Prompt của nó rất đơn giản, chỉ cần nói rõ cách chọn từ khoá theo sở thích, cách gọi công cụ.

- <strong>WeatherQueryAgent (chuyên gia truy vấn thời tiết)</strong> tập trung truy vấn thông tin thời tiết. Nó chỉ cần biết tên thành phố, rồi gọi công cụ truy vấn thời tiết, trả về dự báo thời tiết những ngày tới. Nhiệm vụ của nó rất rõ ràng, gần như không thể sai.

- <strong>HotelAgent (chuyên gia gợi ý khách sạn)</strong> tập trung tìm kiếm thông tin khách sạn. Nó cần hiểu nhu cầu chỗ ở của người dùng (ví dụ "bình dân", "cao cấp"), rồi gọi công cụ tìm kiếm POI, trả về danh sách khách sạn phù hợp yêu cầu.

- <strong>PlannerAgent (chuyên gia lập kế hoạch hành trình)</strong> chịu trách nhiệm tích hợp mọi thông tin. Nó nhận đầu ra của ba Agent trước, cộng với nhu cầu gốc của người dùng (ngày tháng, ngân sách,...), rồi sinh ra kế hoạch du lịch hoàn chỉnh. Nó không cần gọi bất kỳ công cụ bên ngoài nào, chỉ cần tập trung vào việc tích hợp thông tin và sắp xếp hành trình.

Bây giờ hãy thiết kế chi tiết vai trò và prompt của từng Agent. Khi thiết kế prompt, chúng ta cần xét vài câu hỏi then chốt: Agent này cần đầu vào gì? Nó nên tạo ra đầu ra gì? Nó cần gọi công cụ gì? Nó có thể gặp vấn đề gì?

<strong>AttractionSearchAgent</strong> có nhiệm vụ tìm kiếm điểm tham quan theo sở thích người dùng. Đầu vào của nó là tên thành phố và sở thích người dùng (ví dụ "lịch sử văn hoá", "phong cảnh tự nhiên"). Nó cần gọi công cụ `amap_maps_text_search`, tham số là từ khoá và thành phố. Đầu ra của nó là danh sách điểm tham quan, bao gồm tên, địa chỉ, đánh giá và các thông tin khác.

```python
ATTRACTION_AGENT_PROMPT = """Bạn là chuyên gia tìm kiếm điểm tham quan.

**Định dạng gọi công cụ:**
`[TOOL_CALL:amap_maps_text_search:keywords=điểm tham quan,city=tên thành phố]`

**Ví dụ:**
- `[TOOL_CALL:amap_maps_text_search:keywords=điểm tham quan,city=Bắc Kinh]`
- `[TOOL_CALL:amap_maps_text_search:keywords=bảo tàng,city=Thượng Hải]`

**Quan trọng:**
- Phải dùng công cụ để tìm kiếm, không được bịa thông tin
- Tìm kiếm điểm tham quan ở {city} theo sở thích người dùng ({preferences})
"""
```

Prompt này rất ngắn gọn, nhưng chứa đủ mọi thông tin cần thiết. Nó nói rõ định dạng gọi công cụ, cung cấp ví dụ cụ thể, còn nhấn mạnh hai nguyên tắc quan trọng: phải dùng công cụ (không được bịa), và phải tìm kiếm theo sở thích người dùng.

<strong>WeatherQueryAgent</strong> có nhiệm vụ đơn giản hơn, chỉ cần truy vấn thời tiết. Đầu vào của nó là tên thành phố, đầu ra là thông tin thời tiết.

```python
WEATHER_AGENT_PROMPT = """Bạn là chuyên gia truy vấn thời tiết.

**Định dạng gọi công cụ:**
`[TOOL_CALL:amap_maps_weather:city=tên thành phố]`

Hãy truy vấn thông tin thời tiết của {city}.
"""
```

<strong>HotelAgent</strong> có nhiệm vụ tìm kiếm khách sạn. Đầu vào của nó là tên thành phố và loại chỗ ở, đầu ra là danh sách khách sạn.

```python
HOTEL_AGENT_PROMPT = """Bạn là chuyên gia gợi ý khách sạn.

**Định dạng gọi công cụ:**
`[TOOL_CALL:amap_maps_text_search:keywords=khách sạn,city=tên thành phố]`

Hãy tìm kiếm khách sạn {accommodation} ở {city}.
"""
```

<strong>PlannerAgent</strong> là phức tạp nhất, vì nó cần tích hợp mọi thông tin. Đầu vào của nó là nhu cầu người dùng và đầu ra của ba Agent trước, đầu ra là kế hoạch du lịch hoàn chỉnh (định dạng JSON).

```python
PLANNER_AGENT_PROMPT = """Bạn là chuyên gia lập kế hoạch hành trình.

**Định dạng đầu ra:**
Trả về nghiêm ngặt theo định dạng JSON sau:
{
  "city": "tên thành phố",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [...],
  "weather_info": [...],
  "overall_suggestions": "gợi ý tổng thể",
  "budget": {...}
}

**Yêu cầu lập kế hoạch:**
1. weather_info phải chứa thời tiết từng ngày
2. Nhiệt độ là số thuần (không kèm °C)
3. Mỗi ngày sắp xếp 2-3 điểm tham quan
4. Xét khoảng cách điểm tham quan và thời gian tham quan
5. Bao gồm ba bữa sáng, trưa, tối
6. Đưa ra gợi ý thực dụng
7. Bao gồm thông tin ngân sách
"""
```

### 13.3.3 Luồng cộng tác của Agent

Bây giờ hãy xem bốn Agent này cộng tác thế nào để hoàn thành nhiệm vụ lập kế hoạch du lịch. Toàn bộ quy trình có thể chia thành năm bước:

```python
class TripPlannerAgent:
    def __init__(self):
        self.attraction_agent = SimpleAgent(name="Tìm kiếm điểm tham quan", prompt=ATTRACTION_PROMPT)
        self.weather_agent = SimpleAgent(name="Truy vấn thời tiết", prompt=WEATHER_PROMPT)
        self.hotel_agent = SimpleAgent(name="Gợi ý khách sạn", prompt=HOTEL_PROMPT)
        self.planner_agent = SimpleAgent(name="Lập kế hoạch hành trình", prompt=PLANNER_PROMPT)

    def plan_trip(self, request: TripPlanRequest) -> TripPlan:
        # Bước 1: tìm kiếm điểm tham quan
        attraction_response = self.attraction_agent.run(
            f"Hãy tìm kiếm điểm tham quan {request.preferences} ở {request.city}"
        )

        # Bước 2: truy vấn thời tiết
        weather_response = self.weather_agent.run(
            f"Hãy truy vấn thời tiết của {request.city}"
        )

        # Bước 3: gợi ý khách sạn
        hotel_response = self.hotel_agent.run(
            f"Hãy tìm kiếm khách sạn {request.accommodation} ở {request.city}"
        )

        # Bước 4: tích hợp sinh kế hoạch
        planner_query = self._build_planner_query(
            request, attraction_response, weather_response, hotel_response
        )
        planner_response = self.planner_agent.run(planner_query)

        # Bước 5: phân tích JSON
        trip_plan = self._parse_trip_plan(planner_response)
        return trip_plan
```

Luồng này thực hiện tuần tự bốn bước, đầu ra mỗi bước là đầu vào bước tiếp theo. Lưu ý chúng ta dùng hai mô hình Pydantic `TripPlanRequest` và `TripPlan`, được định nghĩa ở mục 13.2.

### 13.3.4 Xây dựng truy vấn

PlannerAgent cần tích hợp mọi thông tin; truy vấn này cần chứa đủ thông tin cần thiết, và phải được tổ chức rõ ràng, có trật tự để LLM hiểu chính xác.

```python
def _build_planner_query(
    self,
    request: TripPlanRequest,
    attraction_response: str,
    weather_response: str,
    hotel_response: str
) -> str:
    """Xây dựng truy vấn cho Agent lập kế hoạch"""
    return f"""
Hãy lập kế hoạch du lịch {request.days} ngày ở {request.city} dựa trên thông tin sau:

**Nhu cầu người dùng:**
- Điểm đến: {request.city}
- Ngày: {request.start_date} đến {request.end_date}
- Số ngày: {request.days} ngày
- Sở thích: {request.preferences}
- Ngân sách: {request.budget}
- Phương tiện di chuyển: {request.transportation}
- Loại chỗ ở: {request.accommodation}

**Thông tin điểm tham quan:**
{attraction_response}

**Thông tin thời tiết:**
{weather_response}

**Thông tin khách sạn:**
{hotel_response}

Hãy sinh kế hoạch du lịch chi tiết, bao gồm sắp xếp điểm tham quan, gợi ý ăn uống, thông tin chỗ ở và chi tiết ngân sách từng ngày.
"""
```

Qua thiết kế cộng tác đa agent này, chúng ta phân rã một nhiệm vụ lập kế hoạch du lịch phức tạp thành bốn nhiệm vụ con đơn giản. Mỗi Agent tập trung vào lĩnh vực mình giỏi, đồng thời đặt nền tảng tốt cho việc mở rộng chức năng trong tương lai (ví dụ thêm Agent gợi ý nhà hàng, Agent quy hoạch giao thông).

## 13.4 Tích hợp công cụ MCP chi tiết

### 13.4.1 Vì sao không gọi API trực tiếp

Trong mục 13.3, chúng ta thiết kế bốn Agent cộng tác để hoàn thành nhiệm vụ lập kế hoạch du lịch. Trong đó AttractionSearchAgent, WeatherQueryAgent và HotelAgent đều cần gọi API của Amap để lấy dữ liệu. Một câu hỏi tự nhiên là: vì sao không gọi thẳng API HTTP của Amap trong Agent?

Hãy xem việc gọi API trực tiếp sẽ như thế nào. Amap cung cấp API tìm kiếm POI; chúng ta cần dựng yêu cầu HTTP, truyền tham số, phân tích phản hồi:

```python
import requests

def search_poi(keywords: str,city: str,api_key: str):
    """Gọi trực tiếp API tìm kiếm POI của Amap"""
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": keywords,
        "city": city,
        "key": api_key,
        "output": "json"
    }
    response = requests.get(url,params=params)
    data = response.json()
    return data
```

Cách này trông có vẻ đơn giản, nhưng khi dùng thực tế sẽ gặp vài vấn đề. Thứ nhất là <strong>Agent không thể tự chủ gọi</strong>. Trong framework HelloAgents của chúng ta, Agent gọi công cụ bằng cách nhận diện dấu hiệu gọi công cụ trong prompt (ví dụ `[TOOL_CALL:tool_name:arg1=value1]`). Nếu gọi API trực tiếp trong mã, Agent sẽ mất khả năng tự chủ quyết định, biến thành một lệnh gọi hàm đơn giản.

Thứ hai là <strong>truyền tham số phức tạp</strong>. API Amap có nhiều tham số, ví dụ tìm kiếm POI có hơn mười tham số như `keywords`, `city`, `types`, `offset`, `page`. Nếu muốn Agent linh hoạt dùng các tham số này, cần mô tả chi tiết ý nghĩa và định dạng của từng tham số trong prompt, khiến prompt trở nên rất phức tạp.

Thứ ba là <strong>phân tích phản hồi khó khăn</strong>. API Amap trả về dữ liệu định dạng JSON với cấu trúc khá phức tạp. Chúng ta cần viết mã phân tích dữ liệu này, trích xuất các trường cần thiết. Nếu định dạng phản hồi API thay đổi, chúng ta phải sửa mã phân tích.

Cuối cùng là <strong>quản lý công cụ lộn xộn</strong>. Amap cung cấp hơn mười API khác nhau (tìm kiếm POI, truy vấn thời tiết, quy hoạch tuyến đường,...). Nếu viết một hàm cho mỗi API rồi tự tay đăng ký vào danh sách công cụ của Agent, mã sẽ rất dài dòng. Hơn nữa khi muốn thêm API mới, phải sửa nhiều nơi.

### 13.4.2 Tích hợp MCP Amap

MCP (Model Context Protocol) là giao thức chuẩn hoá do Anthropic đề xuất, dùng để kết nối LLM với công cụ bên ngoài. Mục này giới thiệu cách tích hợp máy chủ MCP Amap vào dự án. Dự án của chúng ta dùng `amap-mcp-server`, đây là máy chủ MCP hiện thực bằng Node.js:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-7.png" alt="" width="85%"/>
  <p>Hình 13.7 Công cụ của amap-mcp-server</p>
</div>

Máy chủ MCP Amap cung cấp nhiều công cụ, chủ yếu chia thành các loại sau, như Bảng 13.1:

<div align="center">
  <p>Bảng 13.1 Phân loại công cụ MCP của Amap</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-table-1.png" alt="" width="85%"/>
</div>

Thông qua giao thức MCP, chúng ta có thể tích hợp rất thuận tiện trong HelloAgents:

```python
from hello_agents.tools import MCPTool
from app.config import get_settings

settings = get_settings()

# Tạo công cụ MCP
mcp_tool = MCPTool(
    name="amap_mcp",
    command="npx",
    args=["-y", "@sugarforever/amap-mcp-server"],
    env={"AMAP_API_KEY": settings.amap_api_key},
    auto_expand=True
)
```

Đoạn mã này làm gì? Thứ nhất, `command` và `args` chỉ định cách khởi động máy chủ MCP. `npx -y @sugarforever/amap-mcp-server` sẽ tải và chạy gói `amap-mcp-server` từ kho npm. Tham số `env` truyền biến môi trường, ở đây chúng ta truyền API key của Amap.

<strong>Lưu ý:</strong> một số ví dụ trong tài liệu này dùng `npx` để khởi động dịch vụ MCP (Model Context Protocol). Trong kho mã của mục này, chúng ta thực tế dùng cách `uvx`. Cần nói rõ rằng `npx` và `uvx` có triết lý thiết kế rất nhất quán, chỉ khác hệ sinh thái: `npx` hướng tới JavaScript/Node.js (gói từ npm), còn `uvx` hướng tới Python (gói từ PyPI). Hai cách không phân biệt ưu nhược, mọi người hãy chọn theo nhu cầu khi sử dụng.

Khi chúng ta tạo đối tượng `MCPTool`, nó sẽ khởi động tiến trình máy chủ MCP ở nền, và giao tiếp với máy chủ qua stdin/stdout. Đây là một đặc điểm của giao thức MCP: dùng giao tiếp giữa các tiến trình thay vì HTTP, nhờ vậy hiệu quả hơn và dễ quản lý hơn.

Điều then chốt nhất là tham số `auto_expand=True`. Khi đặt là True, `MCPTool` sẽ tự động truy vấn máy chủ MCP xem có những công cụ nào, rồi tạo một đối tượng Tool độc lập cho mỗi công cụ. Đó là lý do chúng ta chỉ tạo một `MCPTool`, nhưng Agent lại có được 16 công cụ. Hãy xem quá trình này:

```python
# Tạo một MCPTool
mcp_tool = MCPTool(..., auto_expand=True)
agent.add_tool(mcp_tool)

# Agent thực tế có được 16 công cụ!
print(list(agent.tools.keys()))
# ['amap_maps_text_search', 'amap_maps_weather', ...]
```

Như Hình 13.8, giả sử người dùng muốn tìm kiếm điểm tham quan ở Bắc Kinh, AttractionSearchAgent nhận truy vấn "Hãy tìm kiếm điểm tham quan lịch sử văn hoá ở Bắc Kinh". Agent phân tích truy vấn này, quyết định gọi công cụ `amap_maps_text_search`, tham số là `keywords=điểm tham quan,city=Bắc Kinh`.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-8.png" alt="" width="85%"/>
  <p>Hình 13.8 Luồng gọi công cụ MCP</p>
</div>

Agent sinh dấu hiệu gọi công cụ: `[TOOL_CALL:amap_maps_text_search:keywords=điểm tham quan,city=Bắc Kinh]`. Framework HelloAgents phân tích dấu hiệu này, trích xuất tên công cụ và tham số, rồi gọi đối tượng Tool tương ứng.

Đối tượng Tool do `MCPTool` tự động tạo, nó gửi yêu cầu gọi đến máy chủ MCP. Cụ thể, nó dựng một thông điệp định dạng JSON-RPC, gửi đến tiến trình máy chủ qua stdin:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "amap_maps_text_search",
    "arguments": {
      "keywords": "điểm tham quan",
      "city": "Bắc Kinh"
    }
  }
}
```

Máy chủ MCP nhận thông điệp này, phân tích tham số, rồi gọi API HTTP của Amap. Nó dựng yêu cầu HTTP, thêm API key, gửi yêu cầu, nhận phản hồi.

API Amap trả về dữ liệu định dạng JSON, chứa danh sách điểm tham quan, địa chỉ, toạ độ và các thông tin khác. Máy chủ MCP phân tích dữ liệu này, trích xuất các trường then chốt, rồi dựng thông điệp phản hồi, trả về `MCPTool` qua stdout:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Tìm thấy các điểm tham quan sau:\n1. Bảo tàng Cố Cung - Địa chỉ: Số 4 phố Cảnh Sơn Tiền, quận Đông Thành\n2. Công viên Thiên Đàn - Địa chỉ: Đường Thiên Đàn, quận Đông Thành\n..."
      }
    ]
  }
}
```

`MCPTool` nhận phản hồi, trích xuất nội dung văn bản, trả về Agent. Agent dùng kết quả này làm đầu ra của lần gọi công cụ, tiếp tục sinh phản hồi cuối cùng.

Quy trình này trông có vẻ phức tạp, nhưng với Agent, nó chỉ cần biết có một công cụ tên `amap_maps_text_search` có thể tìm kiếm điểm tham quan. Mọi chi tiết tầng dưới đều được giao thức MCP và `MCPTool` đóng gói.

### 13.4.3 Chia sẻ instance MCP

Trong hệ thống đa agent của chúng ta, có ba Agent đều cần dùng công cụ của Amap. Vậy mỗi Agent nên tạo instance `MCPTool` riêng, hay chia sẻ cùng một instance?

Nếu mỗi Agent đều tạo một instance `MCPTool`, nghĩa là sẽ có ba tiến trình máy chủ chạy đồng thời. Mỗi tiến trình đều gọi API Amap độc lập, có thể vượt giới hạn tốc độ của API. Hơn nữa nhiều tiến trình sẽ chiếm nhiều bộ nhớ và CPU hơn.

Cách tốt hơn là để tất cả Agent chia sẻ cùng một instance `MCPTool`. Như vậy chỉ cần khởi động một tiến trình máy chủ MCP, mọi lời gọi API đều đi qua tiến trình này. Điều này không chỉ tiết kiệm tài nguyên mà còn kiểm soát tần suất gọi API tốt hơn.

Trong mã, chúng ta tạo một instance `MCPTool` trong hàm khởi tạo của `TripPlannerAgent`, rồi thêm nó vào danh sách công cụ của từng Agent con:

```python
class TripPlannerAgent:
    def __init__(self):
        settings = get_settings()
        self.llm = HelloAgentsLLM()

        # Tạo instance công cụ MCP dùng chung (chỉ tạo một lần)
        self.mcp_tool = MCPTool(
            name="amap_mcp",
            command="npx",
            args=["-y", "@sugarforever/amap-mcp-server"],
            env={"AMAP_API_KEY": settings.amap_api_key},
            auto_expand=True
        )

        # Tạo nhiều Agent, chia sẻ cùng một công cụ MCP
        self.attraction_agent = SimpleAgent(
            name="AttractionSearchAgent",
            llm=self.llm,
            system_prompt=ATTRACTION_AGENT_PROMPT
        )
        self.attraction_agent.add_tool(self.mcp_tool)  # chia sẻ

        self.weather_agent = SimpleAgent(
            name="WeatherQueryAgent",
            llm=self.llm,
            system_prompt=WEATHER_AGENT_PROMPT
        )
        self.weather_agent.add_tool(self.mcp_tool)  # chia sẻ

        self.hotel_agent = SimpleAgent(
            name="HotelAgent",
            llm=self.llm,
            system_prompt=HOTEL_AGENT_PROMPT
        )
        self.hotel_agent.add_tool(self.mcp_tool)  # chia sẻ
```

Như vậy, ba Agent đều có thể dùng 16 công cụ của Amap, nhưng bên dưới chỉ có một tiến trình máy chủ MCP chạy. Khi chúng ta gọi phương thức `plan_trip` của `TripPlannerAgent`, ba Agent sẽ lần lượt gọi công cụ, mọi yêu cầu đều được gửi đến API Amap qua cùng một máy chủ MCP.

### 13.4.4 Tích hợp API ảnh Unsplash

Ngoài Amap, chúng ta còn cần lấy ảnh cho các điểm tham quan để kế hoạch du lịch sinh động, trực quan hơn. Chúng ta dùng API Unsplash để tìm kiếm ảnh điểm tham quan. Cần lưu ý Unsplash là dịch vụ nước ngoài, và là một trong số ít API ảnh có thể dùng miễn phí, nên kết quả tìm kiếm có thể chưa đủ chính xác. Trong dự án thực tế, có thể cân nhắc dùng API ảnh POI của Bing, Baidu hoặc Amap, nhưng những dịch vụ này thường phải trả phí.

Tích hợp API Unsplash khá đơn giản; chúng ta tạo lớp `UnsplashService` để đóng gói lời gọi API:

```python
# backend/app/services/unsplash_service.py
import requests
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class UnsplashService:
    """Dịch vụ ảnh Unsplash"""

    def __init__(self, access_key: str):
        self.access_key = access_key
        self.base_url = "https://api.unsplash.com"

    def search_photos(self, query: str, per_page: int = 10) -> List[Dict]:
        """Tìm kiếm ảnh"""
        try:
            url = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": per_page,
                "client_id": self.access_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Trích xuất URL ảnh
            photos = []
            for result in results:
                photos.append({
                    "url": result["urls"]["regular"],
                    "description": result.get("description", ""),
                    "photographer": result["user"]["name"]
                })

            return photos

        except Exception as e:
            logger.error(f"Tìm kiếm ảnh thất bại: {e}")
            return []

    def get_photo_url(self, query: str) -> Optional[str]:
        """Lấy URL của một ảnh"""
        photos = self.search_photos(query, per_page=1)
        return photos[0].get("url") if photos else None
```

Lớp dịch vụ này cung cấp hai phương thức: `search_photos` tìm nhiều ảnh, `get_photo_url` lấy URL của một ảnh. Chúng ta dùng dịch vụ này trong định tuyến API để lấy ảnh cho từng điểm tham quan:
```python
# backend/app/api/routes/trip.py
from app.services.unsplash_service import UnsplashService

unsplash_service = UnsplashService(settings.unsplash_access_key)

@router.post("/plan", response_model=TripPlan)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    # Sinh kế hoạch du lịch
    trip_plan = trip_planner_agent.plan_trip(request)

    # Lấy ảnh cho từng điểm tham quan
    for day in trip_plan.days:
        for attraction in day.attractions:
            if not attraction.image_url:
                image_url = unsplash_service.get_photo_url(
                    f"{attraction.name} {trip_plan.city}"
                )
                attraction.image_url = image_url

    return trip_plan
```

Lưu ý chúng ta không đóng gói Unsplash thành Tool hay công cụ MCP, mà gọi trực tiếp trong định tuyến API. Lý do là tìm kiếm ảnh không cần quyết định thông minh của Agent, chỉ là một bước tăng cường dữ liệu đơn giản. Nếu bạn muốn Agent tự quyết định có cần ảnh hay không, hoặc chọn nguồn ảnh khác nhau, có thể cân nhắc đóng gói thành Tool.

## 13.5 Phát triển frontend chi tiết

### 13.5.1 Kiến trúc Web tách biệt frontend/backend

Trước khi bắt đầu phát triển frontend, chúng ta cần hiểu mẫu kiến trúc của ứng dụng Web hiện đại. Trong thời kỳ đầu phát triển Web, frontend và backend trộn lẫn với nhau, ví dụ các công nghệ như PHP, JSP, mẫu HTML và mã logic nghiệp vụ viết trong cùng một tệp. Cách này tiện trong dự án nhỏ, nhưng trong dự án lớn sẽ gặp nhiều vấn đề: nhà phát triển frontend và backend phải phối hợp thường xuyên, mã khó tái sử dụng, kiểm thử khó khăn.

Ứng dụng Web hiện đại thường áp dụng kiến trúc <strong>tách biệt frontend/backend</strong>. Backend chỉ chịu trách nhiệm cung cấp giao diện API, trả về dữ liệu định dạng JSON. Frontend là một ứng dụng độc lập, gọi API backend qua yêu cầu HTTP, lấy dữ liệu rồi render trang. Kiến trúc này có vài ưu điểm rõ ràng: frontend và backend có thể phát triển độc lập, triển khai độc lập, kiểm thử độc lập; frontend có thể là ứng dụng Web, ứng dụng di động hoặc ứng dụng desktop, đều dùng chung một bộ API backend; frontend có thể dùng framework và chuỗi công cụ hiện đại, mang lại trải nghiệm người dùng tốt hơn.

Trong dự án trợ lý du lịch thông minh của chúng ta, backend được hiện thực bằng Python và FastAPI, cung cấp một giao diện API cốt lõi `POST /api/trip/plan`, nhận nhu cầu du lịch, trả về kế hoạch du lịch. Frontend được hiện thực bằng Vue 3 và TypeScript, là một ứng dụng đơn trang (SPA); người dùng điền biểu mẫu trong trình duyệt, nhấn nút "Bắt đầu lập kế hoạch", frontend gửi yêu cầu HTTP đến backend, chờ phản hồi, rồi render trang kết quả. Trong toàn bộ quá trình, trang không tải lại, trải nghiệm người dùng rất mượt.

Việc chọn công nghệ frontend cần xét vài yếu tố: hiệu quả phát triển, hiệu năng, hệ sinh thái, đường cong học tập. Như Bảng 13.2, dự án chọn công nghệ sau:

<div align="center">
  <p>Bảng 13.2 Công nghệ frontend</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-table-2.png" alt="" width="85%"/>
</div>

Cấu trúc thư mục dự án như sau:
```
frontend/
├── src/
│   ├── views/              # Component trang
│   │   ├── Home.vue        # Trang chủ (biểu mẫu)
│   │   └── Result.vue      # Trang kết quả
│   ├── services/           # Dịch vụ API
│   │   └── api.ts
│   ├── types/              # Định nghĩa kiểu
│   │   └── index.ts
│   ├── router/             # Cấu hình định tuyến
│   │   └── index.ts
│   ├── App.vue
│   └── main.ts
├── package.json
├── vite.config.ts
└── tsconfig.json
```

Trong đó thư mục `views` chứa component trang, thư mục `services` chứa logic gọi API, thư mục `types` chứa định nghĩa kiểu TypeScript, thư mục `router` chứa cấu hình định tuyến.

### 13.5.2 Định nghĩa kiểu

Trong mục 13.2, chúng ta dùng Pydantic định nghĩa mô hình dữ liệu ở backend, ví dụ `Location`, `Attraction`, `DayPlan`, `TripPlan`,... Ở frontend, chúng ta cần định nghĩa kiểu TypeScript tương ứng.

Hãy xem cách định nghĩa các kiểu này. Trước hết là kiểu `Location` cơ bản nhất, biểu diễn toạ độ kinh độ, vĩ độ:

```typescript
// frontend/src/types/index.ts
export interface Location {
  longitude: number
  latitude: number
}
```

Định nghĩa kiểu này hoàn toàn tương ứng với mô hình Pydantic ở backend. Lưu ý TypeScript dùng từ khoá `interface` để định nghĩa kiểu, kiểu trường phân tách bằng dấu hai chấm, không cần giá trị mặc định.

Tiếp theo là kiểu `Attraction`, biểu diễn thông tin điểm tham quan:

```typescript
export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  rating?: number
  image_url?: string
  ticket_price?: number
}
```

Lưu ý ở đây dùng kiểu `Location` làm kiểu trường, đây là kiểu lồng nhau. Dấu hỏi `?` biểu thị trường tuỳ chọn, tương ứng với `Optional` trong mô hình Pydantic ở backend.

Tương tự, chúng ta định nghĩa các kiểu `Meal`, `Hotel`, `Budget`, `WeatherInfo`,... Cuối cùng là kiểu `TripPlan` ở cấp cao nhất:

```typescript
export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}
```

Còn có kiểu request `TripPlanRequest`, tương ứng với mô hình request ở backend:

```typescript
export interface TripPlanRequest {
  city: string
  start_date: string
  end_date: string
  days: number
  preferences: string
  budget: string
  transportation: string
  accommodation: string
}
```

Những định nghĩa kiểu này có tác dụng gì? Thứ nhất, khi gọi API, TypeScript sẽ kiểm tra dữ liệu chúng ta truyền có khớp kiểu `TripPlanRequest` không. Nếu chúng ta vô tình viết `days` thành chuỗi, TypeScript sẽ báo lỗi ngay. Thứ hai, khi nhận phản hồi API, TypeScript sẽ kiểm tra dữ liệu phản hồi có khớp kiểu `TripPlan` không. Nếu cấu trúc dữ liệu backend trả về thay đổi, frontend sẽ phát hiện ngay. Cuối cùng, IDE có thể dựa trên định nghĩa kiểu để gợi ý mã; khi chúng ta gõ `tripPlan.`, IDE sẽ tự động liệt kê mọi trường khả dụng.

### 13.5.3 Đóng gói dịch vụ API

Đã có định nghĩa kiểu, chúng ta có thể đóng gói lời gọi API. Chúng ta tạo tệp `api.ts`, dùng Axios để gửi yêu cầu HTTP:

```typescript
import axios from 'axios'
import type { TripPlanRequest,TripPlan } from '../types'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 120000, // timeout 2 phút
  headers: {
    'Content-Type': 'application/json'
  }
})
```

Ở đây chúng ta tạo một instance Axios, cấu hình URL gốc, thời gian timeout và header yêu cầu. Vì sao đặt timeout là 2 phút? Vì sinh kế hoạch du lịch cần gọi nhiều Agent, mỗi Agent đều phải gọi LLM và API bên ngoài, toàn bộ quá trình có thể mất 10-30 giây. Nếu timeout quá ngắn, yêu cầu sẽ bị ngắt.

Tiếp theo chúng ta thêm interceptor. Interceptor có thể thực hiện một số logic chung trước khi gửi yêu cầu và sau khi nhận phản hồi, ví dụ ghi log, xử lý lỗi, xác thực,...:

```typescript
// Interceptor yêu cầu
api.interceptors.request.use(
  config => {
    console.log('Gửi yêu cầu:',config)
    return config
  },
  error => Promise.reject(error)
)

// Interceptor phản hồi
api.interceptors.response.use(
  response => {
    console.log('Nhận phản hồi:',response)
    return response
  },
  error => {
    console.error('Yêu cầu thất bại:',error)
    return Promise.reject(error)
  }
)
```

Cuối cùng chúng ta định nghĩa hàm API, đây là cửa ngõ duy nhất để frontend gọi backend:

```typescript
// Sinh kế hoạch du lịch
export const generateTripPlan = async (request: TripPlanRequest): Promise<TripPlan> => {
  const response = await api.post<TripPlan>('/trip/plan',request)
  return response.data
}
```

Lưu ý chữ ký kiểu của hàm này: tham số là kiểu `TripPlanRequest`, giá trị trả về là kiểu `Promise<TripPlan>`. Điều này có nghĩa là TypeScript sẽ kiểm tra tham số người gọi truyền có đáp ứng yêu cầu không, và cũng kiểm tra việc dùng giá trị trả về có đúng không.

### 13.5.4 Thiết kế biểu mẫu Home

Trang Home là cửa vào của người dùng, chứa một biểu mẫu để người dùng điền nhu cầu du lịch. Chúng ta dùng Composition API của Vue 3 để tổ chức mã:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { generateTripPlan } from '@/services/api'
import type { TripPlanRequest } from '@/types'

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const formData = ref<TripPlanRequest>({
  city: '',
  start_date: '',
  end_date: '',
  days: 3,
  preferences: 'Lịch sử văn hoá',
  budget: 'Trung bình',
  transportation: 'Giao thông công cộng',
  accommodation: 'Khách sạn bình dân'
})
</script>
```

Ở đây chúng ta dùng `ref` để tạo biến phản ứng. `formData` là dữ liệu biểu mẫu, kiểu là `TripPlanRequest`. `loading` biểu thị có đang tải hay không, `loadingProgress` biểu thị tiến độ tải, `loadingStatus` biểu thị văn bản trạng thái tải.

Logic gửi biểu mẫu như sau:

```typescript
const handleSubmit = async () => {
  loading.value = true
  loadingProgress.value = 0

  // Mô phỏng cập nhật tiến độ
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      if (loadingProgress.value <= 30) loadingStatus.value = '🔍 Đang tìm kiếm điểm tham quan...'
      else if (loadingProgress.value <= 50) loadingStatus.value = '🌤️ Đang truy vấn thời tiết...'
      else if (loadingProgress.value <= 70) loadingStatus.value = '🏨 Đang gợi ý khách sạn...'
      else loadingStatus.value = '📋 Đang sinh kế hoạch hành trình...'
    }
  },500)

  try {
    const response = await generateTripPlan(formData.value)
    clearInterval(progressInterval)
    loadingProgress.value = 100
    router.push({ name: 'result',state: { tripPlan: response } })
  } catch (error) {
    clearInterval(progressInterval)
    message.error('Sinh kế hoạch thất bại, vui lòng thử lại')
  } finally {
    loading.value = false
  }
}
```

Đoạn mã này làm vài việc. Thứ nhất, đặt `loading` thành true, hiển thị trạng thái tải. Sau đó, khởi động một bộ hẹn giờ, mỗi 500 mili giây cập nhật thanh tiến trình và văn bản trạng thái một lần. Đây là tiến độ mô phỏng, vì chúng ta không thể biết chính xác tiến độ xử lý của backend. Nhưng như vậy người dùng biết hệ thống đang làm việc, chứ không bị treo.

Tiếp theo, gọi hàm `generateTripPlan` để gửi yêu cầu API. Đây là thao tác bất đồng bộ, chúng ta dùng `await` chờ phản hồi. Nếu yêu cầu thành công, xoá bộ hẹn giờ, đặt tiến độ 100%, rồi chuyển sang trang kết quả và truyền dữ liệu kế hoạch du lịch sang. Nếu yêu cầu thất bại, hiển thị thông báo lỗi. Cuối cùng, dù thành công hay thất bại, đều đặt `loading` thành false, ẩn trạng thái tải.

Phần template dùng component của Ant Design Vue:

```vue
<template>
  <div class="home-container">
    <div class="page-header">
      <h1 class="page-title">✈️ Trợ lý du lịch thông minh</h1>
      <p class="page-subtitle">Lập kế hoạch du lịch cá nhân hoá dựa trên AI</p>
    </div>

    <a-card class="form-card">
      <a-form :model="formData" @finish="handleSubmit">
        <a-form-item label="Thành phố điểm đến" name="city" :rules="[{ required: true }]">
          <a-input v-model:value="formData.city" placeholder="Ví dụ: Bắc Kinh" />
        </a-form-item>

        <!-- Các mục biểu mẫu khác... -->

        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" :loading="loading">
            Bắt đầu lập kế hoạch
          </a-button>
        </a-form-item>

        <!-- Thanh tiến trình tải -->
        <a-form-item v-if="loading">
          <a-progress :percent="loadingProgress" status="active" />
          <p>{{ loadingStatus }}</p>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>
```

Lưu ý chỉ thị `v-model:value`, nó hiện thực ràng buộc dữ liệu hai chiều. Khi người dùng nhập nội dung vào ô nhập, `formData.city` sẽ tự động cập nhật. Khi giá trị `formData.city` thay đổi, nội dung ô nhập cũng tự động cập nhật.

### 13.5.5 Hiển thị trang Result

Trang Result là lõi của toàn bộ ứng dụng, hiển thị kế hoạch du lịch được sinh ra. Trang này gồm vài phần: tổng quan hành trình, chi tiết ngân sách, trực quan hoá bản đồ, chi tiết hành trình từng ngày, thông tin thời tiết.

Trước hết là trực quan hoá bản đồ. Chúng ta dùng JS API của Amap để đánh dấu vị trí điểm tham quan trên bản đồ:

```typescript
import AMapLoader from '@amap/amap-jsapi-loader'

const initMap = async () => {
  const AMap = await AMapLoader.load({
    key: 'your_amap_web_key',
    version: '2.0'
  })

  map = new AMap.Map('amap-container',{
    zoom: 12,
    center: [116.397128,39.916527]
  })

  // Thêm marker điểm tham quan
  tripPlan.value.days.forEach((day) => {
    day.attractions.forEach((attraction,index) => {
      const marker = new AMap.Marker({
        position: [attraction.location.longitude,attraction.location.latitude],
        title: attraction.name,
        label: { content: `${index + 1}`,direction: 'top' }
      })
      map.add(marker)
    })
  })
}
```

Đoạn mã này trước hết tải SDK của Amap, rồi tạo instance bản đồ, cuối cùng duyệt mọi điểm tham quan, tạo một marker cho mỗi điểm. Vị trí marker là toạ độ kinh độ, vĩ độ của điểm tham quan, lấy từ đối tượng `Attraction` ở backend.

Chức năng xuất dùng thư viện `html2canvas` và `jsPDF`. `html2canvas` có thể chuyển phần tử DOM thành Canvas, sau đó chúng ta có thể xuất Canvas thành ảnh hoặc PDF:

```typescript
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

// Xuất thành ảnh
const exportAsImage = async () => {
  const element = document.getElementById('trip-plan-content')
  const canvas = await html2canvas(element,{ scale: 2 })
  const link = document.createElement('a')
  link.download = `${tripPlan.value.city}Kế hoạch du lịch.png`
  link.href = canvas.toDataURL()
  link.click()
}

// Xuất thành PDF
const exportAsPDF = async () => {
  const element = document.getElementById('trip-plan-content')
  const canvas = await html2canvas(element,{ scale: 2 })
  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF('p','mm','a4')
  const imgWidth = 210
  const imgHeight = (canvas.height * imgWidth) / canvas.width
  pdf.addImage(imgData,'PNG',0,0,imgWidth,imgHeight)
  pdf.save(`${tripPlan.value.city}Kế hoạch du lịch.pdf`)
}
```

Qua những công nghệ frontend này, chúng ta hiện thực một ứng dụng Web hoàn chỉnh. Người dùng có thể điền biểu mẫu trong trình duyệt, gửi yêu cầu, chờ AI sinh kế hoạch du lịch, rồi xem chi tiết hành trình, thấy vị trí điểm tham quan trên bản đồ, còn có thể xuất thành ảnh hoặc PDF. Toàn bộ quá trình mượt mà tự nhiên, đó chính là sức hấp dẫn của ứng dụng Web hiện đại.

## 13.6 Hiện thực chức năng chi tiết

Mục này giới thiệu hiện thực các chức năng cốt lõi của trợ lý du lịch thông minh, bao gồm tính ngân sách, thanh tiến trình tải, chỉnh sửa hành trình, chức năng xuất và điều hướng bên.

### 13.6.1 Chức năng tính ngân sách

Khi lập kế hoạch du lịch, ngân sách là yếu tố rất quan trọng. Người dùng cần biết chuyến đi này tốn khoảng bao nhiêu tiền, tiền tiêu vào những đâu. Trợ lý du lịch thông minh của chúng ta cung cấp chức năng tính ngân sách tự động, chia chi phí thành bốn loại lớn: vé điểm tham quan, chỗ ở khách sạn, ăn uống và giao thông.

Logic tính ngân sách được hiện thực ở đâu? Chúng ta chọn hiện thực trong PlannerAgent ở backend. Vì sao không tính ở frontend? Vì ước tính ngân sách cần dựa trên giá vé điểm tham quan, khoảng giá khách sạn, tiêu chuẩn ăn uống,... Những thông tin này PlannerAgent đã lấy được khi sinh hành trình. Nếu tính ở frontend, sẽ phải lặp lại logic này, và có thể không chính xác.

Trong prompt của PlannerAgent, chúng ta yêu cầu rõ LLM sinh thông tin ngân sách:

```python
PLANNER_AGENT_PROMPT = """
Bạn là chuyên gia lập kế hoạch hành trình.

**Định dạng đầu ra:**
Trả về nghiêm ngặt theo định dạng JSON sau:
{
  ...
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}

**Yêu cầu lập kế hoạch:**
...
7. Bao gồm thông tin ngân sách, ước tính theo giá vé điểm tham quan, giá khách sạn, tiêu chuẩn ăn uống và phương tiện di chuyển
"""
```

LLM sẽ ước tính chi phí từng khoản dựa trên sắp xếp điểm tham quan, khách sạn, ăn uống trong hành trình. Ví dụ, nếu hành trình gồm Tử Cấm Thành (vé 60 tệ), Thiên Đàn (vé 15 tệ), Di Hoà Viên (vé 30 tệ), thì tổng chi phí vé điểm tham quan là 105 tệ. Nếu là hành trình 3 ngày 2 đêm, khách sạn bình dân (300 tệ/đêm), thì tổng chi phí khách sạn là 600 tệ.

Ở frontend, chúng ta dùng component Statistic của Ant Design Vue để hiển thị thông tin ngân sách. Component này chuyên dùng để hiển thị dữ liệu thống kê, hỗ trợ animation số, tiền tố hậu tố, kiểu tuỳ chỉnh,...:

```vue
<a-card v-if="tripPlan.budget" title="💰 Chi tiết ngân sách">
  <a-row :gutter="16">
    <a-col :span="6">
      <a-statistic title="Vé điểm tham quan" :value="tripPlan.budget.total_attractions" suffix="tệ" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="Chỗ ở khách sạn" :value="tripPlan.budget.total_hotels" suffix="tệ" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="Chi phí ăn uống" :value="tripPlan.budget.total_meals" suffix="tệ" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="Chi phí giao thông" :value="tripPlan.budget.total_transportation" suffix="tệ" />
    </a-col>
  </a-row>
  <a-divider />
  <a-row>
    <a-col :span="24" style="text-align: center;">
      <a-statistic
        title="Tổng chi phí ước tính"
        :value="tripPlan.budget.total"
        suffix="tệ"
        :value-style="{ color: '#cf1322',fontSize: '32px',fontWeight: 'bold' }"
      />
    </a-col>
  </a-row>
</a-card>
```

Đoạn mã này dùng bố cục lưới (`a-row` và `a-col`), hiển thị bốn khoản chi phí song song. Mỗi khoản chi phí dùng một component `a-statistic`, hiển thị tiêu đề và giá trị. Cuối cùng dùng một đường phân cách (`a-divider`), bên dưới hiển thị tổng chi phí bằng chữ đỏ cỡ lớn để làm nổi bật.

Lưu ý điều kiện render `v-if="tripPlan.budget"`. Vì thông tin ngân sách là tuỳ chọn (trong mô hình Pydantic định nghĩa là `Optional[Budget]`), nếu LLM không sinh thông tin ngân sách, thẻ này sẽ không hiển thị. Điều này thể hiện việc frontend xử lý chịu lỗi với dữ liệu.

### 13.6.2 Thanh tiến trình tải

Sinh kế hoạch du lịch là thao tác tốn thời gian. Backend cần lần lượt gọi AttractionSearchAgent, WeatherQueryAgent, HotelAgent và PlannerAgent, mỗi Agent đều phải gọi LLM và API bên ngoài. Toàn bộ quá trình có thể mất 10-30 giây. Nếu sau khi người dùng nhấn nút "Bắt đầu lập kế hoạch" mà trang không có phản hồi nào, người dùng sẽ nghĩ hệ thống bị treo, có thể tải lại trang hoặc nhấn lặp lại.

Để nâng cao trải nghiệm người dùng, chúng ta thêm thanh tiến trình tải và gợi ý trạng thái. Hiện tại chỉ là tiến độ mô phỏng, giúp người dùng biết hệ thống đang làm việc.

```typescript
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const handleSubmit = async () => {
  loading.value = true
  loadingProgress.value = 0

  // Mô phỏng cập nhật tiến độ
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      if (loadingProgress.value <= 30) loadingStatus.value = '🔍 Đang tìm kiếm điểm tham quan...'
      else if (loadingProgress.value <= 50) loadingStatus.value = '🌤️ Đang truy vấn thời tiết...'
      else if (loadingProgress.value <= 70) loadingStatus.value = '🏨 Đang gợi ý khách sạn...'
      else loadingStatus.value = '📋 Đang sinh kế hoạch hành trình...'
    }
  }, 500)

  try {
    const response = await generateTripPlan(formData.value)
    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '✅ Hoàn tất!'
    router.push({ name: 'result', state: { tripPlan: response } })
  } catch (error) {
    clearInterval(progressInterval)
    message.error('Sinh kế hoạch thất bại')
  } finally {
    loading.value = false
  }
}
```

### 13.6.3 Chức năng chỉnh sửa hành trình

Kế hoạch du lịch AI sinh ra tuy rất thông minh, nhưng có thể chưa hoàn toàn phù hợp nhu cầu cá nhân của người dùng. Ví dụ, người dùng có thể không thích một điểm tham quan nào đó và muốn xoá nó; hoặc muốn điều chỉnh thứ tự tham quan. Chúng ta cung cấp chức năng chỉnh sửa hành trình để người dùng tự định nghĩa hành trình.

Lõi của chức năng chỉnh sửa là <strong>quản lý trạng thái</strong>. Chúng ta cần duy trì hai trạng thái: kế hoạch hành trình hiện tại và kế hoạch hành trình gốc. Khi người dùng vào chế độ chỉnh sửa, chúng ta lưu bản sao của kế hoạch gốc. Nếu người dùng huỷ chỉnh sửa, khôi phục kế hoạch gốc. Nếu người dùng lưu thay đổi, cập nhật kế hoạch hiện tại:

```typescript
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)

// Vào chế độ chỉnh sửa
const toggleEditMode = () => {
  editMode.value = true
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
}
```

Lưu ý ở đây dùng `JSON.parse(JSON.stringify(...))` để sao chép sâu đối tượng. Vì sao không gán trực tiếp? Vì trong JavaScript đối tượng là kiểu tham chiếu; nếu gán trực tiếp, `originalPlan` và `tripPlan` sẽ trỏ đến cùng một đối tượng, sửa một cái sẽ ảnh hưởng cái kia. Sao chép sâu tạo ra một bản sao hoàn toàn độc lập.

Logic di chuyển điểm tham quan là hoán đổi vị trí hai phần tử trong mảng:

```typescript
// Di chuyển điểm tham quan
const moveAttraction = (dayIndex: number,attractionIndex: number,direction: 'up' | 'down') => {
  const attractions = tripPlan.value.days[dayIndex].attractions
  const newIndex = direction === 'up' ? attractionIndex - 1 : attractionIndex + 1

  if (newIndex >= 0 && newIndex < attractions.length) {
    [attractions[attractionIndex],attractions[newIndex]] =
    [attractions[newIndex],attractions[attractionIndex]]
  }
}
```

Ở đây dùng cú pháp gán phá cấu trúc ES6 để hoán đổi hai phần tử. `[a,b] = [b,a]` là cách hoán đổi rất thanh lịch, không cần biến tạm.

Xoá điểm tham quan dùng phương thức `splice` của mảng:

```typescript
// Xoá điểm tham quan
const deleteAttraction = (dayIndex: number,attractionIndex: number) => {
  tripPlan.value.days[dayIndex].attractions.splice(attractionIndex,1)
}
```

Khi lưu thay đổi, chúng ta cần khởi tạo lại bản đồ, vì vị trí điểm tham quan có thể đã thay đổi:

```typescript
// Lưu thay đổi
const saveChanges = () => {
  editMode.value = false
  message.success('Đã lưu thay đổi')
  initMap()  // Khởi tạo lại bản đồ
}

// Huỷ chỉnh sửa
const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = originalPlan.value
  }
  editMode.value = false
}
```

Trong template, chúng ta hiển thị UI khác nhau theo giá trị `editMode`. Ở chế độ chỉnh sửa, bên cạnh mỗi điểm tham quan sẽ hiển thị nút di chuyển lên, di chuyển xuống, xoá:

```vue
<div v-if="editMode" class="edit-buttons">
  <a-button size="small" @click="moveAttraction(dayIndex,index,'up')">Lên</a-button>
  <a-button size="small" @click="moveAttraction(dayIndex,index,'down')">Xuống</a-button>
  <a-button size="small" danger @click="deleteAttraction(dayIndex,index)">Xoá</a-button>
</div>
```

### 13.6.4 Chức năng xuất

Sau khi người dùng có kế hoạch du lịch ưng ý, có thể muốn lưu lại hoặc chia sẻ với bạn bè. Chúng ta cung cấp hai cách xuất: xuất thành ảnh và xuất thành PDF.

Lõi của chức năng xuất là thư viện `html2canvas`. Thư viện này có thể chuyển phần tử DOM thành Canvas, rồi chúng ta có thể xuất Canvas thành ảnh. Nhưng ở đây có một khó khăn kỹ thuật: bản đồ được render bằng Canvas, còn `html2canvas` có vấn đề tương thích khi xử lý Canvas lồng nhau.

Chúng ta đã thử nhiều giải pháp, bao gồm chuyển Canvas bản đồ thành ảnh rồi xuất, nhưng do cơ chế render Canvas của Amap và giới hạn cross-origin, giải pháp này không giải quyết triệt để vấn đề. Trong dự án thực tế, có thể cân nhắc các phương án thay thế sau:

1. <strong>Dùng API bản đồ tĩnh của Amap</strong>: gọi công cụ `maps_staticmap` để sinh ảnh bản đồ tĩnh, thay cho bản đồ động
2. <strong>Xuất riêng</strong>: xuất bản đồ và nội dung hành trình riêng, cuối cùng hợp nhất ở backend
3. <strong>Dùng dịch vụ chụp ảnh màn hình</strong>: dùng trình duyệt không giao diện như Puppeteer để chụp ảnh ở phía máy chủ
4. <strong>Đơn giản hoá nội dung xuất</strong>: ẩn bản đồ khi xuất, chỉ xuất nội dung văn bản

Trong hiện thực hiện tại, chúng ta dùng phương án đơn giản hoá: tạm ẩn phần bản đồ khi xuất, chỉ xuất nội dung văn bản của hành trình và thông tin điểm tham quan. Tuy đây không phải phương án lý tưởng nhất, nhưng đảm bảo chức năng xuất khả dụng.

Logic xuất thành ảnh rất đơn giản:

```typescript
import html2canvas from 'html2canvas'

const exportAsImage = async () => {
  const element = document.getElementById('trip-plan-content')
  if (!element) return

  const canvas = await html2canvas(element,{
    backgroundColor: '#ffffff',
    scale: 2,
    useCORS: true
  })

  const link = document.createElement('a')
  link.download = `${tripPlan.value.city}Kế hoạch du lịch.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
  message.success('Xuất thành công!')
}
```

`scale: 2` biểu thị dùng độ phân giải gấp 2, nhờ vậy ảnh xuất ra rõ nét hơn. `useCORS: true` cho phép tải ảnh cross-origin, điều này quan trọng với ảnh điểm tham quan (từ Unsplash).

Xuất thành PDF cần thêm bước: trước hết chuyển thành Canvas, rồi chuyển thành ảnh, cuối cùng thêm vào PDF:

```typescript
import jsPDF from 'jspdf'

const exportAsPDF = async () => {
  // Trước hết chụp bản đồ
  await captureMapImage()

  const element = document.getElementById('trip-plan-content')
  if (!element) return

  const canvas = await html2canvas(element,{
    backgroundColor: '#ffffff',
    scale: 2,
    useCORS: true,
    allowTaint: true
  })

  // Khôi phục bản đồ
  restoreMap()

  const pdf = new jsPDF('p','mm','a4')
  const imgData = canvas.toDataURL('image/png')
  const imgWidth = 210  // Chiều rộng A4
  const imgHeight = (canvas.height * imgWidth) / canvas.width

  pdf.addImage(imgData,'PNG',0,0,imgWidth,imgHeight)
  pdf.save(`${tripPlan.value.city}Kế hoạch du lịch.pdf`)
  message.success('Xuất thành công!')
}
```

Ở đây cần tính chiều cao ảnh, giữ tỉ lệ khung hình. Chiều rộng giấy A4 là 210mm, chúng ta tính chiều cao tương ứng theo tỉ lệ khung hình của Canvas.

### 13.6.5 Điều hướng bên và nhảy đến anchor

Trang Result có nhiều nội dung, bao gồm tổng quan hành trình, chi tiết ngân sách, bản đồ, hành trình từng ngày, thông tin thời tiết,... Nếu người dùng muốn nhanh chóng nhảy đến một phần nào đó, phải cuộn một quãng rất dài. Chúng ta cung cấp chức năng điều hướng bên và nhảy đến anchor, giúp người dùng định vị nhanh.

Điều hướng bên dùng component Menu của Ant Design Vue:

```vue
<a-menu
  v-model:selectedKeys="[activeSection]"
  mode="inline"
  @click="scrollToSection"
>
  <a-menu-item key="overview">📋 Tổng quan hành trình</a-menu-item>
  <a-menu-item key="budget">💰 Chi tiết ngân sách</a-menu-item>
  <a-menu-item key="map">🗺️ Bản đồ</a-menu-item>
  <a-menu-item key="days">📅 Hành trình từng ngày</a-menu-item>
  <a-menu-item key="weather">🌤️ Thời tiết</a-menu-item>
</a-menu>
```

Khi nhấn mục menu, gọi hàm `scrollToSection`:

```typescript
const activeSection = ref('overview')

// Cuộn đến khu vực chỉ định
const scrollToSection = ({ key }: { key: string }) => {
  activeSection.value = key
  const element = document.getElementById(key)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth',block: 'start' })
  }
}
```

`scrollIntoView` là API gốc của trình duyệt, có thể đưa phần tử vào vùng nhìn thấy. `behavior: 'smooth'` biểu thị cuộn mượt, thay vì nhảy tức thời. `block: 'start'` biểu thị đỉnh phần tử căn vào đỉnh vùng nhìn thấy.

Ở các phần khác nhau của trang, chúng ta cần thêm id tương ứng:

```vue
<div id="overview">
  <!-- Nội dung tổng quan hành trình -->
</div>

<div id="budget">
  <!-- Nội dung chi tiết ngân sách -->
</div>

<div id="map">
  <!-- Nội dung bản đồ -->
</div>
```

Như vậy, khi người dùng nhấn một mục trong điều hướng bên, trang sẽ cuộn mượt đến phần tương ứng.

Qua hiện thực những chức năng này, trợ lý du lịch thông minh của chúng ta không chỉ sinh được kế hoạch du lịch mà còn cung cấp nhiều chức năng tương tác phong phú: tính ngân sách giúp người dùng hiểu chi phí, thanh tiến trình tải khiến việc chờ đợi không còn lo lắng, chỉnh sửa hành trình giúp kế hoạch phù hợp nhu cầu cá nhân hơn, chức năng xuất giúp kế hoạch có thể chia sẻ và lưu trữ, điều hướng bên giúp trang dài dễ duyệt. Sự kết hợp của những chức năng này tạo thành một ứng dụng Web hoàn chỉnh, dễ dùng, thực dụng.

## 13.7 Kết luận

Chúc mừng bạn đã hoàn thành chương 13!

Qua chương này, bạn không chỉ học được cách xây dựng một ứng dụng trợ lý du lịch thông minh hoàn chỉnh, quan trọng hơn là đã nắm được:

1. <strong>Tư duy thiết kế hệ thống</strong>: cách phân rã vấn đề phức tạp thành nhiều nhiệm vụ đơn giản
2. <strong>Năng lực thực hành kỹ thuật</strong>: cách chuyển kiến thức lý thuyết thành mã có thể chạy
3. <strong>Năng lực phát triển full-stack</strong>: cách tích hợp công nghệ frontend và backend
4. <strong>Phát triển ứng dụng AI</strong>: cách dùng LLM để xây dựng ứng dụng thực dụng

Dự án này là điểm khởi đầu, không phải điểm kết thúc. Bạn có thể dựa trên dự án này để:

- Thêm nhiều chức năng hơn
- Tối ưu trải nghiệm người dùng
- Mở rộng sang lĩnh vực khác (như trợ lý mua sắm thông minh, trợ lý học tập thông minh,...)
- Triển khai vào môi trường sản xuất, phục vụ người dùng thật

Cách học tốt nhất là thực hành. Đừng chỉ đọc mã, mà hãy tự tay sửa, mở rộng, tối ưu. Mỗi lần thực hành sẽ giúp bạn hiểu sâu hơn về hệ thống đa agent.

Chúc bạn ngày càng tiến xa trên con đường phát triển ứng dụng AI!

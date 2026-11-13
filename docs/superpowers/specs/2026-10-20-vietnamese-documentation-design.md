# Thiết kế bản dịch tiếng Việt cho bộ sách Hello-Agents

## Mục tiêu

Tạo một bản tiếng Việt đầy đủ cho bộ sách chính trong `docs/`, giữ nguyên các bản tiếng Trung và tiếng Anh, đồng thời cung cấp điều hướng độc lập và liên kết ngôn ngữ rõ ràng.

## Phạm vi

Bản dịch gồm 19 tệp nội dung và điều hướng:

- `docs/vi/README.md`
- `docs/vi/Preface.md`
- `docs/vi/_sidebar.md`
- `docs/vi/chapter1/Chuong1-Gioi-thieu-ve-Agent.md`
- `docs/vi/chapter2/Chuong2-Lich-su-phat-trien-cua-Agent.md`
- `docs/vi/chapter3/Chuong3-Co-so-mo-hinh-ngon-ngu-lon.md`
- `docs/vi/chapter4/Chuong4-Xay-dung-cac-mo-hinh-Agent-kinh-dien.md`
- `docs/vi/chapter5/Chuong5-Xay-dung-Agent-voi-nen-tang-low-code.md`
- `docs/vi/chapter6/Chuong6-Thuc-hanh-phat-trien-voi-framework.md`
- `docs/vi/chapter7/Chuong7-Xay-dung-framework-Agent-cua-ban.md`
- `docs/vi/chapter8/Chuong8-Bo-nho-va-truy-xuat.md`
- `docs/vi/chapter9/Chuong9-Ky-thuat-ngu-canh.md`
- `docs/vi/chapter10/Chuong10-Giao-thuc-giao-tiep-Agent.md`
- `docs/vi/chapter11/Chuong11-Agentic-RL.md`
- `docs/vi/chapter12/Chuong12-Danh-gia-hieu-nang-Agent.md`
- `docs/vi/chapter13/Chuong13-Tro-ly-du-lich-thong-minh.md`
- `docs/vi/chapter14/Chuong14-Agent-nghien-cuu-chuyen-sau-tu-dong.md`
- `docs/vi/chapter15/Chuong15-Xay-dung-thi-tran-cyber.md`
- `docs/vi/chapter16/Chuong16-Do-an-tot-nghiep.md`

Ngoài ra, cập nhật liên kết chọn ngôn ngữ trong các trang đầu hiện có khi cần để người đọc có thể chuyển sang bản tiếng Việt.

Không thuộc phạm vi: `Extra-Chapter/`, `code/`, `Co-creation-projects/`, nội dung bên trong ảnh, dữ liệu mẫu và chuỗi giao diện của các dự án minh họa.

## Nguồn và nguyên tắc đối chiếu

- Bản tiếng Trung là nguồn chuẩn về độ đầy đủ và các cập nhật nội dung.
- Bản tiếng Anh dùng để đối chiếu thuật ngữ kỹ thuật và phát hiện khác biệt cấu trúc.
- Khi hai bản khác nhau, giữ nội dung đầy đủ hơn từ bản tiếng Trung; dùng cách gọi tiếng Anh phổ biến cho thuật ngữ không có bản dịch tiếng Việt tự nhiên.
- Giữ nguyên ý nghĩa, mức độ chi tiết, thứ tự mục, cảnh báo và ví dụ. Không tóm tắt hoặc tự bổ sung kiến thức.

## Quy tắc dịch

Dịch toàn bộ văn xuôi, tiêu đề, nhãn bảng, chú thích, ghi chú, cảnh báo, câu hỏi bài tập, mô tả hình và văn bản trình bày trong sơ đồ Mermaid.

Giữ nguyên khi việc dịch có thể làm hỏng tính chính xác hoặc khả năng thực thi:

- mã nguồn, lệnh shell, tên biến, tên hàm, tên lớp và khóa cấu hình;
- URL, đường dẫn kỹ thuật bắt buộc, tên API, tên mô hình, tên thư viện và tên sản phẩm;
- biểu thức toán học, trích dẫn BibTeX và dữ liệu máy đọc;
- đầu ra chương trình khi đầu ra đó được dùng để minh họa chính xác hành vi của chương trình.

Thuật ngữ dùng nhất quán: giữ `Agent`, `LLM`, `prompt`, `token`, `embedding`, `RAG`, `tool`, `workflow`, `framework`, `Memory`, `MCP`, `A2A`, `SFT` và `GRPO` khi đây là cách gọi kỹ thuật rõ nghĩa hơn; giải thích bằng tiếng Việt ở lần xuất hiện đầu tiên nếu bản gốc có giải thích tương ứng.

## Cấu trúc và liên kết

- Bản tiếng Việt nằm hoàn toàn trong `docs/vi/`.
- Các chương dùng tên tệp ASCII có dấu gạch nối để liên kết ổn định trên mọi nền tảng.
- `docs/vi/_sidebar.md` liên kết đủ lời nói đầu và 16 chương theo đúng năm phần của sách.
- Liên kết hình ảnh từ tệp tiếng Việt trỏ tới tài nguyên dùng chung trong `docs/images/` bằng đường dẫn tương đối phù hợp với độ sâu thư mục.
- Liên kết nội bộ trỏ tới tệp tiếng Việt tương ứng nếu tệp đích thuộc phạm vi dịch; các liên kết ngoài và liên kết tới mã nguồn giữ nguyên.
- Trang đầu tiếng Việt cung cấp liên kết chuyển sang bản Trung và bản Anh; các trang đầu hiện có bổ sung liên kết `Tiếng Việt`.

## Kiểm tra chất lượng

Sau khi dịch, thực hiện các kiểm tra sau:

1. Đủ 19 tệp đã liệt kê và không có tệp rỗng.
2. Mọi liên kết Markdown cục bộ và đường dẫn ảnh trong bản tiếng Việt đều trỏ tới tệp tồn tại.
3. Số lượng và loại hàng rào mã được bảo toàn; không dịch nội dung mã có thể thực thi.
4. Không còn các đoạn văn tiếng Trung hoặc tiếng Anh chưa dịch ngoài những ngoại lệ kỹ thuật đã quy định.
5. Điều hướng tiếng Việt mở được trang đầu, lời nói đầu và đủ 16 chương.
6. Kiểm tra thủ công một mẫu ở đầu, giữa và cuối mỗi chương để xác nhận tiêu đề, bảng, hình ảnh và khối mã hiển thị đúng.
7. Khởi chạy trang tài liệu hiện có và mở bản tiếng Việt trong trình duyệt để kiểm tra bề mặt thực tế.

## Tiêu chí hoàn thành

Công việc hoàn thành khi toàn bộ bộ sách chính có bản tiếng Việt đầy đủ trong `docs/vi/`, người đọc có thể điều hướng qua mọi chương, các tài nguyên hiển thị đúng, nội dung kỹ thuật vẫn chính xác và không có phần văn xuôi nào bị bỏ sót hoặc thay bằng nội dung rút gọn.

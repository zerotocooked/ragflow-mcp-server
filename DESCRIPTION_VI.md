# RAGFlow MCP Server - Mô Tả Chi Tiết

## Tổng Quan Dự Án

**RAGFlow MCP Server** là một triển khai Model Context Protocol (MCP) kết nối khả năng xử lý tài liệu và tìm kiếm ngữ nghĩa mạnh mẽ của RAGFlow với các môi trường phát triển hiện đại, đặc biệt là Cursor IDE. Server này cho phép các nhà phát triển tích hợp liền mạch hệ thống quản lý kiến thức được hỗ trợ bởi AI của RAGFlow trực tiếp vào quy trình làm việc của họ.

## Dự Án Này Là Gì?

Dự án này cung cấp một MCP server sẵn sàng cho production hoạt động như một middleware thông minh giữa:
- **RAGFlow**: Hệ thống Retrieval-Augmented Generation (RAG) tiên tiến cho xử lý tài liệu và tìm kiếm ngữ nghĩa
- **Cursor IDE**: Trình soạn thảo code hiện đại được hỗ trợ bởi AI
- **Quy Trình Phát Triển**: Cho phép nhà phát triển truy vấn, quản lý và tìm kiếm thông qua cơ sở kiến thức mà không cần rời khỏi IDE

## Mục Đích Cốt Lõi

Mục tiêu chính của RAGFlow MCP Server là loại bỏ việc chuyển đổi ngữ cảnh cho nhà phát triển bằng cách đưa khả năng quản lý tài liệu và tìm kiếm ngữ nghĩa trực tiếp vào môi trường phát triển. Thay vì chuyển đổi giữa trình soạn thảo code và giao diện web riêng biệt, bạn có thể:

1. Tải lên tài liệu kỹ thuật, tham chiếu API và bài viết kiến thức
2. Thực hiện tìm kiếm ngữ nghĩa để tìm thông tin liên quan
3. Quản lý các bộ sưu tập tài liệu của bạn
4. Giữ cơ sở kiến thức đồng bộ với quy trình phát triển

Tất cả điều này xảy ra trong IDE của bạn thông qua các tương tác ngôn ngữ tự nhiên.

## Khả Năng Chính

### 1. Quản Lý Tài Liệu
- **Tải Lên Tài Liệu**: Thêm tài liệu mới vào cơ sở kiến thức RAGFlow với embedding tự động
- **Cập Nhật Tài Liệu**: Sửa đổi tài liệu hiện có và kích hoạt re-embedding để giữ cơ sở kiến thức cập nhật
- **Xóa Tài Liệu**: Loại bỏ tài liệu lỗi thời hoặc không cần thiết
- **Liệt Kê Tài Liệu**: Duyệt và tìm kiếm thông qua các bộ sưu tập tài liệu của bạn

### 2. Tìm Kiếm Ngữ Nghĩa
- **Truy Xuất Thông Minh**: Tìm thông tin liên quan bằng cách sử dụng truy vấn ngôn ngữ tự nhiên
- **Chấm Điểm Tương Đồng**: Nhận kết quả được xếp hạng theo độ tương đồng ngữ nghĩa
- **Nhận Thức Ngữ Cảnh**: Hiểu ý nghĩa đằng sau các truy vấn, không chỉ khớp từ khóa
- **Kết Quả Có Thể Cấu Hình**: Kiểm soát số lượng và chất lượng kết quả tìm kiếm

### 3. Tổ Chức Dataset
- **Nhiều Dataset**: Tổ chức tài liệu thành các bộ sưu tập logic
- **Khám Phá Dataset**: Liệt kê và khám phá các dataset có sẵn
- **Tìm Kiếm Đa Dataset**: Tìm kiếm trên toàn bộ cơ sở kiến thức hoặc các dataset cụ thể

### 4. Tích Hợp Thân Thiện Với Nhà Phát Triển
- **Tích Hợp IDE**: Hoạt động trực tiếp trong Cursor IDE thông qua giao thức MCP
- **Hoạt Động Bất Đồng Bộ**: Các cuộc gọi API không chặn cho trải nghiệm người dùng mượt mà
- **An Toàn Kiểu**: Type hints đầy đủ và xác thực Pydantic cho độ tin cậy
- **Xử Lý Lỗi**: Xử lý lỗi toàn diện với thông báo có ý nghĩa

## Kiến Trúc Kỹ Thuật

### Các Thành Phần

1. **MCP Server (`server.py`)**
   - Triển khai đặc tả Model Context Protocol
   - Cung cấp các công cụ cho các thao tác RAGFlow
   - Xử lý vòng đời request/response
   - Quản lý vòng đời server và cấu hình

2. **RAGFlow Client (`client.py`)**
   - Trừu tượng hóa các tương tác RAGFlow API
   - Triển khai logic retry và xử lý lỗi
   - Quản lý kết nối HTTP và xác thực
   - Cung cấp giao diện async cho tất cả các thao tác

3. **Quản Lý Cấu Hình (`config.py`)**
   - Cấu hình dựa trên môi trường
   - Xác thực và giá trị mặc định
   - Xử lý thông tin xác thực an toàn
   - Tùy chọn triển khai linh hoạt

4. **Mô Hình Dữ Liệu (`models.py`)**
   - Các mô hình Pydantic cho an toàn kiểu
   - Xác thực request/response
   - Tài liệu schema
   - Thực thi hợp đồng API

5. **Xử Lý Lỗi (`errors.py`)**
   - Hệ thống phân cấp exception tùy chỉnh
   - Thông báo lỗi chi tiết
   - Các loại lỗi được phân loại
   - Thông tin lỗi có thể hành động

## Trường Hợp Sử Dụng

### 1. Tìm Kiếm Tài Liệu Trong Quá Trình Phát Triển
Trong khi lập trình, nhà phát triển có thể nhanh chóng tìm kiếm qua:
- Tài liệu API
- Trang wiki nội bộ
- Đặc tả kỹ thuật
- Hướng dẫn thực hành tốt nhất
- Ví dụ code và snippets

### 2. Bảo Trì Cơ Sở Kiến Thức
Các nhóm phát triển có thể:
- Giữ tài liệu đồng bộ với thay đổi code
- Tải lên tài liệu mới khi chúng được tạo
- Cập nhật tài liệu hiện có khi quy trình thay đổi
- Loại bỏ thông tin lỗi thời

### 3. Onboarding Thành Viên Mới
Nhà phát triển mới có thể:
- Tìm kiếm hướng dẫn cài đặt
- Tìm tài liệu kiến trúc
- Khám phá tiêu chuẩn lập trình
- Truy cập tài liệu đào tạo

### 4. Nghiên Cứu và Khám Phá
Nhà phát triển có thể:
- Khám phá các khái niệm kỹ thuật liên quan
- Tìm các vấn đề và giải pháp tương tự
- Khám phá các mẫu code liên quan
- Truy cập ngữ cảnh lịch sử

## Công Nghệ Sử Dụng

- **Python 3.8+**: Python hiện đại với hỗ trợ async/await
- **MCP Protocol**: Giao thức chuẩn cho tích hợp AI-editor
- **aiohttp**: Client HTTP bất đồng bộ cho RAGFlow API
- **Pydantic**: Xác thực dữ liệu và quản lý cài đặt
- **pytest**: Framework kiểm thử toàn diện
- **Type Hints**: Phủ sóng kiểu đầy đủ cho hỗ trợ IDE

## Nguyên Tắc Thiết Kế

1. **Đơn Giản**: Dễ cài đặt, cấu hình và sử dụng
2. **Độ Tin Cậy**: Xử lý lỗi mạnh mẽ và logic retry
3. **Hiệu Năng**: Hoạt động async và sử dụng API hiệu quả
4. **Bảo Mật**: Quản lý thông tin xác thực an toàn và xác thực API
5. **Khả Năng Mở Rộng**: Kiến trúc sạch cho các cải tiến trong tương lai
6. **Trải Nghiệm Nhà Phát Triển**: Tài liệu rõ ràng và thông báo lỗi hữu ích

## Trạng Thái Dự Án

**Phiên Bản Hiện Tại**: 0.1.0 (Alpha)

Dự án đang trong quá trình phát triển tích cực với chức năng cốt lõi được triển khai và kiểm thử. Nó đã sẵn sàng cho những người dùng đầu tiên và kiểm thử trong môi trường phát triển.

### Những Gì Đang Hoạt Động
- ✅ Triển khai MCP server cốt lõi
- ✅ Tích hợp RAGFlow API
- ✅ Tải lên và quản lý file
- ✅ Tìm kiếm ngữ nghĩa
- ✅ Thao tác dataset
- ✅ Xử lý lỗi và logic retry
- ✅ Quản lý cấu hình
- ✅ Phủ sóng test cơ bản

### Những Gì Sắp Tới
- 🔄 Tùy chọn embedding nâng cao
- 🔄 Thao tác hàng loạt
- 🔄 Bộ lọc tìm kiếm nâng cao
- 🔄 Tối ưu hóa hiệu năng
- 🔄 Mở rộng tài liệu
- 🔄 Phân phối package PyPI

## Đối Tượng Mục Tiêu

Dự án này được thiết kế cho:

- **Nhà Phát Triển Phần Mềm**: Sử dụng Cursor IDE muốn quản lý kiến thức tích hợp
- **Nhóm Phát Triển**: Cần chia sẻ và tìm kiếm qua tài liệu kỹ thuật
- **Technical Writers**: Duy trì tài liệu cùng với code
- **Kỹ Sư DevOps**: Quản lý tài liệu cơ sở hạ tầng và runbooks
- **Data Scientists**: Làm việc với RAGFlow cho nghiên cứu và thử nghiệm

## Điểm Khác Biệt

Không giống như các công cụ tài liệu truyền thống hoặc hệ thống RAG riêng biệt:

1. **Tích Hợp IDE**: Hoạt động tự nhiên trong môi trường phát triển của bạn
2. **Chuẩn MCP**: Sử dụng chuẩn Model Context Protocol đang nổi lên
3. **Async First**: Được xây dựng cho hiệu năng với các hoạt động async xuyên suốt
4. **Type Safe**: Type hints và xác thực toàn diện
5. **Sẵn Sàng Production**: Xử lý lỗi đúng đắn, logic retry và kiểm thử
6. **Mã Nguồn Mở**: Giấy phép MIT, miễn phí sử dụng và sửa đổi

## Cộng Đồng và Hỗ Trợ

Đây là một dự án mã nguồn mở chào đón các đóng góp từ:
- Triển khai tính năng
- Sửa lỗi
- Cải thiện tài liệu
- Tăng cường phủ sóng test
- Tối ưu hóa hiệu năng
- Ví dụ tích hợp

## Tầm Nhìn Tương Lai

Tầm nhìn dài hạn cho RAGFlow MCP Server bao gồm:

1. **Hỗ Trợ Đa IDE**: Mở rộng ra ngoài Cursor sang các editor tương thích MCP khác
2. **Tìm Kiếm Nâng Cao**: Bộ lọc tìm kiếm và tùy chọn xếp hạng tinh vi hơn
3. **Tính Năng Cộng Tác**: Quản lý tài liệu dựa trên nhóm
4. **Phân Tích**: Thông tin chi tiết về sử dụng và phân tích tìm kiếm
5. **Hệ Thống Plugin**: Kiến trúc có thể mở rộng cho các tích hợp tùy chỉnh
6. **Triển Khai Cloud**: Tùy chọn dịch vụ được lưu trữ cho các nhóm

## Giấy Phép

Giấy phép MIT - Miễn phí cho sử dụng cá nhân và thương mại.

## Hướng Dẫn Cài Đặt Nhanh

### Cài Đặt Từ Mã Nguồn

```bash
git clone <repository-url>
cd ragflow-mcp-server
pip install -e .
```

### Cấu Hình

Tạo file `.env` hoặc thiết lập các biến môi trường:

```bash
RAGFLOW_BASE_URL=http://localhost:9380
RAGFLOW_API_KEY=your_api_key_here
```

### Chạy Server

```bash
python -m ragflow_mcp_server
```

### Cấu Hình Cursor IDE

Thêm vào file cấu hình MCP của Cursor:

```json
{
  "mcpServers": {
    "ragflow": {
      "command": "python",
      "args": ["-m", "ragflow_mcp_server"],
      "env": {
        "RAGFLOW_BASE_URL": "http://localhost:9380",
        "RAGFLOW_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Các Công Cụ MCP Có Sẵn

### ragflow_upload_file
Tải lên và embed file mới vào RAGFlow.

### ragflow_update_file
Cập nhật file hiện có và kích hoạt re-embedding.

### ragflow_search
Tìm kiếm qua cơ sở kiến thức RAGFlow.

### ragflow_list_files
Liệt kê tất cả các file trong dataset.

### ragflow_delete_file
Xóa file khỏi RAGFlow.

### ragflow_get_datasets
Lấy danh sách các dataset có sẵn.

## Đóng Góp

Chúng tôi chào đón mọi đóng góp! Vui lòng:

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/amazing-feature`)
3. Commit thay đổi (`git commit -m 'Add amazing feature'`)
4. Push lên branch (`git push origin feature/amazing-feature`)
5. Mở Pull Request

## Liên Hệ và Hỗ Trợ

- **Tài liệu**: Xem README.md và các file trong thư mục docs
- **Báo lỗi**: Mở issue trên GitHub repository
- **Thảo luận**: Tham gia discussions trên GitHub

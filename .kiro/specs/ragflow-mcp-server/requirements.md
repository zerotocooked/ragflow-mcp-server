# Requirements Document

## Introduction

Dự án này sẽ tạo ra một MCP (Model Context Protocol) server để kết nối Cursor IDE với RAGFlow API. Server này sẽ cho phép người dùng thực hiện các thao tác quản lý tài liệu và tìm kiếm thông qua RAGFlow trực tiếp từ Cursor, bao gồm upload file mới, cập nhật file đã tồn tại, và thực hiện tìm kiếm.

## Requirements

### Requirement 1

**User Story:** Là một developer sử dụng Cursor, tôi muốn upload và embed một file mới vào RAGFlow, để có thể sử dụng nội dung file đó trong các tác vụ AI sau này.

#### Acceptance Criteria

1. WHEN người dùng gọi lệnh upload file THEN hệ thống SHALL gửi file đến RAGFlow API và thực hiện embedding
2. WHEN file được upload thành công THEN hệ thống SHALL trả về thông tin xác nhận và ID của file
3. IF file đã tồn tại với cùng tên THEN hệ thống SHALL thông báo lỗi và yêu cầu xác nhận ghi đè
4. WHEN quá trình embedding hoàn tất THEN hệ thống SHALL thông báo trạng thái thành công

### Requirement 2

**User Story:** Là một developer, tôi muốn cập nhật và re-embed một file đã tồn tại trong RAGFlow, để đảm bảo nội dung mới nhất được sử dụng trong các tìm kiếm.

#### Acceptance Criteria

1. WHEN người dùng gọi lệnh update file với file ID THEN hệ thống SHALL thay thế nội dung file cũ
2. WHEN file được cập nhật THEN hệ thống SHALL tự động thực hiện re-embedding
3. IF file ID không tồn tại THEN hệ thống SHALL trả về lỗi "file not found"
4. WHEN quá trình re-embedding hoàn tất THEN hệ thống SHALL thông báo trạng thái cập nhật thành công

### Requirement 3

**User Story:** Là một developer, tôi muốn thực hiện tìm kiếm trong RAGFlow, để có thể tìm thấy thông tin liên quan từ các tài liệu đã được embed.

#### Acceptance Criteria

1. WHEN người dùng nhập query tìm kiếm THEN hệ thống SHALL gửi request đến RAGFlow search API
2. WHEN tìm kiếm thành công THEN hệ thống SHALL trả về danh sách kết quả với điểm relevance
3. WHEN không có kết quả THEN hệ thống SHALL thông báo "no results found"
4. IF query rỗng hoặc không hợp lệ THEN hệ thống SHALL trả về lỗi validation

### Requirement 4

**User Story:** Là một developer, tôi muốn cấu hình kết nối đến RAGFlow API, để có thể sử dụng server với các instance RAGFlow khác nhau.

#### Acceptance Criteria

1. WHEN khởi động MCP server THEN hệ thống SHALL đọc cấu hình API endpoint và authentication
2. WHEN cấu hình không hợp lệ THEN hệ thống SHALL thông báo lỗi cấu hình cụ thể
3. WHEN kết nối đến RAGFlow thất bại THEN hệ thống SHALL retry với exponential backoff
4. IF authentication token hết hạn THEN hệ thống SHALL thông báo lỗi authentication

### Requirement 5

**User Story:** Là một developer, tôi muốn xem danh sách các file đã upload trong RAGFlow, để có thể quản lý và theo dõi các tài liệu.

#### Acceptance Criteria

1. WHEN người dùng gọi lệnh list files THEN hệ thống SHALL trả về danh sách tất cả files với metadata
2. WHEN danh sách rỗng THEN hệ thống SHALL thông báo "no files found"
3. WHEN có lỗi kết nối THEN hệ thống SHALL thông báo lỗi network cụ thể
4. WHEN trả về danh sách THEN mỗi file SHALL bao gồm ID, tên, kích thước, và ngày tạo

### Requirement 6

**User Story:** Là một developer, tôi muốn xóa file khỏi RAGFlow, để có thể dọn dẹp các tài liệu không cần thiết.

#### Acceptance Criteria

1. WHEN người dùng gọi lệnh delete file với file ID THEN hệ thống SHALL xóa file khỏi RAGFlow
2. WHEN xóa thành công THEN hệ thống SHALL thông báo xác nhận
3. IF file ID không tồn tại THEN hệ thống SHALL trả về lỗi "file not found"
4. WHEN có lỗi trong quá trình xóa THEN hệ thống SHALL thông báo lỗi cụ thể
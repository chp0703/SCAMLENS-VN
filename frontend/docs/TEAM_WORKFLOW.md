# Frontend Team Workflow

Tài liệu này thống nhất workflow cho ba Frontend developers của ScamLens VN. Nội dung bổ sung cho repository review rules và `AGENTS.md`; tài liệu không cấp quyền cho Codex thực hiện Git mutation.

## Frontend team và trách nhiệm hiện tại

Frontend team có đúng ba thành viên trực tiếp phát triển:

| GitHub username                                     | Role               | Trách nhiệm hiện tại hoặc dự kiến                                                                                                       |
| --------------------------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| [`kentlatoi`](https://github.com/kentlatoi)         | Frontend Lead      | Setup và quản lý Frontend Foundation; phụ trách architecture, development workflow, code quality; điều phối integration và code review. |
| [`thanhhuong107`](https://github.com/thanhhuong107) | Frontend Developer | Phụ trách Sitemap và User Flow trong giai đoạn đầu; phát triển Frontend modules được phân công sau khi team chốt thiết kế.              |
| [`phkhoiit-1508`](https://github.com/phkhoiit-1508) | Frontend Developer | Phụ trách UI Research và Design Direction trong giai đoạn đầu; phát triển Frontend modules được phân công sau khi team chốt thiết kế.   |

Các trách nhiệm trên mô tả ownership hiện tại hoặc dự kiến, không phải bằng chứng task đã Done. Không suy diễn tiến độ từ GitHub contributions và không nhầm các username trên với repository owner `chp0703`.

## Task ownership

Mỗi task phải ghi rõ owner, mục tiêu, phạm vi file hoặc khu vực dự kiến, dependencies, acceptance criteria và reviewer. Một developer chịu trách nhiệm final integration cho mỗi shared file. Nếu scope thay đổi, phải cập nhật worklog và phối hợp trước khi chỉnh sửa các file bị overlap.

Không tự tạo Jira issue ID. Chỉ liên kết issue khi issue đó thực sự tồn tại.

## Branch naming conventions

Sử dụng một branch có scope rõ ràng cho mỗi thay đổi:

- `feat/<short-description>` cho product capability
- `fix/<short-description>` cho bug fix
- `docs/<short-description>` cho thay đổi chỉ liên quan documentation
- `chore/<short-description>` cho tooling và maintenance

Phần sau prefix dùng lowercase kebab-case. Việc tạo, switch, publish và xóa branch là thao tác thủ công của developer. Codex không được thực hiện các thao tác này trừ khi `kentlatoi` thay đổi restriction hiện hành một cách rõ ràng.

## Coding Conventions

- Sử dụng Node.js 24 LTS và cài dependencies bằng `npm ci`.
- Tuân thủ `.editorconfig`, Prettier, ESLint và strict TypeScript compiler checks.
- Ưu tiên React component nhỏ, có tên rõ ràng và domain types cụ thể.
- Giữ state ở phạm vi local cho đến khi có nhu cầu chia sẻ thực tế để chứng minh giải pháp rộng hơn là cần thiết.
- Tránh premature abstraction và dependencies chưa được phê duyệt.
- Bảo đảm semantic HTML, keyboard access, focus visibility, readable contrast và responsive behavior.
- Không để lộ secrets hoặc sensitive user data trong browser, logs, fixtures, screenshots hay documentation.
- Xem dữ liệu từ API và dữ liệu do user cung cấp là untrusted input.

## Quy trình Pull Request và Code Review

1. Task owner cập nhật worklog và chạy `npm run check`.
2. Task owner review các file changed và untracked để phát hiện scope sai, generated output, secrets hoặc thay đổi Backend ngoài ý muốn.
3. Task owner chủ động stage và commit đúng file, push branch rồi tạo Pull Request thủ công.
4. Pull Request mô tả mục tiêu, implementation, verification evidence, risks, open decisions và screenshots nếu có UI change.
5. Reviewer kiểm tra correctness, types, maintainability, accessibility, responsive behavior, security/privacy, tests và documentation.
6. Task owner xử lý feedback và chạy lại các checks liên quan.
7. `kentlatoi` phê duyệt hoặc điều phối final approval và thực hiện merge theo repository policy.

Không được tuyên bố approval, passing check, commit hash hoặc Pull Request link nếu không có evidence.

## Conflict prevention

- Thông báo ownership trước khi chỉnh sửa shared configuration, app shell, global styles, API types hoặc documentation index.
- Chia công việc theo feature boundary và hạn chế cleanup không liên quan.
- Chỉ định một integrator cho lockfile và shared configuration changes.
- Review upstream changes thủ công trước khi kết hợp công việc; không giải quyết conflict bằng cách loại bỏ thay đổi của developer khác.
- Nếu phát hiện local changes ngoài dự kiến bị overlap với task, dừng lại và hỏi owner thay vì overwrite.

## Testing và Verification

Trong quá trình development, chạy check nhỏ nhất phù hợp với thay đổi. Trước khi review, chạy từ `frontend/`:

```sh
npm run format:check
npm run lint
npm run build
```

`npm run check` là command tổng hợp tương đương. Ghi chính xác commands và kết quả thực tế vào worklog. Sau khi test framework được phê duyệt, thêm behavior test tập trung cho logic mới và regression test cho bug fix.

Đối với UI work, cần kiểm tra viewport sizes liên quan, keyboard navigation, focus states, semantic labels, contrast, reduced motion, text wrapping và loading/empty/error/success states. Mọi browser, device, API hoặc assistive technology chưa kiểm tra phải được ghi rõ là limitation.

## Chính sách Developer Worklog

Mỗi developer chỉ cập nhật worklog mang đúng GitHub username của mình:

- `kentlatoi` → `docs/worklogs/kentlatoi.md`
- `thanhhuong107` → `docs/worklogs/thanhhuong107.md`
- `phkhoiit-1508` → `docs/worklogs/phkhoiit-1508.md`

Mỗi task có một entry ngắn, ưu tiên 3–6 dòng nội dung và đặt entry mới nhất lên trước. Chỉ ghi thay đổi quan trọng, bug cùng root cause/fix khi có, test đã thực sự chạy và next step còn lại. Không tạo report dài, heading lặp lại, work history, Jira issue, commit, Pull Request hoặc test result không có evidence. Nếu chưa rõ owner, hỏi `kentlatoi` trước khi cập nhật.

## Definition of Done

Task sẵn sàng để `kentlatoi` review khi acceptance criteria đã đạt, implementation đúng scope và dễ maintain, các yêu cầu security/privacy và accessibility liên quan đã được xử lý, checks bắt buộc pass, documentation cùng worklog của owner đã cập nhật và mọi limitation được nêu rõ.

Task chưa được integration chỉ vì code đã viết xong. Staging, commit, push, Pull Request, approval và merge là các thao tác thủ công riêng biệt do `kentlatoi` và team kiểm soát.

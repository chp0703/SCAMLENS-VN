# Trạng thái Dự án Frontend

Ngày cập nhật gần nhất: 2026-10-16
Branch đã kiểm tra: `feat/fe-project-setup`

## Milestone hiện tại

Checkpoint 8.4 — Frontend Foundation sẵn sàng để `kentlatoi` thực hiện Git review thủ công.

Ứng dụng hiện vẫn là Vite starter scaffold. Milestone này xây dựng development workflow và review workflow nhất quán; chưa triển khai các tính năng sản phẩm của ScamLens VN.

## Tech stack đã xác nhận

| Hạng mục                   | Technology                                                              |
| -------------------------- | ----------------------------------------------------------------------- |
| UI runtime                 | React 19 (resolved 19.3.1) và React DOM 19 (resolved 19.3.1)            |
| Ngôn ngữ                   | TypeScript 6 (resolved 6.0.3)                                           |
| Build và development       | Vite 8 (resolved 8.3.4) cùng React plugin                               |
| Runtime và package manager | Node.js 24 LTS và npm                                                   |
| Static analysis            | ESLint 10.12 Flat Config, typescript-eslint, React Hooks, React Refresh |
| Formatting                 | Prettier 3.9.10 và eslint-config-prettier 10.1.8                        |
| Commit-time validation     | Husky 9.1.7 và lint-staged 17.6.0                                       |

Các resolved version chính xác được ghi trong `package-lock.json`.

## Frontend team

| GitHub username                                     | Role               | Phạm vi giai đoạn hiện tại                                                             |
| --------------------------------------------------- | ------------------ | -------------------------------------------------------------------------------------- |
| [`kentlatoi`](https://github.com/kentlatoi)         | Frontend Lead      | Frontend Foundation, architecture, workflow, code quality, integration và code review. |
| [`thanhhuong107`](https://github.com/thanhhuong107) | Frontend Developer | Sitemap và User Flow; Frontend modules sau khi team chốt thiết kế.                     |
| [`phkhoiit-1508`](https://github.com/phkhoiit-1508) | Frontend Developer | UI Research và Design Direction; Frontend modules sau khi team chốt thiết kế.          |

Đây là responsibility hiện tại hoặc dự kiến, không xác nhận các task đã Done. Repository owner `chp0703` không phải GitHub username của thành viên Frontend team.

## Tiến độ đã được xác minh

- React, TypeScript và Vite scaffold đã tồn tại trong `frontend/`.
- `.nvmrc` yêu cầu Node.js major version 24.
- `package-lock.json` hỗ trợ cài đặt npm dependencies có thể tái lập.
- ESLint Flat Config gồm recommended rules cho JavaScript, TypeScript, React Hooks, React Refresh và khả năng tương thích với Prettier.
- Prettier conventions và các generated-file exclusions đã được cấu hình.
- Husky đã được khởi tạo cho Git repository có Frontend nằm trong subdirectory.
- `core.hooksPath` được kiểm tra là `frontend/.husky/_` vào ngày 2026-10-16.
- lint-staged và pre-commit hook chỉ áp dụng trong phạm vi Frontend đã được bổ sung.
- `.gitignore` đã bao phủ dependencies, build/test output, caches, environment files, TypeScript artifacts, Husky internals và OS/editor files.
- Tài liệu onboarding, team workflow, Codex constraints, project state và worklog đã được tạo.
- Sitemap và user-flow proposal cho Home, Scam Analyzer và Scam Academy được ghi trong `docs/SITEMAP_USER_FLOWS.md`; Chatbot đã được bỏ theo review feedback. Proposal vẫn cần team chốt trước khi chuyển sang Figma.

Xem `docs/worklogs/kentlatoi.md` để biết commands và kết quả thực tế của Frontend Foundation.

## Configuration đã hoàn thành

- Editor conventions: UTF-8, LF và indent 2 spaces
- Prettier conventions: single quotes, semicolons, trailing commas và print width 100 ký tự
- ESLint checks và safe fix command
- Command `npm run check` để chạy verification tổng hợp
- Pre-commit selection chỉ dành cho Frontend và skip Backend-only commit
- Pipeline ESLint/Prettier trong lint-staged, không format `package-lock.json`
- Ignore rules cho secrets, generated output, tool caches và Husky internals
- Ranh giới Frontend/Git cố định cho các Codex session
- Quy tắc tài liệu trong `frontend/docs/`: giải thích bằng tiếng Việt, giữ technical terms bằng English
- Workflow cho ba Frontend developers và worklog template riêng cho từng thành viên

## Product features chưa triển khai

- ScamLens Home experience
- Analyzer input, result và error flows
- Academy content và navigation
- Backend API integration
- Product routing và navigation architecture
- Product design system và reusable application components
- Automated behavior tests và accessibility test suites

Không được mô tả bất kỳ feature nào ở trên là đã triển khai.

## Open decisions

- User journeys, information architecture và visual designs đã được phê duyệt
- Backend API contract, authentication model, error model và environments
- Routing requirements và library choice nếu thực sự cần library
- Client/server state strategy dựa trên data flows thực tế
- Unit/component/end-to-end test frameworks và coverage expectations
- Browser support matrix và accessibility conformance target
- Analytics, telemetry, consent, retention và privacy requirements
- Deployment platform, CI checks và environment promotion process

Không tự giải quyết các quyết định này bằng cách thêm library khi chưa có requirement rõ ràng.

## Các task tiếp theo

1. `kentlatoi` review toàn bộ Frontend diff và thực hiện pre-commit smoke test thật.
2. Team thống nhất product designs, API contracts, accessibility target và testing strategy.
3. Chỉ tạo application structure tối thiểu khi product slice đầu tiên yêu cầu.
4. Triển khai một feature slice hoàn chỉnh theo chiều dọc, gồm loading, empty, success và error states.
5. Thêm automated testing đã được phê duyệt cùng với product logic.
6. Cập nhật file project state này và worklog của task owner sau mỗi thay đổi có ý nghĩa.

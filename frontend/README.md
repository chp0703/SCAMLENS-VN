# ScamLens VN Frontend

ScamLens VN is an AI-powered scam risk analysis and response assistant for Vietnamese users. This directory contains the browser application and its Frontend-only development tooling.

The current milestone is the Frontend Foundation. React, TypeScript, Vite, linting, formatting, and local pre-commit validation are configured. The ScamLens product screens and features—including Home, Analyzer, Academy, and Chatbot—have **not** been implemented yet; the application still displays the starter scaffold.

## Technology stack

- React 19
- TypeScript 6
- Vite 8
- Node.js 24 LTS
- npm
- ESLint 10 with React Hooks and React Refresh rules
- Prettier 3 with `eslint-config-prettier`
- Husky 9 and lint-staged 17

## Frontend team

- [`kentlatoi`](https://github.com/kentlatoi) — Frontend Lead
- [`thanhhuong107`](https://github.com/thanhhuong107) — Frontend Developer
- [`phkhoiit-1508`](https://github.com/phkhoiit-1508) — Frontend Developer

These GitHub usernames identify the Frontend owners and contributors. The repository owner `chp0703` is not a Frontend team username.

## Prerequisites

- Git
- Node.js 24 LTS (the required major version is recorded in `.nvmrc`)
- npm, bundled with Node.js

If you use `nvm`, prepare the runtime from this directory:

```sh
cd frontend
nvm install
nvm use
node --version
```

The Node.js output should start with `v24.`.

## Install and run locally

From the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Vite prints the local URL in the terminal. Stop the development server with `Ctrl+C`.

Use `npm ci` for a reproducible installation from `package-lock.json`. The `prepare` lifecycle script configures Husky at the repository-level Git directory while keeping the hook source inside `frontend/.husky/`.

## Development commands

Run these commands inside `frontend/`:

| Command                | Purpose                                                      |
| ---------------------- | ------------------------------------------------------------ |
| `npm run dev`          | Start the Vite development server with HMR.                  |
| `npm run build`        | Type-check project references and create a production build. |
| `npm run preview`      | Preview an existing production build locally.                |
| `npm run lint`         | Check the Frontend with ESLint.                              |
| `npm run lint:fix`     | Apply safe ESLint fixes to Frontend files.                   |
| `npm run format`       | Format supported Frontend files with Prettier.               |
| `npm run format:check` | Verify formatting without rewriting files.                   |
| `npm run check`        | Run format check, lint, and production build in sequence.    |

Before asking for review, run:

```sh
npm run check
```

## Code quality workflow

ESLint checks TypeScript and TSX using the recommended JavaScript, TypeScript, React Hooks, and Vite React Refresh rules. Prettier owns formatting; `eslint-config-prettier` disables conflicting ESLint formatting rules.

The repository uses a Frontend-scoped Husky pre-commit hook:

1. The hook checks staged paths from the actual repository root.
2. Backend-only commits skip Frontend validation.
3. When a Frontend file is staged, lint-staged runs from `frontend/` using the locally installed binary.
4. Staged TypeScript/TSX files receive ESLint auto-fixes followed by Prettier.
5. Supported JavaScript, CSS, HTML, JSON, Markdown, and YAML files receive Prettier formatting. `package-lock.json` and generated directories are excluded.

If `node_modules` is absent, the hook stops with an instruction to run `npm ci`.

## Feature branch and review workflow

All Git publishing actions are performed manually by a developer. Start work from the team-approved base, create a focused branch, and avoid mixing unrelated changes. Recommended branch names are:

- `feat/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`

Keep the appropriate username-based file under `docs/worklogs/` current while working. Before handing work to `kentlatoi` or opening a Pull Request:

1. Review all changed and untracked files.
2. Run `npm run check` and record the actual result in the worklog.
3. Confirm no secrets, generated output, or Backend changes are included.
4. Stage and commit only the intended files manually.
5. Push the branch and create the Pull Request manually in GitHub.
6. Include scope, verification evidence, risks, screenshots when UI changes exist, and linked work items only when they actually exist.
7. Obtain the required review before merging.

See [`AGENTS.md`](./AGENTS.md), [`docs/TEAM_WORKFLOW.md`](./docs/TEAM_WORKFLOW.md), and [`docs/FE_PROJECT_STATE.md`](./docs/FE_PROJECT_STATE.md) for the full engineering agreement.

## Environment variables and secrets

- Never commit `.env` or `.env.*` files. Only `.env.example` may be committed as documentation.
- Vite exposes every variable prefixed with `VITE_` to the browser bundle. Never place API keys, tokens, private credentials, or sensitive personal data in a `VITE_` variable.
- Store secrets on trusted server-side infrastructure. The browser should call an approved Backend endpoint.
- Document every required public variable in `.env.example` without real values before using it.

## Troubleshooting

### Wrong Node.js version

Run `nvm use` inside `frontend/`. If Node.js 24 is unavailable, run `nvm install` first.

### Dependency or command not found errors

Run:

```sh
rm -rf node_modules
npm ci
```

Do not delete or regenerate `package-lock.json` unless a deliberate dependency change requires it.

### Husky hook does not run

From `frontend/`, run `npm run prepare`, then verify from the repository root:

```sh
git config --get core.hooksPath
```

The expected value is `frontend/.husky/_`. The tracked hook file is `frontend/.husky/pre-commit`; files under `.husky/_/` are generated by Husky and must remain ignored.

### Formatting fails

Run `npm run format`, inspect the resulting Frontend-only changes, and rerun `npm run format:check`.

### Build fails after changing types

Read the first TypeScript diagnostic, fix its root cause, then rerun `npm run build`. Do not bypass errors with `any` or broad type assertions.

## Current status

Checkpoint 8.4 prepares the Frontend foundation for manual Git review. Tooling and team documentation are present, but product architecture decisions, API contracts, test framework selection, routing, state management, and all user-facing ScamLens features remain pending.

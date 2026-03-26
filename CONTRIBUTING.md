# Contributing

ZhiYiQuant is currently maintained as an independent personal project.

This repository is public, but it is **not** being run as a community-driven collaboration program. The primary development workflow is maintained directly by the project owner.

## Current policy

- Issues are welcome for bug reports and focused suggestions
- Small, clear pull requests may be reviewed when they are directly relevant
- Large unsolicited feature branches are not part of the default workflow
- Architectural direction, release timing, and scope remain under maintainer control

## Before opening a pull request

Please open an issue first if your change is:

- cross-module
- user-facing
- architectural
- likely to change behavior or data layout

This helps avoid duplicated effort and keeps the public history clean.

## What is most helpful

- reproducible bug reports
- minimal fixes
- documentation corrections
- setup or packaging improvements

## Development notes

### Frontend

```bash
cd quantdinger_vue
npm install
npm run serve
```

### Backend

```bash
cd backend_api_python
pip install -r requirements.txt
python run.py
```

### Desktop

```bash
cd src-tauri
cargo tauri dev
```

## License

By submitting code or documentation, you agree that accepted changes are licensed under the repository license.

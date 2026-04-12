import os
import platform
import shutil
import subprocess
import sys


def _target_triple() -> str:
    sysname = platform.system().lower()
    machine = platform.machine().lower()

    is_arm = machine in {"aarch64", "arm64"}
    is_x64 = machine in {"x86_64", "amd64"}

    if sysname.startswith("win"):
        return "aarch64-pc-windows-msvc" if is_arm else "x86_64-pc-windows-msvc"
    if sysname == "darwin":
        return "aarch64-apple-darwin" if is_arm else "x86_64-apple-darwin"
    if sysname == "linux":
        return "aarch64-unknown-linux-gnu" if is_arm else "x86_64-unknown-linux-gnu"
    return "x86_64-unknown-linux-gnu"


def _venv_python(venv_dir: str) -> str:
    if platform.system().lower().startswith("win"):
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def _ensure_venv(backend_root: str, index_url: str) -> str:
    venv_dir = os.path.join(backend_root, ".venv_sidecar")
    py = _venv_python(venv_dir)
    marker = os.path.join(venv_dir, ".zhiyiquant_sidecar_ready")

    if not os.path.exists(py):
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir], cwd=backend_root)

    if not os.path.exists(marker):
        subprocess.check_call([py, "-m", "pip", "install", "--upgrade", "pip"], cwd=backend_root)
        subprocess.check_call(
            [py, "-m", "pip", "install", "-i", index_url, "-r", "requirements.txt"],
            cwd=backend_root,
        )
        with open(marker, "w", encoding="utf-8") as f:
            f.write("ok")

    return py


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    backend_root = os.path.join(repo_root, "backend_api_python")
    entry = os.path.join(backend_root, "sidecar_main.py")
    migrations_dir = os.path.join(backend_root, "migrations")

    if not os.path.exists(entry):
        raise SystemExit(f"sidecar entry not found: {entry}")

    target = _target_triple()
    is_windows = platform.system().lower().startswith("win")
    base_name = f"zhiyiquant-backend-{target}"
    out_name = f"{base_name}.exe" if is_windows else base_name

    dist_dir = os.path.join(backend_root, "dist_sidecar")
    build_dir = os.path.join(backend_root, "build_sidecar")

    for p in [dist_dir, build_dir]:
        os.makedirs(p, exist_ok=True)

    index_url = os.getenv("ZHIYIQUANT_PIP_INDEX_URL") or "https://pypi.org/simple"
    use_venv = not ((os.getenv("ZHIYIQUANT_SIDECAR_NO_VENV") or "").strip() in {"1", "true", "yes"})
    py = _ensure_venv(backend_root, index_url) if use_venv else sys.executable

    cmd = [
        py,
        "-m",
        "PyInstaller",
        "--log-level",
        "WARN",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--exclude-module",
        "PyQt5",
        "--exclude-module",
        "PyQt6",
        "--exclude-module",
        "PySide2",
        "--exclude-module",
        "PySide6",
        "--exclude-module",
        "tensorflow",
        "--exclude-module",
        "torch",
        "--exclude-module",
        "sklearn",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "IPython",
        "--exclude-module",
        "notebook",
        "--exclude-module",
        "jupyterlab",
        "--name",
        base_name,
        "--distpath",
        dist_dir,
        "--workpath",
        build_dir,
        "--add-data",
        f"{migrations_dir}{os.pathsep}migrations",
        entry,
    ]

    subprocess.check_call(cmd, cwd=backend_root)

    built_path = os.path.join(dist_dir, out_name)
    if not os.path.exists(built_path):
        candidates = [p for p in os.listdir(dist_dir) if p.startswith(base_name)]
        raise SystemExit(f"PyInstaller output not found. dist={dist_dir}, candidates={candidates}")

    dest_dir = os.path.join(repo_root, "src-tauri", "binaries")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, out_name)
    shutil.copy2(built_path, dest_path)

    print(dest_path)


if __name__ == "__main__":
    main()

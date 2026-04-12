import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.safe_exec import safe_exec_code


def main():
    res = safe_exec_code(
        code="while True:\n    pass\n",
        exec_globals={},
        exec_locals={},
        timeout=1,
    )
    assert res["success"] is False
    assert "超时" in (res.get("error") or "")
    print("OK")


if __name__ == "__main__":
    main()

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--host", default=os.getenv("PYTHON_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PYTHON_API_PORT", "5000")))
    args, _ = parser.parse_known_args()

    os.environ["PYTHON_API_HOST"] = args.host
    os.environ["PYTHON_API_PORT"] = str(args.port)
    os.environ.setdefault("PYTHON_API_DEBUG", "false")

    app = create_app()
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()


"""uvicorn 入口：`uvicorn calib_cloud.main:app --host 0.0.0.0 --port 8080`"""

from .app import create_app

app = create_app()

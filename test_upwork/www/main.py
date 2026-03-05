from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# 设置模板目录
templates = Jinja2Templates(directory="template")

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    # 使用Jinja2模板渲染页面
    return templates.TemplateResponse("components/layouts/index.html")
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# 设置模板目录
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    # 使用Jinja2模板渲染页面
    return templates.TemplateResponse("index.html", {"request": request, "name": "FastAPI User"})



# 到目录下运行
# (venv) (base) weiliang@lwdeMacBook-Pro my_fastapi_app % uvicorn main:app --reload

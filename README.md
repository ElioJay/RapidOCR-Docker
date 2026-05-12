# RapidOCR-Docker

这是一个面向离线部署的 CPU 版 RapidOCR Docker 应用。它在同一个镜像里提供 HTTP 服务和 CLI 调用，支持图片与 PDF，输出总文本和结构化 JSON 明细。

## 功能

- HTTP：`POST /ocr` 上传图片或 PDF。
- CLI：`docker run ... rapidocr-docker ocr /input/file.pdf`。
- 支持图片：`png`、`jpg`、`jpeg`、`bmp`、`tif`、`tiff`。
- 支持 PDF：按页渲染为图片后 OCR。
- 输出：`text` 总文本、`pages` 页明细、`lines` 行文本、置信度、坐标框。
- 端口可配置：通过 `APP_PORT`、脚本 `-Port` 或 `docker-compose.yml` 变量控制。

## 目录结构

```text
RapidOCR-Docker/
  src/rapidocr_offline/     # 应用代码
  tests/                    # 单元测试
  scripts/                  # 构建、导出、导入、运行脚本
  samples/                  # 本地测试样例目录
  docs/superpowers/         # 设计与实施计划
  Dockerfile
  docker-compose.yml
  requirements.txt
  requirements-dev.txt
```

## 开发过程

在有网开发机执行：

```powershell
cd D:\Code\python\RapidOCR-Docker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

本项目采用测试优先方式实现，核心 OCR 服务通过 fake engine 测试，不依赖真实模型即可验证 JSON 结构、PDF 分页合并和错误处理。

## HTTP 使用

构建并启动服务：

```powershell
.\scripts\build-image.ps1 -ImageName rapidocr-docker -Tag 1.0.0
.\scripts\run-server.ps1 -ImageName rapidocr-docker -Tag 1.0.0 -Port 9000
```

健康检查：

```powershell
curl http://localhost:9000/health
```

OCR 请求：

```powershell
curl -X POST "http://localhost:9000/ocr" -F "file=@D:\data\input.pdf" -F "render_dpi=200"
```

如果要把宿主机端口和容器端口分开：

```powershell
.\scripts\run-server.ps1 -Port 8000 -HostPort 9000
```

此时访问 `http://localhost:9000`，容器内部仍监听 `8000`。

## CLI 使用

输出到终端：

```powershell
.\scripts\run-cli.ps1 -InputFile D:\data\input.pdf -Pretty
```

输出到文件：

```powershell
.\scripts\run-cli.ps1 -InputFile D:\data\input.pdf -OutputFile D:\data\result.json -Pretty
```

启用单字坐标：

```powershell
.\scripts\run-cli.ps1 -InputFile D:\data\input.png -ReturnWordBox -Pretty
```

## JSON 返回格式

```json
{
  "filename": "input.pdf",
  "file_type": "pdf",
  "page_count": 2,
  "text": "第一页文本\n\n第二页文本",
  "pages": [
    {
      "page": 1,
      "text": "第一页文本",
      "lines": [
        {
          "text": "识别文本",
          "score": 0.998,
          "box": [[10, 20], [100, 20], [100, 40], [10, 40]]
        }
      ],
      "elapsed": 0.23
    }
  ],
  "elapsed": 1.2
}
```

错误返回：

```json
{
  "error": {
    "code": "unsupported_file_type",
    "message": "Only image and PDF files are supported."
  }
}
```

## 打包过程

在有网构建机执行：

```powershell
cd D:\Code\python\RapidOCR-Docker
.\scripts\build-image.ps1 -ImageName rapidocr-docker -Tag 1.0.0
.\scripts\save-image.ps1 -ImageName rapidocr-docker -Tag 1.0.0 -Output .\dist\rapidocr-docker-1.0.0.tar
```

把以下内容复制到无网目标机：

- `dist\rapidocr-docker-1.0.0.tar`
- `scripts\load-image.ps1`
- `scripts\run-server.ps1`
- `scripts\run-cli.ps1`
- 需要 OCR 的业务文件

在无网目标机执行：

```powershell
.\scripts\load-image.ps1 -ImageTar .\dist\rapidocr-docker-1.0.0.tar
.\scripts\run-server.ps1 -ImageName rapidocr-docker -Tag 1.0.0 -Port 9000
```

离线 CLI 调用：

```powershell
.\scripts\run-cli.ps1 -ImageName rapidocr-docker -Tag 1.0.0 -InputFile D:\data\input.pdf -OutputFile D:\data\result.json -Pretty
```

## Docker Compose

默认端口：

```powershell
docker compose up --build
```

自定义端口：

```powershell
$env:APP_PORT="9000"
$env:HOST_PORT="9000"
docker compose up --build
```

## 注意事项

- 目标机器只需要 Docker，不需要 Python、pip 或网络。
- PDF 渲染默认 `200 DPI`，可通过 `render_dpi` 或 `-RenderDpi` 修改，允许范围是 `72` 到 `400`。
- 镜像构建阶段会初始化 RapidOCR，确保默认模型文件进入镜像。
- 当前版本是 CPU 版，不依赖 NVIDIA 驱动或 CUDA。

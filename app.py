from flask import Flask, request, jsonify, Response, send_from_directory, send_file
import json, os
import textwrap
from PIL import Image, ImageDraw, ImageFont
import logging

app = Flask(__name__)

# 返回主页图标（固定在页面左上角）
HOME_BUTTON = '''
<div style="position: fixed; top: 10px; left: 10px; z-index: 1000;">
    <a href="/" style="text-decoration: none; font-size: 24px;">🏠</a>
</div>
'''

# ✅ 访问计数文件路径
VISIT_COUNT_FILE = "/app/visit_count.txt"

# ✅ 读取历史访问次数
def load_visit_count():
    if os.path.exists(VISIT_COUNT_FILE):
        try:
            with open(VISIT_COUNT_FILE, "r") as f:
                return int(f.read().strip())
        except ValueError:
            return 0
    return 0

# ✅ 访问计数，启动时加载
visit_count = load_visit_count()

# ✅ 设置日志记录
log_file = "/app/access.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

@app.before_request
def track_visits():
    """ 统计访问量并记录日志 """
    global visit_count
    visit_count += 1

    # ✅ 每次访问后，更新 `visit_count.txt`
    with open(VISIT_COUNT_FILE, "w") as f:
        f.write(str(visit_count))

    visitor_ip = request.remote_addr  # 访问者 IP
    user_agent = request.headers.get("User-Agent", "Unknown")  # 浏览器信息
    logging.info(f"访问 {request.path} 来自 {visitor_ip} - {user_agent}")

@app.route("/stats_count")
def get_stats():
    """ 返回当前访问量统计 """
    return Response(f"<h1>📊 访问量统计</h1><p>总访问次数: {visit_count}</p>", mimetype="text/html")

def get_latest_update_time(jsonl_file="/data/新闻汇总.jsonl"):
    """ 读取 JSONL 文件的最后一行，获取最新的 publish_time """
    try:
        with open(jsonl_file, "r", encoding="utf-8") as file:
            last_line = None
            for line in file:  # 遍历直到最后一行
                last_line = line
            if last_line:
                last_news = json.loads(last_line.strip())  # 解析 JSON
                return last_news.get("publish_time", "未知时间")
    except FileNotFoundError:
        return "暂无更新"
    except json.JSONDecodeError:
        return "数据错误"

    return "暂无更新"

IMAGE_DIR = "/app/news_images"  # 存放所有动态生成的新闻图片

# 确保图片目录存在
os.makedirs(IMAGE_DIR, exist_ok=True)

def read_jsonl(jsonl_file='/data/新闻汇总.jsonl'):
    """ 逐行读取 JSONL，减少内存占用 """
    try:
        with open(jsonl_file, "r", encoding="utf-8") as file:
            return [json.loads(line) for line in file]
    except FileNotFoundError:
        return []

def get_font_path():
    """ 自动查找可用的中文字体 """
    possible_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ 找到字体: {path}", flush=True)
            return path

    print("⚠️ 没有找到可用的中文字体", flush=True)
    return None  # 没找到字体

def generate_news_image(text, date):
    """ 生成带有新闻标题的缩略图，支持中文 """
    image_path = f"/app/news_images/news_{date}.jpeg"

    if os.path.exists(image_path):
        return image_path  # 如果已生成，则直接返回

    # ✅ 设置图片大小
    img_width, img_height = 600, 315
    img = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # ✅ 获取可用的中文字体
    font_path = get_font_path()
    font_size = 28  # 调大字体，提升可读性
    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size, encoding="unic")
        except OSError:
            print("⚠️ 字体加载失败，使用默认字体")
            font = ImageFont.load_default()
    else:
        print("⚠️ 未找到可用字体，使用默认字体")
        font = ImageFont.load_default()

    # ✅ 处理文本换行
    text = text.replace("<b>", "【").replace("</b>", "】")  # 替换 HTML 粗体
    max_chars = 18  # 每行最多 18 个字符
    wrapped_text = "\n".join(textwrap.wrap(text, width=max_chars))  # 自动换行

    margin_x, margin_y = 20, 20  # 左上角的偏移量
    line_spacing = 10  # 行间距

    draw.multiline_text((margin_x, margin_y), wrapped_text, font=font, fill=(0, 0, 0), spacing=line_spacing)

    # ✅ 保存图片
    img.save(image_path)
    print(f"✅ 生成图片: {image_path}")
    return image_path


@app.route("/")
def index(DATA_DIR="/data"):
    """
    读取 /data 目录下所有 JSONL 文件，按日期倒序排列，
    ‘新闻汇总.jsonl’ 放最前，文件内按 publish_time 倒序
    """
    latest_update = get_latest_update_time() 
    html_response = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>新闻汇总</title>
        <style>
            /* ======= 全局样式 ======= */
            body {{
                font-family: "PingFang SC", "Noto Sans SC", sans-serif;
                background-color: #f8f9fa;
                color: #333;
                line-height: 1.8;
                padding: 20px;
                margin: 0;  /* 去掉默认边距 */
            }}
            h1, h2, h3 {{
                color: #333;
                font-weight: bold;
            }}
            h1 {{
                text-align: center;
            }}

            /* ======= 卡片容器 ======= */
            .news-section {{
                background-color: #fff;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 20px;
                transition: transform 0.3s;
            }}
            .news-section:hover {{
                transform: translateY(-5px);
            }}

            /* ======= 列表项样式 ======= */
            .news-item {{
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #ececec;
                list-style: none;
            }}
            .news-item:last-child {{
                border-bottom: none;
            }}

            /* ======= 标题链接 ======= */
            .news-title {{
                font-size: 18px;
                font-weight: bold;
                color: #4b5af5;
                text-decoration: none;
            }}
            .news-title:hover {{
                text-decoration: underline;
            }}

            /* ======= 元信息（来源/时间） ======= */
            .news-meta {{
                color: #666;
                font-size: 14px;
            }}

            /* ======= 折叠/展开按钮 ======= */
            .toggle-button {{
                background-color: #4b5af5;
                color: #fff;
                border: none;
                padding: 6px 10px;
                border-radius: 5px;
                cursor: pointer;
                transition: background-color 0.2s;
                font-size: 14px;
                margin-left: 10px;
            }}
            .toggle-button:hover {{
                background-color: #3a47c7;
            }}

            /* ======= 新闻内容容器，默认显示 ======= */
            .news-content {{
                display: block;
                margin-top: 10px;
            }}

            /* ======= 全局链接样式 ======= */
            a {{
                color: #4b5af5;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            #toggle-all-btn {{
                position: fixed;  /* 固定按钮，不随页面滚动 */
                top: 20px;  /* 离顶部 20px */
                right: 20px;  /* 离右侧 20px */
                background-color: #4b5af5;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.2);
                transition: background-color 0.2s, transform 0.2s;
                z-index: 1000;  /* 确保按钮在最上层 */
            }}

            #toggle-all-btn:hover {{
                background-color: #3a47c7;
                transform: scale(1.05);  /* 鼠标悬停时轻微放大 */
            }}
            .news-header {{
                display: flex;
                align-items: center;
                width: 100%;
                justify-content: space-between; /* 让标题区域和按钮分别靠左、靠右 */
            }}

            .title-area {{
                display: flex;
                align-items: center;
                gap: 10px; /* 控制 "[More]" 和 "最近更新时间" 之间的间距 */
            }}

            .update-time {{
                font-size: 12px;
                color: #888;
                white-space: nowrap; /* 防止换行 */
                margin-top: 10px;
            }}

            .toggle-button {{
                margin-left: auto; /* 确保 "展开/收起" 按钮靠最右 */
            }}
  
        </style>
        <script>
            function toggleNews(id) {{
                var content = document.getElementById(id);
                var button = document.getElementById(id + '-btn');
                if (content.style.display === "none") {{
                    content.style.display = "block";
                    button.innerText = "🔽 收起";
                }} else {{
                    content.style.display = "none";
                    button.innerText = "▶ 展开";
                }}
            }}

            function toggleAll() {{
                var allContents = document.querySelectorAll(".news-content");
                var allButtons = document.querySelectorAll(".toggle-button");
                var isAnyVisible = Array.from(allContents).some(content => content.style.display !== "none");

                allContents.forEach(content => {{
                    content.style.display = isAnyVisible ? "none" : "block";
                }});

                allButtons.forEach(button => {{
                    // 排除“一键收起/展开”自身
                    if (button.id !== "toggle-all-btn") {{
                        button.innerText = isAnyVisible ? "▶ 展开" : "🔽 收起";
                    }}
                }});

                document.getElementById("toggle-all-btn").innerText = isAnyVisible ? "📌 一键展开" : "📌 一键收起";
            }}
        </script>
    </head>
    <body>
        {HOME_BUTTON}
        <h1>📰 新闻汇总</h1>
        <button id="toggle-all-btn" onclick="toggleAll()">📌 一键收起</button>
    """

    # 获取所有 JSONL 文件
    jsonl_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".jsonl")]

    # ✅ 把 "新闻汇总.jsonl" 放在最前面
    summary_file = "新闻汇总.jsonl"
    if summary_file in jsonl_files:
        jsonl_files.remove(summary_file)
        jsonl_files.insert(0, summary_file)

    # ✅ 其余文件按日期倒序排列
    def extract_date(filename):
        # 假设文件名是 YYYY-MM-DD.jsonl 或者别的日期格式
        return os.path.splitext(filename)[0]

    if len(jsonl_files) > 1:
        # 仅对除“新闻汇总.jsonl”外的文件进行排序
        jsonl_files[1:] = sorted(jsonl_files[1:], key=extract_date, reverse=True)

    # 逐个文件生成新闻列表
    for index, file_name in enumerate(jsonl_files):
        file_path = os.path.join(DATA_DIR, file_name)
        news_list = read_jsonl(file_path)
        title = os.path.splitext(file_name)[0]

        # ✅ 按 publish_time 倒序
        news_list = sorted(news_list, key=lambda x: x.get("publish_time", ""), reverse=True)

        # ✅ 获取该文件的最新更新时间
        file_update_time = get_latest_update_time(file_path)

        # ✅ 如果超过 6 条，添加 [More] 按钮
        more_link = f' <a href="/view?file={file_name}" style="font-size:14px;">[More]</a>' if len(news_list) > 6 else ""

        section_id = f"news-{index}"
        html_response += f"""
        <div class="news-section">
            <div class="news-header">
                <div class="title-area">
                    <h2>📅 {title}{more_link}</h2>
                    <span class="update-time"> {file_update_time}更新 </span>
                </div>
                <button id="{section_id}-btn" class="toggle-button" onclick="toggleNews('{section_id}')">🔽 收起</button>
            </div>
            <div id="{section_id}" class="news-content">
                <ul>
        """

        # 只显示前 6 条新闻
        for i, news in enumerate(news_list[:6]):
            article_url = f"/article?file={file_name}&index={len(news_list)-i-1}"
            news_title = news.get("title", "无标题")
            news_publisher = news.get("publisher", "未知来源")
            news_time = news.get("publish_time", "未知时间")
            news_content_preview = news.get("content", "无内容")[:200]

            html_response += f"""
            <li class="news-item">
                <h3><a href="{article_url}" class="news-title">{news_title}</a></h3>
                <p class="news-meta"><b>来源：</b>{news_publisher} | <b>发布时间：</b>{news_time}</p>
                <p>{news_content_preview}...</p>
            </li>
            """

        html_response += "</ul></div></div>"

    html_response += "</body></html>"
    return Response(html_response, mimetype="text/html")


@app.route("/article")
def view_article(DATA_DIR="/data"):
    """ 显示单条新闻的完整内容 """
    file_name = request.args.get("file")
    index = request.args.get("index")

    if not file_name or not file_name.endswith(".jsonl") or not index.isdigit():
        return Response("<h1>无效请求</h1>", mimetype="text/html"), 400

    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        return Response("<h1>文件不存在</h1>", mimetype="text/html"), 404

    news_list = read_jsonl(file_path)
    index = int(index)

    if index >= len(news_list):
        return Response("<h1>新闻索引超出范围</h1>", mimetype="text/html"), 404

    news = news_list[index]
    title = news.get("title", "无标题")
    content_text = news.get("content", "无内容").replace("\n", "<br>")

    html_response = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                margin-top: 50px;
            }}
        </style>
    </head>
    <body>
        {HOME_BUTTON}
        <h1>{title}</h1>
        <p><b>来源：</b>{news.get("publisher", "未知来源")} | <b>发布时间：</b>{news.get("publish_time", "未知时间")}</p>
        <p>{content_text}</p>
    </body>
    </html>
    """
    return Response(html_response, mimetype="text/html")


@app.route("/view")
def view_file(DATA_DIR="/data"):
    """ 显示单个 JSONL 文件的所有新闻 """
    file_name = request.args.get("file")
    if not file_name or not file_name.endswith(".jsonl"):
        return Response("<h1>无效文件</h1>", mimetype="text/html"), 400

    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        return Response("<h1>文件不存在</h1>", mimetype="text/html"), 404

    news_list = read_jsonl(file_path)
    title = os.path.splitext(file_name)[0]

    # ✅ 按 publish_time 倒序
    news_list = sorted(news_list, key=lambda x: x.get("publish_time", ""), reverse=True)

    html_response = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - 全部新闻</title>
        <style>
            body {{
                margin-top: 50px;
            }}
        </style>
    </head>
    <body>
        {HOME_BUTTON}
        <h1>📅 {title} - 全部新闻</h1>
        <ul>
    """

    for news in news_list:
        html_response += f"""
        <li>
            <h3>{news.get("title", "无标题")}</h3>
            <p><b>来源：</b>{news.get("publisher", "未知来源")} | <b>发布时间：</b>{news.get("publish_time", "未知时间")}</p>
            <p>{news.get("content", "无内容")}</p>
        </li>
        """

    html_response += "</ul></body></html>"
    return Response(html_response, mimetype="text/html")


@app.route("/<path:data>")
def get_data(data):
    """ 读取新闻内容，返回 HTML 并支持 Open Graph """
    query_date = data.replace("data=", "")

    news_list = read_jsonl()
    matching_news = [item["content"] for item in news_list if item.get("publish_time") == query_date]

    if matching_news:
        # ✅ 生成新闻缩略图
        image_path = generate_news_image(matching_news[0], query_date)
        content_text = matching_news[0].replace("\n", "<br>")

        html_response = f"""
        <!DOCTYPE html>
        <html lang="zh">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>新闻汇总 - {query_date}</title>
            <meta property="og:title" content="新闻汇总 - {query_date}">
            <meta property="og:description" content="{matching_news[0][:100]}...">
            <meta property="og:image" content="https://www.multmatrix.com/static/news_images/news_{query_date}.jpeg">
            <meta property="og:url" content="https://www.multmatrix.com/data={query_date}">
            <meta name="twitter:card" content="summary_large_image">
            <meta name="twitter:title" content="新闻汇总 - {query_date}">
            <meta name="twitter:description" content="{matching_news[0][:100]}...">
            <meta name="twitter:image" content="https://www.multmatrix.com/static/news_images/news_{query_date}.jpeg">
            <style>
                body {{
                    margin-top: 50px;
                }}
            </style>
        </head>
        <body>
            {HOME_BUTTON}
            <h1>新闻汇总 - {query_date}</h1>
            <p>{content_text}</p>
        </body>
        </html>
        """
        return Response(html_response, mimetype="text/html")
    else:
        return Response("<h1>没有这天的新闻汇总</h1>", mimetype="text/html"), 404

# ✅ 允许访问 /app/news_images/ 目录下动态生成的图片
@app.route("/static/news_images/<filename>")
def serve_news_image(filename):
    return send_file(os.path.join(IMAGE_DIR, filename), mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
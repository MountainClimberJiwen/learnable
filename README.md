# Learnable

点击知识点，探索无限关联。一个基于 AI 的交互式知识树生成器。

> Click a knowledge node, watch the tree bloom. AI-powered infinite knowledge graph.

## 特色

- 🌳 **点击展开** — 点击任意知识点，AI 自动生成子知识点
- 🔍 **无限画布** — 滚轮缩放、拖拽移动，知识空间无边无际
- ✨ **漂亮交互** — 手绘风格、动画展开、贝塞尔连线
- 🤖 **AI 驱动** — 基于 Kimi 大模型生成知识结构
- 📁 **纯前端画布** — HTML5 Canvas，无需复杂前端构建

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端服务将运行在 http://localhost:8080

### 2. 打开前端

```bash
# 方式一：直接用浏览器打开
open frontend/index.html

# 方式二：通过后端静态文件服务
# 访问 http://localhost:8080
```

### 3. 配置 Kimi API

在 `/opt/agentrl/.env` 中设置：

```bash
KIMI_API_KEY=your_api_key_here
```

或者在环境变量中设置 `KIMI_API_KEY`。

## 使用方法

1. 在输入框中输入主题，如 "机器学习"
2. 点击 "开始学习"
3. 根节点自动展开，生成子知识点
4. 点击任意节点，继续展开更多
5. 滚轮缩放查看全局，拖拽移动视角

## 技术栈

| 层 | 技术 |
|-----|------|
| 前端 | HTML5 Canvas + Vanilla JS |
| 后端 | FastAPI + Python |
| AI | Kimi (Moonshot AI) |
| 布局 | 扇形径向布局 + 贝塞尔连线 |

## API 接口

### POST /api/expand

扩展一个知识点为子知识点。

**Request:**

```json
{
  "topic": "机器学习",
  "language": "zh"
}
```

**Response:**

```json
{
  "parent": "机器学习",
  "nodes": [
    {"id": "1", "label": "监督学习", "description": "利用标注数据训练模型"},
    {"id": "2", "label": "无监督学习", "description": "发现数据中的隐藏模式"}
  ]
}
```

## 路线图

```
用户点击节点
    ↓
前端 Canvas 检测点击
    ↓
POST /api/expand {topic: "节点名称"}
    ↓
FastAPI 调用 Kimi API
    ↓
Kimi 生成子知识点
    ↓
前端收到响应
    ↓
扇形布局计算位置
    ↓
动画展开新节点 + 连线
```

## 开源协议

MIT License

## Author

Jiwen (MountainClimberJiwen)

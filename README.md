# HoloAssist - 基于大语言模型构建的智能客服系统

一个基于 FastAPI 构建的智能客服助手项目，支持多种大语言模型，如DeepSeek V3、Qwen2.5系列、Llama3系列等。涵盖了 Agent、RAG 在智能客服领域的主流应用落地需求场景。

## 功能特性

### 1. 通用问答能力
- **支持 DeepSeek V3 在线API**
- **支持使用 Ollama 接入任意对话模型**，如Qwen2.5系列、Llama3系列
- **灵活的模式配置**

### 2. 深度思考能力
- **支持 DeepSeek R1 在线API**
- **支持使用 Ollama 接入任意 Deepseek R1 模型系列**
- **灵活的推理配置**

### 3. RAG（检索增强生成）
- 文档上传和索引
- 基于向量检索的问答
- GraphRAG支持

### 4. LangGraph Agent
- 多Agent协作
- 工具调用支持
- Neo4j图数据库集成

### 5. 搜索增强
- 网络搜索集成
- Function Calling支持
- 搜索结果总结

## 快速开始

### 1. 环境要求

- Python >= 3.12
- uv (Python包管理器)
- MySQL数据库
- Redis（可选）
- Neo4j（可选，用于图数据库功能）

### 2. 安装依赖

```bash
# 使用uv安装开发依赖
uv sync --dev

# 或安装所有依赖（包括运行时依赖）
uv sync
```

### 3. 配置环境变量

复制 `.env.example` 文件到 `.env`，并根据实际情况修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下内容：
- DeepSeek API密钥（如使用）
- Ollama服务地址和模型
- 数据库连接信息
- Redis配置（如使用）
- Neo4j配置（如使用）

### 4. 初始化数据库

```bash
# 运行数据库初始化脚本
python llm_backend/scripts/init_db.py
```

### 5. 启动服务

```bash
# 进入后端目录
cd llm_backend

# 启动服务
python run.py
```

服务启动后可以访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 项目结构

```
HoloAssit/
├── src/holoassist/          # 源代码目录
│   ├── app/                 # 应用模块
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心模块（配置、数据库、日志等）
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # 业务服务
│   │   ├── lg_agent/       # LangGraph Agent模块
│   │   ├── graphrag/       # GraphRAG模块
│   │   ├── prompts/        # 提示词
│   │   └── tools/          # 工具模块
│   └── main.py             # 主应用入口
├── llm_backend/            # 后端入口
│   ├── main.py
│   └── run.py
├── tests/                  # 测试目录
│   ├── unit/              # 单元测试
│   └── integration/       # 集成测试
├── scripts/                # 脚本目录
├── docs/                   # 文档目录
├── config/                 # 配置文件目录
├── pyproject.toml         # 项目配置
└── README.md              # 项目说明
```

## 开发指南

### 代码质量检查

```bash
# 运行代码质量检查脚本
bash scripts/check_code_quality.sh
```

### 依赖管理

```bash
# 同步依赖
bash scripts/manage_dependencies.sh

# 或直接使用uv命令
uv sync
uv tree
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 生成覆盖率报告
pytest tests/ --cov=src/holoassist --cov-report=html
```

### Pre-commit Hooks

安装pre-commit hooks以在提交前自动运行代码质量检查：

```bash
uv sync --dev
pre-commit install
```

## 技术栈

- **后端框架**：FastAPI
- **数据库**：MySQL (SQLAlchemy async)
- **图数据库**：Neo4j
- **缓存**：Redis
- **LLM集成**：OpenAI API (DeepSeek), Ollama
- **Agent框架**：LangGraph
- **RAG**：GraphRAG, FAISS
- **包管理**：uv
- **代码质量**：ruff, mypy
- **测试**：pytest

## 贡献指南

1. Fork本项目
2. 创建特性分支 (`git flow feature start your-feature`)
3. 提交更改 (`git commit -m 'feat: Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建Pull Request

### 提交规范

使用Conventional Commits格式：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

## License

MIT

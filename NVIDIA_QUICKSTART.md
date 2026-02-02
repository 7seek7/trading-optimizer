# 🚀 NVIDIA NIM API 快速开始指南

## ✅ 完成配置只需要3步

### 1. 获取NVIDIA NGC API Key

访问：https://org.ngc.nvidia.com/setup/api-keys

1. 点击 "Generate Personal Key"
2. Key Name: `trading-bot-optimizer`
3. Expiration: `Never Expire`
4. Services: 勾选 "NGC Catalog" 和 "Public API Endpoints"
5. 点击 "Generate Personal Key"
6. 复制KEY（格式：`nvapi-xxxxxxxxxxxxxxxxxxxxx`）

### 2. 配置环境变量

在 `.env` 文件中添加：

```bash
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxx
NVIDIA_API_BASE=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=deepseek-ai/deepseek-v3
```

### 3. 开始使用

#### Python代码
```python
from auto_ai_optimizer import AutoOptimizer
import os

optimizer = AutoOptimizer(
    api_key=os.getenv("NVIDIA_API_KEY"),
    api_base=os.getenv("NVIDIA_API_BASE"),
    model=os.getenv("NVIDIA_MODEL")
)

# 运行优化
optimizer.run()
```

#### Streamlit界面
1. 启动应用：`streamlit run streamlit_app.py`
2. 在侧边栏选择：**"NVIDIA API (推荐)"**
3. 输入API Key：`nvapi-xxxxxxxxxxxxxxxxxxxxx`
4. 选择模型：`deepseek-ai/deepseek-v3 (推荐)`
5. 开始优化！

---

## 📊 NVIDIA NIM vs 其他API对比

| 特性 | NVIDIA NIM (推荐) | DeepSeek | OpenAI |
|------|------------------|----------|--------|
| GPU加速 | ✅ NVIDIA DGX Cloud | ❌ 网络GPU | ✅ GPU |
| API格式 | ✅ OpenAI兼容 | ✅ OpenAI兼容 | ✅ OpenAI |
| 中文支持 | ✅ DeepSeek V3 | ✅ 优秀 | ⚠️ 一般 |
| 速度 | ✅ 快 | ✅ 快 | ✅ 快 |
| 价格 | ⭐⭐⭐⭐ 中等 | ⭐⭐⭐⭐⭐ 最便宜 | ⭐⭐⭐⭐ 最贵 |
| 稳定性 | ✅ 高 | ✅ 高 | ✅ 高 |
| 中国访问 | ⚠️ 需要稳定网络 | ✅ 好 | ❌ 需要VPN |

**推荐：NVIDIA NIM API + DeepSeek模型 = 最佳组合！**

---

## 🖥️ 在Streamlit中使用

### 界面配置

1. 选择 **"🤖 AI智能优化"** 模式
2. 在侧边栏选择 **"NVIDIA API (推荐)"**
3. 配置：
   - API密钥: `nvapi-xxxxxxxxxxxxxxxxxxxxx`
   - API基础URL: `https://integrate.api.nvidia.com/v1`（自动填充）
   - 模型: `deepseek-ai/deepseek-v3 (推荐 - 中文优化)`

### 可选模型

| 模型 | 描述 | 推荐用途 |
|------|------|---------|
| `deepseek-ai/deepseek-v3` |DeepSeek V3 | 交易优化（强烈推荐） |
| `meta/llama-3.1-8b-instruct` | Llama 3.1 8B | 快速测试 |
| `meta/llama-3.1-70b-instruct` | Llama 3.1 70B | 高质量分析 |
| `qwen/qwen2.5-7b-instruct` | 通义千问 2.5 | 中文理解 |

---

## 💡 完整示例

### 配置优化器

```python
# config.py 或 直接使用
from auto_ai_optimizer import AutoOptimizer

# NVIDIA NIM API 配置
nvidia_optimizer = AutoOptimizer(
    api_key="nvapi-xxxxxxxxxxxxxxxxxxxxx",  # 你的NGC API Key
    api_base="https://integrate.api.nvidia.com/v1",
    model="deepseek-ai/deepseek-v3"  # 推荐模型
)

# 选择币种
coins = optimizer.get_available_coins(3)
selected_coins = optimizer.ask_ai_select_coins(coins, 2)

# 生成参数配置
configs = optimizer.ask_ai_generate_configs(selected_coins, 2)

# 运行优化
result = optimizer.run_single_config(selected_coins, configs[0])

# 查看结果
print(f"最佳收益率: {result['best_return']:.2f}%")
```

---

## 🔍 测试连接

```bash
python -c "
import requests
import os

API_KEY = 'nvapi-xxxxxxxxxxxxxxxxxxxxx'  # 替换为你的Key
API_BASE = 'https://integrate.api.nvidia.com/v1/chat/completions'

response = requests.post(
    API_BASE,
    headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
    json={
        'model': 'deepseek-ai/deepseek-v3',
        'messages': [{'role': 'user', 'content': 'Hello!'}],
        'max_tokens': 50
    }
)

if response.status_code == 200:
    print('✅ 连接成功！')
    print(response.json()['choices'][0]['message']['content'])
else:
    print('❌ 连接失败:', response.status_code, response.text)
"
```

---

## 📝 API兼容性

**好消息：NVIDIA NIM API完全兼容OpenAI格式！**

你的代码**不需要修改**可以直接使用：
```python
# 所有这些API都可以用相同的代码调用！
# 只需更换 api_key, api_base, model

api_base = "https://integrate.api.nvidia.com/v1"           # NVIDIA
api_base = "https://api.deepseek.com/v1"                   # DeepSeek
api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"    # 通义千问
api_base = "https://api.openai.com/v1"                       # OpenAI
```

---

## ❓ 常见问题

**Q: API Key格式**
A: NVIDIA NGC API Key格式为 `nvapi-xxxxxxxxxxxxxxxxxxxxx`（必须以nvapi-开头）

**Q: 如何查看API使用量**
A: 登录NGC控制台查看API使用统计和额度

**Q: 中国访问速度**
A: NVIDIA服务器在海外，建议使用稳定的网络连接或代理

**Q: 价格具体是多少**
A: 官方文档显示约$0.0005/千tokens，比DeepSeek稍高，但API更稳定

**Q: 支持哪些模型**
A: 100+模型，包括Llama、DeepSeek、Qwen、Gemma等，详见：https://docs.api.nvidia.com/nim/reference/llm-apis

---

## 🎯 推荐配置

**交易参数优化最佳配置：**
```python
{
    "api_provider": "NVIDIA NIM",
    "model": "deepseek-ai/deepseek-v3",
    "temperature": 0.7,
    "max_tokens": 3000
}
```

**理由**：
- ✅ DeepSeek V3: 中文理解好，适合分析币种特征
- ✅ NVIDIA GPU: 高速推理，响应时间短
- ✅ 价格合理: 性价比高
- ✅ API稳定: NVIDIA基础设施可靠

---

## 📚 相关文档

- NVIDIA NIM官方文档: https://docs.api.nvidia.com/nim/
- API参考: https://docs.api.nvidia.com/nim/reference/llm-apis
- NGC API Keys: https://org.ngc.nvidia.com/setup/api-keys

---

**✅ NVIDIA NIM API配置完成！现在可以开始使用GPU加速的大模型进行交易优化了！🚀**

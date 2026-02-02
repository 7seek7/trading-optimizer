# 🤖 NVIDIA NIM API 使用指南

** NVIDIA NIM (NVIDIA Inference Microservice) - 云端GPU加速大模型API**

---

## 📖 什么是 NVIDIA NIM？

NVIDIA NIM是NVIDIA提供的云端GPU加速大模型API服务，让你无需本地GPU即可调用强大的大模型。

### 核心优势

✅ **GPU加速**: 使用NVIDIA DGX Cloud的GPU集群
✅ **兼容OpenAI API**: 统一的API格式，易于迁移
✅ **模型丰富**: 100+大模型可选（Llama、DeepSeek、Qwen等）
✅ **按需付费**: 只为使用的资源付费
✅ **免费额度**: 新用户有免费试用

---

## 🚀 快速开始

### 步骤1：获取NVIDIA NGC API Key

1. **访问**: https://org.ngc.nvidia.com/setup/api-keys
2. **登录**: 使用NVIDIA账号登录
3. **生成API密钥**:
   - 点击 "Generate Personal Key"
   - 输入Key Name（如：`trading-bot-optimizer`）
   - Expiration: 选择 "Never Expire"（永不过期）
   - Services Included: 勾选 "NGC Catalog" 和 "Public API Endpoints"
   - 点击 "Generate Personal Key"
4. **复制API Key**: 保存到安全的地方

**API Key格式**: `nvapi-xxxxxxxxxxxxxxxxxxxxx`

---

### 步骤2：API配置信息

```python
# NVIDIA NIM API 基础信息
API_BASE: https://integrate.api.nvidia.com/v1/chat/completions
API_KEY: nvapi-xxxxxxxxxxxxxxxxxxxxx
HEADERS:
  - Authorization: Bearer {api_key}
  - Content-Type: application/json
```

---

## 📊 推荐模型

### 中文优化模型

| 模型 | 描述 | 用途 |
|------|------|------|
| `deepseek-ai/deepseek-v3` | DeepSeek V3 | 通用、代码、数学 |
| `qwen/qwen2.5-7b-instruct` | 通义千问 2.5 | 中文、通用 |
| `thudm/chatglm3-6b` | ChatGLM3 | 中文、对话 |

### 英文/通用模型

| 模型 | 描述 | 用途 |
|------|------|------|
| `meta/llama-3.1-8b-instruct` | Llama 3.1 8B | 快速、通用 |
| `meta/llama-3.1-70b-instruct` | Llama 3.1 70B | 复杂任务、高质量 |
| `mistralai/mistral-7b-instruct` | Mistral 7B | 通用、性价比高 |
| `google/gemma-2-9b-it` | Gemma 2 9B | 通用、Google模型 |

### 交易优化推荐

**最佳选择**: `deepseek-ai/deepseek-v3`
- ✅ 中文支持好
- ✅ 价格低
- ✅ 推理质量高
- ✅ 适合分析和决策

**备选**: `meta/llama-3.1-70b-instruct`
- ✅ 生成能力强
- ✅ 支持复杂推理
- ⚠️ 稍慢，价格稍高

---

## 💰 价格对比

| API服务 | 价格（千tokens） |
|---------|----------------|
| **DeepSeek API** | ¥0.001 (~$0.0001) |
| 通义千问 API | ¥0.00001 |
| OpenAI GPT-3.5 | $0.003 |
| **NVIDIA NIM** | $0.0005-$0.003 |

**估算**:
- NVIDIA NIM价格与其他API相当或更低
- 每次AI优化约需要5,000-10,000 tokens
- 成本：$0.005-$0.03/次（约¥0.04-Y0.2）

**免费额度**:
- NVIDIA通常提供新用户免费试用
- 可在NGC控制台查看

---

## 🔧 配置代码

### 1. 修改 `auto_ai_optimizer.py`

找到以下部分并修改：

```python
def call_ai(self, prompt: str) -> str:
    """调用AI API - 支持NVIDIA NIM"""
    try:
        response = requests.post(
            f"{self.api_base}/chat/completions",  # NVIDIA NIM兼容OpenAI格式
            headers={
                'Authorization': f'Bearer {self.api_key}',  # NVAPI-xxxx
                'Content-Type': 'application/json'
            },
            json={
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的量化交易参数优化专家。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 3000
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"API调用失败: {response.status_code} - {response.text}")
    except Exception as e:
        raise Exception(f"AI调用失败: {str(e)}")
```

这个代码已经兼容NVIDIA NIM的API格式（OpenAI兼容）！

---

### 2. 在Web界面配置NVIDIA API

**Streamlit Web界面已经支持自定义API**，只需配置：

**在侧边栏选择 "AI服务提供商": "NVIDIA API"**

或者在当前版本中：

```
AI服务提供商: NVIDIA
API基础URL: https://integrate.api.nvidia.com/v1
API密钥: nvapi-xxxxxxxxxxxxxxxxxxxxx
模型选择: deepseek-ai/deepseek-v3（任意NVIDIA模型）
```

---

## 📝 Python代码示例

### 基本调用示例

```python
import requests

# NVIDIA NIM API配置
API_KEY = "nvapi-xxxxxxxxxxxxxxxxxxxxx"  # 你的NGC API Key
API_BASE = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "deepseek-ai/deepseek-v3"  # 或其他模型

def call_nvidia_api(prompt: str) -> str:
    """调用NVIDIA NIM API"""
    response = requests.post(
        API_BASE,
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'model': MODEL,
            'messages': [
                {'role': 'system', 'content': '你是量化交易专家'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        },
        timeout=60
    )

    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        raise Exception(f"API调用失败: {response.status_code} - {response.text}")

# 使用示例
prompt = "从以下币种中选择最适合的投资标的：DOGEUSDT, PEPEUSDT, BTCUSDT"
result = call_nvidia_api(prompt)
print(result)
```

---

## 🔌 集成到现有代码

### 方法1: 优化器初始化

```python
from auto_ai_optimizer import AutoOptimizer

# 使用NVIDIA NIM API
optimizer = AutoOptimizer(
    api_key="nvapi-xxxxxxxxxxxxxxxxxxxxx",  # NGC API Key
    api_base="https://integrate.api.nvidia.com/v1",
    model="deepseek-ai/deepseek-v3"  # NVIDIA模型
)

# 运行优化
available_coins = optimizer.get_available_coins(3)
coins = optimizer.ask_ai_select_coins(available_coins, 2)
configs = optimizer.ask_ai_generate_configs(coins, 2)

results = optimizer.run_single_config(coins, configs[0])
```

### 方法2: 在Streamlit界面配置

在 `streamlit_app.py` 中添加NVIDIA选项：

```python
def render_ai_config(self):
    """渲染AI API配置"""
    self.api_source = st.sidebar.selectbox(
        "AI服务提供商",
        ["NVIDIA API (推荐)", "DeepSeek", "通义千问", "OpenAI"]
    )

    if self.api_source == "NVIDIA API (推荐)":
        self.api_key = st.sidebar.text_input(
            "API密钥",
            type="password",
            value="nvapi-",  # 前缀提示
            help="输入你的NVIDIA NGC API Key（nvapi-开头）"
        )
        self.api_base = st.sidebar.text_input(
            "API基础URL",
            value="https://integrate.api.nvidia.com/v1"
        )
        self.model = st.sidebar.selectbox(
            "模型（推荐交易优化）",
            [
                "deepseek-ai/deepseek-v3 (推荐 - 性价比最高)",
                "meta/llama-3.1-8b-instruct (速度快)",
                "meta/llama-3.1-70b-instruct (高质量)",
                "mistralai/mistral-7b-instruct (通用)",
                "qwen/qwen2.5-7b-instruct (中文优化)"
            ]
        )
```

---

## 🎯 使用NVIDIA的优势

### 相比DeepSeek API

| 特性 | DeepSeek API | NVIDIA NIM |
|------|-------------|-----------|
| API稳定性 | 高 | **非常高** |
| GPU资源 | 未知 | **NVIDIA DGX Cloud** |
| 模型质量 | 好 | **优秀** |
| 延迟 | 低 | **更低** |
| 价格 | ¥0.001/千tokens | $0.0005/千tokens (~¥0.004) |
| 中国访问 | **可能需要代理** | **连接稳定** |

### 推荐使用场景

**使用NVIDIA NIM API适用于：**
- ✅ 需要高速推理
- ✅ 需要高质量模型
- ✅ 海外服务器部署
- ✅ 需要稳定的API服务

**继续使用DeepSeek API适用于：**
- ✅ 成本敏感（价格最低）
- ✅ 国内部署
- ✅ 简单易用

---

## 📊 完整配置示例

### .env 配置

```bash
# NVIDIA NIM API
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxx
NVIDIA_API_BASE=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=deepseek-ai/deepseek-v3
```

### Python代码

```python
from dotenv import load_dotenv
from auto_ai_optimizer import AutoOptimizer
import os

load_dotenv()

# 使用NVIDIA NIM
optimizer = AutoOptimizer(
    api_key=os.getenv("NVIDIA_API_KEY"),
    api_base=os.getenv("NVIDIA_API_BASE"),
    model=os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v3")
)

# 运行优化
# ...
```

---

## 🧪 测试连接

### 测试脚本

```python
import requests
import os

# 配置
API_KEY = "nvapi-xxxxxxxxxxxxxxxxxxxxx"  # 替换为你的Key
API_BASE = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "deepseek-ai/deepseek-v3"

print("测试NVIDIA NIM API连接...")

# 测试请求
response = requests.post(
    API_BASE,
    headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    },
    json={
        'model': MODEL,
        'messages': [
            {'role': 'user', 'content': 'Hello! Please say "NVIDIA NIM API works!"'}
        ],
        'temperature': 0.7,
        'max_tokens': 100
    },
    timeout=30
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ 连接成功！")
    print(f"模型响应: {result['choices'][0]['message']['content']}")
else:
    print(f"❌ 连接失败: {response.status_code}")
    print(f"错误信息: {response.text}")
```

运行测试：
```bash
python test_nvidia_api.py
```

预期输出：
```
测试NVIDIA NIM API连接...
✅ 连接成功！
模型响应: NVIDIA NIM API works!
```

---

## 🔄 从其他API迁移

### 从DeepSeek迁移

**之前（DeepSeek）:**
```python
optimizer = AutoOptimizer(
    api_key="sk-xxxx",
    api_base="https://api.deepseek.com/v1",
    model="deepseek-chat"
)
```

**之后（NVIDIA NIM）:**
```python
optimizer = AutoOptimizer(
    api_key="nvapi-xxxx",  # 使用NGC API Key
    api_base="https://integrate.api.nvidia.com/v1",
    model="deepseek-ai/deepseek-v3"  # NVIDIA上的DeepSeek V3
)
```

**就这么简单！** API格式完全兼容！

---

## 📚 模型列表参考

### NVIDIA推荐用于交易优化的模型

**Top 推荐:**
1. `deepseek-ai/deepseek-v3` - 综合性能最强
2. `meta/llama-3.1-8b-instruct` - 速度最快
3. `qwen/qwen2.5-7b-instruct` - 中文优化

**其他高质量模型:**
- `mistralai/mistral-7b-instruct`
- `google/gemma-2-9b-it`
- `meta/llama-3.1-70b-instruct`（复杂分析）

完整模型列表: https://docs.api.nvidia.com/nim/reference/llm-apis

---

## ⚠️ 注意事项

1. **API Key安全**:
   - 不要在代码中硬编码API Key
   - 使用环境变量或`.env`文件
   - 将API Key添加到`.gitignore`

2. **速率限制**:
   - NVIDIA可能有速率限制
   - 新用户有试用额度
   - 超出后需付费

3. **模型选择**:
   - 3-8B模型：速度快（推荐测试）
   - 7-8B模型：性价比高（推荐生产）
   - 70B+模型：质量最高，但慢

4. **网络连接**:
   - NVIDIA API服务器在海外
   - 建议使用稳定的网络
   - 考虑使用代理（如果在中国）

---

## 💡 最佳实践

### 1. 配置管理

```python
# config.py
class NVIDIAConfig:
    API_KEY = os.getenv("NVIDIA_API_KEY")
    API_BASE = "https://integrate.api.nvidia.com/v1"
    DEFAULT_MODEL = "deepseek-ai/deepseek-v3"

    # 模型配置
    MODELS = {
        "fast": "meta/llama-3.1-8b-instruct",
        "balanced": "deepseek-ai/deepseek-v3",
        "quality": "meta/llama-3.1-70b-instruct",
        "chinese": "qwen/qwen2.5-7b-instruct"
    }
```

### 2. 错误处理

```python
def call_ai_with_retry(prompt: str, max_retries: int = 3) -> str:
    """带重试的API调用"""
    for attempt in range(max_retries):
        try:
            return call_nvidia_api(prompt)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"重试 {attempt + 1}/{max_retries}...")
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise e
```

### 3. 成本监控

```python
import requests

def estimate_cost(tokens: int) -> float:
    """估算成本"""
    # NVIDIA NIM定价（参考，实际可能不同）
    price_per_1k_tokens = 0.0005  # $0.0005 per 1k tokens
    return (tokens / 1000) * price_per_1k_tokens

# 使用
tokens_used = 5000
cost = estimate_cost(tokens_used)
print(f"本次调用约花费: ${cost:.4f}")
```

---

## 🚀 立即开始

### 快速配置步骤

1. **获取API Key** (5分钟)
   ```bash
   访问: https://org.ngc.nvidia.com/setup/api-keys
   生成Key: nvapi-xxxxxxxxxxxxx
   ```

2. **修改配置** (2分钟)
   ```bash
   # 在 .env 文件中添加
   NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxx
   NVIDIA_API_BASE=https://integrate.api.nvidia.com/v1
   NVIDIA_MODEL=deepseek-ai/deepseek-v3
   ```

3. **在代码中使用** (1行代码)
   ```python
   optimizer = AutoOptimizer(
       api_key=os.getenv("NVIDIA_API_KEY"),
       api_base=os.getenv("NVIDIA_API_BASE"),
       model=os.getenv("NVIDIA_MODEL")
   )
   ```

4. **开始优化**
   ```bash
   python optimizer.py --symbols DOGEUSDT PEPEUSDT
   ```

---

## 📞 需要帮助？

**文档链接:**
- NVIDIA NIM官方文档: https://docs.api.nvidia.com/nim/
- API参考: https://docs.api.nvidia.com/nim/reference/llm-apis
- Python Quickstart: https://docs.api.nvidia.com/nim/docs/api-quickstart

**常见问题:**
1. API Key不工作 → 检查Key格式是否为nvapi-开头
2. 连接超时 → 检查网络连接，尝试使用代理
3. 401错误 → API Key可能过期或无效
4. 429错误 → 速率限制，等待后重试

---

**✅ NVIDIA NIM API配置完成！**

现在你可以使用NVIDIA的云端GPU加速大模型进行交易参数优化了！🚀

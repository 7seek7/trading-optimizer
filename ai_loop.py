#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能优化循环 - AI自动选择配置并运行优化
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("智能优化循环 - AI自动配置和优化")
print("="*70)

optimizer_dir = Path("optimizer")

# 加载最新结果
result_files = list(optimizer_dir.glob("results_*.json")) if optimizer_dir.exists() else []

if result_files:
    result_file = sorted(result_files, reverse=True)[0]
    print(f"\n加载结果文件: {result_file.name}")

    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = data if isinstance(data, list) else data.get('results', data.get('data', []))

    # 分析结果
    successful = [r for r in results if 'error' not in r.get('metrics', {})]
    failed = [r for r in results if 'error' in r.get('metrics', {})]
    returns = [r['metrics']['total_return'] for r in successful]

    print(f"总测试: {len(results)}, 成功: {len(successful)}, 失败: {len(failed)}")
    print(f"最高收益: {max(returns):+.2f}%, 平均: {sum(returns)/len(returns):+.2f}%")

else:
    print("\n未找到之前的结果文件")
    first_optimize = True
    results = []

# 创建AI提示词
prompt_parts = []
prompt_parts.append("你是一个专业的量化交易参数优化专家。")
prompt_parts.append("")
prompt_parts.append("## 背景")

if results:
    prompt_parts.append("这是第N轮优化，之前的统计结果：")
    prompt_parts.append(f"- 总测试数: {len(results)}")
    prompt_parts.append(f"- 成功: {len(successful)}")
    prompt_parts.append(f"- 失败: {len(failed)}")
    prompt_parts.append(f"- 最高收益: {max(returns):+.2f}%")
    prompt_parts.append(f"- 最低收益: {min(returns):+.2f}%")
    prompt_parts.append(f"- 平均收益: {sum(returns)/len(returns):+.2f}%")

    if successful:
        sorted_results = sorted(successful, key=lambda x: x['metrics']['total_return'], reverse=True)
        top5 = sorted_results[:5]

        prompt_parts.append("")
        prompt_parts.append("前5名最佳组合的参数规律：")
        for i, r in enumerate(top5, 1):
            p = r['params']
            prompt_parts.append(f"  排名{i}:")
            for k, v in p.items():
                prompt_parts.append(f"    {k}={v}")

        if failed:
            prompt_parts.append("")
            prompt_parts.append("失败原因统计：")
            from collections import Counter
            errors = Counter([r['metrics'].get('error', 'Unknown')[:100] for r in failed])
            for err, cnt in errors.most_common(5):
                prompt_parts.append(f"  - {err} ({cnt}次)")
else:
    prompt_parts.append("这是第一轮优化，没有历史数据。")
    prompt_parts.append("请使用默认的保守参数范围进行优化。")

prompt_parts.append("")
prompt_parts.append("## 任务")
prompt_parts.append("")
prompt_parts.append("请分析以上数据，并给出**下一轮优化的参数配置**。")
prompt_parts.append("")
prompt_parts.append("## 要求")
prompt_parts.append("")
prompt_parts.append("1. 只输出JSON格式，不要有其他文字")
prompt_parts.append("2. JSON格式如下：")
prompt_parts.append('```json')
prompt_parts.append('{')
prompt_parts.append('  "strategy": "你的优化策略说明（20字内）",')
prompt_parts.append('  "expected_improvement": "预期的改进说明（20字内）",')
prompt_parts.append('  "config": {')
prompt_parts.append('    "参数名": {')
prompt_parts.append('      "start": 开始值,')
prompt_parts.append('      "stop": 结束值,')
prompt_parts.append('      "step": 步长')
prompt_parts.append('    }')
prompt_parts.append('  },')
prompt_parts.append('  "symbols": ["币种1", "币种2"],')
prompt_parts.append('  "interval": "K线周期",')
prompt_parts.append('  "days": 回测天数')
prompt_parts.append('}')
prompt_parts.append('```')
prompt_parts.append("")
prompt_parts.append("3. 根据当前结果选择：")
prompt_parts.append("   - 如果失败率高：使用主流币种、固定更多参数、缩小范围")
prompt_parts.append("   - 如果收益较低：调整核心参数（PRICE_CHANGE_THRESHOLD、VOLUME_THRESHOLD等）")
prompt_parts.append("   - 如果成功：在最佳参数附近进行精细搜索")
prompt_parts.append("")
prompt_parts.append("4. 推荐配置的参数：")
prompt_parts.append("   - PRICE_CHANGE_THRESHOLD: 价格变化阈值（2-6%）")
prompt_parts.append("   - VOLUME_THRESHOLD: 成交量阈值倍数（2-8倍）")
prompt_parts.append("   - HIGH_PROFIT_THRESHOLD: 高盈利止盈阈值（5-15%）")
prompt_parts.append("   - STOPLOSS_TRIGGER1: 第一级止损触发（-10% 到 -5%）")
prompt_parts.append("   - INITIAL_POSITION: 初始开仓比例（10-30%）")
prompt_parts.append("   - LEVERAGE: 杠杆倍数（1-5）")
prompt_parts.append("")
prompt_parts.append("5. 开始值和结束值应该接近，避免范围过大")
prompt_parts.append("")
prompt_parts.append("## 输出示例")
prompt_parts.append('```json')
prompt_parts.append('{')
prompt_parts.append('  "strategy": "缩小核心参数范围",')
prompt_parts.append('  "expected_improvement": "成功率提升到90%以上",')
prompt_parts.append('  "config": {')
prompt_parts.append('    "PRICE_CHANGE_THRESHOLD": {')
prompt_parts.append('      "start": 3.0,')
prompt_parts.append('      "stop": 4.0,')
prompt_parts.append('      "step": 0.5')
prompt_parts.append('    },')
prompt_parts.append('    "VOLUME_THRESHOLD": {')
prompt_parts.append('      "start": 4.0,')
prompt_parts.append('      "stop": 5.0,')
prompt_parts.append('      "step": 0.25')
prompt_parts.append('    }')
prompt_parts.append('  },')
prompt_parts.append('  "symbols": ["BTCUSDT", "ETHUSDT"],')
prompt_parts.append('  "interval": "5m",')
prompt_parts.append('  "days": 30')
prompt_parts.append('}')
prompt_parts.append('```')

prompt = "\n".join(prompt_parts)

# 保存提示词
prompt_file = optimizer_dir / f"ai_config_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
with open(prompt_file, 'w', encoding='utf-8') as f:
    f.write(prompt)

print(f"\n[步骤1] AI配置提示词已生成: {prompt_file.name}")
print(f"         长度: {len(prompt)} 字符")

print(f"\n" + "="*70)
print("[步骤2] 使用AI生成配置")
print("="*70)
print()
print("有两个选择：")
print()
print("  方式1（推荐 - 免费）:")
print(f"    1. 打开文件: {prompt_file}")
print("    2. 复制全部内容")
print("    3. 粘贴到AI对话（ChatGPT/Claude/通义千问等）")
print("    4. 复制AI输出的JSON")
print("    5. 粘贴到这里继续")
print()
print("  方式2（API调用）:")
print("    需要在.env配置 OPENAI_API_KEY")
print("    输入 'api' 使用API自动调用")
print()

choice = input("请选择 api 或手动粘贴json: ").strip().lower()

ai_config = None

if choice == 'api':
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("[错误] 请在.env配置 OPENAI_API_KEY")
        sys.exit(1)

    try:
        import requests
        print("\n正在调用AI...")

        response = requests.post(
            f"{os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')}/chat/completions",
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的量化交易参数优化专家，只输出JSON格式。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 2000
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            ai_config_str = result['choices'][0]['message']['content']
            print("\nAI返回:")
            print(ai_config_str)

            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', ai_config_str)
            if json_match:
                ai_config = json.loads(json_match.group())
            else:
                ai_config = json.loads(ai_config_str)
        else:
            print(f"[错误] API调用失败: {response.status_code}")
            print(response.text)
            sys.exit(1)
    except Exception as e:
        print(f"[错误] {str(e)}")
        print("\n请改为手动粘贴方式")
        ai_config_str = input("\n请粘贴AI返回的JSON: ").strip()
        if ai_config_str:
            import re
            json_match = re.search(r'\{[\s\S]*\}', ai_config_str)
            if json_match:
                ai_config = json.loads(json_match.group())
            else:
                ai_config = json.loads(ai_config_str)
else:
    ai_config_str = input("请粘贴AI返回的JSON: ").strip()
    if ai_config_str:
        import re
        json_match = re.search(r'\{[\s\S]*\}', ai_config_str)
        if json_match:
            ai_config = json.loads(json_match.group())
        else:
            ai_config = json.loads(ai_config_str)

if not ai_config:
    print("[错误] 未能获取AI配置")
    sys.exit(1)

print(f"\n[步骤3] AI配置分析")
print(f"  策略: {ai_config.get('strategy', 'N/A')}")
print(f"  预期改进: {ai_config.get('expected_improvement', 'N/A')}")
print(f"  币种: {ai_config.get('symbols', [])}")
print(f"  周期: {ai_config.get('interval', 'N/A')}")
print(f"  天数: {ai_config.get('days', 'N/A')}")
print(f"  参数数: {len(ai_config.get('config', {}))}")

# 保存AI配置
config_file = optimizer_dir / f"ai_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(ai_config, f, indent=2, ensure_ascii=False)

print(f"\n[步骤4] 配置已保存: {config_file.name}")

# 询问是否立即运行
print(f"\n" + "="*70)
print("[步骤5] 立即运行优化？")
print("="*70)

run_choice = input("是否立即运行优化？ (y/n): ").strip().lower()

if run_choice == 'y':
    print("\n开始运行优化...")
    print("="*70)

    try:
        from optimizer.optimizer import Optimizer

        symbols = ai_config.get('symbols', ['BTCUSDT'])
        interval = ai_config.get('interval', '5m')
        days = ai_config.get('days', 30)
        config_data = ai_config.get('config', {})

        optimizer = Optimizer(
            symbols=symbols,
            interval=interval,
            days=days,
            param_config=config_data,
            use_offline=True
        )

        optimizer.run()

        print("\n" + "="*70)
        print("优化完成！")
        print("="*70)
        print()
        print("下一步:")
        print("  1. 查看优化结果")
        print("  2. 运行 python optimizer/analyze_ai_loop.py 进行下一轮")
        print("="*70)

    except Exception as e:
        print(f"\n[错误] 优化失败: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print("\n跳过优化。配置已保存，可以稍后手动运行：")
    print(f"\npython optimizer/optimizer.py --offline")
    print(f"  --symbols {' '.join(ai_config.get('symbols', []))}")
    print(f"  --interval {ai_config.get('interval', '5m')}")
    print(f"  --days {ai_config.get('days', 30)}")
    print(f"  --config {config_file}")

print("\n" + "="*70)

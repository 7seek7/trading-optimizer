#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("AI智能分析工具")
print("="*70)

optimizer_dir = Path("optimizer")
result_files = list(optimizer_dir.glob("results_*.json")) if optimizer_dir.exists() else []

if not result_files:
    print("\n未找到结果文件，请先运行参数优化")
    sys.exit(0)

result_file = sorted(result_files, reverse=True)[0]
print("\n加载结果文件:", result_file.name)

with open(result_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data if isinstance(data, list) else data.get('results', data.get('data', []))
print("成功加载", len(results), "条结果\n")

summary = {
    'total': len(results),
    'successful': 0,
    'failed': 0,
    'best_return': -999999,
    'worst_return': 999999,
    'returns': [],
    'failed_reasons': {},
    'top_5': []
}

for r in results:
    m = r.get('metrics', {})
    if 'error' in m:
        summary['failed'] += 1
        err = m.get('error', 'Unknown')[:100]
        summary['failed_reasons'][err] = summary['failed_reasons'].get(err, 0) + 1
    else:
        summary['successful'] += 1
        ret = m.get('total_return', 0)
        summary['returns'].append(ret)
        if ret > summary['best_return']:
            summary['best_return'] = ret
        if ret < summary['worst_return']:
            summary['worst_return'] = ret

if summary['returns']:
    summary['avg_return'] = sum(summary['returns']) / len(summary['returns'])
    sorted_results = sorted(
        [r for r in results if 'error' not in r.get('metrics', {})],
        key=lambda x: x['metrics'].get('total_return', 0),
        reverse=True
    )
    summary['top_5'] = sorted_results[:5]

prompt_parts = []
prompt_parts.append("你是一个专业的量化交易参数优化专家。请分析以下回测优化结果，并给出专业的下一步优化建议。")
prompt_parts.append("")
prompt_parts.append("## 优化结果统计")
prompt_parts.append("")
prompt_parts.append("- 总测试数: " + str(summary['total']))
prompt_parts.append("- 成功: " + str(summary['successful']))
prompt_parts.append("- 失败: " + str(summary['failed']))
prompt_parts.append("- 最高收益: " + f"{summary['best_return']:+.2f}%")
prompt_parts.append("- 最低收益: " + f"{summary['worst_return']:+.2f}%")
prompt_parts.append("- 平均收益: " + f"{summary['avg_return']:+.2f}%")
prompt_parts.append("")
prompt_parts.append("## 失败原因统计")
prompt_parts.append("")

for err, cnt in summary['failed_reasons'].items():
    prompt_parts.append(f"- {err} ({cnt}次)")

prompt_parts.append("")
prompt_parts.append("## TOP 5 最佳组合")
prompt_parts.append("")

for i, r in enumerate(summary['top_5'], 1):
    m = r['metrics']
    p = r['params']
    prompt_parts.append(f"排名{i}: 收益{m.get('total_return', 0):+.2f}%, 交易{m.get('total_trades', 0)}笔")
    prompt_parts.append("参数:")
    for k, v in p.items():
        prompt_parts.append(f"  {k}={v}")
    prompt_parts.append("")

prompt_parts.append("## 分析和改进建议")
prompt_parts.append("")
prompt_parts.append("请给出以下分析和建议：")
prompt_parts.append("")
prompt_parts.append("1. 结果质量评估")
prompt_parts.append("2. 失败分析")
prompt_parts.append("3. 参数分析")
prompt_parts.append("4. 下一步优化建议（具体的JSON配置）")
prompt_parts.append("5. 其他建议")

prompt = "\n".join(prompt_parts)

prompt_file = optimizer_dir / f"ai_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
with open(prompt_file, 'w', encoding='utf-8') as f:
    f.write(prompt)

print(f"[OK] 提示词已生成: {prompt_file}")
print(f"    长度: {len(prompt)} 字符")

print("\n" + "="*70)
print("下一步：")
print("="*70)
print()
print("1. 打开提示词文件")
print("2. 复制全部内容")
print("3. 粘贴到AI对话（ChatGPT/Claude/通义千问等）")
print("4. 获取AI分析和建议")
print("5. 根据建议调整参数并重新优化")
print()
print("="*70)

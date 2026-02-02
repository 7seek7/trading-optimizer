#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析失败的回测
"""

import sys
import os
import pickle
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("失败回测分析工具")
print("="*70)

# 查找optimizer目录下所有results_*.json文件
optimizer_dir = Path("optimizer")
result_files = []

if optimizer_dir.exists():
    # 查找所有results_*.json文件
    result_files = sorted(optimizer_dir.glob("results_*.json"), reverse=True)

if not result_files:
    print("\n未找到任何结果文件")
    print("\n可能的原因:")
    print("  1. 优化还未完成")
    print("  2. 优化完成后结果未保存")
    print("  3. 使用的是旧版本代码，没有保存功能")
    print()
    print("请检查:")
    print("  - 优化是否成功完成？")
    print("  - 是否出现了 '已保存完整结果' 的提示？")
    print()
    sys.exit(0)

# 使用最新的结果文件
result_file = result_files[0]
print(f"\n找到结果文件: {result_file.name}")

results = None
try:
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, list):
        results = data
    elif isinstance(data, dict) and 'results' in data:
        results = data['results']
    elif isinstance(data, dict) and 'data' in data:
        results = data['data']

    if results:
        print(f"成功加载 {len(results)} 条结果")
    else:
        print("结果文件格式不正确或为空")
        sys.exit(1)
except Exception as e:
    print(f"[错误] 加载失败: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if not results:
    print("\n未找到结果文件")
    print("\n请手动指定结果文件路径，或检查以下位置:")
    for f in result_files:
        print(f"  - {f}")
    sys.exit(1)

# 分析结果
total = len(results)
failed = [r for r in results if 'error' in r.get('metrics', {})]
successful = [r for r in results if 'error' not in r.get('metrics', {})]

print(f"\n" + "="*70)
print("统计信息")
print("="*70)
print(f"总回测数: {total}")
print(f"成功: {len(successful)} ({len(successful)/total*100:.1f}%)")
print(f"失败: {len(failed)} ({len(failed)/total*100:.1f}%)")

if successful:
    returns = [r['metrics'].get('total_return', 0) for r in successful]
    positive = len([r for r in returns if r > 0])
    print(f"\n成功回测的收益统计:")
    print(f"  盈利: {positive} 个 ({positive/len(successful)*100:.1f}%)")
    print(f"  最高: {max(returns):+.2f}%")
    print(f"  最低: {min(returns):+.2f}%")
    print(f"  平均: {sum(returns)/len(returns):+.2f}%")

if failed:
    # 统计错误类型
    error_messages = Counter()
    for r in failed:
        error = r['metrics'].get('error', 'Unknown')
        # 只取错误消息的前100个字符
        short_error = error[:100] if len(error) > 100 else error
        error_messages[short_error] += 1

    print(f"\n" + "="*70)
    print("失败原因统计 (最多10种)")
    print("="*70)
    for error, count in error_messages.most_common(10):
        print(f"\n  [{count}次] {error}")

    # 显示前10个失败案例的详细参数
    print(f"\n" + "="*70)
    print("失败案例详情 (前10个)")
    print("="*70)
    for i, result in enumerate(failed[:10], 1):
        error = result['metrics'].get('error', 'Unknown')
        params = result['params']
        print(f"\n  失败 #{i}:")
        print(f"    错误: {error[:200]}")  # 只显示前200个字符
        print(f"    参数:")
        for key, value in params.items():
            print(f"      {key} = {value}")

print(f"\n" + "="*70)

# 生成失败的详细日志到文件
log_file = Path(f"optimizer/failed_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
with open(log_file, 'w', encoding='utf-8') as f:
    f.write("="*70 + "\n")
    f.write("失败回测详细分析\n")
    f.write("="*70 + "\n\n")
    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"总回测数: {total}\n")
    f.write(f"成功: {len(successful)}\n")
    f.write(f"失败: {len(failed)}\n\n")

    if failed:
        # 详细错误统计
        f.write("="*70 + "\n")
        f.write("错误统计\n")
        f.write("="*70 + "\n\n")
        for error, count in error_messages.most_common():
            f.write(f"[{count}次] {error}\n\n")

        # 所有失败案例
        f.write("="*70 + "\n")
        f.write("所有失败案例详情\n")
        f.write("="*70 + "\n\n")
        for i, result in enumerate(failed, 1):
            error = result['metrics'].get('error', 'Unknown')
            params = result['params']
            f.write(f"失败 #{i}\n")
            f.write(f"错误: {error}\n")
            f.write("参数:\n")
            for key, value in params.items():
                f.write(f"  {key} = {value}\n")
            f.write("\n")

print(f"\n详细分析已保存到: {log_file}")
print("\n建议:")
if len(failed) > len(successful):
    print("  [!] 失败率很高，建议:")
    print("      1. 检查错误原因，修正参数范围")
    print("      2. 减少参数组合数")
    print("      3. 使用更保守的参数范围")
else:
    print("  [i] 失败率正常，失败的参数组合可能不够合理")
    print("      可以参考成功案例的参数范围进行调整")

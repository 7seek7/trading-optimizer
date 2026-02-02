#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果分析器
分析和比较不同参数组合的回测结果，找出最优配置
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from utils.logger import Logger

logger = Logger.get_logger('optimizer_analyzer')


class ResultAnalyzer:
    """结果分析器 - 简化版"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def add_results(self, param_combinations: List[Dict[str, float]],
                    backtest_results: List[Dict[str, Any]]):
        """添加回测结果"""
        for params, result in zip(param_combinations, backtest_results):
            self.results.append({
                'params': params,
                'metrics': result
            })

    def analyze_and_print(self) -> Dict[str, Any]:
        """分析并打印结果"""
        if not self.results:
            return {'error': '没有结果'}

        # 分离成功和失败的回测
        successful_results = [r for r in self.results if 'error' not in r.get('metrics', {})]
        failed_results = [r for r in self.results if 'error' in r.get('metrics', {})]

        # 如果没有成功的回测，直接失败
        if not successful_results:
            print("\n" + "=" * 70)
            print("参数优化结果")
            print("=" * 70)
            print(f"\n[错误] 所有 {len(self.results)} 个回测都失败了！")
            print(f"\n失败原因:")
            for result in failed_results[:5]:  # 只显示前5个
                error = result['metrics'].get('error', 'Unknown')
                print(f"  - {error[:100]}")
            print(f"\n建议:")
            print(f"  1. 运行 python optimizer/analyze_failures.py 查看详细错误")
            print(f"  2. 检查币种是否在测试网支持列表中")
            print(f"  3. 调整参数范围，避免极端值")
            print("=" * 70)
            return {
                'error': '全部失败',
                'failed_count': len(failed_results)
            }

        # 只分析成功的回测
        sorted_results = sorted(
            successful_results,
            key=lambda x: x['metrics'].get('total_return', 0),
            reverse=True
        )

        # 计算统计
        returns = [r['metrics'].get('total_return', 0) for r in successful_results]
        positive_count = len([r for r in returns if r > 0])
        failed_count = len(failed_results)
        failed_rate = failed_count / len(self.results) * 100

        print("\n" + "=" * 70)
        print("参数优化结果")
        print("=" * 70)

        print(f"\n统计信息:")
        print(f"  总测试数: {len(self.results)}")
        print(f"  成功: {len(successful_results)} ({len(successful_results)/len(self.results)*100:.1f}%)")
        print(f"  失败: {failed_count} ({failed_rate:.1f}%)")
        print(f"  盈利组合: {positive_count} 个")
        print(f"  正收益率: {positive_count / len(successful_results) * 100:.1f}%")
        print(f"  最高收益: {max(returns):+.2f}%")
        print(f"  最低收益: {min(returns):+.2f}%")
        print(f"  平均收益: {sum(returns) / len(successful_results):+.2f}%")

        # 失败率警告
        if failed_rate > 20:
            print(f"\n[警告] 失败率过高 ({failed_rate:.1f}%)！建议:")
            print(f"  - 运行 python optimizer/analyze_failures.py 分析失败原因")
            print(f"  - 检查币种是否在测试网支持列表中")
            print(f"  - 调整参数范围，固定更多参数")
        elif failed_rate > 10:
            print(f"\n[注意] 失败率较高 ({failed_rate:.1f}%)，建议检查参数配置")
        elif failed_rate > 0:
            print(f"\n[提示] 有 {failed_count} 个回测失败，失败的参数组合已被过滤")

        # 前五名
        print(f"\n【TOP 5 最佳组合】")
        for i, result in enumerate(sorted_results[:5], 1):
            metrics = result['metrics']
            params = result['params']
            print(f"\n  排名 #{i}: 收益 {metrics.get('total_return', 0):+.2f}%, "
                  f"资金 {metrics.get('final_balance', 0):.0f}, "
                  f"交易 {metrics.get('total_trades', 0)}")
            print(f"  参数:")
            for param, value in params.items():
                print(f"      {param} = {value}")

        # 后五名
        if len(sorted_results) > 5:
            print(f"\n【BOTTOM 5 最差组合】")
            for i, result in enumerate(sorted_results[-5:], 1):
                metrics = result['metrics']
                params = result['params']
                print(f"\n  排名 #{len(sorted_results) - 5 + i}: "
                      f"收益 {metrics.get('total_return', 0):+.2f}%, "
                      f"资金 {metrics.get('final_balance', 0):.0f}")
                print(f"  参数:")
                for param, value in params.items():
                    print(f"      {param} = {value}")

        print("\n" + "=" * 70)

        return {
            'top_5': sorted_results[:5],
            'bottom_5': sorted_results[-5:] if len(sorted_results) > 5 else [],
            'statistics': {
                'count': len(self.results),
                'successful': len(successful_results),
                'failed': failed_count,
                'positive': positive_count,
                'max': max(returns),
                'min': min(returns),
                'avg': sum(returns) / len(successful_results)
            },
            'best': sorted_results[0] if sorted_results else None
        }

    def update_env_file(self, best_params: Dict[str, float], env_path: Optional[Union[str, Path]] = None):
        """
        更新 .env 文件中的参数

        :param best_params: 最优参数字典
        :param env_path: .env 文件路径
        """
        if env_path is None:
            env_path = Path(__file__).parent.parent / '.env'

        env_path = Path(env_path) if isinstance(env_path, str) else env_path

        if not env_path.exists():
            raise FileNotFoundError(f"环境变量文件不存在: {env_path}")

        # 读取现有内容
        env_content = env_path.read_text(encoding='utf-8')

        # 更新每个参数
        updated_lines = []
        for key, value in best_params.items():
            pattern = f'^{key}=.*$'

            if re.search(pattern, env_content, re.MULTILINE):
                # 替换
                env_content = re.sub(pattern, f'{key}={value}', env_content, flags=re.MULTILINE)
                updated_lines.append(key)
            else:
                # 添加
                env_content += f'\n{key}={value}'
                updated_lines.append(key)

        # 写入文件
        env_path.write_text(env_content, encoding='utf-8')

        logger.info(f"已更新 .env 文件: {', '.join(updated_lines)}")
        print(f"\n已更新 .env 文件中的参数:")
        for key in updated_lines:
            print(f"  - {key} = {best_params[key]}")

    def get_best_params(self) -> Dict[str, float]:
        """获取最优参数"""
        if not self.results:
            return {}

        sorted_results = sorted(
            self.results,
            key=lambda x: x['metrics'].get('total_return', 0),
            reverse=True
        )
        return sorted_results[0]['params']

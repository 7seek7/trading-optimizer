#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全自动化AI参数优化系统
- AI自动选择币种
- AI自动生成多组参数
- 自动批量回测
- 持续迭代优化
"""

import sys
import os
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AutoOptimizer:
    """全自动化AI参数优化器"""

    def __init__(self, api_key: str, api_base: str, model: str):
        """
        初始化自动优化器

        :param api_key: AI API密钥
        :param api_base: API基础URL
        :param model: 模型名称
        """
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.optimizer_dir = Path("optimizer")
        self.optimizer_dir.mkdir(exist_ok=True)

        # 高波动山寨币列表
        self.altcoins = [
            "DOGEUSDT", "4USDT", "AIAUSDT", "BROCCOLI714USDT", "PIPPINUSDT",
            "IPUSDT", "WIFUSDT", "ZECUSDT", "PEPEUSDT", "BONKUSDT",
            "NEARUSDT", "ARBUSDT", "OPUSDT", "UNIUSDT", "AAVEUSDT",
            "LINKUSDT", "GMTUSDT", "AXSUSDT", "SANDUSDT"
        ]

    def get_available_coins(self, max_coins: int = 5) -> List[str]:
        """获取可用的山寨币"""
        data_dir = Path("data/historical")
        available = []

        if data_dir.exists():
            for coin in self.altcoins:
                files = list(data_dir.glob(f"{coin}_1m_*days_*.csv"))
                if files:
                    available.append(coin)

        # 优先选择较大的数据文件（90天）
        available.sort(key=lambda c: max(
            (f.stat().st_size for f in data_dir.glob(f"{c}_1m_90days_*.csv")),
            default=0
        ), reverse=True)

        return available[:max_coins] if max_coins else available

    def call_ai(self, prompt: str) -> str:
        """调用AI API"""
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
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
                raise Exception(f"API调用失败: {response.status_code}")
        except Exception as e:
            raise Exception(f"AI调用失败: {str(e)}")

    def ask_ai_select_coins(self, available_coins: List[str],
                           target_count: int = 3) -> List[str]:
        """让AI选择要优化的币种"""
        prompt = f"""你是量化交易专家。请从以下高波动山寨币中选择最优的{target_count}个进行参数优化。

可用币种：
{', '.join(available_coins)}

选择标准：
1. 高波动性（适合策略）
2. 流动性好（易于交易）
3. 适合这套交易系统的特点（捕获价格突变）

请选择{target_count}个币种，只输出币种列表，用逗号分隔，不要有其他文字。
示例输出格式：
DOGEUSDT, 4USDT, AIAUSDT
"""
        response = self.call_ai(prompt)
        # 提取币种列表
        coins = [c.strip() for c in response.split(',') if c.strip(' :\n') and 'USDT' in c.upper()]
        return coins[:target_count]

    def ask_ai_generate_configs(self, coins: List[str], config_num: int = 3) -> List[Dict]:
        """让AI生成多组参数配置"""
        coin_list = ', '.join(coins)
        prompt = f"""你是量化交易参数优化专家。请为以下{len(coins)}个高性能山寨币生成{config_num}组不同的参数配置。

币种：{coin_list}

优化目标：最大化收益率

请生成{config_num}组配置，每组包含参数范围。输出格式：
```json
[
  {{
    "id": 1,
    "strategy": "策略描述（10字内）",
    "config": {{
      "PRICE_CHANGE_THRESHOLD": {{"start": 3.0, "stop": 5.0, "step": 0.5}},
      "VOLUME_THRESHOLD": {{"start": 3.0, "stop": 5.0, "step": 0.5}},
      "HIGH_PROFIT_THRESHOLD": {{"start": 15.0, "stop": 25.0, "step": 2.0}},
      "STOPLOSS_TRIGGER1": {{"start": -12.0, "stop": -8.0, "step": 1.0}},
      "INITIAL_POSITION": {{"start": 10, "stop": 20, "step": 5}}
    }},
    "expected_return": "预期收益（10%）"
  }}
]
```

要求：
1. 参数范围要合理，避免过大
2. 每10%组合数 ≈ 10-50个
3. 山寨币波动大，适当放宽止盈止损
4. 只输出JSON，不要有其他文字
"""
        response = self.call_ai(prompt)

        # 提取JSON
        import re
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            try:
                configs = json.loads(json_match.group())
                return configs[:config_num]
            except:
                pass

        raise Exception("AI返回的JSON格式不正确")

    def run_single_config(self, coins: List[str], config: Dict) -> Dict:
        """运行单组配置的优化"""
        from optimizer.optimizer import Optimizer

        print(f"\n运行配置 #{config['id']}: {config['strategy']}")
        print(f"  预期收益: {config.get('expected_return', 'N/A')}")

        try:
            optimizer = Optimizer(
                symbols=coins,
                interval='5m',
                days=90,
                param_config=config['config'],
                use_offline=True
            )

            # 跳过确认
            import builtins
            original_input = builtins.input
            builtins.input = lambda x: 'y'

            optimizer.run()

            builtins.input = original_input

            # 读取结果
            result_files = list(self.optimizer_dir.glob("results_*.json"))
            if result_files:
                latest = max(result_files, key=lambda f: f.stat().st_mtime)
                with open(latest, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                results = data if isinstance(data, list) else data.get('results', [])

                # 统计
                successful = [r for r in results if 'error' not in r.get('metrics', {})]
                returns = [r['metrics']['total_return'] for r in successful]

                return {
                    'config_id': config['id'],
                    'strategy': config['strategy'],
                    'total': len(results),
                    'successful': len(successful),
                    'failed': len(results) - len(successful),
                    'best_return': max(returns) if returns else 0,
                    'avg_return': sum(returns) / len(returns) if returns else 0,
                    'positive_rate': len([r for r in returns if r > 0]) / len(returns) if returns else 0,
                    'results_summary': {
                        'top_3': sorted(successful, key=lambda x: x['metrics']['total_return'], reverse=True)[:3]
                    }
                }

        except Exception as e:
            return {
                'config_id': config['id'],
                'strategy': config['strategy'],
                'error': str(e)
            }

    def analyze_all_configs(self, results: List[Dict]) -> Dict:
        """分析所有配置的结果"""
        # 使用AI分析并给出下一步建议
        summary = f"""请分析以下{len(results)}组参数配置的优化结果：

"""

        for idx, r in enumerate(results, 1):
            if 'error' in r:
                summary += f"配置{idx} ({r.get('strategy', 'N/A')}): 失败 - {r['error']}\n"
            else:
                summary += f"""配置{idx} ({r.get('strategy', 'N/A')}):
  总测试: {r['total']}
  成功: {r['successful']} ({r['successful']/r['total']*100:.0f}%)
  最高收益: {r['best_return']:+.2f}%
  平均收益: {r['avg_return']:+.2f}%
  正收益率: {r['positive_rate']*100:.1f}%
"""

        summary += """

请分析并给出：
1. 哪组配置表现最好？为什么？
2. 各组配置的优劣势？
3. 下一轮优化建议（生成新配置）

直接输出最佳配置的参数范围（JSON格式）：
```json
{
  "best_config": {
    "PRICE_CHANGE_THRESHOLD": {"start": X, "stop": Y, "step": Z},
    ...
  },
  "recommendation": "建议说明"
}
```
"""

        response = self.call_ai(summary)

        # 保存分析结果
        analysis_file = self.optimizer_dir / f"auto_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write(response)

        print(f"\n[AI分析] 已保存: {analysis_file.name}")

        # 提取最佳配置
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())

        return {'recommendation': '无法提取最佳配置'}

    def run_auto_optimization(self, rounds: int = 3, max_coins: int = 3, configs_per_round: int = 3):
        """运行全自动化优化"""
        print("="*70)
        print("AI全自动参数优化系统")
        print("="*70)

        best_overall = {
            'return': -999999,
            'config': None,
            'coins': None
        }

        for round_num in range(1, rounds + 1):
            print(f"\n{'='*70}")
            print(f"第 {round_num} 轮优化")
            print(f"{'='*70}")

            # 步骤1: AI选择币种
            if round_num == 1:
                print("\n[步骤1] AI选择币种...")
                available_coins = self.get_available_coins(max_coins)
                coins = self.ask_ai_select_coins(available_coins, max_coins)
                print(f"AI选择的币种: {', '.join(coins)}")
            else:
                print(f"\n[步骤1] 使用币种: {', '.join(coins)}")

            # 步骤2: AI生成参数配置
            print(f"\n[步骤2] AI生成{configs_per_round}组参数配置...")
            configs = self.ask_ai_generate_configs(coins, configs_per_round)
            print(f"已生成{len(configs)}组配置")

            # 步骤3: 批量运行优化
            print(f"\n[步骤3] 批量运行{len(configs)}组配置优化...")
            round_results = []

            for config in configs:
                result = self.run_single_config(coins, config)
                round_results.append(result)

            # 步骤4: AI分析结果
            print(f"\n[步骤4] AI分析本轮结果...")
            analysis = self.analyze_all_configs(round_results)

            # 步骤5: 更新最佳配置
            for r in round_results:
                if 'error' not in r and r['best_return'] > best_overall['return']:
                    best_overall['return'] = r['best_return']
                    best_overall['config'] = r
                    best_overall['coins'] = coins

            print(f"\n[进度] 当前最佳收益: {best_overall['return']:+.2f}%")

            if round_num < rounds:
                print(f"\n[提示] 准备开始第{round_num+1}轮优化...")
                time.sleep(2)

        # 最终报告
        print(f"\n{'='*70}")
        print("自动优化完成！")
        print(f"{'='*70}")

        print(f"\n最佳配置:")
        print(f"  币种: {', '.join(best_overall['coins'])}")
        print(f"  策略: {best_overall['config'].get('strategy', 'N/A')}")
        print(f"  最高收益: {best_overall['return']:+.2f}%")
        print(f"  成功/总数: {best_overall['config'].get('successful', 0)}/{best_overall['config'].get('total', 0)}")

        return best_overall


def main():
    import argparse

    parser = argparse.ArgumentParser(description='AI全自动参数优化')
    parser.add_argument('--apikey', required=True, help='AI API密钥')
    parser.add_argument('--base', default='https://api.openai.com/v1', help='API基础URL')
    parser.add_argument('--model', default='gpt-4', help='模型名称')
    parser.add_argument('--rounds', type=int, default=3, help='优化轮数')
    parser.add_argument('--coins', type=int, default=3, help='每轮选择的币种数')
    parser.add_argument('--configs', type=int, default=3, help='每轮生成的配置数')

    args = parser.parse_args()

    # 创建优化器
    auto_optimizer = AutoOptimizer(args.apikey, args.base, args.model)

    # 运行全自动优化
    best = auto_optimizer.run_auto_optimization(
        rounds=args.rounds,
        max_coins=args.coins,
        configs_per_round=args.configs
    )

    print(f"\n最终最佳配置已保存，可以查看详细结果")


if __name__ == '__main__':
    main()

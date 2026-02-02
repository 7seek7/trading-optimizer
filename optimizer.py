#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数优化器主程序
使用现有回测模块，自动测试参数组合
完整优化模式现在会读取 config_full_alert_trade.json
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Optimizer:
    """参数优化器主类"""

    def __init__(self, symbols: List[str], interval: str, days: int,
                 param_config: Optional[Dict[str, Dict[str, float]]] = None,
                 config_file: Optional[str] = None,
                 use_json_config: bool = False,
                 use_testnet: bool = False,
                 use_offline: bool = False,
                 no_save: bool = False):
        """
        初始化优化器

        :param symbols: 回测币种
        :param interval: K线周期
        :param days: 回测天数
        :param param_config: 参数配置
        :param config_file: 配置文件路径
        :param use_json_config: 是否使用JSON配置文件
        :param use_testnet: 是否使用测试网（推荐中国用户）
        :param use_offline: 是否使用离线模式（推荐有缓存时使用）
        :param no_save: 是否保存结果到文件
        """
        self.symbols = symbols
        self.interval = interval
        self.days = days
        self.use_testnet = use_testnet
        self.use_offline = use_offline
        self.no_save = no_save

        # 加载参数配置
        if config_file:
            self.param_config = self._load_config(config_file)
        elif param_config:
            self.param_config = param_config
        elif use_json_config:
            # 使用JSON配置文件
            self.param_config = self._load_config('optimizer/config_full_alert_trade.json')
        else:
            # 默认使用快速优化配置
            from optimizer.parameter_grid import create_quick_config
            self.param_config = create_quick_config()

        # 初始化组件
        from optimizer.parameter_grid import ParameterGrid
        from optimizer.backtest_executor import BacktestExecutor
        from optimizer.result_analyzer import ResultAnalyzer

        self.grid = ParameterGrid(self.param_config)
        self.executor = BacktestExecutor(symbols, interval, days,
                                       use_testnet=use_testnet,
                                       use_offline=use_offline)
        self.analyzer = ResultAnalyzer()

    def _load_config(self, config_file: str) -> Dict[str, Dict[str, float]]:
        """加载配置文件"""
        import json
        
        path = Path(config_file)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        with open(path, 'r', encoding='utf-8') as f:
            raw_config = json.load(f)

        # 过滤有效的参数配置：
        # 1. 排除以 '_' 开头的注释字段
        # 2. 只保留字典类型（排除字符串注释标题）
        param_config = {}
        for key, value in raw_config.items():
            # 跳过注释字段（以 _ 开头）
            if isinstance(key, str) and key.startswith('_'):
                continue
            # 只保留字典类型的参数配置（跳过字符串标题）
            if isinstance(value, dict) and 'start' in value and 'stop' in value and 'step' in value:
                param_config[key] = value

        if not param_config:
            print(f"\n[警告] 配置文件中没有有效的参数配置")
            print(f"  请确保配置文件中包含类似以下格式的参数:")
            print(f'  "PARAM_NAME": {{"start": 1.0, "stop": 5.0, "step": 0.5}}')

        return param_config

    def print_estimate(self):
        """打印时间估算"""
        print("\n" + "=" * 70)
        print("参数优化 - 时间估算")
        print("=" * 70)

        print(f"\n回测配置:")
        print(f"  - 币种: {', '.join(self.symbols)}")
        print(f"  - K线周期: {self.interval}")
        print(f"  - 回测天数: {self.days} 天")

        print(f"\n待优化参数 ({len(self.param_config)} 个):")
        for i, (param, config) in enumerate(self.param_config.items(), 1):
            print(f"  {i:2}. {param}")
            is_fixed = (config['start'] == config['stop'])
            type_str = "固定" if is_fixed else "范围"
            print(f"      {type_str}: {config['start']} ~ {config['stop']}")

        combinations_count = self.grid.count_combinations()
        print(f"\n总组合数: {combinations_count:,}")

        # 估算时间
        try:
            estimate = self.executor.estimate_time([{}] * combinations_count)
            if estimate:
                print(f"\n预计时间:")
                print(f"  - 数据量: {estimate['total_klines']:,} 根K线")
                print(f"  - 可用进程: {estimate['max_workers']}")

                if estimate['estimated_minutes'] < 60:
                    print(f"  - 预计耗时: {estimate['estimated_minutes']:.1f} 分钟")
                else:
                    print(f"  - 预计耗时: {estimate['estimated_hours']:.1f} 小时")
        except Exception as e:
            print(f"\n时间估算失败: {str(e)}")
            print(f"  可能原因: 回测数据未准备")

        print("\n" + "=" * 70)

        print("\n💡 数据准备说明:")
        print("  - 首次运行将从币安API下载历史K线数据（需要网络连接）")
        print("  - 后续运行会使用本地缓存，不需要网络")
        print("  - 如果下载失败，请检查网络连接或VPN设置")
        print("  - 或者使用测试网模式：")
        print("    * Windows CMD: set USE_TESTNET=1")
        print("    * Windows PowerShell: $env:USE_TESTNET=1")
        print("    * 命令行: python optimizer/optimizer.py --testnet --quick --symbols BTCUSDT --days 30")

    def run(self) -> Dict[str, Any]:
        """运行优化"""
        # 1. 显示估算
        self.print_estimate()

        # 2. 用户确认
        try:
            confirm = input("\n是否开始优化？(y/n): ").strip().lower()
            if confirm != 'y':
                print("优化已取消")
                return {'status': 'cancelled'}
        except (EOFError, KeyboardInterrupt):
            print("\n优化已取消")
            return {'status': 'cancelled'}

        # 3. 生成参数组合
        print("\n生成参数组合...")
        param_combinations = self.grid.generate()
        print(f"已生成 {len(param_combinations):,} 个组合")

        # 4. 运行回测
        print("\n开始回测...")
        results = self.executor.run_parallel(param_combinations)

        # 5. 分析结果
        print("\n分析结果...")
        self.analyzer.add_results(param_combinations, results)
        analysis = self.analyzer.analyze_and_print()

        # 保存完整结果（用于分析失败原因）
        self._save_results(param_combinations, results)

        # 6. 显示失败统计（如果有失败）
        failed_count = sum(1 for r in results if 'error' in r)
        if failed_count > 0:
            print(f"\n[注意] 有 {failed_count} 个回测失败")
            print(f"  可以运行以下命令分析失败原因:")
            print(f"  python optimizer/analyze_failures.py")

        # 7. 更新环境变量
        if analysis.get('best'):
            best_params = analysis['best']['params']
            try:
                self.analyzer.update_env_file(best_params)
            except Exception as e:
                print(f"\n更新 .env 文件失败: {str(e)}")

            return {
                'status': 'completed',
                'analysis': analysis,
                'best_params': best_params
            }

        return {'status': 'completed', 'analysis': analysis}

    def _save_results(self, param_combinations: List[Dict[str, float]],
                     backtest_results: List[Dict[str, Any]]):
        """保存完整结果（使用StorageManager）"""
        # 使用StorageManager保存
        from storage_manager import get_storage_manager

        storage = get_storage_manager()

        # 准备元数据
        metadata = {
            'symbols': self.symbols,
            'interval': self.interval,
            'days': self.days,
            'use_testnet': self.use_testnet,
            'use_offline': self.use_offline,
            'param_config': self.param_config
        }

        # 保存结果
        json_file = storage.save_optimization_result(param_combinations, backtest_results, metadata)

        print(f"\n[保存] 完整结果已保存到: {json_file}")
        print(f"      可以使用 analyze_failures.py 分析失败的回测")


def interactive_mode():
    """交互式模式"""
    print("\n" + "=" * 70)
    print("参数优化器 - 交互式")
    print("=" * 70)

    # 选择配置模式
    print("\n请选择优化模式:")
    print("-" * 70)
    print("  [1] 完整优化 - 使用 config_full_alert_trade.json (你设置的参数)")
    print("  [2] 快速优化 - 核心参数 (推荐，约5-20分钟)")
    print("  [3] 自定义配置 - 指定其他配置文件")
    print("-" * 70)

    try:
        mode_choice = input("请选择 (1/2/3，默认1): ").strip() or '1'
    except (EOFError, KeyboardInterrupt):
        return

    # 获取币种
    while True:
        try:
            symbols_input = input("\n回测币种（多个用空格分隔）: ").strip().upper()
            if symbols_input:
                symbols = symbols_input.split()
                break
            print("请输入币种！")
        except (EOFError, KeyboardInterrupt):
            return

    # 获取天数
    while True:
        try:
            days_input = input("回测天数（默认30）: ").strip()
            if not days_input:
                days = 30
                break
            days = int(days_input)
            if days > 0:
                break
            print("天数必须大于0！")
        except ValueError:
            print("请输入数字！")

    # 获取周期
    intervals = {'1': '1m', '5': '5m', '15': '15m', '60': '1h'}
    choice = input("K线周期 (1/5/15/60，默认5): ").strip() or '5'
    interval = intervals.get(choice, '5m')

    # 是否使用测试网
    print("\n数据源选择:")
    print("  [1] 主网 - 需要VPN（中国用户通常无法访问）")
    print("  [2] 测试网 - 推荐中国用户（数据与主网相同，不需要VPN）")
    print("-" * 70)
    testnet_choice = input("请选择 (1/2，默认2): ").strip() or '2'
    use_testnet = (testnet_choice == '2')

    # 运行优化
    try:
        if mode_choice == '1':
            # 完整优化 - 使用JSON配置文件
            print("\n[提示] 将使用 config_full_alert_trade.json 中的参数")
            print("       确保该文件存在且格式正确")
            print("\n[提示] 如遇组合数过多，请在JSON中固定更多参数")
            print("       设置: 固定参数时 start == stop")
            optimizer = Optimizer(symbols, interval, days, use_json_config=True, use_testnet=use_testnet)
        elif mode_choice == '3':
            # 自定义配置
            print("\n可用配置文件:")
            print("  - optimizer/config_quick.json (快速优化)")
            print("  - optimizer/config_full_alert_trade.json (完整配置)")

            config_path = input("\n输入配置文件路径（包含optimizer目录或相对路径）: ").strip()
            if not config_path:
                print("未输入配置文件，使用快速优化")
                optimizer = Optimizer(symbols, interval, days, use_testnet=use_testnet)
            else:
                optimizer = Optimizer(symbols, interval, days, config_file=config_path, use_testnet=use_testnet)
        else:
            # 快速优化
            optimizer = Optimizer(symbols, interval, days, use_testnet=use_testnet)

        optimizer.run()
    except Exception as e:
        print(f"\n优化失败: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='参数优化器')
    parser.add_argument('--quick', '-q', action='store_true', help='快速模式')
    parser.add_argument('--full', '-f', action='store_true', help='完整优化模式（使用JSON配置文件）')
    parser.add_argument('--offline', '-o', action='store_true',
                        help='离线模式 - 只使用缓存数据，不连接网络（推荐有缓存时使用）')
    parser.add_argument('--no-save', action='store_true',
                        help='不保存结果到文件（如果内存不足）')
    parser.add_argument('--config', '-c', type=str, help='配置文件路径')
    parser.add_argument('--symbols', '-s', nargs='+', help='币种列表')
    parser.add_argument('--interval', '-i', default='5m', help='K线周期')
    parser.add_argument('--days', '-d', type=int, default=30, help='回测天数')
    parser.add_argument('--force', action='store_true', help='跳过确认')
    parser.add_argument('--testnet', '-t', action='store_true',
                        help='使用测试网（推荐中国用户，数据与主网相同，不需要VPN）')

    args = parser.parse_args()

    if args.symbols:
        # 命令行模式
        use_testnet = args.testnet
        use_offline = args.offline

        if args.full:
            # 完整优化 - 使用JSON配置文件
            print("\n[提示] 将使用 config_full_alert_trade.json 中的参数")
            print("       修改该文件可调整参数范围")
            if use_offline:
                print("[离线模式] 只使用缓存数据，不连接网络")
            elif use_testnet:
                print("💡 使用测试网数据源（推荐中国用户）")
            optimizer = Optimizer(args.symbols, args.interval, args.days,
                                 use_json_config=True,
                                 use_testnet=use_testnet,
                                 use_offline=use_offline,
                                 no_save=args.no_save)
        elif args.config:
            # 使用配置文件
            if use_offline:
                print("[离线模式] 只使用缓存数据，不连接网络")
            elif use_testnet:
                print("💡 使用测试网数据源（推荐中国用户）")
            optimizer = Optimizer(args.symbols, args.interval, args.days,
                                 config_file=args.config,
                                 use_testnet=use_testnet,
                                 use_offline=use_offline,
                                 no_save=args.no_save)
        else:
            # 快速优化
            if use_offline:
                print("[离线模式] 只使用缓存数据，不连接网络")
            elif use_testnet:
                print("💡 使用测试网数据源（推荐中国用户）")
            optimizer = Optimizer(args.symbols, args.interval, args.days,
                                 use_testnet=use_testnet,
                                 use_offline=use_offline,
                                 no_save=args.no_save)

        if args.force:
            # 跳过确认
            import builtins
            builtins.input = lambda x: 'y'

        optimizer.run()
    else:
        # 交互式模式
        interactive_mode()


if __name__ == '__main__':
    main()

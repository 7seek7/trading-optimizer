#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测执行器
自动检测并下载数据，使用现有的 EnhancedBacktester 运行回测
"""

import os
import sys
import pickle
import tempfile
import multiprocessing
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_backtest_with_params(params, all_data, task_id=None):
    """使用指定参数运行回测（工作进程函数）"""
    # 创建临时环境变量文件
    temp_env = create_temp_env_params(params)
    start_time = time.time()

    try:
        # 显示开始信息
        if task_id is not None:
            import sys
            print(f"\r[{task_id}] 开始回测...", file=sys.stderr, end='', flush=True)
        # 重新加载环境变量
        os.environ["DOTENV_PATH"] = temp_env
        from dotenv import load_dotenv
        from config.settings import Settings

        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        load_dotenv(temp_env, override=True)
        Settings._reload_all_parameters()

        # 运行回测
        from backtest.enhanced_backtester import EnhancedBacktester

        backtester = EnhancedBacktester()
        backtester.all_data = all_data

        # 设置 interval_minutes
        interval_map = {'1m':1, '3m':3, '5m':5, '15m': 15, '30': 30, '1h': 60, '2h': 120, '4h': 240, '12h': 720, '1d': 1440}
        backtester.interval_minutes = 1

        # 初始化
        backtester.positions = {}
        backtester.closed_positions = []
        backtester.alert_cooldown = {}
        backtester.alert_count = {}

        # 自定义资金跟踪
        balance = backtester.initial_balance
        balance_history = [balance]

        # 找到所有时间点
        all_timestamps = set()
        for df in backtester.all_data.values():
            all_timestamps.update(df['timestamp'].tolist())
        sorted_timestamps = sorted(all_timestamps)

        total_timestamps = len(sorted_timestamps)
        if total_timestamps == 0:
            return {
                'total_return': 0,
                'final_balance': backtester.initial_balance,
                'total_trades': 0,
                'error': 'No data available'
            }

        # 回测主循环
        for idx, timestamp in enumerate(sorted_timestamps):
            backtester.current_date = timestamp

            for symbol, df in backtester.all_data.items():
                kline_data = df[df['timestamp'] == timestamp]
                if kline_data.empty:
                    continue

                current_row = kline_data.iloc[0]

                # 更新持仓
                if symbol in backtester.positions:
                    backtester.update_positions_with_kline(symbol, current_row, timestamp)

                    # 计算当前资金
                    current_balance = balance
                    for pos in backtester.positions.values():
                        if pos.get('profit'):
                            current_balance += pos['profit']

                    balance_history.append(current_balance)

                # 检查警报
                alert_data = backtester.check_alert_conditions_with_kline(symbol, current_row, df)
                if alert_data:
                    backtester.handle_alert(symbol, alert_data, timestamp)

        # 计算结果
        final_balance = balance_history[-1]
        total_return = (final_balance - backtester.initial_balance) / backtester.initial_balance * 100
        total_trades = len(backtester.closed_positions)

        # 显示完成信息
        elapsed = time.time() - start_time
        if task_id is not None:
            import sys
            return_pct = f"{total_return:+.2f}%" if total_return != 0 else "0.00%"
            trades_str = f"{total_trades}笔" if total_trades > 0 else "无交易"
            print(f"\r[{task_id}] 完成 | 收益: {return_pct} | {trades_str} | {elapsed:.2f}s",
                  file=sys.stderr, end='\n', flush=True)

        # 返回结果
        return {
            'total_return': total_return,
            'final_balance': final_balance,
            'total_trades': total_trades
        }

    except Exception as e:
        import traceback
        elapsed = time.time() - start_time
        if task_id is not None:
            import sys
            print(f"\r[{task_id}] 失败 | {str(e)} | {elapsed:.2f}s",
                  file=sys.stderr, end='\n', flush=True)
        return {
            'total_return': 0,
            'final_balance': 300.0,
            'total_trades': 0,
            'error': str(e)
        }
    finally:
        # 清理临时文件
        try:
            if temp_env and os.path.exists(temp_env):
                os.remove(temp_env)
        except:
            pass


def create_temp_env_params(params):
    """创建临时环境变量文件"""
    env_path = Path(__file__).parent.parent / '.env'

    if env_path.exists():
        env_content = env_path.read_text(encoding='utf-8')
    else:
        env_content = ""

    # 修改参数
    for key, value in params.items():
        pattern = f'^{key}=.*$'
        if re.search(pattern, env_content, re.MULTILINE):
            env_content = re.sub(pattern, f'{key}={value}', env_content, flags=re.MULTILINE)
        else:
            env_content += f'\n{key}={value}'

    # 写入临时文件
    temp_file = tempfile.mktemp(suffix='.env')
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(env_content)

    return temp_file


class BacktestExecutor:
    """回测执行器 - 自动检测并下载数据"""

    def __init__(self, symbols: List[str], interval: str, days: int,
                 force_download: bool = False, use_testnet: bool = False, use_offline: bool = False):
        """
        初始化回测执行器

        :param symbols: 回测币种列表
        :param interval: K线周期
        :param days: 回测天数
        :param force_download: 是否强制重新下载数据
        :param use_testnet: 是否使用测试网（适合中国大陆用户）
        :param use_offline: 是否使用离线模式（只使用缓存）
        """
        self.symbols = symbols
        self.interval = interval
        self.days = days
        self.force_download = force_download
        self.use_testnet = use_testnet
        self.use_offline = use_offline
        self._prepare_data()

    def _prepare_data(self):
        """准备回测数据 - 自动检测并下载"""
        from backtest.data_downloader import DataDownloader

        self.downloader = DataDownloader(use_testnet=self.use_testnet, offline=self.use_offline)
        self.all_data = {}

        print(f"\n{'='*70}")
        print(f"数据准备")
        print(f"{'='*70}")

        # 检查本地数据
        missing_symbols = []
        available_symbols = []

        for symbol in self.symbols:
            cache_file = self.downloader.get_cache_filename(symbol, self.interval, self.days)
            if cache_file.exists() and not self.force_download:
                available_symbols.append(symbol)
            else:
                missing_symbols.append(symbol)

        # 显示数据状态
        print(f"\n需要处理的币种: {len(self.symbols)} 个")
        print(f"  ✓ 已有本地数据: {len(available_symbols)} 个 {f'({', '.join(available_symbols)})' if available_symbols else ''}")
        print(f"  ⬇ 需要下载: {len(missing_symbols)} 个 {f'({', '.join(missing_symbols)})' if missing_symbols else ''}")

        if missing_symbols:
            print(f"\n开始下载K线数据...")
            print(f"{'='*70}")

            # 下载缺失数据
            for i, symbol in enumerate(missing_symbols):
                progress = (i + 1) / len(missing_symbols) * 100
                print(f"\r  [{i+1}/{len(missing_symbols)}] {progress:5.1f}% - {symbol} ...",
                      end='', flush=True)

                try:
                    df = self.downloader.download_symbol_data(symbol, self.interval, self.days, self.force_download)
                    if df is not None:
                        self.all_data[symbol] = df
                        print(f"\r  [{i+1}/{len(missing_symbols)}] {progress:5.1f}% - {symbol} ✓ ({len(df)} 条K线)  ")
                    else:
                        print(f"\r  [{i+1}/{len(missing_symbols)}] {progress:5.1f}% - {symbol} ✗ 下载失败  ")
                except Exception as e:
                    print(f"\r  [{i+1}/{len(missing_symbols)}] {progress:5.1f}% - {symbol} ✗ {str(e)}  ")

                time.sleep(0.3)  # 避免API限流

            print(f"\n{'='*70}")

        # 加载本地数据
        if available_symbols:
            print(f"\n加载本地数据...")
            for symbol in available_symbols:
                cache_file = self.downloader.get_cache_filename(symbol, self.interval, self.days)
                df = self.downloader.load_from_cache(cache_file)
                if df is not None:
                    self.all_data[symbol] = df
                    print(f"  ✓ {symbol}: {len(df)} 条K线")

        if not self.all_data:
            raise ValueError("没有可用的回测数据")

        total_klines = sum(len(df) for df in self.all_data.values())
        print(f"\n{'='*70}")
        print(f"数据准备完成")
        print(f"  币种: {len(self.all_data)} 个")
        print(f"  K线: {total_klines} 条")
        print(f"{'='*70}\n")

    def run_single_backtest(self, params):
        """运行单次回测"""
        return run_backtest_with_params(params.copy(), self.all_data, task_id=1)

    def run_parallel(self, param_combinations: List[Dict[str, float]],
                     max_workers: int = 0) -> List[Dict[str, Any]]:
        """并行运行多个回测"""
        if max_workers == 0:
            max_workers = multiprocessing.cpu_count()

        results = []
        total = len(param_combinations)
        completed = 0
        failed = 0

        print(f"\n{'='*70}")
        print(f"开始并行回测")
        print(f"{'='*70}")
        print(f"总组合数: {total}")
        print(f"进程数: {max_workers}")
        print(f"每个回测将显示开始和完成状态（在下方）")
        print(f"{'='*70}\n")

        start_time = time.time()
        update_interval = 1  # 每完成1个更新一次

        # 为每个任务分配ID
        args = [(params, self.all_data, i+1) for i, params in enumerate(param_combinations)]

        with multiprocessing.Pool(max_workers) as pool:
            for i, result in enumerate(pool.starmap(run_backtest_with_params, args)):
                results.append(result)
                completed += 1

                # 统计失败
                if 'error' in result:
                    failed += 1

                elapsed = time.time() - start_time
                progress = completed / total * 100
                eta = (elapsed / completed) * (total - completed) if completed > 0 else 0

                # 计算速度
                speed = completed / elapsed if elapsed > 0 else 0

                # 格式化时间
                elapsed_str = self._format_time(elapsed)
                eta_str = self._format_time(eta)

                # 显示进度（使用stdout，与stderr分开）
                import sys
                print(f"\r[{completed}/{total}] {progress:5.1f}% | "
                      f"速度: {speed:.2f}个/秒 | "
                      f"已用: {elapsed_str} | "
                      f"剩余: {eta_str} | "
                      f"成功: {completed-failed} | "
                      f"失败: {failed}", file=sys.stdout, end='', flush=True)

        print(f"\n{'='*70}")
        total_time = time.time() - start_time
        avg_speed = completed / total_time if total_time > 0 else 0
        print(f"回测完成！")
        print(f"  总耗时: {self._format_time(total_time)}")
        print(f"  平均速度: {avg_speed:.2f}个/秒")
        print(f"  成功: {completed-failed} | 失败: {failed}")
        print(f"{'='*70}\n")

        return results

    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}小时"

    def estimate_time(self, param_combinations: List[Dict[str, float]],
                      max_workers: int = 0) -> Optional[Dict[str, Any]]:
        """估算时间"""
        if max_workers == 0:
            max_workers = multiprocessing.cpu_count()

        total_klines = sum(len(df) for df in self.all_data.values())
        single_test_seconds = total_klines * 0.0002

        total_tests = len(param_combinations)
        estimated_seconds = total_tests * single_test_seconds / max_workers

        return {
            'total_combinations': total_tests,
            'max_workers': max_workers,
            'estimated_seconds': estimated_seconds,
            'estimated_minutes': estimated_seconds / 60,
            'estimated_hours': estimated_seconds / 3600,
            'total_klines': total_klines
        }

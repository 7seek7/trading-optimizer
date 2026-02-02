import time
import json
import sys
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
from backtest.backtester import Backtester
from backtest.data_downloader import DataDownloader
from config.settings import settings
from utils.logger import Logger

matplotlib.use('Agg')

logger = Logger.get_logger('enhanced_backtest')

class EnhancedBacktester(Backtester):
    """增强回测器 - 支持任意时间段和收益曲线"""
    
    def __init__(self):
        super().__init__()
        self.downloader = DataDownloader()
        self.all_data = {}  # 存储所有币种数据
        self.current_date = None  # 当前回测时间
        self.alert_history = {}  # 警报历史，用于判断开仓方向
        self.interval_minutes = 1  # K线周期（分钟），默认1分钟
    
    def get_interval_from_monitor_period(self, monitor_period_minutes):
        """
        根据监控周期（分钟）自动选择更小周期的K线数据
        目的：在监控周期内更早发现量价变化
        
        原理：
        - 如果监控周期是3分钟，应该使用1分钟K线
        - 这样一个监控周期包含3根1分钟K线
        - 可以在3分钟周期内更早地发现变化
        - 而不是等到3分钟周期结束才看到一根K线
        
        :param monitor_period_minutes: 监控周期（分钟）
        :return: K线周期字符串（如 '1m', '5m'）
        """
        # 可用的K线周期（分钟）
        available_intervals = [1, 3, 5, 15, 30, 60, 120, 240, 720, 1440]
        
        # 选择比监控周期更小的最大K线周期
        # 这样可以在监控周期内有多个数据点，更早发现变化
        smaller_intervals = [i for i in available_intervals if i < monitor_period_minutes]
        
        if smaller_intervals:
            # 选择最大的小于监控周期的K线周期
            selected_interval = max(smaller_intervals)
        else:
            # 如果没有更小的周期，使用1分钟（最小周期）
            selected_interval = 1
        
        interval_map = {
            1: '1m',
            3: '3m',
            5: '5m',
            15: '15m',
            30: '30m',
            60: '1h',
            120: '2h',
            240: '4h',
            720: '12h',
            1440: '1d'
        }
        
        selected_interval_str = interval_map[selected_interval]
        
        # 计算一个监控周期包含多少根K线
        klines_per_monitor = monitor_period_minutes / selected_interval
        
        logger.info(f"监控周期{monitor_period_minutes}分钟 → K线周期{selected_interval}分钟")
        logger.info(f"一个监控周期包含约{klines_per_monitor:.1f}根K线")
        logger.info(f"这样可以在{monitor_period_minutes}分钟监控周期内更早发现量价变化")
        
        return selected_interval_str
    
    def run_interactive_backtest(self):
        """交互式回测"""
        try:
            print("\n" + "="*70)
            print("增强回测系统 - 交互式回测")
            print("="*70)

            # 获取用户输入
            while True:
                try:
                    symbols_input = input("\n请输入要回测的币种（多个用空格分隔，如 BTCUSDT ETHUSDT）: ").strip().upper()
                    if symbols_input:
                        symbols = symbols_input.split()
                        break
                    else:
                        print("请输入至少一个币种！")
                except (EOFError, KeyboardInterrupt):
                    print("\n用户取消")
                    return

            while True:
                try:
                    days_input = input("请输入回测天数（默认180天）: ").strip()
                    if not days_input:
                        days = 180
                        break
                    try:
                        days = int(days_input)
                        if days > 0:
                            break
                        else:
                            print("天数必须大于0！")
                    except ValueError:
                        print("请输入有效的数字！")
                except (EOFError, KeyboardInterrupt):
                    print("\n用户取消")
                    return

            # 根据环境变量的监控周期自动选择K线周期
            from config.settings import settings
            default_interval = self.get_interval_from_monitor_period(settings.MONITOR_INTERVAL)

            print(f"\n根据环境变量 MONITOR_INTERVAL={settings.MONITOR_INTERVAL}，")
            print(f"自动选择K线周期: {default_interval}")

            while True:
                try:
                    interval_input = input(f"请输入K线周期（1m/5m/15m/1h/4h，默认{default_interval}，回车使用自动选择）: ").strip().lower()
                    if not interval_input:
                        interval = default_interval
                        break
                    elif interval_input in ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '12h', '1d']:
                        interval = interval_input
                        break
                    else:
                        print("无效的K线周期！请输入：1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d")
                except (EOFError, KeyboardInterrupt):
                    print("\n用户取消")
                    return

            print(f"\n回测配置:")
            print(f"  - 币种: {', '.join(symbols)}")
            print(f"  - 回测天数: {days} 天")
            print(f"  - K线周期: {interval}")
            print(f"  - 初始资金: {self.initial_balance:.2f} USDT")

            try:
                confirm = input("\n是否开始回测？(y/n): ").strip().lower()
                if confirm != 'y':
                    print("回测已取消")
                    return
            except (EOFError, KeyboardInterrupt):
                print("\n用户取消")
                return

            # 运行回测
            self.run_backtest_with_download(symbols, interval, days)

        except (EOFError, KeyboardInterrupt):
            print("\n回测已取消")
            return
    
    def run_backtest_with_download(self, symbols, interval='5m', days=180, force_download=False):
        """
        运行回测（自动下载数据）
        :param symbols: 币种列表
        :param interval: K线周期
        :param days: 回测天数
        :param force_download: 是否强制重新下载数据
        """
        try:
            print("\n" + "="*70)
            print("增强回测开始")
            print("="*70)
            
            print(f"\n[1/4] 检查并下载历史数据...")
            
            # 检查本地数据
            missing_symbols = []
            available_symbols = []
            
            for symbol in symbols:
                cache_file = self.downloader.get_cache_filename(symbol, interval, days)
                if cache_file.exists() and not force_download:
                    available_symbols.append(symbol)
                else:
                    missing_symbols.append(symbol)
            
            # 显示数据状态
            if available_symbols:
                print(f"  已找到 {len(available_symbols)} 个币种的本地数据: {', '.join(available_symbols[:3])}...")
            
            if missing_symbols:
                print(f"  需要下载 {len(missing_symbols)} 个币种的数据: {', '.join(missing_symbols[:3])}...")
                
                # 下载缺失数据
                for i, symbol in enumerate(missing_symbols):
                    print(f"  下载进度: {i+1}/{len(missing_symbols)} - {symbol}")
                    df = self.downloader.download_symbol_data(symbol, interval, days, force_download)
                    if df is not None:
                        self.all_data[symbol] = df
                        time.sleep(0.5)  # 避免API限流
            
            # 加载本地数据
            for symbol in available_symbols:
                cache_file = self.downloader.get_cache_filename(symbol, interval, days)
                df = self.downloader.load_from_cache(cache_file)
                if df is not None:
                    self.all_data[symbol] = df
            
            if not self.all_data:
                print("\n[X] 没有可用的数据！")
                return
            
            print(f"  [OK] 成功获取 {len(self.all_data)} 个币种的数据")
            
            # 显示配置
            print(f"\n[2/4] 回测配置:")
            print(f"  - 初始资金: {self.initial_balance:.2f} USDT")
            print(f"  - 单次建仓: {settings.INITIAL_POSITION}%")
            print(f"  - 杠杆倍数: {settings.LEVERAGE}x")
            print(f"  - 最大持仓: {settings.MAX_POSITIONS} 个")
            print(f"  - 价格阈值: {settings.PRICE_CHANGE_THRESHOLD}%")
            print(f"  - 成交量阈值: {settings.VOLUME_THRESHOLD}x")
            
            # 运行回测
            print(f"\n[3/4] 执行回测...")
            self.execute_backtest(interval)
            
            # 输出结果
            print(f"\n[4/4] 生成报告...")
            metrics = self.print_results()
            
            # 绘制图表
            if metrics and metrics.get('balance_history'):
                print(f"\n[图表] 正在生成图表...")
                self.plot_results(metrics)
            
            # 保存结果
            save_choice = input("\n是否保存回测结果？(y/n，默认y): ").strip().lower()
            if save_choice != 'n':
                result_files = self.save_results(f"enhanced_backtest_{int(time.time())}")
                if result_files:
                    print(f"\n[OK] 回测结果已保存:")
                    for key, filepath in result_files.items():
                        if key != 'metrics':
                            print(f"   - {key}: {filepath}")
            
            print("\n" + "="*70)
            print("增强回测完成")
            print("="*70)
            
        except KeyboardInterrupt:
            print("\n\n回测被用户中断")
            logger.info("回测被用户中断")
        except Exception as e:
            print(f"\n[X] 回测失败: {str(e)}")
            logger.error(f"回测失败: {str(e)}", exc_info=True)
    
    def check_alert_conditions_with_kline(self, symbol, current_kline, df):
        """
        使用K线检查警报条件（回测版本）
        
        与实盘逻辑保持一致：
        1. 价格涨跌幅和成交量需要同时达到阈值（AND 逻辑）
        2. 检查冷却时间
        3. 返回警报数据
        
        :param symbol: 币种
        :param current_kline: 当前K线数据（Series）
        :param df: 完整的DataFrame
        :return: 警报数据字典，或None
        """
        try:
            from config.settings import settings
            
            current_price = current_kline['close']
            current_timestamp = current_kline['timestamp']
            
            # 找到当前K线在DataFrame中的索引
            current_idx = df[df['timestamp'] == current_timestamp].index
            if len(current_idx) == 0:
                return None
            current_idx = current_idx[0]
            
            # 获取监控周期内的K线数据
            monitor_periods = int(settings.MONITOR_INTERVAL / self.interval_minutes)
            start_idx = max(0, current_idx - monitor_periods)
            historical_klines = df.iloc[start_idx:current_idx]
            
            if historical_klines.empty:
                return None
            
            # 计算价格涨跌幅（监控周期内的涨跌幅）
            first_price = historical_klines.iloc[0]['close']
            price_change = ((current_price - first_price) / first_price) * 100
            
            # 计算成交量（当前K线的成交量）
            current_volume = current_kline['quote_volume']
            
            # 计算历史平均成交量（监控周期前的数据）
            compare_periods = min(settings.VOLUME_COMPARE_PERIODS, len(historical_klines))
            if compare_periods == 0:
                compare_periods = 1
            avg_volume = historical_klines.iloc[-compare_periods:]['quote_volume'].mean()
            volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 0
            
            # 检查价格和成交量阈值（AND 逻辑：两者都必须达到阈值才触发）
            # 只有价格涨跌幅和成交量都达到阈值才触发警报
            if abs(price_change) < settings.PRICE_CHANGE_THRESHOLD or volume_ratio < settings.VOLUME_THRESHOLD:
                return None
            
            # 检查冷却时间（基于K线计数）
            if symbol not in self.alert_cooldown:
                self.alert_cooldown[symbol] = 0
            
            # 冷却期：每个监控周期只能触发一次警报
            # 使用K线索引来跟踪
            if current_idx - self.alert_cooldown[symbol] < monitor_periods:
                return None
            
            # 判断方向
            alert_direction = 'LONG' if price_change > 0 else 'SHORT'
            
            # 警报计数
            if symbol not in self.alert_count:
                self.alert_count[symbol] = 0
            self.alert_count[symbol] += 1
            
            # 更新冷却时间（当前K线索引）
            self.alert_cooldown[symbol] = current_idx
            
            alert_data = {
                'symbol': symbol,
                'current_price': current_price,
                'price_change': price_change,
                'volume_usdt': current_volume / 1000,  # 转换为K USDT
                'volume_ratio': volume_ratio,
                'direction': alert_direction,
                'alert_count': self.alert_count[symbol],
                'timestamp': current_timestamp
            }
            
            logger.info(f"[回测警报] {symbol} | 价格: {current_price:.4f} | 涨跌: {price_change:+.2f}% | 成交量: {volume_ratio:.2f}x | 方向: {alert_direction}")
            
            return alert_data
            
        except Exception as e:
            logger.error(f"检查警报条件失败 {symbol}: {str(e)}")
            return None
    
    def update_positions_with_kline(self, symbol, kline, timestamp):
        """
        使用K线数据更新持仓状态

        :param symbol: 币种
        :param kline: K线数据（Series）
        :param timestamp: 时间戳
        """
        try:
            if symbol not in self.positions:
                return

            position = self.positions[symbol]
            direction = position['direction']
            average_price = position['average_price']
            total_quantity = position['total_quantity']
            total_investment = position['total_investment']

            # 关键修复：如果是新时间戳，重置 is_closing 标志
            # 这样允许在新的K线周期中再次平仓
            last_action_time = position.get('last_action_time', 0)
            if last_action_time != timestamp:
                position['is_closing'] = False

            # 检查K线内是否触发了加仓/止盈/止损
            # 由于1分钟K线可能包含显著的价格变化，需要检查高低价
            high_price = kline['high']
            low_price = kline['low']
            close_price = kline['close']

            # 计算高低价对应的盈亏率
            if direction == 'LONG':
                high_profit_pct = ((high_price - average_price) / average_price) * 100
                low_profit_pct = ((low_price - average_price) / average_price) * 100
            else:  # SHORT
                high_profit_pct = ((average_price - low_price) / average_price) * 100
                low_profit_pct = ((average_price - high_price) / average_price) * 100

            # 使用收盘价更新持仓（确保最后状态是正确的）
            current_price = close_price
            if direction == 'LONG':
                profit = (current_price - average_price) * total_quantity
            else:
                profit = (average_price - current_price) * total_quantity

            profit_pct = (profit / total_investment) * 100

            position['profit'] = profit
            position['profit_pct'] = profit_pct
            position['current_price'] = current_price

            # 更新最高盈利（只使用收盘价，避免K线内波动导致错误触发）
            if profit_pct > position.get('max_profit_pct', 0):
                position['max_profit_pct'] = profit_pct

            # 检查加仓条件（使用收盘价）
            self.handle_position_building(symbol, current_price, profit_pct)

            # 检查止盈止损（使用收盘价）
            self.check_exit_conditions(position, timestamp)

        except Exception as e:
            logger.error(f"更新持仓失败 {symbol}: {str(e)}")
    
    def execute_backtest(self, interval):
        """
        执行回测
        
        核心逻辑：
        1. 使用小周期K线数据（如1分钟），实时检查警报
        2. 每根K线都检查警报条件，避免滞后
        3. 警报条件中的数据基于监控周期计算
           - 价格涨跌幅：监控周期内的涨跌幅（如3分钟内）
           - 成交量：监控周期内累计成交量
           - 对比：与历史监控周期的平均值对比
        4. 持仓状态每根K线都更新
        5. 所有参数统一来自环境变量（settings）
        """
        try:
            from config.settings import settings
            
            total_symbols = len(self.all_data)
            total_klines = sum(len(df) for df in self.all_data.values())
            
            print(f"  总共 {total_symbols} 个币种，约 {total_klines} 根K线")
            print(f"  K线周期: {interval}")
            print(f"  监控周期: {settings.MONITOR_INTERVAL}分钟")
            
            # 计算K线周期（分钟）
            interval_minutes_map = {
                '1m':1, '3m':3, '5m':5, '15m': 15, '30m': 30,
                '1h': 60, '2h': 120, '4h': 240, '12h': 720, '1d': 1440
            }
            interval_minutes = interval_minutes_map.get(interval, 1)
            self.interval_minutes = interval_minutes  # 保存为实例变量
            
            # 计算每个监控周期包含多少根K线
            klines_per_monitor = settings.MONITOR_INTERVAL / interval_minutes
            print(f"  每监控周期包含: {klines_per_monitor:.1f}根K线")
            print(f"  实时检查: 每根{interval}K线都检查警报")
            
            # 找到所有币种的时间范围
            all_timestamps = set()
            for df in self.all_data.values():
                all_timestamps.update(df['timestamp'].tolist())
            
            # 按时间排序
            sorted_timestamps = sorted(all_timestamps)
            
            print(f"  回测时间范围: {len(sorted_timestamps)} 个时间点")
            print(f"  警报检查: 每根K线检查（共{total_klines}次）")
            
            # 按时间顺序处理
            for i, timestamp in enumerate(sorted_timestamps):
                self.current_date = timestamp
                current_symbol = None
                
                # 打印进度
                if i % 1000 == 0:
                    dt_str = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M')
                    print(f"  进度: {i+1}/{len(sorted_timestamps)} - {dt_str}")
                
                # 检查每个币种
                for symbol, df in self.all_data.items():
                    current_symbol = symbol
                    # 找到对应时间点的K线
                    kline_data = df[df['timestamp'] == timestamp]
                    if kline_data.empty:
                        continue
                    
                    current_row = kline_data.iloc[0]
                    
                    # 1. 更新持仓状态（每根K线都更新）
                    if symbol in self.positions:
                        self.update_positions_with_kline(symbol, current_row, timestamp)
                    
                    # 2. 检查警报条件并处理（每根K线都检查）
                    alert_data = self.check_alert_conditions_with_kline(symbol, current_row, df)
                    if alert_data:
                        self.handle_alert(symbol, alert_data, timestamp)
            
        except Exception as e:
            logger.error(f"使用K线更新持仓失败 {current_symbol or 'unknown'}: {str(e)}")
    
    def handle_position_building(self, symbol, current_price, profit_rate):
        """处理建仓过程（与实盘逻辑完全一致）"""
        try:
            from config.settings import settings

            position = self.positions[symbol]
            if not position:
                return

            entry_price = position['entry_price']
            direction = position['direction']
            leverage = position['leverage']

            # 检查待执行的加仓计划
            pending_orders = position.get('pending_orders', [])
            added_levels = position.get('added_levels', [])

            for idx, plan in enumerate(pending_orders):
                trigger_rate = plan['trigger_rate']
                add_percent = plan['percent']

                # 检查是否已经执行过该级别的加仓
                if idx in added_levels:
                    continue

                triggered = False
                if trigger_rate < 0:  # 亏损加仓
                    if profit_rate <= trigger_rate:
                        triggered = True
                else:  # 盈利加仓
                    if profit_rate >= trigger_rate:
                        triggered = True

                if triggered:
                    # 获取当前时间戳用于记录
                    current_timestamp = self.current_date if hasattr(self, 'current_date') else 0
                    # 执行加仓（回测中立即成交）
                    self.add_position(
                        position,
                        add_percent,
                        current_timestamp,
                        f"加仓{idx+1}"
                    )
                    # 标记该级别已执行
                    added_levels.append(idx)

        except Exception as e:
            logger.error(f"处理建仓失败 {symbol}: {str(e)}")
    
    def main():
        import sys
        from backtest.enhanced_backtester import EnhancedBacktester
        
        backtester = EnhancedBacktester()
        backtester.run_interactive_backtest()

if __name__ == '__main__':
    main()
import json
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path
from alert.binance_client import BinanceClient
from config.settings import settings
from utils.logger import Logger

matplotlib.use('Agg')

logger = Logger.get_logger('backtest')

class Backtester:
    """回测引擎基类"""
    
    def __init__(self):
        self.client = BinanceClient('live')
        self.positions = {}
        self.closed_positions = []
        # 修复初始资金计算：使用固定值300 USDT作为回测初始资金
        self.balance = 300.0  # 初始资金 (USDT)
        self.initial_balance = self.balance
        self.trade_history = []
        self.alert_count = {}
        self.alert_cooldown = {}
        
        # 创建结果目录
        self.results_dir = Path('data/backtest_results')
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def run_backtest(self, symbols):
        """运行标准回测"""
        raise NotImplementedError("子类必须实现此方法")
    
    def handle_alert(self, symbol, alert_data, timestamp):
        """处理警报信号 - 模拟交易"""
        try:
            # 检查是否达到最大持仓数
            active_positions = sum(1 for p in self.positions.values() 
                                 if p.get('status') == 'active')
            
            if active_positions >= settings.MAX_POSITIONS:
                logger.debug(f"已达到最大持仓数 {settings.MAX_POSITIONS}，跳过 {symbol}")
                return False
            
            # 检查是否已有该币种的仓位
            if symbol in self.positions:
                logger.debug(f"{symbol} 已有仓位，跳过")
                return False
            
            # 计算开仓金额
            position_size = self.balance * (settings.INITIAL_POSITION / 100)
            if position_size > self.balance:
                position_size = self.balance * 0.95
            
            # 开仓价格
            entry_price = alert_data['current_price']

            # 计算开仓数量（包含杠杆）
            # quantity = (position_size * leverage) / entry_price
            quantity = (position_size * settings.LEVERAGE) / entry_price

            # 创建仓位
            position = {
                'symbol': symbol,
                'entry_price': entry_price,
                'current_price': entry_price,
                'quantity': quantity,
                'entry_time': timestamp,
                'entry_size': position_size,
                'status': 'active',
                'direction': alert_data['direction'],
                'stop_loss': None,
                'take_profit': None,
                'average_price': entry_price,
                'total_quantity': quantity,
                'total_investment': position_size,
                'profit': 0.0,
                'profit_pct': 0.0,
                'max_profit_pct': 0.0,  # 初始化为0，避免None错误
                'leverage': settings.LEVERAGE,
                'add_count': 0,
                'add_positions': [],
                # 跟踪已执行的级别
                'added_levels': [],      # 已执行的加仓级别（索引）
                'take_profit_levels': {},  # 已执行的止盈级别
                'stop_loss_levels': {},   # 已执行的止损级别
                'last_action_time': 0,   # 最后操作时间
                'is_closing': False     # 是否正在平仓
            }

            # 更新资金
            self.balance -= position_size
            self.positions[symbol] = position

            # 计算实际交易金额（数量 * 价格）
            actual_amount = quantity * entry_price

            # 记录交易
            trade_record = {
                'timestamp': timestamp,
                'time': datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': symbol,
                'action': 'OPEN',
                'price': entry_price,
                'quantity': quantity,
                'amount': position_size,  # 记录保证金金额
                'actual_amount': actual_amount,  # 记录实际交易金额
                'balance': self.balance,
                'profit': 0.0,
                'profit_pct': 0.0,
                'reason': '警报触发'
            }
            self.trade_history.append(trade_record)
            
            logger.info(f"[模拟开仓] {symbol} | 价格: {entry_price:.4f} | "
                       f"数量: {quantity:.4f} | 保证金: {position_size:.2f} USDT | "
                       f"实际金额: {actual_amount:.2f} USDT | 方向: {alert_data['direction']}")
            
            return True
            
        except Exception as e:
            logger.error(f"处理警报失败: {str(e)}")
            return False
    
    def update_positions(self, symbol, current_price, timestamp):
        """更新持仓状态"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # 更新当前价格
        position['current_price'] = current_price
        
        # 计算盈亏
        if position['direction'] == 'LONG':
            profit = (current_price - position['average_price']) * position['total_quantity']
        else:
            profit = (position['average_price'] - current_price) * position['total_quantity']
        
        profit_pct = (profit / position['total_investment']) * 100
        
        position['profit'] = profit
        position['profit_pct'] = profit_pct
        
        # 更新最高盈利
        if profit_pct > position['max_profit_pct']:
            position['max_profit_pct'] = profit_pct
        
        # 检查加仓条件（使用级别检查，每个级别只执行一次）
        added_levels = position.get('added_levels', [])

        # 计算当前已加仓总金额
        current_add_investment = sum(pos.get('investment', 0) for pos in position.get('add_positions', []))

        # 检查单币种最大投资金额限制
        total_investment = position.get('total_investment', 0)
        if total_investment >= settings.SINGLE_SYMBOL_MAX_INVESTMENT:
            logger.debug(f"{symbol} 已达到单币种最大投资金额 {settings.SINGLE_SYMBOL_MAX_INVESTMENT} USDT，停止加仓")
            # 不再检查加仓条件

        # 加仓逻辑：只检查未执行的级别，使用if而不是elif，允许每个级别独立检查
        # 关键修复：添加日志，调试加仓为什么没有触发
        if 'LOSS1' not in added_levels:
            logger.debug(f"{symbol} LOSS1未执行，当前收益率: {profit_pct:.2f}%, 阈值: {settings.LOSS_STEP1:.2f}%")
            if profit_pct <= settings.LOSS_STEP1:
                self.add_position(position, settings.LOSS_ADD1, timestamp, "亏损加仓1")

        if 'LOSS2' not in added_levels:
            logger.debug(f"{symbol} LOSS2未执行，当前收益率: {profit_pct:.2f}%, 阈值: {settings.LOSS_STEP2:.2f}%")
            if profit_pct <= settings.LOSS_STEP2:
                self.add_position(position, settings.LOSS_ADD2, timestamp, "亏损加仓2")

        if 'LOSS3' not in added_levels:
            logger.debug(f"{symbol} LOSS3未执行，当前收益率: {profit_pct:.2f}%, 阈值: {settings.LOSS_STEP3:.2f}%")
            if profit_pct <= settings.LOSS_STEP3:
                self.add_position(position, settings.LOSS_ADD3, timestamp, "亏损加仓3")

        if 'PROFIT1' not in added_levels:
            logger.debug(f"{symbol} PROFIT1未执行，当前收益率: {profit_pct:.2f}%, 阈值: {settings.PROFIT_STEP1:.2f}%")
            if profit_pct >= settings.PROFIT_STEP1:
                self.add_position(position, settings.PROFIT_ADD1, timestamp, "盈利加仓1")

        if 'PROFIT2' not in added_levels:
            logger.debug(f"{symbol} PROFIT2未执行，当前收益率: {profit_pct:.2f}%, 阈值: {settings.PROFIT_STEP2:.2f}%")
            if profit_pct >= settings.PROFIT_STEP2:
                self.add_position(position, settings.PROFIT_ADD2, timestamp, "盈利加仓2")

        if 'PROFIT3' not in added_levels:
            logger.debug(f"{symbol} PROFIT3未执行，当前收益率: {profit_pct:.2f}%, 阈值: {settings.PROFIT_STEP3:.2f}%")
            if profit_pct >= settings.PROFIT_STEP3:
                self.add_position(position, settings.PROFIT_ADD3, timestamp, "盈利加仓3")

        # 检查止盈止损条件
        self.check_exit_conditions(position, timestamp)
    
    def add_position(self, position, add_pct, timestamp, reason):
        """加仓"""
        try:
            # 根据原因判断是哪个加仓级别
            if "亏损加仓1" in reason:
                level = 0
            elif "亏损加仓2" in reason:
                level = 1
            elif "亏损加仓3" in reason:
                level = 2
            elif "盈利加仓1" in reason:
                level = 3
            elif "盈利加仓2" in reason:
                level = 4
            elif "盈利加仓3" in reason:
                level = 5
            else:
                level = -1
            
            # 检查该加仓级别是否已执行
            if level >= 0 and level in position.get('added_levels', []):
                logger.debug(f"{position['symbol']} 加仓级别{level}已执行，跳过")
                return False
            
            # 保存原值用于计算
            old_total_investment = position['total_investment']
            old_total_quantity = position['total_quantity']
            old_average_price = position['average_price']
            old_entry_price = position['entry_price']
            
            # 计算加仓金额（关键修复：使用当前余额计算，而不是初始开仓金额）
            # 加仓金额 = 当前余额 * 加仓比例
            add_usdt = self.balance * (add_pct / 100)

            # 检查是否有足够的余额进行加仓
            if add_usdt > self.balance:
                logger.warning(f"{position['symbol']} 余额不足，跳过加仓。需要: {add_usdt:.2f} USDT, 余额: {self.balance:.2f} USDT")
                return False

            # 简化：使用当前价格计算加仓数量（避免依赖限价单逻辑）
            current_price = position['current_price']
            leverage = position.get('leverage', settings.LEVERAGE)
            add_quantity = (add_usdt * leverage) / current_price

            # 更新资金（关键修复：从balance中扣除加仓金额）
            self.balance -= add_usdt

            # 新的总投资和数量
            new_total_investment = old_total_investment + add_usdt
            new_total_quantity = old_total_quantity + add_quantity
            
            # 计算新均价
            if new_total_quantity > 0:
                new_average_price = new_total_investment / (new_total_quantity / leverage)
            else:
                new_average_price = old_average_price
            
            # 更新仓位
            position['total_investment'] = new_total_investment
            position['total_quantity'] = new_total_quantity
            position['average_price'] = new_average_price
            position['add_count'] += 1
            position['add_positions'].append({
                'timestamp': timestamp,
                'price': current_price,
                'quantity': add_quantity,
                'investment': add_usdt,
                'reason': reason
            })
            
            # 标记该加仓级别已执行
            if level >= 0:
                position['added_levels'].append(level)

            # 计算实际交易金额（数量 * 价格）
            actual_amount = add_quantity * current_price

            # 记录交易
            trade_record = {
                'timestamp': timestamp,
                'time': datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': position['symbol'],
                'action': 'ADD',
                'price': current_price,
                'quantity': add_quantity,
                'amount': add_usdt,  # 记录保证金金额
                'actual_amount': actual_amount,  # 记录实际交易金额
                'direction': position['direction'],
                'balance': self.balance,
                'profit': 0.0,
                'profit_pct': 0.0,
                'reason': reason
            }
            self.trade_history.append(trade_record)

            logger.info(f"[模拟加仓] {position['symbol']} | 价格: {current_price:.4f} | "
                       f"数量: {add_quantity:.4f} | 保证金: {add_usdt:.2f} USDT | "
                       f"实际金额: {actual_amount:.2f} USDT | 原因: {reason}")
            
            return True

        except Exception as e:
            logger.error(f"加仓失败: {str(e)}")
            return False
    
    def check_exit_conditions(self, position, timestamp):
        """检查退出条件（每个级别只执行一次）"""
        profit_pct = position['profit_pct']
        max_profit_pct = position['max_profit_pct']
        symbol = position['symbol']

        # 获取已执行的级别
        take_profit_levels = position.get('take_profit_levels', {})
        stop_loss_levels = position.get('stop_loss_levels', {})

        # 计算利润回撤 = 最高回报率 - 现在回报率
        profit_drawback = max_profit_pct - profit_pct

        # 止盈策略（按需求文档第六部分）
        # 执行顺序：高盈利止盈 → 低盈利止盈 → HC%保本止盈 → 止损

        # 1. 高盈利止盈（需要先达到GY%才能触发）
        # 需求：若回报率高于GY%后，利润回撤GH1%，止盈GY1%仓位，若利润回撤GH2%，止盈仓位的GY2%
        if max_profit_pct >= settings.HIGH_PROFIT_THRESHOLD:
            if 'HIGH2' not in take_profit_levels and profit_drawback >= settings.HIGH_PROFIT_DRAWBACK2:
                self.close_position(position, settings.HIGH_PROFIT_CLOSE2, timestamp, "高盈利回调止盈2")
                take_profit_levels['HIGH2'] = True
                return
            elif 'HIGH1' not in take_profit_levels and profit_drawback >= settings.HIGH_PROFIT_DRAWBACK1:
                self.close_position(position, settings.HIGH_PROFIT_CLOSE1, timestamp, "高盈利回调止盈1")
                take_profit_levels['HIGH1'] = True
                return

        # 2. 低盈利止盈（关键修复：必须先产生过利润）
        # 需求：若回报率低于DY%且曾经有过利润，利润回撤DH1%，止盈DY1%仓位
        # 修复：max_profit_pct > 0 确保曾经盈利过，避免亏损时触发
        elif 0 < max_profit_pct <= settings.LOW_PROFIT_THRESHOLD:
            if 'LOW' not in take_profit_levels and profit_drawback >= settings.LOW_PROFIT_DRAWBACK1:
                self.close_position(position, settings.LOW_PROFIT_CLOSE1, timestamp, "低盈利回调止盈")
                take_profit_levels['LOW'] = True
                return

        # 3. HC%保本止盈（最后的保本止盈策略）
        # 需求：产生利润回撤后，剩余仓位在利润率减到HC%时全部平仓
        # 实现：只有产生过利润（max_profit_pct > 0）且发生利润回撤后
        #       且利润率 <= HC% (0.5%) 时，全部平仓
        # 关键修复：max_profit_pct > 0 确保从未盈利时不触发
        if 'HC' not in take_profit_levels:
            # 只在产生过利润后（max_profit_pct > 0）且发生利润回撤（profit_drawback > 0）才检查HC%
            if max_profit_pct > 0 and profit_drawback > 0:
                if profit_pct <= settings.BREAKEVEN_THRESHOLD:
                    self.close_position(position, 100, timestamp, "HC%保本止盈")
                    take_profit_levels['HC'] = True
                    return

        # 止损策略（按需求文档第七部分）

        # 1. 强制止损1（首次低于-HK1%时触发限价止损挂单，挂单位置为建仓均价的ZS1%）
        if 'FORCED1' not in stop_loss_levels:
            if profit_pct <= settings.STOPLOSS_TRIGGER1:
                self.close_position(position, 100, timestamp, "强制止损1")
                stop_loss_levels['FORCED1'] = True
                return

        # 2. 第二级止损（价格进一步下跌至建仓均价的HK2%，止盈剩余仓位的ZS2%）
        if 'LEVEL2' not in stop_loss_levels:
            if profit_pct <= settings.STOPLOSS_TRIGGER2:
                self.close_position(position, settings.STOPLOSS_CLOSE2, timestamp, "强制止损2")
                stop_loss_levels['LEVEL2'] = True
                return


    def close_position(self, position, close_pct, timestamp, reason):
        """平仓（重写基类方法，确保参数完全匹配）"""
        symbol = position.get('symbol', 'UNKNOWN')
        try:

            # 检查是否在当前timestamp已经执行过操作（关键修复）
            last_action_time = position.get('last_action_time', 0)
            if last_action_time == timestamp:
                logger.debug(f"{symbol} 同一时间戳已执行过操作，跳过")
                return False

            # 检查是否正在执行平仓（避免并发调用）
            if position.get('is_closing', False):
                logger.debug(f"{symbol} 正在执行平仓，跳过")
                return False

            # 检查是否已经完成平仓（避免对已平仓的仓位操作）
            if position.get('total_quantity', 0) <= 0 or position.get('total_investment', 0) <= 0:
                logger.debug(f"{symbol} 仓位已清空，跳过")
                return False

            # 标记正在平仓，避免重复平仓
            position['is_closing'] = True
            # 记录最后一次操作时间
            position['last_action_time'] = timestamp

            # 计算平仓数量
            close_quantity = position['total_quantity'] * (close_pct / 100)
            if close_pct >= 100:
                close_quantity = position['total_quantity']

            current_price = position['current_price']
            direction = position['direction']
            total_quantity = position['total_quantity']
            total_investment = position.get('total_investment', 0)

            # 计算平仓金额
            if direction == 'LONG':
                close_amount = close_quantity * current_price
            else:
                close_amount = close_quantity * (2 * position['average_price'] - current_price)

            # 计算本次平仓的盈亏
            if direction == 'LONG':
                close_profit = (current_price - position['average_price']) * close_quantity
            else:
                close_profit = (position['average_price'] - current_price) * close_quantity

            # 计算本次平仓对应的持仓成本（使用平仓前的总投资）
            investment_for_close = position['total_investment'] * (close_pct / 100)

            # 限制最大亏损不超过-100%（逐仓保证金模式）
            if investment_for_close > 0:
                close_profit_pct = (close_profit / investment_for_close) * 100
                # 限制亏损不超过-100%
                if close_profit_pct < -100:
                    close_profit_pct = -100
                    close_profit = -investment_for_close
            else:
                close_profit_pct = 0

            # 更新仓位
            position['total_quantity'] -= close_quantity

            # 更新投资金额（先保存原值，再更新）
            original_total_investment = position['total_investment']
            if close_pct < 100:
                position['total_investment'] *= (1 - close_pct / 100)
                # 更新开仓均价
                if position['total_quantity'] > 0:
                    position['average_price'] = position['total_investment'] / (position['total_quantity'] / position.get('leverage', 1))

            # 更新资金（关键修复：只返回保证金，而不是总交易金额）
            # close_amount 是总交易金额（数量 * 价格），需要除以杠杆得到保证金
            close_margin = close_amount / position.get('leverage', 1)
            self.balance += close_margin

            # 记录交易
            trade_record = {
                'timestamp': timestamp,
                'time': datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': symbol,
                'action': 'CLOSE',
                'price': current_price,
                'quantity': close_quantity,
                'amount': close_margin,  # 记录保证金金额
                'actual_amount': close_amount,  # 记录实际交易金额
                'direction': direction,
                'balance': self.balance,
                'profit': close_profit,
                'profit_pct': close_profit_pct,
                'reason': reason
            }
            self.trade_history.append(trade_record)

            # 如果是全部平仓，移除仓位
            if close_pct >= 100:
                logger.info(f"{symbol} 平仓完成: {reason} | "
                           f"保证金: {close_margin:.2f} USDT | "
                           f"实际金额: {close_amount:.2f} USDT | "
                           f"收益: {close_profit:+.2f} USDT ({close_profit_pct:+.2f}%)")
                if symbol in self.positions:
                    del self.positions[symbol]
            else:
                # 部分平仓，更新仓位（关键修复：重置加仓级别，允许重新加仓）
                logger.info(f"{symbol} 部分平仓: {close_pct:.0f}% | "
                           f"保证金: {close_margin:.2f} USDT | "
                           f"实际金额: {close_amount:.2f} USDT | "
                           f"收益: {close_profit:+.2f} USDT ({close_profit_pct:+.2f}%)")
                # 重置加仓级别，允许重新加仓
                position['added_levels'] = []
                position['add_count'] = 0

            return True

        except Exception as e:
            logger.error(f"平仓失败: {str(e)}")
            return False
    
    def close_all_positions(self):
        """平仓所有持仓"""
        for symbol in list(self.positions.keys()):
            if symbol in self.positions:
                self.close_position(self.positions[symbol], 100, 
                                   int(datetime.now().timestamp() * 1000), "回测结束平仓")
    
    def calculate_metrics(self):
        """计算回测指标"""
        try:
            if not self.trade_history:
                return {}
            
            # 准备数据
            trades_df = pd.DataFrame(self.trade_history)
            
            # 按时间排序
            trades_df['datetime'] = pd.to_datetime(trades_df['time'])
            trades_df = trades_df.sort_values('datetime')
            
            # 计算累计收益
            trades_df['cumulative_profit'] = trades_df['profit'].cumsum()
            
            # 计算资金曲线
            initial_balance = self.initial_balance
            balance_history = []
            current_balance = initial_balance
            
            for _, row in trades_df.iterrows():
                if row['action'] == 'OPEN' or row['action'] == 'ADD':
                    current_balance -= row['amount']
                elif row['action'] == 'CLOSE':
                    current_balance += row['amount']
                balance_history.append({
                    'time': row['datetime'],
                    'balance': current_balance
                })
            
            balance_df = pd.DataFrame(balance_history)
            
            # 计算指标
            total_profit = trades_df['profit'].sum()
            total_return_pct = (total_profit / initial_balance) * 100
            
            # 年化收益率（假设回测期为1年）
            days = (trades_df['datetime'].max() - trades_df['datetime'].min()).days
            if days == 0:
                days = 1
            annual_return = (1 + total_return_pct/100) ** (365/days) - 1
            
            # 最大回撤
            if not balance_df.empty:
                balance_df['peak'] = balance_df['balance'].cummax()
                balance_df['drawdown'] = (balance_df['balance'] - balance_df['peak']) / balance_df['peak'] * 100
                max_drawdown = balance_df['drawdown'].min()
                max_drawdown_pct = abs(max_drawdown) if max_drawdown < 0 else 0
            else:
                max_drawdown_pct = 0
            
            # 胜率
            winning_trades = trades_df[(trades_df['action'] == 'CLOSE') & (trades_df['profit'] > 0)]
            total_trades = trades_df[trades_df['action'] == 'CLOSE']
            win_rate = len(winning_trades) / len(total_trades) * 100 if len(total_trades) > 0 else 0
            
            # 盈亏比
            if len(winning_trades) > 0 and len(total_trades) > len(winning_trades):
                avg_win = winning_trades['profit'].mean()
                losing_trades = trades_df[(trades_df['action'] == 'CLOSE') & (trades_df['profit'] <= 0)]
                avg_loss = abs(losing_trades['profit'].mean()) if len(losing_trades) > 0 else 0
                profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
            else:
                profit_loss_ratio = 0
            
            metrics = {
                'initial_balance': initial_balance,
                'final_balance': current_balance,
                'total_profit': total_profit,
                'total_return_pct': total_return_pct,
                'annual_return_pct': annual_return * 100,
                'max_drawdown_pct': max_drawdown_pct,
                'win_rate_pct': win_rate,
                'profit_loss_ratio': profit_loss_ratio,
                'total_trades': len(total_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(total_trades) - len(winning_trades),
                'average_profit_per_trade': total_profit / len(total_trades) if len(total_trades) > 0 else 0,
                'balance_history': balance_history,
                'trade_history': self.trade_history,
                'closed_positions': self.closed_positions
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"计算指标失败: {str(e)}")
            return {}
    
    def save_results(self, filename_prefix="backtest"):
        """保存回测结果"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 1. 保存交易历史
            trades_file = self.results_dir / f"{filename_prefix}_trades_{timestamp}.csv"
            trades_df = pd.DataFrame(self.trade_history)
            if not trades_df.empty:
                trades_df.to_csv(trades_file, index=False)
                logger.info(f"交易历史已保存到: {trades_file}")
            
            # 2. 保存平仓仓位
            positions_file = self.results_dir / f"{filename_prefix}_positions_{timestamp}.json"
            with open(positions_file, 'w', encoding='utf-8') as f:
                json.dump(self.closed_positions, f, ensure_ascii=False, indent=2)
                logger.info(f"平仓仓位已保存到: {positions_file}")
            
            # 3. 保存回测指标
            metrics = self.calculate_metrics()
            metrics_file = self.results_dir / f"{filename_prefix}_metrics_{timestamp}.json"
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
                logger.info(f"回测指标已保存到: {metrics_file}")
            
            return {
                'trades_file': str(trades_file),
                'positions_file': str(positions_file),
                'metrics_file': str(metrics_file),
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"保存结果失败: {str(e)}")
            return {}
    
    def print_results(self):
        """打印回测结果"""
        # 先平仓所有未平仓的持仓
        self.close_all_positions()
        
        # 计算指标
        metrics = self.calculate_metrics()
        
        if not metrics:
            print("\n没有找到有效的交易记录")
            return
        
        print("\n" + "="*80)
        print("回测结果报告")
        print("="*80)
        
        print(f"\n[资金表现]:")
        print(f"  初始资金: {metrics['initial_balance']:.2f} USDT")
        print(f"  最终资金: {metrics['final_balance']:.2f} USDT")
        print(f"  总收益: {metrics['total_profit']:.2f} USDT")
        print(f"  总收益率: {metrics['total_return_pct']:.2f}%")
        print(f"  年化收益率: {metrics['annual_return_pct']:.2f}%")
        print(f"  最大回撤: {metrics['max_drawdown_pct']:.2f}%")
        
        print(f"\n[交易统计]:")
        print(f"  总交易次数: {metrics['total_trades']} 次")
        print(f"  盈利交易: {metrics['winning_trades']} 次")
        print(f"  亏损交易: {metrics['losing_trades']} 次")
        print(f"  胜率: {metrics['win_rate_pct']:.2f}%")
        print(f"  盈亏比: {metrics['profit_loss_ratio']:.2f}")
        print(f"  平均每笔收益: {metrics['average_profit_per_trade']:.2f} USDT")
        
        # 显示盈亏分布
        if self.closed_positions:
            print(f"\n[仓位统计]:")
            total_closed = len(self.closed_positions)
            winning_positions = [p for p in self.closed_positions if p.get('total_profit', 0) > 0]
            losing_positions = [p for p in self.closed_positions if p.get('total_profit', 0) <= 0]
            
            print(f"  总平仓仓位: {total_closed} 个")
            print(f"  盈利仓位: {len(winning_positions)} 个")
            print(f"  亏损仓位: {len(losing_positions)} 个")
            
            if winning_positions:
                avg_win = sum(p['total_profit'] for p in winning_positions) / len(winning_positions)
                max_win = max(p['total_profit'] for p in winning_positions)
                print(f"  平均盈利: {avg_win:.2f} USDT")
                print(f"  最大盈利: {max_win:.2f} USDT")
            
            if losing_positions:
                avg_loss = sum(p['total_profit'] for p in losing_positions) / len(losing_positions)
                max_loss = min(p['total_profit'] for p in losing_positions)
                print(f"  平均亏损: {avg_loss:.2f} USDT")
                print(f"  最大亏损: {max_loss:.2f} USDT")
        
        print("\n" + "="*80)

        return metrics

    def plot_results(self, metrics):
        """
        生成回测图表（盈利曲线）

        Args:
            metrics: 回测指标，包含 balance_history
        """
        try:
            if not metrics or not metrics.get('balance_history'):
                logger.warning("没有有效的资金历史数据，跳过图表生成")
                return

            # 准备数据
            balance_history = metrics['balance_history']
            balance_df = pd.DataFrame(balance_history)

            if balance_df.empty:
                logger.warning("资金历史数据为空，跳过图表生成")
                return

            # 设置中文显示
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
            fig.suptitle('回测结果分析', fontsize=16, fontweight='bold')

            # 1. 资金曲线
            ax1.plot(balance_df['time'], balance_df['balance'],
                    linewidth=2, color='#2E86C1', label='资金曲线')

            # 标记初始资金
            ax1.axhline(y=metrics['initial_balance'], color='green',
                       linestyle='--', alpha=0.5, label=f'初始资金: {metrics["initial_balance"]:.2f} USDT')

            # 标记最终资金
            ax1.axhline(y=metrics['final_balance'], color='red',
                       linestyle='--', alpha=0.5, label=f'最终资金: {metrics["final_balance"]:.2f} USDT')

            ax1.set_title('资金曲线', fontsize=14, fontweight='bold')
            ax1.set_xlabel('时间', fontsize=12)
            ax1.set_ylabel('资金 (USDT)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='upper left', fontsize=10)
            ax1.tick_params(axis='x', rotation=45)

            # 添加统计信息
            stats_text = f"""
            总收益: {metrics['total_profit']:.2f} USDT ({metrics['total_return_pct']:.2f}%)
            年化收益: {metrics['annual_return_pct']:.2f}%
            最大回撤: {metrics['max_drawdown_pct']:.2f}%
            """
            ax1.text(0.02, 0.02, stats_text, transform=ax1.transAxes,
                    fontsize=10, verticalalignment='bottom',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

            # 2. 收益率曲线
            balance_df['return_pct'] = ((balance_df['balance'] - metrics['initial_balance']) /
                                       metrics['initial_balance']) * 100

            # 标记盈亏区间
            ax2.axhline(y=0, color='black', linewidth=1, linestyle='-')
            ax2.fill_between(balance_df['time'], balance_df['return_pct'], 0,
                            where=(balance_df['return_pct'] >= 0),
                            facecolor='green', alpha=0.3, label='盈利区间')
            ax2.fill_between(balance_df['time'], balance_df['return_pct'], 0,
                            where=(balance_df['return_pct'] < 0),
                            facecolor='red', alpha=0.3, label='亏损区间')

            ax2.plot(balance_df['time'], balance_df['return_pct'],
                    linewidth=2, color='#2E86C1', label='收益率')

            ax2.set_title('收益率曲线 (%)', fontsize=14, fontweight='bold')
            ax2.set_xlabel('时间', fontsize=12)
            ax2.set_ylabel('收益率 (%)', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='upper left', fontsize=10)
            ax2.tick_params(axis='x', rotation=45)

            # 调整布局
            plt.tight_layout()

            # 保存图表
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_file = self.results_dir / f"backtest_chart_{timestamp}.png"
            plt.savefig(chart_file, dpi=150, bbox_inches='tight')
            logger.info(f"图表已保存到: {chart_file}")
            plt.close()

            return chart_file

        except Exception as e:
            logger.error(f"生成图表失败: {str(e)}", exc_info=True)
            return None
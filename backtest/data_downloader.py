import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from alert.binance_client import BinanceClient
from utils.logger import Logger

logger = Logger.get_logger('data_downloader')

POPULAR_SYMBOLS = [
    'BTCUSDT','ETHUSDT','BNBUSDT','XRPUSDT','SOLUSDT','ADAUSDT','DOGEUSDT','MATICUSDT','DOTUSDT','AVAXUSDT',
    'LTCUSDT','LINKUSDT','UNIUSDT','ATOMUSDT','ICPUSDT','ETCUSDT','FLOWUSDT','NEARUSDT','FTMUSDT','ETCUSDT',
    'COMPUSDT','AAVEUSDT','XLMUSDT','CHZUSDT','VETUSDT','XTZUSDT','OKBUSDT','FILUSDT','EOSUSDT','THETUSDT'
]

class DataDownloader:
    """K线数据下载器 - 支持离线模式"""

    def __init__(self, mode='live', use_testnet=False, offline=False):
        """
        初始化下载器

        :param mode: 模式 ('live', 'testnet')
        :param use_testnet: 是否使用测试网（在中国大陆建议开启）
        :param offline: 是否使用离线模式（只使用缓存，不连接网络）
        """
        import os

        self.offline = offline
        self.client = None  # 默认不创建客户端

        # 离线模式：只使用缓存，不连接API
        if offline:
            print("[离线模式] 只使用本地缓存数据，不连接网络")
            print("      - 适合已有缓存数据的情况")
            print("      - 不需要网络连接")
            print("      - 加速优化过程")
        else:
            # 检查环境变量，是否强制使用测试网
            if use_testnet or os.getenv('USE_TESTNET') == '1':
                self.mode = 'testnet'
                print("[提示] 使用测试网数据源 (testnet.binance.vision)")
                print("   - 适合中国大陆用户")
                print("   - 数据与主网基本相同")
                print("   - 不需要API密钥")
            else:
                self.mode = mode

            try:
                self.client = BinanceClient(self.mode)
            except Exception as e:
                if "Connection" in str(type(e).__name__) or "Timeout" in str(type(e).__name__):
                    print("\n" + "="*70)
                    print("❌ 无法连接到币安服务器")
                    print("="*70)
                    print("\n可能的原因和解决方案：")
                    print("\n1️⃣ 你在中国大陆，币安主网API无法直接访问")
                    print("   解决方案A: 设置环境变量使用测试网")
                    print("   ```")
                    print("   # Windows CMD")
                    print("   set USE_TESTNET=1")
                    print("   python optimizer/optimizer.py --quick --symbols BTCUSDT --days 30")
                    print("")
                    print("   # Windows PowerShell")
                    print("   $env:USE_TESTNET=1")
                    print("   python optimizer/optimizer.py --quick --symbols BTCUSDT --days 30")
                    print("   ```")
                    print("")
                    print("   解决方案B: 使用离线模式（推荐，如果有缓存数据）")
                    print("   ```")
                    print("   python optimizer/optimizer.py --offline --quick --symbols BTCUSDT --days 30")
                    print("   ```")
                    print("\n2️⃣ 需要开启VPN或配置代理")
                    print("   - 开启VPN后重试")
                    print("   - 或配置系统代理")
                    print("\n3️⃣ 防火墙阻止了网络连接")
                    print("   - 检查防火墙设置")
                    print("   - 允许Python网络访问")
                    print("\n" + "="*70)
                    print()
                    raise ConnectionError("无法连接币安API，请使用测试网/离线模式或VPN")
                else:
                    raise

        self.data_dir = Path('data/historical')
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def download_symbol_data(self, symbol, interval, days, force_download=False):
        """
        下载单个币种的历史数据
        :param symbol: 币种
        :param interval: K线周期 '1m', '5m', '15m', '1h', '4h' 等
        :param days: 回测天数
        :param force_download: 是否强制重新下载
        :return: DataFrame
        """
        try:
            # 检查是否已有缓存
            cache_file = self.get_cache_filename(symbol, interval, days)

            if cache_file.exists():
                if not force_download:
                    logger.info(f"{symbol} 数据已缓存，从文件加载")
                    return self.load_from_cache(cache_file)
                else:
                    logger.info(f"强制重新下载 {symbol} 数据")

            # 离线模式：缓存不存在时报错
            if self.offline:
                if not cache_file.exists():
                    print(f"\n[错误] 离线模式下找不到缓存: {cache_file}")
                    print(f"\n解决方法:")
                    print(f"  1. 先运行在线模式下载数据:")
                    print(f"     python optimizer/optimizer.py --testnet --quick --symbols {symbol} --days {days}")
                    print(f"  2. 或使用 --force 参数强制重新下载")
                    print(f"  3. 或退出离线模式进行数据下载")
                    raise FileNotFoundError(f"离线模式下缺少缓存: {cache_file}")

            logger.info(f"开始下载 {symbol} {interval} 数据，共 {days} 天")

            interval_minutes = self.get_interval_minutes(interval)
            total_klines_needed = int((days * 24 * 60) / interval_minutes)

            all_klines = self.download_in_batches(symbol, interval, total_klines_needed)

            if not all_klines:
                logger.error(f"{symbol} 数据下载失败")
                return None

            df = self.klines_to_dataframe(all_klines)

            self.save_to_cache(df, cache_file)

            logger.info(f"{symbol} 数据下载完成: {len(df)} 根K线")

            return df

        except Exception as e:
            logger.error(f"下载 {symbol} 数据失败: {str(e)}")
            return None
    
    def download_history_data_by_date_range(self, symbol, interval, start_date, end_date):
        """
        按日期范围下载历史数据
        
        Args:
            symbol: 币种
            interval: K线周期
            start_date: 开始日期 (YYYY-MM-DD 格式)
            end_date: 结束日期 (YYYY-MM-DD 格式)
        
        Returns:
            DataFrame
        """
        try:
            from datetime import timedelta
            
            # 转换为时间戳
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # 包含结束当天
            
            start_ts = int(start_dt.timestamp() * 1000)
            end_ts = int(end_dt.timestamp() * 1000)
            
            # 计算天数
            days = (end_dt - start_dt).days
            
            logger.info(f"下载 {symbol} 数据: {start_date} ~ {end_date} ({days}天)")
            
            # 计算需要的K线数量
            interval_minutes = self.get_interval_minutes(interval)
            total_klines_needed = int((days * 24 * 60) / interval_minutes)
            
            # 下载
            all_klines = self.download_in_batches_by_time_range(symbol, interval, start_ts, end_ts, total_klines_needed)
            
            if not all_klines:
                logger.error(f"{symbol} 数据下载失败")
                return None
            
            df = self.klines_to_dataframe(all_klines)
            
            # 过滤时间范围
            df = df[(df['timestamp'] >= start_ts) & (df['timestamp'] < end_ts)].copy()
            
            if df.empty:
                logger.error(f"{symbol} 数据为空（时间范围：{start_date} ~ {end_date}）")
                return None
            
            logger.info(f"{symbol} 数据下载完成: {len(df)} 根K线")
            
            return df
            
        except Exception as e:
            logger.error(f"按日期范围下载 {symbol} 数据失败: {str(e)}")
            return None
    
    def download_in_batches_by_time_range(self, symbol, interval, start_ts, end_ts, total_needed):
        """
        按时间范围分批下载K线数据
        
        Args:
            symbol: 币种
            interval: K线周期
            start_ts: 开始时间戳（毫秒）
            end_ts: 结束时间戳（毫秒）
            total_needed: 需要的总K线数
        
        Returns:
            K线列表
        """
        all_klines = []
        batch_size = 1500  # 币安API单次最大限制
        num_batches = (total_needed + batch_size - 1) // batch_size
        
        logger.info(f"需要 {total_needed} 根K线，分 {num_batches} 批下载")
        
        current_end_ts = end_ts
        
        for batch in range(num_batches):
            try:
                remaining = total_needed - len(all_klines)
                limit = min(batch_size, remaining)
                
                # 计算这批的开始时间
                interval_minutes = self.get_interval_minutes(interval)
                current_start_ts = current_end_ts - (limit - 1) * interval_minutes * 60 * 1000
                
                # 确保不超过开始时间
                if current_start_ts < start_ts:
                    current_start_ts = start_ts
                
                # 下载数据
                klines = self.client.client.futures_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit,
                    startTime=current_start_ts,
                    endTime=current_end_ts
                )
                
                if not klines:
                    logger.warning(f"{symbol} 第 {batch+1} 批数据为空，可能已到最早可用数据")
                    break
                
                all_klines = klines + all_klines
                current_end_ts = int(klines[0][0])
                
                logger.info(f"已下载 {len(all_klines)}/{total_needed} 根K线 (第 {batch+1}/{num_batches} 批)")
                
                if len(all_klines) >= total_needed:
                    break
                    
                # API限流等待
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"第 {batch+1} 批下载失败: {str(e)}")
                if len(all_klines) == 0:
                    raise
                break
        
        return all_klines
    
    def download_in_batches(self, symbol, interval, total_needed):
        """
        分批下载K线数据
        :param symbol: 币种
        :param interval: 周期
        :param total_needed: 需要的总K线数
        :return: K线列表
        """
        all_klines = []
        batch_size = 1500  # 币安API单次最大限制
        num_batches = (total_needed + batch_size - 1) // batch_size
        
        logger.info(f"需要 {total_needed} 根K线，分 {num_batches} 批下载")
        
        end_time = None  # 最新的时间
        
        for batch in range(num_batches):
            try:
                remaining = total_needed - len(all_klines)
                limit = min(batch_size, remaining)
                
                if end_time is None:
                    klines = self.client.get_klines(symbol, interval, limit)
                else:
                    klines = self.client.client.futures_klines(
                        symbol=symbol,
                        interval=interval,
                        limit=limit,
                        endTime=end_time - 1
                    )
                if not klines:
                    logger.warning(f"{symbol} 第 {batch+1} 批数据为空，可能已到最早可用数据")
                    break
                end_time = int(klines[0][0])
                all_klines = klines + all_klines
                logger.info(f"已下载 {len(all_klines)}/{total_needed} 根K线 (第 {batch+1}/{num_batches} 批)")
                if len(all_klines) >= total_needed:
                    break
                if len(klines) < limit:
                    logger.warning(f"{symbol} 已到最早可用数据，实际获取 {len(all_klines)} 根")
                    break
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"第 {batch+1} 批下载失败: {str(e)}")
                if len(all_klines) == 0:
                    raise
                break
        return all_klines
    
    def get_interval_minutes(self, interval):
        """获取周期对应的分钟数"""
        mapping = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480,
            '12h': 720, '1d': 1440, '3d': 4320, '1w': 10080
        }
        return mapping.get(interval, 5)
    
    def klines_to_dataframe(self, klines):
        """将K线数据转换为DataFrame"""
        data = []
        for k in klines:
            data.append({
                'timestamp': int(k[0]),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
                'close_time': int(k[6]),
                'quote_volume': float(k[7]),
                'trades': int(k[8]),
                'taker_buy_base': float(k[9]),
                'taker_buy_quote': float(k[10])
            })
        df = pd.DataFrame(data)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df
    
    def get_cache_filename(self, symbol, interval, days):
        """生成缓存文件名"""
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{symbol}_{interval}_{days}days_{date_str}.csv"
        return self.data_dir / filename
    
    def save_to_cache(self, df, cache_file):
        """保存数据到缓存"""
        try:
            df.to_csv(cache_file, index=False)
            logger.info(f"数据已缓存到: {cache_file}")
        except Exception as e:
            logger.error(f"保存缓存失败: {str(e)}")
    
    def load_from_cache(self, cache_file):
        """从缓存加载数据"""
        try:
            df = pd.read_csv(cache_file)
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            logger.info(f"从缓存加载: {len(df)} 根K线")
            return df
        except Exception as e:
            logger.error(f"加载缓存失败: {str(e)}")
            return None
    
    def download_multiple_symbols(self, symbols, interval, days, force_download=False):
        """
        下载多个币种的数据
        :param symbols: 币种列表
        :param interval: K线周期
        :param days: 回测天数
        :param force_download: 是否强制重新下载
        :return: {symbol: DataFrame}
        """
        result = {}
        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"下载进度: {i+1}/{len(symbols)} - {symbol}")
                df = self.download_symbol_data(symbol, interval, days, force_download)
                if df is not None:
                    result[symbol] = df
                if not force_download and i < len(symbols) - 1:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"下载 {symbol} 失败: {str(e)}")
                continue
        logger.info(f"数据下载完成: {len(result)}/{len(symbols)} 个币种")
        return result
    
    def clear_cache(self, older_than_days=7):
        """
        清理旧缓存
        :param older_than_days: 清理多少天前的缓存
        """
        try:
            cutoff_time = time.time() - (older_than_days * 24 * 3600)
            deleted_count = 0
            for cache_file in self.data_dir.glob('*.csv'):
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    deleted_count += 1
            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 个旧缓存文件")
        except Exception as e:
            logger.error(f"清理缓存失败: {str(e)}")

    def get_top_symbols(self, n=10):
        """根据历史缓存或默认列表，返回前 n 名成交量最高的币种列表。
        优先从本地缓存数据统计，如无缓存则回落使用默认常用币对。
        """
        try:
            symbol_vols = {}
            if self.data_dir.exists():
                for file in self.data_dir.glob('*.csv'):
                    stem = file.stem  # e.g. BTCUSDT_5m_180days_20260115
                    parts = stem.split('_')
                    if not parts:
                        continue
                    symbol = parts[0]
                    try:
                        df = pd.read_csv(file)
                        if 'quote_volume' in df.columns:
                            vol = float(df['quote_volume'].astype(float).sum())
                            symbol_vols[symbol] = vol
                    except Exception:
                        continue
            # 排序并取前 n 名
            sorted_symbols = sorted(symbol_vols.items(), key=lambda x: x[1], reverse=True)
            top = [s for s, _ in sorted_symbols[:n]]
            if len(top) < n:
                for s in POPULAR_SYMBOLS:
                    if s not in top:
                        top.append(s)
                        if len(top) >= n:
                            break
            return top[:n]
        except Exception:
            return POPULAR_SYMBOLS[:n]

POPULAR_SYMBOLS = [
    'BTCUSDT','ETHUSDT','BNBUSDT','XRPUSDT','SOLUSDT','ADAUSDT','DOGEUSDT','MATICUSDT','DOTUSDT','AVAXUSDT',
    'LTCUSDT','LINKUSDT','UNIUSDT','ATOMUSDT','ICPUSDT','ETCUSDT','FLOWUSDT','NEARUSDT','FTMUSDT','ETCUSDT',
    'COMPUSDT','AAVEUSDT','XLMUSDT','CHZUSDT','VETUSDT','XTZUSDT','OKBUSDT','FILUSDT','EOSUSDT','REQUSDT',
    'KCSUSDT','ZENUSDT','SUSHIUSDT','SNXUSDT','YFIIUSDT','CRVUSDT','RUNEUSDT','KLAYUSDT','BCHUSDT','ZILUSDT'
]


def main():
    downloader = DataDownloader()
    symbol = 'BTCUSDT'
    interval = '5m'
    days = 180
    df = downloader.download_symbol_data(symbol, interval, days)
    if df is not None:
        print(f"Downloaded {len(df)} rows for {symbol}")
    else:
        print("Download failed")

if __name__ == '__main__':
    main()

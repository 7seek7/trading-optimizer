#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台版本 - 持久化存储管理器
处理优化结果的保存、加载、清理等操作
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import shutil


class StorageManager:
    """持久化存储管理器"""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化存储管理器

        :param base_dir: 基础目录，默认为当前目录
        """
        if base_dir is None:
            base_dir = Path(__file__).parent

        self.base_dir = Path(base_dir)
        self.results_dir = self.base_dir / "results"
        self.cache_dir = self.base_dir / "data" / "historical"
        self.logs_dir = self.base_dir / "logs"

        # 创建必要的目录
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def save_optimization_result(
        self,
        param_combinations: List[Dict[str, float]],
        backtest_results: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存优化结果

        :param param_combinations: 参数组合列表
        :param backtest_results: 回测结果列表
        :param metadata: 元数据（币种、配置等）
        :return: 保存的文件路径
        """
        # 准备数据
        results_data = []
        for params, result in zip(param_combinations, backtest_results):
            results_data.append({
                'params': params,
                'metrics': result
            })

        # 添加元数据
        if metadata:
            results_data = {
                'results': results_data,
                'metadata': metadata,
                'timestamp': datetime.now().isoformat()
            }

        # 保存为JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = self.results_dir / f'results_{timestamp}.json'

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        return str(json_file)

    def load_optimization_result(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        加载优化结果

        :param file_path: 文件路径
        :return: 结果数据
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载文件失败: {str(e)}")
            return None

    def list_optimization_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出所有优化结果

        :param limit: 最多返回数量
        :return: 结果文件信息列表
        """
        result_files = list(self.results_dir.glob("results_*.json"))

        files_info = []
        for f in sorted(result_files, key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            try:
                data = self.load_optimization_result(str(f))

                info = {
                    'path': str(f),
                    'filename': f.name,
                    'timestamp': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    'size_kb': f.stat().st_size / 1024,
                }

                if isinstance(data, dict):
                    if 'metadata' in data:
                        info['metadata'] = data['metadata']

                    # 统计
                    results = data.get('results', [])
                    successful = len([r for r in results if 'error' not in r.get('metrics', {})])
                    failed = len(results) - successful

                    info['total'] = len(results)
                    info['successful'] = successful
                    info['failed'] = failed

                    if successful > 0:
                        returns = [r['metrics']['total_return']
                                 for r in results if 'error' not in r.get('metrics', {})]
                        info['best_return'] = max(returns)
                        info['avg_return'] = sum(returns) / len(returns)

                files_info.append(info)

            except Exception as e:
                print(f"读取文件失败 {f}: {str(e)}")
                continue

        return files_info

    def get_latest_result(self) -> Optional[Dict[str, Any]]:
        """
        获取最新的优化结果

        :return: 最新的结果数据
        """
        result_files = list(self.results_dir.glob("results_*.json"))

        if not result_files:
            return None

        latest_file = max(result_files, key=lambda f: f.stat().st_mtime)
        return self.load_optimization_result(str(latest_file))

    def delete_old_results(self, keep_count: int = 10):
        """
        删除旧的结果文件，只保留最新的N个

        :param keep_count: 保留的文件数量
        """
        result_files = list(self.results_dir.glob("results_*.json"))
        result_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # 删除超过keep_count的文件
        for f in result_files[keep_count:]:
            try:
                f.unlink()
                print(f"已删除旧结果: {f.name}")
            except Exception as e:
                print(f"删除失败 {f}: {str(e)}")

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息

        :return: 存储统计
        """
        def get_dir_size(dir_path: Path) -> int:
            """计算目录大小"""
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
            return total_size

        stats = {
            'results_dir': {
                'path': str(self.results_dir),
                'size_mb': get_dir_size(self.results_dir) / (1024 * 1024),
                'file_count': len(list(self.results_dir.glob("*.json")))
            },
            'cache_dir': {
                'path': str(self.cache_dir),
                'size_mb': get_dir_size(self.cache_dir) / (1024 * 1024),
                'file_count': len(list(self.cache_dir.glob("*.csv")))
            },
            'logs_dir': {
                'path': str(self.logs_dir),
                'size_mb': get_dir_size(self.logs_dir) / (1024 * 1024),
                'file_count': len(list(self.logs_dir.glob("*.log")))
            }
        }

        stats['total_size_mb'] = (
            stats['results_dir']['size_mb'] +
            stats['cache_dir']['size_mb'] +
            stats['logs_dir']['size_mb']
        )

        return stats

    def cleanup(self, keep_results: int = 10, max_cache_age_days: int = 7):
        """
        清理旧数据，释放存储空间

        :param keep_results: 保留的结果文件数量
        :param max_cache_age_days: 缓存文件最大保留天数
        """
        # 删除旧结果
        self.delete_old_results(keep_results)

        # 删除旧缓存
        now = datetime.now()
        for f in self.cache_dir.glob("*.csv"):
            file_time = datetime.fromtimestamp(f.stat().st_mtime)
            age_days = (now - file_time).days

            if age_days > max_cache_age_days:
                try:
                    f.unlink()
                    print(f"已删除旧缓存: {f.name} (age: {age_days} days)")
                except Exception as e:
                    print(f"删除缓存失败 {f}: {str(e)}")

        # 删除旧日志
        for f in self.logs_dir.glob("*.log"):
            file_time = datetime.fromtimestamp(f.stat().st_mtime)
            age_days = (now - file_time).days

            if age_days > 7:  # 日志保留7天
                try:
                    f.unlink()
                    print(f"已删除旧日志: {f.name} (age: {age_days} days)")
                except Exception as e:
                    print(f"删除日志失败 {f}: {str(e)}")

    def export_results_to_csv(self, file_path: str, limit: int = 100) -> Optional[str]:
        """
        导出结果到CSV文件

        :param file_path: 结果文件路径
        :param limit: 最大导出数量
        :return: CSV文件路径
        """
        data = self.load_optimization_result(file_path)

        if not data:
            return None

        results = data if isinstance(data, list) else data.get('results', [])

        if not results:
            return None

        # 转换为CSV
        import pandas as pd

        rows = []
        for r in results[:limit]:
            row = {
                '收益率': r['metrics'].get('total_return', 0),
                '最终资金': r['metrics'].get('final_balance', 0),
                '交易笔数': r['metrics'].get('total_trades', 0),
                '成功': 'error' not in r['metrics']
            }

            # 添加参数
            for key, value in r['params'].items():
                row[key] = value

            rows.append(row)

        df = pd.DataFrame(rows)

        # 保存CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = self.results_dir / f'export_{timestamp}.csv'
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')

        return str(csv_file)

    def backup_results(self, backup_dir: Optional[str] = None) -> str:
        """
        备份所有结果到指定目录

        :param backup_dir: 备份目录
        :return: 备份目录路径
        """
        if backup_dir is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = self.base_dir / f'backup_{timestamp}'

        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 复制所有结果文件
        if self.results_dir.exists():
            for f in self.results_dir.glob("*.json"):
                shutil.copy2(f, backup_dir / f.name)

        print(f"已备份 {len(list(backup_dir.glob('*.json')))} 个结果文件到: {backup_dir}")

        return str(backup_dir)


# 全局单例（可选）
_storage_manager = None


def get_storage_manager(base_dir: Optional[Path] = None) -> StorageManager:
    """
    获取存储管理器实例

    :param base_dir: 基础目录
    :return: 存储管理器实例
    """
    global _storage_manager

    if _storage_manager is None:
        _storage_manager = StorageManager(base_dir)

    return _storage_manager

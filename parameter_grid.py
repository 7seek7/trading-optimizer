#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数网格生成器
支持固定参数（start == stop）和过滤无效配置项
"""

from itertools import product
from typing import Dict, List, Any

# 组合数警告阈值
WARNING_THRESHOLD = 10000
ERROR_THRESHOLD = 1000000


def create_quick_config() -> Dict[str, Dict[str, float]]:
    """
    创建快速优化配置（核心参数）

    这个配置只包含最重要的4个参数，用于快速测试。
    组合数约875个，预计耗时5-20分钟（取决于硬件）。

    返回:
        参数配置字典
    """
    return {
        'PRICE_CHANGE_THRESHOLD': {
            'start': 2.0,
            'stop': 4.0,
            'step': 0.5
        },
        'VOLUME_THRESHOLD': {
            'start': 3.0,
            'stop': 6.0,
            'step': 0.5
        },
        'HIGH_PROFIT_THRESHOLD': {
            'start': 6.0,
            'stop': 10.0,
            'step': 1.0
        },
        'STOPLOSS_TRIGGER1': {
            'start': -8.0,
            'stop': -6.0,
            'step': 0.5
        }
    }


class ParameterGrid:
    """
    参数网格生成器
    """

    def __init__(self, param_config):
        """
        初始化参数网格生成器

        :param param_config: 参数配置字典
        """
        # 过滤有效的参数配置（只保留完整的字典配置）
        self.param_config = {}
        for param_name, config in param_config.items():
            # 跳过非字典项
            if not isinstance(config, dict):
                continue
            # 只保留包含 start/stop/step 的字典
            if 'start' in config and 'stop' in config and 'step' in config:
                self.param_config[param_name] = config

        if not self.param_config:
            raise ValueError("配置文件中没有有效的参数！请检查配置格式。")

        self._validate_config()
        self._check_combinations_warning()

    def _validate_config(self):
        """验证配置有效性"""
        for param_name, config in self.param_config.items():
            start = config['start']
            stop = config['stop']
            step = config['step']

            # 验证数值范围
            if start > stop:
                raise ValueError(f"参数 {param_name} 的起始值大于结束值")

            # 验证步长（范围参数）
            if start != stop and step <= 0:
                raise ValueError(f"参数 {param_name} 的步长必须大于0")

    def _check_combinations_warning(self):
        """检查并警告组合数是否过大"""
        total = 0
        fixed_count = 0
        range_count = 0

        for param_name, config in self.param_config.items():
            start = config['start']
            stop = config['stop']
            step = config['step']

            # 计算该参数的可能值数量
            if start == stop:
                count = 1
                fixed_count += 1
            else:
                count = int((stop - start) / step) + 1
                range_count += 1

            # 计算总组合数
            if total == 0:
                total = count
            else:
                if total > ERROR_THRESHOLD or count > ERROR_THRESHOLD:
                    total = ERROR_THRESHOLD + 1
                else:
                    total = total * count

        print(f"固定参数: {fixed_count} 个, 范围参数: {range_count} 个")
        if total > ERROR_THRESHOLD:
            print(f"警告: 组合数过多 ({total:,})，建议固定更多参数")
        elif total > WARNING_THRESHOLD:
            print(f"注意: 组合数较大 ({total:,})，可能需要较长时间")

    def _generate_range(self, config):
        """生成参数值列表"""
        start = config['start']
        stop = config['stop']

        # 固定参数：start == stop
        if start == stop:
            return [round(start, 2)]

        # 范围参数：生成范围值
        values = []
        current = start
        while current <= stop:
            values.append(round(current, 2))
            current += config['step']

        return values

    def generate(self):
        """生成所有参数组合"""
        # 检查组合数是否过多
        total = self.count_combinations()
        if total >= ERROR_THRESHOLD:
            raise ValueError(f"参数组合数过多（{total:,}），无法生成。请固定更多参数。")

        # 为每个参数生成值列表
        param_values = {}
        for param_name, config in self.param_config.items():
            param_values[param_name] = self._generate_range(config)

        # 生成所有组合
        combinations = list(product(*param_values.values()))

        # 转换为字典列表
        result = []
        for combo in combinations:
            param_dict = {}
            for i, param_name in enumerate(param_values.keys()):
                param_dict[param_name] = combo[i]
            result.append(param_dict)

        return result

    def count_combinations(self):
        """计算参数组合总数"""
        total = 1
        for config in self.param_config.values():
            start = config['start']
            stop = config['stop']
            step = config['step']

            if start == stop:
                count = 1
            else:
                count = int((stop - start) / step) + 1

            # 防止溢出
            if total > ERROR_THRESHOLD:
                return ERROR_THRESHOLD + 1
            total = total * count

        return total

    def get_param_info(self):
        """获取参数信息"""
        info = {}
        for param_name, config in self.param_config.items():
            values = self._generate_range(config)
            info[param_name] = {
                'range': f"{config['start']} ~ {config['stop']}",
                'step': config['step'],
                'count': len(values),
                'is_fixed': config['start'] == config['stop']
            }
        return info

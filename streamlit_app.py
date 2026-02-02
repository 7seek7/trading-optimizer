#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台版本 - 参数优化系统Streamlit界面
完全在平台上运行，不依赖本地资源
"""

import streamlit as st
import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime
import pandas as pd

# 设置页面配置
st.set_page_config(
    page_title="交易机器人参数优化系统 - 平台版",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 添加当前目录到Python路径（platform_deployment作为独立运行目录）
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

class OptimizerUI:
    """完整的参数优化系统UI"""

    def __init__(self):
        """初始化UI"""
        self.optimizer_dir = current_dir / "results"
        self.optimizer_dir.mkdir(exist_ok=True)

        # 创建必要的子目录
        (current_dir / "data").mkdir(exist_ok=True)
        (current_dir / "data" / "historical").mkdir(parents=True, exist_ok=True)

    def render_header(self):
        """渲染页面标题"""
        st.title("🤖 交易机器人参数优化系统 (平台版)")
        st.markdown("### 24小时云端运行 | 完全离线回测 | AI智能优化")
        st.markdown("---")

        # 功能介绍标签页
        tab1, tab2, tab3 = st.tabs(["✨ 主要功能", "📊 使用场景", "⚠️ 注意事项"])

        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info("🎯 **参数优化**")
                st.write("- 手动设置参数范围\n- 完整/快速优化模式\n- 多币种批量测试")
            with col2:
                st.info("🤖 **AI智能优化**")
                st.write("- AI自动选择高波动币种\n- AI生成最优参数组合\n- 持续迭代学习")
            with col3:
                st.info("☁️ **云端运行**")
                st.write("- 完全平台部署\n- 24小时持续运行\n- 本地电脑不需开机")

        with tab2:
            st.write("🔹 **场景1：手动优化**")
            st.write("当你对参数有一定了解，想要系统性地测试特定参数范围时")
            st.write("🔹 **场景2：AI智能优化**")
            st.write("当希望AI根据策略特性自动选择币种和参数时")
            st.write("🔹 **场景3：持续监控**")
            st.write("需要24小时持续运行，寻找市场最新机会时")

        with tab3:
            st.warning("⚠️ **重要提示**")
            st.write("- 首次运行需要下载历史数据（约5-15分钟，取决于币种数量）")
            st.write("- 后续运行会使用缓存数据，速度大幅提升")
            st.write("- 回测结果仅供参考，实盘请谨慎测试")
            st.write("- 建议从虚拟盘/小资金开始验证")

        st.markdown("---")

    def render_sidebar(self):
        """渲染侧边栏"""
        st.sidebar.header("🔧 系统设置")

        # 模式选择
        self.mode = st.sidebar.radio(
            "选择优化模式",
            ["🎯 手动优化", "🤖 AI智能优化", "📊 历史记录"],
            label_visibility="collapsed"
        )

        st.sidebar.markdown("---")

        # 数据源设置
        st.sidebar.header("📡 数据源设置")
        self.use_testnet = st.sidebar.checkbox(
            "使用测试网（推荐中国用户）",
            value=True,
            help="测试网数据与主网相同，但不需要VPN"
        )

        self.use_offline = st.sidebar.checkbox(
            "离线模式（只使用缓存）",
            value=False,
            help="不下载新数据，只使用已有的缓存数据"
        )

        st.sidebar.markdown("---")

        # 存储空间信息
        self.render_storage_info()

        # AI API配置（仅在AI模式显示）
        if self.mode == "🤖 AI智能优化":
            self.render_ai_config()

        return self.mode

    def render_ai_config(self):
        """渲染AI API配置"""
        st.sidebar.header("🔑 AI API配置")

        self.api_source = st.sidebar.selectbox(
            "AI服务提供商",
            ["NVIDIA API (推荐)", "DeepSeek", "通义千问", "OpenAI"],
            help="推荐使用NVIDIA NIM API：GPU加速，模型丰富，API稳定"
        )

        if self.api_source == "NVIDIA API (推荐)":
            self.api_key = st.sidebar.text_input(
                "API密钥 (NVAPI-开头)",
                type="password",
                value="nvapi-",
                help="输入你的NVIDIA NGC API Key，格式: nvapi-xxxxxxxxxxxxx"
            )
            self.api_base = st.sidebar.text_input(
                "API基础URL",
                value="https://integrate.api.nvidia.com/v1",
                help="NVIDIA NIM API地址"
            )
            self.model = st.sidebar.selectbox(
                "模型（推荐交易优化）",
                [
                    "deepseek-ai/deepseek-v3 (推荐 - 中文优化)",
                    "meta/llama-3.1-8b-instruct (速度快)",
                    "meta/llama-3.1-70b-instruct (高质量)",
                    "mistralai/mistral-7b-instruct (通用)",
                    "qwen/qwen2.5-7b-instruct (中文优化)"
                ],
                help="推荐使用deepseek-v3进行交易优化"
            )
        elif self.api_source == "OpenAI":
            self.api_key = st.sidebar.text_input(
                "API密钥",
                type="password",
                help="输入你的OpenAI API密钥"
            )
            self.api_base = st.sidebar.text_input(
                "API基础URL",
                value="https://api.openai.com/v1",
                help="OpenAI API地址，可使用代理"
            )
            self.model = st.sidebar.selectbox(
                "模型",
                ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"]
            )
        elif self.api_source == "通义千问":
            self.api_key = st.sidebar.text_input(
                "API密钥",
                type="password",
                help="输入你的通义千问API密钥"
            )
            self.api_base = st.sidebar.text_input(
                "API基础URL",
                value="https://dashscope.aliyuncs.com/compatible-mode/v1",
                help="通义千问兼容API地址"
            )
            self.model = st.sidebar.selectbox(
                "模型",
                ["qwen-turbo", "qwen-plus", "qwen-max"]
            )
        else:  # DeepSeek
            self.api_key = st.sidebar.text_input(
                "API密钥",
                type="password",
                help="输入你的DeepSeek API密钥"
            )
            self.api_base = st.sidebar.text_input(
                "API基础URL",
                value="https://api.deepseek.com/v1",
                help="DeepSeek API地址"
            )
            self.model = st.sidebar.selectbox(
                "模型",
                ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
                help="deepseek-chat: 通用推理; deepseek-reasoner: 复杂推理"
            )

    def render_storage_info(self):
        """渲染存储空间信息"""
        data_dir = current_dir / "data"
        if data_dir.exists():
            self.calculate_directory_size(data_dir)

    def calculate_directory_size(self, directory):
        """计算目录大小"""
        total_size = 0
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
                file_count += 1

        size_mb = total_size / (1024 * 1024)
        st.sidebar.info(f"📁 本地数据: {file_count} 文件, {size_mb:.1f} MB")

    def get_available_coins(self):
        """获取已下载的币种数据"""
        data_dir = current_dir / "data" / "historical"
        if not data_dir.exists():
            return []

        coins = []
        csv_files = list(data_dir.glob("*_1m_*days_*.csv"))
        for f in csv_files:
            coin = f.stem.split('_1m')[0]
            if coin not in coins and 'USDT' in coin:
                coins.append(coin)

        return sorted(coins)

    def run_manual_optimization(self):
        """手动优化模式"""
        st.header("🎯 手动参数优化")

        # 配置文件选择
        st.subheader("1. 选择配置文件")

        config_dir = current_dir
        config_files = list(config_dir.glob("config_*.json")) + list(config_dir.glob("*_config.json"))

        config_options = ["快速优化 (默认5-20分钟)"]
        if config_files:
            for f in config_files:
                config_options.append(f.name)

        selected_config = st.selectbox(
            "使用预设参数配置",
            config_options,
            help="快速优化只测试核心参数，完整优化测试所有参数"
        )

        # 币种选择
        st.subheader("2. 选择币种")

        available_coins = self.get_available_coins()

        col1, col2 = st.columns([3, 1])
        with col1:
            # 币种输入（支持多选或自定义）
            coin_input = st.text_input(
                "输入币种（多个用空格或逗号分隔）",
                placeholder="例如: BTCUSDT ETHUSDT DOGEUSDT",
                help="输入币种代码，如 BTCUSDT"
            )

            # 常见币种快速选择
            st.write("**常见币种快速选择:**")
            common_coins = ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "PEPEUSDT",
                          "SOLUSDT", "MATICUSDT", "AVAXUSDT", "LINKUSDT"]
            selected_common = st.multiselect(
                "选择常见币种（可选，或在上文直接输入）",
                common_coins,
                default=[]
            )

        with col2:
            # 回测天数
            days = st.number_input(
                "回测天数",
                min_value=7,
                max_value=365,
                value=30,
                help="历史数据天数"
            )

            # K线周期
            interval = st.selectbox(
                "K线周期",
                ["1m", "5m", "15m", "1h"],
                index=1,
                help="K线时间周期"
            )

        # 解析币种
        coins = []
        if coin_input:
            for c in coin_input.replace(',', ' ').split():
                c = c.strip().upper()
                if c and c not in coins:
                    coins.append(c)

        # 添加从多选框选择的币种
        for c in selected_common:
            if c not in coins:
                coins.append(c)

        # 显示已选择的币种
        if coins:
            st.success(f"✅ 已选择币种: {', '.join(coins)}")
        else:
            st.warning("⚠️ 请至少选择一个币种")

        # 显示可用数据
        if available_coins:
            with st.expander(f"📂 查看已下载的币种 ({len(available_coins)} 个)"):
                cols = st.columns(4)
                for idx, coin in enumerate(available_coins):
                    cols[idx % 4].write(f"- {coin}")

        st.markdown("---")

        # 优化选项
        st.subheader("3. 优化设置")

        col1, col2, col3 = st.columns(3)

        with col1:
            save_results = st.checkbox(
                "保存结果到文件",
                value=True,
                help="保存详细结果供后续分析"
            )

        with col2:
            skip_estimate = st.checkbox(
                "跳过确认",
                value=False,
                help="直接开始优化，不显示估算"
            )

        with col3:
            run_testnet = st.checkbox(
                "使用测试网",
                value=self.use_testnet,
                help="使用测试网数据源"
            )

        # 开始按钮
        st.markdown("---")

        if st.button("🚀 开始优化", type="primary", disabled=not coins):
            self.run_manual_optimization_process(
                coins=coins,
                config=selected_config,
                days=days,
                interval=interval,
                use_testnet=run_testnet,
                use_offline=self.use_offline,
                save_results=save_results,
                skip_estimate=skip_estimate
            )

    def run_manual_optimization_process(self, coins, config, days, interval,
                                       use_testnet, use_offline, save_results, skip_estimate):
        """执行手动优化"""
        try:
            # 显示配置摘要
            with st.spinner("初始化优化器..."):
                from optimizer import Optimizer

                # 确定配置文件
                config_file = None
                use_json_config = False
                if config != "快速优化 (默认5-20分钟)":
                    # 使用指定的配置文件
                    config_file = current_dir / config
                    use_json_config = True
                    if not config_file.exists():
                        st.error(f"配置文件不存在: {config_file}")
                        return

                # 创建优化器
                optimizer = Optimizer(
                    symbols=coins,
                    interval=interval,
                    days=days,
                    config_file=str(config_file) if config_file else None,
                    use_json_config=use_json_config,
                    use_testnet=use_testnet,
                    use_offline=use_offline,
                    no_save=not save_results
                )

            # 时间估算
            if not skip_estimate:
                st.subheader("📊 运行估算")
                with st.spinner("计算预计时间..."):
                    optimizer.print_estimate()

                # 显示摘要
                combinations_count = optimizer.grid.count_combinations()
                st.info(f"将运行 **{combinations_count:,}** 个参数组合回测")

                # 等待确认（在Streamlit中，可以不用确认，直接运行）
                time.sleep(2)

            # 运行优化
            with st.spinner("运行优化中...这可能需要几分钟到几小时..."):
                progress_bar = st.progress(0, text="准备数据...")

                # 由于Optimizer.run()会阻塞，我们需要修改它以支持进度回调
                # 这里我们先直接运行，后续可以改进

                result = optimizer.run()

            # 显示结果
            st.success("✅ 优化完成!")

            if result.get('status') == 'completed':
                analysis = result.get('analysis', {})

                if analysis.get('best'):
                    best = analysis['best']
                    st.subheader("🏆 最佳参数组合")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("收益率", f"{best['metrics']['total_return']:+.2f}%")
                    with col2:
                        st.metric("最终资金", f"{best['metrics']['final_balance']:.0f}")
                    with col3:
                        st.metric("交易笔数", best['metrics']['total_trades'])

                    with st.expander("查看最佳参数"):
                        for param, value in best['params'].items():
                            st.write(f"**{param}**: {value}")

                    # 显示更多结果
                    if analysis.get('successful_count', 0) > 1:
                        st.subheader("📈 统计摘要")
                        st.write("- 成功组合:", analysis.get('successful_count', 0))
                        st.write("- 失败组合:", analysis.get('failed_count', 0))
                        st.write("- 平均收益率:", f"{analysis.get('avg_return', 0):.2f}%")

        except Exception as e:
            st.error(f"❌ 优化失败: {str(e)}")
            with st.expander("查看详细错误"):
                import traceback
                st.code(traceback.format_exc())

    def run_ai_optimization(self):
        """AI智能优化模式"""
        st.header("🤖 AI智能参数优化")

        # 检查API配置
        if not hasattr(self, 'api_key') or not self.api_key:
            st.warning("⚠️ 请先在侧边栏配置AI API密钥")
            return

        st.info("📌 AI优化说明：")
        st.write("""
        - AI会根据交易策略特性，自动选择最适合的高波动币种
        - AI会在您给定的参数范围内，智能调优参数
        - 支持多轮迭代优化，持续寻找最优组合
        - 全程自动，无需人工干预
        """)

        st.markdown("---")

        # 优化配置
        st.subheader("优化设置")

        col1, col2, col3 = st.columns(3)

        with col1:
            rounds = st.number_input(
                "优化轮数",
                min_value=1,
                max_value=10,
                value=3,
                help="迭代轮数，越多可能找到更好参数"
            )

        with col2:
            coins_per_round = st.number_input(
                "每轮币种数",
                min_value=1,
                max_value=10,
                value=3,
                help="每轮选择多少个币种"
            )

        with col3:
            configs_per_coin = st.number_input(
                "每币种配置数",
                min_value=1,
                max_value=5,
                value=2,
                help="每个币种测试多少组参数"
            )

        st.info(f"预计运行约 **{rounds * coins_per_round * configs_per_coin}** 个完整优化流程")

        # 参数范围（可选）
        with st.expander("⚙️ 设置参数范围（可选，不设置则使用默认）"):
            st.write("""
            您可以在这里限制AI的调优范围，例如：
            - STOP_LOSS_PERCENT: 1.0 ~ 3.0
            - TAKE_PROFIT_PERCENT: 2.0 ~ 6.0
            - ALERT_CONFIRMATION_MINUTES: 3.0 ~ 15.0

            不设置此部分，AI会使用默认范围。
            """)
            param_ranges = st.text_area(
                "参数范围（JSON格式）",
                placeholder='{"STOP_LOSS_PERCENT": {"start": 1.0, "stop": 3.0, "step": 0.5}}',
                height=150
            )

        st.markdown("---")

        # 允许用户继续
        if st.button("🚀 开始AI优化", type="primary"):
            self.run_ai_optimization_process(
                api_key=self.api_key,
                api_base=self.api_base,
                model=self.model,
                rounds=rounds,
                coins_per_round=coins_per_round,
                configs_per_coin=configs_per_coin,
                param_ranges=param_ranges
            )

    def run_ai_optimization_process(self, api_key, api_base, model, rounds,
                                   coins_per_round, configs_per_coin, param_ranges):
        """执行AI优化"""
        try:
            # 创建进度状态
            if 'ai_optimization' not in st.session_state:
                st.session_state.ai_optimization = {
                    'status': 'idle',
                    'progress': 0,
                    'message': '',
                    'results': []
                }

            st.session_state.ai_optimization['status'] = 'running'

            progress_bar = st.progress(0, text="初始化AI连接...")
            status_text = st.empty()

            # 导入AI优化器
            from auto_ai_optimizer import AutoOptimizer

            # 创建优化器
            status_text.text("连接AI服务...")
            optimizer = AutoOptimizer(api_key, api_base, model)

            # 解析参数范围
            if param_ranges:
                try:
                    import json
                    user_param_ranges = json.loads(param_ranges)
                except:
                    user_param_ranges = {}
            else:
                user_param_ranges = {}

            # 开始多轮优化
            best_overall = {
                'return': -999999,
                'config': None,
                'coins': None,
                'round': None
            }

            for round_num in range(1, rounds + 1):
                round_progress = (round_num - 1) / rounds
                progress_bar.progress(int(round_progress * 100), text=f"第 {round_num}/{rounds} 轮")
                status_text.text(f"第 {round_num}/{rounds} 轮: 选择币种...")

                # 获取并选择币种
                available_coins = optimizer.get_available_coins()
                coins = optimizer.ask_ai_select_coins(available_coins, coins_per_round)

                status_text.text(f"第 {round_num}/{rounds} 轮: 已选择 {len(coins)} 个币种")

                # 生成配置
                configs = optimizer.ask_ai_generate_configs(coins, configs_per_coin, user_param_ranges)

                # 运行配置
                round_best = None
                for idx, config in enumerate(configs):
                    config_progress = round_progress + ((idx + 1) / len(configs)) / rounds
                    progress_bar.progress(int(config_progress * 100),
                                        text=f"第 {round_num}/{rounds} 轮: 配置 {idx+1}/{len(configs)}")

                    try:
                        result = optimizer.run_single_config(coins, config)

                        # 更新最佳
                        if 'error' not in result:
                            best_return = result.get('best_return', -999999)
                            if best_return > best_overall['return']:
                                best_overall['return'] = best_return
                                best_overall['config'] = result
                                best_overall['coins'] = coins
                                best_overall['round'] = round_num
                                round_best = result

                    except Exception as e:
                        status_text.warning(f"配置运行失败: {str(e)}")

                status_text.text(f"第 {round_num} 轮完成")

            # 完成
            progress_bar.progress(100, text="优化完成!")
            st.session_state.ai_optimization['status'] = 'completed'
            st.session_state.ai_optimization['progress'] = 100

            # 显示结果
            if best_overall['config']:
                st.success("✅ AI优化完成!")

                st.subheader("🏆 最佳结果")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("最佳收益", f"{best_overall['return']:+.2f}%")
                with col2:
                    st.metric("优化轮次", best_overall['round'])
                with col3:
                    st.metric("币种数量", len(best_overall['coins']))

                st.write(f"**使用的币种**:", ', '.join(best_overall['coins']))

                with st.expander("查看详细参数"):
                    st.json(best_overall['config'])
            else:
                st.warning("未找到有效的优化结果")

        except Exception as e:
            st.error(f"❌ AI优化失败: {str(e)}")
            with st.expander("查看详细错误"):
                import traceback
                st.code(traceback.format_exc())
            st.session_state.ai_optimization['status'] = 'error'

    def run_history_view(self):
        """历史记录模式"""
        st.header("📊 优化历史记录")

        # 获取所有结果文件
        result_files = list(self.optimizer_dir.glob("results_*.json"))

        if not result_files:
            st.info("暂无优化记录")
            return

        # 按时间排序
        result_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # 文件选择
        file_options = []
        for f in result_files:
            timestamp = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            size = f.stat().st_size / 1024
            file_options.append(f"{timestamp} ({size:.1f} KB)")

        selected_file = st.selectbox("选择优化记录", file_options)

        if selected_file:
            # 读取结果
            selected_index = file_options.index(selected_file)
            file_path = result_files[selected_index]

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            results = data if isinstance(data, list) else data.get('results', [])

            if results:
                # 统计摘要
                successful = [r for r in results if 'error' not in r.get('metrics', {})]
                failed = [r for r in results if 'error' in r.get('metrics', {})]

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总测试", len(results))
                with col2:
                    st.metric("成功", len(successful), delta=None)
                with col3:
                    st.metric("失败", len(failed), delta=None)
                with col4:
                    success_rate = len(successful) / len(results) * 100 if results else 0
                    st.metric("成功率", f"{success_rate:.1f}%")

                st.markdown("---")

                # 最佳结果
                if successful:
                    st.subheader("🏆 最佳参数组合")

                    successful_sorted = sorted(
                        successful,
                        key=lambda x: x['metrics']['total_return'],
                        reverse=True
                    )

                    best = successful_sorted[0]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("收益率", f"{best['metrics']['total_return']:+.2f}%")
                    with col2:
                        st.metric("最终资金", f"{best['metrics']['final_balance']:.0f}")
                    with col3:
                        st.metric("交易笔数", best['metrics']['total_trades'])

                    with st.expander("查看最佳参数配置"):
                        for param, value in best['params'].items():
                            st.write(f"**{param}**: {value}")

                    st.markdown("---")

                    # TOP 10 结果表格
                    st.subheader("📈 TOP 10 结果")

                    top10_data = []
                    for i, r in enumerate(successful_sorted[:10], 1):
                        top10_data.append({
                            "排名": i,
                            "收益率": f"{r['metrics']['total_return']:+.2f}%",
                            "最终资金": f"{r['metrics']['final_balance']:.0f}",
                            "交易笔数": r['metrics']['total_trades'],
                            "止损": r['params'].get('STOP_LOSS_PERCENT', 0),
                            "止盈": r['params'].get('TAKE_PROFIT_PERCENT', 0),
                            "确认时间": r['params'].get('ALERT_CONFIRMATION_MINUTES', 0)
                        })

                    df = pd.DataFrame(top10_data)
                    st.dataframe(df, use_container_width=True)

                    st.markdown("---")

                # 失败分析
                if failed:
                    st.subheader("❌ 失败分析")
                    from collections import Counter

                    errors = Counter([r['metrics'].get('error', 'Unknown')[:50] for r in failed])

                    error_df = pd.DataFrame([
                        {"错误类型": error, "次数": count, "占比": f"{count/len(failed)*100:.1f}%"}
                        for error, count in errors.most_common()
                    ])
                    st.dataframe(error_df, use_container_width=True)

                # 失败详情
                with st.expander(f"查看所有失败的组合 ({len(failed)} 个)"):
                    for i, r in enumerate(failed[:20], 1):  # 最多显示20个
                        st.write(f"{i}. {r['metrics'].get('error', 'Unknown')}")

    def run(self):
        """运行主程序"""
        # 渲染侧边栏
        mode = self.render_sidebar()

        # 渲染主区域
        self.render_header()

        # 根据模式渲染对应内容
        if mode == "🎯 手动优化":
            self.run_manual_optimization()
        elif mode == "🤖 AI智能优化":
            self.run_ai_optimization()
        elif mode == "📊 历史记录":
            self.run_history_view()

        # 页脚
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: gray; font-size: 0.8em;'>
            交易机器人参数优化系统 - 平台版 | 24小时运行中<br>
            ⚠️ 回测结果仅供参考，不构成投资建议
        </div>
        """, unsafe_allow_html=True)


def main():
    """主函数"""
    app = OptimizerUI()
    app.run()


if __name__ == '__main__':
    main()

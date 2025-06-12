#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Virtual Table Performance Monitor - Virtual Table のパフォーマンス監視
"""

import time
from typing import Dict, Any, List
from datetime import datetime


class VirtualTablePerformanceMonitor:
    """
    Virtual Table のパフォーマンス監視クラス
    
    大量データ処理時のパフォーマンス指標を収集・分析
    """
    
    def __init__(self):
        self.metrics = {
            'data_operations': [],
            'filter_operations': [],
            'rendering_operations': [],
            'memory_usage': [],
            'total_rows': 0,
            'filtered_rows': 0
        }
        self.start_time = None
    
    def start_operation(self, operation_type: str, description: str = ""):
        """操作開始"""
        self.start_time = time.time()
        return {
            'type': operation_type,
            'description': description,
            'start_time': self.start_time
        }
    
    def end_operation(self, operation_info: Dict[str, Any], row_count: int = 0):
        """操作終了"""
        if self.start_time is None:
            return
        
        end_time = time.time()
        duration = end_time - self.start_time
        
        metric = {
            'type': operation_info['type'],
            'description': operation_info['description'],
            'duration': duration,
            'row_count': row_count,
            'timestamp': datetime.now().isoformat(),
            'throughput': row_count / duration if duration > 0 else 0
        }
        
        # 操作タイプ別に記録
        if operation_info['type'] == 'data':
            self.metrics['data_operations'].append(metric)
        elif operation_info['type'] == 'filter':
            self.metrics['filter_operations'].append(metric)
        elif operation_info['type'] == 'render':
            self.metrics['rendering_operations'].append(metric)
        
        self.start_time = None
        return metric
    
    def record_memory_usage(self, usage_mb: float):
        """メモリ使用量を記録"""
        self.metrics['memory_usage'].append({
            'usage_mb': usage_mb,
            'timestamp': datetime.now().isoformat()
        })
    
    def update_row_counts(self, total_rows: int, filtered_rows: int):
        """行数を更新"""
        self.metrics['total_rows'] = total_rows
        self.metrics['filtered_rows'] = filtered_rows
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得"""
        stats = {
            'current_state': {
                'total_rows': self.metrics['total_rows'],
                'filtered_rows': self.metrics['filtered_rows'],
                'filter_ratio': (self.metrics['filtered_rows'] / self.metrics['total_rows'] * 100) 
                               if self.metrics['total_rows'] > 0 else 0
            },
            'data_operations': self._analyze_operations(self.metrics['data_operations']),
            'filter_operations': self._analyze_operations(self.metrics['filter_operations']),
            'rendering_operations': self._analyze_operations(self.metrics['rendering_operations']),
            'memory_usage': self._analyze_memory_usage()
        }
        
        return stats
    
    def _analyze_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """操作のパフォーマンス分析"""
        if not operations:
            return {
                'count': 0,
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0,
                'avg_throughput': 0
            }
        
        durations = [op['duration'] for op in operations]
        throughputs = [op['throughput'] for op in operations if op['throughput'] > 0]
        
        return {
            'count': len(operations),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'avg_throughput': sum(throughputs) / len(throughputs) if throughputs else 0,
            'total_rows_processed': sum(op['row_count'] for op in operations)
        }
    
    def _analyze_memory_usage(self) -> Dict[str, Any]:
        """メモリ使用量分析"""
        if not self.metrics['memory_usage']:
            return {
                'current_mb': 0,
                'peak_mb': 0,
                'avg_mb': 0
            }
        
        usages = [entry['usage_mb'] for entry in self.metrics['memory_usage']]
        
        return {
            'current_mb': usages[-1] if usages else 0,
            'peak_mb': max(usages),
            'avg_mb': sum(usages) / len(usages)
        }
    
    def get_performance_report(self) -> str:
        """パフォーマンスレポートを生成"""
        stats = self.get_performance_stats()
        
        report = "=== Virtual Table Performance Report ===\n\n"
        
        # 現在の状態
        current = stats['current_state']
        report += f"Current State:\n"
        report += f"  Total Rows: {current['total_rows']:,}\n"
        report += f"  Filtered Rows: {current['filtered_rows']:,}\n"
        report += f"  Filter Ratio: {current['filter_ratio']:.1f}%\n\n"
        
        # データ操作
        data_ops = stats['data_operations']
        if data_ops['count'] > 0:
            report += f"Data Operations ({data_ops['count']} operations):\n"
            report += f"  Avg Duration: {data_ops['avg_duration']:.3f}s\n"
            report += f"  Min/Max Duration: {data_ops['min_duration']:.3f}s / {data_ops['max_duration']:.3f}s\n"
            report += f"  Avg Throughput: {data_ops['avg_throughput']:,.0f} rows/sec\n"
            report += f"  Total Rows Processed: {data_ops['total_rows_processed']:,}\n\n"
        
        # フィルタ操作
        filter_ops = stats['filter_operations']
        if filter_ops['count'] > 0:
            report += f"Filter Operations ({filter_ops['count']} operations):\n"
            report += f"  Avg Duration: {filter_ops['avg_duration']:.3f}s\n"
            report += f"  Min/Max Duration: {filter_ops['min_duration']:.3f}s / {filter_ops['max_duration']:.3f}s\n"
            report += f"  Avg Throughput: {filter_ops['avg_throughput']:,.0f} rows/sec\n\n"
        
        # レンダリング操作
        render_ops = stats['rendering_operations']
        if render_ops['count'] > 0:
            report += f"Rendering Operations ({render_ops['count']} operations):\n"
            report += f"  Avg Duration: {render_ops['avg_duration']:.3f}s\n"
            report += f"  Min/Max Duration: {render_ops['min_duration']:.3f}s / {render_ops['max_duration']:.3f}s\n\n"
        
        # メモリ使用量
        memory = stats['memory_usage']
        if memory['peak_mb'] > 0:
            report += f"Memory Usage:\n"
            report += f"  Current: {memory['current_mb']:.1f} MB\n"
            report += f"  Peak: {memory['peak_mb']:.1f} MB\n"
            report += f"  Average: {memory['avg_mb']:.1f} MB\n\n"
        
        return report
    
    def clear_metrics(self):
        """メトリクスをクリア"""
        self.metrics = {
            'data_operations': [],
            'filter_operations': [],
            'rendering_operations': [],
            'memory_usage': [],
            'total_rows': 0,
            'filtered_rows': 0
        }


class VirtualTableBenchmark:
    """
    Virtual Table ベンチマーク実行クラス
    """
    
    @staticmethod
    def run_data_loading_benchmark(widget, data_sizes: List[int]) -> Dict[str, Any]:
        """データロードのベンチマーク"""
        results = {}
        
        for size in data_sizes:
            # テストデータ生成
            test_data = []
            for i in range(size):
                test_data.append({
                    'keyword': f'benchmark_keyword_{i}',
                    'rank': i % 10 + 1,
                    'title': f'Benchmark Title {i}',
                    'url': f'https://benchmark.com/{i}',
                    'snippet': f'Benchmark snippet for item {i}. This is a longer text to test rendering performance.',
                    'timestamp': f'2025-06-13 {i%24:02d}:{i%60:02d}:00'
                })
            
            # ベンチマーク実行
            start_time = time.time()
            widget.setData(test_data)
            duration = time.time() - start_time
            
            results[f'{size}_rows'] = {
                'duration': duration,
                'throughput': size / duration if duration > 0 else 0,
                'rows_per_second': size / duration if duration > 0 else 0
            }
            
            # クリーンアップ
            widget.clearData()
        
        return results
    
    @staticmethod
    def run_filter_performance_benchmark(widget, data_size: int, filter_terms: List[str]) -> Dict[str, Any]:
        """フィルタパフォーマンスのベンチマーク"""
        # テストデータ準備
        test_data = []
        for i in range(data_size):
            test_data.append({
                'keyword': f'filter_test_{i}',
                'rank': i % 10 + 1,
                'title': f'Filter Test Title {i}',
                'url': f'https://filtertest.com/{i}',
                'snippet': f'Filter test snippet {i}. Some items contain special keywords.',
                'timestamp': f'2025-06-13 10:00:00'
            })
        
        widget.setData(test_data)
        
        results = {}
        
        for term in filter_terms:
            start_time = time.time()
            widget.setFilter(term)
            duration = time.time() - start_time
            
            filtered_count = widget.getFilteredCount()
            
            results[f'filter_{term}'] = {
                'duration': duration,
                'filtered_count': filtered_count,
                'filter_ratio': filtered_count / data_size * 100 if data_size > 0 else 0,
                'throughput': data_size / duration if duration > 0 else 0
            }
            
            # フィルタクリア
            widget.clearFilter()
        
        return results
    
    @staticmethod
    def run_memory_usage_benchmark(widget, max_size: int, step_size: int) -> Dict[str, Any]:
        """メモリ使用量のベンチマーク"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        results = {}
        
        for size in range(step_size, max_size + 1, step_size):
            # テストデータ生成
            test_data = []
            for i in range(size):
                test_data.append({
                    'keyword': f'memory_test_{i}',
                    'rank': i % 10 + 1,
                    'title': f'Memory Test Title {i}',
                    'url': f'https://memorytest.com/{i}',
                    'snippet': f'Memory test snippet {i}. This text is used to test memory usage.',
                    'timestamp': f'2025-06-13 10:00:00'
                })
            
            # メモリ使用量測定
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            widget.setData(test_data)
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_diff = memory_after - memory_before
            
            results[f'{size}_rows'] = {
                'memory_before_mb': memory_before,
                'memory_after_mb': memory_after,
                'memory_diff_mb': memory_diff,
                'memory_per_row_kb': (memory_diff * 1024) / size if size > 0 else 0,
                'row_count': size
            }
        
        return results
    
    @staticmethod
    def generate_benchmark_report(results: Dict[str, Any]) -> str:
        """ベンチマーク結果レポートを生成"""
        report = "=== Virtual Table Benchmark Report ===\n\n"
        
        for benchmark_name, data in results.items():
            report += f"{benchmark_name}:\n"
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        report += f"  {key}:\n"
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, float):
                                report += f"    {sub_key}: {sub_value:.3f}\n"
                            else:
                                report += f"    {sub_key}: {sub_value}\n"
                    else:
                        if isinstance(value, float):
                            report += f"  {key}: {value:.3f}\n"
                        else:
                            report += f"  {key}: {value}\n"
            
            report += "\n"
        
        return report

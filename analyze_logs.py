#!/usr/bin/env python3
import csv

def analyze_translation_logs(csv_file):
    # 初始化统计变量
    success_true_count = 0
    success_false_count = 0
    success_true_times = []
    success_true_attempts = []
    success_true_costs = []
    success_false_times = []
    success_false_attempts = []
    success_false_costs = []
    timeout_count = 0
    error_count = 0

    # 读取CSV文件
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['success'] == 'True':
                success_true_count += 1
                success_true_times.append(float(row['processing_time']))
                success_true_attempts.append(int(row['attempts']))
                success_true_costs.append(float(row['api_cost_total']))
            else:
                success_false_count += 1
                success_false_times.append(float(row['processing_time']))
                success_false_attempts.append(int(row['attempts']))
                success_false_costs.append(float(row['api_cost_total']))
                
                # 分析失败原因
                if '超时' in row['error']:
                    timeout_count += 1
                elif '翻译出错' in row['error']:
                    error_count += 1

    total_count = success_true_count + success_false_count

    print('=== 翻译结果统计 ===')
    print(f'总记录数: {total_count}')
    print(f'Success=True 的记录数: {success_true_count}')
    print(f'Success=False 的记录数: {success_false_count}')
    print(f'成功率: {success_true_count/total_count*100:.1f}%')
    print()

    print('=== Success=True 的统计 ===')
    if success_true_count > 0:
        avg_time = sum(success_true_times) / len(success_true_times)
        avg_attempts = sum(success_true_attempts) / len(success_true_attempts)
        avg_cost = sum(success_true_costs) / len(success_true_costs)
        total_cost = sum(success_true_costs)
        
        print(f'平均处理时间: {avg_time:.2f} 秒')
        print(f'平均尝试次数: {avg_attempts:.2f} 次')
        print(f'平均API成本: ${avg_cost:.4f}')
        print(f'总API成本: ${total_cost:.4f}')
        print(f'处理时间范围: {min(success_true_times):.2f} - {max(success_true_times):.2f} 秒')
        print(f'尝试次数范围: {min(success_true_attempts)} - {max(success_true_attempts)} 次')
        print(f'API成本范围: ${min(success_true_costs):.4f} - ${max(success_true_costs):.4f}')
    else:
        print('没有成功的记录')

    print()
    print('=== Success=False 的统计 ===')
    if success_false_count > 0:
        avg_time = sum(success_false_times) / len(success_false_times)
        avg_attempts = sum(success_false_attempts) / len(success_false_attempts)
        avg_cost = sum(success_false_costs) / len(success_false_costs)
        total_cost = sum(success_false_costs)
        
        print(f'平均处理时间: {avg_time:.2f} 秒')
        print(f'平均尝试次数: {avg_attempts:.2f} 次')
        print(f'平均API成本: ${avg_cost:.4f}')
        print(f'总API成本: ${total_cost:.4f}')
        print(f'处理时间范围: {min(success_false_times):.2f} - {max(success_false_times):.2f} 秒')
        print(f'尝试次数范围: {min(success_false_attempts)} - {max(success_false_attempts)} 次')
        print(f'API成本范围: ${min(success_false_costs):.4f} - ${max(success_false_costs):.4f}')
        
        print()
        print('=== 失败原因分析 ===')
        print(f'超时失败: {timeout_count} 次')
        print(f'其他错误: {error_count} 次')
    else:
        print('没有失败的记录')

    print()
    print('=== 总体统计 ===')
    total_api_cost = sum(success_true_costs) + sum(success_false_costs)
    print(f'总API成本: ${total_api_cost:.4f}')
    print(f'平均每文件API成本: ${total_api_cost/total_count:.4f}')
    
    # 分析模型使用情况
    print()
    print('=== 模型使用统计 ===')
    if 'model' in df.columns:
        model_counts = df['model'].value_counts()
        for model, count in model_counts.items():
            percentage = count / total_count * 100
            print(f'{model}: {count} 次 ({percentage:.1f}%)')
    else:
        print('未找到模型信息字段')
    
    print()
    print('=== API价格说明 ===')
    print('使用GPT-4o最新价格:')
    print('- Input: $2.50 per 1M tokens')
    print('- Output: $10.00 per 1M tokens')
    print('注意: 当前成本估算基于脚本中的简单计算，实际成本可能因token使用量而异')

if __name__ == "__main__":
    csv_file = '/home/changdi/sactor/test/logs/translation_log_2025-09-30.csv'
    analyze_translation_logs(csv_file)

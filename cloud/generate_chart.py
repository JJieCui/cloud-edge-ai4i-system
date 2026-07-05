import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results", "tables", "cloud_review_log.csv")
result_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results", "figures")
os.makedirs(result_dir, exist_ok=True)

if os.path.exists(log_path):
    df = pd.read_csv(log_path)
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    consistency_counts = df['consistent_with_edge'].value_counts()
    axes[0].bar(['一致', '不一致'], consistency_counts.values, color=['#4CAF50', '#f44336'])
    axes[0].set_title('云边决策一致性统计')
    axes[0].set_ylabel('样本数量')
    for i, v in enumerate(consistency_counts.values):
        axes[0].text(i, v + 0.1, str(v), ha='center')
    
    latency_data = df[df['mode'] == 'real']['latency_ms'] / 1000
    axes[1].boxplot(latency_data, vert=False)
    axes[1].set_title('云端复核延迟分布（秒）')
    axes[1].set_xlabel('延迟（秒）')
    
    model_counts = df['used_model'].value_counts()
    axes[2].pie(model_counts.values, labels=model_counts.index, autopct='%1.1f%%', startangle=90)
    axes[2].set_title('模型使用分布')
    
    plt.tight_layout()
    chart_path = os.path.join(result_dir, "cloud_review_stats.png")
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存到: {chart_path}")
else:
    print(f"日志文件不存在: {log_path}")
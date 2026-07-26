import flwr as fl
import torch
import os
import csv
import multiprocessing
import time
from flower_client import SimpleMLP, run_single_client

# ===================== 全局配置 =====================
SERVER_ADDR = "127.0.0.1:8080"
ROUND_NUM = 5
CLIENT_NUM = 5
CSV_PATH = "results/tables/local_fed_compare.csv"
CLIENT_DATA_PATHS = [
    "data/ai4i/clients/client_1.csv",
    "data/ai4i/clients/client_2.csv",
    "data/ai4i/clients/client_3.csv",
    "data/ai4i/clients/client_4.csv",
    "data/ai4i/clients/client_5.csv",
]

# 写入实验结果到CSV
def write_exp_result(train_type, client_cnt, round_n, final_loss):
    file_exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["训练类型", "客户端数量", "训练轮数", "最终损失"])
        writer.writerow([train_type, client_cnt, round_n, round(final_loss, 6)])

# 服务端主逻辑
def start_server():
    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=CLIENT_NUM,
        min_evaluate_clients=CLIENT_NUM,
        min_available_clients=CLIENT_NUM
    )
    history = fl.server.start_server(
        server_address=SERVER_ADDR,
        config=fl.server.ServerConfig(num_rounds=ROUND_NUM),
        strategy=strategy
    )
    # 获取最后一轮损失
    final_loss = history.losses_distributed[-1][1]
    print(f"\n✅ 5客户端训练完成，最终损失：{final_loss:.6f}")
    # 写入表格
    write_exp_result("FedAvg联邦训练(client_1~5)", CLIENT_NUM, ROUND_NUM, final_loss)
    return final_loss

# 单客户端进程入口
def client_process(data_path):
    run_single_client(server_addr=SERVER_ADDR, data_csv=data_path)

if __name__ == "__main__":
    # Windows多进程必须加这句
    multiprocessing.freeze_support()

    print("===== 启动5客户端全自动FedAvg实验 =====")
    # 1. 启动服务端进程
    server_proc = multiprocessing.Process(target=start_server)
    server_proc.start()
    time.sleep(2)  # 等待服务端gRPC端口初始化完成

    # 2. 批量创建5个客户端子进程
    client_procs = []
    for path in CLIENT_DATA_PATHS:
        p = multiprocessing.Process(target=client_process, args=(path,))
        p.start()
        client_procs.append(p)
        time.sleep(0.3)

    # 3. 等待所有客户端执行完毕
    for p in client_procs:
        p.join()
    # 等待服务端收尾
    server_proc.join()
    print("\n🎉 全部实验流程结束，结果已存入", CSV_PATH)

import flwr as fl

def get_fedavg_strategy(min_client_num=5):
    return fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=min_client_num,
        min_evaluate_clients=min_client_num,
        min_available_clients=min_client_num
    )

def run_server():
    strategy = get_fedavg_strategy(5)
    # 仅执行训练，移除所有参数保存逻辑，规避版本API报错
    history = fl.server.start_server(
        server_address="127.0.0.1:8080",
        config=fl.server.ServerConfig(num_rounds=5),
        strategy=strategy
    )
    # 打印5轮损失，方便复制进实验表格
    print("=====5客户端FedAvg每轮损失汇总=====")
    for idx, loss in enumerate(history.losses_distributed):
        print(f"round {idx+1}: {loss[1]}")

if __name__ == "__main__":
    run_server()
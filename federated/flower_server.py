# 本科生2：Flower 联邦学习服务器
# TODO: 启动 FedAvg server
import flwr as fl

def get_fedavg_strategy(min_client_num=2):
    return fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=min_client_num,
        min_evaluate_clients=min_client_num,
        min_available_clients=min_client_num
    )

def run_server():
    # 当前基础实验使用2个客户端，后续改为5只需把入参改成5
    strategy = get_fedavg_strategy(2)
    fl.server.start_server(
        server_address="127.0.0.1:8080",
        config=fl.server.ServerConfig(num_rounds=5),
        strategy=strategy
    )

if __name__ == "__main__":
    run_server()

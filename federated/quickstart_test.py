import flwr as fl
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# 简单分类网络（适配后续AI4I故障分类）
class SimpleMLP(nn.Module):
    def __init__(self, input_dim=10, hidden_dim=32, output_dim=2):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )

    def forward(self, x):
        return self.layers(x)

# 模拟本地数据集
def get_dummy_data():
    X = torch.randn(100, 10)
    y = torch.randint(0, 2, (100,))
    return TensorDataset(X, y)

# Flower客户端定义
class FlowerClient(fl.client.NumPyClient):
    def __init__(self):
        self.model = SimpleMLP()
        self.dataset = get_dummy_data()
        self.loader = DataLoader(self.dataset, batch_size=10)
        self.optimizer = optim.SGD(self.model.parameters(), lr=0.01)
        self.criterion = nn.CrossEntropyLoss()

    def get_parameters(self, config):
        # 修复点：先detach剥离梯度再转numpy
        return [val.detach().cpu().numpy() for val in self.model.parameters()]

    def set_parameters(self, params):
        for param, new_param in zip(self.model.parameters(), params):
            param.data = torch.tensor(new_param)

    def fit(self, params, config):
        self.set_parameters(params)
        self.model.train()
        for epoch in range(3):
            for batch_x, batch_y in self.loader:
                self.optimizer.zero_grad()
                pred = self.model(batch_x)
                loss = self.criterion(pred, batch_y)
                loss.backward()
                self.optimizer.step()
        return self.get_parameters(config), len(self.dataset), {}

    def evaluate(self, params, config):
        self.set_parameters(params)
        self.model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for batch_x, batch_y in self.loader:
                pred = self.model(batch_x)
                _, labels = torch.max(pred, 1)
                total += batch_y.size(0)
                correct += (labels == batch_y).sum().item()
        acc = correct / total
        return 0.1, len(self.dataset), {"accuracy": acc}

# 服务端策略
def get_strategy():
    return fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=2,
        min_evaluate_clients=2,
        min_available_clients=2
    )

# 启动服务端
def run_server():
    fl.server.start_server(
        server_address="127.0.0.1:8080",
        config=fl.server.ServerConfig(num_rounds=5),
        strategy=get_strategy()
    )

# 启动单个客户端
def run_client():
    client = FlowerClient().to_client()
    fl.client.start_client(server_address="127.0.0.1:8080", client=client)

if __name__ == "__main__":
    import sys
    if sys.argv[1] == "server":
        run_server()
    elif sys.argv[1] == "client":
        run_client()
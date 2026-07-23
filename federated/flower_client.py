# 本科生2：Flower 联邦学习客户端
# TODO: 每个 client 读取自己的 AI4I 数据并参与训练
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
from sklearn.preprocessing import StandardScaler
import flwr as fl

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

def load_ai4i_client(csv_path):
    df = pd.read_csv(csv_path)
    drop_cols = ["UDI", "Product ID", "Type", "Machine failure", "client_id"]
    X = df.drop(columns=drop_cols).values
    y = df["Machine failure"].values
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    return TensorDataset(
        torch.tensor(X, dtype=torch.float32),
        torch.tensor(y, dtype=torch.long)
    )

class FlowerClient(fl.client.NumPyClient):
    def __init__(self, csv_path):
        self.model = SimpleMLP()
        self.dataset = load_ai4i_client(csv_path)
        self.loader = DataLoader(self.dataset, batch_size=16, shuffle=True)
        self.optimizer = optim.SGD(self.model.parameters(), lr=0.01)
        self.criterion = nn.CrossEntropyLoss()

    def get_parameters(self, config):
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
        loss_sum = 0
        with torch.no_grad():
            for batch_x, batch_y in self.loader:
                pred = self.model(batch_x)
                loss = self.criterion(pred, batch_y)
                loss_sum += loss.item() * batch_x.shape[0]
                _, labels = torch.max(pred, 1)
                total += batch_x.size(0)
                correct += (labels == batch_y).sum().item()
        acc = correct / total
        avg_loss = loss_sum / total
        return avg_loss, len(self.dataset), {"accuracy": acc}

if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1]
    client = FlowerClient(csv_path).to_client()
    fl.client.start_client(server_address="127.0.0.1:8080", client=client)

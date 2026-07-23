import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
from sklearn.preprocessing import StandardScaler

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

if __name__ == "__main__":
    dataset = load_ai4i_client("data/ai4i/clients/client_1.csv")
    loader = DataLoader(dataset, batch_size=16, shuffle=True)
    model = SimpleMLP()
    optimizer = optim.SGD(model.parameters(), lr=0.01)
    criterion = nn.CrossEntropyLoss()

    # 和联邦训练保持一致：总共5轮，每轮内部迭代3个epoch
    for r in range(5):
        model.train()
        for _ in range(3):
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                pred = model(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()

        # 评估
        model.eval()
        total_loss = 0
        correct = 0
        total = 0
        with torch.no_grad():
            for batch_x, batch_y in loader:
                pred = model(batch_x)
                loss = criterion(pred, batch_y)
                total_loss += loss.item() * batch_x.shape[0]
                _, label_pred = torch.max(pred, 1)
                total += batch_x.size(0)
                correct += (label_pred == batch_y).sum().item()
        avg_loss = total_loss / total
        acc = correct / total
        print(f"本地训练 第{r+1}轮 | loss={avg_loss:.6f} | acc={acc:.4f}")

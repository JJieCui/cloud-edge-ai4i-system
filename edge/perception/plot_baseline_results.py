from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = PROJECT_ROOT / "results" / "tables" / "perception_baseline.csv"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures"

MODEL_ORDER = ["LogisticRegression", "RandomForest", "MLP"]
METRICS = {
    "accuracy": {
        "title": "AI4I Edge Perception Accuracy by Model and Client",
        "ylabel": "Accuracy",
        "filename": "perception_accuracy_by_model.png",
    },
    "precision": {
        "title": "AI4I Edge Perception Precision by Model and Client",
        "ylabel": "Precision",
        "filename": "perception_precision_by_model.png",
    },
    "recall": {
        "title": "AI4I Edge Perception Recall by Model and Client",
        "ylabel": "Recall",
        "filename": "perception_recall_by_model.png",
    },
    "f1": {
        "title": "AI4I Edge Perception F1 by Model and Client",
        "ylabel": "F1",
        "filename": "perception_f1_by_model.png",
    },
}


def load_baseline_results() -> pd.DataFrame:
    if not BASELINE_PATH.exists():
        raise FileNotFoundError(
            f"Missing baseline result table: {BASELINE_PATH}\n"
            "Please run first: python edge/perception/train_local_model.py"
        )

    df = pd.read_csv(BASELINE_PATH)
    required_columns = {"client_id", "model", *METRICS.keys()}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Baseline table is missing required columns: {missing_columns}")

    return df


def build_metric_pivot(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    pivot_df = df.pivot(index="client_id", columns="model", values=metric).sort_index()
    ordered_models = [model for model in MODEL_ORDER if model in pivot_df.columns]
    return pivot_df[ordered_models]


def plot_metric_with_matplotlib(pivot_df: pd.DataFrame, metric_config: dict[str, str], output_path: Path) -> None:
    ax = pivot_df.plot(kind="bar", figsize=(11, 6.5), width=0.78)
    ax.set_title(metric_config["title"])
    ax.set_xlabel("Client ID")
    ax.set_ylabel(metric_config["ylabel"])
    ax.set_ylim(0, 1.08)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(title="Model", loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)

    for container in ax.containers:
        ax.bar_label(container, fmt="%.3f", padding=3, fontsize=8)

    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def load_font(size: int) -> ImageFont.ImageFont:
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def plot_metric_with_pillow(pivot_df: pd.DataFrame, metric_config: dict[str, str], output_path: Path) -> None:
    width, height = 1320, 780
    margin_left, margin_right = 115, 70
    margin_top, margin_bottom = 95, 150
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(30)
    label_font = load_font(20)
    tick_font = load_font(16)
    value_font = load_font(14)

    title = metric_config["title"]
    title_width, _ = text_size(draw, title, title_font)
    draw.text(((width - title_width) / 2, 30), title, fill="#111827", font=title_font)

    x0, y0 = margin_left, height - margin_bottom
    x1, y1 = width - margin_right, margin_top
    draw.line((x0, y0, x1, y0), fill="#111827", width=2)
    draw.line((x0, y0, x0, y1), fill="#111827", width=2)

    for tick in range(0, 6):
        value = tick / 5
        y = y0 - (value / 1.08) * plot_height
        draw.line((x0, y, x1, y), fill="#e5e7eb", width=1)
        tick_text = f"{value:.1f}"
        tick_width, tick_height = text_size(draw, tick_text, tick_font)
        draw.text((x0 - tick_width - 12, y - tick_height / 2), tick_text, fill="#374151", font=tick_font)

    clients = list(pivot_df.index)
    models = list(pivot_df.columns)
    colors = ["#2563eb", "#16a34a", "#dc2626"]
    group_width = plot_width / max(len(clients), 1)
    bar_width = group_width * 0.70 / max(len(models), 1)

    for client_idx, client_id in enumerate(clients):
        group_start = x0 + client_idx * group_width + group_width * 0.15
        for model_idx, model in enumerate(models):
            value = float(pivot_df.loc[client_id, model])
            bar_left = group_start + model_idx * bar_width
            bar_right = bar_left + bar_width * 0.82
            bar_top = y0 - (value / 1.08) * plot_height
            draw.rectangle((bar_left, bar_top, bar_right, y0), fill=colors[model_idx % len(colors)])

            label = f"{value:.3f}"
            label_width, label_height = text_size(draw, label, value_font)
            label_x = (bar_left + bar_right) / 2 - label_width / 2
            label_y = max(y1 + 4, bar_top - label_height - 6)
            draw.text((label_x, label_y), label, fill="#111827", font=value_font)

        tick_width, tick_height = text_size(draw, str(client_id), tick_font)
        tick_x = x0 + client_idx * group_width + group_width / 2 - tick_width / 2
        draw.text((tick_x, y0 + 18), str(client_id), fill="#374151", font=tick_font)

    x_label = "Client ID"
    x_label_width, _ = text_size(draw, x_label, label_font)
    draw.text((x0 + plot_width / 2 - x_label_width / 2, height - 55), x_label, fill="#111827", font=label_font)
    draw.text((20, margin_top + plot_height / 2 - 12), metric_config["ylabel"], fill="#111827", font=label_font)

    legend_y = height - 105
    legend_total_width = 0
    legend_items = []
    for model_idx, model in enumerate(models):
        text_width, text_height = text_size(draw, model, tick_font)
        item_width = 26 + text_width + 34
        legend_items.append((model_idx, model, item_width, text_height))
        legend_total_width += item_width

    legend_x = x0 + plot_width / 2 - legend_total_width / 2
    for model_idx, model, item_width, _ in legend_items:
        draw.rectangle((legend_x, legend_y + 2, legend_x + 18, legend_y + 20), fill=colors[model_idx % len(colors)])
        draw.text((legend_x + 26, legend_y), model, fill="#111827", font=tick_font)
        legend_x += item_width

    image.save(output_path)


def plot_metric(df: pd.DataFrame, metric: str) -> Path:
    metric_config = METRICS[metric]
    pivot_df = build_metric_pivot(df, metric)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = FIGURE_DIR / metric_config["filename"]

    if plt is not None:
        plot_metric_with_matplotlib(pivot_df, metric_config, output_path)
    else:
        plot_metric_with_pillow(pivot_df, metric_config, output_path)

    return output_path


def main() -> None:
    baseline_df = load_baseline_results()
    output_paths = [plot_metric(baseline_df, metric) for metric in METRICS]

    print("Generated baseline figures:")
    for output_path in output_paths:
        print(output_path)


if __name__ == "__main__":
    main()

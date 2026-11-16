import numpy as np
import matplotlib.pyplot as plt


# Baseline results

# ---------------- LEMMA-RCA ----------------
lemma = {
    "BARO": {"PR@1": 1.0, "PR@5": 1.0, "PR@10": 1.0, "MRR": 1.0, "MAP@10": 1.0},
    "RCD": {"PR@1": 0.0, "PR@5": 0.0, "PR@10": 0.0, "MRR": 0.0, "MAP@10": 0.0},
    "ε-Diagnosis": {"PR@1": 0.0, "PR@5": 1.0, "PR@10": 1.0, "MRR": 0.500, "MAP@10": 0.900},
    "CIRCA": {"PR@1": 0.0, "PR@5": 0.0, "PR@10": 0.0, "MRR": 0.091, "MAP@10": 0.0}
    }

# ---------------- RCAEval ----------------
rcaeval = {
    "BARO": {"PR@1": 0.0, "PR@5": 1.0, "PR@10": 1.0, "MRR": 0.200, "MAP@10": 0.600},
    "RCD": {"PR@1": 0.0, "PR@5": 0.0, "PR@10": 0.0, "MRR": 0.0, "MAP@10": 0.0},
    "ε-Diagnosis": {"PR@1": 0.0, "PR@5": 1.0, "PR@10": 1.0, "MRR": 0.333, "MAP@10": 0.800}
    }

# Function for plotting baseline results
def plot_baseline(data, dataset_name, output_file):
    models = list(data.keys())
    metrics = ["PR@1", "PR@5", "PR@10", "MRR", "MAP@10"]
    x = np.arange(len(models))
    width = 0.15
    fig, ax = plt.subplots(figsize=(10, 5.5))

    colors = [
        "#4C78A8",  # blue
        "#F2A541",  # orange
        "#8F77B5",  # purple
        "#7A7A7A",  # gray
        "#64B5CD"   # cyan
    ]

    for i, metric in enumerate(metrics):
        values = [data[model][metric] for model in models]
        positions = x + (i - (len(metrics) - 1) / 2) * width
        bars = ax.bar(positions, values, width, label=metric, color=colors[i])

        # Add numerical values above bars
        for bar, value in zip(bars, values):
            if value > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, value + 0.025, f"{value:.3f}", ha="center", va="bottom", fontsize=8, rotation=90)

    ax.set_xlabel("RCA Method")
    ax.set_ylabel("Metric Value")
    ax.set_title(f"Baseline RCA Performance on {dataset_name}")
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylim(0, 1.15)
    ax.legend(title="Metric", ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig(output_file + ".png", dpi=300, bbox_inches="tight")

    # Vector PDF
    plt.savefig(output_file + ".pdf", bbox_inches="tight")
    plt.show()

# Generate figures
plot_baseline(lemma, "LEMMA-RCA", "lemma_baseline")
plot_baseline(rcaeval, "RCAEval", "rcaeval_baseline")
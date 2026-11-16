import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

OUTPUT_DIR = "../results/rcaeval_figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Common x-axis.
rates = np.array([0, 10, 30, 50, 70, 90])
techniques = ["Adjacent Swap", "Case Change", "Char Delete", "Char Insert", "Keyboard Typo", "Random", "Sorted", "Token Insert", "Token Replace",]
models = ["BARO", "RCD", "Epsilon-Diagnosis"]

# Experimental results
# Structure: results[fuzzing technique][model][metric]
results = {

    # --------------------------------------------------------
    # 1. Adjacent Swap
    # --------------------------------------------------------
    "Adjacent Swap": {
        "BARO": {
            "MRR":   [0.200, 0.200, 0.200, 0.200, 0.200, 0.200],
            "PR@5":  [1, 1, 1, 1, 1, 1],
            "MAP@5": [0.200, 0.200, 0.200, 0.200, 0.200, 0.200],
        },

        "RCD": {
            "MRR":   [0, 0, 0, 0, 0, 0],
            "PR@5":  [0, 0, 0, 0, 0, 0],
            "MAP@5": [0, 0, 0, 0, 0, 0],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.333, 0.500, 0.500, 0.333, 0.500],
            "PR@5":  [1, 1, 1, 1, 1, 1],
            "MAP@5": [0.600, 0.600, 0.800, 0.800, 0.600, 0.800],
        },
    },


    # --------------------------------------------------------
    # 2. Case Change
    # --------------------------------------------------------
    "Case Change": {
        "BARO": {
            "MRR":   [0.200] * 6,
            "PR@5":  [1] * 6,
            "MAP@5": [0.200] * 6,
        },

        "RCD": {
            "MRR":   [0, 0.333, 0, 0.333, 0, 0],
            "PR@5":  [0, 1, 0, 1, 0, 0],
            "MAP@5": [0, 0.600, 0, 0.600, 0, 0],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.500, 0.500, 0.333, 0.500, 0.333],
            "PR@5":  [1, 1, 1, 1, 1, 1],
            "MAP@5": [0.600, 0.800, 0.800, 0.600, 0.800, 0.600],
        },
    },


    # --------------------------------------------------------
    # 3. Char Delete
    # --------------------------------------------------------
    "Char Delete": {
        "BARO": {
            "MRR":   [0.200] * 6,
            "PR@5":  [1] * 6,
            "MAP@5": [0.200] * 6,
        },

        "RCD": {
            "MRR":   [0] * 6,
            "PR@5":  [0] * 6,
            "MAP@5": [0] * 6,
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.500, 0.500, 0.500, 0.500, 0.500],
            "PR@5":  [1] * 6,
            "MAP@5": [0.600, 0.800, 0.800, 0.800, 0.800, 0.800],
        },
    },


    # --------------------------------------------------------
    # 4. Char Insert
    # --------------------------------------------------------
    "Char Insert": {
        "BARO": {
            "MRR":   [0.200] * 6,
            "PR@5":  [1] * 6,
            "MAP@5": [0.200] * 6,
        },

        "RCD": {
            "MRR":   [0] * 6,
            "PR@5":  [0] * 6,
            "MAP@5": [0] * 6,
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.500, 0.500, 0.500, 0.500, 0.500],
            "PR@5":  [1] * 6,
            "MAP@5": [0.600, 0.800, 0.800, 0.800, 0.800, 0.800],
        },
    },


    # --------------------------------------------------------
    # 5. Keyboard Typo
    # --------------------------------------------------------
    "Keyboard Typo": {
        "BARO": {
            "MRR":   [0.200] * 6,
            "PR@5":  [1] * 6,
            "MAP@5": [0.200] * 6,
        },

        "RCD": {
            "MRR":   [0] * 6,
            "PR@5":  [0] * 6,
            "MAP@5": [0] * 6,
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.333, 0.500, 0.500, 0.500, 0.333],
            "PR@5":  [1] * 6,
            "MAP@5": [0.600, 0.600, 0.800, 0.800, 0.800, 0.600],
        },
    },


    # --------------------------------------------------------
    # 6. Random
    # --------------------------------------------------------
    "Random": {
        "BARO": {
            "MRR":   [0.200] * 6,
            "PR@5":  [1] * 6,
            "MAP@5": [0.200] * 6,
        },

        "RCD": {
            "MRR":   [0] * 6,
            "PR@5":  [0] * 6,
            "MAP@5": [0] * 6,
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.500, 0.500, 0.333, 0.500, 0.500],
            "PR@5":  [1] * 6,
            "MAP@5": [0.600, 0.800, 0.800, 0.600, 0.800, 0.800],
        },
    },


    # --------------------------------------------------------
    # 7. Sorted
    # --------------------------------------------------------
    "Sorted": {
        "BARO": {
            "MRR":   [0.200] * 6,
            "PR@5":  [1] * 6,
            "MAP@5": [0.200] * 6,
        },

        "RCD": {
            "MRR":   [0] * 6,
            "PR@5":  [0] * 6,
            "MAP@5": [0] * 6,
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.500, 0.500, 0.333, 0.333, 0.500],
            "PR@5":  [1] * 6,
            "MAP@5": [0.600, 0.800, 0.800, 0.600, 0.600, 0.800],
        },
    },


    # --------------------------------------------------------
    # 8. Token Insert
    # --------------------------------------------------------
    "Token Insert": {
        "BARO": {
            "MRR":   [0.200] * 6,
            "PR@5":  [1] * 6,
            "MAP@5": [0.200] * 6,
        },

        "RCD": {
            "MRR":   [0] * 6,
            "PR@5":  [0] * 6,
            "MAP@5": [0] * 6,
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.333, 0.333, 0.333, 0.333, 0.500],
            "PR@5":  [1] * 6,
            "MAP@5": [0.600, 0.600, 0.600, 0.600, 0.600, 0.800],
        },
    },


    # --------------------------------------------------------
    # 9. Token Replace
    # --------------------------------------------------------
    "Token Replace": {
        "BARO": {
            "MRR":   [0.200] * 6,
            "PR@5":  [1] * 6,
            "MAP@5": [0.200] * 6,
        },

        "RCD": {
            "MRR":   [0] * 6,
            "PR@5":  [0] * 6,
            "MAP@5": [0] * 6,
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.333, 0.500, 0.333, 0.500, 0.333, 0.333],
            "PR@5":  [1] * 6,
            "MAP@5": [0.600, 0.800, 0.600, 0.800, 0.600, 0.600],
        },
    },
}

def save_figure(fig, filename):
    pdf_path = os.path.join(OUTPUT_DIR, filename + ".pdf")
    png_path = os.path.join(OUTPUT_DIR, filename + ".png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")

# Figure 1-3:
# One figure for each metric.
# Each figure contains three panels:
# BARO | RCD | Epsilon-Diagnosis
def plot_metric_all_techniques(metric, filename):
    fig, axes = plt.subplots(1, 3, figsize=(17, 5), sharex=True)
    for ax, model in zip(axes, models):
        for technique in techniques:
            values = results[technique][model][metric]
            ax.plot(rates, values, marker="o", linewidth=1.8, markersize=4, label=technique)

        ax.set_title(model, fontsize=13)
        ax.set_xlabel("Perturbation Rate (%)")
        ax.set_xticks(rates)
        ax.grid(True, alpha=0.3)

        # Show BARO MRR y-axis with 3 decimal places
        if metric == "MRR" and model == "BARO":
            ax.yaxis.set_major_formatter(FormatStrFormatter('%.3f'))

    axes[0].set_ylabel(metric)
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.12))

    fig.suptitle(f"{metric} under Increasing Log Perturbation\nRCAEval: re2tt_ts-order-service_delay_2", fontsize=15)
    fig.tight_layout()
    save_figure(fig, filename)
    plt.close(fig)

plot_metric_all_techniques("MRR", "01_mrr_by_fuzzing")
plot_metric_all_techniques("MAP@5", "02_map5_by_fuzzing")
plot_metric_all_techniques("PR@5", "03_pr5_by_fuzzing")

# Figure 4: Epsilon-Diagnosis MRR Heatmap
epsilon_mrr = np.array([results[t]["Epsilon-Diagnosis"]["MRR"]for t in techniques])
fig, ax = plt.subplots(figsize=(9, 7))
im = ax.imshow(epsilon_mrr, aspect="auto", vmin=0, vmax=1)
ax.set_xticks(np.arange(len(rates)))
ax.set_xticklabels([f"{r}%" for r in rates])
ax.set_yticks(np.arange(len(techniques)))
ax.set_yticklabels(techniques)
ax.set_xlabel("Perturbation Rate")
ax.set_ylabel("Fuzzing Technique")
ax.set_title("MRR of Epsilon-Diagnosis under Log Perturbation\n RCAEval: re2tt_ts-order-service_delay_2")

# Put values inside cells
for i in range(len(techniques)):
    for j in range(len(rates)):
        ax.text(j, i, f"{epsilon_mrr[i, j]:.3f}", ha="center", va="center")

cbar = fig.colorbar(im, ax=ax)
cbar.set_label("MRR")
fig.tight_layout()
save_figure(fig, "04_epsilon_mrr_heatmap")
plt.close(fig)

# Figure 5: Delta MRR relative to baseline
# ΔMRR = MRR_fuzzed - MRR_original
# 0% is excluded because its delta is always zero.
delta_epsilon = (epsilon_mrr[:, 1:] - epsilon_mrr[:, [0]])
fig, ax = plt.subplots(figsize=(9, 7))
max_abs = np.max(np.abs(delta_epsilon))

# Avoid zero range
if max_abs == 0:
    max_abs = 1

im = ax.imshow(delta_epsilon, aspect="auto", vmin=-max_abs, vmax=max_abs)
ax.set_xticks(np.arange(len(rates[1:])))
ax.set_xticklabels([f"{r}%" for r in rates[1:]])
ax.set_yticks(np.arange(len(techniques)))
ax.set_yticklabels(techniques)
ax.set_xlabel("Perturbation Rate")
ax.set_ylabel("Fuzzing Technique")
ax.set_title("Change in MRR Relative to the Unfuzzed Baseline\nEpsilon-Diagnosis")

for i in range(len(techniques)):
    for j in range(len(rates[1:])):
        value = delta_epsilon[i, j]
        ax.text(j, i, f"{value:+.3f}", ha="center", va="center")

cbar = fig.colorbar(im, ax=ax)
cbar.set_label(r"$\Delta$MRR")
fig.tight_layout()
save_figure(fig, "05_delta_mrr_heatmap_epsilon")
plt.close(fig)

# Figure 6: Average MRR across all fuzzing techniques
# This is a descriptive average across nine perturbation techniques for this one dataset.
fig, ax = plt.subplots(figsize=(9, 6))

for model in models:
    mean_values = []
    for rate_index in range(len(rates)):
        values = [results[t][model]["MRR"][rate_index] for t in techniques]
        mean_values.append(np.mean(values))
    ax.plot(rates, mean_values, marker="o", linewidth=2, markersize=6, label=model)

ax.set_xlabel("Perturbation Rate (%)")
ax.set_ylabel("Mean MRR")
ax.set_xticks(rates)
ax.set_ylim(bottom=0)
ax.grid(True, alpha=0.3)
ax.legend()
ax.set_title("Mean MRR across Log Fuzzing Techniques\n RCAEval: re2tt_ts-order-service_delay_2")
fig.tight_layout()
save_figure(fig, "06_mrr_model_comparison")
plt.close(fig)

print()
print("=" * 10)
print("All figures generated successfully.")
print(f"Output directory: {OUTPUT_DIR}")
print("=" * 10)
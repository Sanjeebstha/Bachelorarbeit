import os
import numpy as np
import matplotlib.pyplot as plt


OUTPUT_DIR = "../results/lemma_20220606_figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Common x-axis.
# Missing measurements are represented by np.nan.
rates = np.array([0, 30, 50, 70])

techniques = ["Adjacent Swap", "Char Delete", "Keyboard Typo", "Random", "Sorted", "Token Delete", "Token Insert"]
models = ["BARO", "RCD", "Epsilon-Diagnosis", "CIRCA"]

# Experimental results
# Structure: results[fuzzing technique][model][metric]
# np.nan = no result was provided for that perturbation rate
results = {

    # ========================================================
    # 1. Adjacent Swap
    # ========================================================

    "Adjacent Swap": {

        "BARO": {
            "MRR":   [1.000, 1.000, 1.000, 1.000],
            "PR@5":  [1, 1, 1, 1],
            "MAP@5": [1.000, 1.000, 1.000, 1.000],
        },

        "RCD": {
            "MRR":   [0, 0, 0, 0],
            "PR@5":  [0, 0, 0, 0],
            "MAP@5": [0, 0, 0, 0],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.500, 0.071, 0.067, 0.062],
            "PR@5":  [1, 0, 0, 0],
            "MAP@5": [0.800, 0, 0, 0],
        },

        "CIRCA": {
            "MRR":   [0.091, 0.091, 0.083, 0.083],
            "PR@5":  [0, 0, 0, 0],
            "MAP@5": [0, 0, 0, 0],
        },
    },


    # ========================================================
    # 2. Char Delete
    # ========================================================

    "Char Delete": {

        "BARO": {
            "MRR":   [1.000, 1.000, 1.000, np.nan],
            "PR@5":  [1, 1, 1, np.nan],
            "MAP@5": [1.000, 1.000, 1.000, np.nan],
        },

        "RCD": {
            "MRR":   [0, 0, 0, np.nan],
            "PR@5":  [0, 0, 0, np.nan],
            "MAP@5": [0, 0, 0, np.nan],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.500, 0.062, 0.071, np.nan],
            "PR@5":  [1, 0, 0, np.nan],
            "MAP@5": [0.800, 0, 0, np.nan],
        },

        "CIRCA": {
            "MRR":   [0.091, 0.200, 0.091, np.nan],
            "PR@5":  [0, 1, 0, np.nan],
            "MAP@5": [0, 0.200, 0, np.nan],
        },
    },


    # ========================================================
    # 3. Keyboard Typo
    # ========================================================

    "Keyboard Typo": {

        "BARO": {
            "MRR":   [1.000, 1.000, 1.000, np.nan],
            "PR@5":  [1, 1, 1, np.nan],
            "MAP@5": [1.000, 1.000, 1.000, np.nan],
        },

        "RCD": {
            "MRR":   [0, 0, 0, np.nan],
            "PR@5":  [0, 0, 0, np.nan],
            "MAP@5": [0, 0, 0, np.nan],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.500, 0.071, 0.062, np.nan],
            "PR@5":  [1, 0, 0, np.nan],
            "MAP@5": [0.800, 0, 0, np.nan],
        },

        "CIRCA": {
            "MRR":   [0.091, 0.071, 0.062, np.nan],
            "PR@5":  [0, 0, 0, np.nan],
            "MAP@5": [0, 0, 0, np.nan],
        },
    },


    # ========================================================
    # 4. Random
    # ========================================================

    "Random": {

        "BARO": {
            "MRR":   [1.000, 1.000, 1.000, 1.000],
            "PR@5":  [1, 1, 1, 1],
            "MAP@5": [1.000, 1.000, 1.000, 1.000],
        },

        "RCD": {
            "MRR":   [0, 0, 0, 0],
            "PR@5":  [0, 0, 0, 0],
            "MAP@5": [0, 0, 0, 0],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.500, 0.062, 0.059, 0.062],
            "PR@5":  [1, 0, 0, 0],
            "MAP@5": [0.800, 0, 0, 0],
        },

        "CIRCA": {
            "MRR":   [0.091, 0.062, 0.077, 0.071],
            "PR@5":  [0, 0, 0, 0],
            "MAP@5": [0, 0, 0, 0],
        },
    },


    # ========================================================
    # 5. Sorted
    # ========================================================

    "Sorted": {

        "BARO": {
            "MRR":   [1.000, 1.000, 1.000, 1.000],
            "PR@5":  [1, 1, 1, 1],
            "MAP@5": [1.000, 1.000, 1.000, 1.000],
        },

        "RCD": {
            "MRR":   [0, 0, 0, 0],
            "PR@5":  [0, 0, 0, 0],
            "MAP@5": [0, 0, 0, 0],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.500, 0.067, 0.067, 0.071],
            "PR@5":  [1, 0, 0, 0],
            "MAP@5": [0.800, 0, 0, 0],
        },

        "CIRCA": {
            "MRR":   [0.091, 0, 0.067, 0.111],
            "PR@5":  [0, 0, 0, 0],
            "MAP@5": [0, 0, 0, 0],
        },
    },


    # ========================================================
    # 6. Token Delete
    # ========================================================

    "Token Delete": {

        "BARO": {
            "MRR":   [1.000, 1.000, 1.000, np.nan],
            "PR@5":  [1, 1, 1, np.nan],
            "MAP@5": [1.000, 1.000, 1.000, np.nan],
        },

        "RCD": {
            "MRR":   [0, 0.200, 0, np.nan],
            "PR@5":  [0, 1, 0, np.nan],
            "MAP@5": [0, 0.200, 0, np.nan],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.500, 0.100, 0.100, np.nan],
            "PR@5":  [1, 0, 0, np.nan],
            "MAP@5": [0.800, 0, 0, np.nan],
        },

        "CIRCA": {
            "MRR":   [0.091, 0.083, 0.091, np.nan],
            "PR@5":  [0, 0, 0, np.nan],
            "MAP@5": [0, 0, 0, np.nan],
        },
    },


    # ========================================================
    # 7. Token Insert
    # ========================================================

    "Token Insert": {

        "BARO": {
            "MRR":   [1.000, 1.000, 1.000, 1.000],
            "PR@5":  [1, 1, 1, 1],
            "MAP@5": [1.000, 1.000, 1.000, 1.000],
        },

        "RCD": {
            "MRR":   [0, 0.250, 0, 0.250],
            "PR@5":  [0, 1, 0, 1],
            "MAP@5": [0, 0.400, 0, 0.400],
        },

        "Epsilon-Diagnosis": {
            "MRR":   [0.500, 0.077, 0.083, 0.077],
            "PR@5":  [1, 0, 0, 0],
            "MAP@5": [0.800, 0, 0, 0],
        },

        "CIRCA": {
            "MRR":   [0.091, 0.077, 0.077, 0.077],
            "PR@5":  [0, 0, 0, 0],
            "MAP@5": [0, 0, 0, 0],
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


# Figures 1-3:
# One figure for each metric.
# Each figure contains four panels:
# BARO | RCD | Epsilon-Diagnosis | CIRCA
def plot_metric_all_techniques(metric, filename):
    fig, axes = plt.subplots(1, 4, figsize=(21, 5), sharex=True)
    for ax, model in zip(axes, models):
        for technique in techniques:
            values = results[technique][model][metric]
            ax.plot(rates, values, marker="o", linewidth=1.8, markersize=4, label=technique)
        ax.set_title(model, fontsize=13)
        ax.set_xlabel("Perturbation Rate (%)")
        ax.set_xticks(rates)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel(metric)

    # Common legend
    handles, labels = axes[-1].get_legend_handles_labels()

    fig.legend(handles, labels, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.15))
    fig.suptitle(f"{metric} under Increasing Log Perturbation\nLEMMA-RCA: 20220606", fontsize=15)
    fig.tight_layout()
    save_figure(fig, filename)
    plt.close(fig)

plot_metric_all_techniques("MRR", "01_mrr_by_fuzzing")
plot_metric_all_techniques("MAP@5", "02_map5_by_fuzzing")
plot_metric_all_techniques("PR@5", "03_pr5_by_fuzzing")

# Figure 4:
# MRR heatmap for Epsilon-Diagnosis
epsilon_mrr = np.array([results[t]["Epsilon-Diagnosis"]["MRR"] for t in techniques])

fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(epsilon_mrr, aspect="auto", vmin=0, vmax=1)

ax.set_xticks(np.arange(len(rates)))
ax.set_xticklabels([f"{r}%" for r in rates])
ax.set_yticks(np.arange(len(techniques)))
ax.set_yticklabels(techniques)
ax.set_xlabel("Perturbation Rate")
ax.set_ylabel("Fuzzing Technique")
ax.set_title("MRR of Epsilon-Diagnosis under Log Perturbation\nLEMMA-RCA: 20220606")

# Values inside cells
for i in range(len(techniques)):
    for j in range(len(rates)):
        value = epsilon_mrr[i, j]
        if not np.isnan(value):
            ax.text(j, i, f"{value:.3f}", ha="center", va="center")

cbar = fig.colorbar(im, ax=ax)
cbar.set_label("MRR")

fig.tight_layout()
save_figure(fig, "04_epsilon_mrr_heatmap")

plt.close(fig)

# Figure 5: Delta MRR relative to baseline
# Delta MRR = MRR_fuzzed - MRR_original
delta_epsilon = (epsilon_mrr[:, 1:] - epsilon_mrr[:, [0]])

fig, ax = plt.subplots(figsize=(8, 6))
max_abs = np.nanmax(np.abs(delta_epsilon))
if max_abs == 0:
    max_abs = 1

im = ax.imshow(delta_epsilon, aspect="auto", vmin=-max_abs, vmax=max_abs)

ax.set_xticks(np.arange(len(rates[1:])))
ax.set_xticklabels([f"{r}%" for r in rates[1:]])
ax.set_yticks(np.arange(len(techniques)))
ax.set_yticklabels(techniques)
ax.set_xlabel("Perturbation Rate")
ax.set_ylabel("Fuzzing Technique")
ax.set_title("Change in MRR Relative to the Unfuzzed Baseline\nEpsilon-Diagnosis -- LEMMA-RCA 20220606")

for i in range(len(techniques)):
    for j in range(len(rates[1:])):
        value = delta_epsilon[i, j]
        if not np.isnan(value):
            ax.text(j, i, f"{value:.3f}", ha="center", va="center")

cbar = fig.colorbar(im, ax=ax)
cbar.set_label(r"$\Delta$MRR")

fig.tight_layout()
save_figure(fig,"05_delta_mrr_heatmap_epsilon")

plt.close(fig)

# Figure 6: Mean MRR across all available fuzzing techniques
# np.nanmean is used because some techniques do not have results for every perturbation rate.
fig, ax = plt.subplots(figsize=(9, 6))

for model in models:
    mean_values = []
    for rate_index in range(len(rates)):
        values = [results[t][model]["MRR"][rate_index] for t in techniques]
        mean_values.append(np.nanmean(values))
    ax.plot(rates, mean_values, marker="o", linewidth=2, markersize=6, label=model)

ax.set_xlabel("Perturbation Rate (%)")
ax.set_ylabel("Mean MRR")
ax.set_xticks(rates)
ax.set_ylim(bottom=0)
ax.grid(True, alpha=0.3)
ax.legend()
ax.set_title("Mean MRR across Log Fuzzing Techniques\nLEMMA-RCA: 20220606")

fig.tight_layout()

save_figure(fig, "06_mrr_model_comparison")
plt.close(fig)



# Figure 7: Drain parsing behavior
drain_rates = np.array(
    [0, 10, 30, 50, 70, 90]
)

event_ids = np.array([27, 1996, 5742, 8388, 11756, 16122])
event_templates = np.array([43, 3192, 9818, 14287, 18875, 26103])

fig, ax = plt.subplots(figsize=(9, 6))

ax.plot(drain_rates, event_ids, marker="o", linewidth=2, label="Unique Event IDs")
ax.plot(drain_rates, event_templates, marker="o", linewidth=2, label="Unique Event Templates")

ax.set_xlabel("Perturbation Rate (%)")
ax.set_ylabel("Number of Unique Patterns")

ax.set_xticks(drain_rates)
ax.grid(True, alpha=0.3)
ax.legend()
ax.set_title("Effect of Log Perturbation on Drain Parsing\nLEMMA-RCA: 20220606")

fig.tight_layout()

save_figure(fig,"07_drain_parsing_effect")
plt.close(fig)

print()
print("=" * 10)
print("All figures generated successfully.")
print(f"Output directory: {OUTPUT_DIR}")
print("=" * 10)
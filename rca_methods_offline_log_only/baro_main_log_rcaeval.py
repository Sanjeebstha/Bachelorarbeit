import argparse
import os
import numpy as np
import pandas as pd
from sklearn.feature_selection import VarianceThreshold
from baro_algorithm import robust_scorer

def load_log_feature(file_path):
    """
    Load one RCAEval log-derived feature file.

    Expected dictionary:
        KPI_Label
        Container_Name
        KPI_Feature
        Sequence
        time
        step_size
        window_size

    Expected Sequence shape:
        (number_of_entities, number_of_windows, 1)
    """
    data = np.load(file_path, allow_pickle=True).item()
    required_keys = ["KPI_Label", "Container_Name", "KPI_Feature", "Sequence", "time",]

    for key in required_keys:
        if key not in data:
            raise KeyError(f"{file_path} does not contain required key: {key}")

    sequence = np.asarray(data["Sequence"], dtype=float)
    if sequence.ndim == 3:
        if sequence.shape[2] != 1:
            raise ValueError(f"Expected Sequence shape (entities, windows, 1), but got {sequence.shape}")
        sequence = sequence[:, :, 0].T
    elif sequence.ndim == 2:
        sequence = sequence.T
    else:
        raise ValueError(f"Unsupported Sequence shape: {sequence.shape}")
    Container_Names = list(data["Container_Name"])
    time_values = np.asarray(data["time"], dtype=np.int64)

    if sequence.shape[1] != len(Container_Names):
        raise ValueError(f"Number of Sequence entities does not match Container_Name: {sequence.shape[1]} != {len(Container_Names)}")

    if sequence.shape[0] != len(time_values):
        raise ValueError(f"Number of Sequence windows does not match time: {sequence.shape[0]} != {len(time_values)}")

    return {
        "KPI_Label": data["KPI_Label"],
        "Container_Name": Container_Names,
        "KPI_Feature": data["KPI_Feature"],
        "Sequence": sequence,
        "time": time_values,
        "step_size": data.get("step_size"),
        "window_size": data.get("window_size"),
    }

def find_common_entities(feature_data):
    """
    Find entities available in every requested feature

    Return entities that occur in all feature files.

    Preserve the ordering from the first feature instead of
    converting the final result to an unordered set.
    """
    feature_names = list(feature_data.keys())
    first_feature = feature_names[0]
    common = list(feature_data[first_feature]["Container_Name"])
    for feature in feature_names[1:]:
        current_nodes = set(feature_data[feature]["Container_Name"])
        common = [node for node in common if node in current_nodes]

    return common

def verify_same_time(feature_data):
    """
    Verify that all feature files use exactly the same RCAEval time grid.
    """
    feature_names = list(feature_data.keys())
    reference_name = feature_names[0]
    reference_time = feature_data[reference_name]["time"]
    for feature in feature_names[1:]:
        current_time = feature_data[feature]["time"]
        if not np.array_equal(reference_time, current_time):
            raise ValueError(f"Time mismatch between {reference_name} and {feature}")
    return reference_time

def prepare_feature_for_baro(feature_name, feature, common_entities,):
    """
    Select common entities, remove constant features,
    normalize each remaining entity to [0, 1],
    and construct BARO input.

    The first column is the real Unix timestamp.

    Remaining columns use:
        <entity>_<feature>

    Examples:
        ts-order-service_occurrence
        ts-order-service_golden_signal
    """
    all_nodes = feature["Container_Name"]
    entity_indices = [all_nodes.index(node) for node in common_entities]
    X = feature["Sequence"][:, entity_indices]
    print(f"\n{feature_name}: shape before feature selection = {X.shape}")

    # Safety checks
    if np.isnan(X).any():
        raise ValueError(f"{feature_name} contains NaN values.")

    if np.isinf(X).any():
        raise ValueError(f"{feature_name} contains Inf values.")

    # Remove constant entities.
    selector = VarianceThreshold(threshold=0.0)

    try:
        X_selected = selector.fit_transform(X)
    except ValueError:
        print(f"{feature_name}: all entities are constant.")
        return None

    selected_indices = selector.get_support(indices=True)

    if len(selected_indices) == 0:
        print(f"{feature_name}: all entities are constant.")
        return None

    selected_nodes = [common_entities[i] for i in selected_indices]
    print(f"{feature_name}: shape after feature selection = {X_selected.shape}")
    print(f"{feature_name}: retained entities = {len(selected_nodes)}")
    print(f"{feature_name}: root cause retained =", args.root_cause in selected_nodes)

    # Min-max normalization.
    minimum = X_selected.min(axis=0)
    maximum = X_selected.max(axis=0)
    denominator = maximum - minimum
    denominator[denominator == 0] = 1.0

    X_selected = (X_selected - minimum) / denominator

    # BARO's bocpd()/robust_scorer code identifies metric columns through metric names.
    # Therefore preserve occurrence / golden_signal in the column name.
    feature_type = feature["KPI_Feature"]
    columns = [f"{node}_{feature_type}" for node in selected_nodes]
    X_df = pd.DataFrame(X_selected, columns=columns)
    # Real RCAEval Unix timestamps.
    X_df.insert(0, "time", feature["time"])
    return X_df

def save_results(results, output_file,):
    """
    Save BARO root-cause ranking.
    """
    rows = []
    for root_cause, score in results:
        rows.append({"root_cause": root_cause, "score": score,})

    result_df = pd.DataFrame(rows)
    result_df.to_csv(output_file, index=False)
    return result_df

def main(args):
    case_name = args.case
    feature_dir = args.feature_dir
    injection_time = int(args.injection_time)
    output_dir = os.path.join(args.output_dir, case_name)
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("RCAEval BARO - LOG-DERIVED FEATURES")
    print("=" * 70)

    print("Case:", case_name)
    print("Feature directory:", feature_dir)
    print("Injection time:", injection_time)

    # Features to evaluate.
    feature_files = {"log_frequency": "pod_level_log_frequency.npy", "log_golden_signal": "pod_level_log_golden_signal.npy",}
    feature_data = {}

    # Load features.
    for feature_name, filename in feature_files.items():
        file_path = os.path.join(feature_dir, filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Feature file not found: {file_path}")

        print("\nLoading:", file_path)
        feature_data[feature_name] = load_log_feature(file_path)
        data = feature_data[feature_name]
        print("  KPI_Label:", data["KPI_Label"])
        print("  KPI_Feature:", data["KPI_Feature"])
        print("  Sequence shape:", data["Sequence"].shape)
        print("  Number of entities:", len(data["Container_Name"]))
        print("  First time:", data["time"][0])
        print("  Last time:", data["time"][-1])

    # Validate temporal alignment.
    time_values = verify_same_time(feature_data)
    print("\nTime arrays are identical.")
    print("Number of time points:", len(time_values))

    # Verify injection is within the feature time range.
    if not (time_values[0] <= injection_time <= time_values[-1]):
        raise ValueError(f"Injection time is outside feature time range: {injection_time} not in [{time_values[0]}, {time_values[-1]}]")

    nearest_idx = int(np.argmin(np.abs(time_values - injection_time)))

    print("Nearest injection index:", nearest_idx)
    print("Nearest feature timestamp:", time_values[nearest_idx])
    print("Difference from injection:", int(time_values[nearest_idx] - injection_time), "seconds")

    # Find entities shared by both feature files.
    common_entities = find_common_entities(feature_data)
    print("\nCommon entities:", len(common_entities))
    # Ground-truth service is optional, but useful for verification
    if args.root_cause is not None:
        print("Ground-truth root cause:", args.root_cause)
        print("Root cause in common entities:", args.root_cause in common_entities)

        if args.root_cause not in common_entities:
            raise ValueError(f"Ground-truth root cause {args.root_cause} is not available in the common entity set.")

    final_results = {}
    for feature_name in feature_files:
        print("Running BARO for:", feature_name)
        X = prepare_feature_for_baro(feature_name, feature_data[feature_name], common_entities,)
        if X is None:
            continue
        print("BARO input shape:", X.shape)
        print("BARO time range:", X["time"].iloc[0], "-", X["time"].iloc[-1])

        # ----------------------------------------------------
        # Do not run BOCPD to guess the injection point for RCAEval when the benchmark already supplies the known fault injection timestamp.
        # Pass the benchmark injection timestamp directly.
        # ----------------------------------------------------

        results = robust_scorer(X, inject_time=injection_time)
        print("\nBARO ranking:")

        for rank, result in enumerate(results[:10], start=1):
            root_cause, score = result
            print(rank, root_cause, score)

        output_file = os.path.join(output_dir,(f"{feature_name}_baro_{case_name}_root_cause.csv"))
        result_df = save_results(results, output_file)
        final_results[feature_name] = result_df
        print("Saved:", output_file)

    # Aggregate frequency + golden signal scores.
    if len(final_results) > 0:
        # ========================================================
        # Combine the individual BARO feature results.
        #
        # Example before normalization:
        #
        # ts-order-service_occurrence 2.2526
        # ts-order-service_golden_signal 2.2526
        #
        # Both correspond to the same RCA candidate:
        #
        # ts-order-service 4.5052
        # ========================================================

        concatenated_df = pd.concat(final_results.values(), ignore_index=True)
        concatenated_file = os.path.join(output_dir, "concated_df.csv")
        concatenated_df.to_csv(concatenated_file, index=False)

        # Remove the log-feature suffix.
        concatenated_df["entity"] = (concatenated_df["root_cause"].str.replace(r"_occurrence$", "", regex=True).str.replace(r"_golden_signal$", "", regex=True))

        # --------------------------------------------------------
        # Combine scores from:
        # log_frequency + golden_signal
        # This follows the score-summing idea used by the original LEMMA-RCA final aggregation.
        # --------------------------------------------------------

        aggregated_df = (concatenated_df.groupby("entity", as_index=False)["score"].sum())
        aggregated_df = (aggregated_df.sort_values(by="score", ascending=False).reset_index(drop=True))
        aggregated_df = aggregated_df.rename(columns={"entity": "root_cause"})
        final_file = os.path.join(output_dir,(f"final_baro_{case_name}_root_cause.csv"))
        aggregated_df.to_csv(final_file, index=False)
        print("FINAL AGGREGATED BARO RESULT")
        print(aggregated_df.head(10))
        print("\nSaved:", final_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=("BARO using RCAEval log-derived frequency and golden-signal features"))
    parser.add_argument("--case", required=True, type=str, help=("RCAEval case name, e.g. re2tt_ts-order-service_cpu_1"))
    parser.add_argument("--feature_dir", required=True, type=str, help=("Directory containing log_frequency.npy and log_golden_signal.npy"))
    parser.add_argument("--injection_time", required=True, type=int, help=("RCAEval fault injection Unix timestamp"))
    parser.add_argument("--root_cause", default=None, type=str, help=("Ground-truth service/entity, used only for verification"))
    # Change Path
    parser.add_argument("--output_dir", default="/mnt/hdd/sanjeeb_shrestha/final/preprocessing/re2tt_ts-order-service_delay_2/step4_fuzzing/result/baro/", type=str, help="BARO result directory") 
    args = parser.parse_args()
    main(args)
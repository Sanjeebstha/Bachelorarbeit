import pandas as pd
import numpy as np
import argparse
import os
import re

# References [1] Lecheng Zheng, Zhengzhang Chen, Dongjie Wang, Chengyuan Deng, Reon Matsuoka, and Haifeng Chen: LEMMA-RCA: A Large Multi-modal Multi-domain Dataset for Root Cause Analysis. CoRR abs/2406.05375 (2024)

# Sliding-window extraction
class SlidingWindow:
    def __init__(self):
        pass

    def sliding_window(self, df, templates, template_label_dict, window_size, step_size):
        """
        Parameters
        ----------
        df:
            DataFrame with:
                timestamp
                EventTemplate

        window_size:
            Window size in seconds.

        step_size:
            Step size in seconds.

        Returns
        -------
        DataFrame containing:
            StartTime
            EndTime
            EventSequences
            SequenceLabel

        SequenceLabel is the number of occurrences of templates classified as abnormal inside the window.
        """
        log_size = df.shape[0]
        time_data = df.iloc[:, 0]
        event_data = df.iloc[:, 1]
        new_data = []

        # Keep insertion order and avoid duplicate windows.
        start_end_index_pair = []
        seen_pairs = set()

        start_time = time_data.iloc[0]
        end_time = start_time + window_size

        start_index = 0
        end_index = 0

        # First window
        for cur_time in time_data:
            if cur_time < end_time:
                end_index += 1
            else:
                break
        pair = (start_index, end_index)

        if start_index != end_index:
            start_end_index_pair.append(pair)
            seen_pairs.add(pair)

        # Remaining sliding windows
        num_session = 1
        while end_index < log_size:
            start_time = start_time + step_size
            end_time = start_time + window_size

            # Find new start index
            i = start_index
            while (i < log_size and time_data.iloc[i] < start_time):
                i += 1

            # Find new end index
            j = end_index
            while (j < log_size and time_data.iloc[j] < end_time):
                j += 1

            start_index = i
            end_index = j

            # Ignore empty windows.
            if start_index != end_index:
                pair = (start_index, end_index)
                if pair not in seen_pairs:
                    start_end_index_pair.append(pair)
                    seen_pairs.add(pair)
            num_session += 1

            if num_session % 1000 == 0:
                print("process {} time window".format(num_session), end="\r")

        # Calculate golden-signal value for each window
        for start_index, end_index in start_end_index_pair:
            event_sequence = []
            sequence_label = []
            template_frequency = {}

            # Count each EventTemplate in this window
            for event in event_data.iloc[start_index:end_index]:
                event = str(event)
                # Classify template once and cache result.
                if event not in template_label_dict:
                    template_label_dict[event] = (is_abnormal_log(event))
                if event not in template_frequency:
                    template_frequency[event] = 1
                else:
                    template_frequency[event] += 1
                templates.add(event)

            # Golden signal: abnormal(template) * frequency(template)
            # Example:
            # ERROR timeout   -> abnormal=1
            # occurs 4 times  -> contributes 4
            #
            # INFO successful -> abnormal=0
            # occurs 20 times -> contributes 0
            for event, frequency in template_frequency.items():
                event_sequence.append(event)
                event_sequence.append(frequency)
                sequence_label.append(template_label_dict[event] * frequency)

            sequence_label = sum(sequence_label)
            event_sequence = np.array(event_sequence, dtype=object)

            # Actual first/last timestamps represented by this non-empty window.
            window_times = time_data.iloc[start_index:end_index]
            new_data.append([window_times.iloc[0], window_times.iloc[-1], event_sequence, sequence_label])

        new_df = pd.DataFrame(new_data, columns=["StartTime", "EndTime", "EventSequences", "SequenceLabel"])
        print("\nThere are {} instances (sliding windows) in this dataset".format(len(new_df)))
        return new_df, templates

# Abnormal-template detection
def is_abnormal_log(log_message):
    """
    Determine whether a Drain EventTemplate contains one of the abnormal keywords/patterns inherited from the LEMMA-RCA golden-signal implementation.
    Returns:
        1 = abnormal
        0 = normal
    """

    log_message = str(log_message)

    # List of keywords to detect abnormal log data
    keywords = ["error", "exception", "critical", "fatal", "timeout", "connection refused",
                "No space left on device", "out of memory", "terminated unexpectedly", "backtrace", "stack trace",
                "service unavailable", "502 Bad Gateway", "503 Service Unavailable", "504 Gateway Timeout",
                "unable to connect to", "rate limit exceeded", "request limit exceeded", "cloud system down", 
                "cloud service not responding", "failure", "corrupted data", "data loss", "file not found",
                "high CPU utilization", "CPU spike", "CPU saturation", "excessive CPU usage", "failed", "shutdown", 
                "Permission denied", "DEBUG", "cannot be contacted"]
    # Regular expressions for additional patterns
    # Example: Detect HTTP status codes outside the normal range (e.g., 400, 500)
    http_status_code_pattern = r"\b(4\d{2}|5\d{2})\b"
    cloud_provider_error_pattern = r"\b(AWS|Azure|Google Cloud)\b"
    custom_pattern = r"<\*> send error:.*"
    # Combine all patterns into a single regex
    combined_pattern = re.compile("|".join(keywords + [http_status_code_pattern, cloud_provider_error_pattern, custom_pattern]), re.IGNORECASE)
    # Check if the log message matches any of the patterns. 
    if re.search(combined_pattern, log_message):
        return 1
    else:
        return 0


# Find RCAEval Drain structured files
def find_container_files(log_dir):
    """
    Find all non-empty *_messages_structured.csv files.

    RCAEval adaptation:
        Do not use the original LEMMA-RCA 1000-record threshold.
        Even a container with only a few logs is retained.
    """
    files = []
    for filename in sorted(os.listdir(log_dir)):
        if not filename.endswith("_messages_structured.csv"):
            continue
        full_path = os.path.join(log_dir, filename)
        if not os.path.isfile(full_path):
            continue

        # Read only enough to determine whether the CSV contains at least one log record.
        df_check = pd.read_csv(full_path, encoding="Latin-1")
        num_records = len(df_check)
        container_name = filename.replace("_messages_structured.csv", "")
        if num_records == 0:
            print(f"{container_name}: empty structured CSV. Skipping.")
            continue

        print(f"{container_name}: {num_records:,} log records")
        files.append((container_name, full_path))
    return files

# Find nearest existing window
def find_closest_value_index_sorted(input_list, target_value):
    """
    Same alignment principle as the RCAEval frequency extractor:
    find the closest available window index.
    """
    if len(input_list) == 0:
        raise ValueError("Cannot align an empty index list.")

    arr = np.asarray(input_list, dtype=int)
    position = np.searchsorted(arr, target_value)

    if position == 0:
        return 0

    if position == len(arr):
        return len(arr) - 1

    before = arr[position - 1]
    after = arr[position]

    if abs(target_value - before) <= abs(after - target_value):
        return position - 1

    return position

# Main
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=("Extract RCAEval log golden-signal features from Drain structured logs."))
    parser.add_argument("--log_dir", required=True, type=str, help=("Directory containing RCAEval *_messages_structured.csv files"))
    parser.add_argument("--output_dir", required=True, type=str, help=("Directory where log_golden_signal.npy will be saved"))
    parser.add_argument("--dataset_name", default="re2tt_ts-order-service_delay_2", type=str, help="RCAEval case name")
    parser.add_argument("--step_size", default=0.5, type=float, help="Step size in minutes")
    parser.add_argument("--window_size", default=5, type=float, help="Window size in minutes")
    args = parser.parse_args()

    print("=" * 10)
    print("RCAEVAL LOG GOLDEN-SIGNAL EXTRACTION")
    print("=" * 10)
    print("Dataset        :", args.dataset_name)
    print("Drain directory:", args.log_dir)
    print("Window size    :", args.window_size, "minutes")
    print("Step size      :", args.step_size, "minutes")

    print("=" * 10)

    os.makedirs(args.output_dir, exist_ok=True)

    # Find containers
    container_files = find_container_files(args.log_dir)

    if len(container_files) == 0:
        raise ValueError("No non-empty *_messages_structured.csv files were found.")

    container_names = [item[0] for item in container_files]

    print("\nContainers retained:", len(container_names))

    # Extract golden signal for every container
    sequences = {}
    templates = set()

    # Cache: EventTemplate -> 0/1
    # If the same template occurs thousands of times, regex classification is performed only once.
    template_label_dict = {}

    for (container_name, filename) in container_files:
        print("\nProcessing:", container_name)
        print("File:", filename)
        df = pd.read_csv(filename, encoding="Latin-1")
        required_columns = {"Time", "EventTemplate"}
        missing = (required_columns - set(df.columns))
        if missing:
            raise ValueError(f"{filename} is missing columns: {missing}")

        # RCAEval:
        # Drain Time is already Unix timestamp in seconds.
        # Example: 1706066405
        # Do not run pd.to_datetime() here.
        df["timestamp"] = pd.to_numeric(df["Time"], errors="coerce")
        df = df.dropna(subset=["timestamp", "EventTemplate"])
        df["timestamp"] = (df["timestamp"].astype(np.int64))
        df = df.sort_values(by="timestamp", ignore_index=True)
        if len(df) == 0:
            print(container_name, "contains no valid records. Skipping.")
            continue
        print("Rows:", len(df))
        print("Time span:", df["timestamp"].min(), "-", df["timestamp"].max())

        window = SlidingWindow()
        processed_sequence, templates = (window.sliding_window(df[["timestamp", "EventTemplate"]], templates, template_label_dict, window_size=(float(args.window_size) * 60), step_size=(float(args.step_size) * 60)))
        processed_sequence = (processed_sequence.sort_values(by="StartTime", ignore_index=True))
        if len(processed_sequence) == 0:
            print(container_name, "produced no sliding windows. Skipping.")
            continue
        sequences[container_name] = {"StartTime": processed_sequence["StartTime"], "SequenceLabel": processed_sequence["SequenceLabel"]}

    # Remove any container that unexpectedly produced no windows.
    container_names = [name for name in container_names if name in sequences]
    if len(container_names) == 0:
        raise ValueError("No containers produced usable sliding windows.")


    # Diagnostic information about templates
    print("\nTotal unique Drain3 templates:", len(templates))

    abnormal_templates = [template for template in templates if template_label_dict.get(template, 0) == 1]
    print("Abnormal templates detected:", len(abnormal_templates))

    # Print a few so you can verify whether the golden-signal keywords are actually matching RCAEval templates.
    if abnormal_templates:
        print("\nExample abnormal templates:")
        for template in abnormal_templates[:10]:
            print("  -", template)
    else:
        print("\nWARNING: No abnormal EventTemplates were detected.")
        print("The golden-signal feature may therefore be zero/constant for many or all containers.")

    # Establish common global time range
    # This follows the same alignment idea as frequency extractor: earliest first window -> latest first window.
    start_time = min(sequence["StartTime"].min() for sequence in sequences.values())
    end_time = max(sequence["StartTime"].max() for sequence in sequences.values())
    step_seconds = (args.step_size * 60)
    length = (int((end_time - start_time) // step_seconds) + 1)
    print("\nGlobal start time:", start_time)
    print("Global end time  :", end_time)
    print("Aligned windows  :", length)

    # Allocate final feature tensor
    # Shape: containers × windows × 1
    log_sequence = np.zeros((len(container_names), length, 1), dtype=float)

    # Align every container onto the common time grid.
    # This deliberately uses the same nearest-window strategy as RCAEval log_frequency.py so that frequency and golden signal can have identical temporal grids for BARO.
    for container_index, container_name in enumerate(container_names):
        item = sequences[container_name]
        temp_data = np.zeros((length, 1), dtype=float)
        idx = [int((timestamp - start_time) // step_seconds) for timestamp in item["StartTime"]]
        values = np.asarray(item["SequenceLabel"], dtype=float).reshape(-1, 1)

        # Place actual observed windows.
        temp_data[idx] = values

        # Fill missing aligned positions using the nearest available window.
        # This mirrors frequency extractor.
        for target_index in range(length):
            if target_index not in idx:
                closest_position = (find_closest_value_index_sorted(idx, target_index))
                temp_data[target_index] = values[closest_position]

        log_sequence[container_index, :, :] = temp_data
        print(f"{container_name}: windows={len(idx)}, nonzero golden={np.count_nonzero(temp_data)}")

    # Generate time exactly like log_frequency.py.
    # This is important because BARO script explicitly checks:
    # np.array_equal(log_frequency["time"], log_golden_signal["time"])
    ct = np.linspace(start_time, end_time, num=length, endpoint=True, dtype=int)

    # Save RCAEval-compatible feature file

    processed_data = {
        "KPI_Label": args.dataset_name,
        "Container_Name": container_names,
        "KPI_Feature": "golden_signal",
        "Sequence": log_sequence,
        "time": ct,
        "step_size": args.step_size,
        "window_size": args.window_size
    }

    output_file = os.path.join(args.output_dir, "pod_level_log_golden_signal.npy")
    np.save(output_file, processed_data)

    print("\n" + "=" * 10)
    print("GOLDEN-SIGNAL EXTRACTION COMPLETE")

    print("=" * 10)
    print("Saved:", output_file)
    print("Sequence shape:", log_sequence.shape)
    print("Containers:", len(container_names))
    print("Time points:", len(ct))
    print("Abnormal templates:", len(abnormal_templates))
    print("Total golden-signal count:", log_sequence.sum())
    print("=" * 10)
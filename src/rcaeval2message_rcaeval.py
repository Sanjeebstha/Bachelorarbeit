"""
Convert RCAEval logs.parquet into one plain-text log file per container.

Output format:
    <RCAEval Unix timestamp><TAB><normalized log message>

Usage:
    python convert_rcaeval_logs.py --input /path/to/logs.parquet --output_dir /path/to/output
"""

import argparse
import json
import os
import re
import pandas as pd

def remove_leading_timestamp(message):
    """
    Remove a datetime only when it occurs at the beginning of the original log message.
    Timestamps occurring later inside the actual message are not removed.
    """
    text = str(message)
    text = re.sub(r'^\s*\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s*','',text)
    return text.strip()


# Helper for MongoDB attribute values
def flatten_value(value):
    """
    Convert MongoDB values to compact text.
    Dictionaries/lists are serialized as JSON instead of being discarded.
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


# MongoDB structured JSON normalization
def extract_mongodb_message(message):
    """
    Detect MongoDB structured JSON logs and convert them into text suitable for Drain.

    Returns
        tuple(normalized_message, is_mongodb)
    """
    text = str(message).strip()

    # Find JSON object.
    json_start = text.find("{")
    if json_start == -1:
        return text, False
    json_text = text[json_start:]
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return text, False
    if not isinstance(data, dict):
        return text, False

    # Avoid treating arbitrary JSON application messages as MongoDB.
    # MongoDB structured logs normally contain "msg" together with several MongoDB metadata fields.
    if "msg" not in data:
        return text, False
    mongodb_metadata = {"t", "s", "c", "id", "ctx"}
    if not mongodb_metadata.intersection(data.keys()):
        return text, False

    parts = []

    # Do not add data["t"].
    # Example: "t":{"$date":"2024-01-22T14:40:36.797+00:00"}
    # It duplicates RCAEval's outer timestamp.
    severity = data.get("s")
    if severity is not None:
        parts.append(str(severity))

    # MongoDB component
    # Example: "c":"STORAGE"
    component = data.get("c")
    if component is not None:
        parts.append(str(component))

    # MongoDB event/message ID
    # Example: "id":22430
    event_id = data.get("id")
    if event_id is not None:
        parts.append(str(event_id))

    # Context
    # Example: "ctx":"Checkpointer"
    context = data.get("ctx")
    if context is not None:
        parts.append(str(context))

    # Main MongoDB message
    # Example: "msg":"WiredTiger message"
    msg = data.get("msg")
    if msg is not None and str(msg).strip():
        parts.append(str(msg).strip())

    # MongoDB attributes
    attr = data.get("attr")
    if isinstance(attr, dict):
        for key, value in attr.items():
            if value is None:
                continue
            value = flatten_value(value)

            # attr.message normally contains the actual detailed human-readable message.
            # Keep it directly instead of producing:
            # message=....
            if key == "message":
                parts.append(value)
            else:
                # Keep the attribute name because otherwise semantic information could be lost.
                # Example:
                # durationMillis=15
                # remote=10.0.0.1
                parts.append(f"{key}={value}")

    # In unusual MongoDB records attr may not be a dictionary.
    # Preserve it rather than silently discarding it.
    elif attr is not None:
        parts.append(flatten_value(attr))

    normalized = " ".join(parts).strip()

    # If extraction somehow produced an empty string, preserve the original message instead of losing the log event.
    if not normalized:
        return text, True

    return normalized, True


# Normalize one log event
def normalize_message(message):
    """
    Normalize one RCAEval message before sending it to Drain.

    Returns
        tuple(normalized_message, is_mongodb)
    """
    original = str(message).strip()

    # First check MongoDB.
    # This is intentionally done BEFORE normal timestamp removal.
    # MongoDB's timestamp is inside JSON and should be handled structurally, not with a generic regex.
    normalized, is_mongodb = extract_mongodb_message(original)
    if is_mongodb:
        message = normalized
    else:
        # Ordinary Spring/application log
        message = remove_leading_timestamp(original)

    # Ensure exactly one physical line per event.
    message = (message.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n"))
    return message.strip(), is_mongodb

# Convert complete RCAEval Parquet file
def convert(input_file, output_dir):
    print("=" * 10)
    print("RCAEVAL LOG CONVERSION FOR DRAIN3")
    print("=" * 72)
    print(f"Input : {input_file}")
    print(f"Output: {output_dir}")
    print("=" * 10)

    df = pd.read_parquet(input_file)
    required = {"timestamp", "container_name", "message"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input Parquet is missing required columns: {missing}")
    print(f"\nRows loaded: {len(df):,}")
    print(f"Columns    : {list(df.columns)}")

    # Remove rows where required information is absent.
    before = len(df)
    df = df.dropna(subset=["timestamp", "container_name", "message"])
    removed = before - len(df)
    if removed:
        print(f"Dropped {removed:,} rows containing missing values.")

    # Sort chronologically inside each container.
    df = df.sort_values(["container_name", "timestamp"])
    os.makedirs(output_dir, exist_ok=True)
    containers = df["container_name"].nunique()
    print(f"Containers : {containers:,}\n")

    total_logs = 0
    total_mongodb_logs = 0
    # One output file per container.
    for container, group in df.groupby("container_name", sort=False):
        # Basic filename safety
        safe_container = str(container).replace("/", "_")
        output_file = os.path.join(output_dir, f"{safe_container}_messages")
        mongodb_count = 0
        written_count = 0

        with open(output_file, "w", encoding="utf-8") as f:
            for _, row in group.iterrows():
                # Keep RCAEval's outer timestamp.
                timestamp = row["timestamp"]
                # Convert integer-like timestamps such as 1705934409.0 -> 1705934409
                try:
                    numeric_timestamp = float(timestamp)
                    if numeric_timestamp.is_integer():
                        timestamp = int(numeric_timestamp)
                except (ValueError, TypeError):
                    pass

                # Normalize message exactly ONCE.
                message, is_mongodb = normalize_message(row["message"])
                if is_mongodb:
                    mongodb_count += 1

                f.write(f"{timestamp}\t{message}\n")
                written_count += 1

        total_logs += written_count
        total_mongodb_logs += mongodb_count

        if mongodb_count:
            print(f"{container}: {written_count:,} logs | MongoDB={mongodb_count:,} | {output_file}")
        else:
            print(f"{container}: {written_count:,} logs | {output_file}")

    print("\n" + "=" * 10)
    print("CONVERSION COMPLETE")
    print("=" * 10)
    print(f"Containers processed : {containers:,}")
    print(f"Logs written         : {total_logs:,}")
    print(f"MongoDB JSON logs    : {total_mongodb_logs:,}")
    print("=" * 10)

def main():
    parser = argparse.ArgumentParser(description=("Convert RCAEval logs.parquet into per-container text files suitable for Drain3."))
    parser.add_argument("--input_dir", required=True, help="Path to RCAEval logs.parquet")
    parser.add_argument("--output_dir", required=True, help="Directory for converted per-container log files")
    args = parser.parse_args()
    convert(args.input_dir, args.output_dir)

if __name__ == "__main__":
    main()
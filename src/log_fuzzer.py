# __author__ = "Sanjeeb Shrestha"

"""
log_fuzzer.py - pre-Drain log fuzzing for RCA robustness experiments.

Input format (one per-container file): <outer_timestamp>\t<message>

The outer timestamp and protected/structured tokens are copied unchanged.
Whitespace inside messages is preserved. Use one perturbation operator per run
for interpretable robustness curves.

Character-level modes:
    random, sorted, adjacent_swap, char_delete, char_insert, keyboard_typo, case_change
Token modes:
    token_delete, token_replace, token_insert

Example:
    python log_fuzzer.py --input_dir ./test --output_dir ./out --stats_dir ./stats --mode adjacent_swap --probability 0.30 --seed 42
"""

import argparse
import csv
import ipaddress
import os
import random
import re
import string

CHAR_MODES = {"random", "sorted", "adjacent_swap", "char_delete", "char_insert", "keyboard_typo", "case_change"}
TOKEN_MODES = {"token_delete", "token_replace", "token_insert"}
ALL_MODES = sorted(CHAR_MODES | TOKEN_MODES)

# Domain words that normally carry protocol/platform meaning. Keeping these
# fixed lets an experiment target ordinary lexical/template drift instead.
DEFAULT_PROTECTED_VOCAB = {
    "TRACE", "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL",
    "HTTP", "HTTPS", "TCP", "UDP", "TLS", "DNS", "OOM", "CPU", "RAM",
    "JVM", "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS",
    "NULL", "TRUE", "FALSE"
}

# Neutral replacement/insertion vocabulary. These tokens intentionally carry
# little operational meaning; customize with --noise_words if desired.
DEFAULT_NOISE_WORDS = ["context", "message", "status", "operation", "event"]

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")
URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://\S+$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:%|ms|s|m|h|B|KB|MB|GB)?$")
HEX_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{8,}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?$")
HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9-]{2,63}(?::\d{1,5})?$")
PORT_RE = re.compile(r"^(?:[A-Za-z0-9_.-]+:)?\d{1,5}$")
PATH_RE = re.compile(r"^(?:/|\./|\.\./|[A-Za-z]:[\\/])\S+$")
HTTP_STATUS_RE = re.compile(r"^[1-5]\d{2}$")
K8S_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?-[a-z0-9-]{5,}$")
IMAGE_RE = re.compile(r"^(?=\S*(?:/|:|@sha256:))(?:[\w.-]+(?::\d+)?/)?[\w./-]+(?::[\w.-]+|@sha256:[0-9a-fA-F]{64})$")
EXCEPTION_RE = re.compile(r"^(?:[A-Za-z_$][\w$]*\.)*[A-Z][A-Za-z0-9_$]*(?:Exception|Error|Throwable)$")
STACK_FRAME_RE = re.compile(r"^(?:at\s+)?(?:[A-Za-z_$][\w$]*\.)+[A-Za-z_$][\w$]*(?:\([^)]*\))?:?$")
TRACE_KEY_RE = re.compile(r"^(?:trace[_-]?id|span[_-]?id|request[_-]?id|correlation[_-]?id|transaction[_-]?id|session[_-]?id|pod|container|namespace|node|host|hostname|service)\s*[:=].+$", re.IGNORECASE,)
KEY_VALUE_RE = re.compile(r"^[A-Za-z_][\w.-]*=(?:\"[^\"]*\"|'[^']*'|\S+)$")
HTTP_METHOD_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|CONNECT|TRACE)$", re.I)

KEYBOARD_NEIGHBORS = {
    "q":"wa", "w":"qase", "e":"wsdr", "r":"edft", "t":"rfgy",
    "y":"tghu", "u":"yhji", "i":"ujko", "o":"iklp", "p":"ol",
    "a":"qwsz", "s":"awedxz", "d":"serfcx", "f":"drtgvc",
    "g":"ftyhbv", "h":"gyujnb", "j":"huikmn", "k":"jiolm", "l":"kop",
    "z":"asx", "x":"zsdc", "c":"xdfv", "v":"cfgb", "b":"vghn",
    "n":"bhjm", "m":"njk"
}

def split_edge_punctuation(token):
    """
    Split a token into leading punctuation, core text, and trailing punctuation.

    Args:
        token: Input token.

    Returns:
        A tuple containing leading punctuation, core token text, trailing punctuation.
    """
    start, end = 0, len(token)
    while start < end and token[start] in string.punctuation and token[start] not in "/\\":
        start += 1
    while end > start and token[end - 1] in string.punctuation and token[end - 1] not in "/\\":
        end -= 1
    return token[:start], token[start:end], token[end:]


def looks_like_ip(value):
    """
    Check whether a value is a valid IPv4 or IPv6 address.

    IPv6 addresses enclosed in brackets and optionally followed by a port are also supported.

    Args:
        value: String to check.

    Returns:
        True if the value represents an IP address; otherwise False.
    """
    candidate = value.strip("[]")
    # IPv6 may have :port only when bracketed; [::1]:8080 is handled here.
    if value.startswith("[") and "]:" in value:
        candidate = value[1:value.index("]")]
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        return False


def looks_like_json(token):
    """
    Check whether a token appears to be a compact JSON fragment.

    Args:
        token: String to check.

    Returns:
        True if the token has JSON-like structure; otherwise False.
    """
    return ((token.startswith("{") and token.endswith("}")) or (token.startswith("[") and token.endswith("]"))) and (":" in token or "," in token)


def is_structured(token, protected_vocab):
    """
    Determine whether a token should be protected from fuzzing.

    Structured values such as IP addresses, UUIDs, URLs, timestamps,
    paths, numbers, Kubernetes names, HTTP methods, and protected
    vocabulary are preserved unchanged.

    Args:
        token: Token to examine.
        protected_vocab: Set of words that must remain unchanged.

    Returns:
        True if the token is considered structured or protected;
        otherwise False.
    """
    if not token:
        return True
    if token.upper() in protected_vocab:
        return True
    if looks_like_ip(token) or looks_like_json(token):
        return True
    patterns = (
        UUID_RE, MAC_RE, URL_RE, EMAIL_RE, NUMBER_RE, HEX_RE, TIMESTAMP_RE,
        HOST_RE, PATH_RE, HTTP_STATUS_RE, K8S_NAME_RE, IMAGE_RE, EXCEPTION_RE,
        STACK_FRAME_RE, TRACE_KEY_RE, KEY_VALUE_RE, HTTP_METHOD_RE,
    )
    return any(p.fullmatch(token) for p in patterns)


def eligible_core(token, protected_vocab):
    """
    Determine whether a token contains eligible free-text content.

    Edge punctuation is temporarily separated. Structured tokens,
    protected tokens, short tokens, and non-alphabetic tokens are
    excluded from character-level fuzzing.

    Args:
        token: Token to examine.
        protected_vocab: Set of protected words.

    Returns:
        A tuple containing leading punctuation, alphabetic core,
        and trailing punctuation if eligible; otherwise None.
    """
    leading, core, trailing = split_edge_punctuation(token)
    # Check both full token and punctuation-stripped core. This fixes tokens such as ERROR, and SocketTimeoutException:.
    if is_structured(token, protected_vocab) or is_structured(core, protected_vocab):
        return None
    if len(core) <= 3 or not core.isalpha():
        return None
    return leading, core, trailing



def mutate_core(core, mode, rng):
    """
    Apply one character-level perturbation to a token core.

    Supported modes are random, sorted, adjacent_swap, char_delete,
    char_insert, keyboard_typo, and case_change. The first and last
    characters are kept unchanged where possible.

    Args:
        core: Alphabetic token core to modify.
        mode: Character-level perturbation mode.
        rng: Random number generator used for reproducible changes.

    Returns:
        The mutated token core.

    Raises:
        ValueError: If an unsupported character mode is provided.
    """
    if len(core) <= 3:
        return core

    middle = list(core[1:-1])

    if mode == "random":
        rng.shuffle(middle)
        return core[0] + "".join(middle) + core[-1]
    if mode == "sorted":
        return core[0] + "".join(sorted(middle)) + core[-1]
    if mode == "adjacent_swap":
        if len(middle) < 2:
            return core
        i = rng.randrange(len(middle) - 1)
        middle[i], middle[i + 1] = middle[i + 1], middle[i]
        return core[0] + "".join(middle) + core[-1]
    if mode == "char_delete":
        i = rng.randrange(len(middle))
        del middle[i]
        return core[0] + "".join(middle) + core[-1]
    if mode == "char_insert":
        i = rng.randrange(len(middle) + 1)
        middle.insert(i, rng.choice(string.ascii_lowercase))
        return core[0] + "".join(middle) + core[-1]
    if mode == "keyboard_typo":
        candidates = [i for i, ch in enumerate(middle) if ch.lower() in KEYBOARD_NEIGHBORS]
        if not candidates:
            return core
        i = rng.choice(candidates)
        old = middle[i]
        new = rng.choice(KEYBOARD_NEIGHBORS[old.lower()])
        middle[i] = new.upper() if old.isupper() else new
        return core[0] + "".join(middle) + core[-1]
    if mode == "case_change":
        i = rng.randrange(len(middle))
        middle[i] = middle[i].swapcase()
        return core[0] + "".join(middle) + core[-1]
    raise ValueError(f"Unsupported character mode: {mode}")


def mutate_token(token, mode, rng, protected_vocab):
    """
    Apply a character-level mutation to one eligible token.

    The token's surrounding punctuation is preserved.

    Args:
        token: Token to mutate.
        mode: Character-level perturbation mode.
        rng: Random number generator.
        protected_vocab: Set of protected words.

    Returns:
        The mutated token, or the original token if it is not eligible.
    """
    info = eligible_core(token, protected_vocab)
    if info is None:
        return token
    leading, core, trailing = info
    return leading + mutate_core(core, mode, rng) + trailing


# Message-level fuzzing while preserving whitespace
def fuzz_line(message, mode, probability, rng, protected_vocab, noise_words):
    """
    Apply one fuzzing mode to a single log message.

    Whitespace is preserved. Character-level mutations are applied
    to eligible words, while token-level modes can delete, replace,
    or insert words.

    Args:
        message: Log message to perturb.
        mode: Fuzzing mode.
        probability: Probability of selecting each eligible token.
        rng: Random number generator.
        protected_vocab: Set of protected words.
        noise_words: Vocabulary used for token insertion and replacement.

    Returns:
        A tuple containing:
            - the fuzzed message,
            - a dictionary containing fuzzing statistics.
    """
    parts = re.split(r"(\s+)", message)
    token_indices = [i for i, p in enumerate(parts) if p and not p.isspace()]
    eligible_indices = [i for i in token_indices if eligible_core(parts[i], protected_vocab) is not None]

    stats = {
        "total_tokens": len(token_indices),
        "eligible_words": len(eligible_indices),
        "selected_words": 0,
        "changed_words": 0,
        "unchanged_selected": 0,
        "inserted_words": 0,
        "deleted_words": 0,
        "replaced_words": 0,
    }

    # Token insertion is naturally interpreted as one Bernoulli trial per
    # eligible token/position. It does not destroy the selected source token.
    if mode == "token_insert":
        out = []
        eligible_set = set(eligible_indices)
        for i, part in enumerate(parts):
            out.append(part)
            if i in eligible_set and rng.random() < probability:
                stats["selected_words"] += 1
                noise = rng.choice(noise_words)
                # Insert after token with a single space. Original whitespace
                # remains untouched after the inserted token.
                out.append(" " + noise)
                stats["changed_words"] += 1
                stats["inserted_words"] += 1
        return "".join(out), stats

    eligible_set = set(eligible_indices)
    for i in eligible_indices:
        if rng.random() >= probability:
            continue
        stats["selected_words"] += 1
        old = parts[i]

        if mode in CHAR_MODES:
            new = mutate_token(old, mode, rng, protected_vocab)
        elif mode == "token_replace":
            leading, _, trailing = split_edge_punctuation(old)
            new = leading + rng.choice(noise_words) + trailing
            stats["replaced_words"] += int(new != old)
        elif mode == "token_delete":
            # Empty the token but leave separators intact. This deliberately
            # changes lexical content without reformatting neighboring text.
            new = ""
            stats["deleted_words"] += 1
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        parts[i] = new
        if new != old:
            stats["changed_words"] += 1
        else:
            stats["unchanged_selected"] += 1

    return "".join(parts), stats

# File / directory processing and statistics
STAT_KEYS = [
    "total_lines", "malformed_lines", "total_tokens", "eligible_words",
    "selected_words", "changed_words", "unchanged_selected",
    "inserted_words", "deleted_words", "replaced_words",
]


def fuzz_file(input_path, output_path, mode, probability, rng, protected_vocab, noise_words):
    """
    Fuzz all log messages in one input file.

    The timestamp is preserved and the message portion is passed
    to fuzz_line(). Malformed lines without a tab separator are
    copied unchanged.

    Args:
        input_path: Path to the input log file.
        output_path: Path for the fuzzed output file.
        mode: Fuzzing mode.
        probability: Per-token fuzzing probability.
        rng: Random number generator.
        protected_vocab: Set of protected words.
        noise_words: Vocabulary for token insertion and replacement.

    Returns:
        A dictionary containing statistics for the processed file.
    """
    stats = {k: 0 for k in STAT_KEYS}
    with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
        for raw_line in infile:
            stats["total_lines"] += 1
            newline = "\n" if raw_line.endswith("\n") else ""
            line = raw_line[:-1] if newline else raw_line
            if "\t" not in line:
                stats["malformed_lines"] += 1
                outfile.write(raw_line)
                continue
            timestamp, message = line.split("\t", 1)
            fuzzed, line_stats = fuzz_line(message, mode, probability, rng, protected_vocab, noise_words)
            for key, value in line_stats.items():
                stats[key] += value
            outfile.write(f"{timestamp}\t{fuzzed}{newline}")
    return stats


def fuzz_directory(input_dir, output_dir, stats_dir, mode="random", probability=0.3, seed=42, protected_words=None, noise_words=None):
    """
    Fuzz all log files in an input directory.

    Each file is processed using the same fuzzing configuration and
    a reproducible random number generator. Dataset-level statistics
    are accumulated and written to a CSV file.

    Args:
        input_dir: Directory containing input log files.
        output_dir: Directory for fuzzed log files.
        stats_dir: Directory for fuzzing statistics.
        mode: Fuzzing mode.
        probability: Per-eligible-token selection probability.
        seed: Random seed for reproducibility.
        protected_words: Additional words to protect.
        noise_words: Vocabulary used for token insertion and replacement.

    Returns:
        None.
    """
    if not 0 <= probability <= 1:
        raise ValueError("--probability must be between 0.0 and 1.0")
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(stats_dir, exist_ok=True)
    rng = random.Random(seed)  # one reproducible RNG for the complete case
    protected_vocab = set(DEFAULT_PROTECTED_VOCAB)
    if protected_words:
        protected_vocab.update(w.upper() for w in protected_words)
    noise_words = noise_words or DEFAULT_NOISE_WORDS

    filenames = sorted(f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)))
    if not filenames:
        print(f"No files found in: {input_dir}")
        return

    print("=" * 10)
    print("RCA PRE-DRAIN LOG FUZZING")
    print("=" * 10)
    print(f"Input directory       : {input_dir}")
    print(f"Output directory      : {output_dir}")
    print(f"Mode                  : {mode}")
    print(f"Requested probability : {probability:.2%}")
    print(f"Seed                  : {seed}")
    print(f"Container files       : {len(filenames)}")
    print("=" * 10)

    dataset = {k: 0 for k in STAT_KEYS}
    for n, filename in enumerate(filenames, 1):
        fs = fuzz_file(os.path.join(input_dir, filename), os.path.join(output_dir, filename), mode, probability, rng, protected_vocab, noise_words)
        for k in STAT_KEYS:
            dataset[k] += fs[k]
        actual = fs["changed_words"] / fs["eligible_words"] if fs["eligible_words"] else 0
        print(f"[{n:>2}/{len(filenames)}] {filename}: {fs['total_lines']:,} lines | eligible={fs['eligible_words']:,} | selected={fs['selected_words']:,} | changed={fs['changed_words']:,} | actual={actual:.2%}")

    eligible, selected, changed = dataset["eligible_words"], dataset["selected_words"], dataset["changed_words"]
    selection_rate = selected / eligible if eligible else 0
    actual_rate = changed / eligible if eligible else 0
    all_rate = changed / dataset["total_tokens"] if dataset["total_tokens"] else 0

    print("\n" + "=" * 10)
    print("FUZZING SUMMARY")
    print("=" * 10)
    print(f"Mode                       : {mode}")
    print(f"Requested probability      : {probability:.2%}")
    print(f"Seed                       : {seed}")
    print(f"Containers processed       : {len(filenames):,}")
    print(f"Total log lines            : {dataset['total_lines']:,}")
    print(f"Malformed lines            : {dataset['malformed_lines']:,}")
    print(f"Total message tokens       : {dataset['total_tokens']:,}")
    print(f"Eligible words             : {eligible:,}")
    print(f"Selected for fuzzing       : {selected:,}")
    print(f"Actually changed words     : {changed:,}")
    print(f"Selected but unchanged     : {dataset['unchanged_selected']:,}")
    print(f"Inserted / deleted / repl. : {dataset['inserted_words']:,} / {dataset['deleted_words']:,} / {dataset['replaced_words']:,}")
    print(f"Observed selection rate    : {selection_rate:.2%}")
    print(f"Actual perturbation rate   : {actual_rate:.2%}")
    print(f"Changed / all tokens       : {all_rate:.2%}")
    print("=" * 10)

    stats_file = os.path.join(stats_dir, "fuzzing_statistics.csv")
    row = {
        "mode": mode, "requested_probability": probability, "seed": seed,
        "containers_processed": len(filenames), **dataset,
        "observed_selection_rate": selection_rate,
        "actual_perturbation_rate": actual_rate,
        "changed_all_tokens_rate": all_rate,
    }
    with open(stats_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writeheader(); writer.writerow(row)
    print(f"\nStatistics saved in:\n{stats_file}")


def main():
    """
    Parse command-line arguments and run the log fuzzing pipeline.

    The function reads the input directory, output directory,
    statistics directory, fuzzing mode, probability, random seed,
    protected words, and noise words from the command line. It then
    passes these parameters to fuzz_directory().

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Pre-Drain RCA log fuzzer for RCA robustness experiments.")
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--stats_dir", required=True)
    parser.add_argument("--mode", choices=ALL_MODES, default="random")
    parser.add_argument("--probability", type=float, default=0.30, help="Per-eligible-token selection probability [0,1].")
    parser.add_argument("--seed", type=int, default=42, help="Random seed. Same input/options/seed => reproducible output.")
    parser.add_argument("--protect_words", nargs="*", default=None, help="Additional words to preserve, e.g. database timeout retry.")
    parser.add_argument("--noise_words", nargs="*", default=None, help="Words used by token_insert/token_replace.")
    args = parser.parse_args()
    fuzz_directory(args.input_dir, args.output_dir, args.stats_dir, args.mode, args.probability, args.seed, args.protect_words, args.noise_words,)

if __name__ == "__main__":
    main()
import pandas as pd
import sys
import os
import argparse

# References [1] Lecheng Zheng, Zhengzhang Chen, Dongjie Wang, Chengyuan Deng, Reon Matsuoka, and Haifeng Chen: LEMMA-RCA: A Large Multi-modal Multi-domain Dataset for Root Cause Analysis. CoRR abs/2406.05375 (2024)
# Usage:
#   python src/evaluation/evaluation_main.py --dataset rcaeval --method epsilon

# RCAEval configuration 
# Change path
RCAEval_BASE_PATH = ("/mnt/hdd/sanjeeb_shrestha/final/preprocessing/re2tt_ts-order-service_delay_2/test/step5/rcd/")
RCAEval_FOLDERS = ["re2tt_ts-order-service_delay_2"]
RCAEval_GROUND_TRUTH = [["ts-order-service"]]


# LEMMA-RCA configuration 
# Change path
LEMMA_BASE_PATH = ("/mnt/hdd/sanjeeb_shrestha/lemma_rca/raw/preprocessing/token_delete/feature/rate_30/epsilon_diagnosis/")
LEMMA_FOLDERS = ["20220606"]
LEMMA_GROUND_TRUTH = [["productpage-v1-5f9dbcd669-z2prs"]]

# Method -> result file
METHOD_FILES = {
    "baro": "final_baro_{folder}_root_cause.csv",
    "rcd": "final_rcd_{folder}_root_cause.csv",
    "epsilon": "final_epsilon_diagnosis_{folder}_root_cause.csv",
    "circa": "final_circa_{folder}_root_cause.csv",
} 

def remove_metric(name):
    """
    Convert a metric-level root-cause name to a pod-level name
    Remove CPU or memory suffix from a root-cause name.

    Args:
        name: Root-cause name, such as 'pod-name_cpu' or 'pod-name_memory'.

    Returns:
        The pod name without the metric suffix.
    """
    if name.endswith("memory"):
        return name[:-len("_memory")]
    elif name.endswith("_cpu"):
        return name[:-len("_cpu")]
    else:
        return name

def precision_on_topk(predicts,reals,k):
    """
    Calculate precision at K (PR@K).

    Args:
        predicts: Ranked RCA predictions for each dataset case.
        reals: Ground-truth root causes for each dataset case.
        k: Number of top-ranked predictions to consider.

    Returns:
        The PR@K value across all dataset cases.
    """
    pr = 0
    for pred, real in zip(predicts, reals):
        pred = pred[:k]
        hit_count = len(set(pred) & set(real))
        min_len = min(k,len(real))
        pr += hit_count/min_len
    return pr/len(reals)

def mean_precision_k(predicts,reals,k):
    """
    Calculate the mean precision from rank 1 to K.

    The function calculates PR@1, PR@2, ..., PR@K and
    returns their average.

    Args:
        predicts: Ranked RCA predictions for each dataset case.
        reals: Ground-truth root causes for each dataset case.
        k: Maximum rank to consider.

    Returns:
        The mean precision value from rank 1 through K.
    """
    pr = 0
    for i in range(1,k+1):
        pr += precision_on_topk(predicts,reals,i)
    return pr/k

def mrr(predicts,reals):
    """
    Calculate Mean Reciprocal Rank (MRR).

    For each dataset case, the reciprocal of the rank of the
    first correctly identified ground-truth root cause is
    calculated. The final MRR is the average over all cases.

    Args:
        predicts: Ranked RCA predictions for each dataset case.
        reals: Ground-truth root causes for each dataset case.

    Returns:
        The mean reciprocal rank across all dataset cases.
    """
    mrr_val = 0
    for preds,real in zip(predicts,reals):
        tmp = []
        for real_item in real:
            index = preds.index(real_item) if real_item in preds else sys.maxsize-1
            tmp.append(index+1)
        mrr_val += 1/min(tmp)
    return mrr_val/len(reals)

def main():
    """
    The function parses command-line arguments, loads the
    corresponding RCA results, calculates the evaluation metrics,
    prints the results, and saves them to a CSV file.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Evaluate RCA results.")
    parser.add_argument("--dataset", choices=["rcaeval", "lemma"], required=True)
    parser.add_argument("--method", choices=["baro", "rcd", "epsilon", "circa"], required=True)
    args = parser.parse_args()
    DATASET = args.dataset
    METHOD = args.method

    # Select dataset configuration
    if DATASET.lower() == "rcaeval":
        base_path = RCAEval_BASE_PATH
        folders = RCAEval_FOLDERS
        reals = RCAEval_GROUND_TRUTH
    elif DATASET.lower() == "lemma":
        base_path = LEMMA_BASE_PATH
        folders = LEMMA_FOLDERS
        reals = LEMMA_GROUND_TRUTH
    else:
        raise ValueError("Unknown dataset. Use 'rcaeval' or 'lemma'.")  

    # Check method
    if METHOD.lower() not in METHOD_FILES:
        raise ValueError("Unknown method. Use: baro, rcd, epsilon, or circa.")  

    method = METHOD.lower() 

    predicts = []   

    for fd in folders:
        filename = METHOD_FILES[method].format(folder=fd)
        file_path = os.path.join(base_path, fd, filename)
        print("\nReading:", file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Result file does not exist:\n{file_path}")
        df = pd.read_csv(file_path)
        df["pod"] = df["root_cause"].apply(remove_metric)   

        # Same pod may have both CPU and memory.
        # Keep the highest BARO score for that pod.
        pod_ranking = (df.groupby("pod", as_index=False)["score"].max().sort_values("score",ascending=False))
        pods = pod_ranking["pod"].tolist()
        predicts.append(pods)
        print("Top 10 pod predictions:")
        print(pod_ranking.head(10))
        print("Ground truth:")
        print(reals[len(predicts) - 1]) 

    # Evaluation metrics
    k_values = [1,3,5,7,10]

    print("\n" + "*" * 50)
    print(f"{method.upper()} evaluation")
    print(f"Dataset: {DATASET.upper()}")
    print("*" * 50)

    results = []

    for item in k_values:
        pr = precision_on_topk(predicts,reals,item)
        map_val = mean_precision_k(predicts,reals,item)
        mrr_val = mrr(predicts,reals)
        #print("pr@{}:{} map@{}:{} mrr:{}".format(item,pr,item,map_val,mrr_val))
        print(f"pr@{item}:{pr:.3f} map@{item}:{map_val:.3f} mrr:{mrr_val:.3f}")
        results.append({"k": item, "PR@K": pr, "MAP@K": map_val, "MRR": mrr_val})

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)

    # Save as CSV
    output_file = os.path.join(base_path, f"{method}_evaluation.csv") 
    results_df.to_csv(output_file, index=False, float_format="%.3f")

    print(f"\nEvaluation results saved to: {output_file}")

if __name__ == "__main__":
    main()

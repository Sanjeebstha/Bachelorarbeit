import numpy as np
import sys

# Compatibility shim: allow loading .npy/.pkl files pickled under NumPy >=2.0
# ('numpy._core') using this NumPy 1.x environment ('numpy.core').
sys.modules.setdefault('numpy._core', np.core)
sys.modules.setdefault('numpy._core.multiarray', np.core.multiarray)
sys.modules.setdefault('numpy._core.umath', np.core.umath)
import pandas as pd
from sklearn import preprocessing
import os
from sklearn.feature_selection import VarianceThreshold
from sklearn.model_selection import train_test_split
from causalnex.structure.notears import from_pandas
from pyrca.analyzers.ht import HT, HTConfig
from pyrca.analyzers.epsilon_diagnosis import EpsilonDiagnosis, EpsilonDiagnosisConfig
from pyrca.analyzers.rcd import RCD, RCDConfig
# from pyrca.analyzers
import networkx as nx
import argparse

def remove_cycles_from_adjacency_matrix(adj_matrix: pd.DataFrame) -> pd.DataFrame:
    G = nx.from_pandas_adjacency(adj_matrix, create_using=nx.DiGraph())
    while True:
        try:
            cycle = nx.find_cycle(G, orientation='original')
            G.remove_edge(*cycle[0][:2])
        except nx.NetworkXNoCycle:
            break
    adj_matrix_no_cycles = nx.to_pandas_adjacency(G, dtype=int)
    adj_matrix_no_cycles = adj_matrix_no_cycles.reindex_like(adj_matrix)
    print("Now, the adjacency matrix does not have cycles.")
    return adj_matrix_no_cycles

def main(args):
    model_name = args.model
    data_name = args.case
    metric_data = {}
    columns_common = {}
    if args.feature_dir is not None:
        metric_path = args.feature_dir
    else:
        metric_path = '../data/{}'.format(data_name)
    # RCAEval cases
    if data_name.startswith("re2tt_"):
        label = data_name
    else:
        # Original LEMMA-RCA cases
        if data_name == '20220606':
            label = 'reviews-v3'
        else:
            raise ValueError('Invalid data_name')

    if data_name.startswith("re2tt_"):
        POD_METRIC_FILE = {'log_golden_signal': 1, 'log_frequency': 1}
        log_label = data_name
    elif data_name in ['20220606']:
        #POD_METRIC_FILE = {'log_golden_signal': 1, 'log_frequency': 1, 'cpu_usage': 1, 'memory_usage': 1, 'rate_received_packets': 1, 'rate_transmitted_packets': 1, 'received_bandwidth': 1, 'transmit_bandwidth': 1}
        POD_METRIC_FILE = {'log_golden_signal': 1, 'log_frequency': 1}
        log_label = 'ratings.book-info.svc.cluster.local:9080/*'
    else:
        raise ValueError('Invalid data_name')


    pathset = "/mnt/hdd/sanjeeb_shrestha/RCAEval/"
    if not (os.path.exists(pathset)):
        os.mkdir(pathset)
    for metric, weight in POD_METRIC_FILE.items():
        if metric in ['log_golden_signal', 'log_frequency']:
            if data_name.startswith("re2tt_"):
                metric_file = '{}/pod_level_{}.npy'.format(metric_path, metric)
                print("Loading RCAEval feature:", metric_file)
                raw = np.load(metric_file, allow_pickle=True).item()
                metric_data[metric] = {
                label: {
                    'Pod_Name': raw['Container_Name'],
                    'Sequence': raw['Sequence'].squeeze().T,
                    'KPI_Feature': [raw['KPI_Feature']],
                    'time': raw['time']
                }
            }
            else:
                # Original LEMMA-RCA loading
                metric_file = '{}/pod_level_{}.npy'.format(metric_path, metric)
                metric_data[metric] = np.load(metric_file, allow_pickle=True).item()
                # log_label = 'ratings.book-info.svc.cluster.local:9080/*'
                if len(metric_data[metric].keys()) == 1:
                    if log_label != label:
                        metric_data[metric][label] = metric_data[metric][log_label]
                        del metric_data[metric][log_label]
                else:
                    metric_data[metric][label] = metric_data[metric]
                metric_data[metric][label]['Pod_Name'] = metric_data[metric][label]['Container_Name']
                del metric_data[metric][label]['Container_Name']
                metric_data[metric][label]['Sequence'] = metric_data[metric][label]['Sequence'].squeeze().T
                metric_data[metric][label]['KPI_Feature'] = [metric_data[metric][label]['KPI_Feature']]
            if columns_common:
                columns_common = list(set(metric_data[metric][label]['Pod_Name']).intersection(columns_common))
            else:
                columns_common = list(metric_data[metric][label]['Pod_Name'])
        else:
            metric_file = '{}/pod_level_data_{}.npy'.format(metric_path, metric)
            metric_data[metric] = np.load(metric_file, allow_pickle=True).item()
            if columns_common:
                columns_common = list(set(metric_data[metric][label]['Pod_Name']).intersection(columns_common))
            else:
                columns_common = list(metric_data[metric][label]['Pod_Name'])

    index_data = {}
    metric_names = []
    metric_weight_assigned = []

    for metric, weight in POD_METRIC_FILE.items():
        index_data[metric] = [metric_data[metric][label]['Pod_Name'].index(x) for x in columns_common]
        metric_names = metric_names + [metric]
        metric_weight_assigned = metric_weight_assigned + [weight]

    metric_weight = np.zeros((len(POD_METRIC_FILE), 1))
    metric_id = 0
    final_root_results = {}

    for metric in metric_names:
        print('For metric:', metric)
        data = metric_data[metric]
        X = data[label]['Sequence']
        index = index_data[metric]
        if data_name.startswith("re2tt_"):
            # RCAEval already has a relatively small number of sliding-window observations.
            # Do not not aggregate every 20 samples.
            X_metric = X[:, index]
            X_metric = preprocessing.normalize(X_metric, axis=0, norm='l1')

            # RCAEval Sequence contains service/entity columns only.
            # Do not append X[:, -1] as a KPI.
            X = X_metric
            columns = list(columns_common)
        else:
            # Preprocessing to reduce the redundant samples
            if X.shape[0] // 100 < 100:
                patch = 20
            else:
                patch = 100
            sample = X.shape[0] // patch
            X = X[:patch * sample, :]
            X = np.sum(X.reshape((-1, patch, X.shape[1])), axis=1)
            X_metric = X[:, index]
            X_metric = preprocessing.normalize(X_metric, axis=0, norm='l1')
            X = np.append(X_metric, X[:, -1].reshape(-1, 1), axis=1)
            columns = list(columns_common) + data[label]['KPI_Feature']
        if data_name.startswith("re2tt_"):
            feature_X = X
        else:
            feature_X = X[:, :-1]
        std = np.std(feature_X, axis=0)
        idx_std = [i for i, x in enumerate(std > 1e-5) if x]
        if len(idx_std) == 0:
            metric_weight[metric_id] = 0
            metric_id += 1
            print(metric, ' all pods are all constant or quasi-constant')
            continue

        selector = VarianceThreshold(threshold=0)
        X_var = selector.fit_transform(feature_X)
        idx = selector.get_support(indices=True)

        if X_var.shape[1] < 1:
            metric_weight[metric_id] = 0
            metric_id = metric_id + 1
            print(metric, ' all pods are all constant or quasi-constant')
            continue

        mask = np.full(len(columns_common), False, dtype=bool)
        mask[idx] = True
        if data_name.startswith("re2tt_"):
        # RCAEval: all columns are services
            idx = list(idx)
        else:
            idx = list(idx) + [X.shape[1] - 1]
        X = X[:, idx]
        columns = [columns[i] for i in idx]
        X = pd.DataFrame(X, columns=columns)
        if model_name == 'circa':
            sm = from_pandas(X)
            estimated_matrix = nx.to_pandas_adjacency(sm)
            quantile_value = np.quantile(estimated_matrix.values.flatten(), 0.95)
            estimated_matrix = (estimated_matrix > quantile_value).astype(int)
            estimated_matrix = remove_cycles_from_adjacency_matrix(estimated_matrix)

        #X.insert(0, 'time', pd.date_range(start='2024-01-01', periods=len(X), freq='D'))
        #X['time'] = X['time'].astype('int64') // 1_000_000_000
        #X.columns = [f"{col}_cpu" if i < 9 else f"{col}_memory" for i, col in enumerate(X.columns)]

        if data_name.startswith("re2tt_"):
        # Every column is a service/entity
            denominator = X.max() - X.min()
            # Prevent division by zero
            denominator = denominator.replace(0, 1)
            X = (X - X.min()) / denominator
        else:
            denominator = (X.iloc[:, 1:].max() - X.iloc[:, 1:].min())
            denominator = denominator.replace(0, 1)
            X.iloc[:, 1:] = (X.iloc[:, 1:] - X.iloc[:, 1:].min()) / denominator
            
        # Normal/fault split
        if data_name.startswith("re2tt_") and args.injection_time is not None:
            # RCAEval saves one timestamp for every extracted feature window.
            feature_time = np.asarray(data[label]['time']).reshape(-1)
            if len(feature_time) != len(X):
                raise ValueError("Time/feature length mismatch for {}: len(time)={} but RCA input has {} rows.".format(metric, len(feature_time), len(X)))
            # Before fault injection = normal reference distribution.
            # At/after fault injection = anomalous/fault distribution.
            normal_mask = feature_time < args.injection_time
            fault_mask = feature_time >= args.injection_time

            X_train = X.loc[normal_mask].copy()
            X_test = X.loc[fault_mask].copy()

            print("\n--- RCAEval injection-time split ---")
            print("Full RCA input:", X.shape)
            print("Feature time range:", int(feature_time[0]), "-", int(feature_time[-1]))
            print("Injection time:", args.injection_time)
            print("Normal/train:", X_train.shape)
            print("Fault/test:", X_test.shape)

            if len(X_train) == 0:
                raise ValueError("No normal windows before injection_time {}.".format(args.injection_time))
            if len(X_test) == 0:
                raise ValueError("No fault windows at/after injection_time {}.".format(args.injection_time))
        else:
            # if an RCAEval run is intentionally made without injection time.
            X_train, X_test = train_test_split(X, test_size=0.6, shuffle=False)
            print("\n--- Chronological 40/60 split ---")
            print("Full RCA input:", X.shape)
            print("Train:", X_train.shape)
            print("Test:", X_test.shape)

        # Normal vs Fault statistics
        print("\n--- Normal vs Fault Statistics ---")
        print("Number of columns:", len(X.columns))
        print("Columns:", list(X.columns))

        statistics = []
        for col in X.columns:
            train_mean = X_train[col].mean()
            test_mean = X_test[col].mean()
            train_std = X_train[col].std()
            test_std = X_test[col].std()
            difference = abs(test_mean - train_mean)
            statistics.append((col, train_mean, test_mean, difference, train_std, test_std))

        # Largest normal-to-fault changes first.
        statistics.sort(key=lambda item: item[3], reverse=True)
        for col, train_mean, test_mean, difference, train_std, test_std in statistics:
            marker = ""
            if args.root_cause is not None and col == args.root_cause:
                marker = "  <-- TRUE ROOT CAUSE"
            print(
                "{:<40} normal={:.6f} fault={:.6f} "
                "diff={:.6f} normal_std={:.6f} fault_std={:.6f}{}".format(
                    col,
                    train_mean,
                    test_mean,
                    difference,
                    train_std,
                    test_std,
                    marker
                )
            )

        # Diagnostic only; ground truth is NOT passed to RCD.
        if args.root_cause is not None:
            retained = args.root_cause in X.columns
            print("Root cause retained:", "YES" if retained else "NO", "->", args.root_cause)
            if not retained:
                print("Entities passed to RCA:", list(X.columns))

        if model_name == 'rcd':
            model = RCD(config=RCDConfig(k=3,alpha_limit=0.5))
            results = model.find_root_causes(X_train, X_test).to_list()
            print(results)
        elif model_name == 'circa':
            model = HT(config=HTConfig(graph=estimated_matrix, root_cause_top_k=10))
            model.train(X_train)
            results = model.find_root_causes(X_test, metric_data[metric][label]['KPI_Feature'][0], True).to_list()
        elif model_name == 'epsilon_diagnosis':
            model = EpsilonDiagnosis(config=EpsilonDiagnosisConfig(root_cause_top_k=10))
            model.train(X)
            results = model.find_root_causes(X).to_list()
        else:
            raise ValueError('Invalid model_name')

        root_causes = []
        for result in results:
            root_causes.append([result['root_cause'], result['score']])

        root_causes = pd.DataFrame(root_causes, columns=['root_cause', 'score'])
        # Change path
        root_causes.to_csv("/mnt/hdd/sanjeeb_shrestha/final/preprocessing/re2tt_ts-order-service_delay_2/test/step5/rcd/re2tt_ts-order-service_delay_2/{}_{}_{}_root_cause.csv".format(metric, model_name, data_name), index=False)
        #root_causes.to_csv("/mnt/hdd/sanjeeb_shrestha/RCAEval/epsilon_diagnosis/{}_results/{}/{}_{}_{}_root_cause.csv".format(model_name, data_name, metric, model_name, data_name), index=False)
        final_root_results[metric] = root_causes

    # Combine log_frequency + log_golden_signal
    concatenated_df = pd.concat(final_root_results.values(), ignore_index=True)
    # Change path
    concatenated_df.to_csv("/mnt/hdd/sanjeeb_shrestha/final/preprocessing/re2tt_ts-order-service_delay_2/test/step5/rcd/re2tt_ts-order-service_delay_2/concated_df.csv")
    #concatenated_df.to_csv("/mnt/hdd/sanjeeb_shrestha/RCAEval/epsilon_diagnosis/{}_results/{}/concated_df.csv".format(model_name, data_name), index=False)

    aggregated_df = concatenated_df.groupby('root_cause')['score'].sum().reset_index()
    aggregated_df = aggregated_df.sort_values(by='score',ascending=False)
    # Change path
    aggregated_df.to_csv("/mnt/hdd/sanjeeb_shrestha/final/preprocessing/re2tt_ts-order-service_delay_2/test/step5/rcd/re2tt_ts-order-service_delay_2/final_{}_{}_root_cause.csv".format(model_name, data_name), index=False)
    #aggregated_df.to_csv("/mnt/hdd/sanjeeb_shrestha/RCAEval/epsilon_diagnosis/{}_results/{}/final_{}_{}_root_cause.csv".format(model_name, data_name, model_name, data_name), index=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Baro')
    parser.add_argument("--case", type=str, default='re2tt-ts-order-service_delay_2', help="case of the dataset")
    parser.add_argument("--model", type=str, default='rcd', help="model name, [rcd, circa, epsilon_diagnosis], default is rcd")
    parser.add_argument("--feature_dir", type=str, default=None, help="Directory containing log_frequency.npy and log_golden_signal.npy")
    parser.add_argument("--injection_time", type=int, default=None, help="Fault injection Unix timestamp for RCAEval")
    parser.add_argument("--root_cause", type=str, default=None, help="Ground-truth root cause; used for diagnostics/evaluation only")
    parser.set_defaults(validation=True)
    args = parser.parse_args()
    main(args)
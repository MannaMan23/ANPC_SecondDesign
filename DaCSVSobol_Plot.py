import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # rimuovi se vuoi finestre
import matplotlib.pyplot as plt
from SALib.analyze import sobol

# === CONFIG ===
results_folder = r"C:\Users\Marianna\Documents\LTspice\Simulazioni_Automatizzate\Modello_RoHM_Vout\Paper_Grafici"
csv_path = os.path.join(results_folder, "Dataframe_VoutAnalysis_HS1.csv")
out_dir  = os.path.join(results_folder, "Correzione Graficos_Sobol")
os.makedirs(out_dir, exist_ok=True)

# --- util ---
def ensure_id(df: pd.DataFrame) -> pd.DataFrame:
    if 'id' not in df.columns:
        df = df.copy()
        df['id'] = np.arange(len(df))
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    return df.sort_values('id').reset_index(drop=True)

def detect_params(df: pd.DataFrame):
    exclude = {'id','overshoot','damping','status','exit_code','stderr'}
    params = [c for c in df.columns if c not in exclude]
    if not params:
        raise ValueError("Nessun parametro trovato nel CSV.")
    D = len(params)
    problem = {"num_vars": D, "names": params, "bounds": [[0,1]]*D}
    return problem, params, D

def build_Y_from_blocks(df: pd.DataFrame, col: str, block: int):
    """Concatena SOLO i blocchi completi (senza NaN) di lunghezza block (=2D+2)."""
    y = df[col]
    Y_list = []
    n = len(y)
    for start in range(0, n - (block - 1), block):
        chunk = y.iloc[start:start+block]
        if not chunk.isna().any():
            Y_list.append(chunk.to_numpy())
    return (np.concatenate(Y_list) if Y_list else np.array([]),
            len(Y_list))

# def plot_basic_bars(Si, names, title, save_path):
#     x = np.arange(len(names)); w = 0.35
#     fig, ax = plt.subplots(figsize=(10,5))
#     ax.bar(x - w/2, Si['S1'], w, label='S1')
#     ax.bar(x + w/2, Si['ST'], w, label='ST')
#     ax.set_xticks(x); ax.set_xticklabels(names, rotation=45, ha='right')
#     ax.set_ylabel('Indice di sensibilità'); ax.set_title(title)
#     ax.legend(); ax.grid(True, axis='y', linestyle=':', linewidth=0.8, alpha=0.6)
#     plt.tight_layout(); plt.savefig(save_path, dpi=150); plt.close()
#     print("✓ salvato", save_path)


def plot_basic_bars(Si, names, title, save_path):
    x = np.arange(len(names)); w = 0.35
    fig, ax = plt.subplots(figsize=(7,4))   # compatto per una colonna

    ax.bar(x - w/2, Si['S1'], w, label='S1', color='navy')
    ax.bar(x + w/2, Si['ST'], w, label='ST', color='red')

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=90, ha='right', fontsize=14, fontweight='bold')

    ax.set_ylabel('Sensitivity Index', fontsize=15, fontweight='bold')
    # ax.set_title(title, fontsize=17, fontweight='bold')

    ax.legend(fontsize=11)
    ax.grid(True, axis='y', linestyle=':', linewidth=0.8, alpha=0.6)
    ax.tick_params(axis='y', labelsize=11)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)  # alta qualità per stampa
    plt.close()
    

def save_indices_csv(Si, names, save_path):
    pd.DataFrame({"name": names, "S1": Si["S1"], "ST": Si["ST"]}).to_csv(save_path, index=False)
    print("✓ salvato", save_path)

def scatter_all(df: pd.DataFrame, output_col: str, save_dir: str, title_prefix: str):
    inputs = [c for c in df.columns if c not in {'id','overshoot','damping','status','exit_code','stderr'}]
    for name in inputs:
        plt.figure(figsize=(6,4))
        plt.scatter(df[name], df[output_col], alpha=0.5)
        if name.startswith("L_"):
            plt.xscale("log")
        plt.xlabel(name); plt.ylabel(output_col)
        plt.title(f"{title_prefix} {name}")
        plt.grid(True, linestyle=':', linewidth=0.8, alpha=0.6)
        plt.tight_layout()
        path = os.path.join(save_dir, f"Scatter_{output_col}_vs_{name}.png")
        plt.savefig(path, dpi=130); plt.close()








# === MAIN ===
def main():
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV non trovato: {csv_path}")
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("CSV vuoto.")
    df = ensure_id(df)

    problem, names, D = detect_params(df)
    block = 2*D + 2
    print(f"Parametri: {names}  |  D={D}  |  block={block}")

    # --- Overshoot ---
    Y_over, n_blocks_over = build_Y_from_blocks(df, 'overshoot', block)
    if len(Y_over) < block:
        raise RuntimeError("Overshoot: nessun blocco completo (2D+2) disponibile.")
    Si_over = sobol.analyze(problem, Y_over, calc_second_order=False)
    plot_basic_bars(Si_over, names, "Overshoot Vout",
                    os.path.join(out_dir, "Sobol_overshoot_basic.png"))
    save_indices_csv(Si_over, names, os.path.join(out_dir, "Sobol_overshoot_basic.csv"))
    # scatter (opzionale, usa solo il prefisso necessario ai blocchi usati)
    df_over = df.iloc[:n_blocks_over*block]
    scatter_all(df_over, 'overshoot', out_dir, "Overshoot vs")

    # --- Damping ---
    Y_damp, n_blocks_damp = build_Y_from_blocks(df, 'damping', block)
    if len(Y_damp) < block:
        raise RuntimeError("Damping: nessun blocco completo (2D+2) disponibile.")
    Si_damp = sobol.analyze(problem, Y_damp, calc_second_order=False)
    plot_basic_bars(Si_damp, names, "Damping Vout",
                    os.path.join(out_dir, "Sobol_damping_basic.png"))
    # save_indices_csv(Si_damp, names, os.path.join(out_dir, "Sobol_damping_basic.csv"))
    # df_damp = df.iloc[:n_blocks_damp*block]
    # scatter_all(df_damp, 'damping', out_dir, "Damping vs")

    print("\nCompletato. File in:", out_dir)

if __name__ == "__main__":
    main()
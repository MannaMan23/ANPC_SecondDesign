import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # disabilita finestre grafiche
import matplotlib.pyplot as plt
from SALib.analyze import sobol

# === CONFIG ===
results_folder = r"c:\Users\Marianna\Documents\LTspice\Simulazioni_Automatizzate\ControlLoop\VGS_HS_Only"
csv_path = os.path.join(results_folder, "Dataframe_Vgs_HS.csv")
out_dir = os.path.join(results_folder, "Sobol_Results")
os.makedirs(out_dir, exist_ok=True)

# usa sempre lo stesso flag qui e nella analyze()
CALC_SECOND_ORDER = False  # se usi campionamento senza second order, lascia False

# === UTILITY ===
def ensure_id(df: pd.DataFrame) -> pd.DataFrame:
    if 'id' not in df.columns:
        df = df.copy()
        df['id'] = np.arange(len(df))
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    return df.sort_values('id').reset_index(drop=True)

def detect_params(df: pd.DataFrame):
    """
    Riconosce i parametri di input come colonne numeriche che iniziano con R_ o L_.
    Esclude output e colonne non rilevanti.
    """
    exclude = {
        'id',
        'overshoot_vgs1', 'damping_vgs1',
        'overshoot_vgs2', 'damping_vgs2',
        'status', 'exit_code', 'stderr'
    }
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    params = [c for c in numeric_cols if c not in exclude and (c.startswith("R_") or c.startswith("L_"))]
    if not params:
        raise ValueError("⚠ Nessun parametro R_/L_ trovato nel CSV.")
    D = len(params)
    problem = {"num_vars": D, "names": params, "bounds": [[0, 1]] * D}
    return problem, params, D

def build_Y_from_blocks(df: pd.DataFrame, col: str, block: int):
    """
    Concatena SOLO i blocchi completi (senza NaN) di lunghezza 'block':
    block = D+2 se CALC_SECOND_ORDER=False, altrimenti 2D+2.
    """
    y = df[col]
    Y_list = []
    n = len(y)
    for start in range(0, n - (block - 1), block):
        chunk = y.iloc[start:start + block]
        if not chunk.isna().any():
            Y_list.append(chunk.to_numpy())
    return (np.concatenate(Y_list) if Y_list else np.array([]), len(Y_list))

def plot_basic_bars(Si, names, title, save_path):
    x = np.arange(len(names)); w = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - w/2, Si['S1'], w, label='S1')
    ax.bar(x + w/2, Si['ST'], w, label='ST')
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=45, ha='right')
    ax.set_ylabel('Indice di sensibilità')
    ax.set_title(title)
    ax.legend(); ax.grid(True, axis='y', linestyle=':', linewidth=0.8, alpha=0.6)
    plt.tight_layout(); plt.savefig(save_path, dpi=150); plt.close()
    print("✓ Salvato grafico:", save_path)

def save_indices_csv(Si, names, save_path):
    pd.DataFrame({
        "name": names,
        "S1": Si["S1"], "S1_conf": Si.get("S1_conf", np.nan),
        "ST": Si["ST"], "ST_conf": Si.get("ST_conf", np.nan)
    }).to_csv(save_path, index=False)
    print("✓ Salvato CSV:", save_path)

def scatter_all(df: pd.DataFrame, output_col: str, save_dir: str, title_prefix: str):
    # scatter solo per input R_* e L_*
    inputs = [c for c in df.columns if (c.startswith("R_") or c.startswith("L_"))]
    for name in inputs:
        plt.figure(figsize=(6, 4))
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
        raise FileNotFoundError(f"❌ CSV non trovato: {csv_path}")
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("❌ CSV vuoto.")
    df = ensure_id(df)

    problem, names, D = detect_params(df)
    block = (2 * D + 2) if CALC_SECOND_ORDER else (D + 2)
    print(f"Parametri trovati: {names}  |  D={D}  |  block={block}")

    outputs = [
        ("overshoot_vgs1", "Overshoot Vgs1"),
        ("damping_vgs1",  "Damping Vgs1"),
        ("overshoot_vgs2", "Overshoot Vgs2"),
        ("damping_vgs2",  "Damping Vgs2")
    ]

    for col, label in outputs:
        print(f"\n--- Analisi Sobol per {label} ---")
        if col not in df.columns:
            print(f"⚠ Colonna {col} mancante, salto...")
            continue

        Y, n_blocks = build_Y_from_blocks(df, col, block)
        if len(Y) < block:
            print(f"⚠ Nessun blocco completo per {col}, salto.")
            continue

        # debug utile
        print(f"[DEBUG] {col}: len(Y)={len(Y)} | n_blocchi_validi={n_blocks} | D={D} | block={block} | resto={len(Y) % block}")

        Si = sobol.analyze(problem, Y, calc_second_order=CALC_SECOND_ORDER)
        plot_basic_bars(Si, names, f"Sobol: {label}", os.path.join(out_dir, f"Sobol_{col}.png"))
        save_indices_csv(Si, names, os.path.join(out_dir, f"Sobol_{col}.csv"))

        df_used = df.iloc[:n_blocks * block]
        scatter_all(df_used, col, out_dir, label + " vs")

    print("\n✅ Analisi completata. Risultati salvati in:", out_dir)

if __name__ == "__main__":
    main()

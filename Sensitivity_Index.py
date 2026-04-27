import subprocess
import numpy as np
import pandas as pd
import os 
import ltspice
import shutil
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
# from SALib.sample import saltelli
from SALib.sample import sobol as sobol_sample
from SALib.analyze import sobol as sobol_analyze
from jinja2 import Environment, FileSystemLoader

# Confing: read LTSpice path and call templet .net
ltspice_exe = r"C:\Users\Marianna\AppData\Local\Programs\ADI\LTspice\LTspice.exe"
script_dir = os.path.dirname(os.path.abspath(__file__)) #Trovo path assoluto script Python
template_netlist = os.path.join(script_dir, "ANPC_Completo_PlaceHolder.net")
results_folder = os.path.join(script_dir, "ANPC_HS_SecondDesign")
os.makedirs(results_folder, exist_ok=True)
Autosave = 10
scatter_dir_vout = os.path.join(results_folder, "Scatter_vout")
os.makedirs(scatter_dir_vout, exist_ok=True)

# Parasitic parameter I try only with parasitic inductance
param_string = """
L_MP1
L_HS
L_H1H2
L_H1H3
L_BUSHS_SourceHS2
L_BUSHS_NP
"""

# Sample Saltelli creation
params = [p.strip() for p in param_string.strip().splitlines() if p.strip()]
num_vars = len(params)
# bounds = [[1e-3, 100e-3] if p.startswith('R_') else [1e-9, 10e-9] for p in params] # DEFINIRE RANGE ADATTO
min_common, max_common = 0.5e-9, 55.52e-9
bounds = []
for name in params:
    if name == "L_HS":
        bounds.append([0.5e-9, 71.20e-9])
    elif name == "L_LS":
        bounds.append([0.5e-9, 97.27e-9])
    elif name.startswith("L_"):
        bounds.append([min_common, max_common])
    # elif name.startswith("R_"):
        # bounds.append([1e-3, 100e-3])
    else:
        raise ValueError(f"Variabile non riconosciuta: {name}")

problem = {
    'num_vars': num_vars,
    'names': params,
    'bounds': bounds
}

# Function definition
def scrivi_netlist(inputs, sample_id):
    with open(template_netlist) as f:
        net = f.read()
    for name, val in inputs.items():
        net = net.replace(f'{{{{{name}}}}}', f'{val:.6e}')
        net_path = os.path.join(results_folder, f"run_{sample_id}.net") # Correggere qui con +1 per organizzare i pedici delle simulazioni
    with open(net_path, "w") as f:
        f.write(net)
    return net_path

def calculate_overshoot_damping(vout, Vdc):
    V1 = np.max(vout)
    max_index = np.argmax(vout)
    overshoot = V1 - Vdc    
    peaks, properties = find_peaks(vout, prominence=0.01) # Trova tutti i picchi
    if max_index not in peaks:
        peaks = np.append(peaks, max_index) # Il massimo assoluto non è stato identificato come picco. Forzatura manuale
        peaks = np.sort(peaks)    
    next_peaks = [p for p in peaks if p > max_index] # Trova il primo picco dopo il massimo
    delta = 0.0
    zeta = 0.0
    used_peaks = [max_index]

    if next_peaks:
        next_index = next_peaks[0]
        used_peaks.append(next_index)
        V2 = vout[next_index]
        if V1 > V2 > 0:
            delta = np.log(V1 / V2)
            zeta = delta / np.sqrt((2 * np.pi)**2 + delta**2)
    else:
        print("Nessun secondo picco successivo al massimo trovato.")

    return overshoot, zeta

   
    # Think about all transition (4 overshoot, 4 damping) 
def simula_estrai_overshoot_damping(net_path, Vdc): # Vdc è un valore numerico
    raw_path = net_path.replace('.net', '.raw') # path raw inizialization 
    # subprocess.run([ltspice_exe, "-b", net_path], check=True)
    # print("LTSpice è stato lanciato")
    lt = ltspice.Ltspice(raw_path)
    lt.parse()
    vout = lt.get_data('V(out)') 
    if vout is None:
        raise ValueError("Nessun nodo V(out)")
    overshoot, damping = calculate_overshoot_damping(vout, Vdc)
    return overshoot, damping

def pulisci_files(*paths):
    for path in paths:
        if os.path.exists(path):
            print(f"Eliminazione file: {path}")  # Debug
            os.remove(path)
        else:
            print(f"File non trovato: {path}")


def verifica_output(net_path):
    log_path = net_path.replace('.net', '.log')
    with open(log_path) as file:
            return "Simulation Failed" not in file.read()
    
def genera_parametri_random():
    return {
        name: np.random.uniform(low, high)
        for name, (low, high) in zip(problem['names'], problem['bounds'])
    }

def rilancia_simulazione(inputs, sample_id, max_tentativi=5, Vdc=500):
    tentativi = 0
    while True:
        net_path = scrivi_netlist(inputs, sample_id)
        print(f"Net list generato {net_path}")
        print(f"sample{sample}")   
        raw_path = net_path.replace('.net', '.raw')
        log_path = net_path.replace('.net', '.log')               
        while tentativi < max_tentativi:
            try:
                subprocess.run([ltspice_exe, "-b", net_path], check=True)
                if verifica_output(net_path):
                    overshoot, damping = simula_estrai_overshoot_damping(net_path, Vdc=500)
                    pulisci_files(net_path, log_path, raw_path)
                    return {'id': sample_id, **inputs, 'overshoot': overshoot, 'damping': damping}                    
                else:
                    net_path = os.path.join(results_folder, f"run_{sample_id}.net")
                    tentativi += 1
                    print(f"Tentativo {tentativi} fallito per {net_path}. Rilancio simulazione")
            except Exception as e:
                tentativi += 1
                print(f"Tentativo {tentativi+1} fallito: {e}")
            
        print(f"Simulazione fallita per {net_path}")
        inputs = {p: np.random.uniform(*bounds[i]) for i, p in enumerate(params)}
        tentativi = 0
        return overshoot, damping

def plot_indices(Si, title, save_path=None):
    names = problem['names']
    x = np.arange(len(names))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width/2, Si['S1'], width, label='S1')
    ax.bar(x + width/2, Si['ST'], width, label='ST')
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha='right')
    ax.set_ylabel('Indice di sensibilità')
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
        print(f"Grafico salvato in: {save_path}")
        plt.close()
    else:
        plt.show()


def scatterplot_inputs_vs_output(df, output_column, title_prefix="Scatter:", save_folder=None):
    import matplotlib.pyplot as plt

    input_columns = [col for col in df.columns if col not in ['id', 'overshoot', 'damping']]

    for name in input_columns:
        plt.figure(figsize=(6, 4))
        plt.scatter(df[name], df[output_column], alpha=0.5)
        plt.xlabel(name)
        plt.ylabel(output_column)
        plt.title(f"{title_prefix} {name}")
        plt.grid(True)
        plt.tight_layout()
        if save_folder:
            os.makedirs(save_folder, exist_ok=True)
            filename = f"SobolIndex_{output_column}_vs_{name}.png"
            save_path = os.path.join(save_folder, filename)
            plt.savefig(save_path)
            print(f" Grafico salvato in: {save_path}")
            plt.close()
        else:
            plt.show()

# Main
if __name__ == "__main__":
    N = 256  # Partire con valori bassi
    samples = sobol_sample.sample(problem, N, calc_second_order=False)
    print(f"Totale simulazioni da eseguire: {len(samples)}")

    results = []

    for i, sample in enumerate(samples):
        print(f"\n Simulazione {i+1}/{len(samples)}")
        inputs = dict(zip(params, sample))
        # net = scrivi_netlist(inputs, i)
        # print(f"Net list generato {net}")
        # print(f"sample{sample}")        
        try:
            result = rilancia_simulazione(inputs, i, max_tentativi=5, Vdc=500)
            results.append(result)
        except Exception as e:
            print(f"Simulazione {i} errore irreversibile: {e}")
        # finally:
        #     print(f"net {net}")
        #     #pulisci_files(net, net.replace('.net', '.raw')) ## Commento di prova per verificae corrispondenza net - simulazioni
        if (i + 1) % Autosave == 0:
            df_temp = pd.DataFrame(results)
            temp_path = os.path.join(results_folder, f"autosave_{i+1}.csv") # Csotruisce percorso temporaneo del file csv temporaneo
            df_temp.to_csv(temp_path, index=False) # Salva il DataFrame temporaneo in un file CSV 
            print(f"[AutoSave] Salvataggio automatico a {i+1} simulazioni → {temp_path}")


    df = pd.DataFrame(results)

    # Salvataggio risultati raw
    df.to_csv(os.path.join(results_folder, "Dataframe_Vout.csv"), index=False)

    ## Analisi Sobol overshoot
    #print("\n Overshoot")
    Y_overshoot = df['overshoot'].values
    mask_overshoot = ~np.isnan(Y_overshoot)
    X_overshoot = samples[mask_overshoot]  # puoi lasciarla, ma non serve più passarla

    Si_overshoot = sobol_analyze.analyze(problem, Y_overshoot[mask_overshoot], calc_second_order=False)
    plot_indices(Si_overshoot, "Sobol: Overshoot Vout", os.path.join(results_folder, "Sobol_overshoot_Vout.png"))
    scatterplot_inputs_vs_output(df, 'overshoot', title_prefix="Overshoot Vout vs", save_folder=scatter_dir_vout)

    # Analisi Sobol damping (Vgs1)
    Y_damping = df['damping'].values
    mask_damping = ~np.isnan(Y_damping)
    X_damping = samples[mask_damping]  # idem, non serve più

    Si_damping = sobol_analyze.analyze(problem, Y_damping[mask_damping], calc_second_order=False)
    plot_indices(Si_damping, "Sobol: Damping Vout", os.path.join(results_folder, "Sobol_damping_Vout.png"))
    scatterplot_inputs_vs_output(df, 'damping', title_prefix="Damping Vout vs", save_folder=scatter_dir_vout)

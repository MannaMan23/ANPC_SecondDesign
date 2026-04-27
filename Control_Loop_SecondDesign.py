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
template_netlist = os.path.join(script_dir, "ANPC_GateLoop_template.net") # Cmabiare nome
results_folder = os.path.join(script_dir, "ANPC_GateLoop_Res")
os.makedirs(results_folder, exist_ok=True)
Autosave = 10
scatter_dir_vgs1 = os.path.join(results_folder, "Scatter_vgs1")
os.makedirs(scatter_dir_vgs1, exist_ok=True)
scatter_dir_vgs2 = os.path.join(results_folder, "Scatter_vgs2")
os.makedirs(scatter_dir_vgs2, exist_ok=True)


# Parasitic parameter I try only with parasitic inductance
param_string = """
R_onHS1
R_offHS1
L_onHS1
L_offHS1
L_SKHS1
R_onHS2
R_offHS2
L_onHS2
L_offHS2
L_SKHS2
"""

# Sample Saltelli creation
params = [p.strip() for p in param_string.strip().splitlines() if p.strip()]
num_vars = len(params)
# bounds = [[1e-3, 100e-3] if p.startswith('R_') else [1e-9, 10e-9] for p in params] # DEFINIRE RANGE ADATTO
min_common, max_common = 0.5e-9, 55.51e-9
bounds = []
for name in params:
    if name.startswith("R_"):
        bounds.append([0.5, 20])
    elif name.startswith("L_"):
        bounds.append([min_common, max_common])
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


# def calculate_overshoot_damping_vgs1(vgs1, Vg):
#     V1 = np.max(vgs1)
#     max_index = np.argmax(vgs1)
#     overshoot_vgs1 = V1 - Vg    
#     peaks, properties = find_peaks(vgs1, prominence=0.01) # Trova tutti i picchi
#     if max_index not in peaks:
#         peaks = np.append(peaks, max_index) # Il massimo assoluto non è stato identificato come picco. Forzatura manuale
#         peaks = np.sort(peaks)    
#     next_peaks = [p for p in peaks if p > max_index] # Trova il primo picco dopo il massimo
#     delta = 0.0
#     zeta_vgs1 = 0.0
#     used_peaks = [max_index]

#     if next_peaks:
#         next_index = next_peaks[0]
#         used_peaks.append(next_index)
#         V2 = vgs1[next_index]
#         if V1 > V2 > 0:
#             delta = np.log(V1 / V2)
#             zeta_vgs1 = delta / np.sqrt((2 * np.pi)**2 + delta**2)
#     else:
#         print("Nessun secondo picco successivo al massimo trovato.")

#     return overshoot_vgs1, zeta_vgs1


def calculate_overshoot_damping_vgs1(vgs1, Vg, prominence=0.01,min_peaks=5):
    # Overshoot
    V1_abs = np.max(vgs1)
    overshoot_vgs1 = V1_abs - Vg

    # Ricerca dei picchi
    peaks, properties = find_peaks(
        vgs1,
        prominence=prominence
    )

    # Se i picchi sono troppo pochi → damping non affidabile
    if len(peaks) < min_peaks:
        print("Picchi insufficienti per il calcolo multi-peak di Vgs1.")
        return overshoot_vgs1, 0.0

    # Ordina temporalmente
    peaks = np.sort(peaks)

    # Usa i primi N picchi reali
    selected_peaks = peaks[:min_peaks]

    peak_values = vgs1[selected_peaks]

    # Controllo robustezza
    if np.any(peak_values <= 0):
        print("Picchi non validi (<= 0) in Vgs1.")
        return overshoot_vgs1, 0.0

    if not np.all(np.diff(peak_values) < 0):
        print("Attenzione: i picchi di Vgs1 non sono monotonicamente decrescenti.")

    # Multi-peak logarithmic decrement
    n = len(peak_values) - 1

    delta = (1 / n) * np.log(
        peak_values[0] / peak_values[-1]
    )

    # Damping ratio
    zeta_vgs1 = delta / np.sqrt(
        (2 * np.pi)**2 + delta**2
    )

    return overshoot_vgs1, zeta_vgs1


def calculate_overshoot_damping_vgs2(vgs2, Vg):
    V1 = np.max(vgs2)
    max_index = np.argmax(vgs2)
    overshoot_vgs2 = V1 - Vg    
    peaks, properties = find_peaks(vgs2, prominence=0.01) # Trova tutti i picchi
    if max_index not in peaks:
        peaks = np.append(peaks, max_index) # Il massimo assoluto non è stato identificato come picco. Forzatura manuale
        peaks = np.sort(peaks)    
    next_peaks = [p for p in peaks if p > max_index] # Trova il primo picco dopo il massimo
    delta = 0.0
    zeta_vgs2 = 0.0
    used_peaks = [max_index]

    if next_peaks:
        next_index = next_peaks[0]
        used_peaks.append(next_index)
        V2 = vgs2[next_index]
        if V1 > V2 > 0:
            delta = np.log(V1 / V2)
            zeta_vgs2 = delta / np.sqrt((2 * np.pi)**2 + delta**2)
    else:
        print("Nessun secondo picco successivo al massimo trovato.")

    return overshoot_vgs2, zeta_vgs2 


def calcola_minimo_vgs(vgs):
    vgs_min = np.min(vgs)
    return vgs_min


def simula_estrai_overshoot_damping_vg(net_path, Vg): # Vdc è un valore numerico può essere il Bus DC o la Vg
    raw_path = net_path.replace('.net', '.raw') # path raw inizialization 
    # subprocess.run([ltspice_exe, "-b", net_path], check=True)
    # print("LTSpice è stato lanciato")
    lt = ltspice.Ltspice(raw_path)
    lt.parse()
    vgs1 = lt.get_data('V(vg1)') - lt.get_data('V(vsk1)') # Analysis Vgs Gan1 and Gan2
    vgs2 = lt.get_data('V(vg2)') - lt.get_data('V(vsk2)')

    if vgs1 is None:
            raise ValueError("Nessun nodo V(gs1)")
    overshoot_vgs1, damping_vgs1 = calculate_overshoot_damping_vgs1(vgs1, Vg) 
    vgs1_min = calcola_minimo_vgs(vgs1) 
    if vgs2 is None:
        raise ValueError("Nessun nodo V(gs2)")
    overshoot_vgs2, damping_vgs2 = calculate_overshoot_damping_vgs2(vgs2, Vg)
    vgs2_min = calcola_minimo_vgs(vgs2)
    return overshoot_vgs1, damping_vgs1, vgs1_min, overshoot_vgs2, damping_vgs2, vgs2_min

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


def rilancia_simulazione(inputs, sample_id, max_tentativi=5, Vg=6):
    tentativi = 0
    net_path = scrivi_netlist(inputs, sample_id)
    print(f"Net list generato {net_path}")
    raw_path = net_path.replace('.net', '.raw')
    log_path = net_path.replace('.net', '.log')
    op_path = net_path.replace('.net', '.op.raw')

    while tentativi < max_tentativi:
        try:
            subprocess.run([ltspice_exe, "-b", net_path], check=True)
            if verifica_output(net_path):
                # Simulazione riuscita, processa i risultati
                overshoot_vgs1, damping_vgs1, vgs1_min, overshoot_vgs2, damping_vgs2, vgs2_min2 = simula_estrai_overshoot_damping_vg(net_path, Vg)
                pulisci_files(net_path, log_path, raw_path, op_path)  # Elimina i file solo se la simulazione ha successo
                return {
                'id': sample_id, **inputs,
                'overshoot_vgs1': overshoot_vgs1,
                'damping_vgs1': damping_vgs1,
                'vgs1_min': vgs1_min,
                'overshoot_vgs2': overshoot_vgs2,        
                'damping_vgs2': damping_vgs2,
                'vgs2_min': vgs2_min2}
            
            else:
                tentativi += 1
                print(f"Tentativo {tentativi} fallito per {net_path}. Rilancio simulazione")
        except Exception as e:
            tentativi += 1
            print(f"Tentativo {tentativi} fallito: {e}")

    print(f"Dopo {max_tentativi} tentativi, la simulazione {sample_id} è fallita. Genoro imput random.")
    nets_falliti_dir = os.path.join(script_dir, "net_fallite")
    os.makedirs(nets_falliti_dir, exist_ok=True)
    shutil.copy(net_path, os.path.join(nets_falliti_dir, f"failed_original_{sample_id}.net"))


    # Provo a rigenerare con nuovi input casuali
    nuovi_inputs = genera_parametri_random()
    net_path = scrivi_netlist(nuovi_inputs, sample_id)

    try:
        subprocess.run([ltspice_exe, "-b", net_path], check=True)
        if verifica_output(net_path):
            overshoot_vgs1, damping_vgs1, overshoot_vgs2, damping_vgs2 = simula_estrai_overshoot_damping_vg(net_path, Vg)
            pulisci_files(net_path, log_path, raw_path, op_path)  # Elimina i file solo se la simulazione ha successo
            return {
            'id': sample_id, **nuovi_inputs,
            'overshoot_vgs1': overshoot_vgs1,
            'damping_vgs1': damping_vgs1,
            'vgs1_min': vgs1_min,
            'overshoot_vgs2': overshoot_vgs2,        
            'damping_vgs2': damping_vgs2,
            'vgs2_min': vgs2_min2}
        else:
            print(f"La simulazione rigenerata {sample_id} è fallita.")
    except Exception as e:
        print(f"Errore nella simualzione con input rigenerati: {e}")

    # Se anche la rigenerazione fallisce
    print(f"Simulazione fallita per {net_path}. Salvo NaN per la simulazione {sample_id}")
    return {
    'id': sample_id, **inputs,
    'overshoot_vgs1': np.nan,
    'damping_vgs1':  np.nan,
    'vgs1_min': np.nan,
    'overshoot_vgs2': np.nan,
    'damping_vgs2':  np.nan,
    'vgs2_min': np.nan
}


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
    # samples = saltelli.sample(problem, N, calc_second_order=False)
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
            result = rilancia_simulazione(inputs, i, max_tentativi=5, Vg=6)
            results.append(result)
        except Exception as e:
            print(f"Simulazione {i} errore irreversibile: {e}")


        if (i + 1) % Autosave == 0:
            df_temp = pd.DataFrame(results)
            temp_path = os.path.join(results_folder, f"autosave_{i+1}.csv") # Csotruisce percorso temporaneo del file csv temporaneo
            df_temp.to_csv(temp_path, index=False) # Salva il DataFrame temporaneo in un file CSV 
            print(f"[AutoSave] Salvataggio automatico a {i+1} simulazioni → {temp_path}")

    df = pd.DataFrame(results)
    
    # Salvataggio risultati raw
    df.to_csv(os.path.join(results_folder, "Dataframe_Vgs_HS_Vgs_min.csv"), index=False)
    

    ## Analisi Sobol overshoot
    # print("\n Overshoot")
    # Y_overshoot = df['overshoot_vout'].values
    # mask_overshoot = ~np.isnan(Y_overshoot)
    # X_overshoot = samples[mask_overshoot]

    # Si_overshoot = sobol.analyze(problem, Y_overshoot[mask_overshoot], X=X_overshoot ,calc_second_order=False)
    # plot_indices(Si_overshoot, "Sobol: Overshoot", os.path.join(results_folder, "Sobol_overshoot_Vout.png"))
    # scatterplot_inputs_vs_output(df, 'overshoot', title_prefix="Overshoot Vout vs")

    # # Analisi Sobol damping
    # # print("\n Damping ")
    # Y_damping = df['damping_vout'].values
    # mask_damping = ~np.isnan(Y_damping)
    # X_damping = samples[mask_damping]
    # Si_damping = sobol.analyze(problem, Y_damping[mask_damping], X=X_damping, calc_second_order=False)
    # plot_indices(Si_damping, "Sobol: Damping",os.path.join(results_folder, "Sobol_damping_Vout.png"))
    # scatterplot_inputs_vs_output(df, 'damping', title_prefix="Damping Vout vs")


    Y_overshoot = df['overshoot_vgs1'].values
    mask_overshoot = ~np.isnan(Y_overshoot)
    X_overshoot = samples[mask_overshoot]  # puoi lasciarla, ma non serve più passarla

    Si_overshoot = sobol_analyze.analyze(problem, Y_overshoot[mask_overshoot], calc_second_order=False)
    plot_indices(Si_overshoot, "Sobol: Overshoot vgs1", os.path.join(results_folder, "Sobol_overshoot_Vgs1.png"))
    scatterplot_inputs_vs_output(df, 'overshoot_vgs1', title_prefix="Overshoot Vgs1 vs", save_folder=scatter_dir_vgs1)

    # Analisi Sobol damping (Vgs1)
    Y_damping = df['damping_vgs1'].values
    mask_damping = ~np.isnan(Y_damping)
    X_damping = samples[mask_damping]  # idem, non serve più

    Si_damping = sobol_analyze.analyze(problem, Y_damping[mask_damping], calc_second_order=False)
    plot_indices(Si_damping, "Sobol: Damping vgs1", os.path.join(results_folder, "Sobol_damping_Vgs1.png"))
    scatterplot_inputs_vs_output(df, 'damping_vgs1', title_prefix="Damping Vgs1 vs", save_folder=scatter_dir_vgs1)

    Y_vgs1_min = df['vgs1_min'].values
    mask_vgs1_min = ~np.isnan(Y_vgs1_min)
    X_vgs1_min = samples[mask_vgs1_min]  # idem, non serve più

    Si_vgs1_min = sobol_analyze.analyze(problem, Y_vgs1_min[mask_vgs1_min], calc_second_order=False)
    plot_indices(Si_vgs1_min, "Sobol: Vgs1 Min", os.path.join(results_folder, "Sobol_vgs1_min.png"))
    scatterplot_inputs_vs_output(df, 'vgs1_min', title_prefix="Vgs1 Min vs", save_folder=scatter_dir_vgs1)

    # Overshoot (Vgs2)
    Y_overshoot = df['overshoot_vgs2'].values
    mask_overshoot = ~np.isnan(Y_overshoot)
    X_overshoot = samples[mask_overshoot]

    Si_overshoot = sobol_analyze.analyze(problem, Y_overshoot[mask_overshoot], calc_second_order=False)
    plot_indices(Si_overshoot, "Sobol: Overshoot vgs2", os.path.join(results_folder, "Sobol_overshoot_Vgs2.png"))
    scatterplot_inputs_vs_output(df, 'overshoot_vgs2', title_prefix="Overshoot Vgs2 vs", save_folder=scatter_dir_vgs2)

    # Damping (Vgs2)
    Y_damping = df['damping_vgs2'].values
    mask_damping = ~np.isnan(Y_damping)
    X_damping = samples[mask_damping]

    Si_damping = sobol_analyze.analyze(problem, Y_damping[mask_damping], calc_second_order=False)
    plot_indices(Si_damping, "Sobol: Damping vgs2", os.path.join(results_folder, "Sobol_damping_Vgs2.png"))
    scatterplot_inputs_vs_output(df, 'damping_vgs2', title_prefix="Damping Vgs2 vs", save_folder=scatter_dir_vgs2)

    Y_vgs2_min = df['vgs2_min'].values
    mask_vgs2_min = ~np.isnan(Y_vgs2_min)
    X_vgs2_min = samples[mask_vgs2_min]

    Si_vgs2_min = sobol_analyze.analyze(problem, Y_vgs2_min[mask_vgs2_min], calc_second_order=False)
    plot_indices(Si_vgs2_min, "Sobol: Vgs2 Min", os.path.join(results_folder, "Sobol_vgs2_min.png"))
    scatterplot_inputs_vs_output(df, 'vgs2_min', title_prefix="Vgs2 Min vs", save_folder=scatter_dir_vgs2)







import os

# === Parametri da sostituire (gli stessi che usi in SALib)
param_string = """"
L_MP1
L_HS
L_H1H2
L_H1H3
L_BUSHS_SourceHS2
L_BUSHS_NP
"""
params = [p.strip() for p in param_string.strip().splitlines() if p.strip()]

# === Mappa parametri ai nomi dei componenti nel netlist
# Es: mappa "R_MP1" a una linea che contiene "R1" o simili
# Qui si assume che il nome del parametro appaia nel file
param_map = {p: p for p in params}  # può essere esteso se servono alias

# === File input/output
script_dir = os.path.dirname(os.path.abspath(__file__))
netlist_path = os.path.join(script_dir, "ANPC_HS.net")
template_path = os.path.join(script_dir, "ANPC_Completo_PlaceHolder.net")

with open(netlist_path, "r") as f:
    lines = f.readlines()

new_lines = []

for line in lines:
    modified = False
    for param in params:
        if param in line:
            parts = line.strip().split()
            if len(parts) >= 4:
                # Sostituisci l'ultima colonna con {{ PARAM }}
                parts[-1] = f"{{{{{param}}}}}"
                line = " ".join(parts) + "\n"
                modified = True
                break
    new_lines.append(line)

with open(template_path, "w") as f:
    f.writelines(new_lines)

print(f"Template generato: {template_path}")
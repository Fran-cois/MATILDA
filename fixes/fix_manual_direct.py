#!/usr/bin/env python3
# fix_manual_direct.py - Correction manuelle directe des algorithmes Java

import os

def fix_dfd():
    """Correction manuelle directe pour DFD"""
    file_path = "src/algorithms/dfd.py"
    print(f"Correction manuelle de DFD: {file_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Chercher la section problématique
    start_line = 0
    end_line = 0
    for i, line in enumerate(lines):
        if "metanome_cli_jar =" in line:
            start_line = i
        if "cmd_string = (" in line and start_line > 0 and end_line == 0:
            end_line = i
    
    if start_line > 0 and end_line > 0:
        # Remplacer la section problématique
        replacement = [
            "                # Ajouter tous les JAR du répertoire dans le classpath\n",
            "                all_jars = [f\"{jar_path}{jar_file}\" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]\n",
            "                classpath = \":\".join(all_jars)\n",
            "\n",
            "                cmd_string = (\n",
            "                    f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n",
            "                    f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"\n",
            "                    f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n",
            "                    f\"\"\"--output file:{file_name}\"\"\"\n",
            "                )\n",
        ]
        
        # Remplacer les lignes
        new_lines = lines[:start_line] + replacement + lines[end_line + 6:]  # +6 pour inclure toutes les lignes de cmd_string
        
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        
        print(f"✅ DFD corrigé manuellement")
    else:
        print(f"❌ Impossible de trouver la section à corriger dans DFD")

def fix_fastfds():
    """Correction manuelle directe pour FastFDs"""
    file_path = "src/algorithms/fastfds.py"
    print(f"Correction manuelle de FastFDs: {file_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Corriger la classe Java
    for i, line in enumerate(lines):
        if "classPath =" in line:
            lines[i] = "            classPath = \"de.metanome.algorithms.fastfds.FastFD\"\n"
            break
    
    # Chercher la section problématique
    start_line = 0
    end_line = 0
    for i, line in enumerate(lines):
        if "metanome_cli_jar =" in line:
            start_line = i
        if "cmd_string = (" in line and start_line > 0 and end_line == 0:
            end_line = i
    
    if start_line > 0 and end_line > 0:
        # Remplacer la section problématique
        replacement = [
            "                # Ajouter tous les JAR du répertoire dans le classpath\n",
            "                all_jars = [f\"{jar_path}{jar_file}\" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]\n",
            "                classpath = \":\".join(all_jars)\n",
            "\n",
            "                cmd_string = (\n",
            "                    f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n",
            "                    f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"\n",
            "                    f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n",
            "                    f\"\"\"--output file:{file_name}\"\"\"\n",
            "                )\n",
        ]
        
        # Remplacer les lignes
        new_lines = lines[:start_line] + replacement + lines[end_line + 6:]  # +6 pour inclure toutes les lignes de cmd_string
        
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        
        print(f"✅ FastFDs corrigé manuellement")
    else:
        print(f"❌ Impossible de trouver la section à corriger dans FastFDs")

def fix_tane():
    """Correction manuelle directe pour TANE"""
    file_path = "src/algorithms/tane.py"
    print(f"Correction manuelle de TANE: {file_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Corriger la classe Java
    for i, line in enumerate(lines):
        if "classPath =" in line:
            lines[i] = "            classPath = \"de.metanome.algorithms.tane.TaneAlgorithm\"\n"
            break
    
    # Chercher la section problématique
    start_line = 0
    end_line = 0
    for i, line in enumerate(lines):
        if "metanome_cli_jar =" in line:
            start_line = i
        if "cmd_string = (" in line and start_line > 0 and end_line == 0:
            end_line = i
    
    if start_line > 0 and end_line > 0:
        # Remplacer la section problématique
        replacement = [
            "                # Ajouter tous les JAR du répertoire dans le classpath\n",
            "                all_jars = [f\"{jar_path}{jar_file}\" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]\n",
            "                classpath = \":\".join(all_jars)\n",
            "\n",
            "                cmd_string = (\n",
            "                    f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n",
            "                    f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"\n",
            "                    f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n",
            "                    f\"\"\"--output file:{file_name}\"\"\"\n",
            "                )\n",
        ]
        
        # Remplacer les lignes
        new_lines = lines[:start_line] + replacement + lines[end_line + 6:]  # +6 pour inclure toutes les lignes de cmd_string
        
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        
        print(f"✅ TANE corrigé manuellement")
    else:
        print(f"❌ Impossible de trouver la section à corriger dans TANE")

def fix_fdep():
    """Correction manuelle directe pour FDep"""
    file_path = "src/algorithms/fdep.py"
    print(f"Correction manuelle de FDep: {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remplacer la commande avec la définition du classpath
    old_cmd = "cmd_string = (\n            f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"\n            f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n            f\"\"\"--output file:{file_name}\"\"\"\n        )"
    
    new_cmd = "# Ajouter tous les JAR du répertoire dans le classpath\n        all_jars = [f\"{jar_path}{jar_file}\" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]\n        classpath = \":\".join(all_jars)\n        \n        cmd_string = (\n            f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"\n            f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n            f\"\"\"--output file:{file_name}\"\"\"\n        )"
    
    new_content = content.replace(old_cmd, new_cmd)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ FDep corrigé manuellement")

def fix_pyro():
    """Correction manuelle directe pour Pyro"""
    file_path = "src/algorithms/pyro.py"
    print(f"Correction manuelle de Pyro: {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Corriger la classe Java
    content = content.replace("classPath = \"de.hpi.isg.pyro.core.ProfilingAlgorithm\"", "classPath = \"de.hpi.isg.pyro.algorithm.ProfilingAlgorithm\"")
    
    # Remplacer la commande avec la définition du classpath
    old_cmd = "cmd_string = (\n            f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"\n            f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n            f\"\"\"--output file:{file_name}\"\"\"\n        )"
    
    new_cmd = "# Ajouter tous les JAR du répertoire dans le classpath\n        all_jars = [f\"{jar_path}{jar_file}\" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]\n        classpath = \":\".join(all_jars)\n        \n        cmd_string = (\n            f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"\n            f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n            f\"\"\"--output file:{file_name}\"\"\"\n        )"
    
    new_content = content.replace(old_cmd, new_cmd)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Pyro corrigé manuellement")

def fix_aidfd():
    """Correction manuelle directe pour AIDFD"""
    file_path = "src/algorithms/aidfd.py"
    print(f"Correction manuelle de AIDFD: {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Corriger la commande avec les paramètres de configuration corrects
    old_cmd = "cmd_string = (\n            f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"\n            f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n            f\"\"\"--output file:{file_name} \"\"\"\n            f\"\"\"--algorithm-config min_support:{self.min_support},min_confidence:{self.min_confidence},max_lhs_size:{self.max_lhs_size}\"\"\"\n        )"
    
    new_cmd = "# Ajouter tous les JAR du répertoire dans le classpath\n        all_jars = [f\"{jar_path}{jar_file}\" for jar_file in os.listdir(jar_path) if jar_file.endswith('.jar')]\n        classpath = \":\".join(all_jars)\n        \n        # Utiliser les paramètres de configuration reconnus par l'algorithme\n        cmd_string = (\n            f\"\"\"java -Xmx4g -cp {classpath} \"\"\"\n            f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_files} \"\"\"\n            f\"\"\"--file-key INPUT_FILES --separator \",\" --header \"\"\"\n            f\"\"\"--output file:{file_name}\"\"\"\n        )"
    
    new_content = content.replace(old_cmd, new_cmd)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ AIDFD corrigé manuellement")

def main():
    """Fonction principale"""
    print("Début des corrections manuelles directes")
    
    # Corriger DFD
    fix_dfd()
    
    # Corriger FastFDs
    fix_fastfds()
    
    # Corriger TANE
    fix_tane()
    
    # Corriger FDep
    fix_fdep()
    
    # Corriger Pyro
    fix_pyro()
    
    # Corriger AIDFD
    fix_aidfd()
    
    print("Fin des corrections manuelles directes")

if __name__ == "__main__":
    main()

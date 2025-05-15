#!/bin/bash
# fix_metanome_bash.sh - Script shell pour corriger les algorithmes Java Metanome

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Répertoire de base
BASE_DIR=$(pwd)
ALGORITHMS_DIR="$BASE_DIR/src/algorithms"
JAR_DIR="$ALGORITHMS_DIR/bins/metanome"

# Classes Java correctes pour chaque algorithme
AIDFD_CLASS="de.metanome.algorithms.aidfd.AIDFD"
PYRO_CLASS="de.hpi.isg.pyro.algorithm.ProfilingAlgorithm" 
DFD_CLASS="de.metanome.algorithms.dfd.DFD"
FDEP_CLASS="de.metanome.algorithms.fdep.FdepAlgorithm"
FASTFDS_CLASS="de.metanome.algorithms.fastfds.FastFD"
TANE_CLASS="de.metanome.algorithms.tane.TaneAlgorithm"

# Vérifier les fichiers JAR
echo -e "${YELLOW}Vérification des fichiers JAR...${NC}"
if [ ! -d "$JAR_DIR" ]; then
  echo -e "${RED}Erreur: Répertoire JAR introuvable: $JAR_DIR${NC}"
  exit 1
fi

JAR_COUNT=$(ls -1 "$JAR_DIR"/*.jar 2>/dev/null | wc -l)
if [ "$JAR_COUNT" -eq 0 ]; then
  echo -e "${RED}Erreur: Aucun fichier JAR trouvé dans $JAR_DIR${NC}"
  exit 1
fi

echo -e "${GREEN}Trouvé $JAR_COUNT fichiers JAR${NC}"

# Fonction pour sauvegarder un fichier
backup_file() {
  local file="$1"
  local backup="${file}.bak"
  
  if [ ! -f "$backup" ]; then
    cp "$file" "$backup"
    echo -e "${YELLOW}Sauvegarde créée: $backup${NC}"
  fi
}

# Fonction pour corriger le chemin de classe dans un fichier
fix_class_path() {
  local file="$1"
  local class_name="$2"
  
  # Créer une sauvegarde
  backup_file "$file"
  
  # Utiliser sed pour remplacer la classe
  if grep -q "classPath =" "$file"; then
    sed -i'.tmp' "s|classPath = \"[^\"]*\"|classPath = \"$class_name\"|g" "$file"
    rm -f "${file}.tmp"
    echo -e "${GREEN}Classe Java corrigée dans $file${NC}"
  else
    echo -e "${YELLOW}Ligne classPath non trouvée dans $file${NC}"
  fi
}

# Fonction pour corriger la commande Java
fix_cmd_string() {
  local file="$1"
  
  # Trouver et remplacer le bloc cmd_string
  if grep -q "cmd_string = (" "$file"; then
    # Rechercher la ligne de début et de fin du bloc
    local line_num=$(grep -n "cmd_string = (" "$file" | cut -d':' -f1)
    if [ -n "$line_num" ]; then
      # Déterminer l'indentation
      local indent=$(sed -n "${line_num}p" "$file" | sed 's/cmd_string.*//')
      
      # Construire la nouvelle commande
      local new_cmd="${indent}cmd_string = (\n"
      new_cmd+="${indent}    f\"\"\"java -Xmx4g -cp {jar_path}*.jar \"\"\"\n"
      new_cmd+="${indent}    f\"\"\"de.metanome.cli.App --algorithm {classPath} --files {csv_file} \"\"\"\n"
      new_cmd+="${indent}    f\"\"\"--file-key INPUT_FILES --separator \\\",\\\" --header \"\"\"\n"
      new_cmd+="${indent}    f\"\"\"--output file:{file_name}\"\"\"\n"
      new_cmd+="${indent})"
      
      # Remplacer le bloc entier (utilisation de perl pour le remplacement multilignes)
      perl -i -pe "s/cmd_string = \([^\)]+\)/$new_cmd/s" "$file"
      echo -e "${GREEN}Commande Java corrigée dans $file${NC}"
    fi
  else
    echo -e "${YELLOW}Bloc cmd_string non trouvé dans $file${NC}"
  fi
}

# Fonction pour supprimer les dépendances problématiques
fix_dependencies() {
  local file="$1"
  
  # Supprimer les références aux dépendances problématiques
  local deps=("mdms-tools" "mdms-metanome-client" "mdms-model")
  for dep in "${deps[@]}"; do
    if grep -q "$dep" "$file"; then
      # Supprimer les lignes contenant la dépendance
      grep -v "$dep" "$file" > "${file}.tmp"
      mv "${file}.tmp" "$file"
      echo -e "${GREEN}Dépendance $dep supprimée de $file${NC}"
    fi
  done
}

# Corriger chaque algorithme
echo -e "\n${YELLOW}Correction des algorithmes...${NC}"

# AIDFD
echo -e "\n${YELLOW}Correction de AIDFD...${NC}"
AIDFD_FILE="$ALGORITHMS_DIR/aidfd.py"
if [ -f "$AIDFD_FILE" ]; then
  fix_class_path "$AIDFD_FILE" "$AIDFD_CLASS"
  fix_cmd_string "$AIDFD_FILE"
  fix_dependencies "$AIDFD_FILE"
  echo -e "${GREEN}✅ AIDFD corrigé avec succès${NC}"
else
  echo -e "${RED}Fichier AIDFD introuvable: $AIDFD_FILE${NC}"
fi

# PYRO
echo -e "\n${YELLOW}Correction de PYRO...${NC}"
PYRO_FILE="$ALGORITHMS_DIR/pyro.py"
if [ -f "$PYRO_FILE" ]; then
  fix_class_path "$PYRO_FILE" "$PYRO_CLASS"
  fix_cmd_string "$PYRO_FILE"
  fix_dependencies "$PYRO_FILE"
  echo -e "${GREEN}✅ PYRO corrigé avec succès${NC}"
else
  echo -e "${RED}Fichier PYRO introuvable: $PYRO_FILE${NC}"
fi

# DFD
echo -e "\n${YELLOW}Correction de DFD...${NC}"
DFD_FILE="$ALGORITHMS_DIR/dfd.py"
if [ -f "$DFD_FILE" ]; then
  fix_class_path "$DFD_FILE" "$DFD_CLASS"
  fix_cmd_string "$DFD_FILE"
  fix_dependencies "$DFD_FILE"
  echo -e "${GREEN}✅ DFD corrigé avec succès${NC}"
else
  echo -e "${RED}Fichier DFD introuvable: $DFD_FILE${NC}"
fi

# FDEP
echo -e "\n${YELLOW}Correction de FDEP...${NC}"
FDEP_FILE="$ALGORITHMS_DIR/fdep.py"
if [ -f "$FDEP_FILE" ]; then
  fix_class_path "$FDEP_FILE" "$FDEP_CLASS"
  fix_cmd_string "$FDEP_FILE"
  fix_dependencies "$FDEP_FILE"
  echo -e "${GREEN}✅ FDEP corrigé avec succès${NC}"
else
  echo -e "${RED}Fichier FDEP introuvable: $FDEP_FILE${NC}"
fi

# FastFDs
echo -e "\n${YELLOW}Correction de FastFDs...${NC}"
FASTFDS_FILE="$ALGORITHMS_DIR/fastfds.py"
if [ -f "$FASTFDS_FILE" ]; then
  fix_class_path "$FASTFDS_FILE" "$FASTFDS_CLASS"
  fix_cmd_string "$FASTFDS_FILE"
  fix_dependencies "$FASTFDS_FILE"
  echo -e "${GREEN}✅ FastFDs corrigé avec succès${NC}"
else
  echo -e "${RED}Fichier FastFDs introuvable: $FASTFDS_FILE${NC}"
fi

# TANE
echo -e "\n${YELLOW}Correction de TANE...${NC}"
TANE_FILE="$ALGORITHMS_DIR/tane.py"
if [ -f "$TANE_FILE" ]; then
  fix_class_path "$TANE_FILE" "$TANE_CLASS"
  fix_cmd_string "$TANE_FILE"
  fix_dependencies "$TANE_FILE"
  echo -e "${GREEN}✅ TANE corrigé avec succès${NC}"
else
  echo -e "${RED}Fichier TANE introuvable: $TANE_FILE${NC}"
fi

echo -e "\n${GREEN}Tous les algorithmes ont été corrigés!${NC}"
echo -e "${YELLOW}Pour tester les algorithmes, créez un script de test ou utilisez python test_unified_algorithms.py${NC}"

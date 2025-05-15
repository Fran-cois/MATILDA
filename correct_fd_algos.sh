#!/bin/bash
# Script pour corriger les problèmes d'algorithmes FD

# Couleurs pour une meilleure lisibilité
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== VÉRIFICATION DES ALGORITHMES DE DÉPENDANCES FONCTIONNELLES =====${NC}"

# Vérifier s'il y a une erreur Java lors de l'exécution
test_algo() {
    algo_name=$1
    echo -e "${YELLOW}Test de l'algorithme $algo_name...${NC}"
    
    # Créer un petit fichier de test
    mkdir -p test_data
    echo "id,name,age,city" > test_data/test.csv
    echo "1,John,25,Paris" >> test_data/test.csv
    echo "2,Emma,30,Lyon" >> test_data/test.csv
    
    # Exécuter l'algorithme avec fallback
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -c "
import sys
sys.path.append('.')
from src.algorithms.$algo_name import $(echo $algo_name | sed 's/^\(.*\)$/\u\1/')

class MockDB:
    def __init__(self):
        self.base_csv_dir = 'test_data'

db = MockDB()
algo = $(echo $algo_name | sed 's/^\(.*\)$/\u\1/')(db)
try:
    rules = algo.discover_rules(use_fallback=True)
    print(f'✅ {algo_name.upper()} a réussi - Règles découvertes: {len(rules) if rules else 0}')
except Exception as e:
    print(f'❌ {algo_name.upper()} a échoué: {str(e)}')
    exit(1)
"
    
    # Vérifier si le test a réussi
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $algo_name passé avec succès${NC}"
    else
        echo -e "${RED}✗ $algo_name a échoué${NC}"
        FAILED_ALGOS+=($algo_name)
    fi
    
    # Nettoyer
    rm -rf test_data
    echo ""
}

# Tester les scripts spécifiques
test_script() {
    script_name=$1
    echo -e "${YELLOW}Exécution du script $script_name...${NC}"
    
    # Exécuter le script Python
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 "$script_name"
    
    # Vérifier si le script a réussi
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $script_name passé avec succès${NC}"
    else
        echo -e "${RED}✗ $script_name a échoué${NC}"
        FAILED_SCRIPTS+=($script_name)
    fi
    echo ""
}

# Liste pour suivre les tests échoués
declare -a FAILED_ALGOS=()
declare -a FAILED_SCRIPTS=()

echo -e "${YELLOW}---- Test direct des algorithmes individuels ----${NC}"
# Tester tous les algorithmes
test_algo tane
test_algo fdep
test_algo dfd
test_algo fastfds
test_algo aidfd
test_algo pyro

echo -e "${YELLOW}---- Exécution des scripts de test ----${NC}"
# Tester les scripts spécifiques
test_script "test_fdep_direct.py"
test_script "test_aidfd_pyro.py"
test_script "test_algorithms_simple.py"
test_script "test_all_fd_algos.py"

# Afficher le résumé
echo -e "${YELLOW}===== RÉSUMÉ DES TESTS =====${NC}"
if [ ${#FAILED_ALGOS[@]} -eq 0 ] && [ ${#FAILED_SCRIPTS[@]} -eq 0 ]; then
    echo -e "${GREEN}Tous les tests ont réussi !${NC}"
else
    if [ ${#FAILED_ALGOS[@]} -gt 0 ]; then
        echo -e "${RED}${#FAILED_ALGOS[@]} algorithme(s) ont échoué :${NC}"
        for failed in "${FAILED_ALGOS[@]}"; do
            echo -e "${RED}- $failed${NC}"
        done
        echo ""
    fi
    
    if [ ${#FAILED_SCRIPTS[@]} -gt 0 ]; then
        echo -e "${RED}${#FAILED_SCRIPTS[@]} script(s) ont échoué :${NC}"
        for failed in "${FAILED_SCRIPTS[@]}"; do
            echo -e "${RED}- $failed${NC}"
        done
        echo ""
    fi
    
    echo "Vérifiez les messages d'erreur ci-dessus pour plus de détails."
fi

echo ""
echo "Pour exécuter un test spécifique, utilisez une des commandes suivantes :"
echo "python test_fdep_direct.py"
echo "python test_aidfd_pyro.py"
echo "python test_algorithms_simple.py"
echo "python test_all_fd_algos.py"

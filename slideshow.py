import gurobipy as gp
from gurobipy import GRB
import sys
import logging
import argparse

# Initialisation de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_input(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    num_photos = int(lines[0].strip())
    horizontal = []
    vertical = []
    
    for i in range(1, num_photos + 1):
        parts = lines[i].strip().split()
        orientation = parts[0]
        tags = set(parts[2:])  # Assurez-vous que les tags sont des chaînes, pas des entiers
        
        if orientation == 'H':
            horizontal.append((i - 1, tags))
        else:
            vertical.append((i - 1, tags))
    
    vertical_pairs = []
    for i in range(0, len(vertical) - 1, 2):
        v1, v2 = vertical[i], vertical[i + 1]
        vertical_pairs.append((v1[0], v2[0], v1[1] | v2[1]))  # Fusionner les tags
    
    slides = horizontal + vertical_pairs
    return slides

def interest_factor(tags1, tags2):
    """Calcule le score de transition entre deux slides."""
    # Vérification que tags1 et tags2 sont bien des sets
    if not isinstance(tags1, set) or not isinstance(tags2, set):
        logging.error(f"tags1 ou tags2 ne sont pas des sets: {tags1}, {tags2}")
        return 0
    
    return min(len(tags1.intersection(tags2)), 
               len(tags1.difference(tags2)), 
               len(tags2.difference(tags1)))

def optimize_slideshow(slides):
    """Construit et résout le modèle d'optimisation avec Gurobi."""
    model = gp.Model("hashcode2019")
    num_slides = len(slides)
    
    # Création des variables binaires
    x = model.addVars(num_slides, num_slides, vtype=GRB.BINARY, name="x")
    
    # Fonction objectif
    model.setObjective(gp.quicksum(
        interest_factor(slides[i][-1], slides[j][-1]) * x[i, j]
        for i in range(num_slides) for j in range(num_slides) if i != j),
        GRB.MAXIMIZE
)
    
    # Contraintes de flux
    for i in range(num_slides):
        model.addConstr(gp.quicksum(x[i, j] for j in range(num_slides) if i != j) == 1, name=f"slide_out_{i}")
        model.addConstr(gp.quicksum(x[j, i] for j in range(num_slides) if i != j) == 1, name=f"slide_in_{i}")
    
    model.optimize()
    
    if model.status != GRB.OPTIMAL:
        logging.error(f"L'optimisation a échoué avec le statut {model.status}")
        sys.exit(1)
    
    # Initialisation de l'ordre des diapositives
    order = [-1] * num_slides
    used = set()
    
    # Récupération de l'ordre des diapositives depuis les variables x
    for i in range(num_slides):
        for j in range(num_slides):
            if i != j and x[i, j].x > 0.5:
                order[i] = j
                used.add(j)
    
    # Trouver la première diapositive
    unused_slides = [i for i in range(num_slides) if i not in used]
    if not unused_slides:
        logging.error("Impossible de trouver un premier slide, toutes les diapositives semblent être utilisées.")
        sys.exit(1)

    # Prendre la plus petite indice non utilisée comme première diapositive
    first_slide = min(unused_slides)  # Prendre la plus petite indice non utilisée pour éviter les erreurs
    solution = [first_slide]
    
    # Reconstruire l'ordre des diapositives
    while order[first_slide] != -1:
        first_slide = order[first_slide]
        solution.append(first_slide)
    
    # Construction de la solution finale
    result = []
    for slide in solution:
        if len(slides[slide]) == 3:  # Si c'est une paire de photos verticales
            result.append(f"{slides[slide][0]} {slides[slide][1]}")
        else:
            result.append(str(slides[slide][0]))
    
    return result

def write_output(solution, output_path):
    """Écrit la solution dans un fichier output."""
    with open(output_path, 'w') as f:
        f.write(str(len(solution)) + '\n')
        for slide in solution:
            f.write(str(slide) + '\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimisation du diaporama avec Gurobi pour HashCode 2019")
    parser.add_argument('input_file', type=str, help="Le fichier d'entrée contenant les données des photos")
    parser.add_argument('--output_file', type=str, default="slideshow.sol", help="Le fichier de sortie (par défaut : slideshow.sol)")
    
    args = parser.parse_args()
    
    try:
        logging.info(f"Lecture du fichier d'entrée : {args.input_file}")
        slides = read_input(args.input_file)
        logging.info(f"Nombre de diapositives générées : {len(slides)}")
        
        logging.info("Optimisation en cours...")
        solution = optimize_slideshow(slides)
        
        logging.info(f"Écriture du fichier de sortie : {args.output_file}")
        write_output(solution, args.output_file)
        logging.info("Processus terminé avec succès.")
    
    except FileNotFoundError:
        logging.error(f"Le fichier {args.input_file} n'a pas été trouvé. Veuillez vérifier le chemin.")
    except Exception as e:
        logging.error(f"Une erreur s'est produite : {e}")
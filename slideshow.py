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
    
    # Former des paires pour les photos verticales
    vertical_pairs = []
    for i in range(0, len(vertical) - 1, 2):
        v1, v2 = vertical[i], vertical[i + 1]
        vertical_pairs.append((v1[0], v2[0], v1[1] | v2[1]))  # Fusionner les tags
    
    slides = horizontal + vertical_pairs
    return slides

def interest_factor(tags1, tags2):
    """Calcule le score de transition entre deux slides."""
    # Vérification que tags1 et tags2 sont bien des sets
    if not isinstance(tags1, set):
        logging.error(f"tags1 n'est pas un set: {tags1}")
        return 0
    if not isinstance(tags2, set):
        logging.error(f"tags2 n'est pas un set: {tags2}")
        return 0
    
    return min(len(tags1.intersection(tags2)), 
           len(tags1.difference(tags2)), 
           len(tags2.difference(tags1)))

def optimize_slideshow(slides):
    """Construit et résout le modèle d'optimisation avec Gurobi."""
    model = gp.Model("hashcode2019")
    
    num_slides = len(slides)
    
    # Variables de décision : x[i, j] = 1 si i est suivi de j
    x = model.addVars(num_slides, num_slides, vtype=GRB.BINARY, name="x")

    # Fonction objectif : maximiser le score total
    model.setObjective(gp.quicksum(
    interest_factor(slides[i][-1], slides[j][-1]) * x[i, j]
    for i in range(num_slides) for j in range(num_slides) if i != j),
    GRB.MAXIMIZE
)
    
    # Contraintes : chaque slide a un unique successeur et un unique prédécesseur
    for i in range(num_slides):
        model.addConstr(gp.quicksum(x[i, j] for j in range(num_slides) if i != j) == 1, name=f"slide_out_{i}")
        model.addConstr(gp.quicksum(x[j, i] for j in range(num_slides) if i != j) == 1, name=f"slide_in_{i}")

     # Ajout de contraintes pour éviter les cycles en imposant un ordre
    if num_slides > 1:
        u = model.addVars(num_slides, vtype=GRB.INTEGER, name="u")
        for i in range(1, num_slides):
            for j in range(1, num_slides):
                if i != j:
                    model.addConstr(u[i] - u[j] + num_slides * x[i, j] <= num_slides - 1)

    model.optimize()
    
    if model.status != GRB.OPTIMAL:
        logging.error(f"L'optimisation a échoué avec le statut {model.status}")
        sys.exit(1)
    
    # Affichage des variables x[i, j] après optimisation
    for i in range(num_slides):
        for j in range(num_slides):
            if i != j and x[i, j].x > 0.5:
                logging.info(f"x[{i}, {j}] = {x[i, j].x}")

    # Reconstruction de la séquence optimale
    order = [-1] * num_slides
    used = set()
    
    for i in range(num_slides):
        for j in range(num_slides):
            if i != j and x[i, j].x > 0.5:
                order[i] = j
                used.add(j)
                logging.info(f"Slide {i} -> Slide {j}")
    
    # Commencer par le premier slide
    first_slide = next((i for i in range(num_slides) if i not in used), None)

    if first_slide is None:
        logging.error("Aucun premier slide trouvé, cela pourrait signifier un problème dans la solution.")
        sys.exit(1)

    # Construction de la solution avec une vérification des cycles
    solution = [first_slide]
    visited = set()  # Pour vérifier les cycles

    while order[first_slide] != -1:
        if first_slide in visited:
            logging.error("Détection d'un cycle dans la reconstruction !")
            sys.exit(1)
        visited.add(first_slide)
        first_slide = order[first_slide]
        solution.append(first_slide)

    # Formater correctement la solution
    return [f"{slides[i][0]} {slides[i][1]}" if isinstance(slides[i], tuple) and len(slides[i]) == 3 else str(slides[i][0]) for i in solution]

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
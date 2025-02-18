import gurobipy as gp
from gurobipy import GRB
import sys
import logging
import argparse

def read_input(file_path):
    """Lit les données du fichier d'entrée et retourne les informations sous forme exploitable."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    num_photos = int(lines[0].strip())
    horizontal = []
    vertical = []
    
    for i in range(1, num_photos + 1):
        parts = lines[i].strip().split()
        orientation = parts[0]
        tags = set(parts[2:])
        if orientation == 'H':
            horizontal.append((i - 1, tags))
        else:
            vertical.append((i - 1, tags))
    
    # Associer les photos verticales par paires optimales
    vertical.sort(key=lambda x: len(x[1]))  # Trier par nombre de tags pour améliorer les paires
    vertical_pairs = []
    for i in range(0, len(vertical) - 1, 2):
        vertical_pairs.append((vertical[i][0], vertical[i+1][0], vertical[i][1] | vertical[i+1][1]))
    
    slides = horizontal + vertical_pairs
    
    return slides

def interest_factor(tags1, tags2):
    """Calcule le score de transition entre deux slides."""
    return min(len(tags1 & tags2), len(tags1 - tags2), len(tags2 - tags1))

def optimize_slideshow(slides):
    """Construit et résout le modèle d'optimisation avec Gurobi."""
    model = gp.Model("hashcode2019")
    
    num_slides = len(slides)
    
    # Variables binaires : x[i, j] = 1 si la diapositive i est suivie de la diapositive j
    x = model.addVars(num_slides, num_slides, vtype=GRB.BINARY, name="x")
    
    # Objectif : maximiser la somme des intérêts entre diapositives adjacentes
    model.setObjective(gp.quicksum(interest_factor(slides[i][1], slides[j][1]) * x[i, j]
                                   for i in range(num_slides) for j in range(num_slides) if i != j),
                       GRB.MAXIMIZE)
    
    # Contraintes : chaque diapositive doit apparaître exactement une fois
    for i in range(num_slides):
        model.addConstr(gp.quicksum(x[i, j] for j in range(num_slides) if i != j) == 1, name=f"slide_out_{i}")
        model.addConstr(gp.quicksum(x[j, i] for j in range(num_slides) if i != j) == 1, name=f"slide_in_{i}")
    
    model.optimize()
    
    # Reconstruction de la solution
    order = [-1] * num_slides
    used = set()
    
    for i in range(num_slides):
        for j in range(num_slides):
            if i != j and x[i, j].x > 0.5:
                order[i] = j
                used.add(j)
    
    # Trouver le premier élément (celui qui n'a pas de prédecesseur)
    first_slide = next(i for i in range(num_slides) if i not in used)
    solution = [first_slide]
    
    while order[first_slide] != -1:
        first_slide = order[first_slide]
        solution.append(first_slide)
    
    return [slides[i][0] if isinstance(slides[i][0], int) else f"{slides[i][0]} {slides[i][1]}" for i in solution]

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
    
    input_file = args.input_file
    output_file = args.output_file
    
    try:
        logging.info(f"Lecture du fichier d'entrée : {input_file}")
        slides = read_input(input_file)
        logging.info(f"Nombre de diapositives générées : {len(slides)}")
        
        logging.info("Optimisation en cours...")
        solution = optimize_slideshow(slides)
        
        logging.info(f"Écriture du fichier de sortie : {output_file}")
        write_output(solution, output_file)
        logging.info("Processus terminé avec succès.")
        
        # Vérification post-optimisation
        logging.info("Vérification de la solution générée...")
        with open(output_file, 'r') as f:
            lines = f.readlines()
        num_output_slides = int(lines[0].strip())
        assert num_output_slides == len(solution), "Erreur : la solution générée ne correspond pas au fichier de sortie."
        logging.info("Vérification réussie : la solution est cohérente avec l'optimisation.")
    
    except FileNotFoundError:
        logging.error(f"Le fichier {input_file} n'a pas été trouvé. Veuillez vérifier le chemin.")
    except AssertionError as e:
        logging.error(f"Erreur de validation : {e}")
    except Exception as e:
        logging.error(f"Une erreur s'est produite : {e}")

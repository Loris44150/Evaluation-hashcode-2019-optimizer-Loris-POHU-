import gurobipy as gp
from gurobipy import GRB
from itertools import combinations

def read_input(file_path):
    """Lit les donnees du fichier d'entree et retourne les informations sous forme exploitable."""
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
    
    # Associer les photos verticales par paires pour former des slides
    vertical_pairs = [(v1[0], v2[0], v1[1] | v2[1]) for v1, v2 in combinations(vertical, 2)]
    slides = horizontal + vertical_pairs
    
    return slides

def interest_factor(tags1, tags2):
    """Calcule le score de transition entre deux slides."""
    return min(len(tags1 & tags2), len(tags1 - tags2), len(tags2 - tags1))

def optimize_slideshow(slides):
    """Construit et resout le modele d'optimisation avec Gurobi."""
    model = gp.Model("hashcode2019")
    
    # Variables binaires : x[i, j] = 1 si la diapositive i est suivie de la diapositive j
    x = model.addVars(len(slides), len(slides), vtype=GRB.BINARY, name="x")
    
    # Objectif : maximiser la somme des interets entre diapositives adjacentes
    model.setObjective(gp.quicksum(interest_factor(slides[i][1], slides[j][1]) * x[i, j]
                                   for i in range(len(slides)) for j in range(len(slides)) if i != j),
                       GRB.MAXIMIZE)
    
    # Contraintes : chaque diapositive doit apparaitre une seule fois
    for i in range(len(slides)):
        model.addConstr(gp.quicksum(x[i, j] for j in range(len(slides)) if i != j) == 1, name=f"slide_out_{i}")
        model.addConstr(gp.quicksum(x[j, i] for j in range(len(slides)) if i != j) == 1, name=f"slide_in_{i}")
    
    model.optimize()
    
    solution = []
    for i in range(len(slides)):
        for j in range(len(slides)):
            if i != j and x[i, j].x > 0.5:
                solution.append(slides[i][0] if isinstance(slides[i][0], int) else f"{slides[i][0]} {slides[i][1]}")
    
    return solution

def write_output(solution, output_path):
    """Ecrit la solution dans un fichier output."""
    with open(output_path, 'w') as f:
        f.write(str(len(solution)) + '\n')
        for slide in solution:
            f.write(str(slide) + '\n')

if __name__ == "__main__":
    input_file = "example.txt"  # Modifier avec le chemin reel
    output_file = "slideshow.sol"
    
    slides = read_input(input_file)
    solution = optimize_slideshow(slides)
    write_output(solution, output_file)

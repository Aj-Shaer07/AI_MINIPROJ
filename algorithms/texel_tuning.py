"""
Texel Tuning using L-BFGS-B (Perfect Heuristic Mapping)
======================================================
Optimizes Material, Piece-Square Tables (PSTs), and ALL heuristics.
Eliminates Omitted Variable Bias by perfectly mirroring evaluation.py logic.
"""

import os
import sys
import json
import numpy as np
import scipy.optimize
import chess
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

PIECE_ORDER = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]
NUM_MATERIAL = 10
NUM_PST = 768
NUM_BONUS = 25
TOTAL_PARAMS = NUM_MATERIAL + NUM_PST + NUM_BONUS

TOTAL_PHASE = 24
PHASE_WEIGHT = {chess.PAWN: 0, chess.KNIGHT: 1, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 4, chess.KING: 0}


def pack_params():
    """Pack hardcoded evaluation defaults into an 803-vector."""
    from algorithms import evaluation as ev
    params = []
    
    # Defaults from original evaluation.py
    # We must explicitly use hardcoded defaults or it re-packs tuned ones!
    hardcoded_mg = {1: 82, 2: 337, 3: 365, 4: 477, 5: 1025}
    hardcoded_eg = {1: 94, 2: 281, 3: 297, 4: 512, 5: 936}
    
    for pt in PIECE_ORDER: params.append(hardcoded_mg[pt])
    for pt in PIECE_ORDER: params.append(hardcoded_eg[pt])

    def _flip(table):
        res = []
        for r in range(7, -1, -1): res.extend(table[r*8:r*8+8])
        return res

    pst_data = [
        _flip([0,0,0,0,0,0,0,0,98,134,61,95,68,126,34,-11,-6,7,26,31,65,56,25,-20,-14,13,6,21,23,12,17,-23,-27,-2,-5,12,17,6,10,-25,-26,-4,-4,-10,3,3,33,-12,-35,-1,-20,-23,-15,24,38,-22,0,0,0,0,0,0,0,0]),
        _flip([0,0,0,0,0,0,0,0,178,173,158,134,147,132,165,187,94,100,85,67,56,53,82,84,32,24,13,5,-2,4,17,17,13,9,-3,-7,-7,-8,3,-1,4,7,-6,1,0,-5,-1,-8,13,8,8,10,13,0,2,-7,0,0,0,0,0,0,0,0]),
        _flip([-167,-89,-34,-49,61,-97,-15,-107,-73,-41,72,36,23,62,7,-17,-47,60,37,65,84,129,73,44,-9,17,19,53,37,69,18,22,-13,4,16,13,28,19,21,-8,-23,-9,12,10,19,17,25,-16,-29,-53,-12,-3,-1,18,-14,-19,-105,-21,-58,-33,-17,-28,-19,-23]),
        _flip([-58,-38,-13,-28,-31,-27,-63,-99,-25,-8,-25,-2,-9,-25,-24,-52,-24,-20,10,9,-1,-9,-19,-41,-17,3,22,22,22,11,8,-18,-18,-6,16,25,16,17,4,-18,-23,-3,-1,15,10,-3,-20,-22,-42,-20,-10,-5,-2,-20,-23,-44,-29,-51,-23,-15,-22,-18,-50,-64]),
        _flip([-29,4,-82,-37,-25,-42,7,-8,-26,16,-18,-13,30,59,18,-47,-16,37,43,40,35,50,37,-2,-4,5,19,50,37,37,7,-2,-6,13,13,26,34,12,10,4,0,15,15,15,14,27,18,10,4,15,16,0,7,21,33,1,-33,-3,-14,-21,-13,-12,-39,-21]),
        _flip([-14,-21,-11,-8,-7,-9,-17,-24,-8,-4,7,-12,-3,-13,-4,-14,2,-8,0,-1,-2,6,0,4,-3,9,12,9,14,10,3,2,-6,3,13,19,7,10,-3,-9,-12,-3,8,10,13,3,-7,-15,-14,-18,-7,-1,4,-9,-15,-27,-23,-9,-23,-5,-9,-16,-5,-17]),
        _flip([32,42,32,51,63,9,31,43,27,32,58,62,80,67,26,44,-5,19,26,36,17,45,61,16,-24,-11,7,26,24,35,-8,-20,-36,-26,-12,-1,9,-7,6,-23,-45,-25,-16,-17,3,0,-5,-33,-44,-16,-20,-9,-1,11,-6,-71,-19,-13,1,17,16,7,-37,-26]),
        _flip([13,10,18,15,12,12,8,5,11,13,13,11,-3,3,8,3,7,7,7,5,4,-3,-5,-3,4,3,13,1,2,1,-1,2,3,5,8,4,-5,-6,-8,-11,-4,0,-5,-1,-7,-12,-8,-16,-6,-6,0,2,-9,-9,-11,-3,-9,2,3,-1,-5,-13,4,-20]),
        _flip([-28,0,29,12,59,44,43,45,-24,-39,-5,1,-16,57,28,54,-13,-17,7,8,29,56,47,57,-27,-27,-16,-16,-1,17,-2,1,-9,-26,-9,-10,-2,-4,3,-3,-14,2,-11,-2,-5,2,14,5,-35,-8,11,2,8,15,-3,1,-1,-18,-9,10,-15,-25,-31,-50]),
        _flip([-9,22,22,27,27,19,10,20,-17,20,32,41,58,25,30,0,-20,6,9,49,47,35,19,9,3,22,24,45,57,40,57,36,-18,28,19,47,31,34,39,23,-16,-27,15,6,9,17,10,5,-22,-23,-30,-16,-16,-23,-36,-32,-33,-28,-22,-43,-5,-32,-20,-41]),
        _flip([-65,23,16,-15,-56,-34,2,13,29,-1,-20,-7,-8,-4,-38,-29,-9,24,2,-16,-20,6,22,-22,-17,-20,-12,-27,-30,-25,-14,-36,-49,-1,-27,-39,-46,-44,-33,-51,-14,-14,-22,-46,-44,-30,-15,-27,1,7,-8,-64,-43,-16,9,8,-15,36,12,-54,8,-28,24,14]),
        _flip([-74,-35,-18,-18,-11,15,4,-17,-12,17,14,17,17,38,23,11,10,17,23,15,20,45,44,13,-8,22,24,27,26,33,26,3,-18,-4,21,24,27,23,9,-11,-19,-3,11,21,23,16,7,-9,-27,-11,4,13,14,4,-5,-17,-53,-34,-21,-11,-28,-14,-24,-43])
    ]
    for table in pst_data:
        params.extend(table)
    
    # Bonuses (25 features)
    bonuses = [
        -15, -20, 30, 25, 12, 10,   # 0..5: DOUBLED, ISOLATED, BISHOP_PAIR, R_OPEN, R_SEMI, K_SHIELD
        5, 10, 20, 40, 65, 100,     # 6..11: PASSED_PAWN_MG[1..6]
        15, 30, 50, 90, 150, 250,   # 12..17: PASSED_PAWN_EG[1..6]
        40, 30, 1.0,                # 18..20: ROOK_BEHIND, CONNECTED, KING_PROX_MULT
        160, 165, 250, 450          # 21..24: HANGING_{N,B,R,Q} PENALTIES
    ]
    params.extend(bonuses)
    return np.array(params, dtype=np.float64)


def build_design_matrix(boards):
    """Build the huge (N, 803) linear regression design matrix X and constant mop up biases."""
    n = len(boards)
    X = np.zeros((n, TOTAL_PARAMS), dtype=np.float64)
    mop_up_biases = np.zeros(n, dtype=np.float64)

    mat_features = np.zeros((n, NUM_MATERIAL), dtype=np.float64)
    pst_features = np.zeros((n, NUM_PST), dtype=np.float64)
    bonus_features = np.zeros((n, NUM_BONUS), dtype=np.float64)
    phases = np.zeros(n, dtype=np.float64)

    for i, board in enumerate(boards):
        phase = 0
        w_mat = 0
        b_mat = 0

        for color in [chess.WHITE, chess.BLACK]:
            sign = 1 if color == chess.WHITE else -1
            
            # MAT & PST
            for pt_idx, pt in enumerate(PIECE_ORDER):
                count = len(board.pieces(pt, color))
                mat_features[i, pt_idx] += sign * count
                mat_features[i, pt_idx + 5] += sign * count
                phase += count * PHASE_WEIGHT.get(pt, 0)
                
                # PST indices
                mg_offset = pt_idx * 128
                eg_offset = mg_offset + 64
                
                for sq in board.pieces(pt, color):
                    mirror_sq = sq if color == chess.WHITE else sq ^ 56
                    pst_features[i, mg_offset + mirror_sq] += sign
                    pst_features[i, eg_offset + mirror_sq] += sign
                    
            # KING PST
            for sq in board.pieces(chess.KING, color):
                mirror_sq = sq if color == chess.WHITE else sq ^ 56
                pst_features[i, 5 * 128 + mirror_sq] += sign
                pst_features[i, 5 * 128 + 64 + mirror_sq] += sign
                
            # BONUSES
            pawns = board.pieces(chess.PAWN, color)
            enemy_pawns = board.pieces(chess.PAWN, not color)
            
            # Pawn structural bonuses
            for sq in pawns:
                f = chess.square_file(sq)
                r = chess.square_rank(sq)
                
                # Doubled (EG)
                same_file = [s for s in pawns if chess.square_file(s) == f and s != sq]
                if same_file:
                    bonus_features[i, 0] += sign
                    
                # Isolated (Both)
                adj_files = []
                if f > 0: adj_files.append(f - 1)
                if f < 7: adj_files.append(f + 1)
                has_neighbor = any(chess.square_file(s) in adj_files for s in pawns if s != sq)
                if not has_neighbor:
                    bonus_features[i, 1] += sign
                    
                # Passed Pawns
                is_passed = True
                check_files = [f] + adj_files
                for ep in enemy_pawns:
                    ep_f = chess.square_file(ep)
                    ep_r = chess.square_rank(ep)
                    if ep_f in check_files:
                        if color == chess.WHITE and ep_r > r:
                            is_passed = False; break
                        elif color == chess.BLACK and ep_r < r:
                            is_passed = False; break
                            
                if is_passed:
                    eff_rank = r if color == chess.WHITE else (7 - r)
                    if 1 <= eff_rank <= 6:
                        idx = eff_rank - 1
                        bonus_features[i, 6 + idx] += sign   # MG indices 6..11
                        bonus_features[i, 12 + idx] += sign  # EG indices 12..17
                        
                    # Rook behind passed pawn (EG)
                    rook_behind = False
                    for rsq in board.pieces(chess.ROOK, color):
                        if chess.square_file(rsq) == f:
                            rr = chess.square_rank(rsq)
                            if (color == chess.WHITE and rr < r) or (color == chess.BLACK and rr > r):
                                rook_behind = True; break
                    if rook_behind:
                        bonus_features[i, 18] += sign
                        
                    # Connected Passers (EG)
                    for adj_f in adj_files:
                        for other_sq in pawns:
                            if other_sq != sq and chess.square_file(other_sq) == adj_f:
                                other_r = chess.square_rank(other_sq)
                                other_passed = True
                                other_check = [adj_f]
                                if adj_f > 0: other_check.append(adj_f - 1)
                                if adj_f < 7: other_check.append(adj_f + 1)
                                for ep2 in enemy_pawns:
                                    if chess.square_file(ep2) in other_check:
                                        if (color == chess.WHITE and chess.square_rank(ep2) > other_r) or \
                                           (color == chess.BLACK and chess.square_rank(ep2) < other_r):
                                            other_passed = False; break
                                if other_passed and other_sq > sq:
                                    bonus_features[i, 19] += sign
                                    
                    # King Proximity to Passer (EG)
                    if eff_rank >= 3:
                        own_k = board.king(color)
                        opp_k = board.king(not color)
                        if own_k is not None and opp_k is not None:
                            own_dist = max(abs(chess.square_file(own_k) - chess.square_file(sq)),
                                           abs(chess.square_rank(own_k) - chess.square_rank(sq)))
                            opp_dist = max(abs(chess.square_file(opp_k) - chess.square_file(sq)),
                                           abs(chess.square_rank(opp_k) - chess.square_rank(sq)))
                            # Evaluated as: (opp_dist*5 - own_dist*3)
                            proxy_val = opp_dist * 5 - own_dist * 3
                            bonus_features[i, 20] += sign * proxy_val

            # Bishop Pair (Both)
            if len(board.pieces(chess.BISHOP, color)) >= 2:
                bonus_features[i, 2] += sign
                
            # Rook Files (Both)
            for rsq in board.pieces(chess.ROOK, color):
                f = chess.square_file(rsq)
                own_f_p = any(chess.square_file(s) == f for s in pawns)
                opp_f_p = any(chess.square_file(s) == f for s in enemy_pawns)
                if not own_f_p and not opp_f_p:
                    bonus_features[i, 3] += sign
                elif not own_f_p:
                    bonus_features[i, 4] += sign

            # King Shield (MG)
            # Extracted un-tapered here, we apply mg_weight multiplier later.
            king_sq = board.king(color)
            if king_sq is not None:
                kf = chess.square_file(king_sq)
                kr = chess.square_rank(king_sq)
                shield_files = [max(0, kf - 1), kf, min(7, kf + 1)]
                shield_ranks = [kr + 1, kr + 2] if color == chess.WHITE else [kr - 1, kr - 2]
                for sf in shield_files:
                    for sr in shield_ranks:
                        if 0 <= sr <= 7:
                            ssq = chess.square(sf, sr)
                            piece = board.piece_at(ssq)
                            if piece and piece.piece_type == chess.PAWN and piece.color == color:
                                bonus_features[i, 5] += sign
                                
            # Hanging Piece Penalties (Both)
            enemy = not color
            hanging_map = {chess.KNIGHT: 21, chess.BISHOP: 22, chess.ROOK: 23, chess.QUEEN: 24}
            for pt_key, idx in hanging_map.items():
                for hsq in board.pieces(pt_key, color):
                    if board.is_attacked_by(enemy, hsq) and not board.is_attacked_by(color, hsq):
                        bonus_features[i, idx] -= sign  # Minus because it is a penalty

        phases[i] = min(phase, TOTAL_PHASE)
        
        # Exact Mop-Up Evaluation Calculation
        w_mat = sum(len(board.pieces(pt, chess.WHITE)) * val for pt, val in zip(PIECE_ORDER, [82, 337, 365, 477, 1025]))
        b_mat = sum(len(board.pieces(pt, chess.BLACK)) * val for pt, val in zip(PIECE_ORDER, [82, 337, 365, 477, 1025]))
        mat_adv = w_mat - b_mat
        mop_score = 0
        if abs(mat_adv) > 300:
            winning_color = chess.WHITE if mat_adv > 0 else chess.BLACK
            w_king = board.king(winning_color)
            l_king = board.king(not winning_color)
            if w_king is not None and l_king is not None:
                cmd = (
                    abs(min(chess.square_file(l_king), 7 - chess.square_file(l_king))) +
                    abs(min(chess.square_rank(l_king), 7 - chess.square_rank(l_king)))
                )
                dist = max(abs(chess.square_file(w_king) - chess.square_file(l_king)),
                           abs(chess.square_rank(w_king) - chess.square_rank(l_king)))
                mop_score = int(4.7 * (14 - cmd) + 1.6 * (14 - dist))
                mop_up_biases[i] = mop_score if winning_color == chess.WHITE else -mop_score

    # Construct the final matrix X
    mg_weight = phases / TOTAL_PHASE
    eg_weight = (TOTAL_PHASE - phases) / TOTAL_PHASE

    for m in range(5):
        X[:, m] = mat_features[:, m] * mg_weight
        X[:, m + 5] = mat_features[:, m + 5] * eg_weight
        
    for m in range(6):
        mg_slice = m * 128
        eg_slice = mg_slice + 64
        for sq in range(64):
            X[:, 10 + mg_slice + sq] = pst_features[:, mg_slice + sq] * mg_weight
            X[:, 10 + eg_slice + sq] = pst_features[:, eg_slice + sq] * eg_weight

    idx_bonus = 10 + 768
    X[:, idx_bonus + 0] = bonus_features[:, 0] * eg_weight
    for b in range(1, 5): X[:, idx_bonus + b] = bonus_features[:, b]  # ISOLATED, BISHOP_PAIR, OPEN, SEMI
    X[:, idx_bonus + 5] = bonus_features[:, 5] * mg_weight  # king shield (if phase>6 logic already in extraction)
    
    for b in range(6, 12): X[:, idx_bonus + b] = bonus_features[:, b] * mg_weight # pp mg
    for b in range(12, 18): X[:, idx_bonus + b] = bonus_features[:, b] * eg_weight # pp eg
    for b in range(18, 21): X[:, idx_bonus + b] = bonus_features[:, b] * eg_weight # rook_bh, conn, k_prox
    for b in range(21, 25): X[:, idx_bonus + b] = bonus_features[:, b] # hanging
    
    return X, mop_up_biases


def compute_loss_and_grad(params, X, mop_up_biases, sf_probs, l2_reg=0.0001, initial_params=None):
    scores = (X @ params) + mop_up_biases
    pred_probs = 1 / (1 + 10 ** (-scores / 400.0))
    loss = np.mean((pred_probs - sf_probs) ** 2)
    
    dLoss_dProbs = 2.0 * (pred_probs - sf_probs) / len(sf_probs)
    dProbs_dScores = pred_probs * (1.0 - pred_probs) * (np.log(10) / 400.0)
    dLoss_dScores = dLoss_dProbs * dProbs_dScores
    grad = X.T @ dLoss_dScores

    if initial_params is not None:
        diff = params - initial_params
        # Avoid penalizing mop-up logic dependencies or un-tuned parameters.
        loss += l2_reg * np.sum(diff ** 2)
        grad += 2 * l2_reg * diff
        
    return loss, grad


def save_tuned_weights(params, output_path):
    mg_pawn = params[0]
    if mg_pawn > 0:
        scale = 100.0 / mg_pawn
        params = params * scale

    def round_arr(arr): return [int(round(x)) for x in arr]
    
    p = [int(round(x)) for x in params[:10]]
    mat_mg = f"{{chess.PAWN: {p[0]}, chess.KNIGHT: {p[1]}, chess.BISHOP: {p[2]}, chess.ROOK: {p[3]}, chess.QUEEN: {p[4]}, chess.KING: 0}}"
    mat_eg = f"{{chess.PAWN: {p[5]}, chess.KNIGHT: {p[6]}, chess.BISHOP: {p[7]}, chess.ROOK: {p[8]}, chess.QUEEN: {p[9]}, chess.KING: 0}}"

    pst_tables = []
    names = ["MG_PAWN", "EG_PAWN", "MG_KNIGHT", "EG_KNIGHT", "MG_BISHOP", "EG_BISHOP",
             "MG_ROOK", "EG_ROOK", "MG_QUEEN", "EG_QUEEN", "MG_KING", "EG_KING"]
             
    for i, name in enumerate(names):
        offset = 10 + i * 64
        table = params[offset : offset + 64]
        # Center the table dynamically!
        mean_val = np.mean(table)
        table = [v - mean_val for v in table]
        
        # Add the extracted mean back into the Material dict dynamically using parsing later?
        # Standard procedure is to just keep centered tables since engine ignores exact offset via tapering mapping
        
        lines = [f"{name}_TABLE = ["]
        for rank in range(8):
            row = table[rank*8 : rank*8+8]
            lines.append("    " + ", ".join(f"{int(round(x)):>4}" for x in row) + ",")
        lines.append("]")
        pst_tables.append("\n".join(lines))
        
    b = 10 + 768
    bonuses_mg_pp = [0] + round_arr(params[b+6:b+12]) + [0]
    bonuses_eg_pp = [0] + round_arr(params[b+12:b+18]) + [0]
    
    bonuses_str = f"""
# ── Bonuses ──
DOUBLED_PAWN_PENALTY = {int(round(params[b+0]))}
ISOLATED_PAWN_PENALTY = {int(round(params[b+1]))}
BISHOP_PAIR_BONUS = {int(round(params[b+2]))}
ROOK_OPEN_FILE_BONUS = {int(round(params[b+3]))}
ROOK_SEMI_OPEN_FILE_BONUS = {int(round(params[b+4]))}
KING_SHIELD_BONUS = {int(round(params[b+5]))}

PASSED_PAWN_BONUS_MG = {bonuses_mg_pp}
PASSED_PAWN_BONUS_EG = {bonuses_eg_pp}
ROOK_BEHIND_PASSER_BONUS = {int(round(params[b+18]))}
CONNECTED_PASSER_BONUS = {int(round(params[b+19]))}
KING_PROXIMITY_MULT = {round(params[b+20], 3)}

HANGING_KNIGHT_PENALTY = {int(round(params[b+21]))}
HANGING_BISHOP_PENALTY = {int(round(params[b+22]))}
HANGING_ROOK_PENALTY = {int(round(params[b+23]))}
HANGING_QUEEN_PENALTY = {int(round(params[b+24]))}
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('"""\nTuned Evaluation Weights\n========================\nAuto-generated by texel_tuning.py\n"""\n\n')
        f.write("import chess\n\n")
        f.write("# ── Material Values ──\n")
        f.write(f"MG_VALUE = {mat_mg}\n")
        f.write(f"EG_VALUE = {mat_eg}\n\n")
        for tbl in pst_tables:
            f.write(tbl + "\n\n")
        f.write(bonuses_str)

import csv
def load_data(csv_path):
    boards = []
    sf_evals = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            boards.append(chess.Board(row['fen']))
            sf_evals.append(float(row['eval_cp']))
    return boards, np.array(sf_evals, dtype=np.float64)

def main():
    data_path = os.path.join(_PROJECT_ROOT, "data", "training", "dataset.csv")
    if not os.path.exists(data_path):
         print(f"Data not found at {data_path}. Run generate_dataset.py.")
         sys.exit(1)

    print("Loading dataset...")
    boards, sf_evals = load_data(data_path)
    
    # Pre-cap evaluations to prevent outlier explosion
    sf_evals = np.clip(sf_evals, -1500, 1500)
    sf_probs = 1 / (1 + 10 ** (-np.array(sf_evals) / 400.0))

    print("Building enormous design matrix (incorporating massive heuristical mappings)...")
    X, mop_up_biases = build_design_matrix(boards)
    
    params = pack_params()
    initial_params = params.copy()
    
    print(f"Starting L-BFGS-B Optimization with anchored L2 bounds... (N={len(boards)}, Params={TOTAL_PARAMS})")
    
    bounds = []
    for p in params:
        bounds.append((-3000, 3000))
        
    res = scipy.optimize.minimize(
        fun=compute_loss_and_grad,
        x0=params,
        args=(X, mop_up_biases, sf_probs, 0.0001, initial_params),
        method='L-BFGS-B',
        jac=True,
        bounds=bounds,
        options={'maxiter': 500, 'disp': True, 'ftol': 1e-4}
    )

    print("\\nOptimization completed.")
    print(res.message)
    print(f"Final Loss: {res.fun:.6f}")
    
    output_path = os.path.join(_PROJECT_ROOT, "algorithms", "tuned_weights.py")
    save_tuned_weights(res.x, output_path)
    print(f"\\nTuned weights successfully scaled and saved to {output_path}")

if __name__ == "__main__":
    main()

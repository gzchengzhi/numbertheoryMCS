# tools/erdos_straus_p1_mod24_prove_by_system.py
"""20.8: 模拟 MCS 沿着论文思路进行推导。"""

def prove_by_system():
    print("=== MCS Derivation Start ===\n")
    print("Given: p ≡ 1 (mod 24), r ≡ 3 (mod 4) is prime.")
    print("Goal: Derive the equivalence condition for branch success, and the S-unit equation for counterexamples.\n")

    # Step 1
    print("[Step 1] Define the branch equation...")
    print("  4/p = 4/(p+r) + r/(pq), where q = (p+r)/4.")
    print("  -> Activate neuron: branch_equation_p1_mod24\n")

    # Step 2
    print("[Step 2] Apply the two-denominator criterion...")
    print("  Exists d | p^2 q^2 such that d ≡ -pq (mod r).")
    print("  -> Activate neuron: success_criterion_congruence\n")

    # Step 3
    print("[Step 3] Substitute p ≡ 4q (mod r)...")
    print("  d ≡ -4q^2 (mod r).")
    print("  -> Activate neuron: simplified_congruence\n")

    # Step 4
    print("[Step 4] Enumerate d = p^a q^b (0 <= a,b <= 2), eliminate q^2...")
    print("  Three independent equations:")
    print("    (1) q ≡ -1 (mod r)")
    print("    (2) q ≡ -1/4 (mod r)")
    print("    (3) q^2 ≡ -1/4 (mod r)")
    print("  -> Activate neuron: dangerous_classes\n")

    # Step 5
    print("[Step 5] Translate q back to p...")
    print("  Since q = (p+r)/4:")
    print("    (1) p ≡ -4 (mod r)  => r | p+4")
    print("    (2) p ≡ -1 (mod r)  => r | p+1")
    print("    (3) p^2 ≡ -4 (mod r)")
    print("  -> Activate neuron: translate_to_p\n")

    # Step 6
    print("[Step 6] Apply quadratic reciprocity...")
    print("  For r ≡ 3 (mod 4), (-4/r) = (-1/r)(4/r) = -1.")
    print("  Therefore p^2 ≡ -4 (mod r) has no solution.")
    print("  -> Activate neuron: quadratic_reciprocity_exclusion\n")

    # Step 7
    print("[Step 7] Final reduction...")
    print("  Branch success iff r | p+4 or r | p+1.")
    print("  -> Activate neuron: final_divisibility\n")

    # Step 8
    print("[Step 8] Assume a counterexample exists (no r < p succeeds)...")
    print("  Then p+1 and p+4 cannot contain any 3 (mod 4) prime factor.")
    print("  Since p+1 < 2p and p+4 < 2p, any 3 (mod 4) factor must be >= p, impossible.")
    print("  Thus p+1 and p+4 are composed only of 1 (mod 4) prime factors.")
    print("  Let p+1 = 2u1, p+4 = u2, where u1, u2 are pure 1 (mod 4) smooth numbers.")
    print("  Eliminating p yields the S-unit equation: u2 - 2u1 = 3.")
    print("  -> Activate neuron: counterexample_S_unit\n")

    print("=== MCS Derivation End ===")
    print("Conclusion: A counterexample to the Erdos-Straus conjecture for p ≡ 1 (mod 24)")
    print("            is equivalent to the existence of 1 (mod 4) smooth numbers u1, u2")
    print("            satisfying u2 - 2u1 = 3, with 2u1 - 1 prime.")
    print("            (Note: Proving this equation has no solutions requires transcendental number theory,")
    print("             which is beyond the current capability of MCS.)")

if __name__ == "__main__":
    prove_by_system()
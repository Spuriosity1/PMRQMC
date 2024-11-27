-----------------------------------------------------------------------------------------------------------

This program is introduced in the paper: Lev Barash, Arman Babakhani, Itay Hen, A quantum Monte Carlo algorithm for arbitrary spin-1/2 Hamiltonians, Physical Review Research 6, 013281 (2024).

-----------------------------------------------------------------------------------------------------------

# COMPILING

Instructions for the Permutation Matrix Representation Quantum Monte Carlo for spin-1/2 Hamiltonians:

1. Prepare the Hamiltonian input text file, e.g. "ham.txt".
   Each line corresponds to a summand of the Hamiltonian and contains "J q_1 sigma_1 q_2 sigma_2 ...", where J is a constant, q_i is a spin index, and sigma_i = X, Y, and Z correspond to the Pauli matrices. It is also possible to use 1, 2, and 3 instead of X, Y and Z.
2. Decide on the numerical parameters for the QMC run. An example is provided at `examples/standard_params.toml`.
3. Prepare a simulation with `python3 construct_sim.py --hamiltonian <ham.txt> -o <executable_name> <params.toml>`. To compile the TFIM example, this is `python3 construct_sim.py -H examples/H_ZZ-XX_plaq.txt -o bin/test examples/standard_params.toml`.
4. To include an additional observable in the output, pass a list of observable files (in the same format as the Hamiltonian from earlier) to the `--observables` option of the build script.

## NOTES
1. The Makefile is included for convenience, but is not strictly necessary. `construct_sim.py` calls this automatically if the `prepare` utility needs to be built.
2. It is necessary to recompile for every different temperature. For any moderately difficult problem, the runtime of the simulation will significantly exceed this overhead.


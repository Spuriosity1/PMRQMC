import subprocess
import datetime
import argparse
import toml
import os


tmp_dir = "tmp"

DATE = datetime.datetime.now().isoformat()

parser = argparse.ArgumentParser()
parser.add_argument("paramfile", type=str,
                    help="a TOML file specifying the simulation parameters")
parser.add_argument("hamfile", type=str,
                    help="A text file specifying the Hamiltonian in Pauli-sum form")
parser.add_argument("opfile", nargs="*", type=str,
                    help="A list of text files specifying the custom observables in Pauli-sum form")
parser.add_argument("-o", "--output_executable", type=str, required=True,
                    help="name of the executable to be run")
parser.add_argument("--CXX", type=str,
                    help="The non-MPI CXX compiler to use.",
                    default="g++")
parser.add_argument("--MPICXX", type=str,
                    help="The MPI CXX compiler to use. Defaults to non-MPI compilation.",
                    default=None)

parser.add_argument('-T', "--temperature", type=float, 
                    help="simulation temperature")

args = parser.parse_args()

with open(args.paramfile) as pf:
    param_data = dict(toml.load(pf))

if hasattr(args, "temperature"):
    # command line temperature override
    param_data['beta'] = 1./args.temperature

assert param_data['beta'] is not None

work_dir = os.path.join(tmp_dir, args.output_executable)

try:
    os.mkdir(work_dir)
except FileExistsError:
    print("WARN: intermediates already generated with this name, overwriting")

# Write the 'parameters.hpp' header file using the configuration
with open(os.path.join(work_dir, "parameters.hpp"), 'w') as f:
    f.write(f'// This file was generated automatically by \n//{__file__}\n')
    for k in param_data:
        if type(param_data[k]) is bool:
            if not param_data[k]:
                f.write("//")  # comment the line if not needed

            f.write(f"#define {k}\n")
        else:
            f.write(f"#define {k} {param_data[k]}\n")




PREP_EXEC_PATH = os.path.join(work_dir, "prepare")
preprocessor_compile = [args.CXX, "-O3", "-std=c++11", "-I", work_dir,
                        "-o", PREP_EXEC_PATH, "prepare.cpp"]

prep_command = [PREP_EXEC_PATH, args.hamfile]
if hasattr(args, "opfile"):
    prep_command += args.opfile

if args.MPICXX is None:
    main_compile = [args.CXX, "-O3", "-std=c++11", "-o", args.output_executable,
                "-I", work_dir, "PMRQMC.cpp"]
else:
    main_compile = [args.MPICXX, "-O3", "-o", args.output_executable,
                "-I", work_dir, "PMRQMC_mpi.cpp"]


try:

    logfile_loc = f"tmp/compile_{DATE}.log"

    with open(logfile_loc, 'wb') as log:

        def logit(res):
            log.write(b"STDOUT\n: ")
            log.write(res.stdout)
            print(res.stdout.decode('utf8'))
            log.write(b"STDERR\n: ")
            log.write(res.stderr)

        log.write(b"XXX COMPILING PREPROCESSOR\n")
        log.write(b"#"*80 + b"\n\n")
        res = subprocess.run(preprocessor_compile, capture_output=True)
        logit(res)
        res.check_returncode()

        log.write(b"\nXXX PREPARING FILE\n")
        log.write(b"#"*80 + b"\n")

        res = subprocess.run(prep_command, capture_output=True)
        logit(res)
        res.check_returncode()

        # move to the subdir to avoid confusion
        os.rename("hamiltonian.hpp",
                  os.path.join(work_dir, "hamiltonian.hpp"))

        log.write(b"\nXXX COMPILING\n")
        log.write(b"#"*80 + b"\n")
        res = subprocess.run(main_compile, capture_output=True)
        logit(res)
        res.check_returncode()

        print("Success!")

except subprocess.CalledProcessError as e:
    print(f"Failed. Check the logs in {logfile_loc} for details.")
    raise e

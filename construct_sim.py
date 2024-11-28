import subprocess
import datetime
import argparse
import toml
import os


script_dir = os.path.dirname(__file__)

DATE = datetime.datetime.now().isoformat()

# Ensure that `prepare` has been compiled
PREP_EXEC_PATH = os.path.join(script_dir, "bin/prepare")
if not os.path.isfile(PREP_EXEC_PATH):
    print(f"No executable found at {PREP_EXEC_PATH}. Running `make`")
    subprocess.run(["make", "-C", script_dir])


class QMCsettings:
    def __init__(self, paramdata):
        """
        Creates a sim-builder object with all necessary physical information.
        @param tomlfile -> A TOML file containing all necessary data.
        @param resource_path -> the path to hamiltonian.txt and any operator.txt files

        """
        self.numerical = dict(
            Tsteps=1000000,      # number of MC initial equilibration updates
            steps=10000000,              # number of MC updates
            stepsPerMeasurement=10,       # number of MC updates per measurement
            beta=1.0,                   # inverse temperature

            qmax = 1000,                # upper bound for the maximal length of the sequence of permutation operators
            Nbins =  250,                 # number of bins for the error estimation via binning analysis
            EXHAUSTIVE_CYCLE_SEARCH = True      #  set to false for a more restrictive cycle search
        )

        # 'True' indicates that this observavble will be measured.
        self.std_observables = dict(
            MEASURE_H=True,                     # <H>
            MEASURE_H2=True,                   # <H^2>
            MEASURE_HDIAG=True,                # <H_{diag}>
            MEASURE_HDIAG2=True,               # <H_{diag}^2>
            MEASURE_HOFFDIAG=True,             # <H_{offdiag}>
            MEASURE_HOFFDIAG2=True,            # <H_{offdiag}^2>
            MEASURE_Z_MAGNETIZATION=False      # Z-magnetization
        )

        self.custom_observable_files = []
        self.hamiltonian_file = None

        self.load_parameters(paramdata)

    def load_parameters(self, data):
        for k in data:
            if k in self.numerical:
                assert type(self.numerical[k]) is type(data[k])
                self.numerical[k] = data[k]
            elif k in self.std_observables:
                assert type(data[k]) is bool
                self.std_observables[k] = data[k]
            elif k == "observables":
                self.custom_observable_files.append(data[k])
            elif k == "hamiltonian":
                self.hamiltonian_file = data[k]
            else:
                print(f"WARN: ignoring option {k} in passed params")

    def _write_parameters_hpp(self, dest_dir):
        # Write the 'parameters.hpp' header file to dest_dir
        with open(os.path.join(dest_dir, "parameters.hpp"), 'w') as f:
            f.write('// This file was generated automatically by \n')
            f.write(f'// {__file__}\n')

            for paramd in [self.numerical, self.std_observables]:
                for k in paramd:
                    if type(paramd[k]) is bool:
                        if not paramd[k]:
                            f.write("//")  # comment the line if not needed

                        f.write(f"#define {k}\n")
                    else:
                        f.write(f"#define {k} {paramd[k]}\n")

    def build(self, executable_name, CXX, build_dir='.'):
        """
        Compiles a simulation, named <executable_path>, using compiler CXX.
        Intermediate data is stored in build_dir.
        """
        # write parameters.hpp to build_dir/parameters.hpp
        self._write_parameters_hpp(build_dir)

        logfile_loc = os.path.join(build_dir, f"compile_{DATE}.log")

        loc_Ofiles = []
        for file in self.custom_observable_files:
            loc_Ofile = 'O'+os.path.basename(file)
            subprocess.run(['cp', file, 
                            os.path.join(build_dir, loc_Ofile)])
            loc_Ofiles.append(loc_Ofile)

        prep_command = [PREP_EXEC_PATH, os.path.abspath(self.hamiltonian_file)]
        prep_command += loc_Ofiles

        main_compile = [CXX, "-O3", "-std=c++11",
                        "-o", os.path.abspath(executable_name), "-I", script_dir, "-I", ".",
                        os.path.join(script_dir, "PMRQMC.cpp")]

        logfile = open(logfile_loc, 'wb')

        def logit(res):
            logfile.write(b"STDOUT\n: ")
            logfile.write(res.stdout)
            print(res.stdout.decode('utf8'))
            logfile.write(b"STDERR\n: ")
            logfile.write(res.stderr)

        logfile.write(b"\nXXX PREPARING FILE\n")
        logfile.write(b"#"*80 + b"\n")

        # convert all hamiltonian and observable txt files to a header
        # hamiltonian.hpp
        print(prep_command)
        res = subprocess.run(prep_command, capture_output=True, cwd=build_dir)
        logit(res)
        try:
            res.check_returncode()
        except subprocess.CalledProcessError as e:
            print("Failed to prepare headers.\n")
            print(f"Check the logs in {logfile_loc} for details.")
            raise e

        # compile
        logfile.write(b"\nXXX COMPILING\n")
        logfile.write(b"#"*80 + b"\n")
        print(main_compile)
        res = subprocess.run(main_compile, capture_output=True, cwd=build_dir)
        logit(res)
        try:
            res.check_returncode()
        except subprocess.CalledProcessError as e:
            print("Failed to compile.\n")
            print(f"Check the logs in {logfile_loc} for details.")
            raise e

        logfile.close()


# behaviour if invoked as a script
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("paramfile", type=str,
                        help="a TOML file specifying the numerical parameters")
    parser.add_argument("-H", "--hamiltonian", type=str,
                        help="txt file specifying hamiltonian")
    parser.add_argument("-O", "--observables", type=str, nargs="*",
                        help="txt files specifying operators")
    parser.add_argument("-o", "--output_executable", type=str, required=True,
                        help="path for the simulation executable")
    parser.add_argument("--CXX", type=str,
                        help="The (non-MPI) CXX compiler to use.",
                        default="g++")

    parser.add_argument('-T', "--temperature", type=float,
                        help="simulation temperature")

    parser.add_argument("--tmp_dir", type=str, default="build")

    args = parser.parse_args()

    try:
        os.mkdir(args.tmp_dir)
    except FileExistsError:
        print(f"WARN: intermediates exist at {args.tmp_dir}, overwriting...")

    with open(args.paramfile, 'r') as f:
        params = toml.load(f)

    if args.temperature is not None:
        params['beta'] = 1./args.temperature

    settings = QMCsettings(params)
    if args.hamiltonian is not None:
        if settings.hamiltonian_file is not None:
            raise Exception("Hamiltonian file is specified twice, must use only toml or command line")
        settings.hamiltonian_file = args.hamiltonian
    assert settings.hamiltonian_file is not None

    if args.observables is not None:
        for opfile in args.observables:
            settings.custom_observable_files.append(opfile)

    settings.build(args.output_executable, args.CXX, args.tmp_dir)

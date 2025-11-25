{ pkgs, lib, config, inputs, ... }:

{
  packages = [
    pkgs.git
    pkgs.quarto
  ];

  env.LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
    pkgs.zlib
  ];

  languages.python = {
    enable = true;
    venv.enable = true;
    venv.requirements = ''
    ipython
    ipykernel
    pandas
    numpy
    matplotlib
    pyarrow
    polars==1.24.0
    '';
  };

  enterShell = ''
    # Register a Jupyter kernel pointing to the venv
    python -m ipykernel install --user --name devenv --display-name "Python (devenv)"
  '';

}

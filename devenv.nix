{ pkgs, lib, config, inputs, ... }:

{
  packages = [
    pkgs.git
    pkgs.quarto
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
    polars==1.24.0
    '';
  };

  enterShell = ''
    # Register a Jupyter kernel pointing to the venv
    python -m ipykernel install --user --name devenv --display-name "Python (devenv)"
  '';

}

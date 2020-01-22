import os


def tex2png(snippet: str, **kwargs):
    """
    Author: Eric Schneider
    Adapted from Ivan E. Cao-Berg's MATLAB script, found here:
    https://github.com/icaoberg/latex2png/blob/master/latex2png.m

    Feel free to use this wherever <3

    tex2png
    A python script to convert LaTeX snippets to images.
    Dependencies:
    - some sort of TeX typesetter. I recommend texlive.
    - dvipng

    Arguments:
        snippet: the LaTeX snippet to parse.

    kwargs:
        debug: If enabled, will keep intermediate files and print command output
            to stdout.
        density: Proportional to the size of the output image.
        background: The background color. Translates to the -bg parameter of
            dvipng, so read its manual for formatting info.
        foreground: The foreground color. Translates to -fg of dvipng.
        outfile: The pathname (without the .png) of the output file.
        fontsize, mathsize: I'm...not really sure.

    returns:
        -1 for user error
        0 for success
        1 for programmer error
    """
    tex_format = r"""\documentclass[fleqn]{{article}}
    \DeclareMathSizes{{{0}}}{{{1}}}{{{0}}}{{{0}}}
    \usepackage{{amssymb,amsmath,bm}}
    \usepackage[latin1]{{inputenc}}
    \begin{{document}}
    \thispagestyle{{empty}}
    \begin{{equation*}}
    {2}
    \end{{equation*}}
    \end{{document}}"""

    debug = kwargs.get('debug', False)
    density = kwargs.get('density', 500)
    background = kwargs.get('background', "rgb 1.0 1.0 1.0")
    foreground = kwargs.get('foreground', "rgb 0.0 0.0 0.0")
    outfile = kwargs.get('outfile', 'snippet')
    fontsize = kwargs.get('fontsize', 20)
    mathsize = kwargs.get('mathsize', 30)
    latex = kwargs.get('latex', '/usr/bin/latex')
    dvipng = kwargs.get('dvipng', '/usr/bin/dvipng')

    # delete intermediate files
    def cleanup():
        if not debug:
            extensions = [".aux", ".dvi", ".log", ".tex"]
            for extension in extensions:
                try:
                    os.remove(outfile + extension)
                except FileNotFoundError:
                    pass

    # send output to black hole if not in debug mode.
    pipe = "" if debug else " > /dev/null"

    # check for binaries
    if not os.path.isfile(latex):
        print(f"tex2png: LaTeX was not found in '{latex}'. To install "
              f"LaTex in Ubuntu type in terminal: sudo apt-get install "
              f"texlive-full")
        return 1

    if not os.path.isfile(dvipng):
        print(f"tex2png: dvipng was not found in '{dvipng}'. To install "
              f"dvipng in Ubuntu type in terminal: sudo apt-get install "
              f"dvipng")
        return 1

    # write tex file
    with open(f"{outfile}.tex", "w") as texfile:
        texfile.write(tex_format.format(fontsize, mathsize, snippet))

    # format tex to dvi
    if os.system(f"{latex} -interaction=nonstopmode {outfile}.tex{pipe}") != 0:
        print(f"tex2png: LaTeX command returned a non-zero value.")
        cleanup()
        return -1

    # format dvi to png
    if os.system(f"{dvipng} -q -T tight -bg '{background}' -fg '{foreground}' "
              f"-D {density} {outfile}.dvi -o {outfile}.png{pipe}") != 0:
        print(f"tex2png: dvipng returned a non-zero value.")
        cleanup()
        return -1


    cleanup()
    return 0


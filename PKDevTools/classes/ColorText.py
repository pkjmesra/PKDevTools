"""
The MIT License (MIT)

Copyright (c) 2023 pkjmesra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import platform
import sys

import tabulate as tb
from tabulate import DataRow, Line, tabulate


class tbInternal:
    def __init__(self):
        self.tb = tb

    def tabulate(
        self,
        tabular_data,
        headers=(),
        tablefmt="simple",
        floatfmt="g",
        intfmt="",
        numalign="default",
        stralign="default",
        missingval="",
        showindex="default",
        disable_numparse=False,
        colalign=None,
        maxcolwidths=None,
        rowalign=None,
        maxheadercolwidths=None,
        highlightedRows=[],
        highlightedColumns=[],
        highlightCharacter="\U0001f911",
        focussedTexts=[],
    ):
        tabulated_data = self.tb.tabulate(
            tabular_data=tabular_data,
            headers=headers,
            tablefmt=tablefmt,
            floatfmt=floatfmt,
            intfmt=intfmt,
            numalign=numalign,
            stralign=stralign,
            missingval=missingval,
            showindex=showindex,
            disable_numparse=disable_numparse,
            colalign=colalign,
            maxcolwidths=maxcolwidths,
            rowalign=rowalign,
            maxheadercolwidths=maxheadercolwidths,
        )

        brandName = "PKSCREENER"
        maxIndex = len(brandName) - 1
        col_index = 0
        tab_lines_org = tabulated_data.splitlines()
        tab_lines_mod = []
        highlightRows = (
            len(highlightedRows) >= 1 if highlightedRows is not None else False
        )
        highlightColumns = (
            len(highlightedColumns) >= 1 if highlightedColumns is not None else False
        )
        row_num = 0
        findCellEnding1 = "--" if highlightCharacter == "\U0001f911" else "-"
        findCellEnding2 = "==" if highlightCharacter == "\U0001f911" else "="
        for line in tab_lines_org:
            tab_line = line
            col_num = 0
            if line.startswith("+"):
                tab_line = ""
                columns = line.split("+")[1:]
                for col in columns:
                    if (
                        highlightRows
                        and highlightColumns
                        and (row_num in highlightedRows)
                        and (col_num in highlightedColumns)
                    ):
                        highlightValue = col.replace(
                            findCellEnding1, highlightCharacter
                        ).replace(findCellEnding2, highlightCharacter)
                        tab_line = f"{tab_line}{brandName[col_index: col_index + 1]}{highlightValue}"
                    else:
                        tab_line = (
                            f"{tab_line}{brandName[col_index: col_index + 1]}{col}"
                        )
                    col_index += 1
                    if col_index > maxIndex:
                        col_index = 0
                    col_num += 1
                row_num += 1
            tab_lines_mod.append(tab_line)
        tabulated_data = "\n".join(tab_lines_mod)
        STD_ENCODING = sys.stdout.encoding if sys.stdout is not None else "utf-8"
        return tabulated_data.encode("utf-8").decode(STD_ENCODING)


# https://stackoverflow.com/questions/4842424/list-of-ansi-color-escape-sequences
# Decoration Class
# The ANSI escape sequences you're looking for are the Select Graphic Rendition subset.
# All of these have the form
# \033[XXXm
# where XXX is a series of semicolon-separated parameters.

# The usage goes like:
# \033[code;code;codem  # put 'm' at the last
# \033[code;codem  # use semicolon to use more than 1 code
# \033[codem
# \033[m   # reset

# For example, you can make red text on a green background (but why?) using:
# \033[31;42m
# Font Effects:
# ------------------------------------------------------------------------
# Code	    Effect									Note
# ------------------------------------------------------------------------
# 0		    Reset / Normal							all attributes off
# 1		    Bold or increased intensity
# 2		    Faint (decreased intensity)				Not widely supported.
# 3		    Italic	Not widely supported. 			Sometimes treated as inverse.
# 4		    Underline
# 5		    Slow Blink								less than 150 per minute
# 6		    Rapid Blink								MS-DOS ANSI.SYS; 150+ per minute; not widely supported
# 7		    [[reverse video]]						swap foreground and background colors
# 8		    Conceal									Not widely supported.
# 9		    Crossed-out								Characters legible, but marked for deletion. Not widely supported.
# 10	    Primary(default) font
# 11–19	    Alternate font							Select alternate font n-10
# 20		Fraktur	hardly ever supported
# 21		Bold off or Double Underline			Bold off not widely supported; double underline hardly ever supported.
# 22		Normal color or intensity				Neither bold nor faint
# 23		Not italic, not Fraktur
# 24		Underline off							Not singly or doubly underlined
# 25		Blink off
# 27		Inverse off
# 28		Reveal									conceal off
# 29		Not crossed out
# 30–37	    Set foreground color					See color table below
# 38		Set foreground color					Next arguments are 5;<n> or 2;<r>;<g>;<b>, see below
# 39		Default foreground color				implementation defined (according to standard)
# 40–47	    Set background color					See color table below
# 48		Set background color					Next arguments are 5;<n> or 2;<r>;<g>;<b>, see below
# 49		Default background color				implementation defined (according to standard)
# 51		Framed
# 52		Encircled
# 53		Overlined
# 54		Not framed or encircled
# 55		Not overlined
# 60		ideogram underline						hardly ever supported
# 61		ideogram double underline				hardly ever supported
# 62		ideogram overline						hardly ever supported
# 63		ideogram double overline				hardly ever supported
# 64		ideogram stress marking					hardly ever supported
# 65		ideogram attributes off					reset the effects of all of 60-64
# 90–97	Set bright foreground color				    aixterm (not in standard)
# 100–107	Set bright background color				aixterm (not in standard)

# Now we are living in the future, and the full RGB spectrum is available using:
# \033[38;2;<r>;<g>;<b>m     #Select RGB foreground color
# \033[48;2;<r>;<g>;<b>m     #Select RGB background color
# So you can put pinkish text on a brownish background using
# \033[38;2;255;82;197;48;2;155;106;0mHello
# Support for "true color" terminals is listed here: https://gist.github.com/XVilka/8346728
# https://github.com/termstandard/colors


class colorText:
    HEAD = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[32m"
    BRIGHTGREEN = "\033[92m"
    WARN = "\033[33m"
    BRIGHTYELLOW = "\033[93m"
    FAIL = "\033[31m"
    BRIGHTRED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDR = "\033[4m"
    WHITE = "\033[97m"
    UPARROW = "▲"  # u'\u2191' if "Windows" in platform.system() else "▲"
    DOWNARROW = "▼"  # u'\u2193' if "Windows" in platform.system() else "▼"
    WHITE_FG_BRED_BG = "\033[97;101m"
    WHITE_FG_RED_BG = "\033[97;41m"

    No_Pad_GridFormat = "minpadding"

    def miniTabulator():
        tbi = tbInternal()
        tbi.tb._table_formats[colorText.No_Pad_GridFormat] = tb.TableFormat(
            lineabove=Line("+", "-", "+", "+"),
            linebelowheader=Line("+", "=", "+", "+"),
            linebetweenrows=Line("+", "-", "+", "+"),
            linebelow=Line("+", "-", "+", "+"),
            headerrow=DataRow("|", "|", "|"),
            datarow=DataRow("|", "|", "|"),
            padding=0,
            with_header_hide=None,
        )
        tbi.tb.multiline_formats[colorText.No_Pad_GridFormat] = (
            colorText.No_Pad_GridFormat
        )
        tbi.tb.tabulate_formats = list(sorted(tb._table_formats.keys()))
        return tbi

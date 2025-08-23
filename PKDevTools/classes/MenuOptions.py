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

from enum import Enum

from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.log import default_logger


class MenuRenderStyle(Enum):
    STANDALONE = 1
    TWO_PER_ROW = 2
    THREE_PER_ROW = 3


class menu:
    def __init__(self):
        self.menuKey = ""
        self.menuText = ""
        self.submenu = None
        self.level = 0
        self.isException = None
        self.hasLeftSibling = False
        self.parent = None

    def create(self, key, text, level=0, isException=False, parent=None):
        self.menuKey = str(key)
        self.menuText = text
        self.level = level
        self.isException = isException
        self.parent = parent
        return self

    def keyTextLabel(self):
        return f"{self.menuKey} > {self.menuText}"

    def commandTextKey(self, hasChildren=False):
        cmdText = ""
        if self.parent is None:
            cmdText = f"/{self.menuKey}"
            return cmdText
        else:
            cmdText = f"{
    self.parent.commandTextKey(
        hasChildren=True)}_{
            self.menuKey}"
            return cmdText

    def commandTextLabel(self, hasChildren=False):
        cmdText = ""
        if self.parent is None:
            cmdText = f"{self.menuText}" if hasChildren else f"{self.menuText}"
            return cmdText
        else:
            cmdText = (
                f"{
    self.parent.commandTextLabel(
        hasChildren=True)} > {
            self.menuText}"
            )
            return f"{cmdText}"

    def render(self):
        t = ""
        if self.isException:
            if self.menuText.startswith("~"):
                self.menuText = self.renderSpecial(self.menuKey)
            t = f"\n\n     {self.keyTextLabel()}"
        elif not self.menuKey.isnumeric():
            t = f"\n     {self.keyTextLabel()}"
        else:
            # 9 to adjust an extra space when 10 becomes a 2 digit number
            spaces = "     " if int(self.menuKey) <= 9 else "    "
            if not self.hasLeftSibling:
                t = f"\n{spaces}{self.keyTextLabel()}"
            else:
                t = f"\t{self.keyTextLabel()}"
        return t

    def renderSpecial(self, menuKey):
        return "Must be implemented in the inherited child class to return the special text"


# This Class manages application menus
class menus:
    def __init__(self, menuDictionaryList):
        self.level = 0
        self.menuDict = {}
        if menuDictionaryList is None:
            menuDictionaryList = []
        if len(menuDictionaryList) < 5:
            menuDictionaryList.extend([{}, {}, {}, {}, {}])
        self.menuDictionaryList = menuDictionaryList

    def fromDictionary(
        self,
        rawDictionary={},
        renderStyle=MenuRenderStyle.STANDALONE,
        renderExceptionKeys=[],
        skip=[],
        parent=None,
    ):
        tabLevel = 0
        self.menuDict = {}
        for key in rawDictionary:
            if key in skip:
                continue
            m = menu()
            m.create(
                str(key).upper(), rawDictionary[key], level=self.level, parent=parent
            )
            if key in renderExceptionKeys:
                m.isException = True
            elif str(key).isnumeric():
                m.hasLeftSibling = False if tabLevel == 0 else True
                tabLevel = tabLevel + 1
                if tabLevel >= renderStyle.value:
                    tabLevel = 0
            self.menuDict[str(key).upper()] = m
        return self

    def render(self, asList=False):
        menuText = [] if asList else ""
        for k in self.menuDict.keys():
            m = self.menuDict[k]
            if asList:
                menuText.append(m)
            else:
                menuText = menuText + m.render()
        return menuText

    def renderForMenu(self, selectedMenu=None, skip=[],
                      asList=False, renderStyle=None):
        if selectedMenu is None and self.level == 0:
            # Top level Application Main menu
            return self.renderLevel0Menus(
                skip=skip, asList=asList, renderStyle=renderStyle, parent=selectedMenu
            )
        elif selectedMenu is not None:
            if selectedMenu.level == 0:
                self.level = 1
                # sub-menu of the top level main selected menu
                return self.renderLevel1_X_Menus(
                    skip=skip,
                    asList=asList,
                    renderStyle=renderStyle,
                    parent=selectedMenu,
                )
            elif selectedMenu.level == 1:
                self.level = 2
                # next levelsub-menu of the selected sub-menu
                return self.renderLevel2_X_Menus(
                    skip=skip,
                    asList=asList,
                    renderStyle=renderStyle,
                    parent=selectedMenu,
                )
            elif selectedMenu.level == 2:
                self.level = 3
                # next levelsub-menu of the selected sub-menu
                return (
                    self.renderLevel3_X_Reversal_Menus(
                        skip=skip,
                        asList=asList,
                        renderStyle=renderStyle,
                        parent=selectedMenu,
                    )
                    if selectedMenu.menuKey == "6"
                    else self.renderLevel3_X_ChartPattern_Menus(
                        skip=skip,
                        asList=asList,
                        renderStyle=renderStyle,
                        parent=selectedMenu,
                    )
                )

    def find(self, key=None):
        if key is not None:
            try:
                return self.menuDict[str(key).upper()]
            except Exception as e:
                default_logger().debug(e, exc_info=True)
                return None
        return None

    def renderLevel0Menus(self, asList=False,
                          renderStyle=None, parent=None, skip=None):
        menuText = self.fromDictionary(
            self.menuDictionaryList[0],
            renderExceptionKeys=["T", "E", "U"],
            renderStyle=renderStyle
            if renderStyle is not None
            else MenuRenderStyle.STANDALONE,
            skip=skip,
            parent=parent,
        ).render(asList=asList)
        if asList:
            return menuText
        else:
            print(
                colorText.BOLD
                + colorText.WARN
                + "[+] Select a menu option:"
                + colorText.END
            )
            print(
                colorText.BOLD
                + menuText
                + """

        Enter your choice >  (default is """
                + colorText.WARN
                + self.find("X").keyTextLabel()
                + ") "
                "" + colorText.END
            )
            return menuText

    def renderLevel1_X_Menus(
        self, skip=[], asList=False, renderStyle=None, parent=None
    ):
        menuText = self.fromDictionary(
            self.menuDictionaryList[1],
            renderExceptionKeys=["W", "0", "M"],
            renderStyle=renderStyle
            if renderStyle is not None
            else MenuRenderStyle.THREE_PER_ROW,
            skip=skip,
            parent=parent,
        ).render(asList=asList)
        if asList:
            return menuText
        else:
            print(
                colorText.BOLD
                + colorText.WARN
                + "[+] Select an Index for Screening:"
                + colorText.END
            )
            print(
                colorText.BOLD
                + menuText
                + """

        Enter your choice > (default is """
                + colorText.WARN
                + self.find("12").keyTextLabel()
                + ")  "
                "" + colorText.END
            )
            return menuText

    def renderLevel2_X_Menus(
        self, skip=[], asList=False, renderStyle=None, parent=None
    ):
        menuText = self.fromDictionary(
            self.menuDictionaryList[2],
            renderExceptionKeys=["0", "42", "M"],
            renderStyle=renderStyle
            if renderStyle is not None
            else MenuRenderStyle.TWO_PER_ROW,
            skip=skip,
            parent=parent,
        ).render(asList=asList)
        if asList:
            return menuText
        else:
            print(
                colorText.BOLD
                + colorText.WARN
                + "[+] Select a Criterion for Stock Screening: "
                + colorText.END
            )
            print(
                colorText.BOLD
                + menuText
                + """

        """
                + colorText.END
            )
            return menuText

    def renderLevel3_X_Reversal_Menus(
        self, skip=[], asList=False, renderStyle=None, parent=None
    ):
        menuText = self.fromDictionary(
            self.menuDictionaryList[3],
            renderExceptionKeys=["0"],
            renderStyle=renderStyle
            if renderStyle is not None
            else MenuRenderStyle.STANDALONE,
            skip=skip,
            parent=parent,
        ).render(asList=asList)
        if asList:
            return menuText
        else:
            print(
                colorText.BOLD
                + colorText.WARN
                + "[+] Select an option: "
                + colorText.END
            )
            print(
                colorText.BOLD
                + menuText
                + """

        """
                + colorText.END
            )
            return menuText

    def renderLevel3_X_ChartPattern_Menus(
        self, skip=[], asList=False, renderStyle=MenuRenderStyle.STANDALONE, parent=None
    ):
        menuText = self.fromDictionary(
            self.menuDictionaryList[4],
            renderExceptionKeys=["0"],
            renderStyle=renderStyle
            if renderStyle is not None
            else MenuRenderStyle.STANDALONE,
            skip=skip,
            parent=parent,
        ).render(asList=asList)
        if asList:
            return menuText
        else:
            print(
                colorText.BOLD
                + colorText.WARN
                + "[+] Select an option: "
                + colorText.END
            )
            print(
                colorText.BOLD
                + menuText
                + """

        """
                + colorText.END
            )
            return menuText

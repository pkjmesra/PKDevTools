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

import os

import pikepdf

from PKDevTools.classes import Archiver


class PKPikey:
    def savedFilePath(fileName: str):
        filePath = os.path.join(
            Archiver.get_user_data_dir(), f"{fileName.replace('.pdf', '')}.pdf"
        )
        return filePath

    def createFile(fileName: str, fileKey: str, owner: str):
        try:
            file = pikepdf.Pdf.new()
            PKPikey.saveFile(
    file,
    PKPikey.savedFilePath(fileName),
    fileKey,
     owner)
            return True
        except BaseException:
            PKPikey.removeSavedFile(fileName)
            return False

    def openFile(fileName: str, fileKey: str):
        try:
            pikepdf.Pdf.open(
                PKPikey.savedFilePath(fileName),
                allow_overwriting_input=True,
                password=fileKey,
            )
            return True
        except BaseException:
            PKPikey.removeSavedFile(fileName)
            return False

    def saveFile(file, fileName: str, fileKey: str, owner: str):
        try:
            allow_key = pikepdf.Permissions(
                extract=False,
                accessibility=False,
                modify_annotation=False,
                modify_assembly=False,
                modify_form=False,
                modify_other=False,
                print_highres=False,
                print_lowres=False,
            )
            file.save(
                f"{fileName}",
                encryption=pikepdf.Encryption(
                    user=fileKey, owner=owner, allow=allow_key
                ),
            )
            return True
        except BaseException:
            PKPikey.removeSavedFile(fileName)
            return False

    def removeSavedFile(fileName: str):
        try:
            os.remove(PKPikey.savedFilePath(fileName))
        except BaseException:
            pass

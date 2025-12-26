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

    @staticmethod
    def validateOTPFromSubData(userid: str, otp: str):
        """Validate OTP by downloading PDF from SubData branch and trying to open it.
        
        When Turso DB is down, the emergency OTP mechanism creates a password-protected
        PDF and commits it to the SubData branch. The console app can validate the OTP
        by downloading this PDF and attempting to open it with the user-provided OTP.
        
        Args:
            userid: User ID (PDF filename is {userid}.pdf)
            otp: OTP entered by user (used as PDF password)
            
        Returns:
            bool: True if OTP is valid (PDF opens successfully), False otherwise
        """
        import requests
        import tempfile
        
        try:
            # Download the PDF from SubData branch
            pdf_url = f"https://raw.githubusercontent.com/pkjmesra/PKScreener/SubData/results/Data/{userid}.pdf"
            print(f"[OTP-VALIDATE] Downloading PDF from SubData for user {userid}")
            
            response = requests.get(pdf_url, timeout=30)
            if response.status_code != 200:
                print(f"[OTP-VALIDATE] PDF not found for user {userid} (status: {response.status_code})")
                return False
            
            # Save to temp file
            temp_path = os.path.join(tempfile.gettempdir(), f"{userid}_validate.pdf")
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            try:
                # Try to open PDF with OTP as password
                pikepdf.Pdf.open(temp_path, password=str(otp))
                print(f"[OTP-VALIDATE] OTP validated successfully for user {userid}")
                os.remove(temp_path)
                return True
            except pikepdf.PasswordError:
                print(f"[OTP-VALIDATE] Invalid OTP for user {userid}")
                os.remove(temp_path)
                return False
            except Exception as e:
                print(f"[OTP-VALIDATE] Error opening PDF: {e}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
                
        except Exception as e:
            print(f"[OTP-VALIDATE] Error validating from SubData: {e}")
            return False

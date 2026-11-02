# TagLab
# Network weights are not part of the repository: they are downloaded from the TagLab web site the first time
# a tool needs them (the same files that install.py downloads).

import os
import urllib.request

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog

from source.genutils import modelPath

MODELS_URL = "http://taglab.isti.cnr.it/models/"

# the weights that can be downloaded and their approximate size in MB
MODEL_SIZES_MB = {
    "dextr_corals.pth": 196,
    "deeplab-resnet.pth.tar": 475,
    "ritm_corals.pth": 41,
    "pocillopora.net": 238,
    "porites.net": 238,
    "pocillopora_porite_montipora.net": 238,
    "sam_vit_h_4b8939.pth": 2560,
}


def downloadFile(url, filename, progress=None):
    """
    Downloads url to filename (through a .part file, so that an interrupted download is never mistaken
    for a complete one). progress(read_bytes, total_bytes) may return False to cancel. Returns True if completed.
    """

    request = urllib.request.Request(url, headers={"User-agent": "Mozilla/5.0"})
    part = filename + ".part"
    try:
        cancelled = False
        with urllib.request.urlopen(request) as response, open(part, "wb") as out:
            total = int(response.headers.get("Content-Length", 0))
            read = 0
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                read += len(chunk)
                if progress is not None and progress(read, total) is False:
                    cancelled = True
                    break
        if not cancelled and (total == 0 or read == total):
            os.replace(part, filename)
            return True
    except Exception:
        pass
    if os.path.exists(part):
        os.remove(part)
    return False


def ensureModel(name, parent=None):
    """
    Returns the path of the weights file `name` in the models folder. If it is missing, asks the user and downloads
    it (with a progress dialog). Returns None if the file is not available (declined, cancelled or download failed);
    in that case the user has already been told, so the caller only has to give up.
    """

    path = modelPath(name)
    if os.path.exists(path):
        return path

    if name not in MODEL_SIZES_MB:
        QMessageBox.warning(parent, "Model not found", "The model file " + name + " is not in the models folder.")
        return None

    size = MODEL_SIZES_MB[name]
    reply = QMessageBox.question(parent, "Download model",
                                 "The network weights " + name + " (about " + str(size) + " MB) are needed by this tool "
                                 "and are not installed.\n\nDownload them now from " + MODELS_URL + " ?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
    if reply != QMessageBox.Yes:
        return None

    os.makedirs(os.path.dirname(path), exist_ok=True)

    dialog = QProgressDialog("Downloading " + name + "...", "Cancel", 0, size, parent)
    dialog.setWindowTitle("Downloading model")
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setMinimumDuration(0)
    dialog.setValue(0)

    cancelled = []
    dialog.canceled.connect(lambda: cancelled.append(True))

    def progress(read, total):
        if total > 0:
            dialog.setMaximum(max(1, total // (1 << 20)))
        dialog.setValue(min(read // (1 << 20), dialog.maximum() - 1))
        QApplication.processEvents()
        return not cancelled

    ok = downloadFile(MODELS_URL + name, path, progress)
    dialog.canceled.disconnect()
    dialog.close()

    if not ok:
        if not cancelled:
            QMessageBox.warning(parent, "Download failed",
                                "Could not download " + name + ".\nCheck the internet connection, or download\n" +
                                MODELS_URL + name + "\nand copy it into the folder " + os.path.dirname(path))
        return None

    return path
